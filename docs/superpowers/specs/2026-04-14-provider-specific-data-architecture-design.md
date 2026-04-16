# Provider-Specific Data Architecture Design

## 1. 概述 (Overview)
为了充分利用各数据源（如 Sportmonks 和 Footystats）的独有深度数据，同时避免在数据层（Data Layer）进行复杂的强统一（如 `MatchContext`）所带来的负担，我们将对数据处理架构进行重构。

核心理念是从“统一抽象”转向“**生数据缓存 (Raw Data Cache) + 专属分析技能 (Provider-Specific Skills)**”。

## 2. 数据预热与双写缓存层 (Pre-warming & Dual-Write Cache)
新增数据预热引擎，旨在将 API 请求与分析过程解耦，并提供极速的数据访问。

### 2.1 触发机制与范围
- **目标**: 针对配置的重点联赛列表（如 `config/watchlist.yaml`），获取**今日所有比赛**的数据。
- **执行方式**: 定时任务或按需手动执行（如 `scripts/prewarm_cache.py --date 2026-04-14`）。
- **数据范围**: 尽可能拉取包含所有附加信息（Includes/Extras）的完整原始 JSON。

### 2.2 双写存储策略 (Dual-Write Storage)
获取到的原始数据将同时写入以下两种存储介质：
1. **JSON 文件系统 (主用)**:
   - **路径规则**: `data/cache/{provider}/{YYYY-MM-DD}/matches.json`
   - **用途**: 供分析 Agent 直接读取，具备人类可读性，便于调试。
2. **SQLite 本地数据库 (备份与未来扩展)**:
   - **数据库文件**: `data/cache/goalcast.db`
   - **表结构**: `raw_sportmonks_matches`, `raw_footystats_matches`
   - **核心字段**: `match_id` (主键), `date` (索引), `league_id` (索引), `raw_data` (JSON 文本)。
   - **用途**: 作为结构化备份，未来可支持跨表复杂查询与回溯测试。

## 3. 轻量级读取层 (Cache Reader)
取代原有的 `DataFusion` 和庞大的 `MatchContext`，引入极简的数据读取接口：
- `get_cached_matches(provider: str, date: str, leagues: list[str] = None) -> list[dict]`
- 直接从 `data/cache/{provider}/{YYYY-MM-DD}/matches.json` 中反序列化并返回 Python 字典列表。
- 在内存中缓存已读取的 JSON（如 Python Dict），确保同一分析任务中的极速响应。

## 4. 专属分析技能 (Provider-Specific Analyst Skills)
分析 Agent 的 Skill 将与特定数据源强绑定，充分释放独有数据的价值：
- **`sportmonks-analyst-v1/skill.md`**: 
  - 专注于解析 Sportmonks 的原始数据结构（如详尽的 xG 数据、阵容名单、赔率走势等）。
  - Prompt 明确指导大模型如何解析该特定数据源的 JSON 结构并执行深度分析。
- **`footystats-analyst-v1/skill.md`**: 
  - 专注于解析 Footystats 的原始数据结构（如球队近期状态、特定的统计模型等）。
  - Prompt 明确指导大模型利用 Footystats 的独特指标进行分析。

## 5. 执行流程 (Execution Flow)
1. **准备阶段**: 运行预热脚本 `python scripts/prewarm_cache.py --date 2026-04-14`，系统拉取数据并完成 JSON 和 SQLite 的双写。
2. **分析阶段**: Analyst Agent 挂载 `sportmonks-analyst-v1` 或 `footystats-analyst-v1` 技能。
3. **数据读取**: Agent 通过 MCP 工具或直接调用 `CacheReader` 读取本地缓存的今日目标联赛的生数据。
4. **生成洞察**: Agent 根据专属 Skill 的指导，对生数据进行解析并输出赛事分析报告。

## 6. 优势与权衡 (Trade-offs)
- **优势**: 
  - 彻底解耦，无需维护庞大且容易失效的统一数据契约。
  - 最大限度保留和利用各 Provider 的独特数据。
  - 分析过程不再受制于网络延迟和 API 限制，速度极快。
- **权衡**:
  - Analyst Agent（LLM）需要直接理解和解析相对复杂的原始 JSON 结构。由于 LLM 具备强大的模式识别能力，这一权衡是可接受且高效的。

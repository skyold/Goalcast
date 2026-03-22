# Goalcast AI — Task Breakdown

**版本**: 1.0  
**关联**: spec.md · checklist.md  
**最后更新**: 2026-03-22  

---

## 总览

```
Phase 1 · MVP        ████████░░  目标：能跑起来，手动输入，自动分析
Phase 2 · 自动化      ░░░░░░░░░░  目标：数据采集自动化，减少手动操作
Phase 3 · 高级统计    ░░░░░░░░░░  目标：引入球员级数据和高级战术统计
Phase 4 · 回测校准    ░░░░░░░░░░  目标：历史存档 + 模型校准闭环
```

---

## Phase 1 · MVP

> **目标**：系统能运行完整的单场分析，输入由人工准备，输出结构化 JSON 和分析报告。  
> **预计工期**：5–8 天  
> **成本**：FootyStats Hobby £29.99/月

---

### T1 — 项目基础设施

**优先级**: P0 · 阻塞所有后续任务

#### T1.1 项目初始化
- 创建目录结构（参考 spec.md §6.2）
- 初始化 `pyproject.toml` 或 `requirements.txt`
- 配置 `.env` + `.env.example`，定义所有 API Key 变量
- 初始化 Git，设置 `.gitignore`（排除 `.env`、`*.db`、`cache/`）
- 创建 `README.md` 基础模板

**产出**：可运行的空项目骨架

#### T1.2 日志与配置系统
- 安装并配置 `loguru`，统一日志格式
- 实现 `settings.py`：从 `.env` 加载所有配置项
- 定义全局常量：联赛参数表、主场优势系数、降级规则阈值

**产出**：`src/utils/logger.py` · `config/settings.py`

#### T1.3 速率限制与缓存工具
- 实现通用速率限制器（令牌桶或简单 sleep）
- 实现本地文件缓存（JSON 格式，带 TTL）
- 为每个数据源配置独立速率限制参数

**产出**：`src/utils/rate_limiter.py` · `src/utils/cache.py`

---

### T2 — 数据采集层（Collectors）

**优先级**: P0

#### T2.1 FootyStats API 客户端
- 实现 `FootyStatsClient` 类，封装所有端点
- 方法列表：
  - `get_team(team_id)` → 球队赛季统计
  - `get_league_matches(season_id, date)` → 比赛列表
  - `get_match(match_id)` → 比赛详情 + H2H + 赔率
  - `get_league_table(season_id, max_time=None)` → 积分表
- 实现请求重试（3次，指数退避）
- 实现响应缓存（ball队统计缓存 24h，比赛数据缓存 6h）
- 单元测试：mock API 响应，验证字段映射

**产出**：`src/collectors/footystats.py` + tests

#### T2.2 ClubElo API 客户端
- 实现 `ClubEloClient` 类
- 方法：`get_elo(team_name, date=None)` → 返回 Elo 分值
- 维护球队名称映射表（FootyStats 名称 → ClubElo 格式）
- 映射表覆盖：英超、西甲、意甲、德甲、法甲、欧冠主要球队（约 120 支）

**产出**：`src/collectors/clubelo.py` · `config/team_name_map.json`

#### T2.3 The Odds API 客户端
- 实现 `OddsAPIClient` 类
- 方法：
  - `get_current_odds(sport, regions, markets)` → 实时赔率
  - `get_historical_odds(sport, event_id, date)` → 历史赔率（付费功能）
- 实现免费额度监控（记录月度用量，接近 500 次时警告）

**产出**：`src/collectors/odds_api.py`

#### T2.4 OpenWeatherMap 客户端
- 实现 `WeatherClient` 类
- 方法：`get_match_weather(lat, lon, match_datetime)` → 返回风速、降水量
- 维护场馆坐标数据表（主要联赛球场 GPS 坐标）
- 实现天气到 xG 调整值的转换逻辑

**产出**：`src/collectors/weather.py` · `config/stadiums.json`

---

### T3 — 数据聚合层（Aggregator）

**优先级**: P0

#### T3.1 数据模型定义
- 用 `Pydantic` 定义所有数据结构：
  - `MatchInfo`：赛事基本信息
  - `TeamStats`：球队统计数据包
  - `OddsData`：赔率数据包
  - `ContextData`：情境数据（伤病、赛程、动力）
  - `AnalysisInput`：完整分析输入包（上述所有数据的聚合）
- 定义字段验证规则（范围检查、必填检查）

**产出**：`src/aggregator/schema.py`

#### T3.2 Match Builder
- 实现 `MatchBuilder.build(match_id, manual_overrides=None)` 方法
- 流程：
  1. 从 FootyStats 获取比赛基本信息
  2. 并发获取双方球队统计（asyncio）
  3. 获取 Elo 评分
  4. 获取开盘/即时赔率
  5. 获取积分表位置
  6. 获取天气数据
  7. 执行零层数据完整性检查
  8. 生成 `data_quality` 评级和 `missing_data` 列表
- 支持 `manual_overrides`：允许用户粘贴手动采集的数据（阵容、伤病）

**产出**：`src/aggregator/match_builder.py`

#### T3.3 手动数据输入接口
- 实现结构化手动输入解析器：
  - `parse_lineup(text)` → 解析从 FotMob 复制的首发名单文本
  - `parse_injuries(text)` → 解析伤病名单文本
  - `parse_odds(text)` → 解析手动复制的赔率数值

**产出**：`src/aggregator/manual_input.py`

---

### T4 — 分析引擎层（Engine）

**优先级**: P0

#### T4.1 提示词管理
- 将 v3.0 提示词存储为结构化模板文件
- 实现 `PromptBuilder.build(analysis_input: AnalysisInput)` → 格式化后的完整 prompt
- 提示词版本控制：文件命名 `prompt_v3.0.md`，代码中引用版本号
- 支持动态插入：联赛参数、比赛类型、数据质量注释

**产出**：`src/engine/prompt.py` · `prompts/v3.0.md`

#### T4.2 Claude API Runner
- 实现 `AnalysisRunner.run(prompt)` → 调用 Claude API
- 配置：使用 `claude-sonnet-4-6`，`max_tokens=4000`
- 实现流式输出（streaming）以减少等待感
- 错误处理：API 超时、速率限制、响应截断
- 重试逻辑：最多 2 次重试

**产出**：`src/engine/runner.py`

#### T4.3 输出解析与校验
- 实现 `OutputParser.parse(raw_response)` → `AnalysisOutput` Pydantic 模型
- 校验规则：
  - 概率三项之和 ≈ 100%（允许 ±0.5% 误差）
  - 置信度在 [30, 90] 范围内
  - EV 值在合理范围（-1 到 +2）
  - JSON 结构完整性检查
- 解析失败时保留原始响应，记录错误，不抛出异常

**产出**：`src/engine/parser.py`

---

### T5 — 存储层（Storage）

**优先级**: P1

#### T5.1 数据库设计与初始化
- 设计 SQLite schema（参考 spec.md §5.2）
- 主要表：
  - `analyses`：每场分析记录（预测输出）
  - `matches`：比赛基本信息缓存
  - `team_stats`：球队统计缓存（带时间戳）
  - `data_quality_log`：数据缺失记录
- 实现数据库初始化脚本（`CREATE TABLE IF NOT EXISTS`）

**产出**：`src/storage/models.py` · `src/storage/init_db.py`

#### T5.2 Repository 层
- 实现 CRUD 操作：
  - `save_analysis(output: AnalysisOutput)` → 保存分析结果
  - `get_analysis(analysis_id)` → 查询历史分析
  - `list_analyses(filters)` → 列表查询
  - `update_actual_result(analysis_id, result, score)` → 赛后填入实际结果

**产出**：`src/storage/repository.py`

---

### T6 — CLI 入口

**优先级**: P1

#### T6.1 单场分析 CLI
- 实现 `scripts/analyze_match.py`
- 参数：
  - `--match_id` FootyStats 比赛 ID（必填）
  - `--lineup_home` 手动首发（可选，JSON 或文本）
  - `--lineup_away` 手动首发（可选）
  - `--injuries` 手动伤病列表（可选）
  - `--dry_run` 只生成输入包，不调用 Claude
- 运行流程：数据采集 → 聚合 → 提示词构建 → Claude 分析 → 解析 → 存储 → 打印输出

**产出**：`scripts/analyze_match.py`

#### T6.2 输出格式化
- 命令行友好的输出格式（彩色终端输出）
- 同时保存 JSON 文件到 `data/exports/{match_id}_{timestamp}.json`
- 关键信息摘要打印：概率、最可能比分、EV、置信度、投注建议

**产出**：`src/utils/formatter.py`

---

## Phase 2 · 自动化数据采集

> **目标**：消除手动数据准备步骤，数据采集全自动化。  
> **前置条件**：Phase 1 完整运行稳定后启动  
> **预计工期**：1–2 周

---

### T7 — Understat 集成

#### T7.1 安装与封装
- 安装 `understatapi` PyPI 包
- 实现 `UnderstatClient` 封装层，接口与其他 Collector 统一
- 提取字段：xG/xGA 每场、PPDA、控球率趋势

#### T7.2 近期数据计算
- 实现 `compute_recent_form(matches, n=5)` → 近 N 场统计
- 实现 PPDA 赛季均值计算（整合进 `AnalysisInput`）
- 数据同步策略：每周一次全量更新写入 SQLite

**产出**：`src/collectors/understat.py`

---

### T8 — Transfermarkt 伤病自动化

#### T8.1 安装与封装
- 安装 `transfermarkt-scraper` PyPI 包
- 实现 `TransfermarktClient.get_injuries(team_id)` → 返回结构化伤病列表
- 维护球队 ID 映射表（FootyStats → Transfermarkt ID）

#### T8.2 伤病严重程度分级
- 实现自动分级逻辑：
  - 核心球员（市场价值 Top 3 且主力位置）→ ±0.3~0.5 xG
  - 重要球员 → ±0.1~0.25 xG
  - 边缘球员 → 忽略

**产出**：`src/collectors/transfermarkt.py` · `config/tm_team_ids.json`

---

### T9 — 定时调度

#### T9.1 数据更新任务
- 配置 `APScheduler` 定时任务：
  - 每天 06:00：更新积分表 + Elo 评分
  - 每天 12:00：更新球队赛季统计
  - 每周一 02:00：Understat 全量同步
  - 比赛日 -4h：更新伤病名单 + 赔率
  - 比赛日 -1h：触发赔率最终快照

**产出**：`scripts/scheduler.py`

---

## Phase 3 · 高级统计

> **预计工期**：3–5 天

---

### T10 — FBref 集成（PPDA 精化）

#### T10.1 soccerdata 集成
- 安装 `soccerdata` 库
- 实现每周批量抓取 PPDA 和 Pressure 数据
- 写入本地 SQLite，带时间戳缓存

#### T10.2 Understat → FBref 切换逻辑
- 优先用 FBref PPDA（更权威）
- FBref 不可用时降级到 Understat
- 联赛覆盖检查（FBref 仅五大联赛）

**产出**：`src/collectors/fbref.py`

---

### T11 — 球员级数据模块

#### T11.1 Understat 球员数据
- 实现 `get_player_stats(player_id)` → NPxG、xA、出场时间
- 集成到第二层：核心球员缺阵时自动计算 xG 调整量（基于 NPxG）

#### T11.2 停赛风险预测
- 从 FootyStats 球员黄牌数计算累积停赛风险
- 在分析输入中标注"停赛风险球员"

**产出**：扩展 `src/collectors/understat.py`

---

## Phase 4 · 回测与校准

> **预计工期**：2–3 周（数据积累后启动）

---

### T12 — 赛后结果归档

#### T12.1 自动结果回填
- 实现 `scripts/update_results.py`：每天从 FootyStats 拉取已结束比赛结果
- 自动匹配历史分析记录，填入 `actual_result` 和 `actual_score`
- 计算 `ev_realized`：`(实际赔率 × 是否命中) - 1`

#### T12.2 预测准确率统计
- 按置信度分桶（60-70、70-80、80-90）统计命中率
- 计算 Brier Score（概率校准评估）
- 计算 ROI（投资回报率）按月/季度

**产出**：`scripts/update_results.py` · `scripts/backtest_report.py`

---

### T13 — 权重校准

#### T13.1 数据驱动权重优化
- 分析各层数据对最终预测准确率的贡献
- 识别哪种比赛类型（A/B/C/D）预测最不可靠
- 生成权重调整建议报告

**产出**：`scripts/calibrate_weights.py`

---

## Phase 5 · 专业级扩展（未来规划）

| 任务 | 描述 | 前置条件 |
|------|------|----------|
| T14 | Betfair Exchange 成交量集成 | 账户认证 + Phase 2 完成 |
| T15 | 亚盘市场分析模块 | The Odds API 亚盘支持 |
| T16 | 多联赛并行分析仪表盘 | Phase 3 完成 |
| T17 | 自动化 Telegram/通知推送 | Phase 2 + 回测验证盈利 |

---

## 依赖关系图

```
T1 (基础设施)
 ├─► T2 (Collectors)
 │    ├─► T2.1 FootyStats
 │    ├─► T2.2 ClubElo
 │    ├─► T2.3 The Odds API
 │    └─► T2.4 Weather
 │
 ├─► T3 (Aggregator)
 │    ├─► T3.1 Schema        [需要 T2 完成]
 │    ├─► T3.2 MatchBuilder  [需要 T2 + T3.1]
 │    └─► T3.3 手动输入      [独立]
 │
 ├─► T4 (Engine)             [需要 T3 完成]
 │    ├─► T4.1 PromptBuilder
 │    ├─► T4.2 Runner
 │    └─► T4.3 Parser
 │
 ├─► T5 (Storage)            [独立，可并行]
 │
 └─► T6 (CLI)                [需要 T3 + T4 + T5]

Phase 2
 T7 Understat               [需要 Phase 1 完成]
 T8 Transfermarkt           [需要 Phase 1 完成]
 T9 Scheduler               [需要 T7 + T8]

Phase 3
 T10 FBref                  [需要 T7]
 T11 球员模块               [需要 T7 + T10]

Phase 4
 T12 结果归档               [需要 3个月以上数据积累]
 T13 权重校准               [需要 T12]
```

---

## 优先级矩阵

| 任务 | 影响力 | 紧迫性 | 优先级 |
|------|--------|--------|--------|
| T1 基础设施 | 高（阻塞一切） | 高 | P0 |
| T2.1 FootyStats | 高（核心数据） | 高 | P0 |
| T2.2 ClubElo | 中 | 高 | P0 |
| T4 分析引擎 | 高（核心功能） | 高 | P0 |
| T3 聚合层 | 高 | 高 | P0 |
| T6 CLI | 中（可用性） | 中 | P1 |
| T5 存储 | 中（回测基础） | 中 | P1 |
| T2.3 Odds API | 中 | 中 | P1 |
| T2.4 Weather | 低 | 低 | P2 |
| T7 Understat | 高（自动化） | 低 | P2 |
| T8 Transfermarkt | 中 | 低 | P2 |
| T9 Scheduler | 中 | 低 | P2 |

---

*Goalcast AI Task Breakdown v1.0*

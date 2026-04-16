# Sportmonks 数据源模块极简重构设计

## 1. 目标与背景

当前 `datasource/sportmonks` 模块存在过度设计：包含复杂的 `store` (本地快照体系)、`transformer` (复杂的归一化转换)、`collector` (分层数据拉取) 等。
根据用户的实际需求，核心 API 只需提供以下两项功能，同时返回更贴近原始数据/易于 Agent 处理的 JSON 结构：
1. **按日期获取比赛列表 (支持联赛过滤)**。
2. **获取单场比赛详情**。

系统必须保留缓存机制，但要求**智能、简单、直接**（本地有且未过期则取本地，否则查 API），无需原先庞大且多余的文件树与元数据文件。

## 2. 架构与文件结构

我们将整个模块收敛，摒弃多余的类，保留 `service.py` 作为核心（或直接作为唯一核心文件）。

**重构后的文件结构（仅保留 3 个文件）：**
- `__init__.py`: 模块导出。
- `service.py`: 核心业务逻辑，包含获取比赛、获取详情及轻量级的缓存逻辑。
- `models.py`: 仅保留 MCP 层面直接需要的最基本结构（如果直接返回精简的原始字典，则可以进一步删减模型，这里我们为了 Agent 的易用性，会提供一个清洗过的、极简的 `dict` 结构，而非繁重的 Dataclass）。

**删除的文件：**
- ❌ `collector.py`
- ❌ `transformer.py`
- ❌ `store.py`
- ❌ `utils.py`

## 3. 核心 API 签名与设计

### 3.1 接口 1: 获取比赛列表
```python
async def get_matches(
    self,
    date: str | None = None,
    leagues: list[str] | None = None,
) -> list[dict[str, Any]]:
```
**实现逻辑**：
1. **缓存键**：`fixtures_{date}.json`
2. **缓存策略**：读取本地缓存。如果有，直接返回并按 `leagues` 过滤。如果没有，调用 `provider.get_fixtures_by_date`。
3. **数据处理**：不再生成厚重的摘要模型，直接将包含 `participants`, `league` 等基础信息的列表返回（清理掉无用的冗余层级）。写回本地缓存文件（有效期 1 小时或仅做当天缓存）。

### 3.2 接口 2: 获取单场比赛详情
```python
async def get_match_for_analysis(
    self,
    fixture_id: int,
    match_date: str | None = None,
) -> dict[str, Any]:
```
**实现逻辑**：
1. **缓存键**：`match_{fixture_id}.json` (如果需要按天分类可放入 `{date}/match_{fixture_id}.json`)
2. **缓存策略**：
   - 检查本地文件 `match_{fixture_id}.json` 的最后修改时间。
   - **智能过期**：例如，如果比赛未开始且缓存超过 12 小时则过期；如果比赛已结束且有缓存则永不过期；或者采用统一的 N 小时过期策略。
3. **数据获取**：
   - 如果缓存失效或不存在，使用 `provider` 的 `get_fixture_by_id` 配合必要的 `include` (如 `lineups,events,statistics,odds`) 以及 `get_standings`、`get_head_to_head` 并发拉取。
4. **返回格式**：不再通过原先厚重的 `SportmonksMatchData` 及数十个字段转换。将 API 返回的几个 JSON 合并为一个扁平、清晰的字典 (包含 `fixture`, `standings`, `h2h`, `odds` 等键)，直接写入缓存并返回给 MCP。这个格式更适合 Agent 阅读和处理。

## 4. 智能且简单的缓存机制设计 (Simple Cache)

不再使用复杂的 `store.py`。在 `service.py` 中引入一个轻量的内部缓存类或函数：
- **存储路径**：`data/cache/sportmonks/` (符合项目核心记忆要求：数据源隔离)。
- **TTL (Time To Live) 控制**：
  - `fixtures_{date}.json`：当天缓存 2 小时，历史日期永不过期。
  - `match_{fixture_id}.json`：距离开赛时间较远（>24h）缓存 12 小时；临近开赛（<24h）缓存 1 小时；已完赛则永不过期。

## 5. 测试文件清理
- 移除：`test_sportmonks_transformer.py`, `test_sportmonks_store.py`, `test_sportmonks_collector.py`
- 重写：`test_sportmonks_service.py`（仅测试 `get_matches` 和 `get_match_for_analysis` 两个方法的缓存与 API 调用逻辑）。

## 6. 实施步骤
1. 删除 `collector.py`, `transformer.py`, `store.py`, `utils.py`。
2. 重写 `service.py` 包含轻量级 `FileCache` 和两个核心 API。
3. 调整 `models.py` 只保留最核心必需的结构（如果完全使用扁平 dict，则甚至可以清空）。
4. 修复 `mcp_server/tools/sportmonks.py` 以适配新的返回格式（确保返回字典，且契约不破坏 Agent 分析）。
5. 重写对应的单元测试。

# Goalcast Sportmonks 独立数据层 Implementation Plan

> **For agentic workers:** 按阶段执行，使用 checkbox (`- [ ]`) 跟踪完成状态。优先保证 `data_strategy/sportmonks` 成为唯一业务入口，其次再暴露 `goalcast_sportmonks_*` MCP 工具。

**Goal:** 建立一条完全独立于 `MatchContext` 的 Sportmonks 数据链路，以 JSON 为主存储，支持 today 入口、批量预热、单场快照读取、局部刷新和缓存状态查看。

**Architecture:** 六个阶段：

- `P0` 明确边界并收敛旧代码
- `P1` 建立 Sportmonks 领域模型与 JSON store
- `P2` 建立 collector / transformer / service 主链路
- `P3` 暴露 `goalcast_sportmonks_*` MCP 工具
- `P4` 兼容旧 `goalcast_sm_*` 并更新 Agent 使用面
- `P5` 补齐测试、文档与验收

**Primary Inputs:**

- 设计稿：[2026-04-15-goalcast-sportmonks-data-layer-design.md](file:///Users/zhengningdai/workspace/skyold/Goalcast/docs/superpowers/specs/2026-04-15-goalcast-sportmonks-data-layer-design.md)
- 现有 MCP 服务：[server.py](file:///Users/zhengningdai/workspace/skyold/Goalcast/mcp_server/server.py)
- 现有 Sportmonks resolver：[sportmonks_resolver.py](file:///Users/zhengningdai/workspace/skyold/Goalcast/data_strategy/resolvers/sportmonks_resolver.py)
- 现有 Sportmonks 目录：[data_strategy/sportmonks](file:///Users/zhengningdai/workspace/skyold/Goalcast/data_strategy/sportmonks)

**Tech Stack:** Python 3.10+, FastMCP, asyncio, pytest, JSON file storage

---

## File Structure Map

**New files:**

```text
data_strategy/sportmonks/service.py
data_strategy/sportmonks/store.py
data_strategy/sportmonks/collector.py
tests/data_strategy/test_sportmonks_store.py
tests/data_strategy/test_sportmonks_service.py
tests/data_strategy/test_sportmonks_mcp_tools.py
docs/superpowers/plans/2026-04-15-goalcast-sportmonks-data-layer.md
```

**Modified:**

```text
data_strategy/sportmonks/__init__.py
data_strategy/sportmonks/models.py
data_strategy/sportmonks/transformer.py
data_strategy/sportmonks/extractor.py
mcp_server/server.py
mcp_server/internal.py
skills/goalcast-daily/SKILL.md              (如存在 sportmonks 路径说明则更新)
docs/Code_Wiki.md                           (如维护工具清单则更新)
```

**Deprecated after migration:**

```text
goalcast_sm_get_fixtures
goalcast_sm_fetch
```

---

## Phase P0: Boundary Lock

### Task 1: 固化 Sportmonks 专用链路边界

**Files:**

- Read: `docs/superpowers/specs/2026-04-15-goalcast-sportmonks-data-layer-design.md`
- Read: `mcp_server/server.py`
- Read: `data_strategy/sportmonks/models.py`

- [ ] **Step 1: 确认以下边界在代码实现前不再变化**

必须保持：

- `goalcast_sportmonks_*` 不输出 `MatchContext`
- `goalcast_sportmonks_get_todays_matches` 与 `goalcast_sportmonks_prefetch_today` 是高层 today 封装
- `goalcast_sportmonks_get_match` 的核心输入是 `fixture_id`
- MCP 不直接调用 provider，不直接操作文件

- [ ] **Step 2: 标注旧路径为兼容态**

在实现开始前，先在以下代码注释中明确兼容关系：

- `goalcast_sm_get_fixtures`
- `goalcast_sm_fetch`

目标：

- 告诉后续维护者：新功能一律进 `goalcast_sportmonks_*`
- 旧前缀只保留迁移用途

**Checkpoint:** 设计边界稳定，后续开发不再在“通用链路还是专用链路”之间摇摆。

---

## Phase P1: Domain Models And Store

### Task 2: 重构 `data_strategy/sportmonks/models.py`

**Files:**

- Modify: `data_strategy/sportmonks/models.py`
- Modify: `data_strategy/sportmonks/__init__.py`
- Create/Modify: `tests/data_strategy/test_sportmonks_models.py`（如已有则扩展）

- [ ] **Step 1: 定义新的专属领域对象**

在 `models.py` 中新增或重构为以下对象：

- `SportmonksFixtureSummary`
- `SportmonksMatchSnapshot`
- `SportmonksWarmupResult`
- `SportmonksCacheStatus`（可选，若用 dataclass 表达状态）

要求：

- 字段命名与设计稿保持一致
- 保留现有 `SportmonksMatchData` 仅作兼容，避免直接删除引发大面积报错
- 每个模型都提供 `to_dict()` 或明确可 JSON 化

- [ ] **Step 2: 给 snapshot 加上状态元数据**

至少包含：

- `available_layers`
- `missing_layers`
- `cache_status`
- `overall_quality`
- `warmed_at`
- `updated_at`
- `expires_at`

- [ ] **Step 3: 为 today / fixtures 列表定义统一最小字段集**

确保 `SportmonksFixtureSummary` 至少覆盖：

- `fixture_id`
- `match_date`
- `kickoff_time`
- `league_name`
- `league_country_id`
- `league_short_code`
- `season_id`
- `home_team_name`
- `away_team_name`
- `cache_status`

- [ ] **Step 4: 写模型测试**

重点验证：

- `to_dict()` 可 JSON 序列化
- `cache_status` 字段存在
- `available_layers` 与 `missing_layers` 可空但结构稳定

**Expected:** 模型层独立可用，不再依赖 `MatchContext`。

---

### Task 3: 新建 `store.py` 并建立 JSON 存储协议

**Files:**

- Create: `data_strategy/sportmonks/store.py`
- Create: `tests/data_strategy/test_sportmonks_store.py`

- [ ] **Step 1: 设计 Store 对外接口**

至少实现：

```python
class SportmonksStore:
    def get_date_dir(self, date: str) -> Path: ...
    def read_fixtures(self, date: str) -> list[dict]: ...
    def write_fixtures(self, date: str, fixtures: list[dict]) -> None: ...
    def find_match_dir(self, fixture_id: int, date: str | None = None) -> Path | None: ...
    def read_match(self, fixture_id: int, date: str | None = None) -> dict | None: ...
    def write_match(self, fixture_id: int, date: str, snapshot: dict) -> None: ...
    def read_meta(self, fixture_id: int, date: str | None = None) -> dict | None: ...
    def write_meta(self, fixture_id: int, date: str, meta: dict) -> None: ...
    def write_raw_layer(self, fixture_id: int, date: str, layer: str, payload: dict) -> None: ...
```

- [ ] **Step 2: 固化路径结构**

必须支持以下布局：

```text
data/cache/sportmonks/{date}/fixtures.json
data/cache/sportmonks/{date}/{home}__{away}__{fixture_id}/match.json
data/cache/sportmonks/{date}/{home}__{away}__{fixture_id}/meta.json
data/cache/sportmonks/{date}/{home}__{away}__{fixture_id}/raw/*.json
```

- [ ] **Step 3: 实现原子写入**

要求：

- `match.json`、`meta.json` 使用临时文件 + rename
- 任一写入失败不破坏已有文件

- [ ] **Step 4: 写 store 测试**

至少覆盖：

- 写 `fixtures.json` 后能读回
- 写 `match.json` / `meta.json` 后能读回
- `find_match_dir()` 能通过 `fixture_id` 找到对应目录
- 连续刷新不会丢掉未更新层

**Expected:** JSON 存储层可独立工作，后续 service 不需要关心文件结构。

---

### Task 3.1: 在索引层保留联赛身份字段

**Files:**

- Modify: `data_strategy/sportmonks/models.py`
- Modify: `data_strategy/sportmonks/store.py`
- Modify: `tests/data_strategy/test_sportmonks_store.py`

- [ ] **Step 1: 将联赛身份字段纳入 fixtures 索引**

必须保留：

- `league_id`
- `league_name`
- `league_country_id`
- `league_short_code`

- [ ] **Step 2: 验证索引往返不丢字段**

重点测试：

- 写入 `fixtures.json` 后再读回
- 联赛身份字段完整保留

**Expected:** 后续联赛过滤不再依赖纯文本名称。

---

## Phase P2: Collector, Transformer, Service

### Task 4: 从现有 resolver 中抽取 collector

**Files:**

- Create: `data_strategy/sportmonks/collector.py`
- Read/Modify: `data_strategy/resolvers/sportmonks_resolver.py`
- Create/Modify: `tests/data_strategy/test_sportmonks_service.py`

- [ ] **Step 1: 抽取 provider 调用逻辑**

将以下逻辑从现有 resolver 中下沉到 `collector.py`：

- fixtures by date
- standings
- odds
- odds movement
- lineups
- h2h
- predictions
- xG（必要时拆成 home / away team 两次调用）

- [ ] **Step 2: 统一 collector 返回 raw layers**

定义 collector 的标准输出：

```python
{
  "fixture": {...},
  "standings": {...} | None,
  "odds": {...} | None,
  "odds_movement": {...} | None,
  "lineups": {...} | None,
  "h2h": {...} | None,
  "predictions": {...} | None,
  "xg_home": {...} | None,
  "xg_away": {...} | None,
}
```

- [ ] **Step 3: 保持 resolver 可复用但不再作为主入口**

做法：

- `SportmonksResolver` 可继续存在
- 新增注释说明：它是旧链路兼容组件，不是 `goalcast_sportmonks_*` 主入口

**Expected:** provider 调用逻辑从 MCP 与服务层中剥离，集中在 collector。

---

### Task 5: 重构 `transformer.py` 为 snapshot 组装器

**Files:**

- Modify: `data_strategy/sportmonks/transformer.py`
- Create/Modify: `tests/data_strategy/test_sportmonks_transformer.py`

- [ ] **Step 1: 以 raw layers 为输入，组装 `SportmonksMatchSnapshot`**

核心函数建议：

```python
def build_match_snapshot(raw_layers: dict, existing_snapshot: dict | None = None) -> SportmonksMatchSnapshot: ...
```

- [ ] **Step 2: 统一层级状态计算**

实现：

- `available_layers`
- `missing_layers`
- `overall_quality`
- `cache_status`

规则建议：

- 关键层齐全且 TTL 有效 -> `fresh`
- 有缺层但主体可分析 -> `partial`
- 有旧数据且过期 -> `stale`
- 无快照 -> `missing`

- [ ] **Step 3: 支持局部刷新合并**

要求：

- 输入新 raw layer + 旧 snapshot
- 仅覆盖对应层
- 不清空未更新层

- [ ] **Step 4: 写 transformer 测试**

至少覆盖：

- 完整 raw layer 生成 `fresh` snapshot
- 缺少 lineups/odds_movement 生成 `partial`
- 用旧 snapshot + 新 raw layer 合并后保留旧层

**Expected:** 转换层从“零散对象转换”升级为“完整快照组装器”。

---

### Task 6: 实现 `service.py`

**Files:**

- Create: `data_strategy/sportmonks/service.py`
- Create: `tests/data_strategy/test_sportmonks_service.py`

- [ ] **Step 1: 定义服务接口**

实现以下方法：

```python
class SportmonksDataService:
    async def get_todays_matches(self, leagues: list[str] | None = None,
                                 warm_if_missing: bool = True) -> list[SportmonksFixtureSummary]: ...
    async def prefetch_today(self, leagues: list[str] | None = None,
                             refresh_stale: bool = False) -> SportmonksWarmupResult: ...
    async def get_fixtures(self, date: str, leagues: list[str] | None = None,
                           warm_if_missing: bool = True) -> list[SportmonksFixtureSummary]: ...
    async def prefetch(self, date: str, leagues: list[str] | None = None,
                       refresh_stale: bool = False) -> SportmonksWarmupResult: ...
    async def get_match(self, fixture_id: int, date: str | None = None,
                        refresh_if_stale: bool = True) -> SportmonksMatchSnapshot: ...
    async def refresh_match(self, fixture_id: int, date: str | None = None,
                            layers: list[str] | None = None) -> SportmonksMatchSnapshot: ...
    async def get_cache_status(self, date: str | None = None,
                               fixture_id: int | None = None) -> dict: ...
```

- [ ] **Step 2: today 方法只做语义封装**

必须保证：

- `get_todays_matches()` 调用 `get_fixtures(date=today, ...)`
- `prefetch_today()` 调用 `prefetch(date=today, ...)`

不得复制一套独立逻辑。

- [ ] **Step 3: 实现批量预热**

`prefetch()` 流程：

1. 用 collector 拉当天 fixtures
2. 按联赛过滤目标比赛
3. 并发拉每场 raw layers
4. 调 transformer 生成 snapshot
5. 调 store 写 `match.json` / `meta.json` / `raw/*.json`
6. 生成 `fixtures.json`

- [ ] **Step 3.1: 实现统一 league matcher**

要求：

- 只能在 `service.py` 实现一套联赛身份匹配逻辑
- 不允许在 MCP 工具或 skill 中做二次联赛文本过滤

规则优先级：

1. 优先 `league.id`（若已知且稳定）
2. 其次 `league.name + country_id`
3. 再次 `league.name + short_code`
4. 仅在身份字段缺失时回退到精确联赛名匹配

首期必须保证：

- `Premier League` 不匹配埃及 `Premier League`
- `Championship` 匹配英格兰 Championship
- `Serie A` 匹配意大利 Serie A

- [ ] **Step 4: 实现单场读取**

`get_match()` 流程：

1. 从 store 读取 `match.json` 和 `meta.json`
2. 判断是否 `fresh` / `partial` / `stale` / `missing`
3. `refresh_if_stale=True` 时执行按需刷新
4. 返回 `SportmonksMatchSnapshot`

- [ ] **Step 5: 实现单场刷新**

`refresh_match()` 要支持：

- 全量刷新
- 指定层刷新，例如 `["lineups", "odds_movement"]`

- [ ] **Step 6: 写 service 测试**

至少覆盖：

- today 方法正确封装日期型方法
- `prefetch()` 生成 fixtures + match + meta
- `get_match()` 命中本地 snapshot
- `get_match()` 在 stale 时触发刷新
- `refresh_match()` 仅更新指定层
- 歧义联赛只保留目标国家/赛事，不混入同名联赛

**Expected:** 业务能力全部集中在 `SportmonksDataService`，MCP 工具只做薄封装。

---

## Phase P3: MCP Tools

### Task 7: 新增 `goalcast_sportmonks_*` 工具族

**Files:**

- Modify: `mcp_server/server.py`
- Optionally Create: `mcp_server/tools/goalcast_sportmonks.py`（如果决定拆文件）
- Create/Modify: `tests/data_strategy/test_sportmonks_mcp_tools.py`

- [ ] **Step 1: 暴露 today 入口**

新增：

- `goalcast_sportmonks_get_todays_matches`
- `goalcast_sportmonks_prefetch_today`

- [ ] **Step 2: 暴露核心数据层工具**

新增：

- `goalcast_sportmonks_get_fixtures`
- `goalcast_sportmonks_prefetch`
- `goalcast_sportmonks_get_match`
- `goalcast_sportmonks_refresh_match`
- `goalcast_sportmonks_get_cache_status`

- [ ] **Step 3: MCP 工具只调用 service**

严格禁止：

- 在 tool 内直接 new `SportmonksProvider`
- 在 tool 内直接读写 `data/cache`
- 在 tool 内直接调用旧 `SportmonksResolver`

- [ ] **Step 4: 统一 MCP 返回格式**

建议：

```python
{
  "ok": True,
  "message": "...",
  "cache_status": "...",
  "data": ...
}
```

根据不同工具返回：

- 列表型工具：`data` 为 fixtures/warmup result
- 单场工具：`data` 为 snapshot
- 状态工具：`data` 为 cache status payload

- [ ] **Step 5: MCP 工具测试**

验证：

- 每个工具都能被注册
- 每个工具都只依赖 service
- today 工具是对 date 工具的封装

**Expected:** 新 MCP 工具族具备清晰边界，面向 Agent 可直接使用。

---

## Phase P4: Backward Compatibility And Agent Surface

### Task 8: 兼容旧 `goalcast_sm_*`

**Files:**

- Modify: `mcp_server/server.py`
- Modify: `mcp_server/internal.py`

- [ ] **Step 1: 保留旧工具但标记 deprecated**

更新 docstring：

- `goalcast_sm_get_fixtures`
- `goalcast_sm_fetch`

说明：

- 新调用应迁移到 `goalcast_sportmonks_*`

- [ ] **Step 2: 旧工具内部转调新 service**

建议映射：

- `goalcast_sm_get_fixtures` -> `SportmonksDataService.get_fixtures(...)`
- `goalcast_sm_fetch` -> `SportmonksDataService.get_match(...)`

注意：

- 返回格式如需兼容旧调用方，可在旧工具内做轻量适配
- 不要反向让新工具依赖旧工具

**Expected:** 新旧链路可并行一段时间，迁移成本可控。

---

### Task 9: 更新 Agent/Skill 调用约定

**Files:**

- Modify: `skills/goalcast-daily/SKILL.md`（若存在对应逻辑）
- Modify: 其他引用 Sportmonks 工作流的 skill 文档
- Modify: `docs/Code_Wiki.md`（如维护工具清单）

- [ ] **Step 1: 更新 today 批量分析流程**

明确写成：

```text
goalcast_sportmonks_prefetch_today
-> goalcast_sportmonks_get_todays_matches
-> 对每场调用 goalcast_sportmonks_get_match
```

- [ ] **Step 2: 明确禁止直连 provider 工具**

对于 Agent/Skill 文档，增加规则：

- 不调用 `sportmonks_get_*`
- 不读取 `data/cache/sportmonks/*`
- 不把 `goalcast_sportmonks_*` 结果强行转成 `MatchContext`

**Expected:** Agent 使用路径和设计稿保持一致。

---

## Phase P5: Tests, Docs, Acceptance

### Task 10: 完整测试矩阵

**Files:**

- `tests/data_strategy/test_sportmonks_models.py`
- `tests/data_strategy/test_sportmonks_store.py`
- `tests/data_strategy/test_sportmonks_transformer.py`
- `tests/data_strategy/test_sportmonks_service.py`
- `tests/data_strategy/test_sportmonks_mcp_tools.py`

- [ ] **Step 1: 模型测试**
- [ ] **Step 2: store 测试**
- [ ] **Step 3: transformer 测试**
- [ ] **Step 4: service 测试**
- [ ] **Step 5: MCP tool 注册与调用测试**

### Task 11: 手工验收场景

- [ ] **Scenario A: today 列表**

调用：

```text
goalcast_sportmonks_get_todays_matches(leagues=["Premier League"])
```

预期：

- 返回英超当天比赛列表
- 每条有 `fixture_id`
- 返回结构稳定

- [ ] **Scenario B: 批量预热**

调用：

```text
goalcast_sportmonks_prefetch_today(
  leagues=["Premier League", "Championship", "Serie A"]
)
```

预期：

- 生成 `fixtures.json`
- 为每场比赛生成 `match.json` / `meta.json`
- 返回 warmup 汇总

- [ ] **Scenario B1: 联赛歧义验证**

调用：

```text
goalcast_sportmonks_prefetch(
  date=<存在同名联赛的日期>,
  leagues=["Premier League", "Championship", "Serie A"]
)
```

预期：

- 英超不会误命中埃及 `Premier League`
- 仅保留目标国家/目标赛事
- `fixtures_found` 与 `fixtures.json` 中的结果一致

- [ ] **Scenario C: 单场命中**

调用：

```text
goalcast_sportmonks_get_match(fixture_id=..., refresh_if_stale=False)
```

预期：

- 命中本地 snapshot
- 返回 `SportmonksMatchSnapshot`

- [ ] **Scenario D: stale 刷新**

人为将某层状态标记为 stale 后再次调用：

```text
goalcast_sportmonks_get_match(fixture_id=..., refresh_if_stale=True)
```

预期：

- 触发局部刷新
- 不丢失旧层

- [ ] **Scenario E: 旧工具兼容**

调用：

```text
goalcast_sm_fetch(...)
```

预期：

- 可继续返回结果
- 内部路径已转向新 service

---

## Suggested Commit Boundaries

建议按以下粒度提交，便于回滚和 code review：

1. `feat(sportmonks): add domain models for snapshot-based data layer`
2. `feat(sportmonks): add json store for fixtures and match snapshots`
3. `feat(sportmonks): add collector and transformer for raw layer assembly`
4. `feat(sportmonks): add SportmonksDataService with prefetch and match refresh`
5. `feat(mcp): add goalcast_sportmonks today and snapshot tools`
6. `refactor(mcp): route legacy goalcast_sm tools through SportmonksDataService`
7. `test(sportmonks): add store service and mcp coverage`
8. `docs(sportmonks): update skill and tool usage docs`

---

## Exit Criteria

当以下条件全部满足时，视为实现完成：

- `data_strategy/sportmonks/service.py` 成为 Sportmonks 数据的唯一业务入口
- `goalcast_sportmonks_get_todays_matches` 和 `goalcast_sportmonks_prefetch_today` 已可用
- `goalcast_sportmonks_get_match` 返回独立的 `SportmonksMatchSnapshot`
- JSON 快照结构稳定，支持预热、命中、刷新和状态查看
- 联赛过滤已具备歧义消解能力，不会把同名异国联赛混入英超/英冠/意甲结果
- `goalcast_sm_*` 已进入兼容态并转调新 service
- Agent 文档已明确新调用路径
- 自动化测试覆盖 store / transformer / service / MCP 工具

---

## Implementation Notes

- 不要把新 today 工具实现为独立逻辑分支；它们必须只是日期型接口的高层封装
- 不要让 `goalcast_sportmonks_get_match` 依赖 `goalcast_resolve_match`
- 不要在新链路里引入 `MatchContext`
- 允许复用现有 `SportmonksResolver` 的采集细节，但不允许保留其“主入口”地位
- 如果实现过程中发现 `transformer.py` 与旧代码差异过大，可以保留旧函数并新增 snapshot builder，避免一次性破坏兼容逻辑
- 不要只按 `league_name` 字符串过滤；歧义联赛必须通过 `country_id / short_code / league_id` 去歧义

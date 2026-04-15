# Goalcast Sportmonks 独立数据层设计文档

**日期**：2026-04-15
**状态**：待评审
**范围**：`data_strategy/sportmonks` 独立化 + `goalcast_sportmonks_*` MCP 工具 + JSON 主存储预热链路

---

## 背景

当前 Goalcast 同时存在两种数据组织方式：

1. `goalcast_*` 主链路通过 `DataFusion` 将多 provider 数据融合为统一的 `MatchContext`，保证分析层与 provider 解耦。[`MatchContext`](file:///Users/zhengningdai/workspace/skyold/Goalcast/data_strategy/models.py)
2. `goalcast_sm_fetch` 为了利用 Sportmonks 独有数据，绕过 `DataFusion`，直接走 `SportmonksResolver` 并返回 `SportmonksMatchData`。[`goalcast_sm_fetch`](file:///Users/zhengningdai/workspace/skyold/Goalcast/mcp_server/server.py#L156-L302)

这两个方向各自有价值，但目前形成了架构脱节：

- `MatchContext` 路径强调统一抽象，适合 provider 可替换
- `goalcast_sm_fetch` 路径强调 Sportmonks 深度数据利用，但没有形成完整数据层
- `data_strategy/sportmonks` 已经存在 extractor / transformer / models 的雏形，但未成为 MCP 主链路入口
- 预热能力存在于 `goalcast_prefetch_today()`，但它依赖旧的 `goalcast_resolve_match` 思路，且并非 Sportmonks 专属数据层的正式能力

实践结论是：Sportmonks 提供了比分、阵容、赔率、赔率变化、预测、xG 等一系列统一 `MatchContext` 不适合完整承载的深度字段。为了最大化利用这些数据，需要建立一条**完全独立于 `MatchContext` 的 Sportmonks 专用数据链路**。

---

## 设计目标

- `data_strategy/sportmonks` 成为 Sportmonks 数据的唯一业务入口
- `goalcast_sportmonks_*` 只暴露数据层能力，不暴露 provider endpoint 细节
- 数据契约完全独立，不再要求适配或回落到 `MatchContext`
- 以 JSON 文件作为主存储，支持预热、命中、刷新、调试
- 以“单场比赛快照”作为核心数据单元，而不是按 API endpoint 零散缓存
- 支持批量预热和单场刷新，保证 MCP 在高频分析时尽量读取本地快照
- 保留 Sportmonks 特有字段，不做为适配统一模型而裁剪

---

## 非目标

- 本次不重构 `goalcast_* -> MatchContext` 主链路
- 本次不改造 FootyStats / Understat 数据层
- 本次不要求将 Sportmonks 新数据层接回分析层通用契约
- 本次不引入 SQLite 作为主存储；如需保留数据库，仅作为未来扩展，不参与首期主流程
- 本次不做“所有 Sportmonks provider endpoint 的一比一 MCP 暴露”

---

## 核心决策

### 1. 完全独立契约

Sportmonks 新链路不再尝试输出 `MatchContext`。其分析输入和 MCP 返回值均基于 Sportmonks 自身领域对象。

### 2. MCP 只暴露数据层能力

MCP 工具命名统一使用 `goalcast_sportmonks_*` 前缀，表达“这是 Goalcast 的 Sportmonks 数据服务”，而不是 provider 原始 API 包装。

### 3. JSON 主存储

缓存与预热的主结果落在 `data/cache/sportmonks/...` 下的 JSON 文件中。JSON 同时承担三种角色：

- MCP 首选读取源
- 预热产物
- 调试与回放依据

### 4. 按比赛聚合快照

缓存的最小可消费单元不是“赔率响应”“阵容响应”，而是一个按 `fixture_id` 聚合的 `match snapshot`。这使得：

- 单场读取逻辑简单
- MCP 返回稳定
- 局部刷新有明确落点
- 调试时可以完整查看某场比赛的状态

### 5. Agent 友好的 Today 入口

Sportmonks 专用链路虽然以 `fixture` 和 `match snapshot` 为核心，但这并不意味着它不能提供“今日比赛”入口。

本设计明确支持：

- `goalcast_sportmonks_get_todays_matches`
- `goalcast_sportmonks_prefetch_today`

这两个工具是面向 Agent 和用户语义的高层入口，本质上分别是对日期型接口的封装：

- `goalcast_sportmonks_get_todays_matches(...)`
  - 语义上等价于 `goalcast_sportmonks_get_fixtures(date=today, ...)`
- `goalcast_sportmonks_prefetch_today(...)`
  - 语义上等价于 `goalcast_sportmonks_prefetch(date=today, ...)`

这样可以同时满足两类需求：

- 数据层内部继续保持以 `fixture` / `snapshot` 为核心
- Agent 对外使用时仍可采用“分析今天哪些比赛”这种自然工作流

### 6. 联赛身份解析必须去歧义

Sportmonks 真实数据验证表明，不能只用联赛名字符串做过滤。典型问题是：

- `"Premier League"` 不只代表英超
- 同名联赛可能来自不同国家
- 如果只按 `league.name == "Premier League"` 过滤，会把埃及 `Premier League` 也误算进“英超”

因此本设计新增一个硬性要求：

- `goalcast_sportmonks_*` 在筛选联赛时，必须使用**联赛身份解析规则**，而不是仅用联赛名文本匹配

联赛身份解析至少要综合以下字段：

- `league.name`
- `league.country_id`
- `league.short_code`
- `league.id`（如果已知且稳定，可作为最高优先级）

对外语义上，`["Premier League", "Championship", "Serie A"]` 代表的是：

- 英格兰 `Premier League`
- 英格兰 `Championship`
- 意大利 `Serie A`

而不是所有同名联赛的并集。

---

## 架构概览

目标链路如下：

```text
goalcast_sportmonks_* MCP tools
  -> data_strategy/sportmonks/service.py
  -> data_strategy/sportmonks/store.py
  -> data_strategy/sportmonks/collector.py
  -> provider/sportmonks/client.py
```

### 分层职责

- `service.py`
  - 对外提供稳定的业务能力
  - 协调“读缓存 / 回源 / 刷新 / 预热”
  - 组装 MCP 直接返回的数据对象

- `store.py`
  - 负责 JSON 文件路径、读写、原子更新、索引维护
  - 不包含 provider 调用逻辑

- `collector.py`
  - 面向 provider 拉取原始数据
  - 并发收集单场所需的各层原始响应
  - 不负责存储格式

- `transformer.py`
  - 将原始响应转换为 Sportmonks 领域对象
  - 计算 `available_layers`、`missing_layers`、`overall_quality` 等派生元数据

- `models.py`
  - 定义 Sportmonks 专属数据契约
  - 所有返回结构只依赖这些模型，不引用 `MatchContext`

- `extractor.py`
  - 调整定位：从“离线提取器”收敛为“缓存文件读取助手”
  - 首期可以保留少量通用读取逻辑，但不再作为主业务入口

---

## 目录规划

建议将 `data_strategy/sportmonks` 收敛为以下结构：

```text
data_strategy/
  sportmonks/
    __init__.py
    models.py          # Sportmonks 专属领域对象
    service.py         # 对外服务入口
    store.py           # JSON 存储与索引
    collector.py       # provider 数据采集
    transformer.py     # raw -> snapshot 转换
    utils.py           # 公共工具函数
    extractor.py       # 可选：兼容旧缓存读取
```

`mcp_server/` 新增或调整为：

```text
mcp_server/
  server.py
  tools/
    goalcast_sportmonks.py
```

其中：

- `server.py` 只负责初始化 `FastMCP` 并注册工具模块
- `goalcast_sportmonks.py` 只负责定义 `goalcast_sportmonks_*` MCP 工具
- 工具函数内部只调用 `data_strategy/sportmonks/service.py`

---

## 数据模型设计

### 1. SportmonksFixtureSummary

用于日期级列表查询，服务于“列赛程”和“批量预热”。

字段建议：

- `fixture_id`
- `date`
- `kickoff_time`
- `league_id`
- `league_name`
- `league_country_id`
- `league_short_code`
- `season_id`
- `home_team_id`
- `home_team_name`
- `away_team_id`
- `away_team_name`
- `cache_status`
- `last_updated_at`

### 2. SportmonksMatchSnapshot

这是新链路的核心契约，用于单场完整读取。

字段分组建议：

- 比赛元信息
  - `fixture_id`
  - `match_date`
  - `kickoff_time`
  - `league`
  - `season_id`
  - `home_team`
  - `away_team`
  - `home_team_id`
  - `away_team_id`

- 数据层内容
  - `xg`
  - `standings`
  - `odds`
  - `asian_handicap`
  - `odds_movement`
  - `lineups`
  - `h2h`
  - `predictions`

- 元数据
  - `available_layers`
  - `missing_layers`
  - `cache_status`
  - `overall_quality`
  - `warmed_at`
  - `updated_at`
  - `expires_at`
  - `source_versions`

### 3. SportmonksWarmupResult

用于批量预热的返回对象。

字段建议：

- `date`
- `leagues`
- `fixtures_found`
- `fixtures_warmed`
- `fixtures_partial`
- `fixtures_failed`
- `output_path`
- `results`

其中 `results` 为每场比赛的简要状态列表。

### 4. 状态字段定义

`cache_status` 统一为以下枚举：

- `fresh`：全部关键层在 TTL 内
- `partial`：有部分层缺失，但可返回可用快照
- `stale`：存在已过期层，但可作为降级数据返回
- `missing`：本地无可用快照
- `error`：最近一次刷新失败，且无有效旧数据

---

## JSON 存储设计

### 1. 路径结构

采用“日期索引 + 比赛目录”的组织方式：

```text
data/cache/
  sportmonks/
    2026-04-15/
      fixtures.json
      Arsenal__Chelsea__123456/
        match.json
        meta.json
        raw/
          fixture.json
          standings.json
          odds.json
          odds_movement.json
          lineups.json
          h2h.json
          predictions.json
          xg_home.json
          xg_away.json
```

### 2. 文件职责

- `fixtures.json`
  - 该日期所有比赛的摘要索引
  - 供 `goalcast_sportmonks_get_fixtures` 快速读取
  - 必须保留联赛身份字段，如 `league_id / league_country_id / league_short_code`

- `match.json`
  - 单场比赛的规范化快照
  - 是 `goalcast_sportmonks_get_match` 的直接读取源

- `meta.json`
  - 记录各层更新时间、TTL、上次错误、刷新策略

- `raw/*.json`
  - 原始 provider 响应
  - 用于调试、回放、验证 transformer

### 3. 目录命名

为避免只用 `fixture_id` 不便人工排查，目录名建议包含可读信息：

```text
{home_team}__{away_team}__{fixture_id}
```

读取时仍以 `fixture_id` 为主键，目录名中的队名仅用于可读性。

### 4. 原子写入要求

`store.py` 需要保证：

- 写入 `match.json` 时使用临时文件 + rename
- 更新 `meta.json` 与 `match.json` 时，顺序固定
- 局部刷新只覆盖对应层，不删除未更新层
- 任意单层失败，不应破坏已有可用快照

---

## 数据获取与刷新策略

### 1. 两类操作

- `prefetch`
  - 目标：提前生成当日或指定日期的比赛快照
  - 场景：批量分析、日常 dispatch、watchlist 预热

- `refresh_match`
  - 目标：强制刷新某场比赛
  - 场景：临场阵容确认、赔率变化、缓存异常修复

### 2. 分层 TTL

不同层的时效性不同，应在 `meta.json` 中单独记录：

- 长 TTL
  - `xg`
  - `standings`
  - `h2h`

- 中 TTL
  - `predictions`

- 短 TTL
  - `odds`
  - `odds_movement`
  - `lineups`

`get_match()` 在读取时按层判断是否过期，必要时只刷新短 TTL 层，而不是重拉整场。

### 3. 局部刷新原则

如果只发现 `lineups` 过期，而 `xg`、`h2h` 仍有效，则：

- 保留旧的 `match.json` 可读内容
- 仅重新采集 `lineups`
- transformer 合并新旧层后写回
- `cache_status` 重新计算

---

## 联赛过滤设计

### 1. 问题背景

真实验证显示：

- `2026-04-14` 这天如果只按联赛名过滤，`"Premier League"` 会命中埃及超级联赛
- 结果会把 `Modern Sport FC vs El Gounah` 等比赛误算为“英超赛程”

这类错误会直接影响：

- today 赛程列表
- `prefetch` 的抓取范围
- Agent 对“英超/英冠/意甲今日比赛”的理解

### 2. 设计要求

所有 Sportmonks 联赛过滤必须走统一的 `league matcher`，不得散落在 MCP 或 skill 中手工判断。

规则优先级建议：

1. 若存在稳定的 `league.id` 白名单，优先按 `league.id`
2. 否则按 `league.name + country_id`
3. 若 `country_id` 缺失，再按 `league.name + short_code`
4. 仅在身份字段全部缺失时，才允许回退到精确联赛名匹配

### 3. 首期目标映射

首期至少保证以下语义成立：

- `Premier League` -> 英格兰顶级联赛，不匹配埃及 `Premier League`
- `Championship` -> 英格兰冠军联赛体系中的联赛，不匹配其他国家同名赛事
- `Serie A` -> 意大利顶级联赛

### 4. 职责边界

- `service.py` 负责联赛过滤的唯一实现
- `store.py` 负责保留联赛身份字段
- MCP 和 skill 只传用户意图中的联赛名，不自行处理歧义

### 5. 验证标准

真实 smoke test 中至少要验证一组歧义样本：

- 输入：`["Premier League", "Championship", "Serie A"]`
- 日期：存在埃及 `Premier League` 与英格兰 `Championship` 并存的日期
- 预期：埃及 `Premier League` 被排除，英格兰 `Championship` 被保留

---

## MCP 工具设计

首期只暴露数据层能力，不暴露 provider 原始 endpoint。

同时，MCP 分为两层：

- 核心数据层工具：面向日期和 `fixture_id`，表达稳定的数据服务能力
- Agent 友好工具：面向“today”语义，降低 Agent 使用复杂度

### Agent 友好工具

#### 1. `goalcast_sportmonks_get_todays_matches`

```python
goalcast_sportmonks_get_todays_matches(
    leagues: list[str] | None = None,
    warm_if_missing: bool = True,
) -> dict
```

职责：

- 提供“今天的 Sportmonks 比赛列表”这一高频入口
- 内部调用 `goalcast_sportmonks_get_fixtures(date=today, leagues=..., warm_if_missing=...)`
- 返回值仍为 `SportmonksFixtureSummary` 列表，不引入新的数据契约

设计说明：

- 该工具不是 provider endpoint 映射，而是数据层的 today 语义封装
- 它的存在是为了让 Agent 能直接响应“分析今天英超/英冠/意甲全部比赛”这类自然请求

#### 2. `goalcast_sportmonks_prefetch_today`

```python
goalcast_sportmonks_prefetch_today(
    leagues: list[str] | None = None,
    refresh_stale: bool = False,
) -> dict
```

职责：

- 提供“预热今天的目标联赛比赛数据”这一高频入口
- 内部调用 `goalcast_sportmonks_prefetch(date=today, leagues=..., refresh_stale=...)`
- 返回 `SportmonksWarmupResult`

设计说明：

- 该工具是批量分析场景的推荐起点
- 保持 Agent 侧调用简洁，不要求 Agent 自己传 `today` 字符串

### 核心数据层工具

#### 3. `goalcast_sportmonks_get_fixtures`

```python
goalcast_sportmonks_get_fixtures(
    date: str | None = None,
    leagues: list[str] | None = None,
    warm_if_missing: bool = True,
) -> dict
```

职责：

- 读取指定日期的 `fixtures.json`
- 支持按联赛过滤
- 索引缺失时可触发轻量预热
- 返回 `SportmonksFixtureSummary` 列表

#### 4. `goalcast_sportmonks_prefetch`

```python
goalcast_sportmonks_prefetch(
    date: str | None = None,
    leagues: list[str] | None = None,
    refresh_stale: bool = False,
) -> dict
```

职责：

- 批量预热指定日期和联赛的比赛快照
- 生成 `fixtures.json`、`match.json`、`meta.json` 和 `raw/*.json`
- 返回 `SportmonksWarmupResult`

#### 5. `goalcast_sportmonks_get_match`

```python
goalcast_sportmonks_get_match(
    fixture_id: int,
    date: str | None = None,
    refresh_if_stale: bool = True,
) -> dict
```

职责：

- 优先读取本地 `match.json`
- 在允许的情况下对 stale 或 missing 数据执行回源刷新
- 返回 `SportmonksMatchSnapshot`

#### 6. `goalcast_sportmonks_refresh_match`

```python
goalcast_sportmonks_refresh_match(
    fixture_id: int,
    date: str | None = None,
    layers: list[str] | None = None,
) -> dict
```

职责：

- 强制刷新某场比赛的指定层
- 适用于赔率、阵容等临场变动较快的层

#### 7. `goalcast_sportmonks_get_cache_status`

```python
goalcast_sportmonks_get_cache_status(
    date: str | None = None,
    fixture_id: int | None = None,
) -> dict
```

职责：

- 查看某日缓存总览或某场比赛缓存详情
- 输出是否存在 stale / partial / error 状态

---

## Agent 使用约定

本设计不仅要定义数据层和 MCP，还要明确 Agent 应如何正确消费这组工具。核心原则是：**Agent 只调用 `goalcast_sportmonks_*`，不直接调用 `sportmonks_*` provider 工具，不自行拼装 provider include，也不自行管理缓存文件。**

### 为什么 Sportmonks 流程与通用 Goalcast 流程不同

流程差别的根本原因，不是 Sportmonks 不能“获取今日比赛”，而是两条链路的设计中心不同：

- 通用 Goalcast 链路以 `MatchContext` 为中心
  - 典型流程：`goalcast_get_todays_matches -> goalcast_resolve_match -> 分析`
  - 第一阶段的主要目标是“定位比赛并获取 ID”
  - 第二阶段的主要目标是“构建统一上下文”

- Sportmonks 专用链路以 `match snapshot` 为中心
  - 典型流程：`prefetch -> get_fixtures/get_todays_matches -> get_match -> 分析`
  - 第一阶段的主要目标是“建立可复用的本地快照”
  - 第二阶段的主要目标是“稳定读取并消费深度数据”

换句话说：

- 通用链路是“先统一，再分析”
- Sportmonks 链路是“先快照，再分析”

因此流程差别来自架构目标差别，而不是能力差别。

### Sportmonks 是否能实现 `goalcast_sportmonks_get_todays_matches`

可以，而且本设计明确将其作为 Agent 友好的 today 入口。

原因如下：

- Sportmonks 原生就支持按日期获取 fixtures
- 本设计已经有 `goalcast_sportmonks_get_fixtures(date=...)`
- 因此实现 `goalcast_sportmonks_get_todays_matches()` 只是在数据层上增加 today 语义封装，不需要改变底层模型

也就是说，`goalcast_sportmonks_get_todays_matches` 是**应该有**的，而不是“可有可无”的附加项。

### Agent 可见能力

对 Agent 来说，Sportmonks MCP 提供的是七个工具、五类核心业务能力，而不是 provider API endpoint：

- 列出指定日期、指定联赛的比赛
- 预热指定日期、指定联赛的比赛数据
- 读取单场完整比赛快照
- 强制刷新单场或若干数据层
- 查看缓存健康状态

### Agent 调用原则

- 单场分析优先调用 `goalcast_sportmonks_get_match`
- 批量分析优先调用 `goalcast_sportmonks_prefetch`，再调用 `goalcast_sportmonks_get_fixtures`
- Agent 不应假设缓存一定存在，应通过工具参数让数据层决定是否预热、是否刷新
- Agent 不应直接依赖 `fixture_id` 以外的 provider 内部标识进行调度
- Agent 不应自己从赛程列表推断某层是否新鲜，应使用 `cache_status`、`available_layers`、`missing_layers`
- Agent 不应自己实现“英超/英冠/意甲”的文本过滤，应信任数据层的联赛身份解析

### 推荐调用模式

#### 模式 A：单场按需分析

适用于用户只关心一场比赛：

1. 先调用 `goalcast_sportmonks_get_todays_matches(leagues=[...])` 或 `goalcast_sportmonks_get_fixtures(date, leagues=[...])`
2. 按队名定位目标比赛，拿到 `fixture_id`
3. 调用 `goalcast_sportmonks_get_match(fixture_id, refresh_if_stale=True)`
4. 用返回的 `SportmonksMatchSnapshot` 直接进入分析

#### 模式 B：批量联赛分析

适用于用户请求“分析今天某几个联赛的所有比赛”：

1. 先调用 `goalcast_sportmonks_prefetch_today(leagues=[...])` 或 `goalcast_sportmonks_prefetch(date=today, leagues=[...])`
2. 再调用 `goalcast_sportmonks_get_todays_matches(leagues=[...])` 或 `goalcast_sportmonks_get_fixtures(date=today, leagues=[...])`
3. 遍历返回的 `fixtures`
4. 对每场比赛调用 `goalcast_sportmonks_get_match(fixture_id, refresh_if_stale=False)`
5. 将所有 `SportmonksMatchSnapshot` 送入分析流程

该模式下，批量分析的主要成本集中在预热阶段，后续逐场读取应尽量命中本地 JSON 快照。

### 典型场景：分析今天英超、英冠和意甲的所有比赛

这是 Sportmonks 专用链路最典型的使用方式之一。用户示例：

> 使用 sportmonks 数据分析今天英超，英冠和意甲的所有比赛

对应的 Agent 目标不是直接逐场打 provider，而是先建立当天指定联赛的本地快照，再批量读取。

推荐工作流：

```text
Step 1. 调用 goalcast_sportmonks_prefetch_today(
  leagues=["Premier League", "Championship", "Serie A"]
)

Step 2. 调用 goalcast_sportmonks_get_todays_matches(
  leagues=["Premier League", "Championship", "Serie A"]
)
  -> 返回全部目标比赛摘要 + cache_status

Step 3. 遍历 fixtures，对每场调用
  goalcast_sportmonks_get_match(
    fixture_id=...,
    date=today,
    refresh_if_stale=False
  )

Step 4. 对每个 SportmonksMatchSnapshot 执行分析

Step 5. 聚合输出：
  - 每场结论
  - 联赛汇总
  - 当日全量汇总
```

### 为什么批量场景必须先预热

如果 Agent 在“今日三大联赛全部比赛”场景里逐场直接调用 `get_match()`，会有三个问题：

- 首次读取延迟高，分析结果返回慢
- 同一天内重复请求同类数据，provider 成本高
- 很难控制不同比赛之间的数据新鲜度一致性

因此在批量场景中，`prefetch_today -> get_todays_matches -> get_match` 应视为标准流程，而不是可选优化。

### Agent 输出组织建议

当 Agent 基于 `goalcast_sportmonks_*` 分析多场比赛时，建议输出结构也与 MCP 调用方式一致：

- 先输出“预热结果摘要”
- 再输出“赛程总览”
- 然后逐场输出分析结果
- 最后输出跨联赛汇总结论

这样做的好处是，当部分比赛为 `partial` 或 `stale` 状态时，Agent 可以自然解释数据质量，而不是把缺层视为异常。

### Agent 错误恢复建议

如果批量分析过程中发现某场比赛 `cache_status` 为 `partial` 或 `stale`，Agent 应采用以下策略：

- 首选：继续分析，但在结果中标记数据层缺失
- 次选：对该场调用 `goalcast_sportmonks_refresh_match`
- 最后：若刷新失败，仍返回已有可用层，并明确说明不足

Agent 不应因为某一场比赛的阵容或赔率变动层失败，就中断整批联赛分析。

### Agent 禁止事项

为了保持架构边界清晰，Agent 不应执行以下操作：

- 直接调用 `sportmonks_get_*` provider MCP 工具
- 直接读取 `data/cache/sportmonks/...` 文件路径来替代 MCP
- 直接推断某层 TTL 或手动拼装 layer 刷新策略
- 将 `goalcast_sportmonks_*` 的返回值强行转成 `MatchContext`

这些规则保证 Sportmonks 专用链路可以独立演进，而不被旧的统一抽象重新绑回去。

---

## 服务层接口设计

`data_strategy/sportmonks/service.py` 建议提供以下方法：

```python
class SportmonksDataService:
    async def get_fixtures(self, date: str, leagues: list[str] | None = None,
                           warm_if_missing: bool = True) -> list[SportmonksFixtureSummary]:
        ...

    async def prefetch(self, date: str, leagues: list[str] | None = None,
                       refresh_stale: bool = False) -> SportmonksWarmupResult:
        ...

    async def get_match(self, fixture_id: int, date: str | None = None,
                        refresh_if_stale: bool = True) -> SportmonksMatchSnapshot:
        ...

    async def refresh_match(self, fixture_id: int, date: str | None = None,
                            layers: list[str] | None = None) -> SportmonksMatchSnapshot:
        ...

    async def get_cache_status(self, date: str | None = None,
                               fixture_id: int | None = None) -> dict:
        ...
```

服务层是 MCP 唯一可见的后端接口。MCP 工具不直接实例化 provider，不直接操作文件。

---

## 与现有代码的关系

### 保留

- `goalcast_* -> MatchContext` 主链路继续存在
- `DataFusion`、`MatchContext`、通用分析 skill 暂不修改
- `provider/sportmonks/client.py` 继续作为 Sportmonks API 适配层

### 新增

- `goalcast_sportmonks_*` 新工具族
- `data_strategy/sportmonks/service.py`
- `data_strategy/sportmonks/store.py`
- `data_strategy/sportmonks/collector.py`
- 以 `match snapshot` 为中心的新 JSON 缓存规范

### 弃用

以下命名进入兼容期，后续统一迁移：

- `goalcast_sm_get_fixtures`
- `goalcast_sm_fetch`

兼容期策略：

- 第一阶段：保留旧工具，但文档标记 deprecated
- 第二阶段：旧工具内部转调新 `SportmonksDataService`
- 第三阶段：外部调用迁移完成后删除旧前缀

---

## `goalcast_sportmonks_*` 与现有 `goalcast_*` 对照表

这一节用于明确两套 MCP 的职责边界，避免后续实现中再次出现“同一件事到底该走哪条链路”的混淆。

### 总体定位

| 维度 | `goalcast_*` | `goalcast_sportmonks_*` |
| ---- | ------------ | ------------------------ |
| 设计目标 | 统一 provider，构建通用分析输入 | 最大化利用 Sportmonks 深度数据 |
| 数据契约 | `MatchContext` | `SportmonksMatchSnapshot` |
| 架构中心 | 统一上下文 | 比赛快照 |
| 数据组织 | 按请求构建 | 按 `fixture_id` 聚合并落盘 |
| 适用场景 | 通用分析、跨 provider 对比 | Sportmonks 专项分析、批量联赛分析 |
| 对 provider 的态度 | 尽量屏蔽差异 | 明确保留差异 |

### 工具级对照

| 通用工具 | Sportmonks 工具 | 关系说明 |
| -------- | ---------------- | -------- |
| `goalcast_get_todays_matches` | `goalcast_sportmonks_get_todays_matches` | 两者都解决“今天有哪些比赛”，但前者服务统一链路，后者服务 Sportmonks 专用链路 |
| `goalcast_resolve_match` | `goalcast_sportmonks_get_match` | 前者返回 `MatchContext`，后者返回 Sportmonks 专属比赛快照 |
| `goalcast_prefetch_today` | `goalcast_sportmonks_prefetch_today` | 前者预热统一链路缓存，后者预热 Sportmonks JSON 快照 |
| 无直接对应 | `goalcast_sportmonks_refresh_match` | 这是 Sportmonks 专用数据层特有能力，通用链路没有必要暴露 |
| 无直接对应 | `goalcast_sportmonks_get_cache_status` | 这是 Sportmonks 快照层的可观测性接口，通用链路通常不需要 |

### 调用流程对照

#### 通用 Goalcast 链路

```text
goalcast_get_todays_matches
-> 定位比赛 ID
-> goalcast_resolve_match
-> 生成 MatchContext
-> 通用分析流程
```

特点：

- 核心是构建统一 `MatchContext`
- Agent 看到的是 provider 无关的分析入口
- 更适合横向比较不同 data provider 的分析结果

#### Sportmonks 专用链路

```text
goalcast_sportmonks_prefetch_today
-> goalcast_sportmonks_get_todays_matches
-> 定位 fixture_id
-> goalcast_sportmonks_get_match
-> 读取 SportmonksMatchSnapshot
-> Sportmonks 专项分析流程
```

特点：

- 核心是建立和读取本地快照
- Agent 看到的是 provider-specific 数据服务入口
- 更适合当天多联赛批量分析与深度字段消费

### 为什么两套工具不能简单合并

虽然从用户视角看，两边都有“获取今日比赛”“读取单场比赛”这些动作，但它们背后的设计目标不同：

- `goalcast_*` 的任务是**抽象差异**
- `goalcast_sportmonks_*` 的任务是**保留差异**

如果强行合并，会出现两个问题：

- 为了统一字段，Sportmonks 的专有信息会继续被裁剪
- 为了支持专有字段，通用链路会被 provider 细节重新污染

因此两套工具应并存，但边界必须清晰。

### Agent 选择哪套工具的判断规则

当 Agent 面对一个请求时，按以下规则选择：

- 如果目标是“做通用分析”或“比较不同 provider”，用 `goalcast_*`
- 如果目标是“明确使用 Sportmonks 数据做深度分析”，用 `goalcast_sportmonks_*`
- 如果用户显式提到“使用 Sportmonks 数据分析今天英超/英冠/意甲全部比赛”，优先走 `goalcast_sportmonks_prefetch_today -> goalcast_sportmonks_get_todays_matches -> goalcast_sportmonks_get_match`

### 迁移时的落地含义

这份对照表也意味着后续实现时需要遵守以下约束：

- 不把 `goalcast_sportmonks_get_match` 包装成 `goalcast_resolve_match` 的别名
- 不把 `goalcast_sportmonks_get_todays_matches` 实现成对通用 `goalcast_get_todays_matches(data_provider="sportmonks")` 的简单透传
- 允许两者底层复用部分采集逻辑，但 MCP 边界、返回契约和缓存层必须分开

---

## 迁移计划

### P1. 建立数据层边界

- 新增 `service.py` / `store.py` / `collector.py`
- 将现有 `SportmonksResolver` 中可复用的采集逻辑下沉到 `collector.py`
- 保留 resolver 作为旧链路兼容层

### P2. 建立 JSON 快照存储

- 实现 `fixtures.json` / `match.json` / `meta.json` / `raw/*.json`
- 实现目录查找与 `fixture_id` 定位
- 为局部刷新和状态计算建立元数据结构

### P3. 暴露新 MCP

- 新增 `goalcast_sportmonks_get_todays_matches`
- 新增 `goalcast_sportmonks_prefetch_today`
- 新增 `goalcast_sportmonks_get_fixtures`
- 新增 `goalcast_sportmonks_prefetch`
- 新增 `goalcast_sportmonks_get_match`
- 新增 `goalcast_sportmonks_refresh_match`
- 新增 `goalcast_sportmonks_get_cache_status`

### P4. 兼容与替换

- `goalcast_sm_*` 转调新 service
- 更新文档与调用约定
- 在后续 skill 中逐步改用新前缀

---

## 错误处理

### 原则

- 采集失败优先保留旧快照，而不是返回空数据
- 缺层允许返回 `partial` 结果，不应因为单层失败导致整场失败
- MCP 返回值必须明确说明问题所在

### MCP 返回要求

所有 `goalcast_sportmonks_*` 返回值中建议统一包含：

- `ok`
- `cache_status`
- `message`
- `data`
- `errors`

单层失败时，`errors` 中写明层名和最近错误，例如：

```json
{
  "ok": true,
  "cache_status": "partial",
  "errors": {
    "lineups": "provider timeout",
    "odds_movement": "empty response"
  }
}
```

---

## 测试策略

首期测试应覆盖服务层和存储层，不依赖真实 API。

### 1. `store.py`

- 写入并读取 `fixtures.json`
- 写入并读取 `match.json`
- 原子更新不产生半写文件
- 局部刷新不丢失旧层

### 2. `transformer.py`

- 正常响应可转换为完整 `SportmonksMatchSnapshot`
- 部分层缺失时正确生成 `partial`
- `available_layers` / `missing_layers` / `overall_quality` 计算正确

### 3. `service.py`

- 缓存命中路径
- stale 自动刷新路径
- missing 触发回源路径
- 单层失败保留旧快照路径

### 4. MCP 工具

- 工具仅调用 service，不直接碰 provider
- 返回结构稳定且可 JSON 序列化

---

## 风险与权衡

### 1. 双缓存体系风险

当前已有 `utils/cache.py` 结果缓存。引入新的 Sportmonks JSON 快照后，会出现“短期响应缓存”和“正式数据层缓存”两套体系。

决策：

- `utils/cache.py` 继续用于低层短期响应缓存
- `data_strategy/sportmonks/store.py` 成为 Sportmonks 的正式可读数据层
- 新 MCP 工具只信任后者

### 2. JSON 一致性风险

JSON 主存储易读，但多层独立刷新时更容易出现状态不一致。

缓解方案：

- 强制通过 `store.py` 统一写入
- 使用 `meta.json` 记录层级时间戳与错误状态
- 禁止 MCP 工具直接改写缓存文件

### 3. 范围膨胀风险

若一开始就镜像所有 provider 能力，会把“建立稳定数据层”变成“复制整个 Sportmonks API”。

缓解方案：

- 首期只做五个核心能力，外加两个 today 语义工具
- today 工具必须是对日期型工具的封装，而不是新增一套独立实现
- 一切围绕“列赛程、预热、单场读取、单场刷新、查状态”展开

### 4. 联赛歧义风险

如果只按联赛名字符串过滤，会把同名联赛混在一起，导致：

- “英超”命中埃及 `Premier League`
- Agent 对今天赛程的认知出现系统性偏差
- `prefetch` 预热到错误比赛

缓解方案：

- 在 `fixtures.json` 中保留 `league_country_id / league_short_code`
- 统一通过 `service.py` 中的 `league matcher` 做过滤
- 将“歧义联赛 smoke test”纳入验收

---

## 成功标准

以下结果出现时，视为本设计达成目标：

- `goalcast_sportmonks_*` 构成一条完整独立链路，不依赖 `MatchContext`
- MCP 能够直接读取预热后的 Sportmonks 比赛快照
- 对同一场比赛，绝大多数读取请求命中本地 JSON，而不是每次都调用 provider
- `goalcast_sm_*` 可进入兼容期并逐步废弃
- Sportmonks 特有字段在数据层中完整保留，不再为统一抽象而裁剪

---

## 总结

本设计不再尝试让 Sportmonks 适配统一数据契约，而是承认其数据深度和结构特性，建立一条独立的数据层与 MCP 通路：

- 数据层在 `data_strategy/sportmonks`
- MCP 前缀统一为 `goalcast_sportmonks_*`
- JSON 作为主存储和预热产物
- 单场比赛快照作为核心对象

这条链路与现有 `goalcast_* -> MatchContext` 并存，但职责清晰：

- `goalcast_*` 继续服务统一分析框架
- `goalcast_sportmonks_*` 专门服务 Sportmonks 深度数据场景

这是从“临时旁路”升级为“正式架构层”的一步，也是后续构建 provider-specific analysis pipeline 的基础。

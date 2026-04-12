# Goalcast 架构重构设计文档

**日期**：2026-04-12
**状态**：已审批
**范围**：数据层重组 + Provider 解耦 + 分析请求模型升级

---

## 背景

当前架构存在以下问题：

1. 业务核心逻辑（`data_strategy/`、`models/`）埋在 `mcp_server/` 传输层内部，与 FastMCP 工具注册代码混在一起
2. Skills 直接调用 provider 特定工具（`footystats_get_todays_matches`），违反了数据层抽象
3. 分析模型（v2.5、v3.0）与数据源绑定，无法独立组合
4. `mcp_server/server.py` 达 1112 行，超过维护上限
5. 多 provider 的 ID 空间不互通，跨 provider fallback 会导致 ID 混用

核心认知升级：**分析结果 = 数据源 × 分析模型**，两者是独立维度，应该可以自由组合。

---

## 设计目标

- Skills 层只感知 `goalcast_*` 工具，不出现任何 provider 名称
- 数据源与分析模型作为显式参数，支持任意组合对比
- 项目结构清晰：传输层薄，业务逻辑在根目录
- 新增每日工作流入口，支持单场和批量分析

---

## 第一节：项目结构

### 目录重组

```
Goalcast/
  analytics/              ← 原 mcp_server/models/（数学分析模型）
    __init__.py
    poisson.py            # 泊松 + Dixon-Coles 分布
    ev_calculator.py      # EV / Kelly 计算
    confidence.py         # 置信度校准

  data_strategy/          ← 原 mcp_server/data_strategy/（数据策略层）
    __init__.py
    models.py             # MatchContext 等数据契约类
    quality.py            # 数据质量评估
    fusion.py             # DataFusion：根据 data_provider 选择 resolver
    resolvers/
      __init__.py
      sportmonks_resolver.py   # 只用 Sportmonks + Understat
      footystats_resolver.py   # 只用 FootyStats + Understat

  provider/               （不变）
  utils/                  （不变）
  config/                 （不变）

  mcp_server/
    server.py             ← 仅 FastMCP 初始化 + import 工具模块，~100 行
    tools/                ← 新增，按 provider 拆分工具注册
      footystats.py       # footystats_* 工具，~300 行
      understat.py        # understat_* 工具，~300 行
      sportmonks.py       # sportmonks_* 工具，~300 行
      goalcast.py         # goalcast_* 核心工具，~200 行

  skills/
    goalcast-daily/       ← 新增
    goalcast-compare/     ← 重写
    goalcast-analyzer-v25/ ← 降级为子 agent 模板
    goalcast-analyzer-v30/ ← 降级为子 agent 模板
```

### 命名说明

- `analytics/`：纯数学模型，无 I/O，无 provider 依赖
- `data_strategy/models.py`：数据契约类（`MatchContext`、`XGStats` 等），与 `analytics/` 的数学模型是两回事

### 迁移影响

`mcp_server/server.py` 和所有 `scripts/` 中的 import 路径需要更新：

```python
# 旧
from mcp_server.models.poisson import poisson_distribution
from mcp_server.data_strategy.fusion import DataFusion

# 新
from analytics.poisson import poisson_distribution
from data_strategy.fusion import DataFusion
```

---

## 第二节：MCP 工具层

### 核心原则

Skills 只调用 `goalcast_*` 工具，不直接调用 `footystats_*`、`sportmonks_*`、`understat_*`。

### 新增工具：`goalcast_get_todays_matches`

```python
goalcast_get_todays_matches(
    data_provider: str,          # "sportmonks" | "footystats"，必填
    date: str = None,            # YYYY-MM-DD，默认今天
    league_filter: str = None,   # 联赛名过滤，如 "Premier League"
) -> List[MatchSummary]
```

返回标准化 `MatchSummary`，字段与 provider 无关：

```json
{
  "home_team": "Arsenal",
  "away_team": "Chelsea",
  "competition": "Premier League",
  "kickoff_time": "2026-04-12T15:00:00Z",
  "match_id": "...",
  "home_team_id": "...",
  "away_team_id": "...",
  "season_id": "..."
}
```

其中 `match_id`、`home_team_id`、`away_team_id`、`season_id` 均为指定 `data_provider` 的内部 ID，不跨 provider 混用。

**内部实现（无跨 provider fallback）**：

```
data_provider="sportmonks" → sportmonks_get_fixtures_by_date(...)
data_provider="footystats" → footystats_get_todays_matches(...)
```

任一 provider 失败时返回明确错误，不静默降级到另一个 provider。

### 修改工具：`goalcast_resolve_match`

新增必填参数：

```python
goalcast_resolve_match(
    ...,
    data_provider: str,   # "sportmonks" | "footystats"，必填
)
```

### 多 provider 对比时的 ID 问题

当 `goalcast-compare` 同时运行多个不同 data_provider 的子 agent 时，各子 agent 需要各自 provider 的 ID。

**解法**：`goalcast-daily` 只向子 agent 传递队名 + 联赛 + 日期，不传 ID。子 agent 自行调用 `goalcast_get_todays_matches` 获取本 provider 的 ID：

```
子 agent 收到：
  home_team: "Arsenal"
  away_team: "Chelsea"
  competition: "Premier League"
  date: "2026-04-12"
  data_provider: "sportmonks"   ← 各子 agent 独立
  model: "v3.0"
  match_type: "A"               ← 由调用方预设

子 agent Step 1：
  goalcast_get_todays_matches(data_provider="sportmonks", date=..., league_filter=...)
  → 文件缓存命中（TTL 2h，goalcast-daily 已预热）
  → 按队名模糊匹配，获取 Sportmonks fixture_id / team_id
```

文件缓存（`data/cache/`）跨进程共享，`goalcast-daily` 的首次调用预热缓存，子 agent 的再次调用为缓存命中，API 成本接近零。

### 不变工具

`goalcast_calculate_poisson`、`goalcast_calculate_ev`、`goalcast_calculate_kelly`、`goalcast_calculate_risk_adjusted_ev`、`goalcast_calculate_confidence` 均为纯数学工具，无 provider 概念，不需修改。

---

## 第三节：分析请求模型

### 核心概念

```
Analysis = DataProvider × AnalyticsModel

DataProvider:    "sportmonks" | "footystats"
AnalyticsModel:  "v2.5" | "v3.0"

有效组合示例：
  sportmonks + v3.0
  footystats + v3.0
  sportmonks + v2.5
  footystats + v2.5
```

### goalcast-compare（重写为统一调度器）

**职责**：接收比赛信息 + 组合列表，并行调度子 agent，输出对比报告。

**触发方式：**

```
单组合：
  "用 sportmonks+v3.0 分析今天英超比赛"
  → 组合列表只有一个，直接输出分析结果，无对比表

多组合：
  "分别用 sportmonks+v3.0 和 footystats+v3.0 分析今天比赛"
  "用两个数据源和 v3.0 模型对比分析"
  → 并行调度，输出对比报告
```

**执行流程：**

```
Step 1：解析请求
  - 比赛信息：队名 / 联赛 / 日期（不含 provider ID）
  - 组合列表：[(data_provider, model), ...]
  - match_type：A/B/C/D，未指定默认 A

Step 2：批量规模检查
  总子 agent 数 = 比赛场数 × 组合数
  超过 10 个时：展示规模并请求用户确认
  例：5 场 × 2 组合 = 10 个子 agent，提示确认

Step 3：并行启动所有子 agent
  每个子 agent 收到：
    home_team, away_team, competition, date
    data_provider, model
    match_type（默认 A）

  子 agent 执行流程（固定，不发出交互问题）：
    1. goalcast_get_todays_matches(data_provider=X) → 定位比赛，获取 ID
    2. goalcast_resolve_match(..., data_provider=X) → 获取 MatchContext
    3. 执行指定模型（v2.5 五层 / v3.0 八层）
    4. 返回 AnalysisResult JSON

Step 4：收集结果，按模式输出
  单组合单场：直接输出分析结果
  多组合单场：输出组合对比表 + 各组合完整结果
  单组合批量：每场一个卡片，统一格式
  多组合批量：每场展示组合对比，末尾输出全场汇总
```

**子 agent 静默模式规则：**

- 子 agent 收到 `match_type` 参数时，零层数据检查跳过交互询问，直接使用该值
- 未收到时默认 `match_type=A`
- 子 agent 全程不发出任何交互性问题，只返回 `AnalysisResult` JSON

**多组合对比报告格式：**

```markdown
## Arsenal vs Chelsea — 多方案分析对比
日期：2026-04-12 | 联赛：Premier League | 比赛类型：A

### 结论对比

| 维度 | sportmonks+v3.0 | footystats+v3.0 | 差异 |
|------|----------------|----------------|------|
| 数据质量 | 0.82 | 0.74 | — |
| 已启用分析层 | L3完整+L6阵容 | L2近况 | — |
| 主队胜率 | 52% | 49% | ±3% |
| 平局概率 | 25% | 27% | ±2% |
| 客队胜率 | 23% | 24% | ±1% |
| 最佳投注 | 主胜 | 主胜 | ✓一致 |
| EV（风险调整后）| +0.09 | +0.06 | ±0.03 |
| 置信度 | 73 | 67 | ±6 |

### 各方案完整结果
[各方案 AnalysisResult JSON]
```

---

## 第四节：Resolver 重新设计

### 双 Resolver 架构

```python
class DataFusion:
    def __init__(self, data_provider: str, footystats, understat, sportmonks=None):
        if data_provider == "sportmonks":
            self._resolver = SportmonksResolver(sportmonks=sportmonks, understat=understat)
        else:
            self._resolver = FootyStatsResolver(footystats=footystats, understat=understat)
```

### 各 Resolver 数据覆盖

| 数据类型 | SportmonksResolver | FootyStatsResolver |
|----------|-------------------|-------------------|
| xG | Sportmonks xG → Understat → league_avg | Understat → FootyStats proxy → league_avg |
| 近况（Form）| **缺失**（进入 data_gaps）| FootyStats last_x_stats ✅ |
| 赔率 | Sportmonks prematch_odds ✅ | FootyStats match_details |
| 赔率变动 | Sportmonks odds_movement ✅ | **缺失** |
| 积分榜 | Sportmonks standings ✅ | FootyStats league_tables |
| 阵容 | Sportmonks lineups ✅ | **缺失** |
| H2H | Sportmonks head_to_head ✅ | **缺失** |

**原则**：各 resolver 在自己 provider 内部可以有数据类型级别的 fallback（如 Sportmonks xG 失败 → Understat），但不得跨 resolver。`data_gaps` 显式记录缺失项。

### 各 Provider 对分析层的影响

| 分析层 | Sportmonks provider | FootyStats provider |
|--------|--------------------|--------------------|
| L1 基础实力（xG）| Sportmonks xG 或 Understat ✅ | Understat 或 proxy ✅ |
| L2 情境调整（近况）| **无近况数据，调整退化** | FootyStats form ✅ |
| L3 市场行为（赔率）| 赔率 + 赔率变动，**权重恢复 20%** ✅ | 仅静态赔率，权重维持 8% |
| L4 节奏/PPDA | 两者均无，跳过 | 两者均无，跳过 |
| L5 分布模型 | 纯数学，不受影响 ✅ | 纯数学，不受影响 ✅ |
| L6 贝叶斯（阵容）| **阵容可用，真正执行** ✅ | 永远跳过 |
| L7 EV/Kelly | 纯数学，不受影响 ✅ | 纯数学，不受影响 ✅ |
| L8 置信度 | 阵容+赔率变动加分，近况缺失扣分 | 近况加分，无阵容/赔率变动 |

两种 provider 各有侧重，跨 provider 对比有实际意义。

### MatchContext 新增字段

```python
@dataclass(frozen=True)
class MatchContext:
    # 新增
    data_provider: str                       # "sportmonks" | "footystats"

    # 新增：Sportmonks 独有
    lineups: Optional[MatchLineups]
    odds_movement: Optional[OddsMovement]
    head_to_head: Optional[tuple[H2HEntry, ...]]

    # 原有字段不变
    # form 在 sportmonks provider 下为 None，data_gaps 包含 "form"
    # lineups 在 footystats provider 下为 None，data_gaps 包含 "lineups"
    ...
```

### 新增值对象

```python
@dataclass(frozen=True)
class MatchLineups:
    home_formation: Optional[str]    # "4-3-3"
    away_formation: Optional[str]
    home_confirmed: bool             # 是否已确认首发
    away_confirmed: bool

@dataclass(frozen=True)
class OddsMovement:
    home_open: float                 # 开盘赔率
    home_current: float
    draw_open: float
    draw_current: float
    away_open: float
    away_current: float
    movement_hours: int              # 变动时间跨度（小时）

@dataclass(frozen=True)
class H2HEntry:
    date: str
    home_team: str
    away_team: str
    home_goals: int
    away_goals: int
```

---

## 第五节：Skills 层

### goalcast-daily（新增）

每日工作流入口，用户与系统交互的最高层。

```
Step 1：解析分析组合
  从用户输入提取：
  - data_provider：sportmonks / footystats
  - model：v2.5 / v3.0
  - league_filter：如 "Premier League"

  未指定时询问（一次一个问题）：
  - 数据源？sportmonks / footystats
  - 模型？v2.5 / v3.0 / 两者都要

Step 2：获取今日赛程
  调用 goalcast_get_todays_matches(
      data_provider=组合列表第一个 provider,
      date=今天,
      league_filter=用户指定
  )

  展示赛程：
    1. Arsenal vs Chelsea        20:00
    2. Liverpool vs Man City     17:30
    3. ...

Step 3：用户选场
  单场："分析第 2 场"
  批量："分析所有比赛" / "分析前 3 场"

  批量规模检查：
  - 总子 agent 数 = 场数 × 组合数
  - 超过 10 时展示规模，请求确认

Step 4：转交 goalcast-compare
  传入：
  - matches: [{home_team, away_team, competition, date}, ...]
  - combinations: [(data_provider, model), ...]
  - match_type: A（默认）
```

### goalcast-compare（重写）

见第三节完整描述。核心变化：

- 不再硬编码"v2.5 vs v3.0"
- 接受任意 `(data_provider, model)` 组合列表
- 成为系统的统一分析入口

### goalcast-analyzer-v25 / v30（降级为子 agent 模板）

不再对外暴露，只由 `goalcast-compare` 调度。需修改两处：

1. Step 1 改为调用 `goalcast_get_todays_matches(data_provider=X, ...)`，不再直接调用 `footystats_get_todays_matches`
2. Step 2 的 `goalcast_resolve_match` 增加 `data_provider=X` 参数

所有分析逻辑（五层/八层）完全保留，不感知 provider 细节。

---

## 附录：遗留的已知问题（本次不修复）

以下问题在初始 review 中发现，但不在本次重构范围内：

| 问题 | 文件 | 说明 |
|------|------|------|
| `top_scores` 概率未归一化 | `analytics/poisson.py` | score_probs 与胜/平/负百分比轻微不一致 |
| `calculate_confidence_v25` 减法补丁 | `analytics/confidence.py` | 应改为 `market_agrees_bonus` 参数 |
| `httpx.AsyncClient` 未关闭 | `provider/base.py` | 需添加 shutdown 钩子 |
| 数学模型无单元测试 | `analytics/` | 需补充 pytest 测试套件 |

---

## 实施优先级

| 阶段 | 内容 |
|------|------|
| P0 | 目录重组（`analytics/`、`data_strategy/resolvers/`），更新 import 路径 |
| P1 | 双 resolver 实现（SportmonksResolver + FootyStatsResolver） |
| P1 | `goalcast_get_todays_matches` 新工具，`goalcast_resolve_match` 加 `data_provider` 参数 |
| P2 | MatchContext 新字段（lineups、odds_movement、H2H） |
| P2 | `goalcast-compare` 重写，`goalcast-analyzer-v25/v30` 子 agent 静默模式 |
| P3 | `goalcast-daily` 新 skill |
| P3 | `mcp_server/server.py` 拆分为 `tools/` 子模块 |

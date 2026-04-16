---
name: goalcast-analysis-orchestrator
description: Use this skill as the unified analysis entrypoint. It routes by user-specified data source/model or defaults to v4.0 + Sportmonks, then dispatches match analysis skills in batch.
---

# Goalcast Analysis Orchestrator — 统一分析入口与编排器

版本：3.0 | 职责：解析请求 → 路由数据源/模型 → 拉赛程 → 调度分析 skill → 汇总输出

## 设计原则

1. **本 skill 不做具体分析计算**（不做泊松、EV、置信度计算）。
2. **默认路径固定为 `v4.0 + sportmonks`**。
3. **用户显式指定优先于默认**（尤其是 `data_source`）。
4. **入口层只负责编排和调度**，分析细节由 analyzer skills 执行。
5. **统一双模式**：`mode=analyze`（普通分析）与 `mode=compare`（对比分析）。
6. **不修改 MCP 入口函数**：仅在 skill 层做参数映射、结果过滤、格式标准化。

## 路由规则（必须遵守）

### 1) 默认规则
- 未指定 `model_version` 且未指定 `data_source`：
  - 使用 `model_version="v4.0"`
  - 使用 `data_source="sportmonks"`
  - 调度 `goalcast-analyzer-v40`

### 2) 用户覆盖规则
- 用户指定 `data_source` 时，按用户指定执行（覆盖默认数据源）。
- 用户指定 `model_version` 时，按用户指定模型执行（若该模型存在对应 analyzer）。

### 3) 版本与数据源兼容规则
- 推荐映射：
  - `model_version <= v3.0` → `footystats`（调度 `goalcast-analyzer-v30` 或 `goalcast-analyzer-v25`）
  - `model_version >= v4.0` → `sportmonks`（调度 `goalcast-analyzer-v40`）
- 若用户同时指定 `model_version` 与 `data_source` 且不兼容：
  - **以用户指定 `data_source` 为最高优先级**
  - 输出提示：`已按用户指定数据源执行，覆盖默认模型路由`
  - 若无法找到对应 analyzer：明确报错并停止，不自动猜测

## 可用 MCP 工具（当前编排层最小集）

| 工具 | 用途 |
|------|------|
| `goalcast_sportmonks_get_matches` | Sportmonks 链路获取指定日期+联赛赛程 |
| `goalcast_footystats_get_todays_matches` | FootyStats 链路获取指定日期+联赛赛程 |

> 说明：计算类工具（poisson/ev/confidence 等）由 analyzer skills 使用，本 skill 禁止调用。

## 支持联赛名称（中英文映射）

```
"Premier League"   英格兰超级联赛
"Championship"     英格兰冠军联赛
"Serie A"          意大利甲级联赛
"La Liga"          西班牙甲级联赛
"Bundesliga"       德国甲级联赛
"Ligue 1"          法国甲级联赛
```

映射示例：
- 英超 / EPL → "Premier League"
- 英冠 → "Championship"
- 意甲 / 意大利 → "Serie A"
- 西甲 → "La Liga"
- 德甲 → "Bundesliga"
- 法甲 → "Ligue 1"

## 执行步骤

### Step 1：解析请求参数

从用户输入中提取：

| 参数 | 说明 | 默认值 |
|------|------|-------|
| `leagues` | 联赛列表（必须明确） | 无 |
| `date` | 目标日期（YYYY-MM-DD） | 今天 |
| `match_type` | A/B/C/D 比赛类型 | "A" |
| `model_version` | `v2.5 / v3.0 / v4.0` | `v4.0` |
| `data_source` | `footystats / sportmonks` | `sportmonks` |
| `mode` | `analyze / compare` | `analyze` |
| `batch` | 是否无人值守全量分析 | `false` |

无法确定联赛时仅询问一次：
> "请确认要分析的联赛：A) 英超  B) 英冠  C) 意甲  D) 其他"

### Step 2：确定路由目标

按“路由规则”得到最终：
- `resolved_model_version`
- `resolved_data_source`
- `resolved_analyzer_skill`

建议映射表：

| model_version | data_source | analyzer skill |
|--------------|------------|----------------|
| `v2.5` | `footystats` | `goalcast-analyzer-v25` |
| `v3.0` | `footystats` | `goalcast-analyzer-v30` |
| `v4.0` | `sportmonks` | `goalcast-analyzer-v40` |

若映射不存在：明确回复不支持并停止。

### Step 3：按数据源获取赛程

#### 当 `resolved_data_source="sportmonks"`
```
goalcast_sportmonks_get_matches(
    date    = <date>,     # 可省略，省略时默认今天
    leagues = <联赛名列表>
)
```

返回后必须执行二次过滤（防混入）：
- 先按用户目标联赛名过滤 `league_name`（忽略大小写）
- 若 `league_name` 为空，再按 `league_short_code` 白名单过滤
- 对二次过滤后结果再继续分析；过滤后为 0 则按“暂无赛程”处理

#### 当 `resolved_data_source="footystats"`
```
goalcast_footystats_get_todays_matches(
    date         = <date>,                # 如工具不支持可省略
    league_filter= <联赛名或联赛过滤条件>
)
```

展示赛程（按开球时间升序、按联赛分组）。无比赛时回复：
`[日期] [联赛名] 暂无赛程`

展示前标准化：
- `league`：优先 `league_name`，为空时回填 `league_short_code`，仍为空则标记 `"UNKNOWN_LEAGUE"`
- `kickoff_time`：统一转换为 `YYYY-MM-DD HH:mm` 文本格式

### Step 4：确认分析范围

- 用户已明确“全部/所有比赛”或 `batch=true`：直接全量分析。
- 否则询问：
  > "共 N 场，全部分析，还是指定场次？（输入编号如 1,3 或回复'全部'）"

### Step 5：逐场调度 analyzer skill

#### 当 `mode=analyze`

对每场比赛，传入标准参数：
```
fixture_id
home_team, home_team_id
away_team, away_team_id
season_id
league
match_date
kickoff_time
match_type
model_version
data_source
```

调度目标：`resolved_analyzer_skill`。  
执行策略：**顺序执行（不并行）**。  
单场失败：记录 `[比赛名] 分析失败：[原因]` 并继续下一场。

默认路径仿真约束（用于验收）：
- 当用户未指定 `data_source/model_version` 且未要求 compare 时，
  - 强制仅走 `sportmonks + v4.0 + mode=analyze`
  - 不调用 footystats 分支，不触发 compare 分支

#### 当 `mode=compare`

对每场比赛调用 `goalcast-compare`，传入：
```
fixture_id
home_team, home_team_id
away_team, away_team_id
season_id, league
match_date, kickoff_time
match_type
comparison_set  # 可选；未给则由 compare 使用默认对比集
```

执行策略：逐场顺序调用 compare；每场内部组合并行由 compare 控制。

### Step 6：汇总输出

`mode=analyze` 输出批量汇总表，至少包含：
- 比赛
- 联赛
- 实际模型（resolved_model_version）
- 实际数据源（resolved_data_source）
- 最优投注
- EV_adj
- 置信度
- 推荐等级

仅对 `bet_rating != "不推荐"` 的场次展示投注方向与 EV_adj。

`mode=compare` 输出逐场对比摘要 + 全场汇总（推荐差异、EV 差异、置信度差异）。

## 触发条件

以下场景应优先激活本 skill：
- 用户要求“分析今天/某天某联赛全部比赛”
- 用户要求“批量分析”
- 用户要求“按指定数据源分析”（如“用 footystats 跑今天英超”）
- 用户要求“按指定模型分析”（如“用 v3.0 批量分析”）
- 用户要求“同一场/同一批比赛做多模型或多数据源对比”（自动切换 `mode=compare`）

## 兼容与迁移

- 本 skill 为原 `goalcast-daily` 的重命名升级入口。
- 目录已迁移为 `skills/goalcast-analysis-orchestrator/`，后续调用应统一使用新名称。

---
name: goalcast-analyzer-v40
description: Use this skill when the user wants a single-match Goalcast football analysis with the v4.0 nine-layer model, or when goalcast-analysis-orchestrator dispatches a match for analysis.
---

# Goalcast Analyzer v4.0

版本：v4.0 | 框架：九层量化分析模型 + 零层强制检查 + `Mode Router`
数据层：**永久绑定 Sportmonks**（单场数据统一通过 `goalcast_sportmonks_get_match` 获取）
适用：独立调用，或由 `goalcast-analysis-orchestrator`（mode=analyze）按场次调度，或被 `goalcast-compare`（mode=compare）作为 sub-agent 调用

## 触发条件

以下任意情况激活此 skill：
- 用户说"用 v4.0 分析 [比赛]"
- 用户未指定版本的单方法分析（默认使用 v4.0）
- 被 `goalcast-analysis-orchestrator` 在 `mode=analyze` 下按场次调度（接收完整参数，跳过 Step 1）
- 被 `goalcast-compare` 在 `mode=compare` 下作为子分析器调度

## 核心约束（绝对禁止违反）

1. **禁止编造统计数字** - 数据不可得时，必须显式跳过或切模式，不能估算填充未提供的临场字段。
2. **禁止情感化语言** - 禁止"状态火热"/"势如破竹"等表述。
3. **置信度上限 90** - `full_analysis` 最高不超过 90；`early_market` 建议上限 78。
4. **投注建议仅在 EV_adj > 0.05 时输出** - 否则 `bet_rating="不推荐"`。
5. **禁止跳过零层数据检查** - 但零层检查必须先读取 `analysis_mode`，按模式解释字段缺失。
6. **禁止直接调用任何 `sportmonks_get_*` provider 工具** - v4 数据获取统一通过 `goalcast_sportmonks_get_match`。
7. **`early_market` 是标准模式，不是降级模式** - 早盘常缺的 `lineups`、`odds_movement`、`predictions` 不得重复作为异常惩罚项。
8. **输出必须显式说明当前模式与原因** - 必须产出 `analysis_context.analysis_mode`、`mode_trigger`、`user_notice`。

## 可用 MCP 工具（仅以下 8 个，禁止调用其他工具）

| 工具 | 用途 |
|------|------|
| `goalcast_sportmonks_get_matches` | Step 1 赛程定位（唯一列表入口） |
| `goalcast_sportmonks_get_match` | Step 2 数据获取（唯一单场入口） |
| `goalcast_calculate_poisson` | L5 Dixon-Coles 分布 |
| `goalcast_calculate_ah_prob` | Layer AH 亚盘概率 |
| `goalcast_calculate_ev` | L8 EV 计算 |
| `goalcast_calculate_kelly` | L8 Kelly 计算 |
| `goalcast_calculate_risk_adjusted_ev` | L8 风险调整 EV |
| `goalcast_calculate_confidence` | L9 置信度校准 |

## 执行步骤

### Step 1：定位比赛

**被 `goalcast-analysis-orchestrator` 调度时**：直接接收以下参数，跳过 Step 1 所有操作：
```
fixture_id, home_team, home_team_id, away_team, away_team_id,
season_id, league, match_date, kickoff_time, match_type
```

**独立调用时**：
- 今日比赛优先调用 `goalcast_sportmonks_get_matches(leagues=[<联赛名>])`
- 分析非今日比赛时，调用 `goalcast_sportmonks_get_matches(date=<日期>, leagues=[<联赛名>])`
- 按队名模糊匹配提取目标比赛的 `fixture_id / home_team_id / away_team_id / season_id`
- 未找到时：回复"未找到符合条件的比赛"，停止

### Step 2：数据采集（V4.0 唯一数据入口）

调用 `goalcast_sportmonks_get_match`：

```
goalcast_sportmonks_get_match(
    fixture_id = <fixture_id>,
    match_date = <match_date>  # 可选；不确定可省略
)
```

返回 Sportmonks 单场上下文字典，字段读取规则如下：

| 分析层字段 | 路径 |
|-----------|------|
| xG 主队 | `xg.home_xg_for` |
| xG 客队 | `xg.away_xg_for` |
| xG 来源 | `xg.source` |
| 主队积分 | `home_standing.position / points / ...` |
| 客队积分 | `away_standing.position / points / ...` |
| 欧盘赔率 | `odds.home_win / draw / away_win` |
| 亚盘让球线 | `asian_handicap.ah_line` |
| 亚盘赔率 | `asian_handicap.ah_home_odds / ah_away_odds` |
| 赔率时序 | `odds_movement` |
| 阵容 | `lineups` |
| H2H | `h2h.entries` |
| 官方预测 | `predictions.home_win / draw / away_win` |
| 数据质量 | `overall_quality` |
| 缺失列表 | `data_gaps` |

**字段优先级说明**：
- `xg.source = "sportmonks_direct"`：最佳 xG 来源
- `asian_handicap` 非空：允许启用 Layer AH
- `odds_movement` 非空：允许完整模式使用 L3 增强逻辑
- `predictions` 非空：允许完整模式使用 L7 校准逻辑
- `lineups` 非空：允许完整模式使用 L6 贝叶斯更新

**子 agent 静默规则**：收到 `match_type` 参数时，零层检查直接采用该值，不询问用户。

### Step 2.5：Mode Router（必须在零层之前执行）

先基于时间窗口与关键字段判断当前比赛应运行的分析模式。

#### Route A：时间优先

- 计算 `hours_to_kickoff = kickoff_time - now`
- 当 `hours_to_kickoff > 6` 时：直接进入 `early_market`
- 当 `hours_to_kickoff <= 6` 时：才允许尝试 `full_analysis`
- 当 `kickoff_time` 缺失或无法解析时：默认进入 `early_market`，并记录 `mode_trigger="missing_kickoff_time"`

#### Route B：完整模式资格检查

只有在 `hours_to_kickoff <= 6` 且以下条件同时满足时，才进入 `full_analysis`：

- `ctx.xg` 可用
- `ctx.odds` 可用且值 > 0
- `ctx.lineups` 可用
- 以下增强信号至少一项可用：
  - `ctx.odds_movement`
  - `ctx.predictions`
  - `ctx.asian_handicap`

#### Route C：早盘模式触发条件

任一条件成立即进入 `early_market`：

- `hours_to_kickoff > 6`
- `kickoff_time` 缺失或不可解析
- `ctx.xg` 缺失
- `ctx.odds` 缺失
- `ctx.lineups` 缺失
- `ctx.odds_movement`、`ctx.predictions`、`ctx.asian_handicap` 全部缺失

#### Mode Router 输出

在正式分析前构造：

```json
{
  "analysis_mode": "full_analysis | early_market",
  "mode_trigger": "kickoff_gt_6h | missing_kickoff_time | missing_xg | missing_odds | missing_lineups | missing_all_enhancement_signals | hybrid",
  "hours_to_kickoff": 0.0,
  "full_analysis_eligible": true,
  "missing_for_full": [],
  "mode_switch_log": []
}
```

说明：
- `missing_for_full` 只记录“为什么未进入完整模式”的字段，不表示数据异常
- `early_market` 是标准分析路径，不得在后续层中再次把这些预期缺失字段当作默认惩罚项

### 零层：赛前强制检查（必须首先执行，不得跳过）

**比赛类型分类：**
- **A**：联赛常规轮次（默认）
- **B**：杯赛单场淘汰赛（进球方差 +15%）
- **C**：双回合次回合（需用户提供首回合比分）
- **D**：关键积分场次（积分差 ≤3 分且赛季后半段）

询问用户或从上下文判断，确认比赛类型。收到 `match_type` 参数时直接采用，不询问用户。

#### `full_analysis` 检查表

| 数据项 | 检查方式 | 目标状态 | 处理规则 |
|--------|----------|----------|----------|
| xG 数据 | `ctx.xg` 非空 | 必须可用 | 不可用则不得进入完整模式 |
| 赔率 | `ctx.odds` 非空且值 > 0 | 必须可用 | 不可用则不得进入完整模式 |
| 阵容/首发 | `ctx.lineups` 非空 | 必须可用 | 不可用则不得进入完整模式 |
| 赔率变动时序 | `ctx.odds_movement` 非空 | 增强信号 | 可与 `predictions` / `asian_handicap` 互补 |
| 官方预测 | `ctx.predictions` 非空 | 增强信号 | 可与 `odds_movement` / `asian_handicap` 互补 |
| 亚盘 | `ctx.asian_handicap` 非空 | 增强信号 | 可与 `odds_movement` / `predictions` 互补 |
| 积分榜 | `ctx.home_standing` / `ctx.away_standing` 非空 | 推荐可用 | 不可用则 L2 跳过相关动力项 |
| PPDA 数据 | 预期缺失 | 缺失 | L4 保持关闭 |

#### `early_market` 检查表

| 数据项 | 检查方式 | 目标状态 | 处理规则 |
|--------|----------|----------|----------|
| xG 数据 | `ctx.xg` 非空 | 核心字段 | 缺失时允许继续，但必须标记为低质量路径 |
| 赔率 | `ctx.odds` 非空且值 > 0 | 核心字段 | 缺失时跳过 EV 与市场层 |
| 积分榜 | `ctx.home_standing` / `ctx.away_standing` 非空 | 推荐可用 | 用于 L2 情境调整 |
| 阵容/首发 | `ctx.lineups` 非空 | 预期缺失 | 不作为默认惩罚项 |
| 赔率变动时序 | `ctx.odds_movement` 非空 | 预期缺失 | 无则仅保留静态市场参考 |
| 官方预测 | `ctx.predictions` 非空 | 预期缺失 | 无则 L7 默认关闭 |
| 亚盘 | `ctx.asian_handicap` 非空 | 可选 | 有则计算，无则输出 `unavailable` |
| PPDA 数据 | 预期缺失 | 缺失 | L4 关闭 |

**数据质量确定**：
- `ctx.overall_quality >= 0.8` → `data_quality=high`
- `0.5 <= ctx.overall_quality < 0.8` → `data_quality=medium`
- `ctx.overall_quality < 0.5` → `data_quality=low`

**缺失数据处理**：
- 直接使用 `ctx.data_gaps` 作为 `missing_data`
- `missing_data` 用于客观报告，不得替代 `analysis_context.missing_for_full`

### 第一层：基础实力模型（权重 35%）

使用 `ctx.xg` 作为基础引擎：

```
base_xg_home = ctx.xg.home_xg_for
base_xg_away = ctx.xg.away_xg_for
xg_source = ctx.xg.source
```

**xG 数据优先级**：
1. `sportmonks_direct`
2. `understat_direct`
3. `footystats_proxy`
4. `league_avg`

主场优势修正（联赛参数表）：

| 联赛 | 主场 xG 修正 | 场均进球基准 |
|------|-------------|-------------|
| England Premier League | +0.25 | 2.75 |
| La Liga / Spanish | +0.22 | 2.65 |
| Serie A / Italian | +0.20 | 2.55 |
| Bundesliga / German | +0.28 | 3.05 |
| Ligue 1 / French | +0.26 | 2.60 |
| Champions League | +0.18 | 2.50 |
| 其他联赛 | +0.20 | 2.60 |

```
base_xg_home = xg_proxy_home + 主场修正值
base_xg_away = xg_proxy_away
```

比赛类型 B（杯赛）：`base_xg × 0.9`

若 `ctx.xg` 不可用：
- 允许继续分析，但必须改用联赛均值路径
- `analysis_context.mode_trigger` 应包含缺 xG 原因
- 置信度在 L9 中走低质量逻辑

### 第二层：情境调整模型（权重 20%）

所有调整必须量化为 xG 数值，禁止叙述性描述。

可用因素：
- 比赛类型 D：动力调整系数 ×1.5
- 主队积分与第 4 名差距 ≤3 分：`+0.15 xG`
- 主队积分与降级区差距 ≤3 分：`+0.15 xG`
- 客队同理

早盘与完整模式共用以下限制：
- 所有调整幅度上限 `±0.2 xG`
- 伤病/停赛、赛程疲劳、旅行/天气等未提供字段统一写为"数据不可用，跳过"

`early_market` 特别说明：
- 阵容缺失不是本层默认扣分项
- 本层只使用稳定可得字段，如 standings、赛季阶段、比赛类型

```
adjusted_xg_home = base_xg_home + L2_adjustment_home
adjusted_xg_away = base_xg_away + L2_adjustment_away
```

### 第三层：市场行为分析

#### `full_analysis`

- 当 `ctx.odds_movement` 可用时，L3 权重可提升至 20%
- 使用静态赔率 + 赔率时序生成市场行为结论
- 若仅剩静态赔率，则允许继续，但 `mode_trigger` 应反映未命中完整信号

#### `early_market`

- L3 仅作为静态市场参考层，实际权重按 8% 处理
- 允许输出静态市场概率，不输出强市场行为结论
- `odds_movement` 缺失是早盘常态，不作为默认惩罚项

赔率概率计算：

```
odds_home = ctx.odds.home_win
odds_draw = ctx.odds.draw
odds_away = ctx.odds.away_win

overround = 1/odds_home + 1/odds_draw + 1/odds_away
P_market_home = (1/odds_home) / overround
P_market_draw = (1/odds_draw) / overround
P_market_away = (1/odds_away) / overround
```

信号规则：
- `|模型概率 - 市场概率| > 0.10` → 强
- `0.05 ~ 0.10` → 中
- `< 0.05` → 弱

如赔率缺失/值为 0：
- 跳过 L3
- `signal_direction="中立"`
- `signal_strength="弱"`

### 第四层：节奏方差模型（权重 5% → 实际 0%）

PPDA 数据不可用，本层继续跳过。

记录：
`"L4 节奏层：跳过（无 PPDA 数据）"`

### 第五层：分布模型（权重 10%）

⚠️ **必须通过 MCP 工具调用 Dixon-Coles 修正泊松分布，禁止 LLM 心算。**

```
goalcast_calculate_poisson(
    home_lambda = adjusted_xg_home,
    away_lambda = adjusted_xg_away,
    max_goals = 6,
    model = "dixon_coles",
    rho = -0.13
)
```

读取：
- `home_win_pct`
- `draw_pct`
- `away_win_pct`
- `top_scores`
- `score_matrix`
- `rho`

### Layer AH：亚盘扩展层（欧盘并列输出）

⚠️ **必须通过 MCP 工具调用，禁止 LLM 心算 AH 概率。**

模式规则：
- `full_analysis`：若 `ctx.asian_handicap` 可用，正常启用；不可用时不影响已选模式，只标记本层缺失
- `early_market`：若 `ctx.asian_handicap` 可用，可直接计算；若缺失，输出 `available=false`

```
goalcast_calculate_ah_prob(
    score_matrix = <L5 返回的 score_matrix>,
    ah_line = ctx.asian_handicap.ah_line
)
```

读取：
- `p_home_cover_pct`
- `p_away_cover_pct`
- `p_push_pct`
- `ah_type`

若有亚盘赔率，再分别调用：

```
goalcast_calculate_ev(model_probability=p_home_cover_pct, market_odds=ctx.asian_handicap.ah_home_odds)
goalcast_calculate_ev(model_probability=p_away_cover_pct, market_odds=ctx.asian_handicap.ah_away_odds)
```

### 第六层：贝叶斯更新（权重 5%）

#### `full_analysis`

- 仅当 `ctx.lineups` 可用时启用
- 用于吸收临场阵容信息

#### `early_market`

- 默认关闭
- `ctx.lineups` 缺失是早盘常态，不得写成"置信度 -10"
- 若阵容意外已提供，可在 `reasoning_summary` 里记为增强信息，但不因此自动切回完整模式

### 第七层：外部预测模型校准

#### `full_analysis`

- 若 `ctx.predictions` 可用，则读取 `home_win / draw / away_win`
- 与 L5 概率比较，任一方向绝对差值 > `0.15` 时：
  - 触发预警 `"Sportmonks 预测分歧过大"`
  - 在 L9 中传入 `prediction_diverged=True`

#### `early_market`

- 默认关闭
- `ctx.predictions` 缺失是早盘常态，不作为默认惩罚项
- 若早盘已存在官方预测，可作为补充说明写入 `reasoning_summary`

### 第八层：EV 与 Kelly 决策（欧盘 + 亚盘并列）

⚠️ **必须通过 MCP 工具调用，禁止 LLM 心算 EV/Kelly。**

#### 欧盘 EV

```
goalcast_calculate_ev(model_probability=模型P(主胜), market_odds=odds_ft_1)
goalcast_calculate_ev(model_probability=模型P(平),   market_odds=odds_ft_x)
goalcast_calculate_ev(model_probability=模型P(客胜), market_odds=odds_ft_2)
```

选取最高 EV 方向后调用 `goalcast_calculate_risk_adjusted_ev`：

#### `full_analysis`

```
goalcast_calculate_risk_adjusted_ev(
    raw_ev = 最高EV,
    lineup_uncertainty = False,
    market_low_confidence = ctx.odds_movement is None,
    data_quality = <根据 ctx.overall_quality 计算>
)
```

#### `early_market`

```
goalcast_calculate_risk_adjusted_ev(
    raw_ev = 最高EV,
    lineup_uncertainty = False,
    market_low_confidence = True,
    data_quality = <根据 ctx.overall_quality 计算>
)
```

说明：
- `early_market` 的保守性来自模式本身与市场低可信度，不来自阵容缺失的重复惩罚
- 若赔率不可用：`EV=0`、`EV_adj=0`、`bet_rating="不推荐"`

#### 综合投注决策规则（欧盘 / 亚盘相同）

- `EV_adj > 0.10` 且 `confidence > 70` → 推荐
- `EV_adj 0.05~0.10` 且 `confidence >= 60` → 小注
- `EV_adj < 0.05` → 不推荐

### 第九层：置信度校准

⚠️ **必须通过 MCP 工具调用，禁止 LLM 心算置信度。**

核心原则：
- `full_analysis` 与 `early_market` 必须按模式内评分
- `early_market` 不得因 `lineups`、`odds_movement`、`predictions` 的预期缺失重复扣分

#### `full_analysis`

```
goalcast_calculate_confidence(
    method="v4.0",
    base_score=70,
    market_agrees=<是否一致>,
    data_complete=ctx.overall_quality >= 0.8,
    understat_available=ctx.xg.source in ("sportmonks_direct", "understat_direct"),
    odds_available=ctx.odds is not None,
    lineup_unavailable=False,
    xG_proxy_used=ctx.xg.source == "footystats_proxy",
    market_disagrees=<市场是否相反>,
    data_quality_low=ctx.overall_quality < 0.5,
    understat_failed=ctx.xg.source != "understat_direct" and ctx.sources.xg == "understat",
    match_type_c=<是否C类比赛>,
    major_uncertainty=<是否有重大不确定>,
    market_downgraded=ctx.odds_movement is None,
    prediction_diverged=<L7 是否触发预警>
)
```

#### `early_market`

```
goalcast_calculate_confidence(
    method="v4.0",
    base_score=64,
    market_agrees=<是否一致>,
    data_complete=ctx.overall_quality >= 0.8,
    understat_available=ctx.xg.source in ("sportmonks_direct", "understat_direct"),
    odds_available=ctx.odds is not None,
    lineup_unavailable=False,
    xG_proxy_used=ctx.xg.source == "footystats_proxy",
    market_disagrees=<市场是否相反>,
    data_quality_low=ctx.overall_quality < 0.5,
    understat_failed=ctx.xg.source != "understat_direct" and ctx.sources.xg == "understat",
    match_type_c=<是否C类比赛>,
    major_uncertainty=<是否有重大不确定>,
    market_downgraded=False,
    prediction_diverged=False
)
```

模式上限：
- `full_analysis`：`confidence <= 90`
- `early_market`：建议控制在 `<= 78`

### Step 5：输出与落盘持久化 (AnalysisResult)

**强制要求**：当本分析器被 Orchestrator 调度或作为批量任务运行时，生成的 JSON 结果**必须被写入本地文件系统**，路径格式为 `team/data/predictions/YYYY-MM-DD_<home>_<away>_v4.0.json`。绝不允许仅仅将 JSON 打印到终端。

```json
{
  "method": "v4.0",
  "analysis_context": {
    "analysis_mode": "full_analysis | early_market",
    "mode_trigger": "kickoff_gt_6h | missing_kickoff_time | missing_xg | missing_odds | missing_lineups | missing_all_enhancement_signals | hybrid",
    "hours_to_kickoff": 0.0,
    "full_analysis_eligible": true,
    "missing_for_full": [],
    "user_notice": "当前使用早盘分析：距离开赛超过 6 小时，且临场增强字段未齐备。",
    "mode_switch_log": ["kickoff_gt_6h -> early_market"]
  },
  "match_info": {
    "home_team": "<ctx.match_info.home_team>",
    "away_team": "<ctx.match_info.away_team>",
    "competition": "<ctx.match_info.league>",
    "match_type": "A|B|C|D",
    "data_quality": "<根据 ctx.overall_quality 确定>",
    "missing_data": "<ctx.data_gaps>",
    "data_source": "sportmonks"
  },
  "probabilities": {
    "home_win": "<X%>",
    "draw": "<X%>",
    "away_win": "<X%>"
  },
  "top_scores": [
    { "score": "X-X", "probability": "<X%>" },
    { "score": "X-X", "probability": "<X%>" },
    { "score": "X-X", "probability": "<X%>" }
  ],
  "market": {
    "market_probabilities": {
      "home_win": "<X%>",
      "draw": "<X%>",
      "away_win": "<X%>"
    },
    "signal_direction": "支持模型 | 反对模型 | 中立",
    "signal_strength": "强 | 中 | 弱"
  },
  "decision": {
    "ev": 0.0,
    "risk_adjusted_ev": 0.0,
    "best_bet": "<主胜 | 平 | 客胜 | 不推荐>",
    "bet_rating": "推荐 | 小注 | 不推荐",
    "confidence": 0
  },
  "asian_handicap": {
    "available": true,
    "ah_line": 0.0,
    "ah_home_odds": 0.0,
    "ah_away_odds": 0.0,
    "ah_type": "half | whole | quarter",
    "p_home_cover_pct": 0.0,
    "p_away_cover_pct": 0.0,
    "p_push_pct": 0.0,
    "ah_ev_home": 0.0,
    "ah_ev_away": 0.0,
    "ah_ev_adj": 0.0,
    "ah_best_side": "主队覆盖 | 客队覆盖 | 不推荐",
    "ah_bet_rating": "推荐 | 小注 | 不推荐"
  },
  "reasoning_summary": "<第一段必须说明当前模式；若为 early_market，必须明确告知用户当前使用早盘分析；其后包含 L4 跳过原因、L6/L7/Layer AH 状态、xG 数据来源、市场信号、欧盘 EV_adj 和亚盘 EV_adj 计算、置信度说明>"
}
```

**`asian_handicap.available = false` 时**：
```json
"asian_handicap": { "available": false, "reason": "Sportmonks 未返回亚盘数据" }
```

**固定文案要求**：
- 若 `analysis_mode="early_market"`：
  - `user_notice` 必须明确说明：当前使用早盘分析
  - `reasoning_summary` 第一段必须包含：`当前使用早盘分析，不将阵容、赔率时序、官方预测缺失视为异常降级项。`
- 若 `analysis_mode="full_analysis"`：
  - `reasoning_summary` 第一段必须包含：`当前使用完整分析，临场增强字段已满足完整模式要求。`

输出前必须自检：
- [ ] `analysis_context.analysis_mode` 存在且为 `full_analysis` 或 `early_market`
- [ ] `analysis_context.mode_trigger` 与 `missing_for_full` 一致
- [ ] 早盘模式下 `analysis_context.user_notice` 必填
- [ ] `home_win% + draw% + away_win% = 100%`（±0.5%）
- [ ] `confidence ∈ [30, 90]`
- [ ] `ev ∈ [-1, +2]`
- [ ] `asian_handicap.p_home_cover_pct + p_away_cover_pct + p_push_pct ≈ 100%`（可用时，±0.5%）
- [ ] `missing_data` 仅客观报告缺失，不替代模式判定
- [ ] `xg_source` 字段存在（`sportmonks_direct`、`understat_direct`、`footystats_proxy` 或 `league_avg`）
- [ ] `reasoning_summary` 提及 L4 跳过原因、L6/L7 状态、Layer AH 状态、xG 数据来源
- [ ] **所有计算（Dixon-Coles 泊松、AH 概率、EV、Kelly、置信度）均通过 MCP 工具调用**

---
name: goalcast-analyzer-v40
description: Use this skill when the user wants a single-match Goalcast football analysis with the v4.0 nine-layer model, or when goalcast-daily dispatches a match for analysis.
---

# Goalcast Analyzer v4.0

版本：v4.0 | 框架：九层量化分析模型 + 零层强制检查
数据层：**永久绑定 Sportmonks**（直连 SportmonksResolver，跳过 DataFusion）
适用：独立调用 或 由 `goalcast-daily` 按场次调度

## 触发条件

以下任意情况激活此 skill：
- 用户说"用 v4.0 分析 [比赛]"
- 用户未指定版本的单方法分析（默认使用 v4.0）
- 被 `goalcast-daily` 按场次调度（接收完整参数，跳过 Step 1）

## 核心约束（绝对禁止违反）

1. **禁止编造统计数字** - 数据不可得时，必须显式降权而非估算填充
2. **禁止情感化语言** - 禁止"状态火热"/"势如破竹"等表述
3. **置信度上限 90** - 禁止输出超过 90 的置信度
4. **投注建议仅在 EV_adj > 0.05 时输出** - 否则 `bet_rating="不推荐"`
5. **禁止跳过零层数据检查**
6. **禁止直接调用任何 sportmonks_get_* 工具** - 数据获取统一通过 `goalcast_sm_fetch`

## 可用 MCP 工具（仅以下 8 个，禁止调用其他工具）

| 工具 | 用途 |
|------|------|
| `goalcast_sm_fetch` | Step 2 数据获取（唯一数据入口） |
| `goalcast_calculate_poisson` | L5 Dixon-Coles 分布 |
| `goalcast_calculate_ah_prob` | Layer AH 亚盘概率 |
| `goalcast_calculate_ev` | L8 EV 计算 |
| `goalcast_calculate_kelly` | L8 Kelly 计算 |
| `goalcast_calculate_risk_adjusted_ev` | L8 风险调整 EV |
| `goalcast_calculate_confidence` | L9 置信度校准 |

## 执行步骤

### Step 1：定位比赛

**被 goalcast-daily 调度时**：直接接收以下参数，跳过 Step 1 所有操作：
```
fixture_id, home_team, home_team_id, away_team, away_team_id,
season_id, league, match_date, kickoff_time, match_type
```

**独立调用时**：
- 优先调用 `goalcast_sportmonks_get_todays_matches(leagues=[<联赛名>])`
- 分析非今日比赛时，调用 `goalcast_sportmonks_get_fixtures(date=<日期>, leagues=[<联赛名>])`
- 按队名模糊匹配提取目标比赛的 `fixture_id / home_team_id / away_team_id / season_id`
- 未找到时：回复"未找到符合条件的比赛"，停止

### Step 2：数据采集（V4.0 唯一数据入口）

优先调用 `goalcast_sportmonks_get_match`：

```
goalcast_sportmonks_get_match(
    fixture_id    = <fixture_id>,
    date          = <match_date>,
    refresh_if_stale = True,
)
```

兼容说明：
- 旧 `goalcast_sm_fetch(...)` 仍可用，并已转调新 Sportmonks 数据层
- 新调用优先使用 `goalcast_sportmonks_get_match(...)`

返回 Sportmonks 数据字典；新旧入口都应满足以下字段读取规则：

| 分析层字段 | SportmonksMatchData 路径 |
|-----------|------------------------|
| xG 主队 | `xg.home_xg_for` |
| xG 客队 | `xg.away_xg_for` |
| xG 来源 | `xg.source`（影响置信度） |
| 主队积分 | `home_standing.position / points / ...` |
| 客队积分 | `away_standing.position / points / ...` |
| 欧盘赔率 | `odds.home_win / draw / away_win` |
| 亚盘让球线 | `asian_handicap.ah_line` |
| 亚盘赔率 | `asian_handicap.ah_home_odds / ah_away_odds` |
| 赔率时序 | `odds_movement`（非 None → L3 权重提升至 20%）|
| 阵容 | `lineups`（非 None → L6 启用）|
| H2H | `h2h.entries` |
| 官方预测 | `predictions.home_win / draw / away_win` |
| 数据质量 | `overall_quality`（→ data_quality 分级）|
| 缺失列表 | `data_gaps`（→ missing_data）|

**V4.0 专有字段优先级说明**：
- `xg.source = "sportmonks_direct"` → 最优先，置信度 +5
- `asian_handicap` 非 null → Layer AH 启用
- `odds_movement` 非 null → L3 权重从 8% 提升至 20%
- `predictions` 非 null → L7 校准层启用
- `lineups` 非 null → L6 贝叶斯更新启用

**子 agent 静默规则**：收到 `match_type` 参数时，零层检查直接采用该值，不询问用户。
- `ctx.odds_movement` → L3 市场行为权重提升至 20%
- `ctx.head_to_head` → 交锋记录参考
- `ctx.predictions` → L7 外部预测模型校准

**子 agent 静默规则**：收到 `match_type` 参数时，零层检查直接采用该值，不询问用户。

### 零层：赛前强制检查（必须首先执行，不得跳过）

**比赛类型分类：**
- **A**：联赛常规轮次（默认）
- **B**：杯赛单场淘汰赛（进球方差 +15%）
- **C**：双回合次回合（需用户提供首回合比分）
- **D**：关键积分场次（积分差 ≤3 分且赛季后半段）

询问用户或从上下文判断，确认比赛类型。

**数据可用性检查表（必须逐项执行）：**

| 数据项 | 检查方式 | 预期状态 | 降级规则 |
|--------|----------|----------|----------|
| xG 数据 | `ctx.xg` 非空 | 可用 | sportmonks → 优先用 `sportmonks_direct`；不可用时降级 understat → league_avg，`data_quality=low` |
| 主队近况 | `ctx.home_form_10` 非空 | 可用 | 不可用 → L1 使用联赛均值，`data_quality=low` |
| 客队近况 | `ctx.away_form_10` 非空 | 可用 | 不可用 → L1 使用联赛均值，`data_quality=low` |
| 赔率 | `ctx.odds` 非空且值 > 0 | 可用 | 不可用 → L3 权重=0%，跳过 |
| 亚盘赔率 | `ctx.asian_handicap` 非空 | 可用/缺失 | 缺失 → Layer AH 跳过，`asian_handicap` 块输出 `"unavailable"` |
| 积分榜 | `ctx.home_standing` 非空 | 可用 | 不可用 → L2 动力因素跳过 |
| 阵容/首发 | `ctx.lineups` 非空（仅 sportmonks）| 可用/缺失 | 缺失 → 置信度 -10；可用（sportmonks）→ L6 启用 |
| PPDA 数据 | **预期缺失** | 缺失 | L4 权重=0%，跳过 |
| 赔率变动时序 | `ctx.odds_movement` 非空（仅 sportmonks）| 可用/缺失 | 缺失 → L3 权重 8%；可用（sportmonks）→ L3 权重 20% |
| 官方预测概率 | `ctx.predictions` 非空（仅 sportmonks）| 可用/缺失 | 缺失 → L7 校准层跳过 |

**数据质量确定**：
- `ctx.overall_quality >= 0.8` → `data_quality=high`
- `0.5 <= ctx.overall_quality < 0.8` → `data_quality=medium`
- `ctx.overall_quality < 0.5` → `data_quality=low`

**缺失数据处理**：
- 直接使用 `ctx.data_gaps` 作为 `missing_data` 列表

### 第一层：基础实力模型（权重 35%）

使用 `MatchContext` 中的 xG 数据：

```
# 从 ctx.xg 获取 xG 数据
base_xg_home = ctx.xg.home_xg_for
base_xg_away = ctx.xg.away_xg_for
xG_source = ctx.xg.source  # "sportmonks_direct" | "understat_direct" | "footystats_proxy" | "league_avg"
```

**数据来源说明**：
- `sportmonks_direct`：使用 Sportmonks 直接 xG 数据（**最优先**，当 data_provider="sportmonks" 时）
- `understat_direct`：使用 Understat 直接 xG 数据（次优先）
- `footystats_proxy`：使用 FootyStats 近况数据计算的 proxy
- `league_avg`：使用联赛均值（最低优先级）

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
base_xg_home = xG_proxy_home + 主场修正值
base_xg_away = xG_proxy_away
```

比赛类型 B（杯赛）：`base_xg × 0.9`（防守倾向更强）。

数据不可用时：使用联赛场均进球基准的 50/50 分配，`data_quality=low`，注明"基于联赛均值估算"。

**xG 数据优先级总结**：
```
1. Sportmonks xG（data_provider="sportmonks"）→ base_xg = Sportmonks xG（最优先，置信度 +5）
2. Understat 直接 xG → base_xg = Understat xG（次优先，置信度 +5）
3. FootyStats xG（如有）→ base_xg = FootyStats xG
4. Proxy 估算 → base_xg = xG_proxy（降级，置信度 -5）
5. 联赛均值 → base_xg = 联赛均值（最低，置信度 -8）
```

**注意**：xG 数据源的选择由 `goalcast_sm_fetch`（SportmonksResolver 层）负责，Skill 不直接调用任何 provider 工具。
Skill 只读取 `xg.source` 来了解数据来源，并据此调整置信度扣分。

### 第二层：情境调整模型（权重 20%）

**所有调整必须量化为 xG 数值，禁止叙述性描述。**

1. **动力因素**（来自 `ctx.home_standing` 和 `ctx.away_standing`）：
   - 比赛类型 D：动力调整系数 ×1.5
   - 主队积分与第 4 名差距 ≤3 分（争欧战）：+0.15 xG
   - 主队积分与降级区差距 ≤3 分（保级压力）：+0.15 xG
   - 客队同理
2. **阵容不确定性**（预期触发）：
   - **硬性约束**：所有调整幅度上限 ±0.2 xG
   - 置信度 -10
3. **无法获取的因素**（明确标注，不估算）：
   - 伤病/停赛：标注"数据不可用，跳过"
   - 赛程疲劳：标注"数据不可用，跳过"
   - 旅行/天气：标注"数据不可用，跳过"

```
adjusted_xg_home = base_xg_home + L2_adjustment_home（受 ±0.2 上限约束）
adjusted_xg_away = base_xg_away + L2_adjustment_away（受 ±0.2 上限约束）
```

### 第三层：市场行为分析（权重 20% → 实际 8%）

**本层权重自动降至 8%，标注"低可信度（仅静态开盘赔率）"。**

使用 `MatchContext` 中的赔率数据：

```
# 从 ctx.odds 获取赔率
odds_home = ctx.odds.home_win
odds_draw = ctx.odds.draw
odds_away = ctx.odds.away_win

超售率 = 1/odds_home + 1/odds_draw + 1/odds_away
P_market_home = (1/odds_home) / 超售率
P_market_draw = (1/odds_draw) / 超售率
P_market_away = (1/odds_away) / 超售率
```

分歧 = 模型概率 - 市场概率（各方向）

信号强度：`|分歧| > 0.10 → 强`；`0.05~0.10 → 中`；`< 0.05 → 弱`

信号方向：模型某方向概率高于市场 > 0.05 → "支持模型"；否则 → "中立"

如赔率缺失/值为 0：跳过，`signal_direction="中立"`，`signal_strength="弱"`。

### 第四层：节奏方差模型（权重 5% → 实际 0%）

**PPDA 数据不可用，本层跳过。**

记录：`"L4 节奏层：跳过（FootyStats 不提供 PPDA 数据）"`

### 第五层：分布模型（权重 10%）

⚠️ **必须通过 MCP 工具调用 Dixon-Coles 修正泊松分布，禁止 LLM 心算。**

调用 `goalcast_calculate_poisson`：
```
goalcast_calculate_poisson(
    home_lambda=adjusted_xg_home,
    away_lambda=adjusted_xg_away,
    max_goals=6,
    model="dixon_coles",
    rho=-0.13
)
```

从返回结果中提取：
- `home_win_pct` → 主胜概率
- `draw_pct` → 平局概率
- `away_win_pct` → 客胜概率
- `top_scores` → 前 5 高概率比分
- `score_matrix` → 完整比分概率矩阵（**Layer AH 复用此矩阵**）
- `rho` → Dixon-Coles 修正系数（确认使用）

### Layer AH：亚盘扩展层（欧盘并列输出）

⚠️ **必须通过 MCP 工具调用，禁止 LLM 心算 AH 概率。**

**前提检查**：
- 检查 `ctx.asian_handicap` 是否存在
- 如缺失：记录 `"Layer AH: 跳过（无 Sportmonks 亚盘数据）"`，跳过本层，`asian_handicap` 块输出 `"unavailable"`
- 如存在：提取 `ah_line`, `ah_home_odds`, `ah_away_odds`, `source`

**调用 `goalcast_calculate_ah_prob`**（使用第五层的 `score_matrix`）：
```
goalcast_calculate_ah_prob(
    score_matrix=<L5 返回的 score_matrix>,
    ah_line=ctx.asian_handicap.ah_line
)
```

从返回结果中提取：
- `p_home_cover_pct` → 主队覆盖亚盘概率（%）
- `p_away_cover_pct` → 客队覆盖亚盘概率（%）
- `p_push_pct` → 退水概率（整球盘时非零）
- `ah_type` → "half" | "whole" | "quarter"

**亚盘 EV 计算**（调用已有的 `goalcast_calculate_ev`）：
```
goalcast_calculate_ev(
    model_probability=p_home_cover_pct,
    market_odds=ctx.asian_handicap.ah_home_odds
)
goalcast_calculate_ev(
    model_probability=p_away_cover_pct,
    market_odds=ctx.asian_handicap.ah_away_odds
)
```

**亚盘投注决策**（与欧盘规则相同）：
- `EV_adj_ah > 0.10` 且 `confidence > 70` → 推荐
- `EV_adj_ah 0.05~0.10` 且 `confidence ≥ 60` → 小注
- `EV_adj_ah < 0.05` → 不推荐

**退水盘注意（整球盘）**：`p_push > 10%` 时，在 `reasoning_summary` 中注明退水风险。

### 第六层：贝叶斯更新（权重 5%）

**阵容数据不可用，本层跳过。**

记录：`"L6 贝叶斯层：跳过（无 FotMob 阵容确认）"`

### 第七层：外部预测模型校准（新增）

**获取 Sportmonks 官方预测数据**：
检查 `ctx.predictions` 是否存在。如存在，提取 `home_win`, `draw`, `away_win`。
与第五层 Dixon-Coles 算出的概率进行对比（计算各方向的绝对差值）。

**预警触发条件**：
- 如果主胜、平局或客胜中任意一个方向的差值 > 15%（即 0.15）：触发预警 `"Sportmonks 预测分歧过大"`。
- 此时在第九层的置信度校准中，传入 `prediction_diverged=True`（自动扣减 10 点置信度），并在 `reasoning_summary` 中明确说明。
如 `ctx.predictions` 不存在，则本层跳过，记录 `"L7 校准层：跳过（无预测数据）"`。

### 第八层：EV 与 Kelly 决策（欧盘 + 亚盘并列）

⚠️ **必须通过 MCP 工具调用，禁止 LLM 心算 EV/Kelly。**

#### 欧盘 EV（原逻辑不变）

对三个方向分别调用 `goalcast_calculate_ev`：
```
goalcast_calculate_ev(model_probability=模型P(主胜), market_odds=odds_ft_1)
goalcast_calculate_ev(model_probability=模型P(平),   market_odds=odds_ft_x)
goalcast_calculate_ev(model_probability=模型P(客胜), market_odds=odds_ft_2)
```

选取最高 EV 方向，调用 `goalcast_calculate_risk_adjusted_ev` 获取风险调整 EV：
```
goalcast_calculate_risk_adjusted_ev(
    raw_ev=最高EV,
    lineup_uncertainty=True,
    market_low_confidence=True,
    data_quality="medium"
)
```

风险调整乘数：× 0.85（阵容）× 0.90（市场低可信度）→ `EV_adj`

#### 亚盘 EV（Layer AH 已计算时执行）

亚盘 EV 已在 Layer AH 步骤中通过 `goalcast_calculate_ev` 计算完成。
此处复用 Layer AH 的结果：

```
ah_ev_home = Layer AH 中 p_home_cover 方向的 EV
ah_ev_away = Layer AH 中 p_away_cover 方向的 EV
```

同样对亚盘最高 EV 方向施加风险调整：
```
goalcast_calculate_risk_adjusted_ev(
    raw_ev=max(ah_ev_home, ah_ev_away),
    lineup_uncertainty=True,
    market_low_confidence=True,
    data_quality=<同欧盘>
)
```
→ `EV_adj_ah`

#### 综合投注决策规则（欧盘 / 亚盘适用相同阈值）：
- `EV_adj > 0.10` 且 `confidence > 70` → 推荐
- `EV_adj 0.05~0.10` 且 `confidence ≥ 60` → 小注
- `EV_adj < 0.05` → 不推荐

如赔率不可用：`EV=0`，`EV_adj=0`，`bet_rating="不推荐"`。

### 第九层：置信度校准

⚠️ **必须通过 MCP 工具调用，禁止 LLM 心算置信度。**

调用 `goalcast_calculate_confidence(method="v4.0", ...)`：
```
goalcast_calculate_confidence(
    method="v4.0",
    base_score=70,
    market_agrees=<是否一致>,
    data_complete=ctx.overall_quality >= 0.8,
    understat_available=ctx.xg.source in ("sportmonks_direct", "understat_direct"),
    odds_available=ctx.odds is not None,
    lineup_unavailable=True,
    xG_proxy_used=ctx.xg.source == "footystats_proxy",
    market_disagrees=<市场是否相反>,
    data_quality_low=ctx.overall_quality < 0.5,
    understat_failed=ctx.xg.source != "understat_direct" and ctx.sources.xg == "understat",
    match_type_c=<是否C类比赛>,
    major_uncertainty=<是否有重大不确定>,
    market_downgraded=True,  # v4.0 固定降级
    prediction_diverged=<L7 是否触发预警>
)
```

从返回结果中取 `confidence` 作为最终值。

### Step 5：输出 `AnalysisResult`

```json
{
  "method": "v4.0",
  "match_info": {
    "home_team": "<ctx.match_info.home_team>",
    "away_team": "<ctx.match_info.away_team>",
    "competition": "<ctx.match_info.league>",
    "match_type": "A|B|C|D",
    "data_quality": "<根据 ctx.overall_quality 确定>",
    "missing_data": "<ctx.data_gaps>"
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
  "reasoning_summary": "<各层关键结论，必须包含：L4 跳过原因、L6 跳过原因、Layer AH 结果或跳过原因、xG 数据来源、市场信号、欧盘 EV_adj 和亚盘 EV_adj 计算、置信度扣分明细>"
}
```

**`asian_handicap.available = false` 时**（ctx.asian_handicap 缺失）：
```json
"asian_handicap": { "available": false, "reason": "Sportmonks 未返回亚盘数据" }
```

输出前必须自检：
- [ ] `home_win% + draw% + away_win% = 100%`（±0.5%）
- [ ] `confidence ∈ [30, 90]`
- [ ] `ev ∈ [-1, +2]`
- [ ] `asian_handicap.p_home_cover_pct + p_away_cover_pct + p_push_pct ≈ 100%`（±0.5%，可用时）
- [ ] `missing_data` 包含 `"lineup"`、`"ppda"`、`"odds_movement"`、`"predictions"`（如确实缺失）
- [ ] `xG_source` 字段存在（`"sportmonks_direct"`、`"understat_direct"`、`"footystats_proxy"` 或 `"league_avg"`）
- [ ] `reasoning_summary` 提及 L4 跳过（无 PPDA）、L6 跳过（无阵容）、L7 预测差异、Layer AH 状态、xG 数据来源
- [ ] **所有计算（Dixon-Coles 泊松、AH 概率、EV、Kelly、置信度）均通过 MCP 工具调用**

---
name: goalcast-analyzer-v25
description: Use this skill when the user wants a single-match Goalcast football analysis with the v2.5 five-layer model, or when another skill needs the v2.5 analyzer as a sub-agent.
---

# Goalcast Analyzer v2.5

版本：v2.5 | 框架：五层分析模型
适用：独立调用，或被 `goalcast-analysis-orchestrator`（mode=analyze）直接调度，或被 `goalcast-compare`（mode=compare）作为 sub-agent 调用

## 触发条件

以下任意情况激活此 skill：
- 用户说"用 v2.5 分析 [比赛]"
- 用户说"v2.5 方法分析 [比赛]"
- 被 `goalcast-analysis-orchestrator` 在 `mode=analyze` 下按场次调度
- 被 `goalcast-compare` 作为 sub-agent 调用（比赛信息通过 context 传入）

## 核心约束

### ⚠️ 绝对红线 (CRITICAL CONSTRAINTS)
- **禁止自建脚本**：绝对禁止编写、生成或执行任何临时的 Python/Shell 脚本来获取数据或进行计算。
- **禁止直调源码**：绝对禁止直接调用或运行项目底层的源代码文件。
- **强制工具边界**：必须且只能通过 `run_mcp` 调用下文列出的可用 MCP 工具。

1. **禁止编造数据** - 字段不存在时必须标注缺失，不得估算填充
2. **禁止情感化语言** - 不得使用"状态火热"、"势如破竹"等表述
3. **置信度上限 90** - 绝对禁止输出 >90 的置信度
4. **概率三项之和必须 = 100%**（允许 ±0.5% 误差）

## 关键变更

⚠️ **所有数学计算（泊松分布、EV、置信度）必须通过 MCP 工具调用，禁止 LLM 心算。**
- 泊松分布 → `goalcast_calculate_poisson`
- EV 计算 → `goalcast_calculate_ev`
- Kelly → `goalcast_calculate_kelly`
- 风险调整 EV → `goalcast_calculate_risk_adjusted_ev`
- 置信度 → `goalcast_calculate_confidence(method="v2.5", ...)`

## 执行步骤

### Step 1：定位比赛

**注**：通过 `goalcast_footystats_get_todays_matches` 获取比赛 ID，无需直接调用 provider 工具。

调用 `goalcast_footystats_get_todays_matches`：
- 参数 `date`：用户指定日期（YYYY-MM-DD），默认今天
- 参数 `league_filter`：从用户意图提取，如 "Premier League"

按队名模糊匹配提取目标比赛，获取：
- `match_id` / `fixture_id` → provider 内部 ID
- `home_team_id` / `away_team_id`
- `competition` → 联赛名
- `season_id`

如未找到：回复"未找到符合条件的比赛"，停止。

**被 goalcast-compare 作为子 agent 调用时**：
接收参数包含 `fixture_id`, `home_team`, `away_team`, `league`, `match_date`, `model_version`, `data_source`, `match_type`。
调用方在 compare 层做字段映射：`league -> competition`，`match_date -> date`，`model_version -> model`。
此时跳过用户交互，直接以队名在 `goalcast_footystats_get_todays_matches` 结果中定位比赛。

### Step 2：数据采集（统一接口）

调用 `goalcast_footystats_resolve_match` 工具：

```
goalcast_footystats_resolve_match(
    match_id=<match_id>,
    home_team=<home_team>,
    home_team_id=<home_team_id>,
    away_team=<away_team>,
    away_team_id=<away_team_id>,
    season_id=<season_id>,
    league=<competition>,
    match_date=<date>
)
```

**该工具自动处理**：FootyStats 主数据整合、Understat xG 补充、缓存与质量评分。

**子 agent 静默规则**：收到 `match_type` 参数时，零层检查直接采用该值，不询问用户。

### Step 3：零层数据检查

使用 `goalcast_footystats_resolve_match` 返回的 `MatchContext` 进行数据质量评估：

| 数据项 | 检查方式 | 降级处理 |
|--------|----------|----------|
| xG 数据 | `ctx.xg` 非空 | 不可用 → L1 使用联赛均值，`data_quality=low` |
| 主队近况 | `ctx.home_form_10` 非空 | 不可用 → L1 使用联赛均值，`data_quality=low` |
| 客队近况 | `ctx.away_form_10` 非空 | 不可用 → L1 使用联赛均值，`data_quality=low` |
| 赔率 | `ctx.odds` 非空且值 > 0 | 不可用 → L3 跳过，market 信号=中立 |
| 积分榜 | `ctx.home_standing` 非空 | 不可用 → L2 动力因素跳过 |
| 阵容 | **预期缺失** | 置信度 -10，L2 调整幅度上限 ±0.2 xG |

**数据质量确定**：
- `ctx.overall_quality >= 0.8` → `data_quality=high`
- `0.5 <= ctx.overall_quality < 0.8` → `data_quality=medium`
- `ctx.overall_quality < 0.5` → `data_quality=low`

**缺失数据处理**：
- 直接使用 `ctx.data_gaps` 作为 `missing_data` 列表

### Step 4：v2.5 五层分析

**【第一层 - 基础实力（权重 40%）】**

使用 `MatchContext` 中的 xG 数据：

```
# 从 ctx.xg 获取 xG 数据
base_xg_home = ctx.xg.home_xg_for
base_xg_away = ctx.xg.away_xg_for
xG_source = ctx.xg.source  # "understat_direct" | "footystats_proxy" | "league_avg"
```

**数据来源说明**：
- `understat_direct`：使用 Understat 直接 xG 数据（最优先）
- `footystats_proxy`：使用 FootyStats 近况数据计算的 proxy
- `league_avg`：使用联赛均值（最低优先级）

主场优势修正（联赛参数）：

| 联赛 | 主场 xG 修正 |
|------|------------|
| England Premier League | +0.25 |
| La Liga / Spanish | +0.22 |
| Serie A / Italian | +0.20 |
| Bundesliga / German | +0.28 |
| Ligue 1 / French | +0.26 |
| Champions League | +0.18 |
| 其他 | +0.20 |

```
base_xg_home = xG_proxy_home + 主场修正
base_xg_away = xG_proxy_away
```

如近况数据不可用：使用联赛均值（英超：主 1.5 / 客 1.2），标注 `data_quality=low`，注明"基于联赛均值估算"。

**xG 数据优先级总结**：
```
1. Understat 直接 xG → base_xg = Understat xG（最优先，置信度 +5）
2. FootyStats xG（如有）→ base_xg = FootyStats xG
3. Proxy 估算 → base_xg = xG_proxy（降级，置信度 -5）
4. 联赛均值 → base_xg = 联赛均值（最低，置信度 -8）
```

**【第二层 - 状态调整（权重 25%）】**

使用 `MatchContext` 数据进行状态调整：

1. **动力因素**（来自 `ctx.home_standing` 和 `ctx.away_standing`）：
   - 主队积分与第 4 名差距 ≤3 分（争欧战）：主队 +0.15 xG
   - 主队积分与降级区差距 ≤3 分（保级压力）：主队 +0.15 xG
   - 客队同理
2. **阵容不确定性**（预期触发）：
   - 所有调整幅度上限压缩为 ±0.2 xG（硬性约束）
   - 本次调整将置信度 -10
3. **无法获取的因素**（明确标注，不估算）：
   - 伤病/停赛：标注"数据不可用，跳过"
   - 赛程疲劳：标注"数据不可用，跳过"

```
adjusted_xg_home = base_xg_home + L2_adjustment_home（受 ±0.2 上限约束）
adjusted_xg_away = base_xg_away + L2_adjustment_away（受 ±0.2 上限约束）
```

**【第三层 - 市场行为（权重 20%）】**

使用 `MatchContext` 中的赔率数据：

```
# 从 ctx.odds 获取赔率
odds_home = ctx.odds.home_win
odds_draw = ctx.odds.draw
odds_away = ctx.odds.away_win

超售率 = 1/odds_home + 1/odds_draw + 1/odds_away
市场概率（归一化）：
  P_market_home = (1/odds_home) / 超售率
  P_market_draw = (1/odds_draw) / 超售率
  P_market_away = (1/odds_away) / 超售率
```

模型与市场分歧 = 模型概率 - 市场概率（各方向）

信号方向判断：
- 模型主队概率 > 市场主队概率 + 0.05 → "支持模型（主）"
- 模型客队概率 > 市场客队概率 + 0.05 → "支持模型（客）"
- 否则 → "中立"

如赔率字段值为 0 或缺失：跳过本层，`signal_direction="中立"`，`signal_strength="弱"`。

**【第四层 - 分布模型（权重 10%）】**

⚠️ **必须通过 MCP 工具调用，禁止 LLM 心算泊松分布。**

调用 `goalcast_calculate_poisson`：
```
goalcast_calculate_poisson(
    home_lambda=adjusted_xg_home,
    away_lambda=adjusted_xg_away,
    max_goals=6,
    model="standard"
)
```

从返回结果中提取：
- `home_win_pct` → 主胜概率
- `draw_pct` → 平局概率
- `away_win_pct` → 客胜概率
- `top_scores` → 前 5 高概率比分
- `score_matrix` → 完整比分概率矩阵

**【第五层 - 决策与风险（权重 5%）】**

⚠️ **必须通过 MCP 工具调用，禁止 LLM 心算 EV。**

对三个方向分别调用 `goalcast_calculate_ev`：
```
goalcast_calculate_ev(model_probability=模型P(主胜), market_odds=odds_ft_1)
goalcast_calculate_ev(model_probability=模型P(平),   market_odds=odds_ft_x)
goalcast_calculate_ev(model_probability=模型P(客胜), market_odds=odds_ft_2)
```

从返回结果中取 `ev` 最高的方向作为 `best_bet`。

再调用 `goalcast_calculate_risk_adjusted_ev` 获取风险调整后 EV：
```
goalcast_calculate_risk_adjusted_ev(
    raw_ev=最高EV,
    lineup_uncertainty=True,
    market_low_confidence=False,
    data_quality="medium"  # 根据实际数据质量
)
```

投注决策：
- EV > 0.08 → 推荐
- EV 0.04~0.08 → 小注
- EV < 0.04 → 不推荐

如赔率不可用（`odds=0`）：`EV=0`，`bet_rating="不推荐"`，`best_bet="不推荐（赔率数据不可用）"`。

**置信度计算**：

⚠️ **必须通过 MCP 工具调用，禁止 LLM 心算置信度。**

调用 `goalcast_calculate_confidence(method="v2.5", ...)`：
```
goalcast_calculate_confidence(
    method="v2.5",
    base_score=70,
    market_agrees=<是否一致>,
    data_complete=ctx.overall_quality >= 0.8,
    understat_available=ctx.xg.source == "understat_direct",
    odds_available=ctx.odds is not None,
    lineup_unavailable=True,
    xG_proxy_used=ctx.xg.source == "footystats_proxy",
    market_disagrees=<市场是否相反>,
    data_quality_low=ctx.overall_quality < 0.5,
    understat_failed=ctx.xg.source != "understat_direct" and ctx.sources.xg == "understat"
)
```

从返回结果中取 `confidence` 作为最终值。

### Step 5：输出 `AnalysisResult`

严格按以下 JSON schema 输出，字段不得增减：

```json
{
  "method": "v2.5",
  "match_info": {
    "home_team": "<ctx.match_info.home_team>",
    "away_team": "<ctx.match_info.away_team>",
    "competition": "<ctx.match_info.league>",
    "match_type": "A",
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
  "reasoning_summary": "<各层关键结论，须包含：xG 数据来源、市场信号方向、EV 计算依据、置信度扣分项>"
}
```

输出前必须自检：
- [ ] `home_win% + draw% + away_win% = 100%`（±0.5%）
- [ ] `confidence ∈ [30, 90]`
- [ ] `ev ∈ [-1, +2]`
- [ ] `missing_data` 包含 `"lineup"`
- [ ] `xG_source` 字段存在（`"understat_direct"`、`"footystats_proxy"` 或 `"league_avg"`）
- [ ] `reasoning_summary` 非空且提及 xG 数据来源
- [ ] **所有计算（泊松、EV、置信度）均通过 MCP 工具调用**

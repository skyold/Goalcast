---
name: goalcast-analyzer-v25
description: Use this skill when the user wants a single-match Goalcast football analysis with the v2.5 five-layer model, or when another skill needs the v2.5 analyzer as a sub-agent.
---

# Goalcast Analyzer v2.5

版本：v2.5 | 框架：五层分析模型
适用：独立调用或被 `goalcast-compare` 作为 sub-agent 调用

## 触发条件

以下任意情况激活此 skill：
- 用户说"用 v2.5 分析 [比赛]"
- 用户说"v2.5 方法分析 [比赛]"
- 被 `goalcast-compare` 作为 sub-agent 调用（比赛信息通过 context 传入）

## 核心约束

1. **禁止编造数据** - 字段不存在时必须标注缺失，不得估算填充
2. **禁止情感化语言** - 不得使用"状态火热"、"势如破竹"等表述
3. **置信度上限 90** - 绝对禁止输出 >90 的置信度
4. **概率三项之和必须 = 100%**（允许 ±0.5% 误差）

## 执行步骤

### Step 1：定位比赛

调用 `mcp__goalcast__footystats_get_todays_matches`：
- 参数 `date`：用户指定日期（YYYY-MM-DD），默认今天
- 参数 `league_filter`：从用户意图提取，如 "Premier League"、"Champions League"

从返回的 `data[]` 数组中找到目标比赛，提取：
- `id` → match_id
- `homeID` → home_team_id
- `awayID` → away_team_id
- `home_name` → 主队名
- `away_name` → 客队名
- `competition_id` → 用于查积分榜
- `competition_name`（或 `competition`）→ 联赛名

如果找不到比赛：回复"未找到符合条件的比赛，请确认日期和联赛名称"，停止执行。

### Step 2：并行采集数据（FootyStats）

同时调用以下 4 个工具：

```text
mcp__goalcast__footystats_get_match_details(match_id=<id>)
mcp__goalcast__footystats_get_team_last_x_stats(team_id=<homeID>)
mcp__goalcast__footystats_get_team_last_x_stats(team_id=<awayID>)
mcp__goalcast__footystats_get_league_tables(season_id=<competition_id>)
```

注意：工具参数名为 `season_id`，值来自 Step 1 提取的 `competition_id` 字段。FootyStats 中 `season` 与 `competition` 指同一实体。

记录每个调用是否成功。失败项列入 `missing_data`。

### Step 2.5：Understat 数据补充（条件触发）

**触发条件**：满足以下任一情况即执行：
- FootyStats 不提供 xG 数据（`xG` 字段缺失）
- 用户明确要求使用 xG 数据
- 联赛属于 Understat 支持范围（EPL, La_liga, Bundesliga, Serie_A, Ligue_1, RFPL）

**执行步骤**：

1. **确定联赛代码和赛季**：
   ```text
   联赛映射表：
   - England Premier League → EPL
   - La Liga / Spanish → La_liga
   - Bundesliga / German → Bundesliga
   - Serie A / Italian → Serie_A
   - Ligue 1 / French → Ligue_1
   - 其他 → 跳过 Understat
   ```

2. **获取 Understat 联赛比赛列表**：
   ```text
   mcp__goalcast__understat_get_league_matches(league=<联赛代码>, season=<赛季年份>)
   ```

3. **匹配比赛**（通过球队名 + 日期）：
   - 遍历 Understat 比赛列表
   - 匹配条件：`h_team` 包含主队名关键词 OR `a_team` 包含客队名关键词
   - 提取匹配到的 `match_id`（Understat ID）

4. **获取 xG 数据**（如果匹配成功）：
   ```text
   mcp__goalcast__understat_get_match_stats(match_id=<understat_match_id>)
   ```

5. **数据融合**：
   - 从 Understat 提取：`home_xg`, `away_xg`, `shots`（射门详情）
   - 更新 L1 计算：使用 Understat 的 xG 替代 `xG_proxy`
   - 标注数据来源：`xG_source="understat"` 或 `xG_source="proxy"`

**失败处理**：
- Understat 匹配失败 → 降级使用 `xG_proxy`，标注 `xG_source="proxy"`
- Understat 数据不可用 → 标注 `missing_data` 增加 `"understat_xg"`

### Step 3：零层数据检查

分析前，检查并记录每项数据的可用性：

| 数据项 | 检查方式 | 降级处理 |
|--------|----------|----------|
| 主队近况（last_x） | `data` 数组非空 | 不可用 → 使用联赛均值，`data_quality=low` |
| 客队近况（last_x） | `data` 数组非空 | 不可用 → 使用联赛均值，`data_quality=low` |
| 赔率（odds_ft_1/x/2） | 值 > 0 | 不可用 → L3 跳过，market 信号=中立 |
| 积分榜（league_table） | `league_table` 非 null | 不可用 → L2 动力因素跳过 |
| 阵容（首发） | **预期缺失** | 置信度 -10，L2 调整幅度上限 ±0.2 xG |
| xG 直接数据（FootyStats） | **预期缺失** | 尝试 Understat 补充（Step 2.5） |
| xG 直接数据（Understat） | Step 2.5 匹配成功 | 不可用 → L1 使用进球数代理（`xG_proxy`） |

将所有预期和实际缺失的数据写入 `missing_data` 列表。

### Step 4：v2.5 五层分析

**【第一层 - 基础实力（权重 40%）】**

**优先级 1：使用 Understat xG 数据（如果 Step 2.5 成功获取）**

```text
如果 xG_source="understat"：
  base_xg_home = Understat.home_xg
  base_xg_away = Understat.away_xg
  标注：xG_source="understat_direct"
```

**优先级 2：降级使用 proxy（如果 Understat 不可用）**

从 `get_team_last_x_stats` 提取场均进球数（字段：`stats.seasonScoredAVG_overall`，按 `last_x_match_num` 遍历匹配 5 和 10）：

```text
xG_proxy_home = 近 10 场场均进球 × 0.7 + 近 5 场场均进球 × 0.3
xG_proxy_away = 近 10 场场均进球 × 0.7 + 近 5 场场均进球 × 0.3
```

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

```text
base_xg_home = xG_proxy_home + 主场修正
base_xg_away = xG_proxy_away
```

如近况数据不可用：使用联赛均值（英超：主 1.5 / 客 1.2），标注 `data_quality=low`，注明"基于联赛均值估算"。

**xG 数据优先级总结**：
```text
1. Understat 直接 xG → base_xg = Understat xG（最优先，置信度 +5）
2. FootyStats xG（如有）→ base_xg = FootyStats xG
3. Proxy 估算 → base_xg = xG_proxy（降级，置信度 -5）
4. 联赛均值 → base_xg = 联赛均值（最低，置信度 -8）
```

**【第二层 - 状态调整（权重 25%）】**

将可用的短期因素转为结构化 xG 调整（禁止叙述性描述，必须量化）：

1. **动力因素**（来自 `league_table`，字段 `points` / `position`）：
   - 主队积分与第 4 名差距 ≤3 分（争欧战）：主队 +0.15 xG
   - 主队积分与降级区差距 ≤3 分（保级压力）：主队 +0.15 xG
   - 客队同理
2. **阵容不确定性**（预期触发）：
   - 所有调整幅度上限压缩为 ±0.2 xG（硬性约束）
   - 本次调整将置信度 -10
3. **无法获取的因素**（明确标注，不估算）：
   - 伤病/停赛：标注"数据不可用，跳过"
   - 赛程疲劳：标注"数据不可用，跳过"

```text
adjusted_xg_home = base_xg_home + L2_adjustment_home（受 ±0.2 上限约束）
adjusted_xg_away = base_xg_away + L2_adjustment_away（受 ±0.2 上限约束）
```

**【第三层 - 市场行为（权重 20%）】**

使用 `match_details` 中的赔率字段（`odds_ft_1` / `odds_ft_x` / `odds_ft_2`）：

```text
超售率 = 1/odds_ft_1 + 1/odds_ft_x + 1/odds_ft_2
市场概率（归一化）：
  P_market_home = (1/odds_ft_1) / 超售率
  P_market_draw = (1/odds_ft_x) / 超售率
  P_market_away = (1/odds_ft_2) / 超售率
```

模型与市场分歧 = 模型概率 - 市场概率（各方向）

信号方向判断：
- 模型主队概率 > 市场主队概率 + 0.05 → "支持模型（主）"
- 模型客队概率 > 市场客队概率 + 0.05 → "支持模型（客）"
- 否则 → "中立"

如赔率字段值为 0 或缺失：跳过本层，`signal_direction="中立"`，`signal_strength="弱"`。

**【第四层 - 分布模型（权重 10%）】**

使用标准泊松分布（v2.5 不使用 Dixon-Coles 修正）：

```text
λ_home = adjusted_xg_home
λ_away = adjusted_xg_away

P(主队进 k 球) = e^(-λ_home) × λ_home^k / k!
P(客队进 k 球) = e^(-λ_away) × λ_away^k / k!
```

计算 0-5 × 0-5 的比分矩阵（36 种比分组合）：
- `P(主胜)` = 所有主队进球 > 客队进球的概率之和
- `P(平)` = 所有主客进球相等的概率之和
- `P(客胜)` = `1 - P(主胜) - P(平)`

取概率最高的前 3 个比分作为 `top_scores`。

**【第五层 - 决策与风险（权重 5%）】**

EV 计算（v2.5 简化版）：

```text
对主胜方向：EV = 模型P(主胜) × odds_ft_1 - 1
对平局方向：EV = 模型P(平) × odds_ft_x - 1
对客胜方向：EV = 模型P(客胜) × odds_ft_2 - 1
```

选取 EV 最高的方向作为 `best_bet`。

投注决策：
- EV > 0.08 → 推荐
- EV 0.04~0.08 → 小注
- EV < 0.04 → 不推荐

如赔率不可用（`odds=0`）：`EV=0`，`bet_rating="不推荐"`，`best_bet="不推荐（赔率数据不可用）"`。

置信度计算：

```text
基础分 = 70

加分：
+8   市场方向与模型一致（signal_direction 含"支持模型"）
+5   近况数据完整（主客队均有 last_x 数据）
+5   Understat xG 数据可用（xG_source="understat_direct"）

扣分：
-10  阵容不可用（预期触发，必扣）
-5   xG 使用代理值（预期触发，必扣）
-5   赔率方向与模型相反
-8   近况数据不可用（data_quality=low）
-5   Understat 匹配失败（仅当联赛在支持范围内）

范围限制：[30, 90]
```

### Step 5：输出 `AnalysisResult`

严格按以下 JSON schema 输出，字段不得增减：

```json
{
  "method": "v2.5",
  "match_info": {
    "home_team": "<主队名>",
    "away_team": "<客队名>",
    "competition": "<联赛名>",
    "match_type": "A",
    "data_quality": "medium",
    "missing_data": ["lineup", "xG_direct"]
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
  "reasoning_summary": "<各层关键结论，须包含：xG_proxy 数值、市场信号方向、EV 计算依据、置信度扣分项>"
}
```

输出前必须自检：
- [ ] `home_win% + draw% + away_win% = 100%`（±0.5%）
- [ ] `confidence ∈ [30, 90]`
- [ ] `ev ∈ [-1, +2]`
- [ ] `missing_data` 包含 `"lineup"`
- [ ] `xG_source` 字段存在（`"understat_direct"` 或 `"proxy"`）
- [ ] `reasoning_summary` 非空且提及数据来源（Understat 或 proxy）

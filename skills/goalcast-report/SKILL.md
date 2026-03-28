---
name: goalcast-report
description: "Format Goalcast analysis JSON into a human-readable match prediction report. Use after goalcast-analyze produces its JSON output, or when user asks to 'show the report', 'format the analysis', 'display prediction results'. Converts structured JSON into a clear Markdown report with probability tables, contradiction warnings, EV recommendation, and confidence rating."
---

# Goalcast Report Formatter

## Purpose

Convert a `goalcast-analyze` JSON output into a human-readable Markdown report.

## Workflow

1. Receive the JSON from `goalcast-analyze`.
2. Render the report using the template below.
3. Apply conditional blocks based on field values.
4. Output Markdown only — no JSON visible in the final report.

## Rendering Rules

### Confidence badge
- ≥ 70: add `🟢` before the score
- 55–69: add `🟡` before the score
- < 55: add `🔴` before the score, append `（低置信度，谨慎参考）`

### EV label
- EV_adj > 0.10: `高价值`
- EV_adj 0.05–0.10: `中等价值`
- EV_adj < 0.05: `无投注价值`

### Missing data display
Translate internal field names to readable Chinese:
- `injuries` → 伤病/停赛
- `lineup` → 首发阵容
- `schedule_density` → 赛程密度
- `motivation` → 积分动力
- `elo` → Elo 评分
- `odds_movement` → 赔率变动
- `ppda` → 逼抢强度

### Bet block
- Only show `✅ 投注建议` block if bet_rating is `推荐` or `小注`
- Otherwise show `❌ 无投注价值` block

### Contradiction block
- Only show if `contradiction_analysis.exists` is true
- Use `⚠️` header — must be visible, never folded

## Report Template

```
============================================================
⚽ Goalcast 比赛预测
{home_team} vs {away_team}
{competition}
============================================================

📋 数据质量   {data_quality}
{if sample_size_warning}
⚠️  小样本警告：赛季数据场次不足，统计可信度受限
{/if}
{if missing_data not empty}
缺失字段：{missing_data — translated}
{/if}

------------------------------------------------------------
🎯 概率预测
------------------------------------------------------------
             主胜        平局        客胜
模型        {home_win}    {draw}    {away_win}
市场(Pin)  {pin_home}   {pin_draw}  {pin_away}
分歧       {div_home}   {div_draw}  {div_away}

市场信号：{signal_direction}（{signal_strength}）

------------------------------------------------------------
📐 xG 建模
------------------------------------------------------------
λ（主队预期进球）: {lambda_home}
μ（客队预期进球）: {mu_away}

最可能比分：
  1. {score_1}  {prob_1}
  2. {score_2}  {prob_2}
  3. {score_3}  {prob_3}

------------------------------------------------------------
{if contradiction_analysis.exists}
⚠️  矛盾信号
------------------------------------------------------------
{contradiction_analysis.description}

分析：{contradiction_analysis.resolution}
对模型影响：{contradiction_analysis.impact_on_model}

------------------------------------------------------------
{/if}
💡 分析摘要
------------------------------------------------------------
[第一层] {layer1_xg_calc}

[第二层] {layer2_context}

[第三层] {layer3_market}

[第四层] {layer4_tempo_contradiction}

[第五层] {layer5_distribution}

[第七层] {layer7_ev}

------------------------------------------------------------
{if bet_rating in [推荐, 小注]}
✅ 投注建议
------------------------------------------------------------
方向：{best_bet}
EV（原始）：{ev_raw}
EV（风险调整后）：{ev_risk_adjusted}  → {EV label}
评级：{bet_rating}

注：EV 基于 Pinnacle 赔率计算。实际投注请使用最优赔率。
{else}
❌ 无投注价值
------------------------------------------------------------
风险调整后 EV 低于阈值（0.05）。
最高 EV 方向：{best_bet}（EV_adj = {ev_risk_adjusted}）
{/if}

------------------------------------------------------------
📈 置信度
------------------------------------------------------------
{badge} {confidence}/90

{layer8_confidence}

------------------------------------------------------------
⚙️  技术备注
------------------------------------------------------------
· Pinnacle 赔率用于 EV 计算
· Soft odds (odds_ft_*) 仅参考，未用于 EV
· {sample_size_note}
· {league_params}
============================================================
```

## Notes

- If any JSON field is null or empty, omit that line silently rather than showing "null".
- Divergence values: format as `+X.X%` or `-X.X%` (include sign always).
- Keep the report concise. Do not add commentary beyond what is in the JSON.
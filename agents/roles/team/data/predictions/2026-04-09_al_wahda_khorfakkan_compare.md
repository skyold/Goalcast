
## Al Wahda vs Al Ittihad Kalba - 多方法分析对比
**日期**：2026-04-09 | **联赛**：UAE Arabian Gulf League | **数据质量**：medium

---

### 结论对比

| 维度 | v2.5 | v3.0 | 差异 |
|------|------|------|------|
| 数据来源 | proxy | proxy | ✓一致 |
| 主队胜率 | 48.8% | 47.5% | -1.3% |
| 平局概率 | 23.3% | 26.1% | +2.8% |
| 客队胜率 | 27.9% | 26.5% | -1.4% |
| 最佳投注 | 客胜 | 客胜 | ✓一致 |
| EV（风险调整后） | 0.30 | 0.14 | -0.16 |
| 置信度 | 71 | 68 | -3 |

### 主要分歧点

两个方法结论基本一致。主要的微小差异源于：
1. **分布模型差异**：v3.0 使用了 Dixon-Coles 修正，提高了平局概率（从 23.3% 升至 26.1%），导致主客胜率均略有下降。
2. **风险调整**：v3.0 对 EV 进行了更严格的降权处理（乘以 0.85 阵容不确定项和 0.90 市场层降级项），导致最终 EV 从 0.18 降至 0.14。
3. **投注评级**：v2.5 由于原始 EV 较高且置信度过线，给出了“推荐”评级；而 v3.0 考虑到多项不确定因素，评级下调为“小注”。

---

### v2.5 完整分析

```json
{
  "method": "v2.5",
  "match_info": {
    "home_team": "Al Wahda",
    "away_team": "Al Ittihad Kalba",
    "competition": "UAE Arabian Gulf League",
    "match_type": "A",
    "data_quality": "medium",
    "missing_data": ["lineup", "xG_direct"]
  },
  "probabilities": {
    "home_win": "48.8%",
    "draw": "23.3%",
    "away_win": "27.9%"
  },
  "top_scores": [
    { "score": "1-1", "probability_pct": 10.66 },
    { "score": "2-1", "probability_pct": 9.49 },
    { "score": "1-0", "probability_pct": 8.26 }
  ],
  "market": {
    "market_probabilities": {
      "home_win": "58.0%",
      "draw": "22.9%",
      "away_win": "19.2%"
    },
    "signal_direction": "支持模型",
    "signal_strength": "中"
  },
  "decision": {
    "ev": 0.3,
    "best_bet": "客胜",
    "bet_rating": "推荐",
    "confidence": 71
  },
  "reasoning_summary": "v2.5: 使用 proxy xG 数据 (1.63/1.29)，考虑动力调整 (+0.15) 后，模型显示客胜方向具有显著正 EV。市场过度高看主队，创造了博弈空间。"
}
```

---

### v3.0 完整分析

```json
{
  "method": "v3.0",
  "match_info": {
    "home_team": "Al Wahda",
    "away_team": "Al Ittihad Kalba",
    "competition": "UAE Arabian Gulf League",
    "match_type": "A",
    "data_quality": "medium",
    "missing_data": ["lineup", "xG_direct", "ppda", "odds_movement"]
  },
  "probabilities": {
    "home_win": "47.5%",
    "draw": "26.1%",
    "away_win": "26.5%"
  },
  "top_scores": [
    { "score": "1-1", "probability_pct": 12.04 },
    { "score": "2-1", "probability_pct": 9.49 },
    { "score": "2-0", "probability_pct": 7.35 }
  ],
  "market": {
    "market_probabilities": {
      "home_win": "58.0%",
      "draw": "22.9%",
      "away_win": "19.2%"
    },
    "signal_direction": "支持模型",
    "signal_strength": "弱"
  },
  "decision": {
    "ev": 0.18,
    "risk_adjusted_ev": 0.14,
    "best_bet": "客胜",
    "bet_rating": "小注",
    "confidence": 68
  },
  "reasoning_summary": "v3.0: 使用 Dixon-Coles 分布修正，平局概率提升。由于缺乏阵容实时数据和赔率变动时序，市场层和置信度均被降权。风险调整后的 EV 仍支持客胜方向，但建议轻仓。"
}
```

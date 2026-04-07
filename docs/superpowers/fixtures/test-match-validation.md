# AnalysisResult 验证 Checklist

## 测试比赛
- 主队：Arsenal
- 客队：AFC Bournemouth
- match_id：8223599
- homeID：59
- awayID：148
- competition_id：15050
- 联赛：England Premier League
- 日期：2026-04-11

---

## 必须通过的验证项

### 结构完整性
- [ ] 输出包含 `method` 字段，值为 "v2.5" 或 "v3.0"
- [ ] 输出包含 `match_info` 对象，含 home_team / away_team / competition / match_type / data_quality / missing_data
- [ ] 输出包含 `probabilities`，含 home_win / draw / away_win（格式为百分比字符串，如 "45%"）
- [ ] 输出包含 `top_scores` 数组，至少3个比分预测，每项含 score 和 probability
- [ ] 输出包含 `market` 对象，含 market_probabilities / signal_direction / signal_strength
- [ ] 输出包含 `decision` 对象，含 ev / risk_adjusted_ev / best_bet / bet_rating / confidence
- [ ] 输出包含 `reasoning_summary`（非空字符串）

### 数值约束
- [ ] home_win% + draw% + away_win% = 100%（允许 ±0.5% 误差）
- [ ] confidence 在 [30, 90] 范围内
- [ ] ev 在 [-1, +2] 范围内
- [ ] bet_rating 是 "推荐" / "小注" / "不推荐" 之一
- [ ] signal_direction 是 "支持模型" / "反对模型" / "中立" 之一

### 数据质量标注
- [ ] `missing_data` 包含 "lineup"（FotMob 阵容不可用）
- [ ] `missing_data` 包含 "xG_direct"（直接 xG 数据不可用）
- [ ] `data_quality` 为 "medium"（因 xG 使用代理值）
- [ ] `reasoning_summary` 中提到了数据降级或缺失数据

### v3.0 专属验证项
- [ ] `match_type` 为 A/B/C/D 之一（v3.0 必须分类）
- [ ] `missing_data` 包含 "ppda"（PPDA 数据不可用）
- [ ] `missing_data` 包含 "odds_movement"（无赔率变动时序）
- [ ] `reasoning_summary` 提及 L4 节奏层跳过（无 PPDA）
- [ ] `reasoning_summary` 提及 L6 贝叶斯层跳过（无阵容确认）

### v2.5 专属验证项
- [ ] 分析层数为5层（基础实力/状态调整/市场行为/分布模型/决策）
- [ ] 未出现 "Dixon-Coles" 以外的高级修正（v2.5 用标准泊松）

---

## 跨方法一致性验证（运行 goalcast-compare 后检查）
- [ ] 两份结果的 method 字段分别为 "v2.5" 和 "v3.0"
- [ ] 主队胜率差异 < 15%（差距过大说明某 skill 有逻辑问题）
- [ ] v3.0 置信度 ≤ v2.5 置信度（v3.0 有更多扣分项）
- [ ] 对比表包含所有6个维度：主队胜率/平局/客队胜率/最佳投注/EV/置信度

---

## 实际测试记录（运行后填写）

### 测试日期：____
- 触发话术：____
- v2.5 主队胜率：____
- v3.0 主队胜率：____
- 两者差异：____%
- v2.5 置信度：____
- v3.0 置信度：____
- 所有 checklist 项：通过 / 未通过项：____

# 回测中心：长期追踪多模型的预测准确性

> 路线对应：roadmap #5 "将比赛的真实结果和预测比较长期追踪回测不同模型的准确性"
> 它同时是 #4（自有模型）的前置：没有它，没人能证明自有模型相对默认模型有差异化价值。

## Problem Statement

Goalcast 当前给用户的所有预测（Dashboard KPI、Value Bets、错定价、MatchDetail 1X2 概率）都来自单一外部源 OddAlerts，UI 上没有任何机制让用户回答："这个模型最近表现到底如何？在我关注的联赛上比市场准吗？"——结果是：
- 用户对 KPI 数字的信任完全取决于 Goalcast 的"品牌好感"，而不是可验证的事实。
- 我们自己也无法判断 OddAlerts 在哪些联赛 / 哪类比赛上系统性失准——也就无法决定 #4 自有模型应该首先攻克哪片盲区。

## Evidence

- **快照管线已经在跑**：`historical_predictions(fixture_id, waypoint, home_win_pct, draw_pct, away_win_pct, btts_pct, o25_pct, scorelines, captured_at)` 在 T-48h / T-24h / T-6h / T-1h / kickoff 五个 waypoint 采集预测；commit `3eace50` 上线（2026-05 月内）。
- **真实结果数据充沛**：`fixtures` 表 `status='FT' AND score_home IS NOT NULL` 当前 **47,784** 行，含 `predictability` 标注和 `competition_id`。
- **但配对数为零（冷启动期）**：`FT × historical_predictions.waypoint='kickoff'` 当前 join 结果 = **0 条**——管线刚上线，目前 in-snapshot 的比赛尚未走完 FT，预计 1–2 周才能积累首批可用样本。
- **回填路径不可行**：`predictions` 表是 upsert，FT 后被覆写，无法可信地反推历史"开赛前 OddAlerts 预测"；外部 OddAlerts 也不提供历史快照 API。所以本 PRD 只能走 forward-looking。
- **校准信号已经在 Phase 4 雏形里**：`/api/insights/leagues/:id` 已经在算 `model_hit_rate_pct` 和 `upset_pct`（基于 `historical_predictions.waypoint='kickoff'`），但只有联赛维度、只有 top-1 命中率、没有概率级评估、没有时间维度趋势——是"准确性"的最低维度切片。

## Proposed Solution

新增 `/insights/backtest` 页面 + `/api/backtest/*` 一组只读 endpoint，对历史"快照预测 vs 真实结果"配对做四个维度的聚合展示：

1. **Top-1 命中率**（argmax 模型概率 = 实际 1X2 结果的比例，按联赛 / predictability / waypoint 分桶）
2. **Brier 分数**（概率级损失：(模型 - one-hot 实际)² 求和，越低越准）
3. **校准曲线**（把 model_prob 按 10 个分箱 bin 化，对每箱统计实际命中率，理想 = y=x 直线）
4. **市场基线对比**（同样指标对 de-vigged Pinnacle 1X2 implied probability 算一遍，让用户看到"模型相对市场赚多少 / 输多少"）

所有计算复用现有表，无新数据源、无新建表。

> Phase 1 只接 1 个模型（OddAlerts 当前默认），但 schema 与 endpoint 命名（`model_id` 字段）一律预留多模型——为 #4 的"自有模型 vs 默认模型"对比铺路。

## Key Hypothesis

我们相信【一个能看见 OddAlerts 长期 hit rate 和校准曲线的页面】会把 Goalcast 从"AI 黑盒"变成"可验证的赛前工作台"。验收信号：

- 进入过 `/insights/backtest` 至少一次的用户，7 日留存率 ≥ 60%（vs 整体登录用户基线）。
- 数据积累到 ≥ 500 个 FT+kickoff_snap 配对后，OddAlerts 整体 Top-1 命中率落在 [45%, 60%]、Brier 落在 [0.55, 0.65] 区间（超出此区间提示数据管线异常）。
- 至少能识别出 1 个"模型显著优于市场"和 1 个"模型显著劣于市场"的联赛分桶（差异 > 5pp）——这是 #4 自有模型选战场的输入。

## What We're NOT Building

- **训练 / 修改 / 替换任何模型** —— 本 PRD 只评估，不创建。自有模型留 #4。
- **多模型选择 UI**（"切换到模型 B"）—— 数据 schema 预留 `model_id`，UI 留 #4。
- **滚动盘内回测 / 滚球预测评估** —— 只评估赛前 5 waypoint，不评估 live。
- **用户级标注 / CLV / 实战盈亏曲线** —— 那是"投注表现追踪"，跟"模型准确性"不是一码事，留 V1.5。
- **回填历史 OddAlerts 预测** —— 上文 Evidence 已说明不可行；只用 forward-looking 快照。
- **任何 ML pipeline / 自动重训 / 漂移告警** —— 等首批 500+ 配对积累完再考虑。

## Success Metrics

| Metric | Target | How Measured |
|--------|--------|--------------|
| 配对积累速度 | 上线后 14 天内 ≥ 300 个 FT+kickoff_snap 配对 | DB count |
| 页面 P95 加载耗时 | < 1.0s（含计算 + 渲染） | 前端 PerformanceObserver |
| 校准曲线分箱稳定性 | 上线 30 天后每箱样本 ≥ 30 个 | DB query on backtest endpoint |
| 回测 endpoint 命中率与 league_stats 一致 | 差异 < 0.5pp（双重实现交叉校验） | 回归测试 |

## Open Questions

- [ ] **冷启动的 14 天页面如何呈现？** 当前=0 配对，14 天后 ~300 条。建议页面先显示"数据积累中，已收集 N / 500"进度条 + 已有数据的临时分桶；阈值前不挂主导航。
- [ ] **主指标用 Brier 还是 log-loss？** Brier 直觉强（"概率离真相多远"），log-loss 对错得离谱的预测惩罚更重。建议 V1 同时展示，Brier 默认排序，log-loss 在工具提示里。
- [ ] **校准曲线分箱粒度** 10 箱 vs 20 箱？10 箱对 500 配对刚够，20 箱要等到 ≥ 2000。建议从 10 箱起步，超阈值后自动加密。
- [ ] **waypoint 维度怎么切？** 默认按 `kickoff` 评估（最权威），但 T-48h vs kickoff 的对比能揭示"模型在赛前 48h 是否已经稳定"。建议主表只放 kickoff，"waypoint 漂移"作为高级页签。
- [ ] **过期的 predictability 标签怎么办？** 本 PRD 假设 FT fixture 的 predictability 是赛前赋的、未受结果污染；要确认快照管线没有在 FT 之后回写 predictability。

---

## Users & Context

**Primary User**
- **Who**：注重数据可信度的中级以上投注用户，看到 KPI 第一反应是"这个数字从哪来 / 准不准"；目前 30s 内打开 Goalcast 看完总览就跳到其它工具校验。
- **Trigger**：从 Dashboard 看到模型推荐时；从 ValueBets / Mispricings 想下注前。
- **Success state**：能在一个页面回答"OddAlerts 在英超过去 60 天 Top-1 命中率 53.2%，市场 51.8%——模型略胜"，于是愿意把 Goalcast 当主要决策入口。

**Job to Be Done**
当我看到 Goalcast 给的预测时，我希望能直接验证这个模型在我关心的联赛里历史上准到什么程度、是否比市场更准——这样我才知道这个数字应不应该影响我的下注。

**Non-Users**
- 完全依赖 AI "跟单"的休闲用户：他们只看 Top 5 推荐，不会进回测页。
- 只看 prop bets / 球员盘的用户：本期只覆盖 1X2，与他们诉求不重叠。

---

## Solution Detail

### Capabilities (MoSCoW)

| Priority | Capability | Rationale |
|----------|------------|-----------|
| Must | 后端：`GET /api/backtest/summary?competition_id&waypoint&min_samples` 返回 hit rate / Brier / 样本数 / 95% 置信区间 | 主页面数据源 |
| Must | 后端：`GET /api/backtest/calibration?bins=10&...` 返回每箱 (predicted_avg, actual_rate, n) | 校准曲线 |
| Must | 后端：`GET /api/backtest/by-league?waypoint=kickoff` 返回所有联赛的 hit rate + Brier 排序 | "模型在哪些联赛失准"的入口 |
| Must | 前端：`/insights/backtest` 页面，三个 Tab：总览 / 按联赛 / 校准曲线 | 主交付 |
| Must | 数据冷启动保护：所有 endpoint 在样本数 < 阈值（默认 30/箱、100/联赛）时返回 `enough=false` + 计数，前端展示"积累中"占位 | 防止用 5 条数据画曲线误导用户 |
| Must | 所有响应字段含 `model_id`（V1 硬编码 `"oddalerts_default"`），表 / endpoint 命名预留多模型扩展 | 为 #4 铺路 |
| Should | 市场基线对比：同样指标对 de-vigged Pinnacle 1X2 implied prob 算一遍，并列展示 | 让"模型 vs 市场"成为一眼可读的结论 |
| Should | 按 predictability 分桶视图（high/good/medium/poor）| 揭示"模型在难预测的比赛上掉得多狠" |
| Won't (V1) | 多模型并排对比 UI | 等 #4 自有模型上线 |
| Won't (V1) | waypoint 漂移图（T-48h → kickoff 的预测稳定性） | V1.1 |
| Won't (V1) | 时间窗滑动（"过去 30 天"）—— V1 默认全量 | V1.1 |

### Data Flow

```
historical_predictions (waypoint='kickoff')
  ⨝ fixtures (status='FT', score_home/away)
    → 配对生成 (fixture_id, model_prob[home/draw/away], actual_outcome ∈ {H,D,A})
    → 聚合（hit / Brier / per-bin calibration）
    → 缓存（in-process LRU，5 分钟 TTL；每天 FT 入库后失效）
    → /api/backtest/* 响应
```

`historical_odds.waypoint='kickoff' AND bookmaker_id=1 AND market_id=6` 与上面同维度 join 出"市场基线"。

### 字段契约（V1 响应示例）

```json
{
  "model_id": "oddalerts_default",
  "scope": { "competition_id": null, "waypoint": "kickoff" },
  "samples": 312,
  "enough": false,
  "min_samples": 500,
  "metrics": {
    "top1_hit_rate": 0.524,
    "top1_hit_rate_ci95": [0.468, 0.580],
    "brier": 0.612,
    "log_loss": 1.041
  },
  "market_baseline": {
    "top1_hit_rate": 0.518,
    "brier": 0.604
  }
}
```

### Acceptance

1. 5 个新 endpoint 全部加 pytest 覆盖（合成 fixture + 已知预期值，至少 1 个测试覆盖 `enough=false` 冷启动分支）。
2. `/insights/backtest` 在 0 配对、< min_samples 配对、> min_samples 配对三个状态下都不崩。
3. `model_hit_rate_pct`（来自 `/api/insights/leagues/:id`）与本 PRD 的 by-league endpoint 算出来的 hit rate 差异 < 0.5pp——双实现交叉校验。
4. E2E：积累 ≥ 30 个真实配对后，校准曲线 endpoint 必须返回非空 bins 列表。

### Phasing

- **Phase A（首 14 天 · 等数据）**：上线 endpoint + 占位页面（`enough=false` 状态），不挂主导航；让快照管线安静积累配对。
- **Phase B（30 天 / 500+ 配对）**：解锁主导航 Tab，发布"OddAlerts 模型表现快照"首份月报。
- **Phase C（90 天 / 多模型可比）**：与 #4 自有模型对接，多模型并排，PRD 升级到 v2。

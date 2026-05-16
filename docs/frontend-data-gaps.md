# 前端数据需求 vs OddAlerts API 缺口对照

> 基于 `Goalcast Prototype.html` 设计原型对照 `docs/oddalerts-api.md` 整理。
> 用于驱动后端补字段、决定原型模块去留。

---

## 总览

| 类别 | 数量 |
|---|---|
| ✅ 直接可用 | 11 项 |
| 🟡 需后端聚合 | 9 项 |
| ❌ 完全缺失 / 须自建 | 4 项 |
| 🔧 前端实现缺口（数据就绪未渲染）| 1 项 |
| ⚠️ 已知坑（文档列出） | 7 项 |

---

## ❌ 完全没有 — 必须自建

| # | 原型字段 | 出现位置 | API 状态 | 处理建议 | 优先级 |
|---|---|---|---|---|---|
| 1 | 球队主色 `home_color / away_color` | MatchCard 队标方块 / 详情页 Hero | 完全无 | 自建 `team_meta` 静态表 (`team_id → primary_color`)，前端 JSON 或后端缓存 | P0 |
| 2 | 球队 logo / 队徽图 | MatchCard / 详情页（原型用首字母方块兜底） | 完全无 | 同 #1，加 `badge_url`；或接 sportmonks/api-football 的 logo CDN | P1 |
| 3 | H2H 交锋历史 | 详情页"交锋历史"模块 | 无专用端点 | **已决定：从原型删除**。OddAlerts 不提供 H2H，后端聚合成本不划算。 | ~~P0~~ ✅ |
| 4 | 联赛 logo | Sidebar / MatchCard header | 无 logo（但 `/countries` 有 `code`） | 用 country code 做 emoji 国旗即可；联赛 logo 仅在必要时自托管 | P2 |

---

## 🟡 需要后端再加工 / 聚合

| # | 原型字段 | 出现位置 | API 现状 | 处理方案 | 优先级 |
|---|---|---|---|---|---|
| 5 | `form5` 近 5 场 W/D/L 字符串 | MatchCard / 详情页 | `/stats/season/:ID?last_x=5_overall` 拿到聚合，**不直接给 `"WDLWW"`** | 后端聚合：拉最近 5 场 fixture 结果，对照该队主客状态生成 W/D/L 字符串挂到 fixture summary | P0 |
| 6 | 球队短码 `home_abbr / away_abbr` | MatchCard 队标 | `/teams/find/:ID` 有 `short_code`，fixture summary 不含 | 后端 join 一次，把 `short_code` 拼到 fixture 响应上 | P0 |
| 7 | per-fixture predictability | MatchCard 徽章、详情页 | API 给的是 `competition_predictability`（按整个联赛标） | **决策**：① 沿用并改名 "联赛可预测度" ② 自己用模型置信度（top1 概率减熵）算 per-fixture 标签 | P1 决策 |
| 8 | ValueBet 的 `edge_pct / prob / odds` | 价值投注页 | `/value/upcoming` 文档字段列表**不含 edge**，需实测 raw 响应 | curl 一次确认字段；如缺，后端用 `edge = prob × odds − 1` 计算（`prob` 来自 `/predictions`，`odds` 来自 `/odds/history` closing） | P0 |
| 9 | 历史回测 `result / edge / ROI` | History 页 + Dashboard KPI | `/value/results` 含已结算 value bet；ROI 需自算 | 后端建 `bet_outcomes` 表：fixture FT 结果 × 原赔率 → P/L；按时间窗口聚合得到胜率/ROI | P1 |
| 10 | Dashboard 数据健康覆盖率 | 总览页右下卡片（赔率/阵容/模型/伤停 4 个进度条） | 无现成 API | 后端基于 fixture 的 `has_odds`、有无 `lineup`、有无 prediction record 等 flag 聚合；或**删除该卡片** | P2 决策 |
| 11 | Dashboard 7 日命中率 / 趋势 spark | KPI 卡 | 需后端持久化每日预测 vs FT 结果 | 后端每日跑回填任务，写入 `daily_metrics` 表 | P1 |
| 12 | 详情页"两队状态对比"（控球/胜率/净胜）| 详情页右下卡片 | `/stats/fixture/:ID` 含 won/drawn/lost/points/goals 全口径 ✅；但 **possession（控球率）不在已知 stats 字段中** | 用 stats 已有字段重做该卡片（净胜、点球率、主客胜率等），删除"控球" | P1 |
| 13 | fixture 透传 `home_rank / away_rank` | MatchCard "排名 #N" | 上游 `/fixtures/upcoming` 有 `home_position / away_position`（见 ✅ 区第 4 行），但 Goalcast 后端 `FixtureSummary` 当前未透传，前端 `TeamForm` 类型也没有 `rank` 字段 | 后端在 fixture 响应中直接带出 `home_position / away_position`，前端类型加 `home_rank / away_rank` 后 MatchCard 渲染 | P0 |

---

## 🔧 前端实现缺口（上游数据 + 后端字段都就绪，前端未渲染）

| # | 原型字段 | 出现位置 | 当前状态 | 处理建议 | 优先级 |
|---|---|---|---|---|---|
| F1 | 跌赔角标 `▼ 31%` | MatchCard 右上角 | `FixtureSummary.drop_flag.drop_percentage` 类型已定义，API 也返回；`MatchCard.tsx` 已取了 `dropPct` 但未渲染 | 在卡片头部加 `{dropPct != null && <span className="mc-drop">▼ {Math.round(dropPct)}%</span>}`，并补对应样式 | P0 |

---

## ✅ 直接可用 — 一对一映射

| 原型字段 | 来源端点 / 字段 |
|---|---|
| `home_team / away_team` | `/fixtures/upcoming` → `home_name / away_name` |
| `competition_name / country` | `/fixtures/upcoming` → `competition_name / competition_country` |
| `kickoff_utc` | `/fixtures/upcoming` → `unix / ko_human` |
| `home_rank / away_rank` | `/fixtures/upcoming` → `home_position / away_position` |
| `goals.hf/ha/af/aa` 总进失球 | `/stats/fixture/:ID` → `goals_for.total / goals_against.total` |
| `prediction_summary`（主胜/平/客胜/btts/o25）| `/predictions/generate/:ID` |
| 比分概率热图 cells | `/predictions/generate/:ID` → `scorelines{}` 或 `/correctScores` |
| 1x2 / AH / 大小球 等 45 个市场赔率 | `/odds/history/:ID?bookmakers=Pinnacle,Bet365` |
| 跌赔榜全部字段 | `/odds/dropping` —— 字段全对应原型 |
| 详情页"跌赔记录"时序 | `/odds/movement/:ID` 320 条带时间戳 |
| 比赛实时状态（比分/HT/补时）| `/fixtures/live` → `home_goals / away_goals / ht_score / elapsed` |

---

## ⚠️ 已知坑（落地前留意）

| # | 坑 | 影响 |
|---|---|---|
| 1 | `/fixtures/id` 字面路径返回空 | 别用，统一走 `/fixtures/upcoming` |
| 2 | `/odds/dropping` 的 `market_key=` 过滤不生效 | 用 `markets=<id>` 数字 |
| 3 | `/trends/:TREND` 名字严格驼峰大小写 | `homeWin` 对，`home_win` 错 |
| 4 | `/odds/multiple` 返回 HTML | 路径或参数与 Postman 有差异，需重新确认 |
| 5 | `/betslips` 仅支持 POST | GET 返回 405 |
| 6 | `/trends` 的 `duration` 参数触发 500 | 固定使用 5 Days |
| 7 | 无限速 header，但建议生产环境节流 ~150ms | 自己加节流 / 缓存层 |

---

## 推荐落地顺序

**第一周**（让原型对接真数据所需的最短路径）：

- [ ] 写 `team_meta` 静态表（id, short_code, primary_color）→ 解决 #1 #6
- [ ] 后端 `/fixtures/upcoming` 响应里 join `short_code` + 前端 form5 字符串 → 解决 #5 #6
- [ ] curl `/value/upcoming` 实测，决定 edge 字段是 API 给还是前端算 → 解决 #8
- [ ] 决定 #7（predictability 定义）、#10（数据健康）2 个产品决策

**已完成的决策**：~~#3 H2H~~ ✅删除、~~#12 控球率~~ ✅删除

**第二周**：

- [ ] 引入 `bet_outcomes` 表 + 每日回填任务 → 解决 #9 #11
- [ ] 详情页"两队状态对比"用 stats 字段重做 → 解决 #12

**可选 / 长期**：

- [ ] 队徽 CDN（#2）

---

## 原型字段 → API 端点 索引

```
MatchCard
├─ home/away_name, competition, kickoff       → /fixtures/upcoming
├─ home/away_position                         → /fixtures/upcoming
├─ short_code (queed as home/away_abbr)       → 🟡 后端 join /teams/find/:ID
├─ goals_for/against                          → /stats/fixture/:ID
├─ form5 "WDLWW"                              → 🟡 后端聚合最近 5 场结果
├─ home/away_color                            → ❌ 自建 team_meta
├─ predictability                             → /fixtures/upcoming (competition 级别)
├─ prediction_summary                         → /predictions/generate/:ID
├─ ft_result odds (pin/365)                   → /odds/history/:ID
├─ asian_handicap                             → /odds/history/:ID market=51
└─ drop_flag pct                              → /odds/dropping

MatchDetail（增量）
├─ scorelines heatmap                         → /predictions/generate/:ID
├─ AH 全线表                                  → /odds/history/:ID market=51 多 line
├─ 跌赔时序记录                               → /odds/movement/:ID
└─ 两队状态对比                               → /stats/fixture/:ID（仅留 stats 能拿的字段）

ValueBets
├─ selection / market                         → /value/upcoming
├─ edge / prob / odds                         → 🟡 实测 + 自算
└─ kickoff / teams                            → /value/upcoming

DroppingOdds
└─ 全部字段                                   → /odds/dropping ✅

History
├─ 已结算列表                                 → /value/results
├─ result W/L/D + edge + ROI                  → 🟡 后端 bet_outcomes 表
└─ 策略筛选                                   → /value/you/:ID

Dashboard
├─ 候选总数 / AI 覆盖率 / 高跌幅数            → 聚合 /fixtures/upcoming + /odds/dropping
├─ 7 日命中率 + spark                         → 🟡 后端 daily_metrics
├─ Top 5 跌赔                                 → /odds/dropping (top sort)
├─ Top 5 价值投注                             → /value/upcoming (top sort by edge)
└─ 数据健康                                   → 🟡 后端聚合 / 可砍
```

# 分析者洞察增强（时间序列 / 错定价 / 分歧告警 / 联赛统计 / H2H）

## Problem Statement

Goalcast 已经在采集大量高价值原始数据（70k 条赔率快照、bookmaker_odds 的 opening/current/peak 三段定价、predictions 含 simulations + scorelines），但 UI 只露出了一刀切的"当前跌幅 %""单点 edge"，对真正做赛前研究的投注者几乎没有"信号链路"——他们看不到赔率的运动方向、看不到自己关注的比赛何时出现可疑分歧、也看不到任何对手历史与联赛风格画像。结果：用户在 Goalcast 之外仍要打开 Pinnacle / FlashScore / SofaScore / 微信群多个 tab 拼信息。

## Evidence

- `backend/data/goalcast.db` 中 `odds_snapshots` 70,000 行（含 `drop_pct` 时间序列），但前端只展示当前点最大跌幅——99% 时间序列信息浪费。
- `backend/database.py` 的 `bookmaker_odds` 表存了 `opening / current / peak` 三段 + opening_at/current_at 时间戳，但前端仅消费 current 值，**CLV / 盘口漂移 / sharp vs square 全部读得到但未展示**。
- `fixtures` 表有 `h2h TEXT` 列但实测 **0 / 59,134 行** 有数据（OddAlerts 不填）——已有 schema 漏洞，可改为从 `fixtures` 表自身回溯历史交手填补。
- `predictions` 表每场存了 `simulations + home_win/draw/away_win` 计数；与当前赔率叉乘可立即算出**模型 vs 市场 implied probability 偏差**，但 Dashboard 仅展示按 edge_pct 过滤的"价值投注"（只看正 Edge 单选项），不揭示负 Edge / 双侧分歧 / 全市场扫描。
- `bookmaker_odds.market_id=51` 22,209 行 AH 多档赔率全谱已存，但 MatchDetail 的 AhLineTable 只是一张静态表，未呈现时间漂移、未做盘口主流档识别——真正 AH 玩家最重要的信息缺位。
- 投注用户行为观察：用户从 Goalcast 进入比赛详情后通常会立即跳出去查 H2H / xG / 联赛 standing——说明这些是核心研究路径，Goalcast 是断点。

## Proposed Solution

把"已采集 + 未展示"的数据按 5 个分析视角变成可视/可订阅的产品面，且让 sharp vs square 分歧自动告警，把用户从被动浏览变成主动等通知。所有功能复用现有数据库（**无新数据源依赖**）；告警系统复用 backend 已有的 APScheduler。

不引入 xG / 球员伤停 / 公开投注比例等需要新数据源的特性——那些留作 V2 与外部 feed 接入议题。

## Key Hypothesis

我们相信【时间序列 + 错定价扫描 + sharp/square 分歧告警 + 联赛画像 + H2H 自建】会把 Goalcast 从"赛前阅读工具"升级为"赛前决策工作台"。验收信号：

- 用户日活页深度（人均访问的 match detail 数）上升 ≥ 30%
- 在 24h 开赛比赛中，至少 60% 触发过至少 1 条 sharp/square 分歧告警（说明信号密度匹配赛事节奏）
- 告警 dismiss 率 < 30%（高 dismiss = 噪音过多，需重新调阈值）

## What We're NOT Building

- **xG / 球员伤停 / 公开投注比例** — 需要新数据源（Understat / API-Football injuries）；本期纯利用现有 OddAlerts + 内部聚合。
- **Email / SMS / Web Push 告警** — 仅站内铃铛 + inbox；推送通道 V2。
- **多渠道 sharp 定义**（Bet365 + Pinnacle 之外加 Betfair Exchange、SBOBet 等） — 本期只比较 Pinnacle (sharp) vs Bet365 (square) 两家。
- **机器学习的"异常检测"** — 阈值告警简单可解释，避免黑盒；ML 留 V2。
- **多市场告警**（不止 1x2 分歧，还有 AH / 大小球分歧） — 本期只 1x2 (market_id=6)；AH/总进球分歧留 V2。
- **付费层** — 全部功能对登录用户免费；监控成本未来可拆分。

## Success Metrics

| Metric | Target | How Measured |
|--------|--------|--------------|
| 时间序列图渲染覆盖率 | 100% 有 ≥ 5 个 odds_snapshots 点的 fixture 在详情页展示曲线 | 前端覆盖率脚本扫 MatchDetail 渲染分支 |
| Top 错定价列表 P50 列表大小（每日） | ≥ 20 项 | 后端聚合 endpoint 在工作日数据样本上的中位数 |
| Sharp/Square 分歧告警 false-positive 率 | < 30% （即 dismiss 比 < 30%） | `alerts.dismissed_at IS NOT NULL` 比例 |
| 告警延迟（事件发生→用户看到） | P95 < 6 min | scheduler job 间隔 5min + 前端 poll/SSE 1min |
| 联赛统计页加载耗时 | P95 < 800ms | 前端 PerformanceObserver |
| H2H 自建命中率（有 ≥ 3 场历史的对阵比例） | ≥ 70% | DB query: 同两队历史 fixture 计数分布 |

## Open Questions

- [ ] 告警阈值是否要按市场分别可配（1x2 / AH / 大小球各自一档）？默认本期全市场共用 5% delta，简化用户配置；用户反馈后再分拆。
- [ ] 告警是仅当事件发生时**单次**触发，还是阈值持续满足期间**反复**触发？默认单次（per fixture per market），并在持续满足超过 30 min 后允许第二次提醒。
- [ ] 时间序列图是否包含 AH 多档漂移？还是只画 1x2 主赔？默认 v1 只画 1x2 + drop_pct 双轴；AH 漂移留 Phase 1.1。
- [ ] 联赛统计页"模型命中率"按什么粒度回看？本赛季 vs 滚动 3 个月？默认本赛季（season_id）。
- [ ] H2H 自建的"同两队历史"是否要含国内 vs 国外杯赛混合？默认 across-competition，因为对阵历史本来就跨赛；加 toggle 让用户切。
- [ ] CLV 是否在本 PRD 中？逻辑上属于"错定价"家族，但需要用户自己输入"我下注时的赔率"。默认 V1.5 加：用户可标记"已下注"+ 系统自动算 CLV。

---

## Users & Context

**Primary User**
- **Who**：中级以上足球投注分析者，每天花 ≥ 30min 做赛前研究，关心 sharp/square 信号、模型偏差、盘口漂移；通常持有 Pinnacle + Bet365 + 至少一家亚盘账户。
- **Current behavior**：开 Goalcast 看一眼总览，然后跳到 Pinnacle 看实时赔率走势、跳到 FlashScore 看 H2H、再回 Goalcast 看模型。多 tab 来回切换。
- **Trigger**：早 / 午 / 比赛前 1h 三个时点重点扫赛；任何时段收到"赔率突变"信号会立即介入。
- **Success state**：进入 Goalcast 即可完成 95% 的赛前研究链路；偶尔的"sharp 分歧告警"让他能介入自己之前没关注的场次。

**Job to Be Done**
当我在做某场比赛的赛前研究时，我希望看到赔率从开盘到现在的完整走向 + sharp 与 square 是否分歧 + 这两队最近 5 次交手结果，这样我可以独立判断该场是否值得下注，而不必跳到 4 个外部站点。

**Non-Users**
- 纯靠 AI 推荐"跟单"的休闲用户：他们用 Dashboard 的 Top 5 推荐就够了，本期增强对他们不构成必备。
- 玩 prop bets / 球员个人盘的用户：本期 1x2 + AH 主线，不覆盖球员市场。

---

## Solution Detail

### Core Capabilities (MoSCoW)

| Priority | Capability | Rationale |
|----------|------------|-----------|
| Must | MatchDetail 加入跌赔 / 主赔率时间序列双轴图 | 70k 行数据当前 99% 被浪费；最直接的"signal in noise"展示 |
| Must | 新页 `/insights/mispricing`：Top N 错定价列表（含 negative edge） | 比 Value Bets 主动；揭示市场"高估"也展示"低估" |
| Must | Sharp/Square 分歧告警系统（铃铛 + inbox + dismiss） | 本 PRD 主诉求；让用户离开 app 也能被叫回 |
| Must | 告警阈值 / 开关配置页 | 否则信号噪音不可控 |
| Must | 新页 `/insights/leagues/:id`：联赛级统计（场均进球 / 主胜率 / 平局率 / 爆冷率 / 模型命中率） | 投注者选战场必备 |
| Must | MatchDetail 加 H2H 卡片（从 fixtures 自建） | OddAlerts 不填 h2h；自建用现有数据 |
| Should | AH 多档时间漂移图（Phase 1.1） | AH 玩家高频诉求；可在 Phase 1 同色谱里追加 |
| Should | 模型校准（Calibration）页：按可预测度档真实命中率 | 验证模型 vs 现实；建立信任 |
| Should | 比赛卡片新增"分歧标记"图标（已告警过的赛会在卡片上有标） | 视觉强化，避免完全依赖铃铛 |
| Could | 告警按市场细分（1x2 / AH / 总进球） | 留 V2 |
| Could | CLV 自动算（用户标记下注后跟踪到收盘） | 留 V1.5 |
| Won't | xG / 伤停 / 公众投注比例 | 新数据源，留 V2 |
| Won't | Email / SMS / Push | 站内即可解决；通道 V2 |

### MVP Scope

**绝对 MVP**：Phase 1（时间序列）+ Phase 3 含告警的最小版本（仅 1x2 市场、固定 5% 阈值、铃铛 + inbox）。这两件是 PRD 主诉求的核心；其他 Phase 2 / 4 / 5 可在主版本之后串行追加。

### User Flow

**主动研究路径**：
1. 用户进 MatchDetail
2. 上半屏看时间序列图（drop% + 主赔率双轴）→ 1 秒判断"市场是否在动"
3. 中部看 H2H 卡片（近 5 次交手 + 双方阵型）
4. 底部看模型 vs 市场对比

**被动告警路径**：
1. 用户外出 / 工作中，Goalcast tab 后台开着或不开
2. 后端 scheduler 每 5 min 扫"我的联赛 + 24h 内开赛 fixtures + 1x2 市场"，计算 Pinnacle/Bet365 implied prob delta
3. 命中阈值 → 写入 `alerts` 表
4. 用户下次打开 / 前端 poll 拿到新 alert → 顶栏铃铛 +N 红点 + 站内 toast
5. 用户点铃铛 → inbox 看每条告警的赔率详情 → 进 MatchDetail 决策
6. 用户 dismiss 不感兴趣的告警；告警在 fixture 开赛后自动 expire

**联赛筛选路径**（次要）：
1. 用户在 /matches 看到本周某联赛比赛特别多
2. 点 chip 区"📊 联赛统计"链接 → /insights/leagues/{id}
3. 看联赛画像（爆冷率 / 主胜率），决定要不要重点投这片
4. 返回 Matches，调整 chip 选择

---

## Technical Approach

**Feasibility**: HIGH

**Architecture Notes**

- **时间序列**：新 endpoint `GET /api/fixtures/:id/odds-timeseries` 返回 `[{recorded_at, drop_pct, ft_home, ft_draw, ft_away}, ...]`，从 `odds_snapshots` 直接 SELECT。前端 recharts / visx / 自建 SVG 都可——为保 bundle 小，建议用现有 ScorelineHeatmap 风格的 inline SVG。
- **错定价列表**：新 endpoint `GET /api/insights/mispricings?date=...&min_abs_edge=...`。计算公式：implied_prob = 1/odds（去 vig 后）→ delta = model_prob - implied_prob；按 |delta| 排序。
- **Sharp/Square 分歧检测**：
  - 每 5 min scheduled job 扫所有 pre-status 且 kickoff < 24h 的 fixtures
  - 对每场算 Pinnacle (bookmaker_id=1) 与 Bet365 (bookmaker_id=2) 的 1x2 (market_id=6) implied prob，取 max 偏差
  - 若 > 用户阈值且过去 30min 没为此 fixture 写过告警 → INSERT `alerts`
- **告警表**：
  ```sql
  CREATE TABLE alerts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    fixture_id   INTEGER NOT NULL REFERENCES fixtures(id),
    alert_type   TEXT NOT NULL,                -- 'sharp_square_divergence'
    payload      TEXT NOT NULL,                -- JSON: {market, pinnacle_home, bet365_home, delta_pct, ...}
    created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    dismissed_at TIMESTAMP,
    expires_at   TIMESTAMP NOT NULL             -- = fixture.kickoff_utc + 30min
  );
  CREATE INDEX idx_alerts_user_active ON alerts(user_id, dismissed_at, expires_at);

  CREATE TABLE user_alert_settings (
    user_id                INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    divergence_threshold   REAL NOT NULL DEFAULT 5.0,     -- delta % implied prob
    enabled                INTEGER NOT NULL DEFAULT 1
  );
  ```
- **告警传递**：前端 `useQuery(['alerts'], { refetchInterval: 60_000 })` 每分钟 poll；或后续接 SSE/WebSocket。Phase 3 用 poll 简化。
- **联赛统计页**：新 endpoint `GET /api/insights/leagues/:id?season_id=` 返回聚合：场均进球、主胜率、平局率、爆冷率（low predictability win by underdog）、模型命中率（finished fixtures）。
- **H2H 自建**：纯 SQL `SELECT * FROM fixtures WHERE (home_team_id=? AND away_team_id=?) OR (home_team_id=? AND away_team_id=?) AND status='FT' ORDER BY kickoff_utc DESC LIMIT 10`。
- **CSS**：复用现有 `themes.css` 设计系统；图表配色用 `--acc / --acc-2 / --neg` token。
- **i18n**：所有新文案走 Phase 4 的 messages.zh/en，避免再次硬编码。

**Technical Risks**

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| 5min 扫描频次产生大量 false-positive alerts（市场短时抖动） | H | 引入 30min 去重窗口；阈值默认 5% 而非 3% |
| odds_snapshots 时间序列在 70k 行规模查询慢 | M | 已有 `idx_odds_fixture` 索引；按 fixture_id 查询 < 50ms |
| 用户阈值设太低导致 alert spam | M | UI 阈值滑块下限设 2%；并在配置页显示"过去 7 天该阈值会触发多少 alerts"实时回算 |
| H2H 自建数据稀疏（两队从未交手） | M | 命中 0 时优雅降级"无历史交手记录"，不强占空间 |
| Calibration 计算需要 finished fixtures + winning_team 列 | L | `fixtures.winning_team` 列已存在；空值跳过 |
| 时间序列点过密视觉拥挤 | M | server-side 降采样：> 50 点时按时间窗口分桶取均值 |
| 告警表无限增长 | L | scheduled cleanup job 删除 expires_at < now - 7d 的行 |

---

## Implementation Phases

| # | Phase | Description | Status | Parallel | Depends | PRP Plan |
|---|-------|-------------|--------|----------|---------|----------|
| 1 | 跌赔时间序列图 | `/api/fixtures/:id/odds-timeseries` endpoint + MatchDetail 加图表卡片 | pending | with 2 | - | - |
| 2 | Top N 错定价列表 | `/api/insights/mispricings` endpoint + 新页 `/insights/mispricing` + Dashboard 卡片 link | pending | with 1 | - | - |
| 3 | Sharp/Square 分歧告警 | alerts + user_alert_settings 表；scheduled scan job；铃铛 UI；阈值配置页 | pending | - | - | - |
| 4 | 联赛级统计页 | `/api/insights/leagues/:id` endpoint + 新页 `/insights/leagues/:id` + Matches chip 区入口 | pending | with 5 | 1 | - |
| 5 | H2H 自建卡片 | MatchDetail 内嵌 `/api/fixtures/:id/h2h` endpoint + 卡片 | pending | with 4 | - | - |
| 6 | 验收 + i18n + 截图回归 | i18n key 补齐；scripts/check_i18n_coverage 跑绿；Playwright 5 新页 desktop+mobile 截图 | pending | - | 1, 2, 3, 4, 5 | - |

### Phase Details

**Phase 1: 跌赔时间序列图**
- **Goal**：详情页能看到 24h / 7d 赔率走势
- **Scope**：
  - 后端：`GET /api/fixtures/:id/odds-timeseries?window=24h|7d`；从 `odds_snapshots` SELECT；> 50 点时按时间窗口降采样
  - 前端：MatchDetail 新卡片 `<OddsTimeseries fixtureId={f.id} />`；内部 SVG 双轴 line + drop% 区域填充
  - 文案 key：`insights.timeseries.title / window.24h / window.7d / empty`
- **Success signal**：对 odds_snapshots 数据 ≥ 5 点的 fixture，详情页可见曲线；P95 < 500ms 渲染。

**Phase 2: Top N 错定价列表**
- **Goal**：用户在一个页面看到全市场最大错定价（含双向）
- **Scope**：
  - 后端：`GET /api/insights/mispricings?date=&min_abs_edge=&limit=`；计算 `implied = 1/odds_de_vigged`，取 |model_prob - implied| 排序
  - 前端：`/insights/mispricing` 新页；Dashboard 卡片"今日最大错定价 TOP 3"→ 跳转
  - 文案 key：`insights.mispricing.title / subtitle / col.model_prob / col.market_prob / col.delta / col.direction`
- **Success signal**：每日数据样本上 P50 ≥ 20 行；负 Edge 与正 Edge 都展示。

**Phase 3: Sharp/Square 分歧告警**
- **Goal**：用户能被动收到分歧信号
- **Scope**：
  - 后端：`alerts` + `user_alert_settings` 两表 DDL；`backend/services/alerts.py` 模块（扫描 + INSERT）；通过 APScheduler 注入 5min 间隔 job；endpoint `GET /api/me/alerts`（未 dismissed 且未 expired）/ `POST /api/me/alerts/:id/dismiss` / `GET|PUT /api/me/alert-settings`
  - 前端：顶栏 `<AlertsBell />`（react-query refetchInterval 60s）；下拉 inbox 列表；`/settings/alerts` 页（阈值滑块 + on/off）；新 toast `<AlertToast />` 在新告警进入时短暂提示
  - 文案 key：`alerts.title / alerts.empty / alerts.divergence.template / alerts.dismiss / alerts.settings.title / alerts.threshold`
- **Success signal**：
  - 8 项 pytest 覆盖：threshold 边界、30min 去重、expires_at 计算、dismiss、未登录访问 401、阈值更新生效
  - E2E：登录用户 → 设阈值 2% → 工作 fixture 数据下应至少看到 1 条告警 → 点 dismiss 后从 bell 计数消失

**Phase 4: 联赛级统计页**
- **Goal**：用户在联赛维度做战场选择
- **Scope**：
  - 后端：`GET /api/insights/leagues/:id?season_id=` 返回 `{matches_played, avg_goals, home_win_pct, draw_pct, away_win_pct, upset_pct, model_hit_rate, top_predictability_pct}`
  - 前端：`/insights/leagues/:id` 新页；Matches chip 区右侧加"📊 联赛"小图标按钮 → 跳此页
  - 文案 key：`insights.league.*`
- **Success signal**：22 主流联赛全部能渲染；P95 < 800ms。

**Phase 5: H2H 自建卡片**
- **Goal**：详情页有近 N 场对阵历史，无需跳外站
- **Scope**：
  - 后端：`GET /api/fixtures/:id/h2h?limit=10` 从 fixtures 表反查（两队任意主客方向 + status='FT'）
  - 前端：MatchDetail 加 `<H2HCard />` 卡片：每行 = 1 场过去比赛（日期 / 联赛 / 比分 / 主客方向）
  - 文案 key：`insights.h2h.title / insights.h2h.empty / insights.h2h.row.score`
- **Success signal**：≥ 70% 的 fixtures 至少有 3 场历史对阵。

**Phase 6: 验收 + i18n + 截图回归**
- **Goal**：5 个新功能不破坏现有 + 全双语 + 自动截图核验
- **Scope**：
  - `scripts/check_i18n_coverage.py` 通过（所有新 key 在 zh + en JSON 中）
  - `frontend/tests/e2e/insights.spec.ts` 新增 5 屏 mobile + desktop 截图
  - 后端 pytest 全套跑绿（新增 Phase 3 8 用例 + Phase 1/2/4/5 各自基础测试）
- **Success signal**：CI `acceptance` + `e2e` 两 job 全绿。

### Parallelism Notes

- Phase 1 ↔ Phase 2 完全独立（不同 endpoint，不同前端页），可并行。
- Phase 3 独立但工作量最大（告警子系统），建议单独节奏推。
- Phase 4 ↔ Phase 5 都依赖 Phase 1 的 i18n 文案约定（避免 key collision），但本身互不依赖，可并行。
- Phase 6 必须最后跑。

---

## Decisions Log

| Decision | Choice | Alternatives | Rationale |
|----------|--------|--------------|-----------|
| 告警通道 | 站内铃铛 + inbox | Email / SMS / Web Push | 启动成本最低；Email 涉及 SMTP；Web Push 需要 service worker 跨域复杂；先验证产品价值再加通道 |
| 默认告警阈值 | 5% implied prob delta | 3% / 7% | Pinnacle vs Bet365 同盘正常波动 < 3%；> 7% 太罕见；5% 是观察值的次罕见区间 |
| 告警去重窗口 | 30 min per (fixture, market) | 永久去重 / 不去重 | 永久会漏掉真正的二次信号；不去重会 spam；30 min 平衡 |
| 告警范围 | 我的联赛 ∩ 24h 内 pre fixtures | 全联赛 / 7d 内 | 与 Phase 3 我的联赛权威性一致；24h 是赛前研究黄金窗 |
| 时间序列降采样 | server-side 时间窗口分桶取均值 | client-side / no downsampling | server 控制网络成本；client 计算 50 点 vs 1000 点 React 性能差异显著 |
| 错定价 Edge 计算 | `model_prob - implied_prob_devigged` | `(model_prob × odds) - 1` (传统 Edge) | 去 vig 后的对比对盘口公平；传统 Edge 包含 vig 噪声 |
| H2H 数据源 | 本仓库 `fixtures` 表自建 | 接 OddAlerts 新 endpoint / SofaScore scrape | 零外部依赖；数据已有；不会有授权或费率问题 |
| Bell poll 间隔 | 60 s | 30 s / WebSocket | 60s 是新告警敏感度（< P95 6min target）与服务器 load 的平衡点 |
| 联赛统计页路由 | `/insights/leagues/:id` | `/matches?stats=1` | 独立路由便于直接收藏 / 分享 |
| 校准与错定价分页 | 校准留 Should（暂不本期） | 与错定价同期 | 错定价是 forward-looking（决策用），校准是 backward-looking（信任建立）；两者价值/紧急度不同，分期发布 |

---

## Research Summary

**Market Context**

- 同类产品分类：
  - **真正面向 sharp 的工具**（OddsAssist, BetBurger, RebelBetting）—— 主打跨盘套利与 sharp/square 分歧告警，月费 €50+；本 PRD 等于免费版的 sharp 分歧告警子集。
  - **大众体育数据**（FlashScore, SofaScore）—— 强项是 H2H 与联赛 standings；这正是 Goalcast Phase 4/5 借鉴方向。
  - **Pinnacle 内嵌工具** —— 时间序列图是其招牌；我们做的是 Pinnacle + 其他 book 的对照版本，附加自有模型。
- 用户洞察（社区观察）：sharp 用户对告警的容忍度极低（30% dismiss 就会卸载），决定我们把"先小批量准确告警"放在"早高密度告警"之上。

**Technical Context**

- Goalcast 当前依赖：FastAPI + SQLite + APScheduler + React + Vite + zustand + react-query。本 PRD 不引入任何新依赖。
- 时间序列图 SVG vs 第三方库（recharts/visx）：recharts ~ +180kb gzipped；自建 SVG ~ +3kb。倾向自建。
- APScheduler 现有 job：`backend/services/sync.py:scheduler` 已注册数据同步任务；alerts scan job 加入同 scheduler，5min 间隔与现有 sync 节奏一致。
- 告警 poll：react-query `refetchInterval` 已在多处使用（不引入新模式）。
- 估算工作量分布：Phase 1（图）~ 0.5 周 / Phase 2（错定价）~ 0.5 周 / Phase 3（告警子系统）~ 2 周 / Phase 4（联赛统计）~ 1 周 / Phase 5（H2H）~ 0.5 周 / Phase 6（验收）~ 0.5 周。总约 5 周。

---

*Generated: 2026-05-17*
*Status: DRAFT - 待评审*

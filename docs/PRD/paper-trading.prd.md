# 模拟投注：把模型相对市场的 edge 翻译成可量化的虚拟 ROI

> 路线对应：roadmap 之外的桥梁项，**承接 #5（回测）**——回测证明"模型概率准"，本 PRD 证明"按本站信号下单能赢"。
> 也是 #1（会员分层）的差异化付费钩子来源：一个公开、可审计、自动跟单的"信号账户"长期 ROI 曲线。

## Problem Statement

#5 回测 PRD 解决了"OddAlerts 模型预测概率有多准"的知识层问题，但**准不等于赚**：一个模型完全可能 hit rate 高、Brier 低，但赔率市场已经把这种准确性反映在 vig 后的价格里——用户和 Goalcast 自己都无法从"准"反推到"长期价值"。

要回答"依据本站数据下单能否长期赚钱"，必须有一个**对外可审计、对内可校准**的虚拟下注账本：把 #5 输出的"模型 vs 市场基线"差值在哪些子集为正 → 自动按固定 stake 下单 → 按真实赛果结算 → 跟踪 ROI/Sharpe/CLV 曲线。**这才是商业层证据**，而 #5 是它的必要前提。

## Evidence

- **市场基线已在 #5 中算**：`backtest-accuracy.prd.md` 的 market_baseline 字段对 `historical_odds.waypoint='kickoff', bookmaker_id=1, market_id=6` 做 de-vig，所以"模型 prob − 市场 implied prob"这个 edge 信号每天免费产出。
- **错定价雏形已上线**：`/api/insights/mispricings`（commit `ba27fab`）按 fixture 输出 |Δ| 最大的 selection，但**只展示**信号，不**结算**——下一步天然是"跟单 + 结算"。
- **冷启动同 #5**：`historical_predictions × FT` 配对当前=0；任何"信号 → 真实结果"的回路都受同一时间窗约束，无法靠回填补救。
- **没有用户行为画像数据**：当前数据库没有任何"用户下注 / 关注 / 跟单"的痕迹表，#3"自有数据"目前完全是聚合层数据，缺一类"用户决策"维度——本 PRD 同时填补这块。
- **道德 / 合规风险存在**：Goalcast 当前定位"研究工作台"，没有任何下注引导。模拟投注 UX 若靠近庄家界面，会侵蚀这一定位。

## Proposed Solution

新增 `/insights/paper-trading` 页面 + `/api/paper-trading/*` endpoint + 新表 `simulated_bets`，承载两类账户：

1. **House Book（系统信号账户）—— Must**
   每天扫描 `/api/insights/mispricings` 中 `|Δ| ≥ 阈值` 且 `delta_pct > 0`（模型相对市场正 edge）的 selection，**自动**生成虚拟下单：固定 1 unit stake、entry_odds = 当前 Pinnacle 1X2、entry_at = 信号触发时刻。FT 后按真实结果结算 P&L。**这是对外承诺"按本站数据下单能赢"的核心证据**——0 用户也能从 day 1 跑。

2. **Personal Book（用户手动账户）—— Should**
   登录用户在 MatchDetail / Mispricings 页一键"标记我下了 X 单"，stake 单位、selection、entry odds 由用户填或从当前界面继承。FT 后同样自动结算。**目标：用户个人 ROI 曲线 + 行为画像（供 #3 / #1 后续使用）**。

两类账户共用同一张 `simulated_bets` 表（`book_type` 区分），共用同一套结算逻辑，UI 上同页并列展示——左侧 House Book 全站累计曲线，右侧 Personal Book 用户个人曲线。

## Key Hypothesis

我们相信【一个自动跟单 #5 信号、按真实结果结算的公开账户】会把 Goalcast 从"展示数据"升级为"可审计的预测平台"。验收信号：

- House Book 上线 90 天（足够 ≥ 500 个已结算虚拟单）后，**累计 ROI ≥ +2%（按 unit 计）**——这是"本站信号有 edge"的最低门槛；< 0% 提示信号体系需要重新设计而非继续上线。
- 登录用户中 ≥ 20% 在 30 天内创建过至少 1 笔 Personal Book 虚拟单（说明粘性钩子成立）。
- House Book ROI 曲线 30 天 max drawdown < 25%（控制过山车感，避免用户因短期亏损流失）。

## What We're NOT Building

- **真实下注 / 真实账户对接 / 出入金 / 任何金钱流转** —— 永不做。bankroll 永远 "unit"，永不挂 ¥/$ 符号；UI 永不出现"切到真实账户""下注送钱"等引导。
- **AH 半赢半输 / push / cash out / 撤单 / 推迟比赛 / 改判结算** —— MVP 只支持 1X2 全有全无（home/draw/away，全赢或全输）；AH / O/U 留 V1.5；cash out / 撤单 永不做。
- **Kelly / 凯利动态 stake** —— V1 固定 1 unit stake；动态 stake 留 V1.5（含 stake 策略 A/B 测试）。
- **复杂订单组合 / 串关 / 系统注** —— MVP 单注；串关永不做（与"评估 edge"目标不一致）。
- **跨用户排行榜 / 跟单别人 / 社区** —— 与"研究工作台"定位不符，永不做。
- **退化为赌博练习场的 UX** —— 没有"在线 X 个人下注""今日热门跟单""+888 unit 战绩"等赌博 app 元素。
- **跨模型并排账户**（同一比赛"模型 A 的 House Book" vs "模型 B 的 House Book"）—— 等 #4 自有模型上线后才有意义，V1 单模型。

## Success Metrics

| Metric | Target | How Measured |
|--------|--------|--------------|
| House Book 90 天累计 ROI | ≥ +2% | (sum pnl_units) / (sum stake_units) |
| House Book ROI 95% bootstrap CI 下界 | > 0% | 后端 bootstrap 1000 次 |
| 信号 → 结算延迟 | P95 < 1h（FT 入库后） | scheduler tick + 结算 worker |
| 登录用户 30d Personal Book 渗透率 | ≥ 20% | DB query |
| "一键下单" 点击 → 成交确认 | ≤ 3 次点击 | E2E recording |
| 误结算率（已结算但需要回滚的单） | < 0.5% | 错误日志 |

## Open Questions

- [ ] **House Book 的信号来源是什么？** Option A: 直接用 mispricings endpoint 的 `delta_pct > 阈值` 列表（简单、即用）。Option B: 等 #5 backtest 输出"模型在 X 联赛胜率比市场高 N%"再下单（更精准但要等 #5 上线 + 数据攒够）。建议 V1 用 A 攒数据，V1.5 切到 B。
- [ ] **House Book stake 阈值** delta_pct 多少才下单？3% / 5% / 7%？建议 V1 同时跑三档（三个独立 book_type："house_3pct"/"house_5pct"/"house_7pct"），90 天后看哪档 ROI 最稳，淘汰其它。
- [ ] **结算 odds 用什么？** entry_odds 锁在信号触发时刻（CLV 计算需要）；但结算赔付按 entry_odds 还是按 closing odds？建议按 entry_odds（这才是"我下注时承诺的赔付"），CLV 单独算并显示。
- [ ] **Personal Book 是否允许"模拟撤单 / 修改 stake"？** 不允许——一旦录入即锁定，否则 ROI 曲线可篡改不可审计。
- [ ] **公开 House Book 还是只对登录用户开放？** 建议公开（无需登录即可看），因为"对外可审计"是核心价值；Personal Book 必登录。
- [ ] **bankroll 起点是多少 unit？** 1000 unit 起步（够分散 500+ 注），每注 1 unit stake；爆仓（< 0）后按 90 天累计 ROI 报告，不重置——避免"假装永远在赚"。

---

## Users & Context

**Primary Users（双向）**

- **External**：投注分析者，对 Goalcast 给的数字将信将疑。看到 House Book 90 天 ROI +3.4%（CI 下界 +0.8%）后，愿意把 Goalcast 当主要决策入口；自己用 Personal Book 跟踪个人决策表现。
- **Internal**：Goalcast 团队自己。House Book ROI 是判断"我们的信号体系到底有没有价值"的唯一硬指标——如果跑 90 天 ROI < 0，整个 #3 / #4 / #5 的产品线需要根本性重构。

**Job to Be Done**
- 用户视角：当我考虑信任 Goalcast 的预测做实战投注时，我希望看到一个公开、自动、按本站信号下单的虚拟账户长期 ROI 曲线——这样我才能判断这个网站给我的信号是不是真有 edge。
- 团队视角：当我们想知道"我们做的事到底对不对"时，我希望有一个对内公开、对外审计的账本，让真实赛果给我们打分——而不是靠模型自评。

**Non-Users**
- 不下注的研究/兴趣用户：House Book 公开曲线对他们仍有阅读价值（验证平台可信度），但不会主动用 Personal Book。
- 高频高额的职业玩家：单位 stake 1 unit 的固定 size 设计对他们不适用——他们要 Kelly 动态 stake，本期不覆盖。

---

## Solution Detail

### Capabilities (MoSCoW)

| Priority | Capability | Rationale |
|----------|------------|-----------|
| Must | 新表 `simulated_bets` + 索引 `(book_type, settled_at)` 与 `(user_id, settled_at)` | 数据基础 |
| Must | 后端：APScheduler job 每 30 分钟扫 mispricings、对 `delta_pct > 阈值 AND status='NS' AND kickoff_utc > now+1h` 的 selection 生成 House Book 虚拟单 | 信号 → 下单 |
| Must | 后端：FT 入库后的结算 worker（监听 fixtures.status 转 FT）→ 按 entry_odds 计 pnl_units、写回 `simulated_bets` | 下单 → 结算 |
| Must | 后端：`GET /api/paper-trading/house?book_type=&since=` 返回累计 ROI 曲线、当前 bankroll、95% bootstrap CI、CLV 平均、max drawdown | 主页面数据源 |
| Must | 后端：`GET /api/paper-trading/personal`（含 auth）返回当前用户 Personal Book 同结构数据 | 个人曲线 |
| Must | 后端：`POST /api/paper-trading/personal/bets` 接受用户手动下单（fixture_id + selection + stake_units + entry_odds 可继承当前 mispricings 行） | 一键下单入口 |
| Must | 前端：`/insights/paper-trading` 页面 — 左 House Book 公开曲线，右 Personal Book（未登录态显示登录引导）| 主交付 |
| Must | MatchDetail / Mispricings 行加 "📒 模拟下单" 浮层按钮，≤ 3 次点击成交 | 粘性 + 入口密度 |
| Must | 全站 footer 与下单确认页强免责："虚拟单位，不构成投注建议" | 合规护栏 |
| Must | 冷启动占位：House Book 0 已结算时显示"信号账户运行中，第一批结算预计在 N 天"进度条 | 不挂死数据 |
| Should | Personal Book 行为画像（联赛偏好 / 盘口偏好 / 平赔大小直方图） | 喂 #3 自有数据 + 为 #1 付费分层做用户画像准备 |
| Should | House Book 多档并行（3% / 5% / 7% delta 阈值同时跑）90 天后做淘汰 | 信号阈值自适应实验 |
| Should | CLV（closing line value）单独栏：entry_odds vs kickoff 时市场 closing odds 的盈亏 | sharp 玩家最关心的长期指标 |
| Won't (V1) | AH / O/U / 进球数 / 角球 / 任何 1X2 之外的盘口 | V1.5 |
| Won't (V1) | Kelly / 动态 stake | V1.5 |
| Won't (V1) | 真实账户对接 / 跨用户排行 / 跟单别人 / 串关 | 永不做 |
| Won't (V1) | cash out / 撤单 / 修改已下单 | 永不做（破坏审计） |

### Data Flow

```
[每 30 min] APScheduler →
  /api/insights/mispricings (delta_pct > 阈值, status='NS', kickoff > now+1h)
    → 对每条 selection 写 simulated_bets(book_type='house_5pct', stake=1,
        entry_odds=当前 Pinnacle odds, entry_at=now, outcome=NULL)
    → 去重：(book_type, fixture_id, selection, user_id) UNIQUE

[fixtures.status FT 转换] sync 时触发 →
  扫描 simulated_bets WHERE outcome IS NULL AND fixture_id IN (新结算的)
    → 按 fixtures.score_home/away 推 H/D/A
    → 命中：pnl_units = stake * (entry_odds - 1)；未中：pnl_units = -stake
    → UPDATE simulated_bets SET outcome, pnl_units, settled_at = now

[/api/paper-trading/house]
  → 累计聚合：sum(pnl_units), running bankroll, bootstrap CI, CLV 平均, max drawdown
  → 缓存 5 min LRU
```

### `simulated_bets` Schema

```sql
CREATE TABLE simulated_bets (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  book_type       TEXT    NOT NULL,        -- 'house_3pct'/'house_5pct'/'house_7pct'/'personal'
  user_id         INTEGER,                  -- NULL for house_*
  fixture_id      INTEGER NOT NULL REFERENCES fixtures(id),
  selection       TEXT    NOT NULL,         -- 'home'/'draw'/'away'
  stake_units     REAL    NOT NULL,         -- V1 固定 1.0
  entry_odds      REAL    NOT NULL,         -- 下单时 Pinnacle 1X2 odds
  entry_at        TIMESTAMP NOT NULL,
  signal_source   TEXT,                     -- 'mispricings_delta_5pct'/'manual' 等
  outcome         TEXT,                     -- NULL until settled; then 'win'/'loss'
  pnl_units       REAL,                     -- NULL until settled
  settled_at      TIMESTAMP,
  closing_odds    REAL,                     -- snapshot for CLV
  UNIQUE (book_type, fixture_id, selection, user_id)
);
CREATE INDEX idx_sb_book_settled ON simulated_bets(book_type, settled_at);
CREATE INDEX idx_sb_user_settled ON simulated_bets(user_id, settled_at);
CREATE INDEX idx_sb_fixture_pending ON simulated_bets(fixture_id) WHERE outcome IS NULL;
```

### Response 字段契约（V1 House Book 示例）

```json
{
  "book_type": "house_5pct",
  "since": "2026-05-18T00:00:00Z",
  "bets_settled": 312,
  "bets_pending": 47,
  "bankroll": { "start": 1000.0, "current": 1034.2, "peak": 1062.1, "trough": 988.7 },
  "metrics": {
    "roi_pct": 3.42,
    "roi_ci95": [0.8, 6.1],
    "win_rate": 0.487,
    "avg_clv_pct": 1.2,
    "max_drawdown_pct": -7.3,
    "sharpe_30d": 0.84
  },
  "timeseries": [
    { "settled_at": "2026-05-19T22:00:00Z", "bankroll": 1001.4 },
    { "settled_at": "2026-05-19T22:30:00Z", "bankroll": 1003.1 }
  ]
}
```

### Acceptance

1. 新表 + 5 个 endpoint 全部 pytest 覆盖，含 House Book 自动下单去重、FT 结算正确性（合成"赔率 ×N stake 1 命中" 与"未中 -1"）、CLV 计算、bootstrap CI、冷启动 `enough=false` 分支。
2. `/insights/paper-trading` 在 0 已结算 / < 100 已结算 / > 100 已结算 三态都不崩。
3. 误结算回归测试：人为 INSERT 一个未中单后修改 fixtures.score_home/away → 结算 worker 必须能识别并重算（或显式拒绝重算，二选一并 documented）。
4. E2E：登录态下从 Mispricings 行点击 "📒 模拟下单" → ≤ 3 次点击完成下单 → Personal Book 立即出现 pending 记录。
5. 合规护栏 E2E：全站 grep 不到 "¥" "$" "投注建议" "切换到真实账户" 等违规字串。

### Phasing

- **Phase A（首 14 天 · 等 FT 配对）**：上线 schema + House Book 自动下单 scheduler + endpoint + 占位页面（`bets_settled=0` 状态）。Personal Book 入口先不挂。
- **Phase B（30 天 / 100+ 已结算）**：解锁主导航 Tab，发布"House Book 第一份 30 天审计快照"。Personal Book 一键下单上线。
- **Phase C（90 天 / 500+ 已结算）**：判读 House Book ROI 是否达到 +2% 门槛 / CI 下界 > 0；达到 → 进入"#1 会员分层"讨论（House Book 公开、Personal Book 高级指标付费）；未达到 → 暂停 #1，回头修信号体系。
- **Phase D（与 #4 联动）**：自有模型上线后，House Book 增加 `house_owner_model` 子账户，两个模型 ROI 曲线并排。

# 信号决策旅程:理解 → 区分 → 回测 → 验证

> 路线对应:**承接 `proprietary-signals.prd.md`**(已建立的 `GS-*` 命名空间 + 计算契约)、
> **`paper-trading.prd.md`**(行 63 已声明 "V1.5 切到可配置 subscription")、
> **`backtest-accuracy.prd.md`**(模型层回测;本 PRD 在它之上加"信号层回测")。
> 也是 #1 会员分层的关键 UX 抓手 —— 用户必须先**理解** → **区分** → **回测** → **验证**,
> 才会订阅 / 付费。

## Problem Statement

随着 `GS-*` 信号集陆续上线(commit `dda0973` 上线 `GS-KEN-HT-EV`,第 4 条;
`proprietary-signals.prd.md` 还规划了 `GS-OddsDrop / GS-Predictability / GS-H2HForm`),
信号体系的**计算契约层**已经完备,但**用户决策旅程的四个阶段**全都缺工具:

1. **理解阶段:无法回答"这个信号是什么 / 怎么算 / 何时失效"。** `Signals.tsx` 只显示
   `signal_type / strength / 一行 detail`,没有方法论、没有归一化口径、没有失效情形。
   用户看到 `Mispricing · home · +15.0%` 不知道:它是模型 prob 还是市场 implied?+15%
   是怎么算的?strength 100% 的门槛是什么? **决策摩擦巨大,新用户首次访问即流失。**
2. **区分阶段:无法回答"信号 A 和信号 B 的差异是什么 / 我该挑哪个"。** 当前 4 条信号
   在 `Signals.tsx` 共享一张表,只有 `signal_type` 名字不同,detail 列各自一行,
   **没有任何并列对比**。用户无法快速判断"GS-LineMove 和 GS-SharpSquare 是不是其实在
   做同一件事"。
3. **回测阶段:无法回答"过去 30 天用这个信号下单,ROI 多少"。** `backtest-accuracy.prd.md`
   做的是**模型层**回测(模型概率 vs 实际结果);**信号层**回测(信号触发 → 假设下单 →
   按 FT 结算)目前 0 实现。新信号上线时,House Book 0 已结算,**冷启动期完全无法判断
   是否值得跟单**。
4. **验证阶段:模拟盘 House Book 信号源被硬编码为 `GS-Mispricing`**(`paper-trading.prd.md`
   line 119 + line 63 已点名 V1.5 要改),用户无法 (a) 看到当前在跑的信号到底是哪几条;
   (b) 用同样起始资金**并行**比较多条信号长期 ROI 曲线;(c) 把某条信号 fork 到自己账户
   改参数 / 改比赛范围。

此外:**4 个阶段都没有"比赛范围"的概念**。当前 `/api/signals/*` 永远扫全市场,**不**尊重
用户 `user_competition_prefs`(`services/alerts.py` 已经在按用户联赛过滤了,但 signals 没
跟上)。有些用户只关心英超 + 西甲,展示全市场信号是噪音;有些用户想看全市场发现机会,
强制按个人偏好过滤又会漏掉。**两种模式必须共存且用户可切换。**

## Evidence

- **直接观察**(commit `dda0973`):`frontend/src/pages/Signals.tsx` 共 189 行,没有任何
  信号方法论文案,detail 渲染对 4 个 signal_type 写死(`switch` block),新信号要改前端 +
  i18n + 渲染逻辑三处。
- **PRD 间已有的呼应**:`proprietary-signals.prd.md` line 60 `"GS-Mispricing 当 Δ>5% 时
  主胜命中率多少 / Brier 多少 —— 这是把信号本身作为评估对象"` —— 信号层回测的
  正当性已经在那篇 PRD 里被反复提及但**未实现**。
- **`alerts` 已经按用户联赛偏好过滤**(`services/alerts.py:91`),但 `signals` 没有 —— 这是
  现状里**不一致的设计**,本 PRD 要统一。
- **`ui-explainability-tooltips.prd.md` 不覆盖**信号方法论(它只处理图例 hover)。
  本 PRD 与它**共享 glossary 但不重叠**。
- **冷启动证据**:`GS-KEN-HT-EV` 上线 5 天(commit `dda0973`),`simulated_bets WHERE
  signal_type='GS-KEN-HT-EV'` 必然为 0(snapshot 还没跑过有效 HT 数据的 waypoint);
  即使未来跑起来,House Book 累计 ≥ 200 已结算需要 ~30 天 —— **没有回测工具,
  用户在这 30 天里无法判断这条信号是否值得跟**。

## Proposed Solution

围绕用户的**四阶段决策旅程**组织,每个阶段映射到一个具体表面 + 一个数据契约:

```
┌─────────────────────────────────────────────────────────────────────┐
│ 1. 理解  /insights/signals 左侧 catalog + 右侧方法论 panel              │
│         数据:signal_methodology(signal_type, locale, body_md)         │
│              BaseSignal.{description, output_schema, strength_formula, │
│                          failure_modes}                                │
├─────────────────────────────────────────────────────────────────────┤
│ 2. 区分  catalog 顶部"对比模式"切换 → 多条信号并列表 (description /     │
│         strength_formula / 近 7d ROI / 近 7d hit_rate / 触发数)         │
│         数据:同上 + 实时从 signals_snapshot 聚合统计                   │
├─────────────────────────────────────────────────────────────────────┤
│ 3. 回测  catalog 卡片 + book 详情页都有 "回测" 按钮 → 选时间窗 + 比赛范围 │
│         → 立即返回 ROI / hit_rate / drawdown / equity curve            │
│         数据:复用 signals_snapshot × historical_odds × fixtures(FT 结果)│
│              无需新表;输出落 simulated_bets_backtest(separate from live)│
├─────────────────────────────────────────────────────────────────────┤
│ 4. 验证  /insights/paper-trading 主图 = 多曲线对比图,每个 book 一条曲线 │
│         House Books(N 条,每条信号一个)+ Personal Books(用户 fork)    │
│         数据:simulated_books(扩展 signal_type/version/conditions/      │
│                              starting_units/match_scope)              │
│              simulated_bets(沿用,加 book_id)                          │
└─────────────────────────────────────────────────────────────────────┘

跨阶段共享概念:
  match_scope: 'all' | 'my_leagues'
    — Catalog & Backtest & Book 都接受这个参数,意义一致(用 user_competition_prefs 过滤)
```

**核心模型还是 "信号即账户":** 每条 `REGISTERED` 信号自动有一个 House Book,起始资金
100 units,独立记账。但本 PRD 把它**放在第 4 阶段**(验证),不再当作整个 PRD 的核心 —— 因为
没有前面 3 个阶段,用户根本不知道为什么要看那张 ROI 多曲线对比图。

## Key Hypothesis

我们相信【把信号决策旅程的 4 个阶段全部铺平 + 用户可选"全市场 / 我的联赛"】会**显著
提高信号→模拟下单→会员转化的漏斗转化率**,验收信号:

- **理解阶段**:进入 `/insights/signals` 的用户中,≥ 60% 在 30 天内点击过任意信号的"方法论"
  展开(埋点 `signals.catalog.expand`)。
- **区分阶段**:catalog 切到"对比模式"的 session 比例 ≥ 25%(埋点 `signals.catalog.compare`)。
- **回测阶段**:发起 ≥ 1 次回测的登录用户 / 全部登录用户 ≥ 40%(埋点 `signals.backtest.run`)。
- **验证阶段(forward)**:`House-GS-*` 之间长期 ROI 差距 ≥ 2pp 的信号对 / 全部信号对
  ≥ 30%(只有真有 alpha 差异,验证才有意义)。
- **验证阶段(historical)**:每条 `REGISTERED` 信号至少有 1 次成功的回测运行,且回测产出的
  累计 ROI 与同期 House Book forward ROI 偏差 < 1pp(回测可信度)。
- **House Book 行为平迁**:`House-GS-Mispricing` V1.5 上线后 14 天入库速率与上线前 baseline
  ±5% 内。

## What We're NOT Building

- **不**做信号"组合"DSL(`GS-Mispricing AND GS-LineMove same direction`) —— V1.5 是
  "信号即账户,各跑各的",**组合靠用户在图上肉眼对比**;复合条件留 V2。
- **不**给方法论文案做富文本编辑器 —— 写入 DB 是手维护 markdown,前端 markdown-it 渲染。
- **不**重做 alerts 告警系统 —— 本 PRD 完成后单写一份 `alerts-subscription-merge.prd.md`
  把 alerts 退化为 books 上的一个 channel。
- **不**重写 `Signals.tsx` 的 SQL 层 —— 沿用 `/api/signals/active` 和 `/api/signals/:type`,
  catalog 是新增 endpoint 而非替代既有。
- **不**对 scope='member' 的方法论加密 —— **方法论永远公开**(Q3 在 Open Questions 论证)。
- **不**做 Kelly / 动态 stake —— V2 / 独立 PRD。
- **不**支持回测时改"信号公式 / version" —— 回测只接受**当前生效的 signal_version**,改
  公式要重跑 snapshot 后再回测。
- **不**做信号交叉回测("如果 GS-Mispricing AND GS-LineMove 同时触发再下") —— 与
  "不做组合 DSL"同一原因。

## Success Metrics

| Metric | Target | How Measured |
|---|---|---|
| 注册信号 catalog 覆盖率 | `REGISTERED` 100% 有非空 description + methodology(zh + en) | `signal_methodology` JOIN `REGISTERED`,CI check |
| 方法论 panel 展开率 | ≥ 60% session 至少展开 1 条 | 埋点 `signals.catalog.expand` |
| 对比模式使用率 | ≥ 25% session 切到对比模式 | 埋点 `signals.catalog.compare` |
| 回测使用率 | ≥ 40% 登录用户 30 天内发起 ≥ 1 次回测 | 埋点 `signals.backtest.run` |
| 回测 ↔ forward 一致性 | 同窗口内回测 ROI 与 forward ROI 偏差 < 1pp | 自动对账脚本 |
| House Books ROI 区分度 | 互相 ROI 差距 ≥ 2pp 的信号对 / 全部 ≥ 30% | `simulated_books` × `simulated_bets` 聚合 |
| Personal Book fork 采纳 | 登录用户 30 天内 ≥ 30% fork 过 ≥ 1 个 | `simulated_books WHERE user_id > 0` |
| 比赛范围切换可用性 | catalog / 回测 / book 三处 `match_scope` 切换均工作正常 | E2E 测试 + 人工验收 |
| 新增信号工作量 | 加一个 signal 只需后端 1 文件 + DB 1 行 methodology,前端 0 改动 | 人工 code review |

## Open Questions

- [ ] **Q1: 方法论文案存哪儿?** (a) `signal_methodology` DB 表 — 可热改、可 A/B、可埋点;
      (b) `frontend/src/lib/methodology.ts` 静态常量 — 部署即生效但要发版;(c) MDX 静态页面 —
      排版自由但工作流割裂。**建议 V1 选 (a)** —— 跟 `competitions.name_zh` 的 "DB 即翻译"
      模式一致。
- [ ] **Q2: `conditions_json` 表达力到哪里?** V1 建议 schema:`{strength_min?: number,
      filters?: [{path: "value.delta_pct", op: ">", value: 5}, ...]}` —— 单层 AND,引
      JSON-Logic 留 V2。
- [ ] **Q3: scope='member' 的方法论是否对 public 用户可见?** **是。** 信号本身付费 ≠ 算法保密。
      公式都在网上能搜到,藏在订阅墙后只会降低信任 → 降低转化。real moat 是 historical
      数据 + 长期 ROI 历史 + 实时计算速度。
- [ ] **Q4: Personal Book 起始资金?** House Book 统一 `starting_units=100.0`;Personal fork
      时默认继承,允许 override。固定起始资金是为了 ROI 曲线**直接可比**。
- [ ] **Q5: 跟 alerts 模块怎么衔接?** 短期不动 alerts,留独立 PRD
      `alerts-subscription-merge.prd.md` —— 那时 alerts 退化为 `simulated_books` 的一个
      `notify_channels: ['bell' | 'email']` 列。
- [ ] **Q6: `strength` 跨信号可比吗?** **不可比。** Catalog 要在方法论里**明示**归一化口径。
      **ROI 跨信号可比** —— 这是"信号即账户 + 统一 starting_units"的最大产品价值。
- [ ] **Q7: House Book 是否可禁用?** 不行 —— 它是 Goalcast 信号体系的公开证据。若某信号
      长期 ROI < 0,保留曲线 + catalog 标记 "negative-ROI for 90+ days",不隐藏。透明
      压力。
- [ ] **Q8: `match_scope='my_leagues'` 在未登录态怎么办?** 三选项:(a) 隐藏切换(默认 `all`);
      (b) 显示但点击触发登录引导;(c) localStorage 缓存"游客联赛偏好"。**建议 (b)** —— 与
      `/insights/leagues` 的现有未登录处理一致(redirect to login)。
- [ ] **Q9: 回测的时间窗最大多长?** 受限于 `signals_snapshot` 覆盖度。`signals_snapshot`
      从 commit `f34f83c` 上线(2026-04 左右),目前最多 ~30 天历史。建议 V1.5 默认
      "近 7 天 / 14 天 / 30 天" 三档,自动按可用数据上限收敛;**不**支持"自定义起止日期"
      留 V2(避免边界条件 + UI 复杂度)。

## Users & Context

- **四阶段决策旅程对应的用户画像**:
  - **理解阶段**:新用户 / 评估用户 —— 进 catalog 看方法论。
  - **区分阶段**:进入"评估付费"阶段的用户 —— 想搞清 4 条信号到底差异在哪。
  - **回测阶段**:已经有点经验的用户 —— 在 fork book 之前要先看历史表现。
  - **验证阶段**:深度用户 —— 跑 House Books 对比 + 自己的 Personal Books。
- **`match_scope` 的两类用户**:
  - "全市场发现机会"型:看 `match_scope='all'`,接受信号涉及小联赛(可能没下注渠道但提供
    研究价值)。
  - "我的联赛聚焦"型:`match_scope='my_leagues'`,只看自己设置过偏好的联赛(`user_competition_prefs`)。
    这类用户更接近最终下注用户。
- **不覆盖**:批量 API 用户、机构客户、Kelly stake、组合策略(留 V2)。

## Solution Detail

### 阶段 1:理解 — 方法论 panel

| Priority | Capability | Rationale |
|---|---|---|
| Must | `BaseSignal` 加 4 ClassVar:`description: str`、`output_schema: dict`、`strength_formula: str`、`failure_modes: list[str]` | 给 catalog endpoint 喂结构化数据 |
| Must | 新表 `signal_methodology(signal_type TEXT, locale TEXT, body_md TEXT, updated_at TIMESTAMP, PRIMARY KEY (signal_type, locale))` | 文案与代码解耦,可热改 |
| Must | seed script `scripts/seed_methodology.py` 写入 4 条现存信号的中英方法论(共 8 行) | 上线即满覆盖 |
| Must | `GET /api/signals/catalog?locale=zh` → 全部注册信号 + metadata + methodology + 实时统计(近 7d 触发数、近 7d hit rate、House Book ROI sparkline) | 单 endpoint 喂前端 catalog |
| Must | 前端 `/insights/signals` 改 master-detail:左 catalog(信号卡片),右 = 方法论 panel + 该信号的 fixture 表 + "Fork to my book" + "Backtest" 按钮 | 主交付物 1 |

### 阶段 2:区分 — 对比模式

| Priority | Capability | Rationale |
|---|---|---|
| Must | catalog 页面顶部 toggle "对比模式":展开后多条信号并列,字段对齐:`description / strength_formula / 近 7d 触发数 / 近 7d hit rate / House Book 累计 ROI / scope` | 让用户一眼看出 4+ 信号的差异 |
| Should | 对比模式默认勾选所有 public 信号;member 信号显示但带"会员"标记(未付费就置灰但仍可见方法论) | 给付费决策提供材料 |
| Should | catalog 行可拖拽排序,本地 localStorage 持久化 | 用户自定义关注度 |

### 阶段 3:回测 — 信号层回测

| Priority | Capability | Rationale |
|---|---|---|
| Must | `POST /api/signals/:signal_type/backtest` body: `{conditions_json, window: '7d'|'14d'|'30d', match_scope: 'all'|'my_leagues'}` → 返回 `{settled_count, roi_pct, hit_rate, max_drawdown, equity_curve: [{date, cum_pnl}]}` | 核心 endpoint |
| Must | backtest evaluator(`services/signals/backtest.py`):遍历 `signals_snapshot WHERE signal_type=?` × `historical_odds` × `fixtures.status='FT'` → 对每条 snapshot 应用 conditions → 假设以该 waypoint 的 Pinnacle odds 下 1 unit → 用 fixture 的 winning_team 结算 P&L | 复用既有表,无新表 |
| Must | backtest 不污染 live `simulated_bets` —— 输出只在内存,不持久化(避免与 forward bets 混淆) | 模型清晰 |
| Must | 前端"回测"模态框:选 conditions(继承当前 book / 自定义)+ window + match_scope → 点击 Run → 展示 equity curve + 摘要数字 | UX 闭环 |
| Should | 回测结果可"另存为 Personal Book"(`POST /api/paper-trading/books` 带 `seed_conditions_from_backtest_id`) | 回测 → 创建 book 的最短路径 |
| Won't (V1.5) | 持久化 backtest run 历史 | V2(避免存储成本 + UI 复杂度) |
| Won't (V1.5) | 自定义起止日期 / 跨年回测 | V2(见 Q9) |

### 阶段 4:验证 — Books + 多曲线对比

| Priority | Capability | Rationale |
|---|---|---|
| Must | `simulated_books` 扩展为(沿用既有表 id):新增 `signal_type TEXT NOT NULL`、`signal_version TEXT NOT NULL`、`conditions_json TEXT NOT NULL DEFAULT '{}'`、`starting_units REAL NOT NULL DEFAULT 100.0`、`match_scope TEXT NOT NULL DEFAULT 'all'` | 1 book ↔ 1 信号 + 比赛范围一等公民 |
| Must | 每条 `REGISTERED` 信号自动建一个 House Book(`user_id=0`, name=`House-<signal_type>`, `match_scope='all'`),启动 init 时 INSERT OR IGNORE | 信号加进来就有账户跑 |
| Must | 迁移:旧 `simulated_bets.book_type='house'` 行按 `signal_type` 批量 UPDATE `book_id` 到对应 House Book | 平迁 |
| Must | snapshot worker 改 "per-book 评估":对 `signals_snapshot` 每条新行,遍历该 signal_type 下所有 active books,各自 eval `conditions_json` + `match_scope` 后写 `simulated_bets`(各 book 独立 UNIQUE) | V1.5 核心改动 |
| Must | `match_scope='my_leagues'` 评估时 `JOIN fixtures × user_competition_prefs WHERE user_id=books.user_id`;House Books `user_id=0` 永远走 `match_scope='all'`(站点级公共账户必须全市场) | 个人偏好正交 |
| Must | `POST /api/paper-trading/books`(body: `from_house_book_id` 或 `seed_conditions_from_backtest`)→ fork:复制 signal_type / version / conditions / starting_units 到新 Personal Book,`match_scope` 默认 `'my_leagues'` | 用户从看 → 做的最短路径 |
| Must | `PATCH /api/paper-trading/books/:id`(改 conditions / starting_units / match_scope / name / archive) + `DELETE` 软删 | 用户管自己的 book |
| Must | 前端 `/insights/paper-trading` 主图升级 "多曲线对比图" —— 每个未 archive 的 book 一条 ROI 曲线,顶部 toggle "House only / Personal only / All" | 主交付物 2 |
| Must | book 卡片:当前 ROI / 累计下单数 / 近 7d hit rate / max drawdown / signal_version / match_scope 标签 | 评判一条信号 |
| Should | catalog 信号卡片 "ROI sparkline" 缩略图(House Book 近 30 天) + "已更新" 红点 | 选信号时不用跳页 |
| Should | MatchDetail 行 "📒 模拟下单" 浮层标注 "命中你的哪几个 book" | 闭环到下单 |
| Won't (V1.5) | 同信号多 book 在同 fixture+selection 上的冲突仲裁 | **不存在该问题** —— `UNIQUE(book_id, fixture_id, selection)` 各算各的 |
| Won't (V1.5) | 跨用户 books 排行 / 跟单 | 永不做(`paper-trading.prd.md` 已划红线) |

### `match_scope` 评估细节

```python
def fixture_visible(fixture_id: int, book: SimulatedBook) -> bool:
    if book.match_scope == 'all':
        return True
    # match_scope == 'my_leagues'
    if book.user_id == 0:
        return True   # House Books 强制全市场,保证站点统计可比
    return await db.fetchone(
        "SELECT 1 FROM fixtures f JOIN user_competition_prefs p "
        "ON p.competition_id = f.competition_id "
        "WHERE f.id = ? AND p.user_id = ?", (fixture_id, book.user_id)
    ) is not None
```

> 关键不变量:House Books `match_scope='my_leagues'` **被禁止** —— 公共账户必须是全市场
> 视角才能跨用户可比;若某用户偏好 = 英超 + 西甲,`House-GS-Mispricing` 仍然扫全市场
> 写入 `simulated_bets`,但**该用户的 `/insights/paper-trading` 视图可以 toggle "只看
> 我联赛"** 用前端 filter 屏蔽其他联赛的下单行(不影响 House Book 全局曲线)。

### Data Flow (Forward 下单 with match_scope)

```
[snapshot worker 每个 waypoint tick]
  for each fixture in (NS 且距 kickoff 在 waypoint 范围):
    for each signal in REGISTERED:
      result = signal.compute(db, fixture_id, waypoint)
      if result is None: continue
      INSERT INTO signals_snapshot (...)                          ← 既有

      books = SELECT * FROM simulated_books
              WHERE signal_type = signal.signal_type
                AND signal_version = signal.signal_version
                AND archived_at IS NULL
      for book in books:
        if not await fixture_visible(fixture_id, book):  continue   # ← match_scope
        if not eval_conditions(book.conditions_json, result): continue
        INSERT OR IGNORE INTO simulated_bets (
          book_id     = book.id, user_id = book.user_id,
          fixture_id, selection = result.value_json.selection,
          stake_units = 1.0,
          entry_odds  = <对应 waypoint 的 Pinnacle odds>,
          entry_at = now, entry_waypoint = waypoint,
          signal_type = signal.signal_type,
          signal_version = signal.signal_version,
          outcome = NULL,
        )
        UNIQUE(book_id, fixture_id, selection) 自动去重单 book 内重复触发
```

### Data Flow (Backtest,与 forward 同公式回放历史)

```
POST /api/signals/:signal_type/backtest
body: {conditions_json, window: '30d', match_scope: 'my_leagues'}

evaluator:
  start = now - 30 days
  rows = SELECT s.fixture_id, s.waypoint, s.value_json, s.captured_at,
                f.status, f.winning_team, f.score_home, f.score_away,
                o.odds AS pinnacle_odds
         FROM signals_snapshot s
         JOIN fixtures f ON f.id = s.fixture_id
         LEFT JOIN historical_odds o ON o.fixture_id = s.fixture_id
                                    AND o.waypoint = s.waypoint
                                    AND o.bookmaker_id = 1
                                    AND o.market_id = 6
                                    AND o.outcome = <derived from value_json.selection>
         WHERE s.signal_type = ?
           AND s.captured_at >= ?
           AND f.status = 'FT'
  for r in rows:
    if not eval_match_scope(r.fixture_id, match_scope, user_id): continue
    if not eval_conditions(conditions_json, r.value_json): continue
    won = r.winning_team == <map selection to team_id>
    pnl = (r.pinnacle_odds - 1) if won else -1
    accumulate to equity_curve
  return {settled_count, roi_pct, hit_rate, max_drawdown, equity_curve}
```

> 回测的**关键忠诚度保证**:同样的 evaluator 函数(`eval_conditions`、`fixture_visible`)
> 在 forward(snapshot worker)与 historical(backtest endpoint)两条路径上**共享调用**,
> 行为完全一致。这就是 Success Metrics 里 "回测 ↔ forward 一致性 < 1pp" 的物理基础。

### `conditions_json` v1 schema

```json
{
  "strength_min": 0.5,
  "filters": [
    {"path": "value.delta_pct",  "op": ">",  "value": 5},
    {"path": "value.selection",  "op": "==", "value": "home"}
  ]
}
```

- `path`: 只允许 `strength` / `value.<key>` 两种 prefix。
- `op` 白名单:`==` / `!=` / `>` / `>=` / `<` / `<=` / `in`。
- 全 AND,无 OR(OR 等价于多 fork 几个 book)。
- evaluator ≤ 40 行 Python,`services/signals/conditions.py`。

### Catalog endpoint 输出形态(示例)

```json
{
  "items": [
    {
      "signal_type":     "GS-KEN-HT-EV",
      "signal_version":  "v1.0",
      "scope":           "public",
      "description":     "上半场平手盘 EV 5%~28% 反推香港盘赔率区间",
      "output_schema":   {"ah_line": "float", "ah_label": "draw|...", "hk_home_5": "float, EV=5% HK odds", "selection": "home|away"},
      "strength_formula": "min(2 * |eff_home - 0.5|, 1.0)",
      "failure_modes": [
        "FT 主盘不在 {0, ±0.25, ±0.5} → 不出信号",
        "HT 1X2 概率缺失 → 不出信号",
        "BET365 与 Pinnacle 都缺 AH 行 → 不出信号"
      ],
      "methodology_md": "## 计算原理\n\n...",
      "house_book_id":  12,
      "stats_7d": {
        "triggered":     34,
        "hit_rate":      0.51,
        "roi_pct":       2.3,
        "max_drawdown": -4.1,
        "sparkline":     [0.0, 0.3, 0.8, 0.5, 1.1, 1.7, 2.3]
      }
    }
  ]
}
```

### 平迁路径(House Book 零回归)

V1.5 部署后立即执行 `scripts/migrate_to_per_signal_books.py`:

1. `ALTER simulated_books ADD COLUMN signal_type / signal_version / conditions_json /
   starting_units / match_scope`(全部 idempotent + 默认值)
2. 遍历 `REGISTERED`,对每条信号 `INSERT OR IGNORE INTO simulated_books
   (user_id=0, name='House-<signal_type>', signal_type, signal_version,
    conditions_json=<信号自带 default 或 '{}'>, starting_units=100.0, match_scope='all')`
3. `GS-Mispricing` House Book `conditions_json` 写为
   `'{"filters":[{"path":"value.delta_pct","op":">","value":5}]}'`(等价当前硬编码)
4. `UPDATE simulated_bets SET book_id=<对应 House Book id> WHERE book_type='house'
   AND signal_type=<对应>`(批量按 signal_type 分配)
5. snapshot worker 切到 per-book 评估的新版本
6. 14 天观察期:`House-GS-Mispricing` 入库速率必须与上线前 baseline ±5% 内,否则
   `git revert` snapshot worker 改动

### 文件改动估算

- **backend 新文件**:
  - `services/signals/conditions.py` (evaluator)
  - `services/signals/backtest.py` (历史回放)
  - `routers/signals_catalog.py` (catalog + backtest endpoint)
  - `scripts/seed_methodology.py`、`scripts/migrate_to_per_signal_books.py`
- **backend 改动文件**:
  - `database.py` — 1 张新表 + `simulated_books` 5 个 idempotent ALTER + 启动 init 建 House Books
  - `services/signals/base.py` — 4 个 ClassVar
  - 4 个现存 `gs_*.py` — 各填 4 ClassVar(+ 可选 `default_conditions`)
  - `services/snapshot.py` — 改下单循环为 per-book 评估 + `fixture_visible` 调用
  - `routers/paper_trading.py` — books CRUD + `match_scope` query
- **frontend 新文件**:
  - `pages/SignalCatalog.tsx`(替代 `Signals.tsx`)
  - `components/MethodologyPanel.tsx`、`components/CompareTable.tsx`、`components/BacktestModal.tsx`、`components/BookEditor.tsx`、`components/MultiBookRoiChart.tsx`
- **frontend 改动文件**: `lib/api.ts` / `pages/PaperTrading.tsx` / `routes.tsx` / `i18n/messages.{zh,en}.json`
- **测试**: 每个 endpoint 一份 router 测试 + conditions evaluator 单测 + backtest evaluator 单测 + 平迁脚本 db fixture 测试 + per-book 下单循环 snapshot 测试 + match_scope E2E

预估总规模:**约 1400 行新代码 + 800 行测试**(比上一稿多了回测 evaluator + match_scope 一等公民),
1.5 人 sprint(3 周)交付 V1.5。

---

**Status:** Draft v3 · 等待评审
**Depends on:** `proprietary-signals.prd.md`(已交付) · `paper-trading.prd.md`(V1 已交付,本 PRD 即其 V1.5) · `backtest-accuracy.prd.md`(模型层回测,本 PRD 在其之上加信号层)
**Blocks:** `alerts-subscription-merge.prd.md`(未来) · 会员分层差异化付费(`#1`) · Kelly stake sizing PRD(未来)

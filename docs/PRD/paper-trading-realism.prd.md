# 模拟盘现实度演进:从 1X2 sandbox 到可信的多盘口虚拟交易所

> 路线对应:**承接 `paper-trading.prd.md` V1**(已上线的 House Book 单注模拟)与
> **`signal-catalog-and-subscriptions.prd.md` Phase 4**(信号即账户、多曲线
> ROI 对比、Personal Book fork)。
>
> 这两份 PRD 解决了"用户能用什么信号 / 看哪条信号长期赢钱"的问题,本 PRD
> 解决"模拟盘的 ROI 数字到底有多接近真实玩家的回报"。

## Problem Statement

当前模拟盘的下单与结算路径(commit `84b4eac`)有 **9 处理想化假设**,导致:

1. **某些信号的 ROI 数据完全无意义** ——`GS-KEN-HT-EV` 信号本意是 "HT 平手盘
   AH 的主/客",但 `place_bets_for_books`(`services/paper_trading.py:213-238`)
   一律按 **FT 1X2** 查 Pinnacle odds 并按 FT 1X2 结算。两个完全不同的盘口
   被强行映射,该 House Book 累积的 4 个 bet(`simulated_bets` 当前数据)其
   `value_json` 是 "HT EV 反推",但 `pnl_units` 按 FT 主客胜结算 —— 数据对
   该信号长期 ROI 评估**毫无参考价值**,且会污染多曲线对比图。

2. **ROI 数字与真实玩家最多差 5pp** —— 无 commission(高估 2pp)、无 slippage
   (高估 1-2pp)、无 CLV 追踪(无法判断"长期是否打败收盘")、stake 固定 1u
   (低估 sharp 玩家用 Kelly 能放大的 ROI)。综合下来,House Book 显示
   "House-GS-Mispricing ROI 3.5%" 可能对应真实玩家 1-6% 区间的任一值。
   **这个误差范围让 "PRD 验收 ±5%" 几乎没区分度**。

3. **盘口品类锁死在 FT 1X2** —— `place_bets_for_books` 硬要求 `value.selection
   ∈ {home, draw, away}`(`services/paper_trading.py:209-211`)+ Pinnacle
   `market_id=6` 查 odds。任何未来不是 1X2 的信号(AH / O-U / HT 半场盘 /
   角球 / 红黄牌 / ...)都无法接入模拟盘。这把"信号即账户"框架的可扩展性
   钉死在 1X2 这一种盘口里。

4. **没有 CLV(Closing Line Value)记录** —— `simulated_bets.closing_odds`
   列存在(`database.py:248`)但 `settle_bets`(`services/paper_trading.py`)
   从来没写入它。这意味着我们能算 ROI 但**算不出 CLV**,而 CLV 才是 sharp
   玩家判断"信号是否真的有 alpha"的金标准。一年回头看,只有 ROI 没 CLV
   等于只有 P&L 没有 Sharpe ratio。

5. **stake 永远 1u flat** —— 没有 Kelly / fractional Kelly / fixed-fraction
   / level-staking 任何 sizing 策略。`paper-trading.prd.md` 已经把这个划到
   Won't (V1);本 PRD 重新评估在 V2.5 加可选 stake 策略。

## Evidence

- **Tier 1 数据完整性 issue**:`services/paper_trading.py:209-219` 显示所有
  `place_bets_for_books` 触发的 bet 都查 `bookmaker_id=1 AND market_id=6`,
  且只接受 `selection ∈ {home, draw, away}`。GS-KEN-HT-EV 的 `value_json`
  里 selection 确实是 'home'/'away'(因为 1X2 和 HT-AH 共享"home/away"标签),
  所以会触发,但 odds 取错了市场。**这是已经在生产数据库 (`backend/data/
  goalcast.db`) 累积的脏数据**:4 行 simulated_bets WHERE signal_type='GS-KEN-HT-EV',
  无法用现有结算逻辑产出有意义的 P&L。
- **CLV 列在 schema 里但未启用**:`grep -n "closing_odds" backend/services/
  paper_trading.py` 只在 `settle_bets` 的 docstring 提到了"snapshot closing
  odds from historical_odds.waypoint='kickoff' for CLV",但实际 INSERT/UPDATE
  从未写这列。
- **VOID 处理已经写好但仅 1X2**:`paper_trading.py:VOID_STATUSES`(PST/CAN/
  ABD/AWD/WO)有覆盖,但仅对 1X2 结算路径,非 1X2 盘口的 void 规则不一定相同
  (例如 AH 还有 dead heat / 部分退本规则)。
- **真实玩家社区共识**:Pinnacle vig ≈ 2.5-3%(他们 take sharp action,要
  pay-out 高),Bet365/365bet ≈ 5-8%(他们 take retail),Betfair commission
  2-5%。本站只用 Pinnacle odds → 已经隐含 ~2.5% vig。不修也算"近乎无 vig"
  乐观估计。

## Proposed Solution

把"模拟盘现实度"做成一个**5 阶段渐进升级**,每阶段独立可发布、可 revert,
按"投入 / 收益 / 风险"排序:

```
┌──────────────────────────────────────────────────────────────────────┐
│ Phase A (~3 天)  Tier 1 数据完整性 — 必须做                            │
│   A1. 信号 ↔ 盘口绑定:BaseSignal 增加 settle_market 元数据             │
│   A2. KEN-HT-EV 暂时归档,等 Phase B AH 结算上线再重新激活               │
│   A3. CLV 记录:settle_bets 写入 closing_odds (用现有 schema 列)        │
├──────────────────────────────────────────────────────────────────────┤
│ Phase B (~1 周)  多盘口结算 — 解锁 AH 信号                              │
│   B1. settle_bets 按 settle_market 分派:1X2 vs AH 两条结算路径         │
│   B2. AH 结算规则:line=0 平手盘 push,±0.25 半赢半输,±0.5 全赢全输      │
│   B3. odds 查找逻辑:bookmaker_id 仍 Pinnacle,market_id 跟 settle_market│
│   B4. KEN-HT-EV House Book 重新激活,backfill 重算 4 个旧 bet            │
├──────────────────────────────────────────────────────────────────────┤
│ Phase C (~3 天)  ROI 透明度 — 让数字可解读                              │
│   C1. CLV % 计算:(entry_odds - closing_odds) / closing_odds × 100     │
│   C2. /paper-trading/books 响应里加 summary.clv_pct                    │
│   C3. BookCard 显示 CLV;ROI 旁边加 "vig adjusted" 注解                  │
│   C4. 多曲线图:可选 toggle "理想 ROI" / "去 vig 后 ROI"                 │
├──────────────────────────────────────────────────────────────────────┤
│ Phase D (~1 周)  Stake 策略 — Kelly + 自定义                            │
│   D1. simulated_books 加 stake_strategy 列 {'flat' | 'kelly' | 'kelly_half'}│
│   D2. BookEditor 加 stake 策略选择 + Kelly fraction                    │
│   D3. place_bets_for_books 按策略算 stake_units 而非固定 1u            │
│   D4. 多曲线图按各 Book 的实际 stake 策略画                              │
├──────────────────────────────────────────────────────────────────────┤
│ Phase E (V2 候选)  高阶现实度                                           │
│   E1. Commission 建模 (Betfair-style 2% off winnings)                 │
│   E2. Slippage 模型 (信号 fire 到下单中间随机移动 0-3 ticks)            │
│   E3. 限额 / 拒单模拟 (sharp player at Pinnacle limit 50u)             │
│   E4. 滚球 in-play (LIVE 状态下单,需要分钟级 odds 数据)                 │
└──────────────────────────────────────────────────────────────────────┘
```

**核心承诺**:每个 phase 都保持**正向数据兼容** —— 旧的 simulated_bets 行
不会被改写,新逻辑只影响后续 bet。Phase B/C 提供一次性 backfill 脚本让历史
数据"算上 CLV"或"重算 AH 结算",但不强制。

## Key Hypothesis

我们相信【把模拟盘从 1X2-only 升级到多盘口 + CLV + Kelly】会**显著提高用户
对 "House Book ROI 数字" 的信任度**,验收信号:

- **数据有效性 invariant**: GS-KEN-HT-EV 重新激活后,该 Book 的 ROI / 命中率
  与回测出来的 30 天历史 ROI 偏差 < 1pp(forward ↔ backtest parity)。
- **CLV 区分度**: 4 个公开信号(Mispricing/LineMove/SharpSquare/HT-EV)长期
  CLV 至少有 2 个不显著重叠(差距 ≥ 1.5pp)—— 否则说明信号体系本身没 alpha,
  跟现实度无关。
- **多盘口覆盖**: Phase B 上线后,所有 4 个 REGISTERED 信号都能被模拟盘正确
  结算,不再有"信号在 catalog 但 Book 不接"的情形。
- **行为平迁(再来一次)**: Phase A 上线 14 天内,`House-GS-Mispricing` 的
  入库速率 / ROI 与 Phase A 上线前 ±5% 内(纯 1X2 路径未变,Phase A 只动了
  CLV 写入和 KEN-HT-EV 归档)。

## What We're NOT Building

- **不**做真实账户对接 / 出入金 / 真钱下单 —— 这是合规红线,
  `paper-trading.prd.md` 已明确划掉,永不做。
- **不**做用户间排行 / 跟单别人的 Book —— 同上,合规红线。
- **不**做 cash-out / 撤单 / 修改已下单 —— 破坏审计完整性。
- **不**做 fractional unit (0.3u 这种小数 stake) —— Phase D 的 Kelly 也只
  允许整数倍 / half-Kelly 离散档,避免 0.x 单位浮点累积误差。
- **不**做 multi-leg parlay (串关) —— Phase E 也不做,留 V3 评估。串关的
  EV / 限额 / 结算复杂度都不是渐进可加的。
- **不**做实时 (in-play) 滚球下单 —— Phase E 列了但带"V2 候选"标签,需要先
  搞清楚分钟级 odds 数据是否真能拉到。
- **不**自动按 PRD 升级历史数据 —— 每个 phase 提供 backfill 脚本,但默认
  不跑;由 ops 决定何时跑、跑多少历史窗口。
- **不**为 KEN-HT-EV 这类"非 1X2 信号"在 Phase A 立即上线结算 —— Phase A
  做的是"先把它停下来防止脏数据继续累积",Phase B 才补 AH 结算路径。

## Success Metrics

| Metric | Target | How Measured |
|---|---|---|
| Phase A 数据完整性 | KEN-HT-EV House Book archived;无新 KEN bet 用 1X2 错盘口下 | `SELECT COUNT(*) FROM simulated_bets WHERE signal_type='GS-KEN-HT-EV' AND entry_at > <A_deploy_at>` = 0 |
| Phase A CLV 覆盖率 | settle_bets 后 ≥ 95% 已结算行的 closing_odds 非空 | `SELECT COUNT(*) FROM simulated_bets WHERE outcome IS NOT NULL AND closing_odds IS NULL` / total settled < 5% |
| Phase B AH 结算正确性 | 用历史已知 FT 比分 + 已知 AH line 跑 fixture 测试集,结算 100% 与人工预期一致 | 单测覆盖 line ∈ {0, ±0.25, ±0.5, ±0.75, ±1} × {home/away leads/even} 所有组合 |
| Phase C 用户对 ROI 的 trust | catalog 卡片显示 CLV 后,catalog → paper-trading 跳转率 +20% | 埋点 `signals.catalog.click_to_paper` 切前后 4 周对比 |
| Phase D Kelly 采纳 | Personal Book 中使用非 flat stake 策略的比例 ≥ 20% | `SELECT COUNT(*) WHERE stake_strategy != 'flat' AND user_id > 0` / 总数 |
| Forward ↔ backtest parity | 任意 Book 的 forward 30 天 ROI 与同窗口 backtest 的差距 < 1pp | 周度对账脚本 |

## Open Questions

- [ ] **Q1: settle_market 怎么表达?** Option A: BaseSignal ClassVar
      `settle_market: tuple[int, str]` = `(market_id, outcome_type)` 例如
      `(6, '1X2')` 或 `(51, 'AH_0')`;Option B: 让每个信号自己定义 `settle()`
      方法,返回 pnl。**建议 V1 选 A**(声明式,scheduler 可批量),Option B
      留 V3(复合信号 / 跨市场对冲)。
- [ ] **Q2: AH line=0 push 部分退本规则?** 主流书商对 AH 部分退本的处理:
      home_-0.25 输了 → 全输 stake;赢了 → 全赢 stake×odds-1 (没有 push)。
      home_-0.5 输了 → 全输;赢了 → 全赢。home_0 → 平手退本。这些规则在 V1
      的 settle_bets 全部实现,还是先只做 line=0?**建议 V1 做完整规则**,
      因为反正一次写完。
- [ ] **Q3: CLV 用哪个 waypoint 作为 closing?** `historical_odds.waypoint=
      'kickoff'` 应该是最接近开赛的赔率快照。但 kickoff waypoint 是 snapshot
      worker 在比赛开始**之后**才写入(`hours_to <= 0`),所以 settle_bets
      跑到时 closing_odds 一定已经存在。✓
- [ ] **Q4: Kelly 用什么概率?** Kelly 公式 `f = (b·p − q) / b` 需要 `p`
      = 真实胜率。我们有的是 **模型概率**(`historical_predictions.home_win_pct`),
      和 **市场 de-vig 后概率**。建议默认用模型,允许用户切到市场。
- [ ] **Q5: 多盘口下,UNIQUE 约束的去重 key 还是 (book_id, fixture_id,
      selection) 吗?** 如果同一 book 既订阅了 1X2 home 又订阅了 AH home,
      `selection='home'` 字符串冲突。建议把 UNIQUE 扩成
      `(book_id, fixture_id, market_id, selection)`。
- [ ] **Q6: backfill 历史数据(尤其 Phase B 的 AH 结算修复 KEN-HT-EV)谁
      触发?** 自动跑(危险,DELETE+重算可能影响已有 ROI 曲线)还是 ops 手动
      跑(安全但容易忘)?建议 ops 手动 + 跑前自动备份 DB。
- [ ] **Q7: stake_strategy='kelly' 时,如果某 fixture 算出 stake=0.7 unit,
      怎么处理?** Floor 到 0(跳过下单)?Round 到 1(过度下注)?用 fractional
      Kelly 0.5x 让所有信号都能下整数 stake?建议 floor 但加 warning(让用户
      看到模型说"这条信号没强到值得 1u")。

## Users & Context

- **谁会受益于 Phase A?** 所有用户 —— 错的数据(KEN-HT-EV 的 4 个 bet)消失,
  catalog ROI 数字不再被污染。**最低成本最高价值**,所以先做。
- **谁会受益于 Phase B?** 想看 HT-EV / 未来 AH 类信号长期 ROI 的用户。这是
  解锁未来信号扩展的前置工作。
- **谁会用 CLV?** 真正 sharp 的玩家(可能是少数)。但 CLV 上线后,即使非
  sharp 玩家在 catalog 看到"这条信号 30 天 CLV +1.2%"也会**间接受益**(高
  CLV → 长期更可能 +EV),所以不是 power-user-only。
- **谁会用 Kelly?** 同上,sharp 玩家。但 BookEditor 加 dropdown 不增加普通
  用户认知负担(默认 flat 不变)。
- **不覆盖**:批量 API 用户、机构、跟单他人、真钱用户。

## Solution Detail

### Phase A — Tier 1 数据完整性

| Priority | Capability | Rationale |
|---|---|---|
| Must | BaseSignal 加 `settle_market: tuple[int, str] = (6, '1X2')` ClassVar | 让每条信号声明自己结算所在的盘口 |
| Must | 4 个现存信号填 settle_market:GS-Mispricing/LineMove/SharpSquare = `(6, '1X2')`;GS-KEN-HT-EV = `(51, 'AH_0_HT')`(新 outcome_type 占位) | 明示意图 |
| Must | place_bets_for_books 读 signal.settle_market;若不是 `(6, '1X2')` 则**跳过下单**(等 Phase B 接) | 防止 KEN-HT-EV 继续错下 |
| Must | scripts/archive_misconfigured_books.py 一次性归档 KEN-HT-EV House Book(已有 4 个 bet 不动) | 让生产 catalog 不再误导 |
| Must | settle_bets 写 closing_odds:`SELECT odds FROM historical_odds WHERE waypoint='kickoff' AND bookmaker_id=1 AND market_id=6 AND outcome=:selection` | 启用现有 schema 的 CLV 列 |
| Must | 测试:CLV 写入正确性 + 跳过非 1X2 信号 + 归档脚本幂等 | 平迁安全 |

### Phase B — 多盘口结算

| Priority | Capability | Rationale |
|---|---|---|
| Must | settle_bets 按 settle_market 分派 1X2 / AH 两条结算路径 | 核心 |
| Must | services/paper_trading_ah.py: `settle_ah(line, score_home, score_away, selection) → (outcome, pnl_multiplier)` 覆盖 line ∈ {0, ±0.25, ±0.5, ±0.75, ±1} | 复用的纯函数 |
| Must | place_bets_for_books 解锁 AH:按 signal.settle_market 查 `historical_odds.market_id=51`(AH market_id) | KEN-HT-EV 重新可下单 |
| Must | UNIQUE(book_id, fixture_id, **market_id**, selection) 替换旧 UNIQUE | 同 fixture 不同盘口可共存 |
| Must | scripts/migrate_ah_unique.py 迁移已有索引 | DDL 改变要 idempotent |
| Should | 重新激活 KEN-HT-EV House Book + 一次性 backfill 旧 4 行(可选,操作员决定) | 数据可恢复 |
| Won't (B) | O-U / 角球 / 红黄牌 / 半场 1X2 (HT 1X2) 结算 | V2 加,本期只做 AH |

### Phase C — ROI 透明度

| Priority | Capability | Rationale |
|---|---|---|
| Must | book_summary 加 `clv_pct: float \| None` (over settled bets WHERE closing_odds IS NOT NULL) | 把已记的 closing_odds 算出来 |
| Must | GET /paper-trading/books 响应里加 summary.clv_pct | API 透出 |
| Must | BookCard / MultiBookRoiChart 工具栏加 CLV 显示 | UI 暴露 |
| Should | catalog 卡片显示 House Book 的 30d CLV(已经显示 ROI sparkline,加个数字) | sharp 玩家从 catalog 直接判断 |
| Should | "实际 ROI" 与 "去 vig 后 ROI" toggle(后者 = ROI + clv_pct,粗近似) | 让用户看见 vig 吃了多少 |

### Phase D — Stake 策略

| Priority | Capability | Rationale |
|---|---|---|
| Must | simulated_books 加 `stake_strategy TEXT DEFAULT 'flat'` 列(ALTER 幂等) | 选项数据基础 |
| Must | place_bets_for_books 调用 services/staking.py:`compute_stake(strategy, book, signal_result) → float` | 解耦 |
| Must | services/staking.py 实现 'flat' / 'kelly' / 'kelly_half';Kelly 用模型概率,允许 conditions_json 里 override `kelly_p_source: 'model' \| 'market'` | 灵活 |
| Must | BookEditor 加 stake 策略 dropdown | UI |
| Should | 多曲线图按各 Book 实际 stake 累积 PnL(已经是这样,因为 timeseries 用 pnl_units) | 自然支持 |
| Won't (D) | Kelly fractional dynamic (按当前 bankroll 调整) | 留 V2.5,需要 streaming bankroll |

### Phase E — 高阶现实度(V2 候选,不在本 PRD 承诺范围)

预留位置,具体设计等 Phase A-D 上线后再写另一个 PRD。

### Data Flow 变化(Phase B 之后)

```
[snapshot tick]
  for signal in REGISTERED:
    result = signal.compute(...)
    INSERT signals_snapshot
    market_id, outcome_type = signal.settle_market    # ← 新增
    books = SELECT * WHERE signal_type AND signal_version AND archived_at IS NULL
    for book in books:
      if not eval_conditions(...): continue
      if not fixture_visible_for_match_scope(...): continue
      selection = result.value_json.selection
      # ↓ Phase B: 按 signal.settle_market 查对应市场的 odds
      entry_odds = lookup_odds(fixture_id, waypoint, market_id, selection)
      if entry_odds is None: continue
      stake = compute_stake(book.stake_strategy, book, result)  # ← Phase D
      INSERT OR IGNORE INTO simulated_bets (
        book_id, market_id, selection, stake_units=stake,
        entry_odds, entry_at, signal_type, signal_version, ...
      )
      UNIQUE(book_id, fixture_id, market_id, selection)         # ← Phase B
```

```
[settle_bets tick]
  for bet IN pending bets WHERE fixture status changed:
    if fixture.status == 'FT':
      market_id = bet.market_id
      if market_id == 6:           # 1X2
        outcome, pnl = settle_1x2(score_home, score_away, bet.selection, bet.entry_odds, bet.stake_units)
      elif market_id == 51:        # AH
        line = parse_ah_line_from_outcome_type(bet.outcome_type)
        outcome, pnl = settle_ah(line, score_home, score_away, bet.selection, bet.entry_odds, bet.stake_units)
      else:
        outcome = 'void'; pnl = 0  # 未支持市场默认 void
      closing_odds = lookup_odds(bet.fixture_id, 'kickoff', market_id, bet.selection)  # ← Phase A
      UPDATE simulated_bets SET outcome, pnl_units, closing_odds, settled_at WHERE id=?
```

### 文件改动估算

#### Phase A (~3 天,1 commit)
- backend 新文件:`scripts/archive_misconfigured_books.py`
- backend 改动:`services/signals/base.py`(加 settle_market ClassVar)、4 个
  `gs_*.py`(填值)、`services/paper_trading.py`(gate + CLV 写入)
- 测试:`tests/test_paper_trading_clv.py` 新文件(CLV 写入 + 1X2 gate)
- 估算:**~350 行 + 200 行测试**

#### Phase B (~1 周,2 commits)
- backend 新文件:`services/paper_trading_ah.py`(AH 结算纯函数)
- backend 改动:`database.py`(UNIQUE 索引迁移)、`services/paper_trading.py`
  (settle 分派)、`scripts/migrate_ah_unique.py`
- 测试:`tests/test_paper_trading_ah.py`(line × score × selection 网格覆盖)
- 估算:**~700 行 + 500 行测试**

#### Phase C (~3 天,1 commit)
- backend 改动:`services/paper_trading.py`(book_summary 加 clv_pct)、
  `routers/paper_trading.py`(API 透出)
- frontend:`lib/api.ts`(类型) / `pages/PaperTrading.tsx`(BookCard 显示) /
  `components/signals/MultiBookRoiChart.tsx`(CLV toggle)
- 估算:**~400 行 + 100 行测试**

#### Phase D (~1 周,1-2 commits)
- backend 新文件:`services/staking.py`
- backend 改动:`database.py`(ALTER)、`services/paper_trading.py`(call stake)、
  `routers/paper_trading.py`(POST/PATCH 验证 stake_strategy)
- frontend:`components/signals/BookEditor.tsx`(dropdown + Kelly 参数)
- 估算:**~600 行 + 300 行测试**

**总计 Phase A-D ~2050 行 + 1100 行测试,3-4 周顺序交付**(每个 phase 一个
14 天观察期重叠跑,实际 wall-clock 大概 6-7 周)。

---

**Status:** Draft v1 · 等待评审
**Depends on:** `paper-trading.prd.md`(V1 已交付)、
                `signal-catalog-and-subscriptions.prd.md`(Phase 0-4c 已交付)
**Blocks:** 未来非 1X2 信号(任何 AH/O-U/HT/Corner/Card 类的信号都需要 Phase B
            之后才能接入模拟盘)、Kelly 类 staking 教学内容、CLV 投资者材料

# Goalcast Signals：把散落的衍生指标沉淀成命名良好的自有信号集

> 路线对应：roadmap #3 "对现有数据的加工产生自有数据"。
> 它是 #5（回测）和模拟投注 House Book 的信号源，是 #4 自有模型的特征工程入口，是 #1 会员分层的差异化付费内容。

## 关于 xG / 球员伤停 / 阵容等"行业标准数据"

**不在本 PRD 范围**。这些是行业内已经标准化的第三方数据（Understat / StatsBomb / Opta / SofaScore / FBref），Goalcast 当前数据源（OddAlerts + Pinnacle/Bet365 赔率）**完全不提供**。把它们叫"自有"是名实不副。

如果要接入，那是另一个独立的 **"external-stats-sources" PRD**（外部数据源扩展），并应该和 **#4 自有模型** 一起规划——因为 xG/伤停/阵容等几乎**只有作为模型特征**时才能真正发挥价值，而单独以 UI 形式展示（"这场比赛 xG 1.4 vs 1.1"）并不构成 Goalcast 的差异化护城河（任何免费数据网站都给）。

本 PRD 的"自有"定义是：**只用 Goalcast 现有数据库已有字段加工，产出别处直接拿不到的衍生指标 / 标注 / 知识**。

## Problem Statement

Goalcast 当前已经在产出 6 条以上**第三方拿不到的衍生指标**——错定价 Δ、predictability 标签、跌赔窗口、价值投注 edge、H2H 自建、赔率时间序列——但它们：

1. **散在 6 个 endpoint，没有"信号"这层统一抽象**：每个 endpoint 各自计算、各自命名、各自返回结构。
2. **没有版本 / 文档 / 命名空间**：用户不知道这些是 Goalcast 独有的还是从某处转售的；团队自己也无法在 #5 回测时引用"GS-Mispricing v1.2"这种稳定标识。
3. **没有信号本身的历史快照**：`historical_predictions` 只快照模型预测的概率，没快照"这场比赛在 T-24h 时 mispricing Δ 是多少"——所以 #5 想回测"信号触发后命中率"做不到，模拟投注 House Book 想按当时的信号值跟单也做不到（只能用当前值近似）。
4. **没有可订阅 / 可导出形态**：用户想"每天 9am 看一份最新错定价 + 跌赔合订榜"做不到，要点 4 个 tab 自己拼。
5. **没有为 #1 会员分层做内容切分**：哪些信号公开、哪些付费、付费会员还能拿到什么不公开的——目前完全没设计。

## Evidence

- 现有 endpoints 数（截至 commit `ba27fab`）：`/insights/mispricings`、`/insights/leagues/:id`、`/dropping-odds`、`/value-bets`、`/fixtures/:id/h2h`、`/fixtures/:id/odds-timeseries` —— 6 个独立 endpoint，6 套响应格式，0 个共享"signal"命名空间。
- `fixtures.predictability`（'high'/'good'/'medium'/'poor'）是 commit `d46c86b` 重新赋的语义标签，**当前完全没被外露**为可订阅信号，只在联赛统计里以分布形式出现一次。
- `bookmaker_odds.opening / current / peak` 三段定价信息当前只在 MatchDetail 部分展示；"开盘到现在的盘口漂移"是一个明显的自有信号但**尚未实体化**。
- 比对 `value-bets` 和 `mispricings`：两者其实是**同一信号的双面**（前者只看正 edge，后者看双向），但实现是两套独立 SQL—— 典型"散落 + 重复"症状。
- **Sharp/Square 分歧**（Pinnacle vs Bet365 1X2 偏差）在 `analyst-insights.prd.md` 提到为 Must，但代码层暂未发现独立 router 实现——既然要做，就纳入本 PRD 一并实体化。

## Proposed Solution

把上述衍生指标统一抽象成 **Goalcast Signals**：

```
Signal = {
  type: 'GS-Mispricing' | 'GS-OddsDrop' | 'GS-Predictability'
       | 'GS-LineMove' | 'GS-SharpSquare' | 'GS-H2HForm',
  version: 'v1.0',
  fixture_id: int,
  value: <信号自定义 JSON>,
  strength: float [0,1],         // 标准化强度，便于跨信号排序
  scope: 'public' | 'member',
  captured_at: timestamp,
}
```

每条信号是一个**纯函数** `compute(fixture_id, waypoint) -> SignalRow`，输入仅来自现有数据库表，无副作用。这层抽象做四件事：

1. **统一计算管线**：新增 `services/signals/` 目录，每个信号一个文件（`gs_mispricing.py`、`gs_odds_drop.py` 等），共享 `BaseSignal` 接口。
2. **信号快照**：跟 #5 的 5 waypoint 管线对齐，每场比赛每个 waypoint 给每条信号留一行 `signals_snapshot`——让"信号在某时点是什么值"可被回测、可被模拟下单引用。
3. **统一 endpoint**：`GET /api/signals/:type?fixture_id=&min_strength=&since=` 替代 6 个散落 endpoint（旧 endpoint 保留兼容期，新 UI 用新接口）。
4. **公开 / 会员切分**：`scope` 字段直接落 schema，公开 signal 任意访问、member-only signal 必登录 +（为 #1）未来可挂套餐。

## Key Hypothesis

我们相信【把已有衍生指标系统化为命名的 Goalcast Signals】会同时为 #5 / 模拟投注 / #4 / #1 解锁路径：

- **#5 回测可以多评估"信号 → 命中率"**：例如"GS-Mispricing 当 Δ>5% 时主胜命中率多少 / Brier 多少"——这是把信号本身（而不是只模型概率）作为评估对象。
- **模拟投注 House Book 信号源从硬编码升级到配置化 subscription**：未来用 `signal_type='GS-Mispricing' AND value.delta_pct > 5` 替代当前 PRD 写死的逻辑，多条信号并发跑账户。
- **#4 自有模型的特征工程**直接读 `signals_snapshot` ——每场比赛每个 waypoint 都有 N 个标准化数值特征，省去重新做特征。
- **#1 会员分层**直接挂 `scope='member'`：基础 3 条信号公开，进阶 3 条会员；判读门槛在 paper-trading PRD Phase C 之后启动定价。

可量化验收：

- 6 个旧 endpoint 100% 能由 `/api/signals/:type` 等价产出（覆盖率回归测试通过）。
- 上线 30 天后 `signals_snapshot` 行数 ≥ `historical_predictions` × 6（信号数）的 80%（管线稳定性）。
- 至少 1 条信号在 #5 回测中表现出"Δ > 阈值 时 hit rate 显著高于基线"的可发布结论。

## What We're NOT Building

- **xG / 球员伤停 / 公开投注比例 / 阵容 / 球员评分 / 教练战术** —— 第三方数据，本 PRD 0 个新数据源。另起 "external-stats-sources" PRD，与 #4 联动。
- **任何 ML 训练 / 自动调参** —— 信号公式手写、可解释，黑盒留 #4。
- **多语言信号别名 / 国际化** —— 信号 `type` 始终是英文 stable ID（如 `GS-Mispricing`），UI 文案另由 i18n 处理。
- **实时流式信号 / WebSocket 订阅** —— V1 拉取 + 定时 snapshot；流式留 V2。
- **信号组合 / 复合策略** —— 例如"GS-Mispricing AND GS-OddsDrop 同时触发才算 strong signal"——单信号先做扎实，复合留 V1.5。
- **信号回测自身**（"信号好不好用"）—— 是 #5 backtest endpoint 的职责，本 PRD 只保证信号**计算 + 快照 + 暴露**正确，不评估它好坏。
- **跨用户信号 / 群体心智 / 用户聚合数据信号** —— Goalcast 当前没有用户行为数据；这种信号要等模拟投注积累 personal book 数据之后才能讨论。
- **用户自定义信号 / DSL** —— 不在产品路线上。

## Success Metrics

| Metric | Target | How Measured |
|--------|--------|--------------|
| 旧 endpoint 行为等价回归 | 6/6 通过 | pytest 对比新旧响应 |
| Signal snapshot 覆盖率 | 30 天后每场 FT 比赛 5 waypoint × N 信号 完整率 ≥ 80% | DB query |
| `/api/signals/:type` P95 延迟 | < 300ms（30 天累计样本） | 后端 metrics |
| 公开 vs 会员信号分割 | 至少 3 公开 + 3 会员 | Schema 字段 |
| 信号文档完整率 | 100%——每条信号 README 含公式 + 阈值含义 + 典型场景 + 已知失效 | `docs/signals/*.md` 文件数 |

## Open Questions

- [ ] **`signals_snapshot` 稠密存 vs 稀疏存？** 稠密：每场 5 waypoint × 6 信号 = 30 行 / 比赛，100 场/天 = 3000 行/天，年增 ~1M 行可控；稀疏：只在阈值触发时写。建议**稠密** —— 对齐 `historical_predictions` 设计，查询简单，体量可控。
- [ ] **`GS-LineMove`（盘口漂移）和 `GS-OddsDrop`（跌赔）的关系？** 跌赔是 line move 的一种特殊视角（绝对值百分比）；建议合并为 `GS-LineMove`，把 drop 作为其字段之一。但意味着要废弃 `/dropping-odds` 旧 endpoint。
- [ ] **`GS-SharpSquare` 当前未实体化** —— 本 PRD 实现还是只占位？建议本 PRD 实现（接口 + 计算公式），告警系统留独立项。
- [ ] **信号 version bump 策略**：改阈值 / 微调常数 = patch（v1.0.1，不变 schema）；改公式 = minor（v1.1）；改输入字段或语义 = major（v2.0）并保留 v1 endpoint 30 天兼容。
- [ ] **公开 / 会员的分割具体怎么切？** 草案：基础（Mispricing / Predictability / OddsDrop 公开）、进阶（LineMove / SharpSquare / H2HForm 会员）。但**这条决定不在本 PRD 拍板**——等 paper-trading Phase C 给出 ROI 信号有效证据后由 #1 会员分层 PRD 拍。本 PRD 只保证 schema 字段就位。
- [ ] **旧 endpoint 兼容期多长？** 建议 90 天双跑后下线，UI 同步切到 `/api/signals/*`。

---

## Users & Context

**Primary Users（三向）**

- **External 普通用户**：希望在一个地方看完所有"Goalcast 独有的判断"，而不是在 6 个 tab 里拼。
- **External 会员用户（未来）**：愿意为"别处拿不到的进阶信号 + 历史时序"付费——前提是公开信号本身已经被证明有 edge（依赖 paper-trading Phase C）。
- **Internal 团队**：希望把"信号"作为 #5 回测对象、#4 模型特征、模拟投注下单条件的统一抽象，不再为每个新需求重写一遍 SQL。

**Job to Be Done**
- 用户：当我做赛前研究想看 Goalcast 独家信号时，我希望一眼看完所有 active signal、按强度排序、可点入溯源，而不是在多个不同结构的页面里拼。
- 团队：当我做新功能（回测 / 模拟投注 / 自有模型）需要引用"Goalcast 对这场比赛的判断"时，我希望读一个标准 schema 的 `signals_snapshot` 表，而不是 5 套异构 endpoint。

**Non-Users**
- 只看自家关注球队近况的纯兴趣用户：信号集对他们附加价值低，本期不针对他们设计 UI。
- 跨平台量化做市玩家：他们要 streaming + 毫秒级，本期纯快照接口不覆盖。

---

## Solution Detail

### V1 信号清单

| Signal Type | 来源 | 数学定义（V1）| Scope | 已实现 |
|-------------|------|----------------|-------|--------|
| `GS-Mispricing` | predictions × bookmaker_odds | `model_prob - de_vig(market_prob)`，每场取 max\|Δ\| 那个 selection | public | ✅ /insights/mispricings |
| `GS-Predictability` | OddAlerts + Goalcast 语义改名 | enum: high/good/medium/poor | public | ✅ fixtures 字段 |
| `GS-OddsDrop` | odds_snapshots.drop_pct | 时间窗口内某市场跌幅 % | public | ✅ /dropping-odds |
| `GS-LineMove` | bookmaker_odds.opening/current/peak | (current − opening) / opening × 100，含峰值漂移 | member | ❌ 数据有但未实体化 |
| `GS-SharpSquare` | bookmaker_odds (Pinnacle vs Bet365) | de_vig 1X2 prob 在两家分歧的最大 selection | member | ❌ 新建 |
| `GS-H2HForm` | fixtures 自建 H2H | 近 N 场 H2H 主胜 / 平 / 客胜 % + 进球差代理（≠ xG）| member | 🟡 /fixtures/:id/h2h 有原始数据，未聚合 |

> "进球差代理"（GoalDiff Proxy）用 score_home/away 差代替 xG，**这是一个近似指标**，会在文档里标明"待 #4 阶段接入真 xG 后升级"。

### Schema 草案

```sql
CREATE TABLE signals_snapshot (
  fixture_id     INTEGER NOT NULL REFERENCES fixtures(id),
  signal_type    TEXT    NOT NULL,        -- 'GS-Mispricing' etc.
  signal_version TEXT    NOT NULL,        -- 'v1.0'
  waypoint       TEXT    NOT NULL,        -- 48h/24h/6h/1h/kickoff（与 historical_predictions 五点对齐；
                                          --  不引入额外 'now' waypoint，避免双轨）
  scope          TEXT    NOT NULL,        -- 'public'/'member'
  value_json     TEXT    NOT NULL,        -- 信号自定义 JSON
  strength       REAL,                    -- 标准化强度 [0,1]，用于排序
  captured_at    TIMESTAMP NOT NULL,
  PRIMARY KEY (fixture_id, signal_type, waypoint)
);
CREATE INDEX idx_ss_type_strength ON signals_snapshot(signal_type, strength DESC);
CREATE INDEX idx_ss_fixture       ON signals_snapshot(fixture_id);
```

### Endpoint 契约

```
GET /api/signals/:type
  ?fixture_id=&competition_id=&min_strength=&waypoint=kickoff&since=

# waypoint 默认取 'kickoff'（最权威、与 #5 回测对齐）；可选 48h/24h/6h/1h。
# 如果调用方需要"最新可用"语义（即所有信号在赛前最接近现在的那个 waypoint），
# 可省略 waypoint 参数，后端按 max(captured_at) 返回每场比赛各信号的最新行。

→ {
  "signal_type": "GS-Mispricing",
  "version": "v1.0",
  "scope": "public",
  "items": [
    {
      "fixture_id": 123,
      "waypoint": "kickoff",
      "captured_at": "2026-05-18T09:00:00Z",
      "strength": 0.72,
      "value": { "delta_pct": -14.5, "selection": "home" }
    }
  ],
  "next_cursor": null
}
```

### Capabilities (MoSCoW)

| Priority | Capability | Rationale |
|----------|------------|-----------|
| Must | `services/signals/` 目录 + `BaseSignal` 抽象 + 6 个 V1 信号文件 | 统一计算管线 |
| Must | 新表 `signals_snapshot` + APScheduler job 在 5 waypoint 各跑一遍写入 | 历史可回测 |
| Must | `GET /api/signals/:type` 统一 endpoint | 替代散落接口 |
| Must | 6 条信号各一份 `docs/signals/gs-*.md`（公式 / 阈值 / 失效场景） | 文档不可省 |
| Must | 公开 vs 会员 scope 字段 schema 就位（V1 不挂付费墙） | 为 #1 铺路 |
| Must | 旧 endpoint 双跑 + 行为等价回归测试 | 切换零风险 |
| Should | `GS-LineMove` 和 `GS-SharpSquare` 新建实现（已有数据） | 用满库存 |
| Should | `/insights/signals` 一页统览：按信号类型分 Tab、按 strength 排序、可订阅"今日 active signals" | 用户层入口 |
| Should | 信号 README 入 i18n（zh / en 各一份） | 国际化对齐 |
| Won't (V1) | 真 xG / 伤停 / 公开投注比例 / 阵容 | 第三方数据，独立 PRD |
| Won't (V1) | 信号组合策略 / 复合信号 | V1.5 |
| Won't (V1) | streaming / WebSocket / push | V2 |
| Won't (V1) | 用户自定义信号 / DSL | 不在产品路线上 |

### Data Flow

```
[每个 waypoint tick · 复用现有 services/snapshot.py 的 _capture 钩子，不新建 scheduler]
  for each fixture in (NS 且距 kickoff 在 waypoint 范围):
    1) 现有逻辑：写 historical_predictions / historical_odds 一行（已存在）
    2) 新增：for each Signal in registered_signals:
         row = Signal.compute(db, fixture_id, waypoint)
         INSERT OR REPLACE INTO signals_snapshot
       try/except 隔离：信号失败不阻塞 1) 的快照入库

[/api/signals/:type]
  → SELECT FROM signals_snapshot 按 strength 排序
  → 缓存 60s LRU

[/api/insights/mispricings] (旧)
  → 兼容层：内部 SELECT FROM signals_snapshot WHERE signal_type='GS-Mispricing'
    AND waypoint=（默认 kickoff 或最新可用），响应字段映射回旧 schema
```

### 信号读源契约（critical）

每个 Signal 的 `compute(db, fixture_id, waypoint)` **必须从带 waypoint 的历史表读，不读 upsert 的 live 表**：

| Signal | 读源（waypoint-stamped）| ⚠️ 不读 |
|--------|--------------------------|---------|
| `GS-Mispricing` | `historical_predictions(fixture_id, waypoint)` × `historical_odds(fixture_id, bookmaker_id=1, market_id=6, waypoint)` | ❌ `predictions`（upsert）/ ❌ `bookmaker_odds.current`（live） |
| `GS-OddsDrop` | `historical_odds` 按 waypoint 取相邻两点计算跌幅 | ❌ `odds_snapshots.drop_pct`（live 衍生字段，未来废弃） |
| `GS-LineMove` | `historical_odds` 按 waypoint 序列分析 | ❌ `bookmaker_odds.opening/current/peak`（混合时间语义） |
| `GS-SharpSquare` | `historical_odds` 同 waypoint 在 Pinnacle vs Bet365 上做 de-vig 对比 | ❌ `bookmaker_odds.current` |
| `GS-Predictability` | `fixtures.predictability`（赛前赋的标签，FT 后不可被改写——需 sync 层 audit）| — |
| `GS-H2HForm` | `fixtures` 自建 H2H（按 status='FT' 历史交手）| — |

**理由**：`predictions` 和 `bookmaker_odds` 是 upsert 表，T-48h 时刻读它们已经丢失彼时数据；
而 `historical_predictions / historical_odds` 在每个 waypoint 都写一行不可变快照。
只有从历史表读，"在 T-48h 时这个信号是什么值"才可被 #5 回测、可被 paper-trading House Book 跟单。

### Acceptance

1. 6 条信号每条至少 3 个 pytest 用例（典型 / 边界 / 缺数据），合成 fixtures 覆盖。
2. `historical_predictions × signals_snapshot` 在 5 waypoint × 30 场合成数据下完整率 100%。
3. 旧 endpoint 双跑 30 天，差异 = 0（pytest snapshot 比对）。
4. E2E：`/insights/signals` 在 0 信号 / 部分信号 / 全部信号 三态都不崩。
5. 6 份 `docs/signals/gs-*.md` 全部含【公式】【阈值含义】【典型场景】【已知失效】四节。

### Phasing

- **Phase A（2 周）**：抽象 + 实现 `GS-Mispricing` / `GS-Predictability` / `GS-OddsDrop` 三条（重构现有 endpoint），上 schema，新旧 endpoint 双跑。
- **Phase B（2 周）**：新实现 `GS-LineMove` / `GS-SharpSquare` / `GS-H2HForm` 三条，上 `/insights/signals` 统览页。
- **Phase C（30 天观察）**：与 #5 联动——每条信号在 backtest endpoint 里独立评估"信号触发后 hit rate / ROI / CLV"，淘汰证伪的信号 / 锁定有效的 v1.0。
- **Phase D（与 #1 联动）**：依据 paper-trading Phase C 的 ROI 证据决定哪些会员化，定价由 #1 PRD 拍板。
- **Phase E（与 #4 联动）**：`signals_snapshot` 直接作为自有模型特征表使用。

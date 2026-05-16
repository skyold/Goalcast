# 亚盘押注决策 MVP — 设计文档

- **日期**：2026-05-16
- **分支**：v2
- **数据源**：OddAlerts Football Data API（替代已弃用的 sportmonk / footystats）
- **参考能力清单**：[`docs/oddalerts-api.md`](../../oddalerts-api.md)
- **前置 spec**：[`2026-05-15-ui-overhaul-design.md`](./2026-05-15-ui-overhaul-design.md)（v2 UI 已完成）

---

## 1. 概述与目标

### 业务目标
让 Goalcast 成为「亚盘押注决策助手」。打开任一场赛事，5 秒内拿到亚盘下注判断所需的 **8 件事**：
1. 当前主流亚盘盘口 + 双家庄家赔率
2. 盘口移动（opening → current → peak）
3. 跌幅旗标
4. 模型胜平负 + 进球分布
5. 比分热力图
6. 两队赛季统计
7. 近 5 场 form
8. 联赛 predictability（风险等级）

### Gold Path
```
Matches 页（按 predictability 过滤、按跌幅排序）
  └─ MatchCard：Pinnacle/Bet365 盘口 + 跌幅 + form5 + 风险标
     └─ MatchDetail：模型胜率 + 7×7 比分热力图 + 两队统计全表
        └─ 决策（手动到博彩 App 或纸面记录）
```

### 非目标（明确不做）
- 实际投注（不接博彩 API）
- 亚盘走势折线（Phase 2）
- 角球/卡牌/球员盘（Phase 3）
- H2H 交锋记录（OddAlerts 无端点，永久搁置 T-DATA-2）
- live 滚球分析（非 MVP）

### KPI
- 时延：MatchCard 显示赔率 ≤ 5min 旧；predictions ≤ 6h 旧；form5 ≤ 24h 旧
- 覆盖：未来 7 天 9,700+ 场全部进库（vs 当前仅 ~600 场）
- 可用性：单个 sync job 挂掉不影响其他 job 数据可见

---

## 2. 数据模型

### 架构方案：纯增量加表
不动现有 `fixtures` / `odds_snapshots` / `sync_log`。新增 3 张表 + `fixtures` 加 1 列。

### 新表

#### `predictions`
来源：`/predictions/generate/:ID`。6h 刷新。

```sql
CREATE TABLE predictions (
  fixture_id INTEGER PRIMARY KEY,
  simulations INTEGER,                    -- 50000
  home_win INTEGER, draw INTEGER, away_win INTEGER,  -- 模拟次数
  btts INTEGER,
  o15_goals INTEGER, o25_goals INTEGER, o35_goals INTEGER, o45_goals INTEGER,
  scorelines TEXT,                        -- JSON: {"1-0":13.44, "2-0":11.87, ...}
  updated_at TEXT
);
```

#### `team_form`
来源：`/stats/season/:ID?last_x=5_overall`。6h 刷新（按 distinct season_id）。

```sql
CREATE TABLE team_form (
  team_id INTEGER,
  season_id INTEGER,
  form5_str TEXT,                         -- "WWLDW"
  played INT, won INT, drawn INT, lost INT,
  goals_for INT, goals_against INT, goals_avg REAL,
  updated_at TEXT,
  PRIMARY KEY (team_id, season_id)
);
```

查询时 `JOIN team_form ON team_id=fixtures.home_id AND season_id=fixtures.season_id`。不在 fixtures 上加 FK 列。

#### `bookmaker_odds`
来源：`/odds/history/:ID`（seed 一次）+ `/odds/latest`（5min 流式更新）。

```sql
CREATE TABLE bookmaker_odds (
  fixture_id INTEGER,
  bookmaker_id INTEGER,                   -- 1=Pinnacle, 2=Bet365
  market_id INTEGER,                      -- 6=ft_result, 51=asian_handicap
  outcome TEXT,                           -- 'home'/'draw'/'away' or 'home_m05'/'away_p05' …
  opening REAL,
  current REAL,
  peak REAL,
  opening_at TEXT,
  current_at TEXT,
  PRIMARY KEY (fixture_id, bookmaker_id, market_id, outcome)
);
CREATE INDEX idx_bo_fix ON bookmaker_odds(fixture_id);
CREATE INDEX idx_bo_fix_market ON bookmaker_odds(fixture_id, market_id);
```

### fixtures 表加 1 列
```sql
ALTER TABLE fixtures ADD COLUMN predictability TEXT;  -- 'high'|'good'|'medium'|'poor'|NULL
```

### 数据量估算
| 表 | 预计行数 | 依据 |
|---|---|---|
| `predictions` | ~3,000–6,000 | `/correctScores` 72h 实测 3,860；7 天外推 ~6,000；预跑过滤 `predictability='poor'` 实际更少 |
| `team_form` | ~3,000 | 7 天窗口内有 fixture 的 distinct season 数 |
| `bookmaker_odds` | ~175,000 | 9,700 场 × 2 家 × (3 个 1x2 outcome + ~6 个 AH outcome) |

总增量 ~190k 行，SQLite 完全可承受。

---

## 3. 同步架构

### 任务清单
| Job | 状态 | 频率 | API 调用/周期 | 作用 |
|---|---|---|---|---|
| `sync_fixtures_upcoming` | 新 | 1h | ~40 次（分页） | 主源切换：覆盖 9,703 场赛程 |
| `sync_dropping_odds` | 保留 | 5min | 1 次 | 已存在 |
| `sync_ah_odds_seed` | 新 | 触发式 | 1 次/新 fixture | 一次性拉 `/odds/history/:ID` 写 opening/peak |
| `sync_ah_odds_latest` | 新 | 5min | ~10 次（分页） | `/odds/latest?bookmakers=1,2&markets=6,51` 翻页到上次同步时间，更新 current |
| `sync_predictions` | 新 | 6h | ~240 次（批量） | `/predictions/generate/multiple?ids=…`，每批 25 |
| `sync_team_form` | 新 | 6h | ~500 次 | 按 distinct season_id |
| `sync_from_trends` | 保留 | 1h | 3 次 | 已存在，保留 trend flag 源 |

**总配额估算**：~300 次/小时，~5 次/分钟。文档无显式速率限制，实测 150ms 间隔无报错。

### 关键设计决定

1. **AH 赔率拉取混合策略**：单场 9,700 × 5min 不可能。
   - **seed**：新 fixture 第一次进库时调 `/odds/history/:fixture_id` 拿 opening + 当时 current
   - **stream**：每 5min 翻 `/odds/latest?bookmakers=1,2&markets=6,51&per_page=500` 找过去 5min 内的变动，更新对应 `bookmaker_odds.current`
   - API 调用从 9,700 砍到 ~10/周期

2. **predictions 用批量端点**：`/predictions/generate/multiple?ids=…`。**实施前需 spike 验证最大批次**（Postman 文档未明说，预设 25）。

3. **predictability 过滤**：sync_predictions 跳过 `predictability='poor'`，省 ~1/3 调用、且模型在 poor 联赛不准。

4. **错误隔离**：每个 job 独立 try/except 包住、独立写 `sync_log`、单 job 挂不影响其他。已存在的 `_log()` 机制复用。

5. **首次启动 backfill**：写成独立脚本 `backend/scripts/backfill.py`，按顺序跑：
   - `sync_fixtures_upcoming`（写满 fixtures）→
   - `sync_team_form`（拿到所有 season_id 后跑）→
   - `sync_ah_odds_seed` 对所有新 fixture 跑一遍 →
   - `sync_predictions`（按 predictability 过滤）
   - 估时 ~20 分钟完成首次填充

### 不动的部分
- `models/`、`database.py` 现有连接池逻辑
- `services/oddalerts.py` 的 5 个现有方法（保留，新增方法叠加）
- `odds_snapshots` 表（dropping odds 继续往里写）

---

## 4. 后端 API 契约

### 路由变化总览
| 路由 | 状态 | 改动 |
|---|---|---|
| `GET /fixtures` | 改 | 返回字段扩充；query 加 `predictability` / `min_drop` / `has_ai` |
| `GET /fixtures/{id}` | 改 | 返回字段大幅扩充，含 prediction、双家庄家全 AH 档、form |
| `GET /competitions` | 不动 | — |
| `GET /dropping-odds` | 不动 | — |
| `GET /value-bets` | 不动 | MVP 不动 |
| `GET /sync/*` | 不动 | — |

### `GET /fixtures` 响应（列表项）
```json
{
  "id": 420559890,
  "home_name": "Plaza Amador",
  "away_name": "UMECIT",
  "competition_name": "Lpf",
  "competition_country": "Panama",
  "predictability": "medium",
  "kickoff_utc": "...",
  "status": "pre",
  "home_form": {
    "form5": "WWLDW",
    "won": 3, "drawn": 1, "lost": 1,
    "gf": 8, "ga": 4
  },
  "away_form": { "...": "..." },
  "prediction_summary": {
    "home_win_pct": 57.3,
    "draw_pct": 23.97,
    "away_win_pct": 18.73,
    "btts_pct": 44.15,
    "o25_pct": 44.57
  },
  "odds": {
    "ft_result": {
      "pinnacle": {"home": 1.95, "draw": 3.40, "away": 4.20, "current_at": "..."},
      "bet365":   {"home": 1.91, "draw": 3.50, "away": 4.00, "current_at": "..."}
    },
    "asian_handicap": {
      "line": -0.5,
      "pinnacle": {
        "home_outcome": "home_m05", "home_odds": 1.85,
        "away_outcome": "away_p05", "away_odds": 1.95
      },
      "bet365": { "...": "..." }
    }
  },
  "drop_flag": {
    "market_key": "total_goals",
    "drop_percentage": 87.21
  }
}
```

任意字段在缺数据时可为 `null`。

### `GET /fixtures` query 参数
| 参数 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `date` | YYYY-MM-DD | 今天 | 已存在 |
| `leagues` | csv ints | — | 已存在；**改为非必需**，缺省时返回所有联赛 |
| `predictability` | csv | 缺省 | `high,good,medium,poor` 任意组合 |
| `min_drop` | float | 缺省 | 只返回跌幅 ≥ X 的场次 |
| `has_ai` | bool | false | 只返回 prediction 非空 |
| `status` | str | 缺省 | 已存在 |
| `limit` | int | 200 | 已存在；默认改 200 防 9,700 全返回 |

### `GET /fixtures/{id}` 响应
```json
{
  "fixture": {
    "id": 420559890,
    "predictability": "medium",
    "is_friendly": false, "is_cup": false,
    "season_progress": 97
  },
  "home_team": {
    "id": 14643, "name": "Plaza Amador",
    "stats": { "...": "/stats/fixture 70+ 项嵌套" },
    "form": { "form5": "WWLDW", "won": 3 }
  },
  "away_team": { "...": "..." },
  "prediction": {
    "simulations": 50000,
    "home_win_pct": 57.3, "draw_pct": 23.97, "away_win_pct": 18.73,
    "btts_pct": 44.15,
    "o25_pct": 44.57, "o35_pct": 23.40,
    "scorelines": {"1-0": 13.44, "2-0": 11.87},
    "updated_at": "..."
  },
  "odds": {
    "ft_result": {
      "pinnacle": {"home":1.95,"draw":3.40,"away":4.20,"opening":2.05,"current_at":"..."},
      "bet365":   { "...": "..." }
    },
    "asian_handicap_lines": [
      {
        "line": -0.5,
        "pinnacle": {"home":1.85,"away":1.95,"opening_home":1.92,"current_at":"..."},
        "bet365":   { "home": 1.82, "away": 2.05 }
      },
      {
        "line": -0.75,
        "pinnacle": { "home": 2.10, "away": 1.75 },
        "bet365":   { "home": 2.05, "away": 1.78 }
      }
    ]
  },
  "dropping_records": [
    {
      "market_key": "total_goals",
      "outcome": "under_15",
      "opening": 8.6,
      "closing": 1.1,
      "drop_pct": -87.21,
      "bookmaker": "Betfair Exchange",
      "recorded_at": "..."
    }
  ]
}
```

### 关键设计决定
1. **"主线档"由后端推导**：查 Pinnacle 所有 AH outcome，选 `|home_odds - away_odds|` 最小那档。列表页用统一展示，避免前端各家档位逻辑。无 AH 数据时返回 `asian_handicap: null`。
2. **无 deprecation 兼容层**：直接破坏式更新 `/fixtures` 响应（v2 还没发布、只有自家前端消费）。
3. **不开新路由**：所有数据嵌入两个现有路由响应里。Detail 一次请求拿齐所有信息。

---

## 5. 前端改动

### 改 Pages

#### `Matches.tsx` — 候选场次浏览
**Filter chips（在现有 leagues 之上）**：
- `predictability`：「排除 poor」「只看 high+good」两个快捷开关
- `min_drop`：「跌幅 ≥ 50%」
- `has_ai`：「只看有 AI 模型的」
- `leagues` 改非必需，默认拉所有联赛，按 predictability 排序
- 默认 `limit=200` + 「加载更多」按钮

**联赛分组**：保留现有，每组组头加 predictability 平均色阶条。

#### `MatchCard.tsx` — 候选卡片
**改后布局**（高度 120 → 200）：
```
┌─────────────────────────────────────────────────────────────┐
│ [predictability medium]   Plaza Amador  vs  UMECIT          │
│ Lpf · Panama · Thu 21st 08:30                  [跌 -87% ⚠]  │
│                                                              │
│ FORM:  WWLDW   ·   LWDWW                                    │
│                                                              │
│ AI:    主 57.3%  平 24.0%  客 18.7%   o2.5: 44.6%           │
│                                                              │
│ ┌─ Pinnacle ──────────┐ ┌─ Bet365 ──────────┐               │
│ │ 1.95 / 3.40 / 4.20  │ │ 1.91 / 3.50 / 4.00 │   ←1x2       │
│ │ AH -0.5  1.85/1.95  │ │ AH -0.5  1.82/2.05 │   ←亚盘主线 │
│ └─────────────────────┘ └────────────────────┘               │
└──────────────────────────────────────────────────────────────┘
```

**颜色规则**：
- predictability：high=绿、good=浅绿、medium=黄、poor=灰红
- form 字母：W=绿、D=黄、L=红
- 双家赔率差 > 5%：差大的一侧背景浅绿、另一侧浅红
- 跌幅 < -50%：警告红

**降级**：无 prediction → 隐藏 AI 行；无 AH → 显示「— 无亚盘」；无双家 → 单家展示。

#### `MatchDetail.tsx` — 单场分析
**自上而下 block 顺序**：
1. **Hero**（保留 + 加 predictability 标签 + 当前 AH 主线大字号显示）
2. **模型概率 block**：横向条形图 + 数字（home_win/draw/away_win + btts + o15/o25/o35/o45）。无模型时灰显「该场暂无 AI 模型」。
3. **★ 比分热力图 block**（killer feature）：
   - 7×7 网格（home goals 0–6+，away goals 0–6+）
   - 每格颜色深浅 ∝ 概率，hover 显示 "1-0 = 13.44%"
   - 覆盖一条斜线 / 区域标记，把当前选中的 AH 档切成「赢 / 和 / 输」三块，旁边列出三块概率合计
   - 顶部一个下拉切档（`AhLineSelector`），切换 -0.5 / -0.75 / -1，热力图标记实时重画
4. **赔率全表 block**：
   - 1x2：Pinnacle / Bet365 三路赔率 + 跌幅 + opening → current
   - 亚盘：所有档 × 两家 × home/away，opening / current 双栏
5. **两队赛季统计 block**：左右两列对比，复用现有 stats 渲染。加 form5 strip。
6. **跌赔历史 block**：该场所有 `dropping_records` 时间倒序，每条一个小条目。
7. **删除 H2H block**（永久无数据）。

#### `Dashboard.tsx` — 总览
最小改动：
- 把现有「总场次」tile 改为「未来 7 天候选 / 有 AI 模型 / predictability ≥ medium」三栏
- 加一个「今日 top 5 跌赔」list

### 不动 Pages
- `DroppingOdds.tsx`（已工作，可未来扩展双家切换）
- `ValueBets.tsx`（MVP 不动）
- `History.tsx`

### 新增 Components
| 组件 | 位置 | 用途 |
|---|---|---|
| `PredictabilityBadge` | `shared/` | 4 档颜色 pill 标签 |
| `FormStrip` | `match/` | 渲染 "WWLDW" 5 个彩色方块 |
| `OddsPair` | `match/` | 双家庄家赔率对比，自动算差值高亮 |
| `AhLineSelector` | `match/` | 详情页 AH 档下拉 |
| `ScorelineHeatmap` | `match/` | 7×7 比分概率热力图 + AH 切片覆盖 |
| `PredictionBars` | `match/` | 模型概率条形图 |
| `AhLineTable` | `match/` | 详情页所有 AH 档表格 |

### 改 / 不改 Components
- `ProbBar`：保留，用于 MatchCard 的 AI 三路 mini bar
- `MatchCard`：大改

### 类型层 `lib/api.ts`
```ts
type Predictability = 'high' | 'good' | 'medium' | 'poor' | null

type TeamForm = {
  form5: string
  won: number; drawn: number; lost: number
  gf: number; ga: number
}

type BookmakerOdds = {
  home: number; draw?: number; away: number
  opening?: number; current_at: string
}

type AsianHandicapLine = {
  line: number
  pinnacle: { home: number; away: number; opening_home?: number; opening_away?: number }
  bet365:   { home: number; away: number }
}

type Prediction = {
  simulations: number
  home_win_pct: number; draw_pct: number; away_win_pct: number
  btts_pct: number; o25_pct: number; o35_pct: number
  scorelines: Record<string, number>
  updated_at: string
}

type FixtureSummary = {
  id: number
  predictability: Predictability
  home_form: TeamForm | null
  away_form: TeamForm | null
  prediction_summary:
    | { home_win_pct: number; draw_pct: number; away_win_pct: number; btts_pct: number; o25_pct: number }
    | null
  odds: {
    ft_result: { pinnacle: BookmakerOdds; bet365: BookmakerOdds }
    asian_handicap: {
      line: number
      pinnacle: { home_outcome: string; home_odds: number; away_outcome: string; away_odds: number }
      bet365:   { home_outcome: string; home_odds: number; away_outcome: string; away_odds: number }
    }
  } | null
  drop_flag: { market_key: string; drop_percentage: number } | null
}

type FixtureDetail = Omit<FixtureSummary, 'odds'> & {
  prediction: Prediction | null
  odds: {
    ft_result: { pinnacle: BookmakerOdds; bet365: BookmakerOdds }
    asian_handicap_lines: AsianHandicapLine[]
  } | null
  home_team: { id: number; name: string; stats: unknown; form: TeamForm | null }
  away_team: { id: number; name: string; stats: unknown; form: TeamForm | null }
  dropping_records: Array<{
    market_key: string; outcome: string
    opening: number; closing: number; drop_pct: number
    bookmaker: string; recorded_at: string
  }>
}
```

### 设计系统增量（CSS className）
- `.predictability-high / -good / -medium / -poor` 配色
- `.odds-better / .odds-worse` 5% 差值高亮
- `.form-w / -d / -l` 字母颜色
- `.heatmap-cell` 灰度梯度（0% → 25%）

### 验证截图任务
spec 完成需要 4 张截图：
1. Matches 页带新 filter chips
2. MatchCard 新布局（带 predictability + 双家赔率 + form + drop flag）
3. MatchDetail 比分热力图 + AH 切片切换
4. MatchDetail 模型概率 + 赔率全表

---

## 6. 实施分期与里程碑

### M1 — 后端地基（~1 sprint）
**交付**：库结构 + 主源/赔率/form 同步可工作

任务：
- SQLite migration（`migrations/0002_*.sql`）：3 新表 + ALTER fixtures
- 实现 `sync_fixtures_upcoming`（1h）
- 实现 `sync_team_form`（6h，按 distinct season_id）
- 实现 `sync_ah_odds_seed`（fixture insert 触发，复用 `/odds/history/:ID`）
- 实现 `sync_ah_odds_latest`（5min，分页直到 unix < last_sync）
- 首次启动 backfill 脚本（按序跑 4 job）
- 每个 job 加 `services/sync.py` 单测（mock httpx）

**验收**：`/fixtures` 现有路由返回 fixtures 数 ≥ 5,000，`bookmaker_odds` ≥ 50k，`team_form` ≥ 1,500。

### M2 — Predictions + Backend API（~1 sprint）
**交付**：能从 API 拿到亚盘决策全部数据

任务：
- **预跑 spike**：验证 `/predictions/generate/multiple` 真实最大批次（25 / 50 / 100 测试）
- 实现 `sync_predictions`（6h，按 predictability!=poor 过滤）
- 实现「主 AH 档」推导函数
- 改 `GET /fixtures`：响应字段扩充，加 `predictability/min_drop/has_ai` 过滤
- 改 `GET /fixtures/{id}`：返回 prediction + 全 AH 档 + dropping_records + 双家 stats/form
- 集成测试覆盖空数据降级

**验收**：detail 接口对带 AI 模型的场次能返回完整 7×7 scorelines。

### M3 — 前端类型 + 共享组件 + MatchCard（~1 sprint）
**交付**：列表浏览体验全面升级

任务：
- 改 `lib/api.ts` 全部类型
- 新组件：`PredictabilityBadge`、`FormStrip`、`OddsPair`
- 改 `MatchCard.tsx`（高度 200，新布局如第 5 节图示）
- 改 `Matches.tsx`：filter chips（predictability / min_drop / has_ai）+ 加载更多
- 设计 token：CSS 加 `.predictability-*` / `.odds-better,-worse` / `.form-w,-d,-l`
- 视觉 QA + 截图

**验收**：MatchCard 在 ≥ 60% 场次能完整渲染（双家赔率 + form + drop + AI summary）。

### M4 — MatchDetail + 比分热力图（~1 sprint）
**交付**：亚盘核心决策面板

任务：
- 新组件：`AhLineSelector`、`AhLineTable`、`PredictionBars`
- **新组件 `ScorelineHeatmap`**（最复杂，预留 buffer 时间）：
  - 7×7 网格 + 颜色梯度
  - AH 切片覆盖逻辑
  - hover tooltip
- 改 `MatchDetail.tsx`：6 个 block 重排，删 H2H block
- 改 `Dashboard.tsx`（3 栏 tile + top 5 跌赔）
- 端到端验证 + 4 张截图归档

**验收**：5 场不同 predictability + 不同 AH 档场次，热力图渲染 < 200ms，切档 < 50ms。

### 时间线
| Milestone | 周期 | 后端 | 前端 | 阻塞下游 |
|---|---|---|---|---|
| M1 | 1 sprint | ✅ | — | M2 / M3 |
| M2 | 1 sprint | ✅ | — | M3 / M4 |
| M3 | 1 sprint | — | ✅ | M4 |
| M4 | 1 sprint | — | ✅ | — |

**总计 ~4 sprints**。M3 / M4 可在 M2 末尾用 mock 数据并行开工。

### 风险与缓解
| 风险 | 影响 | 缓解 |
|---|---|---|
| `/predictions/generate/multiple` 批次上限未知 | M2 同步效率 | M2 开头先做 spike 测试 |
| 「主 AH 档」推导对边界场次失败（无 AH outcome） | MatchCard 显示空 | 推导函数返回 `null`，UI 显示「— 无亚盘」 |
| 5min 同步 175k 行表频繁更新 | I/O 压力 | 加 `(fixture_id, bookmaker_id, market_id)` 复合索引，UPSERT 批处理 |
| `ScorelineHeatmap` 工作量超预期 | M4 延期 | M4 buffer 50%，可降级为表格视图 |
| 首次 backfill 长（~20min） | 首次部署体验 | backfill 写成独立脚本，部署前跑 |

### MVP 完成定义（DoD）
- 9,700+ fixtures 全部进库且每小时刷新
- `predictions` 表 ≥ 3,000 行（有 AI 模型场次）
- 至少 60% 候选场次能在 MatchCard 上看到「Pinnacle + Bet365」双家赔率
- 至少 80% 上线场次有 form5
- MatchDetail 比分热力图能在 200ms 内渲染、切档 < 50ms
- 4 张验收截图（M3 末 2 张、M4 末 2 张）入 `docs/`

---

## 附录 A — 取代的 T-DATA 任务

来自 [`2026-05-15-ui-overhaul-design.md`](./2026-05-15-ui-overhaul-design.md) 附录：

| 任务 | 当前状态 | 本 spec 解法 |
|---|---|---|
| T-DATA-1 form5 近 5 场 | 渲染空 | M1 `sync_team_form` + M3 `FormStrip` |
| T-DATA-2 H2H 交锋 | 渲染空状态 | **永久搁置**（OddAlerts 无端点） |
| T-DATA-3 opening 开盘价 | 不显示对比 | M1 `sync_ah_odds_seed` 写入 `bookmaker_odds.opening` + M4 赔率全表 block |
| T-DATA-4 1x2 三路赔率 | 显示 `—` | M1 `sync_ah_odds_*` 写入 `bookmaker_odds`（market_id=6）+ M3 MatchCard 渲染 |

---

## 附录 B — 关键 OddAlerts 端点速查

详见 [`docs/oddalerts-api.md`](../../oddalerts-api.md)。本 spec 用到的子集：

| 端点 | 用途 |
|---|---|
| `GET /fixtures/upcoming` | 主赛程源 |
| `GET /fixtures/:id` | 继续保留（本 spec 主要靠 upcoming） |
| `GET /stats/fixture/:ID` | MatchDetail 两队赛季统计 |
| `GET /stats/season/:ID?last_x=5_overall` | team_form |
| `GET /odds/history/:ID` | bookmaker_odds seed |
| `GET /odds/latest?bookmakers=1,2&markets=6,51` | bookmaker_odds 流式更新 |
| `GET /predictions/generate/multiple?ids=...` | predictions |
| `GET /odds/dropping` | 现有 dropping odds 保留 |
| `GET /competitions/:ID` | predictability 在 fixture 上有冗余字段，不必单独调 |

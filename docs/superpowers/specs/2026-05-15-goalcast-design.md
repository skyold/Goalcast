# Goalcast — 设计文档

**日期:** 2026-05-15  
**状态:** 已批准  
**数据源:** OddAlert API (`https://data.oddalerts.com/api`)  
**定位:** 个人足球数据分析与下注辅助工具，前后端分离

---

## 1. 目标

- 从 OddAlert 实时拉取比赛、赔率、跌水、趋势数据并持久化存储
- 任何时候都能从本地数据库重新加载历史快照，不依赖外部 API 可用性
- 提供美观的深色专业风格前端，参考 aibetting.me 视觉风格
- 个人单用户工具，无需认证

---

## 2. 技术栈

| 层 | 选型 |
|----|------|
| 后端 | Python 3.12 · FastAPI · APScheduler |
| 数据库 | SQLite (aiosqlite) |
| 前端 | React 18 · Vite · Tailwind CSS |
| HTTP 客户端 | httpx (async, follow_redirects=True) |
| 外部 API | OddAlert (`ODDALERTS_API_KEY` 在 `.env`) |

---

## 3. 页面结构

共 6 个页面，通过固定宽侧边栏（200px，图标 + 文字）切换：

| 页面 | 路由 | 说明 |
|------|------|------|
| Dashboard | `/` | 今日统计概览、Value Bets 精选、跌水警报、精选比赛卡片 |
| 比赛列表 | `/matches` | 双列卡片网格，按联赛分组，含日期/联赛筛选 |
| 比赛详情 | `/matches/:id` | 赔率历史、H2H、赛季数据对比、AI 趋势分析 |
| Value Bets | `/value-bets` | 按边际优势排序的投注机会列表 |
| 跌水监控 | `/dropping` | 赔率显著下跌的比赛，含变动轨迹 |
| 历史记录 | `/history` | 所有已存储比赛表格，含结果/预测/赔率 |

---

## 4. 数据模型

### 4.1 `fixtures` — 比赛基础信息

```sql
CREATE TABLE fixtures (
    id              INTEGER PRIMARY KEY,   -- OddAlert fixture ID
    competition_id  INTEGER NOT NULL,
    competition_name TEXT NOT NULL,
    home_team       TEXT NOT NULL,
    away_team       TEXT NOT NULL,
    home_team_id    INTEGER,
    away_team_id    INTEGER,
    kickoff_utc     DATETIME NOT NULL,
    status          TEXT DEFAULT 'pre',    -- pre | live | ft
    score_home      INTEGER,
    score_away      INTEGER,
    -- 预测概率 (0-1)
    prob_home_win   REAL,
    prob_draw       REAL,
    prob_away_win   REAL,
    -- 趋势标志
    trend_home_win  INTEGER DEFAULT 0,
    trend_away_win  INTEGER DEFAULT 0,
    trend_btts      INTEGER DEFAULT 0,
    -- 赛季统计 (JSON 存储)
    home_stats      TEXT,   -- JSON: {pos, wins, draws, losses, gf, ga, form5}
    away_stats      TEXT,   -- JSON: {pos, wins, draws, losses, gf, ga, form5}
    h2h             TEXT,   -- JSON: [{date, home, away, score_h, score_a}]
    -- 元数据
    fetched_at      DATETIME NOT NULL,
    updated_at      DATETIME NOT NULL
);
CREATE INDEX idx_fixtures_date_comp ON fixtures(date(kickoff_utc), competition_id);
CREATE INDEX idx_fixtures_status    ON fixtures(status);
```

### 4.2 `odds_snapshots` — 赔率历史快照

```sql
CREATE TABLE odds_snapshots (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    fixture_id  INTEGER NOT NULL REFERENCES fixtures(id),
    market      TEXT NOT NULL,    -- '1x2' | 'over25' | 'btts'
    bookmaker   TEXT NOT NULL,    -- 'bet365' | 'pinnacle' ...
    odds_home   REAL,
    odds_draw   REAL,
    odds_away   REAL,
    drop_pct    REAL,             -- 跌水幅度 (负值 = 赔率下降)
    drop_market TEXT,             -- 跌水市场方向: 'home'|'draw'|'away'
    recorded_at DATETIME NOT NULL
);
CREATE INDEX idx_odds_fixture ON odds_snapshots(fixture_id, recorded_at);
CREATE INDEX idx_odds_drop    ON odds_snapshots(drop_pct, recorded_at);
```

### 4.3 `sync_log` — 同步记录

```sql
CREATE TABLE sync_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    sync_type   TEXT NOT NULL,    -- 'dropping' | 'trends' | 'fixture_detail'
    status      TEXT NOT NULL,    -- 'ok' | 'error'
    records     INTEGER DEFAULT 0,
    error_msg   TEXT,
    started_at  DATETIME NOT NULL,
    finished_at DATETIME
);
```

---

## 5. 数据同步策略

### 5.1 后台定时任务 (APScheduler)

| 任务 | 频率 | 端点 |
|------|------|------|
| 跌水赔率 | 每 5 分钟 | `GET /odds/dropping` |
| 主胜/客胜/BTTS 趋势 | 每 5 分钟 | `GET /trends/{homeWin\|awayWin\|btts}` |
| 当日赛程发现 | 每小时 | `GET /fixtures/id` (discover) |

### 5.2 按需拉取 (用户触发)

- 点击比赛详情时：若 `updated_at < 10分钟前`，重新调用 `GET /fixtures/{id}?include=h2h,correctScores` 和 `GET /stats`
- 手动点击"刷新"按钮：立即触发一次全量同步

### 5.3 离线降级

- OddAlert 不可用时，所有接口返回最后一次缓存数据
- 响应头和前端均显示"数据来自 X 分钟前"
- 同步失败写入 `sync_log`，不抛出异常，不中断服务

---

## 6. 后端 API 接口

所有接口返回 JSON，前缀 `/api`。

```
GET  /api/fixtures
     ?date=2026-05-15          # 默认今天
     ?leagues=101,102,103      # competition_id 列表；比赛列表页必须传，
                               # Dashboard 传 Zustand store 中的已选联赛
     ?limit=10                 # 仅 Dashboard 精选时使用，其余页面不传（虚拟滚动处理全量）
     ?status=pre|live|ft       # 可选
     → { fixtures: [...], cached_at, total }

GET  /api/fixtures/:id
     → { fixture, odds_history, h2h, stats }

GET  /api/dropping-odds
     ?min_drop=10              # 最小跌幅%，默认 10
     ?market=home|draw|away    # 可选
     → { items: [...], synced_at }

GET  /api/value-bets
     ?min_edge=5               # 最小边际优势%，默认 5
     → { items: [...] }

GET  /api/history
     ?limit=50&offset=0
     ?league=101
     ?has_value_bet=true
     → { items: [...], total }

POST /api/sync/trigger
     → { started: true }
```

---

## 7. 前端架构

### 7.1 比赛列表性能方案

**筛选优先 + 虚拟滚动**（解决大量比赛的问题）：

1. **必须选联赛才请求数据** — `leagues` 参数为空时不发请求，显示"请先选择联赛"提示
2. **后端按 `(date, competition_id)` 索引查询** — 一次返回所选联赛当天全部比赛
3. **前端用 `@tanstack/virtual`** — 双列卡片网格虚拟化，仅渲染视口内卡片，滚动流畅
4. **数据库联合索引** — 查询响应 <10ms，即使 10k+ 历史记录

典型场景：用户选 5 个联赛，一天约 20-80 场，虚拟滚动轻松处理。极端场景（全选所有联赛 300+ 场）同样流畅，因为 DOM 节点始终只有视口内的卡片。

### 7.2 组件结构

```
src/
  pages/
    Dashboard.tsx
    Matches.tsx          # 筛选 + 虚拟卡片网格
    MatchDetail.tsx      # 赔率历史 + H2H + 数据对比
    ValueBets.tsx
    DroppingOdds.tsx
    History.tsx
  components/
    MatchCard.tsx        # v6 双列卡片（单个）
    MatchCardGrid.tsx    # @tanstack/virtual 虚拟网格
    LeagueFilter.tsx     # 按洲分组的联赛 pill 选择器
    DateFilter.tsx       # 今天/明天/后天/指定日期
    OddsHistory.tsx      # 赔率走势条形图
    ProbBar.tsx          # 主/平/客胜率条
  lib/
    api.ts               # 所有后端请求封装
    store.ts             # Zustand 全局状态
```

### 7.3 状态管理

使用 Zustand：
- `selectedLeagues: number[]` — 选中联赛 ID（持久化到 localStorage）
- `selectedDate: string` — 当前日期
- `syncStatus: { synced_at, is_syncing }` — 同步状态（前端每 30s 轮询）

---

## 8. 视觉设计规范

- **背景色:** `#060d1a`（页面）· `#070e1c`（主区域）· `#0d1626`（卡片）
- **边框色:** `#1a2d47`（卡片）· `#1e293b`（分隔线）
- **强调色:** `#22c55e`（主胜/正向）· `#f59e0b`（客胜/警告）· `#3b82f6`（信息）
- **Value Bet 色:** `#a855f7`
- **字体:** `-apple-system, 'Inter', sans-serif`
- **卡片:** 双列网格，圆角 10px，悬浮时蓝色边框高亮

### 比赛卡片结构 (v6 已批准)

```
[头部] 联赛旗帜 + 联赛名  |  开赛时间 + 状态标签
[主体] 主队(右对齐)        |  VS/比分  |  客队(左对齐)
       3字母色块 + 队名         平局%        3字母色块 + 队名
       联赛排名 + W/D/L积分    H2H记录      联赛排名 + W/D/L积分
       进/失球 + 场均球                      进/失球 + 场均球
       近5场 W/D/L 色块                      近5场 W/D/L 色块
       主场胜率%                             客场胜率%
[胜率条] ████ 主胜% ░ 平% ░ 客胜%
[底部] Bet365 主/平/客赔率  |  跌水幅度  |  趋势标签
```

---

## 9. 错误处理原则

- **API 不可用:** 返回缓存数据，前端显示数据时间戳
- **无数据:** 显示空状态（"当天无比赛"或"请选择联赛"）
- **网络超时:** httpx timeout=10s，失败记录 sync_log，等下次定时任务重试
- **前端加载态:** 骨架屏（Skeleton），减少布局抖动

---

## 10. 不在范围内

- 用户认证 / 多用户
- 实际下注功能（仅分析辅助）
- 移动端响应式（桌面优先）
- 推送通知
- 多数据源（仅 OddAlert）

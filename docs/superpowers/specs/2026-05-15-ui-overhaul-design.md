# Goalcast UI Overhaul — 设计文档

**日期:** 2026-05-15
**状态:** 已批准
**背景:** 当前实现与 2026-05-15 批准的 v6 设计稿存在显著差距，本文档定义将全部 6 个页面对齐设计稿所需的所有变更。

---

## 1. 目标

将所有前端页面完整还原至批准的 `matches-v6.html` / `all-pages-preview.html` 设计稿，包括：
- CSS 架构从 inline style 迁移到全局 CSS class 体系
- 每个页面的布局、组件结构、颜色、间距与设计稿完全一致
- 缺失数据字段优雅降级（不显示或显示"暂无"占位），**不** 在本阶段补充数据接口

---

## 2. CSS 架构变更

### 方案：设计系统 CSS 提取到 `index.css`

将设计稿所有 CSS class 整体迁移至 `frontend/src/index.css`，组件改用 `className`，**不引入新 npm 依赖**。

**核心 CSS class 体系（来自设计稿）：**

```css
/* 布局 */
.layout, .sidebar, .main, .page-header

/* 侧边栏 */
.sidebar-logo, .logo-icon, .logo-text
.nav-item, .nav-item.active, .nav-icon, .nav-section, .nav-spacer
.sync-status, .sync-dot

/* 通用控件 */
.btn, .btn-primary, .btn-secondary
.chip, .chip.active
.pill, .pill.sel, .pill.all-pill
.sort-select
.badge, .bg, .ba, .bb, .bp, .br

/* 比赛卡片 v6 */
.mcard, .mcard.live
.mc-hdr, .mc-hdr-lname, .mc-hdr-time, .mc-status
.st-pre, .st-live, .st-ft
.mc-body
.mc-team, .mc-team.home, .mc-team.away
.t-namerow, .t-abbr, .t-fullname
.t-record, .t-pos, .t-wdl
.t-goals, .g-for, .g-sep, .g-ag, .g-avg
.t-form, .fp, .fp.W, .fp.D, .fp.L
.t-winpct, .t-winpct.h, .t-winpct.a, .t-winlbl
.mc-center, .mc-vs-txt, .mc-score, .mc-draw, .mc-drawlbl
.mc-divider, .mc-h2h
.mc-probbar, .pb-wrap, .pb-home, .pb-draw, .pb-away
.pb-labels, .pbl
.mc-ftr, .odds-box, .ob, .ob.hot, .ob .ol, .ob .ov
.ftr-sep, .drop-col, .drop-val, .drop-mkt, .badges

/* Dashboard */
.stats-grid, .stat-card, .stat-label, .stat-value, .stat-sub
.dash-section, .dash-section-title, .dash-2col
.alert-card, .alert-icon, .alert-match, .alert-detail, .alert-tags

/* 比赛详情 */
.detail-area, .detail-hero, .detail-teams-row
.detail-team, .detail-abbr, .detail-tname, .detail-record, .detail-center
.detail-grid, .detail-card, .detail-card-title
.oh-row, .oh-time, .oh-bar-wrap, .oh-bar, .oh-val
.h2h-row, .h2h-date, .h2h-match, .h2h-score, .h2h-res
.res-h, .res-a, .res-d
.sc-row, .sc-lbl, .sc-bars, .sc-h, .sc-a, .sc-vl, .sc-vr

/* Value Bets */
.vb-list, .vb-card, .vb-rank, .vb-match, .vb-teams, .vb-meta, .vb-stat
.vb-stat-val, .vb-stat-lbl

/* 跌水监控 */
.do-list, .do-card, .do-hdr, .do-body
.do-teams, .do-matchname, .do-league
.do-track, .do-track-lbl, .do-track-row, .do-old, .do-new
.do-pct, .do-pct-val, .do-pct-mkt

/* 历史记录 */
.hist-table, .hist-filters
.rw, .rd, .rl, .td-match, .td-score, .td-drop

/* 比赛列表 */
.matches-area, .league-group, .league-title, .league-name, .league-count
.match-grid

/* 滚动条 */
::-webkit-scrollbar, ::-webkit-scrollbar-track, ::-webkit-scrollbar-thumb
```

---

## 3. 文件变更清单

| 文件 | 操作 |
|------|------|
| `src/index.css` | 全量替换为设计系统 CSS |
| `src/components/layout/Sidebar.tsx` | 重写：渐变 logo + 图标导航 + 底部同步状态 |
| `src/components/match/MatchCard.tsx` | 重写为完整 v6 结构 |
| `src/components/match/ProbBar.tsx` | 迁移为 className 版本 |
| `src/pages/Matches.tsx` | 重写：内联筛选 + 联赛分组 |
| `src/pages/Dashboard.tsx` | 重写：stat 卡片 + 警报 + 精选比赛 |
| `src/pages/MatchDetail.tsx` | 重写：hero + 2列网格 |
| `src/pages/ValueBets.tsx` | 重写：排名列表 |
| `src/pages/DroppingOdds.tsx` | 重写：卡片式 + 赔率轨迹 |
| `src/pages/History.tsx` | 重写：完整表格 + 筛选 chip |

不新建文件，不新增 npm 依赖。

---

## 4. 各页面详细设计

### 4.1 Sidebar（`src/components/layout/Sidebar.tsx`）

```
[Logo 区] .sidebar-logo
  .logo-icon (渐变 linear-gradient(135deg,#3b82f6,#22c55e), 30px, radius:8px) ⚽
  .logo-text "Goalcast"

[导航项] .nav-item (width:200px)
  ⊞  Dashboard      → /
  📋 比赛列表       → /matches
  💎 Value Bets     → /value-bets
  📉 跌水监控       → /dropping
  .nav-section "数据"
  🕒 历史记录       → /history

[底部] .sync-status
  .sync-dot (6px 绿圆) + "同步于 X 分钟前"
```

active 状态：`background:#22c55e18; color:#22c55e`；通过 `useLocation()` 判断当前路由。

同步时间：从 Zustand store 的 `syncStatus.synced_at` 计算，每 30s 更新显示。

### 4.2 MatchCard v6（`src/components/match/MatchCard.tsx`）

```
┌─ .mc-hdr (background:#09111f) ────────────────────────────┐
│  [flag] [.mc-hdr-lname 联赛名]   [.mc-hdr-time] [.mc-status]│
├─ .mc-body ─────────────────────────────────────────────────┤
│  .mc-team.home          .mc-center(54px)   .mc-team.away   │
│  .t-namerow(row-rev)    .mc-vs-txt "VS"    .t-namerow      │
│  .t-abbr(彩色28px)      .mc-draw draw%     .t-abbr(彩色)   │
│  .t-fullname(95px max)  .mc-drawlbl "平局" .t-fullname     │
│  .t-record(pos+WDL)     .mc-divider        .t-record       │
│  .t-goals(进/失/均)     .mc-h2h H2H        .t-goals        │
│  .t-form(W/D/L方块)     (有数据才显示)      .t-form         │
│  .t-winpct.h 大号%                          .t-winpct.a %  │
│  .t-winlbl "主场胜率"                        .t-winlbl      │
├─ .mc-probbar ──────────────────────────────────────────────┤
│  [.pb-home] [.pb-draw] [.pb-away] + .pb-labels            │
│  (prob_home_win===null 时不渲染整个 probbar 区域)            │
├─ .mc-ftr (background:#09111f) ────────────────────────────┤
│  .odds-box [主.ob] [平.ob] [客.ob]  .ftr-sep               │
│  .drop-col [.drop-val] [.drop-mkt]  .badges               │
└───────────────────────────────────────────────────────────┘
```

**队徽颜色：** 对已知球队（英超、西甲等大联赛）使用品牌色，其余用 `hsl(从队名哈希生成)` 保证每队颜色稳定。

**数据降级规则：**
- `form5 === []` → 不渲染 `.t-form` 行
- `h2h === []` 或无 H2H → 不渲染 `.mc-h2h`
- `odds_home === null` → `.ob .ov` 显示 `—`
- `prob_home_win === null` → 不渲染 `.mc-probbar`
- `drop_pct === null` → `.drop-col` 显示 `—`

**状态：**
- `pre` → `.st-pre` "未开赛"
- `live` → `.st-live` "● 进行中"（pulse 动画；header 背景 `#071a10`；时间文字 `#22c55e`）
- `ft` → `.st-ft` "已结束"

### 4.3 Matches 页（`src/pages/Matches.tsx`）

**布局改为全宽，不再有子侧边栏。**

```
[page-header]
  左: "比赛列表" + 副标题
  右: "↻ 刷新" .btn.btn-secondary

[filter-section] padding:12px 28px; border-bottom
  行1 日期筛选:
    label "日期" | 今天.chip.active | 明天.chip | 后天.chip | 📅指定日期.chip
    (选"指定日期"后显示 <input type="date">)
  行2 联赛筛选:
    label "联赛" | [全选.pill.all-pill] [全不选.pill]
    🌍 欧洲 → [含"Premier/Liga/Bundesliga/Serie/Ligue/Champions/Europa/Eredivisie/Primeira/Lig/Scottish"的联赛]
    🌎 美洲 → [含"MLS/Liga MX/Brasileirao/Copa"的联赛]
    🌏 亚洲 → [含"J1/K League/CSL/A-League/AFC/Saudi"的联赛]
    其他 → 剩余联赛
  行3 排序 + 计数:
    排序下拉 [开赛时间 | 跌水幅度 | 主胜概率] | 共 N 场 · 已选 M 个联赛

[matches-area] padding:16px 28px
  无联赛选中 → 居中提示 "请先在左侧选择联赛以加载比赛数据"
  加载中 → Skeleton 骨架屏（2列）
  有数据 → .league-group × 每个联赛
    .league-title  [flag emoji] [.league-name] [.league-count N场]
    .match-grid 2列 MatchCard（虚拟滚动保留）
```

**排序逻辑（前端）：**
- 开赛时间：按 `kickoff_utc` 升序（分组内排序）
- 跌水幅度：按 `drop_pct` 升序（绝对值最大在前）
- 主胜概率：按 `prob_home_win` 降序

**联赛分组：** 前端按 `competition_name` 分组，同名的卡片在一组。联赛标题 flag emoji 复用 `LeagueFilter` 的大洲判断逻辑。

### 4.4 Dashboard（`src/pages/Dashboard.tsx`）

```
[page-header] Dashboard | "今日数据概览 · YYYY年M月D日" | 刷新按钮

[stats-grid] 4列
  今日比赛数 (fixtures.total)  绿色副文字"● N 场进行中"
  Value Bets 数 (value-bets count)  紫色数值
  跌水警报数 (dropping-odds count)  绿色数值
  已存储比赛 (history.total via GET /api/history?limit=0)  蓝色数值

[dash-section] 💎 今日 Value Bets
  [dash-2col] 最多 4 条 .alert-card（border-color:#a855f733）
    .alert-icon 💎 (purple bg)
    .alert-match 队名 vs 队名
    .alert-detail 联赛 · 时间 · 方向
    .alert-tags [边际+X%] [赔率N.NN] [概率N%]

[dash-section] 📉 最新跌水警报
  [dash-2col] 最多 4 条 .alert-card（border-color:#22c55e33）
    .alert-icon ↓ (green bg)
    .alert-match 队名 vs 队名
    .alert-detail 联赛 · 时间/状态
    .alert-tags [XXX跌 ↓N%] [赔率变化]

[dash-section] 📋 今日精选比赛
  [match-grid] 最多 4 张精选 MatchCard（已选联赛当日前4场）
```

**数据来源：** `/api/fixtures?limit=4&leagues=...`、`/api/value-bets`、`/api/dropping-odds`。无已选联赛时精选比赛区域显示提示。

### 4.5 MatchDetail（`src/pages/MatchDetail.tsx`）

```
[page-header]
  左: "比赛详情" + "联赛 · 日期时间"
  右: [← 返回列表] [↻ 刷新]

[detail-hero] .detail-hero
  [detail-teams-row]
    [主队.detail-team] 52px队徽 + 队名 + "Nth · NW ND NL · 进N 失N" + form5
    [中间.detail-center] 时间 + 日期 + 联赛 + 状态 badges（Value/BTTS等）
    [客队.detail-team] 同上
  [概率条 height:8px] + 主/平/客 % 文字
  [赔率行] [主胜.ob.hot] [平局.ob] [客胜.ob] [跌水.ob（绿色bg）]

[detail-grid] 2列 .detail-card
  [赔率历史] .oh-row 列表（时间 + 横向条形 + 值）
    有 odds_history → 每条记录一行
    无 → "暂无赔率历史记录"
  [H2H 记录] .h2h-row 列表
    有 h2h → 日期 + 队名 + 比分 + 主/平/客结果标签
    无 → "暂无 H2H 交锋记录"
  [赛季数据对比] .sc-row 列表
    进球 / 失球 / 主场胜率% / 场均球数 / 客场胜率%（双向对比条形）
    数据来自 home_stats / away_stats
  [趋势分析] 动态文字卡片
    有 drop_pct < -10 → 显示跌水分析段落
    有 trend_home_win/away_win/btts → 显示对应趋势段落
    有 edge_pct（从 `/api/value-bets` 获取全量数据后客户端按 `fixture_id` 过滤）→ 显示 Value Bet 分析段落
    三项均无 → "暂无分析数据"
```

### 4.6 ValueBets（`src/pages/ValueBets.tsx`）

```
[page-header]
  左: "Value Bets" + "边际优势 ≥ N% 的投注机会 · 今日 N 个"
  右: chip 筛选 [全部] [主胜] [客胜] [平局]

[vb-list] .vb-list
  [vb-card × N 按 edge_pct 降序]
    .vb-rank N（紫色圆圈）
    .vb-match: .vb-teams 主队 vs 客队; .vb-meta 联赛 · 时间
    .vb-stat: 方向文字（主胜/平局/客胜）
    .ob.hot: 赔率值
    .vb-stat: 概率% (purple)
    .vb-stat: +edge% (green)
    .badges: 趋势标签

空状态 → "当前无符合条件的 Value Bets"
```

### 4.7 DroppingOdds（`src/pages/DroppingOdds.tsx`）

```
[page-header]
  左: "跌水监控" + "赔率显著下跌的比赛"
  右: chip 筛选 [所有市场] [主胜] [大球] [客胜]
      最小跌幅 select [5%|10%|15%|20%]

[do-list] .do-list
  [do-card × N 按 drop_pct 升序]
    [do-hdr]
      左: [flag] [联赛名] [状态标签.mc-status]
      右: 记录时间（几分钟前）
    [do-body]
      .do-teams: .do-matchname 主 vs 客; .do-league 联赛名
      .do-track:
        .do-track-lbl "XXX赔率变动"
        .do-track-row: (opening 待后续) → .do-new 当前值 + 时间标注
        注：opening 字段待 T-DATA-3 完成后补充 .do-old 显示
      .do-pct: .do-pct-val ↓N%; .do-pct-mkt 市场方向
      .badges: 趋势标签
```

### 4.8 History（`src/pages/History.tsx`）

```
[page-header]
  左: "历史记录" + "已存储比赛数据 · 共 N 场"
  右: chip 筛选 [全部] [有跌水]（联赛 chip 从 competitions 列表动态生成，最多显示 top 8）

[hist-table] .hist-table
  <table>
    thead: 日期 | 比赛 | 联赛 | 比分 | 趋势标签 | 跌水 | 操作
    tbody: 每行
      日期（MM/DD）
      .td-match 主队 vs 客队
      联赛名
      .td-score 比分（status=ft 时显示，否则"—"）
      趋势 badges
      .td-drop 跌水幅度（有则显示）
      （点击行跳转到 /matches/:id）

无数据 → "暂无已完成比赛记录"
```

---

## 5. 缺失数据后续任务（UI 完成后处理）

以下任务**不在本次 UI 工作范围内**，记录在实施计划中作为独立后续任务：

| 任务 ID | 字段 | 描述 | UI 当前降级方式 |
|---------|------|------|----------------|
| T-DATA-1 | `form5` 近5场 | 调查 OddAlerts 哪个接口有 recent form 数据 | 不渲染 `.t-form` 行 |
| T-DATA-2 | `h2h` 交锋记录 | 验证 `/fixtures/{id}?include=h2h` 是否返回 H2H | 显示"暂无 H2H 交锋记录" |
| T-DATA-3 | `opening` 开盘价 | 跌水接口的 `opening` 字段存入 `odds_snapshots` | 只显示当前价+跌幅 |
| T-DATA-4 | `odds_home/draw/away` | 调查 `/odds` 接口获取三路 1x2 赔率 | 显示 `—` |

---

## 6. 不在范围内

- 移动端响应式（桌面优先）
- 新增 API 接口或后端数据库结构变更
- 引入新 npm 依赖
- 任何数据接口补充（见第 5 节后续任务）

# Goalcast · OddAlert-Only Pivot — Design Spec

**Date**: 2026-05-14
**Status**: Draft (awaiting user review)
**Scope**: 重大架构调整 — 收敛到 OddAlerts 单数据源 + 全新浏览优先 UI，同时保留自研分析层。

---

## 1. Background & Motivation

需求变化：

1. **agent 不是必须** — 自研分析仍保留，但 agent 编排不再是产品卖点，沦为后台跑分析的实现细节。
2. **数据源收敛到 OddAlerts 单源** — FootyStats / Sportmonks / Understat 全部下线。
3. **需要完整浏览页** — 参考 [aibetting.me](https://aibetting.me/)，展示赛程、赔率、联赛、跌水、趋势等。
4. **美观显示** — 沿用 Goalcast 暗色绿主题（`#00FF9D`）。

产品定位：「多源 + Agent 量化平台」→「**OddAlerts 数据浏览站 + 自研分析增强**」。

## 2. Goals / Non-Goals

### Goals
- 删除三个非 OddAlerts provider 及其融合层。
- 保留并改造 `analytics/`（poisson / ev_calculator / confidence）— 入参来自 OddAlerts。
- 保留 `agents/` RD 循环 — `data_collector` 单源化，输出回写 `match_store`。
- 实现 10+ 类新页面：浏览主页、完整赛事详情页、跌水榜、趋势榜、列表视图、联赛主页、球队主页、分析报告、Pipeline 监控、收藏、设置。
- 移动端响应式。
- 沿用 React + Ant Design + 现有暗色主题。

### Non-Goals
- 不引入新 UI 库（保持 Ant Design）。
- 不重写 LLM provider 抽象。
- 不改账户系统。
- 不集成博彩平台下注 API（订单仅本地记录）。
- 不做国际化（暂时中文）。

## 3. Architecture

### 3.1 Data Flow
```
OddAlerts API
   ├─→ HTTP API 层（新, 供新前端）
   │     /api/competitions
   │     /api/fixtures?date=&competition_id=
   │     /api/fixtures/{id}             (聚合: fixture+odds_history+h2h+stats+trends)
   │     /api/trends/{home_win|away_win|btts|over25}
   │     /api/odds/dropping
   │     /api/teams/{id}
   │     /api/leagues/{id}/standings
   │
   └─→ agents/core/data_collector.py（改造：仅 oddalerts）
         └─→ analytics
               ├─ poisson.py        (xG → λ → P(H/D/A))
               ├─ ev_calculator.py  (closing 价 → EV/Kelly)
               └─ confidence.py     (trends 概率作先验)
                     └─→ Orchestrator → Analyst → Trader → Reviewer → Reporter
                           └─→ match_store（推荐/EV/置信回写）
                                 └─→ 新前端浏览页"自研徽章"读取
```

### 3.2 Backend Module Changes
| 模块 | 操作 |
|---|---|
| `backend/provider/footystats/` | **删除** |
| `backend/provider/sportmonks/` | **删除** |
| `backend/provider/understat/` | **删除** |
| `backend/provider/oddalerts/` | **保留**（核心） |
| `backend/services/datafusion/` | **删除** |
| `backend/services/sportmonks/` | **删除** |
| `backend/provider/base.py` | 简化为 oddalerts 直通薄层 |
| `backend/agents/core/fixture_merger.py` | 简化为 oddalerts 数据归一化 |
| `backend/agents/core/data_collector.py` | 单源化 |
| `backend/analytics/poisson.py` | 入参改用 OddAlerts `/api/stats` 字段 |
| `backend/analytics/ev_calculator.py` | 用 `/api/odds/history.closing` 计算 |
| `backend/analytics/confidence.py` | 用 OddAlerts `trends.{homeWin,awayWin,btts}` 作先验 |
| `backend/agents/`（5 个角色） | **保留**，只换数据源 |
| `backend/server/routes/`（5 路由） | **保留**，新增 `browse.py` |
| `backend/mcp_server/` | **保留** |
| `main.py` 的 RD 循环 CLI | **保留** |

### 3.3 New HTTP API Layer
新增模块：`backend/server/routes/browse.py`

| Endpoint | 数据来源 | 缓存 TTL |
|---|---|---|
| `GET /api/competitions` | oddalerts `/api/competitions` | 24h |
| `GET /api/fixtures?date=&competition_id=` | oddalerts `/api/odds/dropping` + `competitions` 拼装 | 5min |
| `GET /api/fixtures/{id}` | oddalerts 多端点聚合（沿用 `OddAlertsProvider.collect_fixture_data`） | 5min（近场）/ 不可变（已结束） |
| `GET /api/trends/{type}` | oddalerts `/api/trends/{type}` | 15min |
| `GET /api/odds/dropping?market=&min_drop=&window=` | oddalerts `/api/odds/dropping` | 5min |
| `GET /api/teams/{id}` | oddalerts `/api/stats?type=season&id=` | 6h |
| `GET /api/leagues/{id}/standings` | oddalerts 或 fixture 聚合 | 6h |
| `GET /api/analysis/recent?limit=` | `match_store` | 实时 |
| `POST /api/analysis/run` | 触发 Orchestrator 一轮 | — |

**速率限制**：单点 token bucket，默认 280 req/min（300 上限预留 20 给后台分析）。

**缓存层**：sqlite 文件缓存 `backend/data/cache.db`：
```sql
CREATE TABLE cache (
  key TEXT PRIMARY KEY,
  value BLOB,
  expires_at INTEGER,
  created_at INTEGER
);
```

### 3.4 Frontend Routes
```
/                       → BettingPage (新主页，替代 /dashboard 默认重定向)
/fixture/:id            → FixtureDetailPage
/dropping               → DroppingOddsPage
/trends/:type           → TrendsPage (默认 home_win)
/league/:id             → LeaguePage
/team/:id               → TeamPage
/analysis               → AnalysisReportsPage (旧 BoardPage 重命名)
/analysis/pipeline      → PipelineMonitor (保留)
/analysis/chat          → ChatPanel (保留，可选)
/my                     → FavoritesPage
/my/bets                → BetHistoryPage
/settings               → SettingsPage
/legacy/dashboard       → DashboardPage (保留至验收)
/legacy/board           → BoardPage (旧)
```

**侧导航 SideNav 分两组**：「浏览」(主页/跌水/趋势/联赛) 与 「分析」(报告/Pipeline/对话)。

## 4. Page Specifications

所有页面在 `.superpowers/brainstorm/80848-1778739816/content/` 下有 HTML mockup 参考：
- `betting-page-v1.html` — 主页 + 详情抽屉
- `more-views-v1.html` — 完整详情页 / 跌水榜 / 趋势榜 / 列表视图 / 移动端
- `extra-pages-v1.html` — 联赛主页 / 球队主页 / 分析报告 / Pipeline / 收藏 / 设置

### 4.1 BettingPage `/`
- 顶栏：Logo + 主导航 + OddAlerts 配额状态
- 左侧栏 (240px)：搜索 + 快捷分组（今日/关注/跌水/高 EV）+ 联赛树（按国家折叠 + 国旗 + 计数）
- 顶部筛选：日期 + 市场切换（1X2/BTTS/O-U/亚盘/角球）+ 趋势 chips + 卡片/列表切换
- 赛程网格：按联赛分组；卡片含联赛 + KO + 队徽队名 + 三路赔率（最优高亮，含涨跌幅）+ OddAlerts 概率彩条 + 跌水/EV 徽章 + 自研推荐星级
- 详情抽屉（点卡片）：自研分析 + 赔率曲线 + H2H + 统计；底部「查看完整页面」跳 `/fixture/:id`

### 4.2 FixtureDetailPage `/fixture/:id`
- Hero：双队头像 + KO + 跌水/EV 徽章 + 收藏/重新分析按钮 + breadcrumb
- KPI 行 (5 卡)：市场 P(H) / OddAlerts 模型 P(H) / 自研 Poisson P(H) / EV / Kelly
- Tab：概览 / 赔率深度 / 赔率曲线 / 统计对比 / H2H / 球员阵容 / 自研分析 / JSON 原始
- 主区：市场深度表（10 家博彩并排）+ 其他市场快览 + 完整统计 + H2H
- 右栏：自研推荐卡（含 Analyst/Reviewer 报告片段）+ OddAlerts 趋势 + 相关比赛 + 运行历史

### 4.3 DroppingOddsPage `/dropping`
- 表格：KO / 联赛 / 对阵 / 市场 / 开盘 / 当前 / 跌幅（可视化条）/ 博彩 / 自研徽章
- chips 过滤：市场、跌幅阈值（≥5%/≥8%/≥12%）、时间窗口（1h/6h/24h）

### 4.4 TrendsPage `/trends/:type`
- 4 个 tab：主胜 / 客胜 / BTTS / 大球
- 卡片网格：排名 + 概率大数字 + 概率条 + 赔率/EV/自研星级

### 4.5 LeaguePage `/league/:id`
- Hero：联赛 logo + 元信息 + KPI（今日/本周/高EV/跌水）
- Tab：赛程 / 积分榜 / 射手榜 / 球队 / 本轮趋势
- 主区赛程表 + 积分榜；右栏本轮高 EV + 射手榜 + 联赛趋势

### 4.6 TeamPage `/team/:id`
- Hero：队徽 + 联赛排名 + 近 5 场色块 + KPI
- Tab：概览 / 近期比赛 / 即将比赛 / 统计数据 / 球员阵容
- 主区即将比赛 + 近 5 场含 xG；右栏赛季统计 + 队内射手 + **自研对此队推荐胜率**（基于历史推荐回测）

### 4.7 AnalysisReportsPage `/analysis`
- Header：触发新一轮 + 过滤 chips（全部/已下注/已结算/高 EV）
- Summary 条：近 7 天 / 已下注 / 已结算 / 命中率 / 累计 ROI
- 列表：每行 = 推荐 + EV + 状态（待开赛/已下注/✓命中/✗未中）+ 置信度

### 4.8 PipelineMonitor `/analysis/pipeline`
- 顶部 KPI 行（轮次/比赛/推荐/Token/冷却倒计时）
- 轮次卡片：6 阶段 stage bar（Orchestrator → Data → Analyst → Trader → Reviewer → Reporter）+ 实时日志
- 失败轮次卡片含错误日志 + 重试时间

### 4.9 FavoritesPage `/my`
- 4 tab：关注比赛 / 关注联赛 / 关注球队 / 下注记录
- 下注记录表格：日期/比赛/市场/赔率/仓位/结果/盈亏 + 累计行

### 4.10 SettingsPage `/settings`
- 左侧分组导航
- 配置组：
  - OddAlerts API：Token / 速率限制 / 缓存 TTL / 健康检查
  - LLM 提供商：保留现有 anthropic/openai
  - 分析参数：概率混合权重（Poisson / OddAlerts trends / 市场隐含，∑=1）/ 最低 EV / 最低置信度 / 分析间隔
  - 资金/Kelly：Bankroll / Kelly 分数 / 单注上限 / 日累计上限
  - 联赛过滤 / 通知 / 显示偏好 / 缓存
  - Legacy 数据源：只读展示「已删除」

### 4.11 Mobile Responsive (≤390px)
- 主页：日期横滑 + chips 横滑 + 紧凑卡片 + 底部 5-tab bar（浏览/跌水/趋势/推荐/我的）
- 详情页：单列展示，KPI 横滑
- 列表/榜单：行高加大，关键列优先

## 5. Frontend Component Inventory

### 新建
| 文件 | 用途 |
|---|---|
| `pages/BettingPage.tsx` | 主页 |
| `pages/FixtureDetailPage.tsx` | 完整详情 |
| `pages/DroppingOddsPage.tsx` | 跌水榜 |
| `pages/TrendsPage.tsx` | 趋势榜（4 tab） |
| `pages/LeaguePage.tsx` | 联赛主页 |
| `pages/TeamPage.tsx` | 球队主页 |
| `pages/AnalysisReportsPage.tsx` | 分析报告（替代 BoardPage） |
| `pages/FavoritesPage.tsx` | 我的关注 |
| `pages/BetHistoryPage.tsx` | 下注记录 |
| `pages/SettingsPage.tsx` | 设置 |
| `components/LeagueTree.tsx` | 左栏联赛树 |
| `components/FixtureCard.tsx` | 赛程卡片 |
| `components/FixtureDetailDrawer.tsx` | 详情抽屉 |
| `components/OddsCurveChart.tsx` | 赔率曲线（SVG 自实现，避免大依赖） |
| `components/StatsCompare.tsx` | 统计对比条 |
| `components/H2HTable.tsx` | H2H 表格 |
| `components/AnalysisBadge.tsx` | EV + 置信度星级 |
| `components/MarketDepthTable.tsx` | 多博彩深度表 |
| `components/StandingsTable.tsx` | 积分榜 |
| `components/MobileTabBar.tsx` | 底部 tab bar |

### 改造
- `App.tsx`：路由重写
- `layouts/AppLayout.tsx`：SideNav 分两组（浏览/分析）
- `components/SideNav.tsx`：分组化

### 归档至 `pages/legacy/`
- `BoardPage.tsx`、`DashboardPage.tsx`、`MatchSourcePanel.tsx`、`AgentDetailDrawer.tsx`、`ChatPanel.tsx`、`TokenStatsPage.tsx`

## 6. Backend Implementation Tasks

### Phase 1: Provider 裁剪
1. 删除 `backend/provider/{footystats,sportmonks,understat}/`
2. 删除 `backend/services/{datafusion,sportmonks}/`
3. 清理 `provider/__init__.py` 与 base 抽象
4. 清理 `agents/core/fixture_merger.py` 多源逻辑
5. ruff + pytest 通过

### Phase 2: Analytics 适配
1. `poisson.py` 输入适配器：从 OddAlerts stats 抽取 xG/进失球率
2. `ev_calculator.py`：closing 价取自 `/api/odds/history`
3. `confidence.py`：trends 概率作先验，混合权重读自 settings
4. 单元测试 ≥80% 关键路径

### Phase 3: HTTP API 层
1. 新建 `backend/server/routes/browse.py`
2. 实现 9 个端点（§3.3）
3. sqlite 缓存模块 `backend/utils/cache.py`
4. token-bucket 速率限制 middleware
5. 端点集成测试

### Phase 4: Agent 单源化
1. `data_collector.py` 仅调 oddalerts
2. 输出回写 `match_store` 附带 model_prob / market_prob / ev / kelly / confidence
3. 跑一轮 RD 烟雾测试

### Phase 5: Frontend 骨架
1. 路由重写 + SideNav 分组
2. 主页骨架（联赛树 + 顶栏筛选 + 占位卡片网格）
3. 接入 `/api/competitions` + `/api/fixtures`

### Phase 6: 主流程页面
1. 赛程卡片 + 详情抽屉
2. `FixtureDetailPage`
3. 赔率曲线 SVG 组件

### Phase 7: 列表与榜单
1. `DroppingOddsPage`
2. `TrendsPage`（4 tab）
3. 列表视图切换

### Phase 8: 联赛/球队/分析/我的/设置
1. 五个剩余页面
2. 收藏功能（localStorage + 后端可选持久化）

### Phase 9: 移动端响应式
1. 顶栏汉堡化 + 底部 tab bar
2. 卡片紧凑模式
3. 横滑日期/筛选

### Phase 10: 清理
1. 删除 `pages/legacy/*`
2. 删除三个 provider 残留测试与配置
3. 更新 README

## 7. Data Model

`match_store` 项增加自研字段：
```python
{
  "fixture_id": int,
  # ... 原有字段
  "analysis": {                      # 新增
    "model_prob": {"H": 0.621, "D": 0.197, "A": 0.182},
    "market_prob": {"H": 0.581, "D": 0.260, "A": 0.159},
    "pick": "H",
    "odds": 1.72,
    "ev": 0.068,
    "kelly": 0.024,
    "confidence_stars": 4,
    "analyst_summary": "...",
    "reviewer_verdict": "pass",
    "run_id": "0042",
    "analyzed_at": "2026-05-14T10:19:25Z"
  }
}
```

## 8. Risks & Mitigations
| 风险 | 缓解 |
|---|---|
| OddAlerts 速率限制 300/min 不够 | 缓存 + 后台预取 + 用户配额预留 20 |
| `/api/fixtures/between` 实测为空 | 用 dropping_odds 反向推赛程，或扫描 competitions+fixtures/id |
| analytics 旧入参与 oddalerts 字段不匹配 | 加适配层；缺失字段时**跳过比赛**（保守策略）|
| 69KB `MatchSourcePanel.tsx` 拆分困难 | 不拆，直接归档 legacy |
| Legacy import 残留 | Phase 10 统一清理，配合 ruff/eslint |
| 自研分析与浏览解耦不彻底 | `match_store` 作为唯一桥梁 |

## 9. Acceptance Criteria
- 浏览主页能展示当日 OddAlerts 赛程，含赔率/跌水/概率/自研徽章
- 点击卡片打开抽屉，再点「查看完整页面」进入 `/fixture/:id`
- 跌水/趋势两个独立榜单可访问，含过滤
- 联赛/球队主页可访问
- RD 循环跑一轮后，浏览页卡片显示自研 EV/星级徽章
- Pipeline 监控页实时显示运行状态
- 设置页可修改 OddAlerts Token、分析参数、Kelly 参数
- 移动端 (390px) 主页可用
- 三个旧 provider 在仓库与运行时均无残留
- 测试覆盖率 ≥ 70%（关键路径 ≥ 80%）

---

**下一步**：用户审阅本文档 → 修正 → 进入 `superpowers:writing-plans` 生成实施计划。

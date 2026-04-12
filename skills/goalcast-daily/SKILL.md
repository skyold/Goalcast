---
name: goalcast-daily
description: Use this skill when the user wants to run today's daily analysis workflow, get a list of today's matches for a specific provider, or run batch analysis across all watchlist leagues.
---

# Goalcast Daily — 每日工作流入口

版本：1.0 | 职责：解析今日赛程 → 数据预热（可选）→ 转交 goalcast-compare 分析

## 触发条件

- "分析今天的比赛"
- "用 sportmonks+v3.0 跑今天英超的分析"
- "今天有哪些比赛？"
- 定时任务调用（批量模式）

## 执行步骤

### Step 0（批量时推荐）：数据预热

当分析场数 > 3 或用户明确要求批量时，先预热数据：

```
goalcast_prefetch_today(
    data_provider=<provider>,
    leagues=<watchlist 中的联赛列表 或 用户指定>,
    date=今天
)
```

输出：`已预热 N 场比赛数据，缓存写入 data/cache/`

**单场分析跳过此步骤**，直接从 Step 1 开始。

### Step 1：解析分析组合

从用户输入中提取：

| 参数 | 提取方式 | 默认值 |
|------|---------|-------|
| data_provider | "sportmonks"/"footystats" in 输入 | "sportmonks" |
| model | "v2.5"/"v3.0" in 输入 | "v3.0" |
| league_filter | 联赛名 in 输入 | None（全部） |
| date | YYYY-MM-DD in 输入 | 今天 |

如提取不到 data_provider，询问（单次，不重复）：
> "请问使用哪个数据源？A) sportmonks  B) footystats"

### Step 2：获取今日赛程

```
goalcast_get_todays_matches(
    data_provider=<data_provider>,
    date=<date>,
    league_filter=<league_filter>
)
```

展示赛程（时间升序）：
```
今日比赛（Premier League | sportmonks）

 1. Arsenal vs Chelsea           20:00
 2. Liverpool vs Man City        17:30
 3. Tottenham vs Newcastle       15:00
 ...
```

无比赛时：回复"今日 [联赛名] 暂无比赛安排"，停止。

### Step 3：用户选场（交互模式）或自动批量（无人值守模式）

**交互模式**（用户在线）：
- "分析第 2 场" → 单场
- "分析所有比赛" → 全部
- "分析前 3 场" → 指定数量

**无人值守模式**（定时任务调用，参数中含 `batch=true`）：
- 自动选择全部比赛
- 跳过交互，直接进入 Step 4

### Step 4：转交 goalcast-compare

调用 goalcast-compare，传入：

```
matches: [
  {home_team, away_team, competition, date},
  ...
]
combinations: [(data_provider, model)]   ← 本次组合
match_type: "A"                          ← 默认，可由用户指定
```

goalcast-compare 负责：
- 批量规模检查（>10 子 agent 时确认）
- 并行调度子 agent
- 收集结果 + 输出报告

### Step 5（可选）：保存结果

如用户要求持久化（或在 .env 中设置 `GOALCAST_PERSIST_RESULTS=true`）：
- 从各子 agent 的 AnalysisResult JSON 中提取关键字段
- 调用内部存储层写入 `data/reports/` 和 `data/analysis.db`

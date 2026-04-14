---
name: goalcast-daily
description: Use this skill when the user wants to analyze all matches today (or on a specific date) for one or more leagues using Goalcast v4.0. Triggers include "analyze today's matches", "run daily analysis", "analyze EPL/Championship/Serie A today".
---

# Goalcast Daily — V4.0 每日批量分析入口

版本：2.0 | 数据层：Sportmonks（固定）| 分析模型：V4.0（固定）
职责：解析目标联赛 → 拉取赛程 → 按场次调度 goalcast-analyzer-v40

## 可用 MCP 工具（仅以下 1 个）

| 工具 | 用途 |
|------|------|
| `goalcast_sm_get_fixtures` | 获取指定日期 + 联赛的全部赛程 |

分析工具由 goalcast-analyzer-v40 负责，本 skill 不调用计算工具。

## 支持的联赛名称

```
"Premier League"   英格兰超级联赛
"Championship"     英格兰冠军联赛
"Serie A"          意大利甲级联赛
"La Liga"          西班牙甲级联赛
"Bundesliga"       德国甲级联赛
"Ligue 1"          法国甲级联赛
```

## 执行步骤

### Step 1：解析请求

从用户输入中提取：

| 参数 | 提取方式 | 默认值 |
|------|---------|-------|
| `leagues` | 联赛名 in 输入（支持中英文） | 无默认，必须明确 |
| `date` | YYYY-MM-DD in 输入 | 今天 |
| `match_type` | A/B/C/D in 输入 | "A" |

**中英文联赛名映射**：
- 英超 / EPL → "Premier League"
- 英冠 → "Championship"
- 意甲 / 意大利 → "Serie A"
- 西甲 → "La Liga"
- 德甲 → "Bundesliga"
- 法甲 → "Ligue 1"

如果无法确定联赛，询问（一次）：
> "请确认要分析的联赛：A) 英超  B) 英冠  C) 意甲  D) 其他"

### Step 2：获取赛程

调用：
```
goalcast_sm_get_fixtures(
    leagues = <联赛名列表>,   # 如 ["Premier League", "Championship", "Serie A"]
    date    = <date>,
)
```

展示赛程（按开球时间升序，按联赛分组）：

```
今日赛程（2026-04-14）

Premier League（N 场）
  1. Arsenal vs Chelsea          20:00
  2. Liverpool vs Man City        17:30

Championship（N 场）
  3. Leeds vs Sheffield Wed      19:45

Serie A（N 场）
  4. Juventus vs AC Milan        21:00
  ...

共 N 场比赛
```

无比赛时：回复"今日 [联赛名] 暂无赛程"，停止。

### Step 3：确认分析范围

**用户已明确"全部"/"所有比赛"**：跳过询问，直接 Step 4。

**其他情况**询问：
> "共 N 场，全部分析，还是指定场次？（输入编号如 1,3 或回复'全部'）"

**无人值守模式**（定时任务 / 参数含 `batch=true`）：自动选全部。

### Step 4：逐场调度 goalcast-analyzer-v40

对每场比赛，传入完整参数调用 goalcast-analyzer-v40：

```
fixture_id    = <fixture.fixture_id>
home_team     = <fixture.home_team>
home_team_id  = <fixture.home_team_id>
away_team     = <fixture.away_team>
away_team_id  = <fixture.away_team_id>
season_id     = <fixture.season_id>
league        = <fixture.league>
match_date    = <date>
kickoff_time  = <fixture.kickoff_time>
match_type    = <match_type>
```

**顺序执行**（不并行）：每场完成后立即输出，再进入下一场。
任意一场报错时注明"[比赛名] 分析失败：[原因]"，继续下一场。

### Step 5：汇总输出

全部场次完成后输出：

```markdown
## 今日分析汇总（N 场）

| 比赛 | 联赛 | 最优投注 | EV_adj | 置信度 | 推荐 |
|------|------|---------|--------|--------|------|
| Arsenal vs Chelsea | EPL | 主胜 | +0.12 | 74 | ✅ 推荐 |
| Liverpool vs Man City | EPL | 平局 | +0.06 | 61 | 🔸 小注 |
| Leeds vs Sheff Wed | Championship | — | — | 55 | ❌ 不推荐 |

推荐：X 场 ｜ 小注：X 场 ｜ 不推荐：X 场
```

仅 `bet_rating != "不推荐"` 的场次展示具体投注方向和 EV_adj。

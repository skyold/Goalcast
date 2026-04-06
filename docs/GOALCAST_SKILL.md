# Goalcast MCP — 标准分析工作流

## 单场比赛分析（推荐）

```
1. footystats_get_todays_matches(date, league_filter="Premier League")
   → 获取当日目标联赛比赛，拿到 match_id 列表

2. footystats_get_match_details(match_id)
   → 获取单场赔率、H2H、阵容、进球时间，足够做量化分析
```

## 联赛深度分析

```
1. footystats_get_league_tables(season_id)   → 积分榜 + 当前战绩
2. footystats_get_league_teams(season_id)    → 所有球队统计
3. footystats_get_team_last_x_stats(team_id) → 近期状态（5/6/10 场）
```

## Season ID 速查（2025/26 赛季）

| 联赛     | season_id |
|----------|-----------|
| 英超     | 15050     |
| 德甲     | 14968     |
| 西甲     | 14956     |
| 意甲     | 15068     |
| 法甲     | 14932     |
| 欧冠     | 14924     |

## 数据量警告

| 工具                          | 风险    | 缓解措施                        |
|-------------------------------|---------|--------------------------------|
| `get_todays_matches` (无过滤) | 高      | 传 `league_filter` 参数        |
| `get_league_matches`          | 高      | 改用 todays→match_details 流程 |
| `get_btts_stats`              | 中      | 直接使用，无需特殊处理          |
| `get_match_details`           | 低      | 单场数据，安全                  |

## 不推荐用法

- ❌ `get_league_matches` 获取完整赛程（超限风险）
- ❌ `get_todays_matches` 不带 `league_filter` 分析单联赛
- ✅ 替代：`get_todays_matches(league_filter=...)` → `get_match_details`

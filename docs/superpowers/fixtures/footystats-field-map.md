# FootyStats 真实字段映射

> 探索日期：2026-04-07
> 测试比赛：Arsenal vs AFC Bournemouth（match_id: 8223599）
> 联赛：England Premier League（competition_id: 15050）

---

## get_todays_matches → data[] 中的比赛对象

返回结构：`{ success, pager, metadata, data: [...], message }`，`data` 是比赛对象数组。

- match ID：`id`（示例值：8223599）
- 主队 ID：`homeID`（示例值：59，Arsenal）
- 客队 ID：`awayID`（示例值：148，AFC Bournemouth）
- 主队名称：`home_name`（示例值："Arsenal"）
- 客队名称：`away_name`（示例值："AFC Bournemouth"）
- season（赛季字符串）：`season`（示例值："2025/2026"，**字符串，不是数字 ID**）
- 联赛/赛季 ID（用于 league_tables/league_matches）：`competition_id`（示例值：15050）
- 比赛日期（Unix 时间戳）：`date_unix`（示例值：1775907000，对应 2026-04-11 11:30 UTC）

> 注：`get_todays_matches` 返回的比赛对象**已包含完整赔率字段**（与 `get_match_details` 相同）。
> **没有独立的数字 season_id 字段**，联赛/积分榜查询使用 `competition_id`。

---

## get_match_details → 赔率字段

返回结构：`{ success, pager, metadata, data: {...}, message }`，`data` 是单个比赛对象（dict）。

赔率字段直接在 `data` 顶层，**无嵌套**：

- 主队赔率（主场胜）：`data.odds_ft_1`（示例值：1.34，Arsenal 主场胜）
- 平局赔率：`data.odds_ft_x`（示例值：5.78）
- 客队赔率（客场胜）：`data.odds_ft_2`（示例值：10.4，AFC Bournemouth 客场胜）
- 赔率可用：**是**（字段存在且有值，为 float 类型）

其他赔率字段（同在顶层）：
- `data.odds_ft_over25`：大于 2.5 球（示例值：1.6）
- `data.odds_btts_yes`：双方都进球（部分比赛为 0，表示暂未开放）
- `data.odds_1st_half_result_1/x/2`：半场结果赔率
- `data.odds_comparison`：多家博彩公司赔率对比（嵌套 dict，键如 "FT Result"、"Goals Over/Under" 等）

---

## get_match_details → H2H 数据

`data.h2h` 是一个嵌套 dict：

```
data.h2h = {
  "team_a_id": 59,
  "team_b_id": 148,
  "previous_matches_results": {  # 汇总统计，不是比赛列表
    "team_a_win_home": 7,
    "team_a_win_away": 6,
    "team_b_win_home": 2,
    "team_b_win_away": 1,
    "draw": 3,
    "team_a_wins": 13,
    "team_b_wins": 3,
    "totalMatches": 19,
    "team_a_win_percent": 68,
    "team_b_win_percent": 16
  },
  "betting_stats": {  # H2H 投注统计
    "over05", "over15", "over25", ...,
    "btts", "avg_goals", "total_goals", ...
  },
  "previous_matches_ids": [  # 历史比赛 ID 列表（含进球数）
    {"id": 8223544, "date_unix": 1767461400, "team_a_id": 148, "team_b_id": 59,
     "team_a_goals": 2, "team_b_goals": 3},
    ...
  ]
}
```

---

## get_match_details → 球队赛季统计（如有）

`get_match_details` **不返回球队赛季进球统计**。这些数据需通过 `get_team_last_x_stats` 获取。

- 主队赛季进球（来自 match_details）：不可用
- 客队赛季进球（来自 match_details）：不可用

---

## get_team_last_x_stats → 近况字段

**调用方式**：`get_team_last_x_stats(team_id=59)`

返回结构：`{ success, pager, metadata, data: [...], message }`

**data 是一个数组，包含 3 个对象**，分别对应不同时间窗口：
- `data[0]`：`last_x_match_num: 5`（近 5 场，overall）
- `data[1]`：`last_x_match_num: 6`（近 6 场，overall）
- `data[2]`：`last_x_match_num: 10`（近 10 场，overall）

> ⚠️ 建议按 `last_x_match_num` 值遍历匹配目标对象，不要依赖数组下标（API 不保证返回顺序）

每个对象结构：
```
{
  "id": 59,
  "name": "Arsenal",
  "last_x_match_num": 5,
  "last_x_home_away_or_overall": 0,  // 0=overall
  "stats": { ... }
}
```

### stats 对象中的关键字段

进球/失球总数（用于手动计算均值）：
- 近 N 场进球总数：`stats.seasonGoals_overall`（last5=6，last10=17）
- 近 N 场失球总数：`stats.seasonConceded_overall`（last5=5，last10=10）
- 近 N 场出场总数：`stats.seasonMatchesPlayed_overall`（last5=5，last10=10）

**场均进球（API 直接提供）**：
- 场均进球：`stats.seasonScoredAVG_overall`（last5=1.2，last10=1.7）
- 场均失球：`stats.seasonConcededAVG_overall`（last5=1.0，last10=1.0）
- 场均总球数：`stats.seasonAVG_overall`（last5=2.2，last10=2.7）
- 积分均值：`stats.seasonPPG_overall`（last5=1.4，last10=1.8）

其他分类统计（均在 `stats` 顶层）：
- `stats.seasonGoals_home` / `stats.seasonGoals_away`：主/客场进球
- `stats.seasonCS_overall`：零封场次
- `stats.seasonBTTS_overall`：双方进球场次
- `stats.seasonWinsNum_overall`：胜场数

> 数据结构层级：`data[N].stats.<字段名>`，**无额外嵌套**。

---

## get_league_tables → 积分榜字段

**调用方式**：`get_league_tables(season_id=15050)`（使用 `competition_id`）

返回结构：`{ success, pager, metadata, data: {...}, message }`

`data` 包含多个表：
- `data.league_table`：**主要积分榜**，20 支球队（英超等常规联赛有值；UCL 等杯赛为 null）
- `data.all_matches_table_overall`：全部比赛积分榜，与 `league_table` 内容相同（英超为 20 队）
- `data.all_matches_table_home`：主场成绩榜（list）
- `data.all_matches_table_away`：客场成绩榜（list）
- `data.specific_tables`：分轮次/组别的专项榜（list）

> ℹ️ 对于英超等常规联赛，优先使用 `data.league_table`（有值）。UCL 等杯赛 `league_table` 为 null，需回退到 `all_matches_table_overall`。

### league_table 中每支球队的字段

- 球队积分：`points`（示例：Arsenal 70 分）
- 排名：`position`（示例：Arsenal position=1，第 1 名）
- 球队名称：`name`（示例："Arsenal FC"）
- 球队 ID：`id`（示例：59）
- 场均积分：`ppg_overall`（示例：2.26）
- 总进球：`seasonGoals`（示例：61）
- 总失球：`seasonConceded`（示例：22）
- 出场数：`matchesPlayed`（示例：31）
- 胜/平/负：`seasonWins_overall`、`seasonDraws_overall`、`seasonLosses_overall`

---

## 测试比赛信息（供后续 Task 使用）

| 字段 | 值 |
|------|----|
| 主队名 | Arsenal |
| 客队名 | AFC Bournemouth |
| match_id | 8223599 |
| home_team_id（homeID） | 59 |
| away_team_id（awayID） | 148 |
| competition_id（用于 league_tables） | 15050 |
| season（字符串） | "2025/2026" |
| 联赛 | England Premier League |
| 日期（Unix） | 1775907000（2026-04-11 11:30 UTC） |

---

## 重要说明

1. **无独立数字 season_id**：`get_todays_matches` 的 `season` 字段是字符串（"2025/2026"），`competition_id` 才是传给 `get_league_tables` 和 `get_league_matches` 的整数 ID。
2. **赔率字段平铺在顶层**：`data.odds_ft_1/x/2` 无需嵌套路径，直接读取。
3. **get_team_last_x_stats 返回数组**：通过 `last_x_match_num` 区分 5/6/10 场数据；**不要依赖数组下标**，应遍历数组匹配 `last_x_match_num` 目标值。
4. **league_table 因联赛类型而异**：英超等常规联赛 `data.league_table` 有值（20 队），UCL 等杯赛为 null，此时应回退使用 `all_matches_table_overall`。
5. **get_match_details 已包含赔率**：无需额外调用，`get_todays_matches` 返回的比赛对象也已含完整赔率字段。

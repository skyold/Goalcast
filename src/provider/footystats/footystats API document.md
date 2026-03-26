# FootyStats API 完整文档

> 本文档整合了 FootyStats API 的所有端点说明、参数和响应示例

---

## 目录

1. [入门指南](#入门指南)
2. [基础端点](#基础端点)
   - [联赛列表](#联赛列表)
   - [国家列表](#国家列表)
   - [每日比赛](#每日比赛)
3. [联赛数据端点](#联赛数据端点)
   - [联赛统计](#联赛统计)
   - [联赛比赛](#联赛比赛)
   - [联赛球队](#联赛球队)
   - [联赛球员](#联赛球员)
   - [联赛裁判](#联赛裁判)
   - [联赛积分榜](#联赛积分榜)
4. [详细数据端点](#详细数据端点)
   - [比赛详情](#比赛详情)
   - [球队详情](#球队详情)
   - [球队近况统计](#球队近况统计)
   - [球员详情](#球员详情)
   - [裁判详情](#裁判详情)
5. [统计数据端点](#统计数据端点)
   - [BTTS 统计](#btts 统计)
   - [Over 2.5 统计](#over-25-统计)

---

## 入门指南

### API 基础信息

- **基础 URL**: `https://api.football-data-api.com/`
- **认证方式**: API Key（通过 `key` 参数传递）
- **响应格式**: JSON
- **请求方法**: GET

### 通用参数

- `key`: 您的 API 密钥（必需）
- `season_id`: 联赛赛季 ID
- `match_id`: 比赛 ID
- `player_id`: 球员 ID
- `referee_id`: 裁判 ID

---

## 基础端点

### 联赛列表

获取 API 数据库中所有可用的联赛列表。

**请求示例**:
```
GET https://api.football-data-api.com/league-list?key=YOURKEY
```

**查询参数**:

| 参数名 | 类型 | 描述 |
|--------|------|------|
| chosen_leagues_only | string | 如果设置为 "true"，只返回用户选择的联赛 |
| key* | string | 您的 API 密钥 |
| country | integer | 国家的 ISO 编号，用于筛选特定国家的联赛 |

**响应示例**:
```json
{
    "success": true,
    "data": [
        {
            "name": "USA MLS",
            "season": [
                {
                    "id": 1,
                    "year": 2016
                },
                {
                    "id": 16,
                    "year": 2015
                },
                {
                    "id": 1076,
                    "year": 2018
                }
            ]
        }
    ]
}
```

**返回字段说明**:

| 字段 | 描述 |
|------|------|
| name | 联赛名称 |
| league_name | 不含国家的联赛名称 |
| country | 国家名称 |
| season > id | 赛季 ID |
| season > year | 赛季年份 |

---

### 国家列表

获取国家列表及其 ISO 编号，常用于筛选其他端点的结果。

**请求示例**:
```
GET https://api.football-data-api.com/country-list?key=YOURKEY
```

**查询参数**:

| 参数名 | 类型 | 描述 |
|--------|------|------|
| key* | string | 您的 API 密钥 |

**响应示例**:
```json
{
    "success": true,
    "data": [
        {
            "id": 4,
            "name": "Afghanistan"
        },
        {
            "id": 901,
            "name": "Africa"
        },
        {
            "id": 248,
            "name": "Åland Islands"
        },
        {
            "id": 8,
            "name": "Albania"
        }
    ]
}
```

**返回字段说明**:

| 字段 | 描述 |
|------|------|
| id | 国家 ID |
| name | 国家名称 |

---

### 每日比赛

获取按日期排列的比赛列表。

**请求示例**:
```
GET https://api.football-data-api.com/todays-matches?key=YOURKEY
```

**查询参数**:

| 参数名 | 类型 | 描述 |
|--------|------|------|
| timezone | string | 时区，例如 `&timezone=Europe/London`，默认 Etc/UTC |
| date | string | 日期格式 YYYY-MM-DD，例如 `&date=2020-07-30` |
| key* | string | 您的 API 密钥 |

**响应示例**:
```json
{
    "success": true,
    "pager": {
        "current_page": 1,
        "max_page": 1,
        "results_per_page": 200,
        "total_results": 2
    },
    "data": [
        {
            "id": 579362,
            "homeID": 155,
            "awayID": 93,
            "season": "2019/2020",
            "status": "incomplete",
            "roundID": 50055,
            "game_week": 37,
            "homeGoalCount": 0,
            "awayGoalCount": 0,
            "team_a_corners": -1,
            "team_b_corners": -1,
            "odds_ft_1": 8.75,
            "odds_ft_x": 5.8,
            "odds_ft_2": 1.33
        }
    ]
}
```

**返回字段说明**:

| 字段 | 描述 |
|------|------|
| id | 比赛 ID |
| homeID | 主队 ID |
| awayID | 客队 ID |
| season | 联赛赛季 |
| status | 比赛状态（complete/suspended/canceled/incomplete） |
| game_week | 比赛周次 |
| homeGoalCount | 主队进球数 |
| awayGoalCount | 客队进球数 |
| team_a_corners | 主队角球数 |
| team_b_corners | 客队角球数 |
| odds_ft_1 | 主队胜赔率 |
| odds_ft_x | 平局赔率 |
| odds_ft_2 | 客队胜赔率 |

---

## 联赛数据端点

### 联赛统计

获取联赛赛季统计数据和参与的球队信息。

**请求示例**:
```
GET https://api.football-data-api.com/league-season?key=YOURKEY&season_id=X
```

**查询参数**:

| 参数名 | 类型 | 描述 |
|--------|------|------|
| max_time | integer | UNIX 时间戳，返回指定时间之前的统计数据 |
| key* | string | 您的 API 密钥 |
| season_id* | integer | 联赛赛季 ID |

**响应示例**:
```json
{
    "success": true,
    "data": [
        {
            "id": "161",
            "division": "1",
            "name": "Premier League",
            "shortHand": "premier-league",
            "country": "England",
            "type": "Domestic League",
            "iso": "gb-eng",
            "continent": "eu",
            "clubNum": 20,
            "year": "20172018",
            "season": "2017/2018",
            "totalMatches": 380,
            "matchesCompleted": 380,
            "total_goals": 1072,
            "seasonAVG_overall": 2.82,
            "btts_matches": 189,
            "seasonBTTSPercentage": 49.7
        }
    ]
}
```

**主要返回字段**:

| 字段 | 描述 |
|------|------|
| id | 赛季 ID |
| name | 联赛名称 |
| country | 国家名称 |
| clubNum | 参赛球队数量 |
| season | 赛季描述 |
| totalMatches | 总比赛数 |
| matchesCompleted | 已完成比赛数 |
| total_goals | 总进球数 |
| seasonAVG_overall | 场均进球数 |
| btts_matches | 双方进球场次数 |
| seasonBTTSPercentage | 双方进球百分比 |

---

### 联赛比赛

获取指定联赛的完整比赛赛程。

**请求示例**:
```
GET https://api.football-data-api.com/league-matches?key=YOURKEY&season_id=1
```

**查询参数**:

| 参数名 | 类型 | 描述 |
|--------|------|------|
| page | integer | 分页，每页默认 500 场比赛 |
| max_per_page | integer | 每页最大比赛数，最高 1000 |
| max_time | integer | UNIX 时间戳 |
| key* | string | 您的 API 密钥 |
| season_id* | integer | 联赛赛季 ID |

**响应示例**:
```json
{
    "success": true,
    "data": [
        {
            "id": 49347,
            "homeID": 1002,
            "awayID": 1003,
            "season": "2017",
            "status": "complete",
            "roundID": "245",
            "game_week": "1",
            "homeGoalCount": 3,
            "awayGoalCount": 2,
            "team_a_corners": 3,
            "team_b_corners": 5,
            "team_a_shotsOnTarget": 9,
            "team_b_shotsOnTarget": 10,
            "team_a_possession": 34,
            "team_b_possession": 66,
            "btts": true,
            "over25": true
        }
    ]
}
```

---

### 联赛球队

获取联赛中所有球队的详细统计数据。

**请求示例**:
```
GET https://api.football-data-api.com/league-teams?key=YOURKEY&season_id=*
```

**查询参数**:

| 参数名 | 类型 | 描述 |
|--------|------|------|
| max_time | integer | UNIX 时间戳 |
| key* | string | 您的 API 密钥 |
| season_id* | integer | 联赛赛季 ID |

**响应示例**:
```json
{
    "success": true,
    "data": [
        {
            "team_id": 1,
            "team_name": "Manchester City",
            "position": 1,
            "played": 38,
            "won": 32,
            "drawn": 2,
            "lost": 4,
            "goalsFor": 106,
            "goalsAgainst": 27,
            "goalDifference": 79,
            "points": 98
        }
    ]
}
```

---

### 联赛球员

获取参与联赛赛季的所有球员及其统计数据。

**请求示例**:
```
GET https://api.football-data-api.com/league-players?key=YOURKEY&season_id=*&include=stats
```

**查询参数**:

| 参数名 | 类型 | 描述 |
|--------|------|------|
| page | integer | 分页，每页最多 200 名球员 |
| max_time | integer | UNIX 时间戳 |
| key* | string | 您的 API 密钥 |
| season_id* | integer | 联赛赛季 ID |

**响应示例**:
```json
{
    "success": true,
    "data": [
        {
            "id": 2984,
            "competition_id": 161,
            "full_name": "Petr Čech",
            "first_name": "Petr",
            "last_name": "Čech",
            "age": 36,
            "league": "Premier League",
            "position": "Goalkeeper",
            "minutes_played_overall": 3040,
            "appearances_overall": 34,
            "goals_overall": 0
        }
    ]
}
```

**返回字段说明**:

| 字段 | 描述 |
|------|------|
| id | 球员 ID |
| full_name | 球员全名 |
| position | 位置 |
| minutes_played_overall | 出场总分钟数 |
| appearances_overall | 出场次数 |
| goals_overall | 进球数 |

---

### 联赛裁判

获取参与联赛赛季的所有裁判及其统计数据。

**请求示例**:
```
GET https://api.football-data-api.com/league-referees?key=YOURKEY&season_id=*
```

**查询参数**:

| 参数名 | 类型 | 描述 |
|--------|------|------|
| max_time | integer | UNIX 时间戳 |
| key* | string | 您的 API 密钥 |
| season_id* | integer | 联赛赛季 ID |

**响应示例**:
```json
{
    "success": true,
    "pager": {
        "current_page": 1,
        "max_page": 1,
        "results_per_page": 200,
        "total_results": 21
    },
    "data": [
        {
            "id": 393,
            "full_name": "Michael Oliver",
            "age": 35,
            "league": "Premier League",
            "appearances_overall": 32,
            "wins_home": 11,
            "wins_away": 13,
            "draws_overall": 8,
            "goals_overall": 96,
            "goals_per_match_overall": 3,
            "cards_overall": 105,
            "cards_per_match_overall": 3.28,
            "yellow_cards_overall": 105,
            "red_cards_overall": 0
        }
    ]
}
```

**返回字段说明**:

| 字段 | 描述 |
|------|------|
| id | 裁判 ID |
| full_name | 裁判全名 |
| appearances_overall | 执法场次数 |
| goals_per_match_overall | 场均进球数 |
| cards_per_match_overall | 场均出牌数 |

---

### 联赛积分榜

获取联赛赛季的积分榜数据。

**请求示例**:
```
GET https://api.football-data-api.com/league-tables?key=YOURKEY&season_id=X
```

**查询参数**:

| 参数名 | 类型 | 描述 |
|--------|------|------|
| max_time | integer | UNIX 时间戳 |
| key* | string | 您的 API 密钥 |
| season_id* | integer | 联赛赛季 ID |

**响应示例**:
```json
{
    "success": true,
    "data": {
        "all_matches_table_overall": [],
        "all_matches_table_home": [],
        "all_matches_table_away": [],
        "specific_tables": [
            {
                "round": "Group Stage",
                "groups": [
                    {
                        "name": "Group A",
                        "table": [
                            {
                                "id": "76",
                                "name": "Villarreal CF",
                                "points": 11,
                                "matchesPlayed": 6,
                                "seasonWins_overall": 3,
                                "seasonDraws_overall": 2,
                                "seasonLosses_overall": 1,
                                "seasonGoals": 10,
                                "seasonConceded": 6,
                                "seasonGoalDifference": 4,
                                "position": 1
                            }
                        ]
                    }
                ]
            }
        ]
    }
}
```

---

## 详细数据端点

### 比赛详情

获取单场比赛的详细统计数据、交锋记录和赔率比较。

**请求示例**:
```
GET https://api.football-data-api.com/match?key=YOURKEY&match_id=1
```

**查询参数**:

| 参数名 | 类型 | 描述 |
|--------|------|------|
| key* | string | 您的 API 密钥 |
| match_id* | integer | 比赛 ID |

**响应示例**:
```json
{
    "success": true,
    "pager": {
        "current_page": 1,
        "max_page": 1,
        "results_per_page": 1,
        "total_results": 1
    },
    "data": {
        "id": 579101,
        "homeID": 251,
        "awayID": 145,
        "season": "2019/2020",
        "status": "complete",
        "homeGoalCount": 3,
        "awayGoalCount": 0,
        "team_a_corners": 7,
        "team_b_corners": 6,
        "team_a_shotsOnTarget": 7,
        "team_b_shotsOnTarget": 0,
        "team_a_possession": 45,
        "team_b_possession": 55,
        "odds_ft_1": 2.4,
        "odds_ft_x": 3.15,
        "odds_ft_2": 3.35,
        "lineups": {
            "team_a": [
                {
                    "player_id": 10127,
                    "shirt_number": 1,
                    "player_events": []
                }
            ]
        },
        "h2h": {
            "team_a_id": 251,
            "team_b_id": 145,
            "previous_matches_results": {
                "team_a_wins": 0,
                "team_b_wins": 4,
                "draw": 1,
                "totalMatches": 5
            }
        },
        "odds_comparison": {
            "FT Result": {
                "1": {
                    "BetFred": "2.38",
                    "10Bet": "2.28"
                }
            }
        }
    }
}
```

**主要返回字段**:

| 字段 | 描述 |
|------|------|
| lineups | 首发阵容及事件（进球、黄牌等） |
| bench | 替补球员及换人时间 |
| trends | 球队近期状态文字分析 |
| h2h | 历史交锋记录 |
| odds_comparison | 各大博彩公司赔率对比 |
| weather | 比赛天气信息 |
| tv_stations | 转播电视台 |

---

### 球队详情

获取单个球队的详细统计数据。

**请求示例**:
```
GET https://api.football-data-api.com/team?key=YOURKEY&team_id=*
```

**查询参数**:

| 参数名 | 类型 | 描述 |
|--------|------|------|
| key* | string | 您的 API 密钥 |
| team_id* | integer | 球队 ID |

**响应示例**:
```json
{
    "success": true,
    "data": {
        "team_id": 1,
        "team_name": "Manchester City",
        "league": "Premier League",
        "season": "2019/2020",
        "played": 38,
        "wins": 26,
        "draws": 3,
        "losses": 9,
        "goalsFor": 102,
        "goalsAgainst": 35,
        "points": 81,
        "position": 2,
        "form": "WWLWW",
        "home_record": {
            "played": 19,
            "wins": 18,
            "draws": 0,
            "losses": 1
        },
        "away_record": {
            "played": 19,
            "wins": 8,
            "draws": 3,
            "losses": 8
        }
    }
}
```

---

### 球队近况统计

获取球队最近 5/6/10 场比赛的详细统计数据。一次查询可以同时获取最近 5 场、6 场和 10 场比赛的统计数据。

**请求示例**:
```
GET https://api.football-data-api.com/lastx?key=YOURKEY&team_id=*
```

**查询参数**:

| 参数名 | 类型 | 描述 |
|--------|------|------|
| key* | string | 您的 API 密钥 |
| team_id* | integer | 球队 ID |

**说明**: 一次查询可以获取所有 3 种统计数据（最近 5 场/6 场/10 场）。未来将添加最近 15 场和 20 场的统计数据。统计属性和数据类型与球队端点一致。

**响应示例**:
```json
{
    "success": true,
    "pager": {
        "current_page": 1,
        "max_page": 1,
        "results_per_page": 50,
        "total_results": 3
    },
    "data": [
        {
            "id": 59,
            "name": "Arsenal",
            "full_name": "Arsenal FC",
            "country": "England",
            "founded": "1886",
            "image": "https://cdn.footystats.org/img/teams/england-arsenal-fc.png",
            "url": "https://footystats.org/clubs/england/arsenal-fc",
            "last_x_match_num": 5,
            "stats": {
                "seasonWinsNum_overall": 4,
                "seasonDrawsNum_overall": 1,
                "seasonLossesNum_overall": 0,
                "seasonMatchesPlayed_overall": 5,
                "seasonGoalsTotal_overall": 9,
                "seasonConcededNum_overall": 1,
                "seasonCS_overall": 4,
                "seasonCSPercentage_overall": 80,
                "seasonBTTS_overall": 1,
                "seasonBTTSPercentage_overall": 20,
                "seasonPPG_overall": 2.6,
                "seasonAVG_overall": 1.8,
                "winPercentage_overall": 80,
                "clean_sheet_num": 4,
                "failed_to_score_num": 1
            }
        }
    ]
}
```

**主要返回字段**:

| 字段 | 描述 |
|------|------|
| id | 球队 ID |
| name | 球队名称 |
| full_name | 球队全称 |
| country | 国家 |
| founded | 成立年份 |
| last_x_match_num | 统计的比赛场次数（5/6/10） |
| stats/seasonWinsNum_overall | 胜场数 |
| stats/seasonDrawsNum_overall | 平局数 |
| stats/seasonLossesNum_overall | 负场数 |
| stats/seasonGoalsTotal_overall | 总进球数 |
| stats/seasonConcededNum_overall | 失球数 |
| stats/seasonCS_overall | 零封场数 |
| stats/seasonCSPercentage_overall | 零封百分比 |
| stats/seasonBTTS_overall | 双方进球场次数 |
| stats/seasonBTTSPercentage_overall | 双方进球百分比 |
| stats/seasonPPG_overall | 场均积分 |
| stats/seasonAVG_overall | 场均进球数 |
| stats/winPercentage_overall | 胜率 |

---

### 球员详情

获取单个球员的详细统计数据。

**请求示例**:
```
GET https://api.football-data-api.com/player-stats?key=YOURKEY&player_id=*
```

**查询参数**:

| 参数名 | 类型 | 描述 |
|--------|------|------|
| key* | string | 您的 API 密钥 |
| player_id* | integer | 球员 ID |

**响应示例**:
```json
{
    "success": true,
    "data": [
        {
            "id": "3171",
            "full_name": "Cristiano Ronaldo dos Santos Aveiro",
            "age": "33",
            "league": "UEFA Champions League",
            "position": "Forward",
            "minutes_played_overall": "1170",
            "appearances_overall": "13",
            "goals_overall": "6",
            "assists_overall": "2",
            "yellow_cards_overall": "1",
            "red_cards_overall": "0"
        }
    ]
}
```

**主要返回字段**:

| 字段 | 描述 |
|------|------|
| goals_overall/home/away | 进球数 |
| assists_overall | 助攻数 |
| clean_sheets_overall | 零封场数 |
| penalty_goals | 点球进球 |
| goals_per_90_overall | 每 90 分钟进球数 |
| cards_overall | 黄牌/红牌数 |
| detailed/average_rating_overall | 平均评分 |
| detailed/shots_per_game_overall | 场均射门 |
| detailed/passes_per_game_overall | 场均传球 |
| detailed/tackles_per_game_overall | 场均抢断 |

---

### 裁判详情

获取单个裁判的详细统计数据。

**请求示例**:
```
GET https://api.football-data-api.com/referee?key=YOURKEY&referee_id=*
```

**查询参数**:

| 参数名 | 类型 | 描述 |
|--------|------|------|
| key* | string | 您的 API 密钥 |
| referee_id* | integer | 裁判 ID |

**响应示例**:
```json
{
    "success": true,
    "pager": {
        "current_page": 1,
        "max_page": 1,
        "results_per_page": 50,
        "total_results": 33
    },
    "data": [
        {
            "id": 393,
            "full_name": "Michael Oliver",
            "age": 35,
            "league": "UEFA Nations League",
            "appearances_overall": 2,
            "draws_overall": 2,
            "btts_overall": 50,
            "goals_overall": 2,
            "goals_per_match_overall": 1,
            "penalties_given_overall": 0,
            "cards_overall": 105,
            "cards_per_match_overall": 3.28,
            "yellow_cards_overall": 105,
            "red_cards_overall": 0
        }
    ]
}
```

---

## 统计数据端点

### BTTS 统计

获取双方进球（BTTS）相关的顶级球队、赛程和联赛数据。

**请求示例**:
```
GET https://api.football-data-api.com/stats-data-btts?key=YOURKEY
```

**查询参数**:

| 参数名 | 类型 | 描述 |
|--------|------|------|
| key* | string | 您的 API 密钥 |

**响应示例**:
```json
{
    "data": {
        "top_teams": {
            "title": "BTTS Teams",
            "list_type": "teams",
            "data": [
                {
                    "team_id": 1,
                    "team_name": "Liverpool",
                    "btts_count": 25,
                    "btts_percentage": 65.8
                }
            ]
        },
        "top_fixtures": {
            "title": "BTTS Fixtures",
            "list_type": "fixtures",
            "data": []
        },
        "top_leagues": {
            "title": "BTTS Leagues",
            "list_type": "leagues",
            "data": [
                {
                    "league_id": 1,
                    "league_name": "Premier League",
                    "btts_count": 189,
                    "btts_percentage": 49.7
                }
            ]
        }
    }
}
```

---

### Over 2.5 统计

获取大球（Over 2.5）相关的顶级球队、赛程和联赛数据。

**请求示例**:
```
GET https://api.football-data-api.com/stats-data-over25?key=YOURKEY
```

**查询参数**:

| 参数名 | 类型 | 描述 |
|--------|------|------|
| key* | string | 您的 API 密钥 |

**响应示例**:
```json
{
    "success": true,
    "data": {
        "top_teams": {
            "title": "Over 2.5 Teams",
            "list_type": "teams",
            "data": [
                {
                    "team_id": 1,
                    "team_name": "Manchester City",
                    "over25_count": 28,
                    "over25_percentage": 73.7
                }
            ]
        },
        "top_fixtures": {
            "title": "Over 2.5 Fixtures",
            "list_type": "fixtures",
            "data": []
        },
        "top_leagues": {
            "title": "Over 2.5 Leagues",
            "list_type": "leagues",
            "data": [
                {
                    "league_id": 1,
                    "league_name": "Premier League",
                    "over25_count": 210,
                    "over25_percentage": 55.3
                }
            ]
        }
    }
}
```

---

## 附录

### 错误处理

API 返回的错误响应格式：

```json
{
    "success": false,
    "error": {
        "code": 401,
        "message": "Invalid API Key"
    }
}
```

### 速率限制

- 每个 API Key 有每小时请求限制
- 请求限制每小时重置一次
- 响应头中包含剩余请求数信息

### 数据更新频率

- 比赛数据：实时更新
- 球员统计数据：比赛结束后更新
- 联赛积分榜：比赛结束后更新
- 历史数据：定期维护和修正

### 支持与联系

- 官方文档：https://footystats.org/api/documentations/
- 技术支持：通过 FootyStats 网站联系

---

> 文档版本：1.0  
> 最后更新：2026-03-26  
> 数据来源：FootyStats API

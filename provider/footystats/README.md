# FootyStats Provider 使用示例

本文档展示如何使用 FootyStatsProvider 访问所有 16 个 API 端点。

## 初始化

```python
from provider.footystats import FootyStatsProvider

# 方法 1: 使用配置文件中的 API key
provider = FootyStatsProvider()

# 方法 2: 直接传入 API key
provider = FootyStatsProvider(api_key="your_api_key_here")

# 检查 API 是否可用
available = await provider.is_available()
print(f"API available: {available}")
```

## 基础端点

### 1. 联赛列表 (League List)

```python
# 获取所有联赛
leagues = await provider.get_league_list()

# 只获取用户选择的联赛
chosen_leagues = await provider.get_league_list(chosen_leagues_only=True)

# 按国家筛选（使用 ISO 编号）
england_leagues = await provider.get_league_list(country=826)
```

### 2. 国家列表 (Country List)

```python
# 获取所有国家及其 ISO 编号
countries = await provider.get_country_list()

# 示例响应结构
# {
#     "success": true,
#     "data": [
#         {"id": 826, "name": "England"},
#         {"id": 724, "name": "Spain"},
#         ...
#     ]
# }
```

### 3. 每日比赛 (Today's Matches)

```python
# 获取今天的比赛
matches = await provider.get_todays_matches()

# 获取指定日期的比赛
matches = await provider.get_todays_matches(date="2024-01-15")

# 指定时区
matches = await provider.get_todays_matches(
    date="2024-01-15",
    timezone="Europe/London"
)
```

## 联赛数据端点

### 4. 联赛统计 (League Stats)

```python
# 获取联赛赛季统计数据
season_id = 2012  # 例如英超 2019/2020 赛季
stats = await provider.get_league_stats(season_id=season_id)

# 获取特定时间点的统计数据
stats = await provider.get_league_stats(
    season_id=season_id,
    max_time=1577836800  # 2020-01-01 的 UNIX 时间戳
)
```

### 5. 联赛比赛 (League Matches)

```python
# 获取联赛比赛（每页 500 场）
matches = await provider.get_league_matches(season_id=2012)

# 分页获取
page1 = await provider.get_league_matches(season_id=2012, page=1)
page2 = await provider.get_league_matches(season_id=2012, page=2)

# 自定义每页数量（最大 1000）
matches = await provider.get_league_matches(
    season_id=2012,
    page=1,
    max_per_page=1000
)
```

### 6. 联赛球队 (League Teams)

```python
# 获取联赛中所有球队的统计数据
teams = await provider.get_league_teams(season_id=2012)

# 示例响应结构
# {
#     "success": true,
#     "data": [
#         {
#             "team_id": 1,
#             "team_name": "Manchester City",
#             "position": 1,
#             "played": 38,
#             "points": 98,
#             ...
#         },
#         ...
#     ]
# }
```

### 7. 联赛球员 (League Players)

```python
# 获取联赛球员列表
players = await provider.get_league_players(season_id=2012)

# 包含详细统计数据
players_with_stats = await provider.get_league_players(
    season_id=2012,
    include_stats=True
)

# 分页获取
page1 = await provider.get_league_players(season_id=2012, page=1)
page2 = await provider.get_league_players(season_id=2012, page=2)
```

### 8. 联赛裁判 (League Referees)

```python
# 获取联赛裁判列表
referees = await provider.get_league_referees(season_id=2012)

# 示例响应结构
# {
#     "success": true,
#     "data": [
#         {
#             "id": 393,
#             "full_name": "Michael Oliver",
#             "appearances_overall": 32,
#             "cards_per_match_overall": 3.28,
#             ...
#         },
#         ...
#     ]
# }
```

### 9. 联赛积分榜 (League Tables)

```python
# 获取联赛积分榜
tables = await provider.get_league_tables(season_id=2012)

# 示例响应结构
# {
#     "success": true,
#     "data": {
#         "all_matches_table_overall": [...],
#         "all_matches_table_home": [...],
#         "all_matches_table_away": [...],
#         "specific_tables": [...]
#     }
# }
```

## 详细数据端点

### 10. 比赛详情 (Match Details)

```python
# 获取单场比赛的详细信息（包含阵容、赔率、交锋记录等）
match = await provider.get_match_details(match_id=579101)

# 示例响应包含：
# - 比赛基本信息（比分、角球、射门等）
# - 首发阵容和替补
# - 历史交锋记录
# - 赔率对比
# - 天气信息
```

### 11. 球队详情 (Team)

```python
# 获取单个球队的详细统计数据
team = await provider.get_team(team_id=59)  # 例如阿森纳

# 示例响应结构
# {
#     "success": true,
#     "data": {
#         "team_id": 59,
#         "team_name": "Arsenal",
#         "league": "Premier League",
#         "season": "2019/2020",
#         "played": 38,
#         "wins": 14,
#         "draws": 14,
#         "losses": 10,
#         ...
#     }
# }
```

### 12. 球队近况统计 (Last 5/6/10 Team Stats)

```python
# 获取球队最近 5/6/10 场比赛的统计数据
# 一次查询同时返回三种统计数据
last_x = await provider.get_team_last_x_stats(team_id=59)

# 示例响应结构
# {
#     "success": true,
#     "data": [
#         {
#             "id": 59,
#             "name": "Arsenal",
#             "last_x_match_num": 5,
#             "stats": {
#                 "seasonWinsNum_overall": 4,
#                 "seasonDrawsNum_overall": 1,
#                 "seasonLossesNum_overall": 0,
#                 "seasonGoalsTotal_overall": 9,
#                 "seasonCSPercentage_overall": 80,
#                 "seasonBTTSPercentage_overall": 20,
#                 ...
#             }
#         }
#     ]
# }
```

### 13. 球员详情 (Player - Individual)

```python
# 获取单个球员的详细统计数据
player = await provider.get_player_stats(player_id=3171)  # 例如 C 罗

# 示例响应包含：
# - 基本信息（姓名、年龄、位置、国籍等）
# - 出场次数、进球、助攻
# - 详细技术统计（传球、射门、抢断等）
# - 百分位排名
```

### 14. 裁判详情 (Referee - Individual)

```python
# 获取单个裁判的详细统计数据
referee = await provider.get_referee_stats(referee_id=393)  # 例如 Michael Oliver

# 示例响应包含：
# - 基本信息（姓名、年龄、国籍等）
# - 执法场次、胜负平分布
# - 进球数、牌数统计
# - 点球判罚统计
```

## 统计数据端点

### 15. BTTS 统计 (BTTS Stats)

```python
# 获取双方进球（BTTS）相关的顶级球队、赛程和联赛数据
btts_stats = await provider.get_btts_stats()

# 示例响应结构
# {
#     "data": {
#         "top_teams": {
#             "title": "BTTS Teams",
#             "list_type": "teams",
#             "data": [...]
#         },
#         "top_fixtures": {
#             "title": "BTTS Fixtures",
#             "list_type": "fixtures",
#             "data": [...]
#         },
#         "top_leagues": {
#             "title": "BTTS Leagues",
#             "list_type": "leagues",
#             "data": [...]
#         }
#     }
# }
```

### 16. Over 2.5 统计 (Over 2.5 Stats)

```python
# 获取大球（Over 2.5）相关的顶级球队、赛程和联赛数据
over_2_5_stats = await provider.get_over_2_5_stats()

# 响应结构与 BTTS 类似，包含：
# - top_teams: Over 2.5 球队排名
# - top_fixtures: Over 2.5 比赛推荐
# - top_leagues: Over 2.5 联赛排名
```

## 完整示例

```python
import asyncio
from provider.footystats import FootyStatsProvider

async def main():
    # 初始化 provider
    provider = FootyStatsProvider(api_key="your_api_key")
    
    # 检查是否可用
    if not await provider.is_available():
        print("API not available")
        return
    
    # 1. 获取联赛列表
    leagues = await provider.get_league_list()
    print(f"Found {len(leagues['data'])} leagues")
    
    # 2. 获取国家列表
    countries = await provider.get_country_list()
    print(f"Found {len(countries['data'])} countries")
    
    # 3. 获取今日比赛
    today_matches = await provider.get_todays_matches()
    print(f"Today: {len(today_matches['data'])} matches")
    
    # 4. 获取联赛统计（需要 season_id）
    # season_id = 2012  # 英超 2019/2020
    # stats = await provider.get_league_stats(season_id=season_id)
    
    # 5. 获取联赛比赛
    # matches = await provider.get_league_matches(season_id=season_id)
    
    # 6. 获取联赛球队
    # teams = await provider.get_league_teams(season_id=season_id)
    
    # 7. 获取联赛球员
    # players = await provider.get_league_players(season_id=season_id)
    
    # 8. 获取联赛裁判
    # referees = await provider.get_league_referees(season_id=season_id)
    
    # 9. 获取联赛积分榜
    # tables = await provider.get_league_tables(season_id=season_id)
    
    # 10. 获取比赛详情
    # match = await provider.get_match_details(match_id=579101)
    
    # 11. 获取球队详情
    # team = await provider.get_team(team_id=59)
    
    # 12. 获取球队近况
    # last_x = await provider.get_team_last_x_stats(team_id=59)
    
    # 13. 获取球员详情
    # player = await provider.get_player_stats(player_id=3171)
    
    # 14. 获取裁判详情
    # referee = await provider.get_referee_stats(referee_id=393)
    
    # 15. 获取 BTTS 统计
    # btts = await provider.get_btts_stats()
    
    # 16. 获取 Over 2.5 统计
    # over_2_5 = await provider.get_over_2_5_stats()

if __name__ == "__main__":
    asyncio.run(main())
```

## 错误处理

```python
from provider.footystats import FootyStatsProvider

async def safe_call():
    provider = FootyStatsProvider()
    
    try:
        result = await provider.get_league_list()
        if result:
            if result.get("success"):
                print("Success:", result["data"])
            else:
                print("API error:", result.get("error"))
        else:
            print("No response")
    except Exception as e:
        print(f"Request failed: {e}")
```

## 注意事项

1. **API Key**: 必须配置有效的 API Key 才能使用
2. **赛季 ID**: 大部分联赛相关端点需要 `season_id` 参数，可以通过 `get_league_list()` 获取
3. **分页**: 球员、比赛等数据量大的端点支持分页
4. **速率限制**: API 有每小时请求限制，请注意控制请求频率
5. **数据更新**: 比赛数据实时更新，统计数据在比赛结束后更新

## API 端点映射表

| 方法名 | API 端点 | 说明 |
|--------|---------|------|
| `get_league_list()` | `/league-list` | 联赛列表 |
| `get_country_list()` | `/country-list` | 国家列表 |
| `get_todays_matches()` | `/todays-matches` | 每日比赛 |
| `get_league_stats()` | `/league-season` | 联赛统计 |
| `get_league_matches()` | `/league-matches` | 联赛比赛 |
| `get_league_teams()` | `/league-teams` | 联赛球队 |
| `get_league_players()` | `/league-players` | 联赛球员 |
| `get_league_referees()` | `/league-referees` | 联赛裁判 |
| `get_league_tables()` | `/league-tables` | 联赛积分榜 |
| `get_match_details()` | `/match` | 比赛详情 |
| `get_team()` | `/team` | 球队详情 |
| `get_team_last_x_stats()` | `/lastx` | 球队近况 |
| `get_player_stats()` | `/player-stats` | 球员详情 |
| `get_referee_stats()` | `/referee` | 裁判详情 |
| `get_btts_stats()` | `/stats-data-btts` | BTTS 统计 |
| `get_over_2_5_stats()` | `/stats-data-over25` | Over 2.5 统计 |

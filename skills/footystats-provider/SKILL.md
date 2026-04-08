---
name: footystats-provider
description: Use this skill when the user needs FootyStats API guidance, asks about league tables, team statistics, match details, BTTS/Over 2.5 stats, or how to use any of the 16 FootyStats endpoints.
---

# FootyStats Provider Skill

## 📋 概述

本 skill 提供 FootyStats API 的完整使用指南，包括所有 16 个端点的详细说明、使用示例和最佳实践。

**Provider 位置**: `provider/footystats/client.py`

**API 文档**: https://api.football-data-api.com

## 🎯 触发条件

当用户询问以下内容时触发此 skill：
- "如何使用 FootyStats API"
- "FootyStats API 端点"
- "获取联赛积分榜"
- "获取球队统计数据"
- "获取比赛详情"
- "FootyStats API 配置"
- "获取 BTTS 统计"
- "获取 Over 2.5 统计"
- "查询球员数据"

## 🔑 核心知识

### 1. API 端点分类（16 个端点）

#### 一、基础数据端点（3 个）

1. **联赛列表** (`/league-list`)
   - 获取所有可用联赛列表，支持按国家筛选
   - 参数：`chosen_leagues_only`, `country`
   - 示例：`await provider.get_league_list()`

2. **国家列表** (`/country-list`)
   - 获取所有国家及其 ISO 编号
   - 无参数
   - 示例：`await provider.get_country_list()`

3. **每日比赛** (`/todays-matches`)
   - 获取指定日期的所有比赛（包括已完赛和未开赛）
   - 参数：`date` (YYYY-MM-DD), `timezone`
   - 示例：`await provider.get_todays_matches(date="2026-04-08")`

#### 二、联赛数据端点（6 个）

4. **联赛统计** (`/league-season`)
   - 获取联赛赛季的详细统计数据和参赛球队信息
   - 参数：`season_id` (必需), `max_time`
   - 示例：`await provider.get_league_stats(season_id=14968)`

5. **联赛比赛** (`/league-matches`)
   - 获取联赛的完整比赛赛程（所有比赛）
   - 参数：`season_id` (必需), `page`, `max_per_page`, `max_time`
   - 示例：`await provider.get_league_matches(season_id=14968)`

6. **联赛球队** (`/league-teams`)
   - 获取联赛中所有球队的详细统计数据
   - 参数：`season_id` (必需), `max_time`
   - 示例：`await provider.get_league_teams(season_id=14968)`

7. **联赛球员** (`/league-players`)
   - 获取联赛中所有球员及其统计数据
   - 参数：`season_id` (必需), `page`, `include_stats`, `max_time`
   - 示例：`await provider.get_league_players(season_id=14968)`

8. **联赛裁判** (`/league-referees`)
   - 获取联赛中所有裁判及其统计数据
   - 参数：`season_id` (必需), `max_time`
   - 示例：`await provider.get_league_referees(season_id=14968)`

9. **联赛积分榜** (`/league-tables`)
   - 获取联赛赛季的积分榜排名
   - 参数：`season_id` (必需), `max_time`
   - 示例：`await provider.get_league_tables(season_id=14968)`

#### 三、详细数据端点（4 个）

10. **比赛详情** (`/match`)
    - 获取单场比赛的详细统计数据、交锋记录、赔率
    - 参数：`match_id` (必需)
    - 示例：`await provider.get_match_details(match_id=8227534)`

11. **球队详情** (`/team`)
    - 获取单个球队的完整统计数据
    - 参数：`team_id` (必需)
    - 示例：`await provider.get_team_details(team_id=46)`

12. **球队近况统计** (`/lastx`)
    - 获取球队最近 5/6/10 场比赛的详细表现
    - 参数：`team_id` (必需)
    - 示例：`await provider.get_team_last_x_stats(team_id=46)`

13. **球员详情** (`/player-stats`)
    - 获取单个球员的详细统计数据
    - 参数：`player_id` (必需)
    - 示例：`await provider.get_player_details(player_id=12345)`

14. **裁判详情** (`/referee`)
    - 获取单个裁判的详细统计数据
    - 参数：`referee_id` (必需)
    - 示例：`await provider.get_referee_details(referee_id=789)`

#### 四、统计数据端点（2 个）

15. **BTTS 统计** (`/stats-data-btts`)
    - 获取双方进球相关的顶级球队、赛程、联赛数据
    - 无参数
    - 示例：`await provider.get_btts_stats()`

16. **Over 2.5 统计** (`/stats-data-over25`)
    - 获取大球（Over 2.5）相关的顶级球队、赛程、联赛数据
    - 无参数
    - 示例：`await provider.get_over25_stats()`

### 2. 配置 API Key

在 `.env` 文件中配置：
```bash
FOOTYSTATS_API_KEY=your_api_key_here
```

## 💻 使用方法

### 初始化 Provider

```python
from provider.footystats.client import FootyStatsProvider

# 使用配置文件中的 API key
provider = FootyStatsProvider()

# 或直接传入 API key
provider = FootyStatsProvider(api_key="your_api_key")

# 检查 API 是否可用
available = await provider.is_available()
if not available:
    print("API 不可用，请检查配置")
```

### 使用场景与示例

#### 场景 1: 获取德国甲级联赛完整赛程

```python
# 步骤 1: 获取联赛列表，找到德甲
leagues = await provider.get_league_list()
bundesliga = None

for league in leagues.get("data", []):
    if "bundesliga" in league.get("league_name", "").lower() and \
       "germany" in league.get("country", "").lower():
        bundesliga = league
        break

if not bundesliga:
    print("未找到德国甲级联赛")
    return

# 获取最新赛季 ID
seasons = bundesliga.get("season", [])
latest_season = seasons[-1] if seasons else None
season_id = latest_season.get("id") if latest_season else None

# 步骤 2: 获取完整赛程
matches = await provider.get_league_matches(season_id=season_id)

# 步骤 3: 显示结果
if matches and matches.get("success"):
    match_data = matches.get("data", [])
    print(f"共 {len(match_data)} 场比赛")
    
    for match in match_data[:5]:  # 显示前 5 场
        print(f"{match.get('Date')} - {match.get('HomeTeam')} vs {match.get('AwayTeam')}")
```

#### 场景 2: 获取联赛积分榜

```python
# 获取积分榜
standings = await provider.get_league_tables(season_id=14968)

if standings and standings.get("success"):
    table = standings.get("data", [])
    
    print("德甲积分榜:")
    print("-" * 60)
    print(f"{'排名':<4} {'球队':<20} {'赛':<4} {'胜':<4} {'平':<4} {'负':<4} {'积分':<4}")
    print("-" * 60)
    
    for team in table:
        print(f"{team.get('OverallPosition'):<4} "
              f"{team.get('OverallTeamName'):<20} "
              f"{team.get('OverallPlayed'):<4} "
              f"{team.get('OverallWon'):<4} "
              f"{team.get('OverallDrawn'):<4} "
              f"{team.get('OverallLost'):<4} "
              f"{team.get('OverallPoints'):<4}")
```

#### 场景 3: 获取球队详细统计

```python
# 获取球队详情
team_stats = await provider.get_team_details(team_id=46)

if team_stats and team_stats.get("success"):
    team = team_stats.get("data", {})
    
    print(f"球队：{team.get('TeamName')}")
    print(f"总体胜率：{team.get('OverallWinPercentage')}%")
    print(f"主场胜率：{team.get('HomeWinPercentage')}%")
    print(f"客场胜率：{team.get('AwayWinPercentage')}%")
    print(f"场均进球：{team.get('AverageGoalsScored')}")
    print(f"场均失球：{team.get('AverageGoalsConceded')}")
    print(f"BTTS 概率：{team.get('BTTSPercentage')}%")
    print(f"Over 2.5 概率：{team.get('Over25Percentage')}%")
```

#### 场景 4: 获取比赛详情（含 xG）

```python
# 获取比赛详情
match = await provider.get_match_details(match_id=8227534)

if match and match.get("success"):
    data = match.get("data", {})
    
    print(f"比赛：{data.get('HomeTeam')} vs {data.get('AwayTeam')}")
    print(f"日期：{data.get('Date')}")
    print(f"比分：{data.get('FTResult')}")
    
    # 获取 xG 数据（如果有）
    if "xG" in data:
        print(f"主队 xG: {data.get('HomeXG')}")
        print(f"客队 xG: {data.get('AwayXG')}")
    
    # 获取交锋记录
    h2h = data.get("H2H", [])
    if h2h:
        print("\n最近交锋:")
        for h2h_match in h2h[:3]:
            print(f"  {h2h_match.get('Date')}: {h2h_match.get('HomeTeam')} {h2h_match.get('FTResult')}")
```

#### 场景 5: 获取 BTTS 和 Over 2.5 统计

```python
# BTTS 统计
btts_stats = await provider.get_btts_stats()

# Over 2.5 统计
over25_stats = await provider.get_over25_stats()

if btts_stats and btts_stats.get("success"):
    btts_data = btts_stats.get("data", {})
    top_teams = btts_data.get("topTeams", [])
    
    print("BTTS 概率最高的球队:")
    for team in top_teams[:5]:
        print(f"  {team.get('teamName')}: {team.get('percentage')}%")

if over25_stats and over25_stats.get("success"):
    over25_data = over25_stats.get("data", {})
    top_teams = over25_data.get("topTeams", [])
    
    print("\nOver 2.5 概率最高的球队:")
    for team in top_teams[:5]:
        print(f"  {team.get('teamName')}: {team.get('percentage')}%")
```

## ⚠️ 注意事项

### 1. API Key 管理
- API Key 是必需的，所有请求都需要携带
- 不要将 API Key 提交到版本控制系统
- 使用环境变量管理 API Key

### 2. 速率限制
- FootyStats 有请求频率限制
- 建议添加请求间隔（1-2 秒）
- 实现错误重试机制

### 3. 数据缓存

```python
import json
from pathlib import Path
from datetime import datetime, timedelta

cache_dir = Path("data/footystats_cache")
cache_dir.mkdir(exist_ok=True)

async def cached_api_call(provider, method, *args, cache_ttl=3600, **kwargs):
    """带缓存的 API 调用"""
    import time
    import hashlib
    
    # 生成缓存 key
    cache_key = f"{method}_{args}_{kwargs}"
    cache_hash = hashlib.md5(cache_key.encode()).hexdigest()
    cache_file = cache_dir / f"{cache_hash}.json"
    
    # 检查缓存
    if cache_file.exists():
        cache_data = json.loads(cache_file.read_text())
        if time.time() - cache_data["timestamp"] < cache_ttl:
            return cache_data["data"]
    
    # API 调用
    method_func = getattr(provider, method)
    result = await method_func(*args, **kwargs)
    
    if result and result.get("success"):
        # 保存缓存
        json.dump({
            "timestamp": time.time(),
            "data": result
        }, cache_file.open("w"))
    
    return result
```

### 4. 错误处理

```python
from typing import Optional

def safe_get_data(result: Any) -> Optional[list]:
    """安全提取数据"""
    if not result:
        return None
    if not result.get("success"):
        error_msg = result.get("error", "Unknown error")
        print(f"API 错误：{error_msg}")
        return None
    return result.get("data")

# 使用示例
standings = await provider.get_league_tables(season_id=14968)
data = safe_get_data(standings)
if not data:
    print("未获取到积分榜数据")
```

## 🔍 常见问题解答

### Q1: 如何获取特定日期的比赛？
**A:** 使用 `get_todays_matches` 方法：
```python
matches = await provider.get_todays_matches(date="2026-04-08")
```

### Q2: 如何获取联赛的赛季 ID？
**A:** 从联赛列表中获取：
```python
leagues = await provider.get_league_list()
for league in leagues.get("data", []):
    seasons = league.get("season", [])
    if seasons:
        latest_season = seasons[-1]
        season_id = latest_season.get("id")
```

### Q3: 如何获取实时比分？
**A:** FootyStats 不提供实时比分，数据有延迟。需要实时数据请使用其他服务。

### Q4: 如何获取 xG 数据？
**A:** 部分联赛和比赛包含 xG 数据，在 `get_match_details` 的返回数据中查找 `xG` 字段。

### Q5: API 返回失败怎么办？
**A:** 
1. 检查 API Key 是否有效
2. 检查赛季 ID 是否正确
3. 查看错误信息：`result.get("error")`
4. 检查请求频率是否过高

## 📊 数据字段说明

### 比赛数据字段
| 字段 | 说明 | 类型 |
|------|------|------|
| `Date` | 比赛日期时间 | str |
| `HomeTeam` | 主队名称 | str |
| `AwayTeam` | 客队名称 | str |
| `FTResult` | 全场比分 | str |
| `HTResult` | 半场比分 | str |
| `xG` | 期望进球（如果有） | float |

### 积分榜字段
| 字段 | 说明 | 类型 |
|------|------|------|
| `OverallPosition` | 排名 | int |
| `OverallTeamName` | 球队名称 | str |
| `OverallPlayed` | 已赛场次 | int |
| `OverallWon` | 胜场 | int |
| `OverallDrawn` | 平局 | int |
| `OverallLost` | 负场 | int |
| `OverallPoints` | 积分 | int |

### 球队统计字段
| 字段 | 说明 | 类型 |
|------|------|------|
| `TeamName` | 球队名称 | str |
| `OverallWinPercentage` | 总体胜率 | float |
| `AverageGoalsScored` | 场均进球 | float |
| `AverageGoalsConceded` | 场均失球 | float |
| `BTTSPercentage` | BTTS 概率 | float |
| `Over25Percentage` | Over 2.5 概率 | float |

## 📚 相关文档

- [MCP 服务器文档](../mcp_server/README.md)
- [SportMonks 使用指南](../docs/SPORTMONKS_USAGE.md)
- [Understat 实现总结](../docs/UNDERSTAT_IMPLEMENTATION_SUMMARY.md)

## 🆘 故障排除

### 问题：API 返回 401 错误
**原因：** API Key 无效  
**解决：** 检查 `.env` 文件中的配置，确认 API Key 正确

### 问题：返回空数据
**原因：** 赛季 ID 错误或数据不存在  
**解决：** 检查赛季 ID 是否正确，尝试其他赛季

### 问题：响应超时
**原因：** 网络问题或数据量过大  
**解决：** 增加超时时间，使用分页获取数据

## 📝 最佳实践

1. **始终检查 API 响应**
   ```python
   result = await provider.get_league_tables(season_id=14968)
   if not result or not result.get("success"):
       print("获取数据失败")
       return
   ```

2. **使用缓存减少请求**
   - 联赛列表等静态数据使用长缓存（1 天）
   - 比赛数据使用短缓存（1 小时）
   - 积分榜使用中等缓存（6 小时）

3. **添加请求间隔**
   ```python
   import asyncio
   
   async def make_request_with_delay(provider, method, *args, delay=1.0, **kwargs):
       await asyncio.sleep(delay)
       return await getattr(provider, method)(*args, **kwargs)
   ```

4. **批量获取数据**
   ```python
   # 获取多个联赛的数据
   league_ids = [14968, 14969, 14970]
   for league_id in league_ids:
       standings = await provider.get_league_tables(season_id=league_id)
       await asyncio.sleep(1)  # 添加间隔
   ```

## 🔄 更新日志

- **2026-04-08**: 初始版本，包含所有 16 个端点的完整文档
  - 详细的使用示例
  - 最佳实践
  - 故障排除指南

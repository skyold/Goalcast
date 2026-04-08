# SportMonks API v3 使用指南

## 📋 概述

SportMonks API v3 是一个专业的足球数据 API，提供全球足球联赛、球队、球员、比赛等详细数据。

## 🔑 配置

### 环境变量
在 `.env` 文件中配置：
```bash
SPORTMONKS_API_KEY=your_api_key_here
```

### 初始化
```python
from provider.sportmonks.client import SportmonksProvider

# 使用配置文件中的 API key
provider = SportmonksProvider()

# 或直接传入 API key
provider = SportmonksProvider(api_key="your_api_key")

# 检查 API 是否可用
available = await provider.is_available()
```

## ✅ 免费计划可用端点

根据测试，以下端点在 **Football Free Plan** 下可用：

### 1. Fixtures (比赛数据) ⭐ 推荐

#### `/fixtures` - 获取比赛列表
```python
# 获取所有比赛（分页，每页 25 条）
fixtures = await provider.get_fixtures_by_date("2026-04-08")
# 或使用分页
fixtures_page1 = await provider._request_raw("/fixtures", {"page": 1})
fixtures_page2 = await provider._request_raw("/fixtures", {"page": 2})
```

**返回数据示例：**
```json
{
  "data": [
    {
      "id": 19146701,
      "league_id": 501,
      "season_id": 23614,
      "starting_at": "2026-04-08 19:00:00",
      "result_info": "FT",
      "participants": [...]
    }
  ]
}
```

#### `/fixtures/between/{start_date}/{end_date}` - 获取日期范围内的比赛
```python
# 获取 2026-04-08 至 2026-04-15 的比赛
fixtures = await provider.get_fixtures_between(
    "2026-04-08", 
    "2026-04-15",
    include="participants"
)
```

**用途：**
- 获取特定周/月的比赛
- 筛选特定联赛的比赛（需要后处理）
- 赛季数据分析

### 2. Leagues (联赛数据) 📊

#### `/leagues` - 获取联赛列表
```python
# 获取联赛列表（分页）
leagues = await provider.get_leagues(page=1)
```

**返回数据示例：**
```json
{
  "data": [
    {
      "id": 271,
      "name": "Superliga",
      "country_id": 320,
      "active": true,
      "short_code": "DNK SL"
    }
  ]
}
```

**用途：**
- 获取可用联赛列表
- 识别联赛 ID 用于其他查询

### 3. Seasons (赛季数据) 📅

#### `/seasons` - 获取赛季列表
```python
# 获取赛季列表（分页）
seasons = await provider.get_seasons(page=1)
```

**用途：**
- 获取联赛的赛季信息
- 识别当前赛季 ID

### 4. Teams (球队数据) ⚽

#### `/teams` - 获取球队列表
```python
# 获取球队列表（分页）
teams = await provider.get_teams(page=1)
```

**返回数据示例：**
```json
{
  "data": [
    {
      "id": 85,
      "name": "Bayern München",
      "short_code": "BAY",
      "country_id": 11,
      "founded": 1900
    }
  ]
}
```

### 5. Players (球员数据) 👥

#### `/players` - 获取球员列表
```python
# 获取球员列表（分页）
players = await provider.get_players(page=1)
```

**用途：**
- 获取球员基本信息
- 球员 ID 用于详细查询

## ❌ 免费计划不可用的端点

以下端点在免费计划下**不可用**（需要付费升级）：

### 实时数据
- `/livescores` - 实时比分
- `/livescores/inplay` - 正在进行中的比赛
- `/livescores/latest` - 最新比赛更新

### 高级筛选
- `/fixtures/date/{date}` - 按日期筛选比赛
- `/leagues/countries/{country_id}` - 按国家筛选联赛
- `/leagues/search/{name}` - 搜索联赛

### 统计数据
- `/standings/seasons/{season_id}` - 积分榜
- `/teams/seasons/{season_id}` - 赛季球队数据
- `/topscorers/seasons/{season_id}` - 射手榜

### 赔率与预测
- `/odds/markets` - 赔率市场
- `/odds/bookmakers` - 博彩公司
- `/predictions/value-bets` - 价值投注

### 赛程详情
- `/fixtures/seasons/{season_id}` - 赛季完整赛程
- `/schedules/seasons/{season_id}` - 赛季赛程计划
- `/rounds/seasons/{season_id}` - 轮次信息
- `/stages/seasons/{season_id}` - 阶段信息

## 💡 使用技巧

### 1. 获取特定联赛的比赛

```python
# 步骤 1: 获取联赛列表，找到目标联赛 ID
leagues = await provider.get_leagues(page=1)
bundesliga_id = None
for league in leagues.get("data", []):
    if "bundesliga" in league.get("name", "").lower():
        bundesliga_id = league["id"]
        break

# 步骤 2: 获取日期范围内的比赛
fixtures = await provider.get_fixtures_between(
    "2026-04-08", "2026-04-15",
    include="participants"
)

# 步骤 3: 筛选特定联赛
bundesliga_fixtures = [
    f for f in fixtures.get("data", [])
    if f.get("league_id") == bundesliga_id
]
```

### 2. 分页获取完整数据

```python
async def get_all_pages(provider, endpoint, max_pages=10):
    """分页获取所有数据"""
    all_data = []
    for page in range(1, max_pages + 1):
        response = await provider._request_raw(endpoint, {"page": page})
        if response and "data" in response:
            all_data.extend(response["data"])
            # 如果返回数据少于 25 条，说明是最后一页
            if len(response["data"]) < 25:
                break
    return all_data

# 使用示例
all_teams = await get_all_pages(provider, "/teams")
```

### 3. 使用 include 参数获取关联数据

```python
# 获取比赛时包含参赛队伍信息
fixtures = await provider.get_fixtures_between(
    "2026-04-08", "2026-04-15",
    include="participants,league"
)
```

### 4. 获取单场比赛详情

```python
# 通过比赛 ID 获取详细信息
fixture = await provider.get_fixture_by_id(
    fixture_id=19146701,
    include="participants,lineups,statistics"
)
```

## 📈 数据使用场景

### 场景 1: 赛前分析
```python
# 1. 获取即将进行的比赛
fixtures = await provider.get_fixtures_between(start_date, end_date)

# 2. 获取球队历史数据
team_fixtures = await provider.get_fixtures_by_team(team_id)

# 3. 获取交锋记录
h2h = await provider.get_head_to_head(team1_id, team2_id)
```

### 场景 2: 数据统计
```python
# 1. 获取所有比赛
all_fixtures = await get_all_pages(provider, "/fixtures")

# 2. 分析进球数据
goals_stats = analyze_goals(all_fixtures)

# 3. 分析球队表现
team_performance = analyze_team_stats(all_fixtures)
```

### 场景 3: 联赛追踪
```python
# 1. 获取联赛列表
leagues = await provider.get_leagues()

# 2. 获取赛季信息
seasons = await provider.get_seasons()

# 3. 获取球队列表
teams = await provider.get_teams()
```

## 🚀 MCP Server 集成

在 MCP Server 中，SportMonks API 已封装为以下工具：

### 可用工具

1. **sportmonks_get_livescores** - 获取实时比分（免费计划受限）
2. **sportmonks_get_fixtures_by_date** - 获取指定日期比赛
3. **sportmonks_get_fixture_by_id** - 获取单场比赛详情
4. **sportmonks_get_lineups** - 获取比赛阵容
5. **sportmonks_get_player_stats** - 获取球员统计
6. **sportmonks_get_odds_movement** - 获取赔率变化（付费）
7. **sportmonks_get_head_to_head** - 获取交锋记录
8. **sportmonks_get_standings** - 获取积分榜（付费）
9. **sportmonks_get_expected_goals** - 获取期望进球（xG）
10. **sportmonks_get_prematch_odds** - 获取赛前赔率（付费）
11. **sportmonks_get_predictions** - 获取比赛预测（付费）
12. **sportmonks_get_value_bets** - 获取价值投注（付费）

### 使用示例

```python
# 通过 MCP 调用
result = await mcp.tool("sportmonks_get_fixtures_by_date", {
    "date": "2026-04-08",
    "include": "league,participants"
})
```

## ⚠️ 注意事项

1. **API 限制**
   - 免费计划有请求频率限制
   - 部分端点返回历史数据而非实时数据
   - 数据更新可能有延迟

2. **最佳实践**
   - 使用分页获取完整数据
   - 缓存已获取的数据避免重复请求
   - 处理 API 错误和空响应
   - 遵守速率限制

3. **数据质量**
   - 免费计划数据可能不完整
   - 部分高级统计数据需要付费
   - 实时数据需要付费订阅

## 📚 参考资料

- [SportMonks 官方文档](https://docs.sportmonks.com/)
- [API v3 端点列表](https://docs.sportmonks.com/football/endpoints-and-entities/endpoints)
- [免费计划详情](https://www.sportmonks.com/pricing/)

## 🆘 故障排除

### 问题：API 返回 404
**原因：** 端点不存在或需要付费
**解决：** 检查端点路径，确认订阅计划

### 问题：API 返回 403
**原因：** 订阅计划不包含该端点
**解决：** 升级到付费计划或使用其他可用端点

### 问题：返回空数据
**原因：** 查询条件无匹配结果
**解决：** 检查查询参数，尝试不同的日期范围

### 问题：速率限制
**原因：** 请求过于频繁
**解决：** 添加请求间隔，实现重试逻辑

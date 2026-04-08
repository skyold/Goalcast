# SportMonks API v3 免费计划测试报告

## 📋 测试概述

**测试时间：** 2026-04-08 21:00:00  
**API Key:** Y4Q4Lr04PZS7WLz...  
**计划类型：** Football Free Plan  
**测试端点：** 22 个

## ✅ 可用端点（6 个）

### 1. Fixtures (比赛数据)

#### `/fixtures` - 比赛列表
- **状态：** ✅ 可用
- **数据量：** 25 条/页
- **参数：** `page` (分页)
- **用途：** 获取历史比赛数据
- **示例：**
  ```python
  response = await provider._request_raw("/fixtures", {"page": 1})
  # 返回 25 条历史比赛数据
  ```

#### `/fixtures/between/{start_date}/{end_date}` - 日期范围比赛
- **状态：** ✅ 可用
- **数据量：** 可变（取决于日期范围）
- **参数：** 开始日期、结束日期 (YYYY-MM-DD)
- **用途：** 获取特定时间段的比赛
- **示例：**
  ```python
  response = await provider.get_fixtures_between(
      "2026-04-08", "2026-04-15",
      include="participants"
  )
  # 返回 12 条比赛数据
  ```

### 2. Leagues (联赛数据)

#### `/leagues` - 联赛列表
- **状态：** ✅ 可用
- **数据量：** 25 条/页（实际返回 4 条）
- **参数：** `page` (分页)
- **用途：** 获取可用联赛列表
- **示例：**
  ```python
  response = await provider.get_leagues(page=1)
  # 返回：Superliga, Premiership 等联赛
  ```

### 3. Seasons (赛季数据)

#### `/seasons` - 赛季列表
- **状态：** ✅ 可用
- **数据量：** 25 条/页
- **参数：** `page` (分页)
- **用途：** 获取联赛赛季信息
- **示例：**
  ```python
  response = await provider.get_seasons(page=1)
  ```

### 4. Teams (球队数据)

#### `/teams` - 球队列表
- **状态：** ✅ 可用
- **数据量：** 25 条/页
- **参数：** `page` (分页)
- **用途：** 获取球队基本信息
- **示例：**
  ```python
  response = await provider.get_teams(page=1)
  # 返回球队 ID、名称、简称等信息
  ```

### 5. Players (球员数据)

#### `/players` - 球员列表
- **状态：** ✅ 可用
- **数据量：** 25 条/页
- **参数：** `page` (分页)
- **用途：** 获取球员基本信息
- **示例：**
  ```python
  response = await provider.get_players(page=1)
  ```

## ❌ 不可用端点（16 个）

### 实时数据（3 个）
- ❌ `/livescores` - 实时比分
- ❌ `/livescores/inplay` - 正在进行比赛
- ❌ `/livescores/latest` - 最新比赛

**错误信息：** "No result(s) found matching your request"

### 高级筛选（3 个）
- ❌ `/fixtures/date/{date}` - 按日期筛选
- ❌ `/leagues/countries/{id}` - 按国家筛选
- ❌ `/leagues/search/{name}` - 搜索联赛

**错误信息：** "No result(s) found matching your request"

### 统计数据（6 个）
- ❌ `/standings/seasons/{id}` - 积分榜
- ❌ `/teams/seasons/{id}` - 赛季球队数据
- ❌ `/topscorers/seasons/{id}` - 射手榜
- ❌ `/schedules/seasons/{id}` - 赛程计划
- ❌ `/rounds/seasons/{id}` - 轮次信息
- ❌ `/stages/seasons/{id}` - 阶段信息

**错误信息：** "No result(s) found matching your request"

### 赔率与预测（4 个）
- ❌ `/odds/markets` - 赔率市场 (HTTP 404)
- ❌ `/odds/bookmakers` - 博彩公司 (HTTP 404)
- ❌ `/predictions/value-bets` - 价值投注 (HTTP 403)
- ❌ `/fixtures/seasons/{id}` - 赛季比赛 (HTTP 404)

## 📊 数据使用统计

### 测试中获取的数据量

| 端点 | 返回数据量 | 说明 |
|------|-----------|------|
| `/fixtures` | 25 条 | 分页数据 |
| `/fixtures/between` | 12 条 | 7 天范围 |
| `/leagues` | 4 条 | 免费计划限制 |
| `/seasons` | 25 条 | 分页数据 |
| `/teams` | 25 条 | 分页数据 |
| `/players` | 25 条 | 分页数据 |

### 数据字段示例

#### Fixtures 数据
```json
{
  "id": 19146701,
  "sport_id": 1,
  "league_id": 501,
  "season_id": 23614,
  "stage_id": 77457731,
  "round_id": null,
  "name": null,
  "starting_at": "2026-04-08 19:00:00",
  "result_info": "FT",
  "participants": [...]
}
```

#### Leagues 数据
```json
{
  "id": 271,
  "sport_id": 1,
  "country_id": 320,
  "name": "Superliga",
  "active": true,
  "short_code": "DNK SL"
}
```

## 💡 使用建议

### ✅ 推荐使用场景

1. **历史比赛分析**
   - 使用 `/fixtures` 获取历史数据
   - 使用 `/fixtures/between` 获取特定时间段比赛

2. **基础数据查询**
   - 联赛列表查询
   - 球队基本信息
   - 球员基本信息

3. **数据聚合**
   - 分页获取完整数据集
   - 后处理筛选特定联赛/球队

### ❌ 不推荐使用场景

1. **实时数据需求**
   - 实时比分
   - 正在进行比赛
   - 最新赛况更新

2. **高级统计**
   - 积分榜排名
   - 球队详细统计
   - 射手榜

3. **特定日期查询**
   - 单日比赛查询（改用日期范围）
   - 按国家筛选联赛

## 🔄 替代方案

### 需要实时数据
**推荐：** 使用 FootyStats API
```python
matches = await footystats_get_todays_matches(date="2026-04-08")
```

### 需要积分榜
**推荐：** 使用 FootyStats API
```python
standings = await footystats_get_league_tables(season_id=14968)
```

### 需要球队统计
**推荐：** 使用 FootyStats API
```python
team_stats = await footystats_get_team_details(team_id=46)
```

## 📈 免费计划限制总结

### 数据访问限制
- ✅ 基础数据：联赛、球队、球员、比赛
- ❌ 实时数据：比分、赛况
- ❌ 高级统计：积分榜、射手榜
- ❌ 赔率预测：价值投注、详细赔率

### 功能限制
- ✅ 分页访问（每页 25 条）
- ✅ 日期范围查询
- ❌ 单日期精确查询
- ❌ 按国家/名称筛选

### 数据更新
- ⚠️ 历史数据较为完整
- ⚠️ 实时数据不可用
- ⚠️ 数据更新可能有延迟

## 🎯 最佳实践

### 1. 分页获取数据
```python
async def get_all_pages(provider, endpoint):
    all_data = []
    page = 1
    while True:
        response = await provider._request_raw(endpoint, {"page": page})
        if response and "data" in response:
            all_data.extend(response["data"])
            if len(response["data"]) < 25:
                break
            page += 1
    return all_data
```

### 2. 日期范围筛选
```python
# 获取本周比赛
from datetime import datetime, timedelta
today = datetime.now()
monday = today - timedelta(days=today.weekday())
sunday = monday + timedelta(days=6)

fixtures = await provider.get_fixtures_between(
    monday.strftime("%Y-%m-%d"),
    sunday.strftime("%Y-%m-%d")
)
```

### 3. 后处理筛选
```python
# 筛选特定联赛
leagues = await provider.get_leagues(page=1)
bundesliga_id = next(
    l["id"] for l in leagues["data"]
    if "bundesliga" in l["name"].lower()
)

fixtures = await provider.get_fixtures_between(start, end)
bundesliga_matches = [
    f for f in fixtures["data"]
    if f["league_id"] == bundesliga_id
]
```

## 📝 结论

SportMonks API v3 免费计划提供**基础但有限**的足球数据访问：

### 优势
- ✅ 6 个核心端点可用
- ✅ 支持分页获取数据
- ✅ 可获取历史比赛记录
- ✅ 基础联赛/球队/球员数据

### 劣势
- ❌ 无实时数据
- ❌ 无高级统计
- ❌ 无赔率预测
- ❌ 筛选功能受限

### 建议
对于需要**完整足球数据**的应用，建议：
1. 结合使用 FootyStats API（推荐）
2. 或升级到 SportMonks 付费计划
3. 免费计划仅用于基础数据查询和测试

---

**生成时间：** 2026-04-08 21:00:29  
**测试脚本：** `test_sportmonks_endpoints.py`  
**详细报告：** `sportmonks_api_report.json`

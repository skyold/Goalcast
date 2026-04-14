---
name: sportmonks-provider
description: Use this skill when the user needs SportMonks API v3 guidance, asks about free plan endpoints, fixtures/leagues/seasons data, or how to configure and use SportMonks API. NOT FOR MATCH ANALYSIS.
---

# SportMonks Provider Skill

## ⚠️ 重要架构变更说明 (2026-04-14)
**注意：本技能已退居幕后，仅作为“数据获取指南”使用。**
- **不可用于直接分析**：如果你正在执行足球比赛分析任务，请**停止使用**此技能，并改用 `sportmonks-analyst-v1` 技能读取本地缓存数据。
- **新职责**：本技能专用于指导数据工程师 Agent 或开发人员如何正确调用 SportMonks API（例如：编写 `prewarm_cache.py` 预热脚本、处理限流、免费端点限制等）。

## 📋 概述

本 skill 提供 SportMonks API v3 的完整使用指南，包括免费计划可用端点、使用技巧、最佳实践和常见问题解决方案。

**Provider 位置**: `provider/sportmonks/client.py`

## 🎯 触发条件

当用户询问以下内容时触发此 skill：
- "如何使用 SportMonks API"
- "SportMonks 免费计划能获取什么数据"
- "SportMonks API 端点测试"
- "获取足球比赛数据"
- "SportMonks API 配置"
- "SportMonks 使用示例"
- "查询比赛数据"
- "SportMonks API key 配置"

## 🔑 核心知识

### 1. 免费计划可用端点（6 个）✅

#### Fixtures (比赛数据)
- **`/fixtures`** - 获取比赛列表（分页，每页 25 条）
  - 用途：获取历史比赛、赛季数据
  - 参数：`page` (分页)
  - 示例：`await provider._request_raw("/fixtures", {"page": 1})`

- **`/fixtures/between/{start_date}/{end_date}`** - 获取日期范围内的比赛
  - 用途：获取特定时间段的比赛
  - 参数：日期范围 (YYYY-MM-DD)
  - 示例：`await provider.get_fixtures_between("2026-04-08", "2026-04-15")`

#### Leagues (联赛数据)
- **`/leagues`** - 获取联赛列表（分页）
  - 用途：获取可用联赛、识别联赛 ID
  - 参数：`page` (分页)
  - 示例：`await provider.get_leagues(page=1)`

#### Seasons (赛季数据)
- **`/seasons`** - 获取赛季列表（分页）
  - 用途：获取联赛赛季信息
  - 参数：`page` (分页)
  - 示例：`await provider.get_seasons(page=1)`

#### Teams (球队数据)
- **`/teams`** - 获取球队列表（分页）
  - 用途：获取球队信息、识别球队 ID
  - 参数：`page` (分页)
  - 示例：`await provider.get_teams(page=1)`

#### Players (球员数据)
- **`/players`** - 获取球员列表（分页）
  - 用途：获取球员基本信息
  - 参数：`page` (分页)
  - 示例：`await provider.get_players(page=1)`

### 2. 免费计划不可用端点（16 个）❌

#### 实时数据（需要付费）
- `/livescores` - 实时比分
- `/livescores/inplay` - 正在进行比赛
- `/livescores/latest` - 最新比赛

#### 高级筛选（需要付费）
- `/fixtures/date/{date}` - 按日期筛选
- `/leagues/countries/{id}` - 按国家筛选
- `/leagues/search/{name}` - 搜索联赛

#### 统计数据（需要付费）
- `/standings/seasons/{id}` - 积分榜
- `/teams/seasons/{id}` - 赛季球队
- `/topscorers/seasons/{id}` - 射手榜
- `/schedules/seasons/{id}` - 赛程计划
- `/rounds/seasons/{id}` - 轮次信息
- `/stages/seasons/{id}` - 阶段信息

#### 赔率与预测（需要付费）
- `/odds/markets` - 赔率市场
- `/odds/bookmakers` - 博彩公司
- `/predictions/value-bets` - 价值投注

## 💻 使用方法

### 初始化 Provider

```python
from provider.sportmonks.client import SportmonksProvider

# 使用配置文件中的 API key
provider = SportmonksProvider()

# 或直接传入 API key
provider = SportmonksProvider(api_key="your_api_key")

# 检查 API 是否可用
available = await provider.is_available()
if not available:
    print("API 不可用，请检查配置")
```

### 配置 API Key

在 `.env` 文件中配置：
```bash
SPORTMONKS_API_KEY=your_api_key_here
```

### 使用场景与示例

#### 场景 1: 获取本周德国甲级联赛比赛

```python
# 步骤 1: 获取联赛列表，找到德甲 ID
leagues = await provider.get_leagues(page=1)
bundesliga_id = None
for league in leagues.get("data", []):
    if "bundesliga" in league.get("name", "").lower():
        bundesliga_id = league["id"]
        break

# 步骤 2: 获取本周比赛
from datetime import datetime, timedelta
today = datetime.now()
monday = today - timedelta(days=today.weekday())
sunday = monday + timedelta(days=6)

fixtures = await provider.get_fixtures_between(
    monday.strftime("%Y-%m-%d"),
    sunday.strftime("%Y-%m-%d"),
    include="participants"
)

# 步骤 3: 筛选德甲比赛
bundesliga_fixtures = [
    f for f in fixtures.get("data", [])
    if f.get("league_id") == bundesliga_id
]

# 步骤 4: 显示结果
for fixture in bundesliga_fixtures:
    participants = fixture.get("participants", [])
    home = next((p.get("name") for p in participants if p.get("location") == "home"), "Unknown")
    away = next((p.get("name") for p in participants if p.get("location") == "away"), "Unknown")
    print(f"{home} vs {away}")
```

#### 场景 2: 分页获取完整数据

```python
async def get_all_pages(provider, endpoint, max_pages=10):
    """分页获取所有数据"""
    all_data = []
    for page in range(1, max_pages + 1):
        response = await provider._request_raw(endpoint, {"page": page})
        if response and "data" in response:
            all_data.extend(response["data"])
            if len(response["data"]) < 25:
                break  # 最后一页
    return all_data

# 使用示例
all_teams = await get_all_pages(provider, "/teams")
all_players = await get_all_pages(provider, "/players")
```

#### 场景 3: 获取单场比赛详情

```python
# 获取比赛详情（包括阵容、统计等）
fixture = await provider.get_fixture_by_id(
    fixture_id=19146701,
    include="participants,lineups,statistics"
)

# 提取信息
home_team = None
away_team = None
for p in fixture.get("data", {}).get("participants", []):
    if p.get("location") == "home":
        home_team = p.get("name")
    elif p.get("location") == "away":
        away_team = p.get("name")

print(f"{home_team} vs {away_team}")
```

## ⚠️ 注意事项

### 1. API 限制
- 免费计划有请求频率限制
- 部分端点返回历史数据而非实时数据
- 数据更新可能有延迟

### 2. 错误处理

```python
from typing import Optional

def safe_get_data(result: Any) -> Optional[list]:
    """安全提取数据"""
    if not result:
        return None
    if isinstance(result, dict):
        if "error" in result:
            print(f"API 错误：{result['error']}")
            return None
        return result.get("data", [])
    return None

# 使用示例
fixtures = await provider.get_fixtures_between(start_date, end_date)
data = safe_get_data(fixtures)
if not data:
    print("未获取到数据")
```

### 3. 速率限制处理

```python
import asyncio

async def rate_limited_call(provider, endpoint, params=None, delay=1.0):
    """带速率限制的 API 调用"""
    await asyncio.sleep(delay)  # 添加请求间隔
    return await provider._request_raw(endpoint, params or {})
```

### 4. 数据缓存

```python
import json
from pathlib import Path
from datetime import datetime, timedelta

cache_dir = Path("data/cache")
cache_dir.mkdir(exist_ok=True)

async def cached_api_call(provider, endpoint, params=None, cache_ttl=3600):
    """带缓存的 API 调用"""
    import time
    
    cache_key = f"{endpoint}_{json.dumps(params or {})}"
    cache_file = cache_dir / f"{hash(cache_key)}.json"
    
    # 检查缓存
    if cache_file.exists():
        cache_data = json.loads(cache_file.read_text())
        if time.time() - cache_data["timestamp"] < cache_ttl:
            return cache_data["data"]
    
    # API 调用
    result = await provider._request_raw(endpoint, params or {})
    if result:
        # 保存缓存
        json.dump({
            "timestamp": time.time(),
            "data": result
        }, cache_file.open("w"))
    
    return result
```

## 🔍 常见问题解答

### Q1: 为什么获取不到实时比分？
**A:** 免费计划不包含实时数据端点（`/livescores`）。需要使用 FootyStats API 或升级到 SportMonks 付费计划。

### Q2: 如何获取特定联赛的比赛？
**A:** 
1. 先用 `/leagues` 获取联赛列表，找到联赛 ID
2. 用 `/fixtures/between` 获取日期范围内的比赛
3. 在后处理中按 `league_id` 筛选

### Q3: API 返回 404 怎么办？
**A:** 
- 检查端点路径是否正确
- 某些端点如 `/fixtures/seasons/{id}` 在免费计划不可用
- 改用 `/fixtures` 或 `/fixtures/between` 端点

### Q4: 如何获取完整的赛季赛程？
**A:** 免费计划无法直接获取。替代方案：
1. 使用 `/fixtures/between` 获取整个赛季日期范围
2. 分页获取 `/fixtures` 然后筛选
3. 使用 FootyStats API 的 `/league-matches` 端点

### Q5: 数据如何更新？
**A:** 
- 免费计划数据更新有延迟
- 历史比赛数据较为完整
- 实时数据需要付费订阅

## 📊 与 FootyStats API 对比

| 功能 | SportMonks 免费计划 | FootyStats |
|------|-------------------|------------|
| 联赛列表 | ✅ 有限 | ✅ 完整 |
| 比赛数据 | ✅ 有限 | ✅ 完整 |
| 实时比分 | ❌ | ❌ |
| 积分榜 | ❌ | ✅ |
| 球队统计 | ❌ | ✅ |
| 球员数据 | ✅ 基础 | ✅ 详细 |
| 赔率数据 | ❌ | ✅ |
| 使用难度 | 中等 | 简单 |

**建议：** 
- 基础数据查询：使用 SportMonks
- 完整联赛数据：使用 FootyStats
- 实时数据：都需要付费

## 📚 相关文档

- [详细使用指南](../docs/SPORTMONKS_USAGE.md)
- [测试报告](../docs/SPORTMONKS_TEST_REPORT.md)
- [MCP 服务器文档](../mcp_server/README.md)

## 🆘 故障排除

### 问题：API 返回 401 错误
**原因：** API Key 无效或缺失  
**解决：** 检查 `.env` 文件中的配置，确认环境变量已加载

### 问题：响应超时
**原因：** 数据量过大或网络问题  
**解决：** 增加超时时间，使用分页获取数据

### 问题：SportMonks 返回空数据
**原因：** 免费计划限制  
**解决：** 
1. 改用 FootyStats API
2. 检查端点是否在免费计划内
3. 升级到付费计划

## 📝 最佳实践

1. **始终检查 API 可用性**
   ```python
   if not await provider.is_available():
       print("API 不可用")
       return
   ```

2. **使用分页获取大数据集**
   ```python
   async def get_all_data(provider, endpoint):
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

3. **添加适当的错误处理**
   ```python
   try:
       data = await provider.get_leagues(page=1)
       if data and "data" in data:
           process_data(data["data"])
   except Exception as e:
       logger.error(f"API 错误：{e}")
   ```

4. **实现数据缓存**
   - 避免重复请求相同数据
   - 设置合理的缓存过期时间
   - 对于静态数据（如联赛列表）使用较长缓存

## 🔄 更新日志

- **2026-04-08**: 初始版本，基于实际 API 测试结果
  - 测试了 22 个端点
  - 确认 6 个免费可用端点
  - 提供完整使用示例

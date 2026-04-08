# Goalcast MCP Server

Goalcast MCP Server 提供足球数据 API 接口，支持 SportMonks 和 FootyStats 两个数据源。

## 📊 数据源状态

### SportMonks API v3

**配置状态：** ✅ 已配置  
**计划类型：** Football Free Plan  
**可用性：** ✅ 部分可用

#### ✅ 免费计划可用端点 (6 个)

| 端点 | 功能 | 数据量 | 用途 |
|------|------|--------|------|
| `/fixtures` | 比赛列表 | 25 条/页 | 获取历史比赛数据 |
| `/fixtures/between/{start}/{end}` | 日期范围比赛 | 可变 | 获取特定时间段比赛 |
| `/leagues` | 联赛列表 | 25 条/页 | 获取可用联赛 |
| `/seasons` | 赛季列表 | 25 条/页 | 获取赛季信息 |
| `/teams` | 球队列表 | 25 条/页 | 获取球队信息 |
| `/players` | 球员列表 | 25 条/页 | 获取球员信息 |

#### ❌ 免费计划不可用端点（需要付费）

- 实时数据：`/livescores`, `/livescores/inplay`, `/livescores/latest`
- 高级筛选：`/fixtures/date`, `/leagues/countries`, `/leagues/search`
- 统计数据：`/standings`, `/teams/seasons`, `/topscorers`
- 赔率预测：`/odds/*`, `/predictions/*`

#### 使用建议

**推荐场景：**
- ✅ 获取历史比赛数据
- ✅ 获取联赛/球队/球员基础信息
- ✅ 日期范围筛选比赛

**不推荐场景：**
- ❌ 实时比分查询（使用 FootyStats）
- ❌ 积分榜查询（使用 FootyStats）
- ❌ 详细统计分析（使用 FootyStats）

### FootyStats API

**配置状态：** ✅ 已配置  
**计划类型：** 标准计划  
**可用性：** ✅ 完全可用

#### 主要功能

- ✅ 联赛列表和赛程
- ✅ 积分榜
- ✅ 球队详细统计
- ✅ 比赛详情（含赔率、阵容）
- ✅ BTTS 和 Over/Under 统计

## 🚀 启动方式

### 本地开发模式

```bash
# 激活虚拟环境
source .venv/bin/activate

# 启动 MCP 服务器
python mcp_server/server.py
```

### SSE 模式（远程访问）

```bash
# 启动 SSE 模式
python mcp_server/server.py sse

# 或指定主机和端口
FASTMCP_HOST=0.0.0.0 FASTMCP_PORT=8000 python mcp_server/server.py
```

## 🛠️ 可用工具

### FootyStats 工具（推荐用于完整数据）

1. **footystats_get_league_list** - 获取联赛列表
2. **footystats_get_todays_matches** - 获取今日/指定日期比赛
3. **footystats_get_league_matches** - 获取联赛完整赛程
4. **footystats_get_league_tables** - 获取积分榜
5. **footystats_get_league_stats** - 获取联赛统计
6. **footystats_get_match_details** - 获取比赛详情
7. **footystats_get_team_details** - 获取球队详情
8. **footystats_get_btts_stats** - BTTS 统计
9. **footystats_get_over25_stats** - Over 2.5 统计

### SportMonks 工具（推荐用于基础数据）

1. **sportmonks_get_livescores** - 实时比分（免费计划受限）
2. **sportmonks_get_fixtures_by_date** - 指定日期比赛（免费计划受限）
3. **sportmonks_get_fixture_by_id** - 比赛详情
4. **sportmonks_get_lineups** - 比赛阵容
5. **sportmonks_get_player_stats** - 球员统计
6. **sportmonks_get_head_to_head** - 交锋记录
7. **sportmonks_get_expected_goals** - 期望进球 (xG)

## 📖 使用示例

### 示例 1：获取本周德国甲级联赛比赛

#### 使用 SportMonks（基础数据）

```python
# 步骤 1: 获取联赛列表
leagues = await sportmonks_get_leagues(page=1)
bundesliga = next(l for l in leagues["data"] 
                  if "bundesliga" in l["name"].lower())

# 步骤 2: 获取本周比赛
from datetime import datetime, timedelta
today = datetime.now()
monday = today - timedelta(days=today.weekday())
sunday = monday + timedelta(days=6)

fixtures = await sportmonks_get_fixtures_between(
    monday.strftime("%Y-%m-%d"),
    sunday.strftime("%Y-%m-%d")
)

# 步骤 3: 筛选德甲比赛
bundesliga_fixtures = [
    f for f in fixtures["data"]
    if f["league_id"] == bundesliga["id"]
]
```

#### 使用 FootyStats（推荐）

```python
# 步骤 1: 获取联赛列表
leagues = await footystats_get_league_list()
bundesliga = next(l for l in leagues["data"]
                  if "bundesliga" in l["league_name"].lower())

# 步骤 2: 获取今日比赛（带联赛过滤）
matches = await footystats_get_todays_matches(
    date="2026-04-08",
    league_filter="Bundesliga"
)
```

### 示例 2：获取球队详情

#### 使用 SportMonks

```python
# 获取球队列表
teams = await sportmonks_get_teams(page=1)
bayern = next(t for t in teams["data"]
              if "bayern" in t["name"].lower())

# 获取球队参与的比赛
fixtures = await sportmonks_get_fixtures_by_date("2026-04-08")
bayern_matches = [
    f for f in fixtures["data"]
    for p in f["participants"]
    if p["id"] == bayern["id"]
]
```

#### 使用 FootyStats（推荐）

```python
# 直接获取球队详情
team_details = await footystats_get_team_details(team_id=46)

# 获取球队近期状态
recent_form = await footystats_get_team_last_x_stats(team_id=46)
```

### 示例 3：获取比赛详情

#### 使用 SportMonks

```python
# 获取比赛详情（含阵容）
fixture = await sportmonks_get_fixture_by_id(
    fixture_id=19146701,
    include="participants,lineups,statistics"
)

# 获取 xG 数据
xg_data = await sportmonks_get_expected_goals(fixture_id=19146701)
```

#### 使用 FootyStats

```python
# 获取完整比赛详情
match_details = await footystats_get_match_details(match_id=8227534)

# 获取阵容
lineups = await footystats_get_lineups(match_id=8227534)
```

## 🎯 最佳实践

### 1. 选择合适的 API

| 需求 | 推荐 API | 原因 |
|------|---------|------|
| 实时比分 | FootyStats | SportMonks 免费计划不可用 |
| 积分榜 | FootyStats | SportMonks 免费计划不可用 |
| 历史比赛 | SportMonks | 基础数据足够 |
| 球队统计 | FootyStats | 数据更详细 |
| 联赛赛程 | FootyStats | 完整的赛季数据 |
| 球员信息 | SportMonks | 基础信息可用 |

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
```

### 3. 数据缓存

```python
import json
from pathlib import Path
from datetime import datetime, timedelta

cache_dir = Path("data/mcp_cache")
cache_dir.mkdir(exist_ok=True)

def get_cached(key: str, ttl_hours: int = 1) -> Optional[Any]:
    """获取缓存数据"""
    cache_file = cache_dir / f"{key}.json"
    if cache_file.exists():
        data = json.loads(cache_file.read_text())
        cached_at = datetime.fromisoformat(data["timestamp"])
        if datetime.now() - cached_at < timedelta(hours=ttl_hours):
            return data["content"]
    return None

def set_cached(key: str, content: Any):
    """保存缓存数据"""
    cache_file = cache_dir / f"{key}.json"
    json.dump({
        "timestamp": datetime.now().isoformat(),
        "content": content
    }, cache_file.open("w"), indent=2)
```

### 4. 速率限制

```python
import asyncio

async def rate_limited_call(func, *args, delay: float = 1.0, **kwargs):
    """带速率限制的调用"""
    await asyncio.sleep(delay)
    return await func(*args, **kwargs)
```

## 📝 配置说明

### 环境变量

在 `.env` 文件中配置：

```bash
# SportMonks API
SPORTMONKS_API_KEY=your_sportmonks_key

# FootyStats API
FOOTYSTATS_API_KEY=your_footystats_key

# MCP Server 配置
FASTMCP_HOST=127.0.0.1
FASTMCP_PORT=8000
```

### MCP 客户端配置

在 Claude Desktop 配置中添加：

```json
{
  "mcpServers": {
    "goalcast": {
      "command": "python",
      "args": ["/path/to/mcp_server/server.py"],
      "env": {
        "SPORTMONKS_API_KEY": "your_key",
        "FOOTYSTATS_API_KEY": "your_key"
      }
    }
  }
}
```

## 🔍 故障排除

### 问题：API 返回 401 错误

**原因：** API Key 无效或缺失

**解决方案：**
1. 检查 `.env` 文件中的配置
2. 确认环境变量已加载
3. 重启 MCP 服务器

### 问题：响应超时

**原因：** 数据量过大

**解决方案：**
1. 使用 `league_filter` 参数过滤
2. 使用分页获取数据
3. 减少 `include` 参数

### 问题：SportMonks 返回空数据

**原因：** 免费计划限制

**解决方案：**
1. 改用 FootyStats API
2. 检查端点是否在免费计划内
3. 升级到付费计划

## 📚 相关文档

- [SportMonks 使用指南](../docs/SPORTMONKS_USAGE.md)
- [FootyStats 使用指南](../provider/footystats/README.md)
- [MCP 迁移指南](../docs/MCP_MIGRATION_GUIDE.md)

## 🆘 支持

如有问题，请查看：
- [SportMonks 官方文档](https://docs.sportmonks.com/)
- [FootyStats API 文档](https://api.football-data-api.com/)

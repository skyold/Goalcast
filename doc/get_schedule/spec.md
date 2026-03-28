# get_schedule 命令行功能规格说明书

## 1. 功能概述

开发一个名为 `get_schedule` 的命令行工具，用于获取和显示足球比赛日程表。该工具基于 FootyStats API 提供比赛数据，支持多种查询模式，包括按时间范围查询和按球队查询。

## 2. 功能需求

### 2.1 显示字段

每场比赛必须显示以下信息：

| 字段 | 说明 | 数据来源 |
|------|------|----------|
| 比赛时间 | 比赛开球时间（格式：YYYY-MM-DD HH:MM） | `kickoff_time` / `date_unix` |
| 比赛 ID | 比赛的唯一标识符 | `id` |
| 开赛联赛 | 比赛所属联赛名称 | `league_name` |
| 比赛国家 | 联赛所属国家 | 从 `league-list` API 获取 |
| 主队名称 | 主队完整名称 | `home_name` |
| 主队 ID | 主队唯一标识符 | `homeID` |
| 客队名称 | 客队完整名称 | `away_name` |
| 客队 ID | 客队唯一标识符 | `awayID` |
| 比赛状态 | 比赛当前状态 | `status` |

### 2.2 查询模式

#### 模式 1：时间范围查询

**子模式 1.1**: 最近有比赛的一天
- 从今天开始向后查找，返回第一个有比赛日期的所有比赛
- 参数：`--nearest`

**子模式 1.2**: 未来 N 天所有比赛
- 获取从今天开始未来 N 天内的所有比赛
- 参数：`--next-days N`（N 为正整数）

**子模式 1.3**: 指定起始日期范围内的比赛
- 获取指定日期范围内的所有比赛
- 参数：`--from YYYY-MM-DD` 和 `--to YYYY-MM-DD`

#### 模式 2：球队 + 时间查询

**子模式 2.1**: 球队最近的一场比赛
- 查找指定球队最近的一场比赛（包括历史比赛和未来比赛）
- 参数：`--team "球队名称"` + `--nearest`

**子模式 2.2**: 球队未来几天内的比赛
- 查找指定球队在未来 N 天内的所有比赛
- 参数：`--team "球队名称"` + `--next-days N`

**子模式 2.3**: 球队在指定时间范围内的比赛
- 查找指定球队在指定日期范围内的所有比赛
- 参数：`--team "球队名称"` + `--from YYYY-MM-DD` + `--to YYYY-MM-DD`

### 2.3 输出格式

#### 表格格式（默认）
```
┌──────────────┬──────────┬─────────────────┬──────────────┬─────────────────────┬─────────┬─────────────────────┬─────────┬───────────┐
│ 比赛时间     │ 比赛 ID  │ 开赛联赛        │ 比赛国家     │ 主队名称            │ 主队 ID │ 客队名称            │ 客队 ID │ 比赛状态  │
├──────────────┼──────────┼─────────────────┼──────────────┼─────────────────────┼─────────┼─────────────────────┼─────────┼───────────┤
│ 2026-03-28   │ 579101   │ Premier League  │ England      │ Manchester City     │ 1       │ Liverpool           │ 14      │ SCHEDULED │
│ 15:00        │          │                 │              │                     │         │                     │         │           │
└──────────────┴──────────┴─────────────────┴──────────────┴─────────────────────┴─────────┴─────────────────────┴─────────┴───────────┘
```

#### JSON 格式
- 参数：`--json`
- 输出结构化的 JSON 数据

#### 简洁格式
- 参数：`--compact`
- 每行显示一场比赛的基本信息

### 2.4 辅助功能

- **联赛国家映射缓存**: 首次调用时缓存联赛 - 国家映射关系，避免重复 API 调用
- **球队名称模糊匹配**: 支持部分球队名称匹配（不区分大小写）
- **错误处理**: 友好的错误提示信息
- **调试模式**: 显示 API 原始返回数据

## 3. 技术实现

### 3.1 文件结构

```
cmd/
├── get_schedule.py          # 主命令行脚本（只调用 DataSource 层）
└── __init__.py

src/
├── provider/
│   └── footystats/
│       └── client.py        # Provider 层，直接调用 API
├── datasource/
│   ├── match/
│   │   └── match_datasource.py  # DataSource 层，已有 fetch_* 方法
│   └── types.py             # 数据类型定义（Match 已包含所有字段）
└── utils/
    └── league_cache.py      # 联赛 - 国家映射缓存工具
```

### 3.2 架构层次

```
┌─────────────────────────────────────┐
│     Command Layer (cmd/)            │  ← 命令行界面
│     - get_schedule.py               │     只调用 DataSource
├─────────────────────────────────────┤
│     DataSource Layer (src/datasource/)  ← 业务逻辑层
│     - MatchDataSource               │     数据解析、缓存、聚合
│     - 已有方法：fetch_for_date,     │
│       fetch_next_n_days, 等         │
├─────────────────────────────────────┤
│     Provider Layer (src/provider/)  ← API 适配层
│     - FootyStatsProvider            │     直接调用 FootyStats API
│     - get_todays_matches()          │
└─────────────────────────────────────┘
```

### 3.3 依赖关系

**注意**：命令行只调用 DataSource 层，不直接调用 Provider 层。

- **MatchDataSource** (DataSource 层): 命令行的主要调用对象
  - ✅ `fetch_for_date()`: 获取指定日期的比赛 - **已存在**
  - ✅ `fetch_in_date_range()`: 获取日期范围内的比赛 - **已存在**
  - ✅ `fetch_next_n_days()`: 获取未来 N 天的比赛 - **已存在**
  - ✅ `fetch_nearest_match_day()`: 获取最近比赛日 - **已存在**
  - ✅ `fetch_upcoming_summary()`: 获取汇总信息 - **已存在**
  - 新增：`fetch_for_date_with_country()`: 获取指定日期比赛并包含国家信息
  - 新增：`filter_matches_by_team()`: 过滤包含指定球队的比赛

- **FootyStatsProvider** (Provider 层): 由 DataSource 内部调用
  - ✅ `get_todays_matches()`: 获取指定日期的比赛 - **已存在**
  - ✅ `get_league_list()`: 获取联赛列表 - **已存在**
  - 新增：`get_league_country_mapping()`: 获取联赛 - 国家映射（辅助方法）

### 3.4 核心算法

#### 球队比赛查找算法（在 DataSource 层实现）

```python
# 在 MatchDataSource 类中添加
async def fetch_team_matches(
    self,
    team_name: str,
    start_date: date,
    end_date: date
) -> List[Match]:
    """
    查找指定球队在日期范围内的所有比赛
    
    实现步骤：
    1. 调用 fetch_in_date_range() 获取范围内所有比赛
    2. 过滤包含指定球队的比赛（主队或客队）
    3. 支持模糊匹配（不区分大小写，部分匹配）
    4. 返回过滤后的比赛列表
    """
    date_range_data = await self.fetch_in_date_range(start_date, end_date)
    
    all_matches = []
    for day_data in date_range_data:
        for match in day_data["matches"]:
            if self._matches_team(match, team_name):
                all_matches.append(match)
    
    return all_matches

def _matches_team(self, match: Match, team_name: str) -> bool:
    """
    判断比赛是否包含指定球队（模糊匹配）
    """
    team_name_lower = team_name.lower()
    return (team_name_lower in match.home_team.lower() or 
            team_name_lower in match.away_team.lower())
```

#### 联赛 - 国家映射缓存（工具类）

```python
# 在 src/utils/league_cache.py 中
class LeagueCountryCache:
    """联赛 - 国家映射缓存类"""
    
    _instance = None
    _mapping: Dict[str, str] = {}
    _cache_time: float = 0
    _ttl: int = 86400  # 24 小时
    
    async def get_country(self, league_name: str) -> str:
        """
        获取联赛所属国家
        
        1. 首先检查缓存是否过期
        2. 如果过期，调用 Provider API 获取联赛列表
        3. 构建联赛 - 国家映射并缓存
        4. 返回国家名称，找不到返回 "Unknown"
        """
        if self._is_cache_expired():
            await self._load_from_api()
        
        return self._mapping.get(league_name, "Unknown")
```

### 3.5 命令行参数设计

```python
parser = argparse.ArgumentParser(
    description="FootyStats 比赛日程查询工具",
    formatter_class=argparse.RawDescriptionHelpFormatter
)

# 查询模式（互斥组）
mode_group = parser.add_mutually_exclusive_group()
mode_group.add_argument("--nearest", action="store_true",
                        help="获取最近有比赛的一天的所有比赛")
mode_group.add_argument("--next-days", type=int, metavar="N",
                        help="获取未来 N 天内的所有比赛")
mode_group.add_argument("--date-range", nargs=2, metavar=("YYYY-MM-DD", "YYYY-MM-DD"),
                        help="获取指定日期范围内的所有比赛")

# 球队过滤
parser.add_argument("--team", type=str, metavar="TEAM_NAME",
                    help="球队名称（支持模糊匹配）")

# 输出格式
format_group = parser.add_mutually_exclusive_group()
format_group.add_argument("--json", action="store_true",
                          help="输出 JSON 格式")
format_group.add_argument("--compact", action="store_true",
                          help="输出简洁格式")

# 其他选项
parser.add_argument("--debug", action="store_true",
                    help="打印调试信息")
parser.add_argument("--no-cache", action="store_true",
                    help="不使用缓存（强制刷新联赛 - 国家映射）")
```

### 3.6 状态码映射

FootyStats API 返回的比赛状态需要映射到标准状态：

| API 状态 | 映射状态 | 说明 |
|----------|----------|------|
| incomplete | SCHEDULED | 比赛未开始 |
| timed | TIMED | 已设定时间 |
| in_play / live | LIVE | 比赛中 |
| paused | PAUSED | 暂停 |
| complete / finished | FINISHED | 比赛结束 |
| suspended | SUSPENDED | 比赛中断 |
| canceled / postponed | CANCELED | 比赛取消/延期 |

## 4. DataSource 层扩展

### 4.1 需要添加的方法

在 `MatchDataSource` 类中添加以下方法：

#### 4.1.1 球队比赛过滤

```python
async def fetch_team_matches(
    self,
    team_name: str,
    start_date: date,
    end_date: date
) -> List[Match]:
    """
    获取指定球队在日期范围内的所有比赛
    
    Args:
        team_name: 球队名称（支持模糊匹配）
        start_date: 开始日期
        end_date: 结束日期
    
    Returns:
        比赛列表
    """
```

#### 4.1.2 带国家信息的比赛查询

```python
async def fetch_for_date_with_country(
    self,
    target_date: date,
    league_cache: LeagueCountryCache
) -> List[Dict[str, Any]]:
    """
    获取指定日期的比赛，并包含联赛国家信息
    
    Args:
        target_date: 目标日期
        league_cache: 联赛 - 国家缓存实例
    
    Returns:
        比赛数据列表，每项包含 match 对象和 country 字段
    """
```

### 4.2 工具类实现

在 `src/utils/league_cache.py` 创建：

```python
class LeagueCountryCache:
    """联赛 - 国家映射缓存（单例模式）"""
    
    @classmethod
    async def get_instance(cls) -> 'LeagueCountryCache':
        """获取单例实例"""
    
    async def get_country(self, league_name: str) -> str:
        """获取联赛所属国家"""
    
    async def refresh(self) -> None:
        """强制刷新缓存"""
```

## 5. API 使用策略

### 5.1 主要 API 端点

1. **`/todays-matches`**: 获取指定日期的比赛
   - 参数：`date` (YYYY-MM-DD), `timezone`
   - 用途：所有日期查询模式的基础
   - 调用方式：通过 `MatchDataSource.fetch_for_date()` 间接调用

2. **`/league-list`**: 获取联赛列表
   - 参数：`country` (可选)
   - 用途：构建联赛 - 国家映射
   - 调用方式：通过 `LeagueCountryCache` 间接调用

### 5.2 速率限制处理

- FootyStats API 有每小时请求限制
- DataSource 层实现缓存：
  - 日期查询结果缓存 30 秒（已在 `MatchDataSource` 中实现）
  - 联赛 - 国家映射缓存 24 小时（在 `LeagueCountryCache` 中实现）
- 批量查询时添加延迟（0.5 秒/请求）

## 6. 错误处理

### 6.1 错误类型

| 错误类型 | 错误码 | 处理方式 |
|----------|--------|----------|
| API Key 未配置 | 1001 | 提示用户配置 API Key |
| API 不可用 | 1002 | 检查网络连接和 API 状态 |
| 日期格式错误 | 2001 | 提示正确的日期格式 |
| 球队未找到 | 3001 | 提示可能的拼写错误或建议 |
| 无比赛数据 | 4001 | 友好提示无比赛 |
| 参数冲突 | 5001 | 提示正确的参数组合 |

### 6.2 错误消息示例

```
❌ 错误：未找到球队 "Mancherster United"
💡 提示：请检查球队名称拼写，是否意为 "Manchester United"？

❌ 错误：日期格式无效 "2026/03/28"
💡 提示：请使用 YYYY-MM-DD 格式，例如：2026-03-28

❌ 错误：API Key 未配置
💡 提示：请在配置文件中设置 FOOTYSTATS_API_KEY

ℹ️  提示：2026-03-28 至 2026-03-30 期间没有比赛
```

## 7. 性能优化

### 7.1 缓存策略

- **日期查询缓存**: 30 秒 TTL（已在 `MatchDataSource` 中实现）
- **联赛 - 国家映射缓存**: 24 小时 TTL（在 `LeagueCountryCache` 中实现）
- **球队 ID 缓存**: 1 小时 TTL（可选）

### 7.2 并发优化

- 使用 `asyncio.gather()` 并发获取多天数据
- 限制并发请求数（最大 3 个并发）
- 使用信号量控制并发度

## 8. 测试策略

### 8.1 单元测试

- 日期解析和验证
- 球队名称模糊匹配逻辑
- 状态码映射
- 缓存机制

### 8.2 集成测试

- API 调用测试（使用测试 API Key）
- 端到端命令行测试
- 错误处理测试

### 8.3 性能测试

- 大量日期范围查询性能
- 缓存命中率测试
- 并发请求性能

## 9. 文档要求

### 9.1 代码文档

- 模块级 docstring
- 函数级 docstring（包含参数说明和返回值）
- 关键算法注释

### 9.2 用户文档

- README 文件（包含使用示例）
- 命令行帮助信息（--help）
- 常见问题解答（FAQ）

## 10. 验收标准

### 10.1 功能验收

- [ ] 所有查询模式正常工作
- [ ] 显示字段完整且准确
- [ ] 球队模糊匹配有效
- [ ] 错误处理友好且准确
- [ ] 输出格式正确

### 10.2 性能验收

- [ ] 单次查询响应时间 < 3 秒
- [ ] 缓存命中率 > 80%
- [ ] 并发请求无竞态条件

### 10.3 代码质量

- [ ] 符合项目代码规范
- [ ] 通过 lint 检查
- [ ] 单元测试覆盖率 > 80%
- [ ] 文档完整

## 11. 参考资料

- [FootyStats API 文档](/Users/zhengningdai/workspace/skyold/Goalcast/src/provider/footystats/footystats%20API%20document.md)
- [现有 get_matches 实现](/Users/zhengningdai/workspace/skyold/Goalcast/cmd/get_matches.py)
- [现有 get_matches_from_provider 实现](/Users/zhengningdai/workspace/skyold/Goalcast/cmd/get_matches_from_provider.py)
- [Match 数据类型定义](/Users/zhengningdai/workspace/skyold/Goalcast/src/datasource/types.py)

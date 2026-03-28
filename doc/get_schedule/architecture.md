# get_schedule 架构决策记录

## 决策背景

在开发 `get_schedule` 命令行功能时，需要明确软件架构层次和各层职责。

## 架构决策

### 决策 1：分层架构

**决策**：采用三层架构

```
Command Layer (cmd/)
    ↓ calls
DataSource Layer (src/datasource/)
    ↓ uses
Provider Layer (src/provider/)
```

**理由**：
1. **职责分离**：每层有明确的职责
   - Command Layer：用户界面和参数解析
   - DataSource Layer：业务逻辑、数据聚合、缓存
   - Provider Layer：API 调用适配

2. **可维护性**：层次清晰，易于理解和维护

3. **可测试性**：各层可独立测试

4. **符合项目现有架构**：项目已有 DataSource 和 Provider 分层

### 决策 2：命令行只调用 DataSource

**决策**：命令行工具只调用 DataSource 层的方法，不直接调用 Provider 层。

**正确示例**：
```python
from datasource.match import MatchDataSource

match_ds = MatchDataSource()
matches = await match_ds.fetch_for_date(target_date=date(2026, 3, 28))
```

**错误示例**：
```python
from provider.footystats import FootyStatsProvider

provider = FootyStatsProvider()
matches = await provider.get_todays_matches(date="2026-03-28")
```

**理由**：
1. **数据封装**：DataSource 层封装了数据解析、缓存等逻辑
2. **统一接口**：DataSource 提供统一的业务接口
3. **缓存机制**：DataSource 层已实现缓存，避免重复 API 调用
4. **多 Provider 支持**：DataSource 可以聚合多个 Provider 的数据

### 决策 3：复用现有 DataSource 方法

**决策**：充分利用 MatchDataSource 已有的方法，避免重复实现。

**已有方法**：
- ✅ `fetch_for_date()` - 获取指定日期的比赛
- ✅ `fetch_in_date_range()` - 获取日期范围内的比赛
- ✅ `fetch_next_n_days()` - 获取未来 N 天的比赛
- ✅ `fetch_nearest_match_day()` - 获取最近比赛日
- ✅ `fetch_upcoming_summary()` - 获取汇总信息

**需要扩展的方法**：
- ➕ `fetch_team_matches()` - 获取球队比赛（新增）
- ➕ `fetch_for_date_with_country()` - 带国家信息的比赛查询（可选）

**理由**：
1. **避免重复造轮子**：现有方法已实现核心功能
2. **保证一致性**：使用统一的数据访问方法
3. **减少维护成本**：逻辑集中在一处

### 决策 4：联赛 - 国家映射缓存（重新评估）

**原决策**：创建独立的缓存工具类 `LeagueCountryCache` 在 `src/utils/league_cache.py`

**问题**：
1. utils 层不应该包含业务逻辑和 API 调用
2. 联赛 - 国家映射是业务数据，应该由 DataSource 管理
3. 违反了"所有对 Provider 的调用都在 DataSource 层"的原则

**新决策**：创建 `LeagueDataSource` 在 DataSource 层

**实现位置**：`src/datasource/league/league_datasource.py`

**理由**：
1. **职责清晰**：DataSource 层负责所有业务数据的获取和缓存
2. **数据封装**：联赛数据和国家映射都在 DataSource 层管理
3. **统一接口**：Command 层通过 DataSource 获取所有数据
4. **符合架构原则**：所有 Provider 调用都在 DataSource 层

## 架构对比

### ❌ 错误架构（扁平化）

```
Command Layer
    ↓ calls
Provider Layer (直接调用 API)
```

**问题**：
- 缺少业务逻辑层
- 命令行直接处理 API 原始数据
- 无法利用缓存
- 代码重复

### ✅ 正确架构（分层）

```
Command Layer
    ↓ calls
DataSource Layer (业务逻辑、缓存、聚合)
    ↓ uses
Provider Layer (API 调用)
```

**优势**：
- 职责清晰
- 可维护性强
- 可测试性好
- 可复用性高

## 实现指南

### Command Layer 职责

```python
# cmd/get_schedule.py

async def main():
    # 1. 参数解析
    args = parser.parse_args()
    
    # 2. 初始化 DataSource（不直接初始化 Provider）
    match_ds = MatchDataSource()
    league_ds = LeagueDataSource()
    
    # 3. 调用 DataSource 方法
    if args.nearest:
        result = await match_ds.fetch_nearest_match_day()
    elif args.next_days:
        result = await match_ds.fetch_next_n_days(args.next_days)
    
    # 4. 获取国家信息（通过 LeagueDataSource）
    for match in result:
        country = await league_ds.get_country(match.competition)
        # 格式化输出...
    
    # 5. 输出结果
    print(format_table(result, league_ds))
```

### DataSource Layer 职责

```python
# src/datasource/match/match_datasource.py

class MatchDataSource:
    async def fetch_team_matches(
        self,
        team_name: str,
        start_date: date,
        end_date: date
    ) -> List[Match]:
        # 1. 调用已有方法获取日期范围内所有比赛
        date_range_data = await self.fetch_in_date_range(start_date, end_date)
        
        # 2. 过滤包含指定球队的比赛
        filtered = []
        for day_data in date_range_data:
            for match in day_data["matches"]:
                if self._matches_team(match, team_name):
                    filtered.append(match)
        
        return filtered
    
    def _matches_team(self, match: Match, team_name: str) -> bool:
        # 模糊匹配逻辑
        team_name_lower = team_name.lower()
        return (team_name_lower in match.home_team.lower() or 
                team_name_lower in match.away_team.lower())
```

### LeagueDataSource 职责

```python
# src/datasource/league/league_datasource.py

class LeagueDataSource:
    """联赛数据源 - 管理联赛和国家数据"""
    
    def __init__(self, providers: List[BaseProvider] = None):
        super().__init__(providers)
        self._league_country_cache: Dict[str, str] = {}
    
    async def get_country(self, league_name: str) -> str:
        """获取联赛所属国家"""
        # 1. 检查缓存
        if league_name in self._league_country_cache:
            return self._league_country_cache[league_name]
        
        # 2. 从 API 加载
        await self._load_league_list()
        
        # 3. 返回结果
        return self._league_country_cache.get(league_name, "Unknown")
    
    async def _load_league_list(self):
        """从 Provider 加载联赛列表"""
        raw_data = await self._try_providers("get_league_list")
        if raw_data and raw_data.get("success"):
            for league in raw_data.get("data", []):
                league_name = league.get("name", "")
                country = league.get("country", "")
                if league_name and country:
                    self._league_country_cache[league_name] = country
```

### Provider Layer 职责

```python
# src/provider/footystats/client.py

class FootyStatsProvider:
    async def get_todays_matches(
        self,
        date: Optional[str] = None,
        timezone: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        # 直接调用 FootyStats API
        return await self._request_raw("/todays-matches", params)
    
    async def get_league_list(
        self,
        chosen_leagues_only: bool = False,
        country: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        # 调用联赛列表 API
        return await self._request_raw("/league-list", params)
```

## 验证清单

在代码审查时，检查以下要点：

- [ ] Command Layer 是否只调用 DataSource 方法
- [ ] Command Layer 是否不直接调用 Provider 方法
- [ ] DataSource 是否正确调用 Provider 方法
- [ ] Provider 层是否只负责 API 调用
- [ ] **新增**：联赛 - 国家缓存在 LeagueDataSource 中
- [ ] **新增**：LeagueDataSource 在 DataSource 层
- [ ] 各层职责是否清晰分离

## 参考资料

- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [项目现有 DataSource 实现](/Users/zhengningdai/workspace/skyold/Goalcast/src/datasource/base.py)
- [项目现有 Provider 实现](/Users/zhengningdai/workspace/skyold/Goalcast/src/provider/base.py)

## 决策日期

2026-03-28

## 决策者

Goalcast Team

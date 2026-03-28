# 架构对比：联赛 - 国家缓存的实现方案

## 问题描述

如何为 `get_schedule` 功能实现联赛 - 国家映射缓存？

## 方案对比

### 方案 1：在 utils 层创建缓存工具（❌ 已废弃）

**实现位置**：`src/utils/league_cache.py`

```python
# src/utils/league_cache.py
class LeagueCountryCache:
    async def get_country(league_name: str) -> str:
        # 检查缓存
        # 调用 Provider API
        # 返回国家
```

**问题**：
1. ❌ **违反分层原则**：utils 层不应该调用 Provider
2. ❌ **职责混乱**：工具类包含业务逻辑
3. ❌ **难以测试**：需要 mock Provider 和 HTTP 请求
4. ❌ **重复代码**：每个使用缓存的地方都要初始化 Provider

**调用示例**：
```python
# cmd/get_schedule.py
league_cache = LeagueCountryCache()
country = await league_cache.get_country("Premier League")
```

---

### 方案 2：在 DataSource 层创建 LeagueDataSource（✅ 推荐）

**实现位置**：`src/datasource/league/league_datasource.py`

```python
# src/datasource/league/league_datasource.py
class LeagueDataSource(DataSource):
    async def get_country(self, league_name: str) -> str:
        # 检查缓存
        # 调用 Provider.get_league_list()
        # 返回国家
```

**优势**：
1. ✅ **符合分层架构**：DataSource 层负责业务数据
2. ✅ **职责清晰**：每个 DataSource 管理特定领域的业务数据
3. ✅ **易于测试**：可以 mock Provider
4. ✅ **复用基类功能**：继承 DataSource 的缓存、错误处理等
5. ✅ **统一接口**：所有数据都通过 DataSource 获取

**调用示例**：
```python
# cmd/get_schedule.py
league_ds = LeagueDataSource()
country = await league_ds.get_country("Premier League")
```

---

### 方案 3：在 MatchDataSource 中添加联赛方法（备选）

**实现位置**：在现有的 `MatchDataSource` 中添加方法

```python
# src/datasource/match/match_datasource.py
class MatchDataSource(DataSource):
    async def get_league_country(self, league_name: str) -> str:
        # 检查缓存
        # 调用 Provider.get_league_list()
        # 返回国家
```

**优势**：
- 简单，不需要创建新文件
- 适合只有少量联赛相关方法的场景

**问题**：
- ❌ **职责不清**：MatchDataSource 应该只管比赛数据
- ❌ **代码膨胀**：随着功能增加，类会变得臃肿
- ❌ **违反单一职责原则**：一个类管理多种数据

---

## 架构决策

### 最终选择：方案 2（LeagueDataSource）

**理由**：

1. **清晰的职责分离**
   ```
   MatchDataSource → 比赛数据
   LeagueDataSource → 联赛数据
   TeamDataSource → 球队数据
   ```

2. **符合项目现有架构**
   ```
   src/datasource/
   ├── match/
   │   └── match_datasource.py
   ├── league/          # 新增
   │   └── league_datasource.py
   ├── team/
   │   └── team_datasource.py
   └── ...
   ```

3. **易于扩展**
   - 未来可以添加更多联赛相关方法
   - 不会污染其他 DataSource
   - 可以独立测试和维护

4. **统一的调用方式**
   ```python
   # 所有数据都通过 DataSource 获取
   match_ds = MatchDataSource()
   league_ds = LeagueDataSource()
   team_ds = TeamDataSource()
   
   matches = await match_ds.fetch_for_date(...)
   country = await league_ds.get_country(...)
   team_info = await team_ds.get_team(...)
   ```

---

## 实现细节

### LeagueDataSource 结构

```python
from typing import Dict, Optional, List
from datasource.base import DataSource, DataCapability
from datasource.types import DataSourceType, League

class LeagueDataSource(DataSource[League]):
    """联赛数据源 - 管理联赛和国家数据"""
    
    def __init__(self, providers: List[BaseProvider] = None):
        super().__init__(providers)
        self._league_country_cache: Dict[str, str] = {}
        self._cache_loaded = False
    
    @property
    def data_type(self) -> DataSourceType:
        return DataSourceType.LEAGUE  # 需要在 types.py 中添加
    
    def capabilities(self) -> DataCapability:
        return DataCapability(
            type=DataSourceType.LEAGUE,
            name="联赛数据",
            description="联赛列表、国家映射等",
            providers=[p.name for p in self._providers],
            params={"league_name": "联赛名称"},
            update_freq=86400.0,  # 24 小时
            historical=True,
            realtime=False,
        )
    
    async def get_country(self, league_name: str) -> str:
        """获取联赛所属国家"""
        # 1. 检查缓存
        if league_name in self._league_country_cache:
            return self._league_country_cache[league_name]
        
        # 2. 加载联赛列表
        if not self._cache_loaded:
            await self._load_league_list()
        
        # 3. 返回结果
        return self._league_country_cache.get(league_name, "Unknown")
    
    async def _load_league_list(self):
        """从 Provider 加载联赛列表并构建缓存"""
        raw_data = await self._try_providers("get_league_list")
        if raw_data and raw_data.get("success"):
            for league in raw_data.get("data", []):
                league_name = league.get("name", "")
                country = league.get("country", "")
                if league_name and country:
                    self._league_country_cache[league_name] = country
            self._cache_loaded = True
    
    async def fetch(self, **params) -> Optional[League]:
        """获取联赛详情（可选实现）"""
        pass
```

### 在 types.py 中添加数据类型

```python
# src/datasource/types.py

class DataSourceType(Enum):
    MATCH = "match"
    TEAM = "team"
    LEAGUE = "league"  # 新增
    ODDS = "odds"
    STANDINGS = "standings"
    ELO = "elo"
    WEATHER = "weather"
    INJURY = "injury"

@dataclass
class League:
    """联赛实体"""
    league_id: str
    name: str
    country: str
    season: Optional[str] = None
    season_id: Optional[int] = None
```

---

## 性能对比

| 方案 | 首次加载 | 缓存命中 | 内存占用 | 可维护性 |
|------|---------|---------|---------|---------|
| 方案 1（utils） | 快 | 快 | 低 | 差 |
| **方案 2（DataSource）** | **中** | **快** | **中** | **优** |
| 方案 3（MatchDataSource） | 中 | 快 | 中 | 中 |

**说明**：
- 方案 2 首次加载稍慢是因为要初始化 DataSource，但这是值得的
- 所有方案缓存命中性能相同
- 方案 2 内存占用适中，因为缓存独立管理

---

## 总结

**选择方案 2（LeagueDataSource）的原因**：

1. ✅ 符合分层架构原则
2. ✅ 职责清晰，易于维护
3. ✅ 可测试性好
4. ✅ 易于扩展
5. ✅ 统一的数据访问接口

**不选择其他方案的原因**：

- 方案 1（utils）：违反分层原则，职责混乱
- 方案 3（MatchDataSource）：违反单一职责原则，代码膨胀

**实施步骤**：

1. 在 `types.py` 中添加 `League` 数据类型和 `DataSourceType.LEAGUE`
2. 创建 `src/datasource/league/league_datasource.py`
3. 实现 `LeagueDataSource` 类
4. 在 `cmd/get_schedule.py` 中使用 `LeagueDataSource`
5. 编写单元测试

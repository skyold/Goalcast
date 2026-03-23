# Goalcast Collectors 重构规范

**版本**: 1.0  
**状态**: Draft  
**创建日期**: 2026-03-22  
**参考架构**: nofx datasource/provider 模式

---

## 1. 重构目标

### 1.1 当前问题

当前 `collectors/` 目录存在以下问题：

1. **Provider 与 DataSource 耦合**：每个 collector 同时负责 HTTP 调用、缓存、解析
2. **无统一接口**：各个 collector 返回不同的 dict 结构，缺乏类型约束
3. **无 Provider 回退机制**：每个数据源只对应单一 API，失败即终止
4. **按 Provider 组织**：按 API 来源组织，而非按数据类型组织

### 1.2 重构目标

参考 nofx 架构模式，实现：

1. **Provider/DataSource 分离**：Provider 只负责 HTTP 调用，DataSource 负责缓存、解析、回退
2. **统一接口**：定义 `DataSource` 抽象基类和标准数据类型
3. **多 Provider 支持**：同一数据类型可使用多个 Provider，支持自动回退
4. **按数据类型组织**：按 Match、Team、Standings 等数据类型组织

---

## 2. 新架构设计

### 2.1 目录结构

```
src/
├── provider/                      # 原始 API 客户端层
│   ├── __init__.py
│   ├── base.py                   # Provider 基类
│   ├── footystats/
│   │   ├── __init__.py
│   │   └── client.py             # FootyStats HTTP 客户端
│   ├── football_data/
│   │   ├── __init__.py
│   │   └── client.py             # Football-Data HTTP 客户端
│   ├── understat/
│   │   ├── __init__.py
│   │   └── client.py             # Understat HTTP 客户端
│   ├── clubelo/
│   │   ├── __init__.py
│   │   └── client.py             # ClubElo HTTP 客户端
│   ├── odds/
│   │   ├── __init__.py
│   │   └── client.py             # The Odds API HTTP 客户端
│   └── weather/
│       ├── __init__.py
│       └── client.py             # OpenWeatherMap HTTP 客户端
│
├── datasource/                    # 数据抽象层
│   ├── __init__.py
│   ├── base.py                   # DataSource 基类与接口
│   ├── types.py                  # 标准数据类型定义
│   ├── registry.py               # 数据源注册管理
│   │
│   ├── match/                    # 比赛数据源
│   │   ├── __init__.py
│   │   └── match_datasource.py
│   │
│   ├── team/                     # 球队数据源
│   │   ├── __init__.py
│   │   └── team_datasource.py
│   │
│   ├── standings/                # 积分榜数据源
│   │   ├── __init__.py
│   │   └── standings_datasource.py
│   │
│   ├── odds/                     # 赔率数据源
│   │   ├── __init__.py
│   │   └── odds_datasource.py
│   │
│   ├── elo/                      # Elo 评分数据源
│   │   ├── __init__.py
│   │   └── elo_datasource.py
│   │
│   └── weather/                  # 天气数据源
│       ├── __init__.py
│       └── weather_datasource.py
│
└── collectors/                    # 保留向后兼容
    └── __init__.py               # 导出兼容接口
```

### 2.2 层级职责

| 层级 | 职责 | 示例 |
|------|------|------|
| **Provider** | 纯 HTTP 调用，返回原始 API 数据 | `FootyStatsClient.get_team()` |
| **DataSource** | 缓存、解析、多 Provider 回退、类型转换 | `TeamDataSource.fetch()` |
| **Registry** | 数据源注册、查询、生命周期管理 | `DataRegistry.get(DataSourceType.TEAM)` |

---

## 3. 核心接口定义

### 3.1 Provider 基类

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import httpx

class BaseProvider(ABC):
    """Provider 基类：只负责 HTTP 调用"""
    
    BASE_URL: str = ""
    DEFAULT_TIMEOUT: float = 10.0
    
    def __init__(self, api_key: str = "", timeout: float = None):
        self.api_key = api_key
        self.timeout = timeout or self.DEFAULT_TIMEOUT
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _request(
        self, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """执行 HTTP 请求，返回原始 JSON 数据"""
        ...
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider 名称"""
        ...
    
    @abstractmethod
    async def is_available(self) -> bool:
        """检查 Provider 是否可用"""
        ...
```

### 3.2 DataSource 基类

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, TypeVar, Generic
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class DataSourceType(Enum):
    MATCH = "match"
    TEAM = "team"
    STANDINGS = "standings"
    ODDS = "odds"
    ELO = "elo"
    WEATHER = "weather"

@dataclass
class DataCapability:
    """数据能力描述"""
    type: DataSourceType
    name: str
    description: str
    providers: List[str]
    params: Dict[str, str]
    update_freq: float  # 秒
    historical: bool
    realtime: bool

T = TypeVar('T')

class DataSource(ABC, Generic[T]):
    """DataSource 基类：负责缓存、解析、回退"""
    
    def __init__(self, providers: List['BaseProvider'] = None):
        self._providers = providers or []
        self._cache: Dict[str, Any] = {}
        self._cache_ttl: float = 30.0
    
    @property
    @abstractmethod
    def data_type(self) -> DataSourceType:
        """数据类型"""
        ...
    
    @abstractmethod
    def capabilities(self) -> DataCapability:
        """数据能力描述"""
        ...
    
    @abstractmethod
    async def fetch(self, **params) -> Optional[T]:
        """获取数据（带缓存和回退）"""
        ...
    
    @abstractmethod
    def parse(self, raw_data: Dict[str, Any]) -> T:
        """解析原始数据为标准类型"""
        ...
    
    async def is_available(self) -> bool:
        """检查是否有可用的 Provider"""
        for provider in self._providers:
            if await provider.is_available():
                return True
        return False
    
    def _cache_key(self, **params) -> str:
        """生成缓存键"""
        return ":".join(f"{k}={v}" for k, v in sorted(params.items()))
```

### 3.3 标准数据类型

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from enum import Enum

class MatchType(Enum):
    LEAGUE = "A"       # 联赛常规
    CUP = "B"          # 杯赛单场
    TWO_LEG = "C"      # 双回合
    CRUCIAL = "D"      # 关键联赛

class MatchStatus(Enum):
    SCHEDULED = "SCHEDULED"
    LIVE = "LIVE"
    FINISHED = "FINISHED"
    POSTPONED = "POSTPONED"
    CANCELLED = "CANCELLED"

@dataclass
class Match:
    """比赛数据"""
    match_id: str
    home_team: str
    away_team: str
    home_team_id: Optional[str] = None
    away_team_id: Optional[str] = None
    competition: str = ""
    match_type: MatchType = MatchType.LEAGUE
    status: MatchStatus = MatchStatus.SCHEDULED
    kickoff_time: Optional[datetime] = None
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    odds_home: Optional[float] = None
    odds_draw: Optional[float] = None
    odds_away: Optional[float] = None

@dataclass
class Team:
    """球队数据"""
    team_id: str
    name: str
    short_name: Optional[str] = None
    
    # xG 数据
    xg_home: Optional[float] = None
    xg_away: Optional[float] = None
    xga_home: Optional[float] = None
    xga_away: Optional[float] = None
    
    # 赛季统计
    ppg: Optional[float] = None
    position: Optional[int] = None
    played: Optional[int] = None
    won: Optional[int] = None
    drawn: Optional[int] = None
    lost: Optional[int] = None
    goals_for: Optional[int] = None
    goals_against: Optional[int] = None
    
    # 近期状态
    recent_form: List[str] = field(default_factory=list)
    recent_xg: Optional[float] = None
    recent_xga: Optional[float] = None
    
    # 节奏数据
    possession: Optional[float] = None
    ppda: Optional[float] = None
    
    # Elo
    elo: Optional[float] = None
    
    # 伤病
    injuries: List[str] = field(default_factory=list)

@dataclass
class StandingsEntry:
    """积分榜条目"""
    position: int
    team_id: str
    team_name: str
    played: int
    won: int
    drawn: int
    lost: int
    goals_for: int
    goals_against: int
    goal_difference: int
    points: int
    ppg: Optional[float] = None

@dataclass
class Odds:
    """赔率数据"""
    home: float
    draw: float
    away: float
    bookmaker: str = ""
    timestamp: Optional[datetime] = None
    
    # 隐含概率
    home_prob: Optional[float] = None
    draw_prob: Optional[float] = None
    away_prob: Optional[float] = None

@dataclass
class Elo:
    """Elo 评分数据"""
    team_name: str
    elo: float
    date: Optional[datetime] = None
    rank: Optional[int] = None

@dataclass
class Weather:
    """天气数据"""
    condition: str
    wind_speed: float
    rain_1h: float
    temperature: Optional[float] = None
    xg_adjustment: float = 0.0
```

### 3.4 数据源注册表

```python
from typing import Dict, List, Optional, Type
from .base import DataSource, DataSourceType

class DataRegistry:
    """数据源注册表"""
    
    _instance: Optional['DataRegistry'] = None
    
    def __new__(cls) -> 'DataRegistry':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._data_sources: Dict[DataSourceType, List[DataSource]] = {}
        return cls._instance
    
    def register(self, datasource: DataSource) -> None:
        """注册数据源"""
        dtype = datasource.data_type
        if dtype not in self._data_sources:
            self._data_sources[dtype] = []
        self._data_sources[dtype].append(datasource)
    
    def get(self, dtype: DataSourceType) -> Optional[DataSource]:
        """获取指定类型的数据源（返回第一个可用的）"""
        sources = self._data_sources.get(dtype, [])
        return sources[0] if sources else None
    
    def get_all(self, dtype: DataSourceType) -> List[DataSource]:
        """获取指定类型的所有数据源"""
        return self._data_sources.get(dtype, [])
    
    def capabilities(self) -> Dict[DataSourceType, 'DataCapability']:
        """获取所有数据源的能力描述"""
        return {
            dtype: sources[0].capabilities()
            for dtype, sources in self._data_sources.items()
            if sources
        }

# 全局注册表实例
registry = DataRegistry()
```

---

## 4. Provider 实现规范

### 4.1 FootyStats Provider

```python
# src/provider/footystats/client.py

from typing import Dict, Any, Optional
from provider.base import BaseProvider

class FootyStatsProvider(BaseProvider):
    """FootyStats API Provider"""
    
    BASE_URL = "https://api.football-data-api.com"
    DEFAULT_TIMEOUT = 10.0
    
    @property
    def name(self) -> str:
        return "footystats"
    
    async def is_available(self) -> bool:
        return bool(self.api_key)
    
    async def get_team(self, team_id: str) -> Optional[Dict[str, Any]]:
        """获取球队数据（原始 JSON）"""
        return await self._request("/team", {"team_id": team_id})
    
    async def get_match(self, match_id: str) -> Optional[Dict[str, Any]]:
        """获取比赛数据（原始 JSON）"""
        return await self._request("/match", {"match_id": match_id})
    
    async def get_league_matches(
        self, 
        league_id: str, 
        date: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """获取联赛比赛列表（原始 JSON）"""
        params = {"league_id": league_id}
        if date:
            params["date"] = date
        return await self._request("/league-matches", params)
    
    async def get_league_table(
        self, 
        league_id: str,
        season_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """获取积分榜（原始 JSON）"""
        params = {"league_id": league_id}
        if season_id:
            params["season_id"] = season_id
        return await self._request("/league-tables", params)
```

### 4.2 Football-Data Provider

```python
# src/provider/football_data/client.py

from typing import Dict, Any, Optional, List
from provider.base import BaseProvider

COMPETITION_IDS = {
    "Premier League": "PL",
    "La Liga": "PD",
    "Serie A": "SA",
    "Bundesliga": "BL1",
    "Ligue 1": "FL1",
    "Champions League": "CL",
    "Europa League": "EL",
}

class FootballDataProvider(BaseProvider):
    """Football-Data API Provider"""
    
    BASE_URL = "https://api.football-data.org/v4"
    DEFAULT_TIMEOUT = 10.0
    
    @property
    def name(self) -> str:
        return "football_data"
    
    async def is_available(self) -> bool:
        return bool(self.api_key)
    
    async def get_matches(
        self,
        competition: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """获取比赛列表（原始 JSON）"""
        comp_id = COMPETITION_IDS.get(competition, competition)
        params = {}
        if date_from:
            params["dateFrom"] = date_from
        if date_to:
            params["dateTo"] = date_to
        return await self._request(f"/competitions/{comp_id}/matches", params)
    
    async def get_standings(self, competition: str) -> Optional[Dict[str, Any]]:
        """获取积分榜（原始 JSON）"""
        comp_id = COMPETITION_IDS.get(competition, competition)
        return await self._request(f"/competitions/{comp_id}/standings")
    
    async def get_team(self, team_id: int) -> Optional[Dict[str, Any]]:
        """获取球队数据（原始 JSON）"""
        return await self._request(f"/teams/{team_id}")
```

---

## 5. DataSource 实现规范

### 5.1 Match DataSource

```python
# src/datasource/match/match_datasource.py

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from datasource.base import DataSource, DataCapability, DataSourceType
from datasource.types import Match, MatchType, MatchStatus
from provider.base import BaseProvider

class MatchDataSource(DataSource[Match]):
    """比赛数据源：支持多 Provider 回退"""
    
    def __init__(self, providers: List[BaseProvider] = None):
        super().__init__(providers)
        self._cache_ttl = 30.0  # 30 秒缓存
    
    @property
    def data_type(self) -> DataSourceType:
        return DataSourceType.MATCH
    
    def capabilities(self) -> DataCapability:
        return DataCapability(
            type=DataSourceType.MATCH,
            name="比赛数据",
            description="比赛信息、比分、状态、赔率等",
            providers=[p.name for p in self._providers],
            params={
                "match_id": "比赛 ID",
                "competition": "联赛名称",
                "date_from": "开始日期 (YYYY-MM-DD)",
                "date_to": "结束日期 (YYYY-MM-DD)",
            },
            update_freq=10.0,
            historical=True,
            realtime=True,
        )
    
    async def fetch(self, **params) -> Optional[Match]:
        """获取单场比赛数据"""
        match_id = params.get("match_id")
        if not match_id:
            return None
        
        cache_key = self._cache_key(**params)
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if datetime.now() - cached["time"] < timedelta(seconds=self._cache_ttl):
                return cached["data"]
        
        # 尝试各个 Provider
        for provider in self._providers:
            try:
                raw_data = await provider.get_match(match_id)
                if raw_data:
                    match = self.parse(raw_data)
                    self._cache[cache_key] = {
                        "data": match,
                        "time": datetime.now(),
                    }
                    return match
            except Exception as e:
                continue
        
        return None
    
    async def fetch_upcoming(
        self, 
        competition: str, 
        days: int = 7
    ) -> List[Match]:
        """获取即将进行的比赛"""
        today = datetime.now()
        date_from = today.strftime("%Y-%m-%d")
        date_to = (today + timedelta(days=days)).strftime("%Y-%m-%d")
        
        for provider in self._providers:
            try:
                raw_data = await provider.get_matches(
                    competition, date_from, date_to
                )
                if raw_data:
                    return self.parse_list(raw_data)
            except Exception:
                continue
        
        return []
    
    def parse(self, raw_data: Dict[str, Any]) -> Match:
        """解析原始数据为 Match 类型"""
        # 根据数据源类型选择解析方法
        ...
    
    def parse_list(self, raw_data: Dict[str, Any]) -> List[Match]:
        """解析比赛列表"""
        ...
```

### 5.2 Team DataSource

```python
# src/datasource/team/team_datasource.py

from typing import Optional, List, Dict, Any
from datasource.base import DataSource, DataCapability, DataSourceType
from datasource.types import Team
from provider.base import BaseProvider

class TeamDataSource(DataSource[Team]):
    """球队数据源：支持多 Provider 回退"""
    
    def __init__(self, providers: List[BaseProvider] = None):
        super().__init__(providers)
        self._cache_ttl = 3600.0  # 1 小时缓存
    
    @property
    def data_type(self) -> DataSourceType:
        return DataSourceType.TEAM
    
    def capabilities(self) -> DataCapability:
        return DataCapability(
            type=DataSourceType.TEAM,
            name="球队数据",
            description="球队统计、xG/xGA、近期状态等",
            providers=[p.name for p in self._providers],
            params={
                "team_id": "球队 ID",
                "team_name": "球队名称",
            },
            update_freq=3600.0,
            historical=True,
            realtime=False,
        )
    
    async def fetch(self, **params) -> Optional[Team]:
        """获取球队数据"""
        team_id = params.get("team_id")
        if not team_id:
            return None
        
        cache_key = self._cache_key(**params)
        # ... 缓存逻辑
        
        # 尝试各个 Provider
        for provider in self._providers:
            try:
                raw_data = await provider.get_team(team_id)
                if raw_data:
                    return self.parse(raw_data)
            except Exception:
                continue
        
        return None
    
    def parse(self, raw_data: Dict[str, Any]) -> Team:
        """解析原始数据为 Team 类型"""
        ...
```

---

## 6. 向后兼容

### 6.1 collectors/__init__.py

```python
# src/collectors/__init__.py
"""
向后兼容层：保持原有导入路径可用

新代码应使用:
  from datasource import MatchDataSource, TeamDataSource
  from provider import FootyStatsProvider, FootballDataProvider
"""

# 导入新的 DataSource
from datasource.match import MatchDataSource
from datasource.team import TeamDataSource
from datasource.standings import StandingsDataSource
from datasource.odds import OddsDataSource
from datasource.elo import EloDataSource
from datasource.weather import WeatherDataSource

# 导入新的 Provider
from provider.footystats import FootyStatsProvider
from provider.football_data import FootballDataProvider
from provider.understat import UnderstatProvider
from provider.clubelo import ClubEloProvider
from provider.odds import OddsProvider
from provider.weather import WeatherProvider

# 兼容旧名称
FootyStatsClient = FootyStatsProvider
FootballDataClient = FootballDataProvider
UnderstatClient = UnderstatProvider
ClubEloClient = ClubEloProvider
OddsAPIClient = OddsProvider
WeatherClient = WeatherProvider

__all__ = [
    # 新名称
    "MatchDataSource",
    "TeamDataSource",
    "StandingsDataSource",
    "OddsDataSource",
    "EloDataSource",
    "WeatherDataSource",
    "FootyStatsProvider",
    "FootballDataProvider",
    "UnderstatProvider",
    "ClubEloProvider",
    "OddsProvider",
    "WeatherProvider",
    # 兼容旧名称
    "FootyStatsClient",
    "FootballDataClient",
    "UnderstatClient",
    "ClubEloClient",
    "OddsAPIClient",
    "WeatherClient",
]
```

---

## 7. 数据源映射

### 7.1 当前 Collector → 新架构映射

| 当前 Collector | 新 Provider | 新 DataSource |
|----------------|-------------|---------------|
| `footystats.py` | `provider/footystats/client.py` | `datasource/match/`, `datasource/team/`, `datasource/standings/` |
| `football_data.py` | `provider/football_data/client.py` | `datasource/match/`, `datasource/standings/` |
| `understat.py` | `provider/understat/client.py` | `datasource/team/` (xG/PPDA) |
| `clubelo.py` | `provider/clubelo/client.py` | `datasource/elo/` |
| `odds_api.py` | `provider/odds/client.py` | `datasource/odds/` |
| `weather.py` | `provider/weather/client.py` | `datasource/weather/` |

### 7.2 数据类型与 Provider 对应

| 数据类型 | 可用 Provider | 优先级 |
|----------|---------------|--------|
| **Match** | footystats, football_data | footystats 优先 |
| **Team** | footystats, understat | footystats 为主，understat 补充 xG |
| **Standings** | footystats, football_data | footystats 优先 |
| **Odds** | odds_api | 唯一 |
| **Elo** | clubelo | 唯一 |
| **Weather** | weather | 唯一 |

---

## 8. 测试策略

### 8.1 Provider 测试

```python
# tests/test_provider/test_footystats.py

import pytest
from provider.footystats import FootyStatsProvider

@pytest.fixture
def provider():
    return FootyStatsProvider(api_key="test_key")

class TestFootyStatsProvider:
    async def test_get_team(self, provider, httpx_mock):
        httpx_mock.add_response(json={"data": {"team_id": "123"}})
        result = await provider.get_team("123")
        assert result is not None
        assert result["data"]["team_id"] == "123"
    
    async def test_is_available(self, provider):
        assert await provider.is_available() is True
```

### 8.2 DataSource 测试

```python
# tests/test_datasource/test_match.py

import pytest
from datasource.match import MatchDataSource
from datasource.types import Match
from provider.footystats import FootyStatsProvider
from provider.football_data import FootballDataProvider

@pytest.fixture
def match_datasource():
    providers = [
        FootyStatsProvider(api_key="test"),
        FootballDataProvider(api_key="test"),
    ]
    return MatchDataSource(providers)

class TestMatchDataSource:
    async def test_fetch_returns_match(self, match_datasource, httpx_mock):
        httpx_mock.add_response(json={"data": {"match_id": "123", ...}})
        result = await match_datasource.fetch(match_id="123")
        assert isinstance(result, Match)
    
    async def test_fallback_to_second_provider(self, match_datasource, httpx_mock):
        # 第一个 Provider 失败
        httpx_mock.add_response(status_code=500)
        # 第二个 Provider 成功
        httpx_mock.add_response(json={"matches": [...]})
        
        result = await match_datasource.fetch(match_id="123")
        assert result is not None
```

---

## 9. 迁移步骤

### Phase 1: 基础设施 (Day 1-2)

1. 创建 `provider/` 目录和基类
2. 创建 `datasource/` 目录和基类
3. 定义 `types.py` 标准数据类型
4. 实现 `registry.py` 注册表

### Phase 2: Provider 迁移 (Day 3-5)

1. 迁移 `footystats.py` → `provider/footystats/`
2. 迁移 `football_data.py` → `provider/football_data/`
3. 迁移 `understat.py` → `provider/understat/`
4. 迁移 `clubelo.py` → `provider/clubelo/`
5. 迁移 `odds_api.py` → `provider/odds/`
6. 迁移 `weather.py` → `provider/weather/`

### Phase 3: DataSource 实现 (Day 6-8)

1. 实现 `MatchDataSource`
2. 实现 `TeamDataSource`
3. 实现 `StandingsDataSource`
4. 实现 `OddsDataSource`
5. 实现 `EloDataSource`
6. 实现 `WeatherDataSource`

### Phase 4: 集成与测试 (Day 9-10)

1. 更新 `match_builder.py` 使用新接口
2. 添加向后兼容层
3. 编写单元测试
4. 编写集成测试
5. 更新文档

---

## 10. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 破坏现有功能 | 高 | 保持向后兼容层，渐进迁移 |
| 性能下降 | 中 | 优化缓存策略，异步并发 |
| API 响应格式变化 | 中 | Provider 层隔离变化，DataSource 层适配 |
| 测试覆盖不足 | 中 | 每个 Provider 和 DataSource 都有测试 |

---

*Goalcast Collectors Refactoring Spec v1.0*

# Goalcast AI — 架构文档 v2.0

> **最后更新**: 2026-03-22
> **版本**: Phase 2 完成 - Provider/DataSource 架构重构

---

## 1. 系统架构概览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Goalcast AI 系统架构                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │
│  │   CLI 入口   │    │  调度器      │    │  手动输入    │    │  API 服务   │ │
│  │ analyze_    │    │ scheduler.  │    │  manual_    │    │  (未来)     │ │
│  │ match.py    │    │ py          │    │  input.py   │    │             │ │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘    └─────────────┘ │
│         │                  │                  │                           │
│         └──────────────────┼──────────────────┘                           │
│                            ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      数据聚合层 (Aggregator)                         │   │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐              │   │
│  │  │ MatchBuilder│───▶│  Schema     │───▶│AnalysisInput│              │   │
│  │  │             │    │  (Pydantic) │    │             │              │   │
│  │  └──────┬──────┘    └─────────────┘    └─────────────┘              │   │
│  └─────────┼───────────────────────────────────────────────────────────┘   │
│            ▼                                                                │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    DataSource 层 (数据源管理)                         │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │   │
│  │  │  Match   │ │   Team   │ │Standings │ │  Odds    │ │   Elo    │  │   │
│  │  │DataSource│ │DataSource│ │DataSource│ │DataSource│ │DataSource│  │   │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘  │   │
│  │       │            │            │            │            │         │   │
│  │  ┌────┴────────────┴────────────┴────────────┴────────────┴────┐    │   │
│  │  │                     DataRegistry (单例)                     │    │   │
│  │  └─────────────────────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│            ▼                                                                │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      Provider 层 (API 客户端)                        │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │   │
│  │  │FootyStats│ │Football- │ │Understat │ │ ClubElo  │ │ Odds API │  │   │
│  │  │ Provider │ │  Data    │ │ Provider │ │ Provider │ │ Provider │  │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │   │
│  │  ┌──────────┐                                                        │   │
│  │  │ Weather  │                                                        │   │
│  │  │ Provider │                                                        │   │
│  │  └──────────┘                                                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│            ▼                                                                │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      分析引擎层 (Engine)                             │   │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐              │   │
│  │  │PromptBuilder│───▶│ Claude API  │───▶│OutputParser │              │   │
│  │  │             │    │   Runner    │    │             │              │   │
│  │  └─────────────┘    └─────────────┘    └─────────────┘              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│            ▼                                                                │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      存储层 (Storage)                                │   │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐              │   │
│  │  │  SQLite DB  │    │ JSON Cache  │    │ JSON Export │              │   │
│  │  │  (分析记录)  │    │ (API缓存)   │    │ (输出文件)  │              │   │
│  │  └─────────────┘    └─────────────┘    └─────────────┘              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 数据采集层架构

### 2.1 架构设计理念

数据采集层采用 **Provider/DataSource 分层架构**，遵循单一职责原则：

| 层级 | 职责 | 特点 |
|------|------|------|
| **Provider** | 仅负责 HTTP 调用，返回原始 JSON | 无状态、可替换、轻量级 |
| **DataSource** | 缓存、解析、多源回退、类型转换 | 有状态、智能、业务感知 |
| **Registry** | 数据源注册与发现 | 单例模式、全局管理 |

### 2.2 目录结构

```
src/
├── provider/                      # Provider 层 - API 客户端
│   ├── __init__.py
│   ├── base.py                    # BaseProvider 抽象基类
│   ├── footystats/
│   │   ├── __init__.py
│   │   └── client.py              # FootyStatsProvider
│   ├── football_data/
│   │   ├── __init__.py
│   │   └── client.py              # FootballDataProvider
│   ├── understat/
│   │   ├── __init__.py
│   │   └── client.py              # UnderstatProvider
│   ├── clubelo/
│   │   ├── __init__.py
│   │   └── client.py              # ClubEloProvider
│   ├── odds/
│   │   ├── __init__.py
│   │   └── client.py              # OddsProvider
│   └── weather/
│       ├── __init__.py
│       └── client.py              # WeatherProvider
│
├── datasource/                    # DataSource 层 - 数据源管理
│   ├── __init__.py
│   ├── base.py                    # DataSource 泛型基类
│   ├── types.py                   # 标准数据类型定义
│   ├── registry.py                # DataRegistry 单例
│   ├── match/
│   │   ├── __init__.py
│   │   └── match_datasource.py    # MatchDataSource
│   ├── team/
│   │   ├── __init__.py
│   │   └── team_datasource.py     # TeamDataSource
│   ├── standings/
│   │   ├── __init__.py
│   │   └── standings_datasource.py
│   ├── odds/
│   │   ├── __init__.py
│   │   └── odds_datasource.py
│   ├── elo/
│   │   ├── __init__.py
│   │   └── elo_datasource.py
│   └── weather/
│       ├── __init__.py
│       └── weather_datasource.py
│
└── collectors/                    # 向后兼容层
    └── __init__.py                # 导出别名
```

---

## 3. Provider 层

### 3.1 BaseProvider 抽象基类

**文件**: [base.py](file:///Users/zhengningdai/workspace/skyold/Goalcast/src/provider/base.py)

```python
class BaseProvider(ABC):
    BASE_URL: str = ""
    DEFAULT_TIMEOUT: float = 10.0
    MAX_RETRIES: int = 3
    RETRY_DELAY: float = 1.0

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider 唯一标识"""
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """检查 Provider 是否可用"""
        pass
```

#### 核心特性

| 特性 | 说明 |
|------|------|
| **异步 HTTP** | 使用 `httpx.AsyncClient` |
| **自动重试** | 指数退避，最多 3 次 |
| **速率限制处理** | 自动识别 429 状态码，等待 Retry-After |
| **错误隔离** | 单个 Provider 失败不影响其他 Provider |

### 3.2 Provider 列表

| Provider | 类名 | 数据源 | 成本 |
|----------|------|--------|------|
| FootyStatsProvider | `FootyStatsProvider` | footystats | £29.99/月 |
| FootballDataProvider | `FootballDataProvider` | football-data.org | 免费/付费 |
| UnderstatProvider | `UnderstatProvider` | understat | 免费 |
| ClubEloProvider | `ClubEloProvider` | clubelo | 免费 |
| OddsProvider | `OddsProvider` | The Odds API | 500次/月免费 |
| WeatherProvider | `WeatherProvider` | OpenWeatherMap | 免费 |

### 3.3 FootyStatsProvider 示例

**文件**: [provider/footystats/client.py](file:///Users/zhengningdai/workspace/skyold/Goalcast/src/provider/footystats/client.py)

```python
class FootyStatsProvider(BaseProvider):
    BASE_URL = "https://api.football-data-api.com"
    
    @property
    def name(self) -> str:
        return "footystats"

    async def is_available(self) -> bool:
        return bool(self.api_key)

    async def get_team(self, team_id: str) -> Optional[Dict[str, Any]]:
        return await self._request_raw("/team", {"team_id": team_id})

    async def get_match(self, match_id: str) -> Optional[Dict[str, Any]]:
        return await self._request_raw("/match", {"match_id": match_id})

    async def get_league_matches(self, league_id: str, date: Optional[str] = None):
        params = {"league_id": league_id}
        if date:
            params["date"] = date
        return await self._request_raw("/league-matches", params)

    async def get_league_table(self, league_id: str, season_id: Optional[str] = None):
        params = {"league_id": league_id}
        if season_id:
            params["season_id"] = season_id
        return await self._request_raw("/league-tables", params)
```

---

## 4. DataSource 层

### 4.1 DataSource 泛型基类

**文件**: [datasource/base.py](file:///Users/zhengningdai/workspace/skyold/Goalcast/src/datasource/base.py)

```python
class DataSource(ABC, Generic[T]):
    def __init__(self, providers: List[BaseProvider] = None):
        self._providers: List[BaseProvider] = providers or []
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl: float = 30.0

    @property
    @abstractmethod
    def data_type(self) -> DataSourceType:
        """数据类型标识"""
        pass

    @abstractmethod
    async def fetch(self, **params) -> Optional[T]:
        """获取数据"""
        pass

    @abstractmethod
    def parse(self, raw_data: Dict[str, Any]) -> T:
        """解析原始数据为标准类型"""
        pass

    async def _try_providers(self, method_name: str, **kwargs) -> Optional[Dict]:
        """按顺序尝试所有 Provider，返回第一个成功结果"""
        ...
```

#### 核心特性

| 特性 | 说明 |
|------|------|
| **泛型支持** | `DataSource[T]` 返回类型安全的数据 |
| **多源回退** | 自动尝试多个 Provider 直到成功 |
| **内存缓存** | 基于 TTL 的简单缓存 |
| **能力声明** | `capabilities()` 方法描述数据能力 |

### 4.2 DataSource 列表

| DataSource | 数据类型 | 支持的 Provider |
|------------|----------|-----------------|
| MatchDataSource | MATCH | FootyStats, Football-Data |
| TeamDataSource | TEAM | FootyStats, Understat |
| StandingsDataSource | STANDINGS | FootyStats |
| OddsDataSource | ODDS | Odds API |
| EloDataSource | ELO | ClubElo |
| WeatherDataSource | WEATHER | OpenWeatherMap |

### 4.3 MatchDataSource 示例

**文件**: [datasource/match/match_datasource.py](file:///Users/zhengningdai/workspace/skyold/Goalcast/src/datasource/match/match_datasource.py)

```python
class MatchDataSource(DataSource[Match]):
    @property
    def data_type(self) -> DataSourceType:
        return DataSourceType.MATCH

    async def fetch(self, **params) -> Optional[Match]:
        match_id = params.get("match_id")
        if not match_id:
            return None

        cache_key = self._cache_key(**params)
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        raw_data = await self._try_providers("get_match", match_id=match_id)
        if raw_data is None:
            return None

        match = self.parse(raw_data)
        if match:
            self._set_cache(cache_key, match)
        return match

    def parse(self, raw_data: Dict[str, Any]) -> Optional[Match]:
        data = raw_data.get("data", raw_data)
        return Match(
            match_id=str(data.get("match_id") or data.get("id", "")),
            home_team=data.get("home_name") or data.get("homeTeam", {}).get("name", ""),
            away_team=data.get("away_name") or data.get("awayTeam", {}).get("name", ""),
            ...
        )
```

---

## 5. 标准数据类型

**文件**: [datasource/types.py](file:///Users/zhengningdai/workspace/skyold/Goalcast/src/datasource/types.py)

### 5.1 数据类型枚举

```python
class DataSourceType(Enum):
    MATCH = "match"
    TEAM = "team"
    STANDINGS = "standings"
    ODDS = "odds"
    ELO = "elo"
    WEATHER = "weather"
```

### 5.2 核心数据类

#### Match - 比赛数据

```python
@dataclass
class Match:
    match_id: str
    home_team: str
    away_team: str
    home_team_id: Optional[str] = None
    away_team_id: Optional[str] = None
    competition: str = ""
    competition_id: Optional[str] = None
    match_type: MatchType = MatchType.LEAGUE
    status: MatchStatus = MatchStatus.SCHEDULED
    kickoff_time: Optional[datetime] = None
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    odds_home: Optional[float] = None
    odds_draw: Optional[float] = None
    odds_away: Optional[float] = None
    venue: Optional[str] = None
    referee: Optional[str] = None
```

#### Team - 球队数据

```python
@dataclass
class Team:
    team_id: str
    name: str
    short_name: Optional[str] = None
    
    xg_home: Optional[float] = None
    xg_away: Optional[float] = None
    xga_home: Optional[float] = None
    xga_away: Optional[float] = None
    
    ppg: Optional[float] = None
    position: Optional[int] = None
    played: Optional[int] = None
    won: Optional[int] = None
    drawn: Optional[int] = None
    lost: Optional[int] = None
    goals_for: Optional[int] = None
    goals_against: Optional[int] = None
    
    recent_form: List[str] = field(default_factory=list)
    possession: Optional[float] = None
    ppda: Optional[float] = None
    elo: Optional[float] = None
    injuries: List[str] = field(default_factory=list)
```

#### StandingsEntry - 积分榜

```python
@dataclass
class StandingsEntry:
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
    form: List[str] = field(default_factory=list)
    competition: Optional[str] = None
```

#### Odds - 赔率数据

```python
@dataclass
class Odds:
    home: float
    draw: float
    away: float
    bookmaker: str = ""
    timestamp: Optional[datetime] = None
    
    home_prob: Optional[float] = None
    draw_prob: Optional[float] = None
    away_prob: Optional[float] = None
    
    def calculate_implied_probabilities(self):
        """计算隐含概率并去除抽水"""
        total = 1 / self.home + 1 / self.draw + 1 / self.away
        self.home_prob = (1 / self.home) / total
        self.draw_prob = (1 / self.draw) / total
        self.away_prob = (1 / self.away) / total
```

#### Elo - Elo 评分

```python
@dataclass
class Elo:
    team_name: str
    elo: float
    date: Optional[datetime] = None
    rank: Optional[int] = None
    country: Optional[str] = None
    level: Optional[float] = None
```

#### Weather - 天气数据

```python
@dataclass
class Weather:
    condition: str
    wind_speed: float
    rain_1h: float
    temperature: Optional[float] = None
    humidity: Optional[int] = None
    xg_adjustment: float = 0.0

    def calculate_xg_adjustment(self) -> float:
        """计算天气对 xG 的调整量"""
        adjustment = 0.0
        if self.wind_speed > 8:
            adjustment -= 0.10
        if self.rain_1h > 5:
            adjustment -= 0.10
        if self.condition.lower() in ["snow", "fog", "mist"]:
            adjustment -= 0.10
        self.xg_adjustment = adjustment
        return adjustment
```

---

## 6. DataRegistry 数据注册中心

**文件**: [datasource/registry.py](file:///Users/zhengningdai/workspace/skyold/Goalcast/src/datasource/registry.py)

### 6.1 设计模式

DataRegistry 采用 **单例模式**，提供全局的数据源注册与发现机制。

```python
class DataRegistry:
    _instance: Optional['DataRegistry'] = None
    
    def __new__(cls) -> 'DataRegistry':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._data_sources: Dict[DataSourceType, List[DataSource]] = {}
        return cls._instance

    def register(self, datasource: DataSource) -> None:
        """注册数据源"""
        ...

    def get(self, dtype: DataSourceType) -> Optional[DataSource]:
        """获取指定类型的数据源"""
        ...

    def get_all(self, dtype: DataSourceType) -> List[DataSource]:
        """获取指定类型的所有数据源"""
        ...

    def capabilities(self) -> Dict[DataSourceType, DataCapability]:
        """获取所有数据源的能力描述"""
        ...
```

### 6.2 使用示例

```python
from datasource import registry, MatchDataSource, TeamDataSource
from datasource.types import DataSourceType
from provider import FootyStatsProvider, FootballDataProvider

footystats = FootyStatsProvider(api_key="...")
football_data = FootballDataProvider(api_key="...")

match_ds = MatchDataSource(providers=[footystats, football_data])
team_ds = TeamDataSource(providers=[footystats])

registry.register(match_ds)
registry.register(team_ds)

match = await registry.get(DataSourceType.MATCH).fetch(match_id="12345")
```

---

## 7. 向后兼容

**文件**: [collectors/__init__.py](file:///Users/zhengningdai/workspace/skyold/Goalcast/src/collectors/__init__.py)

为保持向后兼容，`collectors` 模块导出所有别名：

```python
from provider import (
    FootyStatsProvider, FootballDataProvider, UnderstatProvider,
    ClubEloProvider, OddsProvider, WeatherProvider,
    FootyStatsClient, FootballDataClient, UnderstatClient,
    ClubEloClient, OddsAPIClient, WeatherClient,
)
from datasource import (
    MatchDataSource, TeamDataSource, StandingsDataSource,
    OddsDataSource, EloDataSource, WeatherDataSource, registry,
)
```

---

## 8. 数据流完整示例

```
用户输入: match_id = "12345"
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ MatchBuilder.build("12345")                                 │
├─────────────────────────────────────────────────────────────┤
│ 1. registry.get(DataSourceType.MATCH).fetch("12345")        │
│    │                                                        │
│    ├── MatchDataSource._try_providers("get_match")          │
│    │   ├── FootyStatsProvider.get_match("12345")            │
│    │   │   └── 返回原始 JSON                                 │
│    │   └── (如果失败) FootballDataProvider.get_match(...)   │
│    │                                                        │
│    └── MatchDataSource.parse(raw_data) → Match              │
│                                                             │
│ 2. 并发获取:                                                 │
│    • TeamDataSource.fetch(home_id) → Team                   │
│    • TeamDataSource.fetch(away_id) → Team                   │
│    • EloDataSource.fetch(home_team) → Elo                   │
│    • EloDataSource.fetch(away_team) → Elo                   │
│    • OddsDataSource.fetch(match_id) → Odds                  │
│    • WeatherDataSource.fetch(venue) → Weather               │
│                                                             │
│ 3. 数据质量评估                                              │
│ 4. 构建AnalysisInput                                        │
└─────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ PromptBuilder.build(AnalysisInput)                          │
│ → 生成完整提示词                                             │
└─────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ AnalysisRunner.run(prompt)                                  │
│ → 调用Claude API                                            │
│ → 返回原始响应                                               │
└─────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ OutputParser.parse(response)                                │
│ → 提取JSON                                                  │
│ → 校验修复                                                  │
│ → 构建AnalysisOutput                                        │
└─────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ 输出                                                        │
│ • 终端显示 (OutputFormatter)                                 │
│ • JSON文件 (data/exports/)                                  │
│ • 数据库存储 (Repository)                                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 9. 数据源详细说明

### 9.1 数据源总览

| 数据源 | Provider 类 | 成本 | 主要用途 | 覆盖范围 |
|--------|-------------|------|----------|----------|
| **FootyStats** | FootyStatsProvider | £29.99/月 | 核心数据源 | 60+ 联赛 |
| **Football-Data.org** | FootballDataProvider | 免费/付费 | 比赛数据 | 主要联赛 |
| **ClubElo** | ClubEloProvider | 免费 | Elo 评分 | 全球俱乐部 |
| **Understat** | UnderstatProvider | 免费 | xG/PPDA 明细 | 五大联赛 |
| **The Odds API** | OddsProvider | 500次/月免费 | 赔率数据 | 全球赛事 |
| **OpenWeatherMap** | WeatherProvider | 免费 | 天气数据 | 全球 |

### 9.2 各 Provider 可用方法

#### FootyStatsProvider

| 方法 | 返回数据 | 说明 |
|------|----------|------|
| `get_team(team_id)` | 原始 JSON | 球队赛季统计 |
| `get_match(match_id)` | 原始 JSON | 单场比赛详情 |
| `get_league_matches(league_id, date)` | 原始 JSON | 联赛比赛列表 |
| `get_league_table(league_id, season_id)` | 原始 JSON | 联赛积分榜 |

#### FootballDataProvider

| 方法 | 返回数据 | 说明 |
|------|----------|------|
| `get_match(match_id)` | 原始 JSON | 单场比赛详情 |
| `get_matches(competition, date_from, date_to)` | 原始 JSON | 比赛列表 |
| `get_standings(competition)` | 原始 JSON | 积分榜 |

#### ClubEloProvider

| 方法 | 返回数据 | 说明 |
|------|----------|------|
| `get_elo(team_name, date)` | 原始 JSON | 球队 Elo 评分 |

#### OddsProvider

| 方法 | 返回数据 | 说明 |
|------|----------|------|
| `get_odds(sport, match_id, regions, markets)` | 原始 JSON | 赔率数据 |

#### WeatherProvider

| 方法 | 返回数据 | 说明 |
|------|----------|------|
| `get_weather(lat, lon)` | 原始 JSON | 天气数据 |

---

## 10. 配置文件

| 文件 | 用途 |
|------|------|
| `config/settings.py` | 全局配置 (API密钥、联赛参数、EV阈值) |
| `config/team_name_map.json` | ClubElo 球队名称映射 |
| `config/stadiums.json` | 球场 GPS 坐标 |
| `config/odds_sport_keys.json` | The Odds API 联赛 key |
| `config/understat_leagues.json` | Understat 联赛名称映射 |

---

## 11. 调度器 (Scheduler)

**文件**: `scripts/scheduler.py`

### 定时任务

| 任务 | 频率 | 说明 |
|------|------|------|
| `update_standings_elo` | 每日 06:00 | 更新积分榜和 Elo |
| `update_team_stats` | 每日 12:00 | 更新球队统计 |
| `sync_understat` | 每周一 02:00 | 同步 Understat 数据 |
| `update_injuries` | 每6小时 | 更新伤病数据 |
| `update_odds` | 每4小时 | 更新赔率快照 |
| `health_check` | 每小时 | 健康检查 |

---

## 12. 未来扩展

| 阶段 | 功能 | 状态 |
|------|------|------|
| Phase 3 | 回测系统 | 未开始 |
| Phase 3 | 模型校准 | 未开始 |
| Phase 3 | Web 界面 | 未开始 |
| Phase 3 | 实时赔率监控 | 未开始 |
| Phase 3 | Redis 缓存替换内存缓存 | 未开始 |
| Phase 3 | Provider 健康监控 | 未开始 |

---

## 附录：架构演进历史

### v1.0 → v2.0 变更

| 变更项 | v1.0 | v2.0 |
|--------|------|------|
| 数据采集层 | 单层 Collectors | Provider/DataSource 双层 |
| 数据类型 | Dict/Pydantic | dataclass 标准类型 |
| 数据源管理 | 无 | DataRegistry 单例 |
| 多源支持 | 手动切换 | 自动回退 |
| 缓存位置 | Provider 内部 | DataSource 层 |
| 目录结构 | 扁平化 | 按数据类型分目录 |

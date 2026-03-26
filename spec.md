# FootyStats 数据解析与缓存机制规范

## 1. 概述

### 1.1 目标
为 FootyStats API 的所有 16 个端点建立完整的数据解析和缓存机制，实现：
- **结构化数据模型**：为每个 API 端点定义 Pydantic 数据模型（基于真实 API 响应）
- **分层解析**：在 Provider 层进行原始数据解析，在 DataSource 层进行业务转换
- **数据缓存**：建立多级缓存机制，逐步积累历史数据
- **数据可追溯**：保留原始 JSON 访问能力

### 1.2 设计原则
1. **单一职责**：Provider 层负责 API 调用和基础解析，DataSource 层负责业务逻辑
2. **类型安全**：使用 Pydantic 模型确保数据类型正确
3. **缓存友好**：支持数据增量更新和历史数据积累
4. **向后兼容**：保留访问原始数据的能力

### 1.3 API 响应结构特征

基于 FootyStats API 文档，所有响应遵循以下模式：

```json
{
    "success": true,
    "data": [...],  // 或单个对象
    "pager": {      // 可选，分页信息
        "current_page": 1,
        "max_page": 1,
        "results_per_page": 200,
        "total_results": 2
    },
    "error": {      // 错误时
        "code": 401,
        "message": "Invalid API Key"
    }
}
```

**关键特征**：
- 统一外层包装：`success` + `data`
- 分页信息在 `pager` 字段
- 错误响应包含 `error` 对象
- 数据可能在 `data` 数组中，也可能在 `data` 对象中

## 2. 架构设计

### 2.1 分层架构

```
┌─────────────────────────────────────────────────────────┐
│                    Application Layer                     │
│                   (MatchBuilder, etc.)                   │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                   DataSource Layer                       │
│  (业务逻辑、数据聚合、缓存管理、多 Provider 融合)            │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│               Provider Parsing Layer                     │
│        (API 响应解析、原始数据→结构化模型)                   │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                  API Provider Layer                      │
│            (HTTP 请求、错误处理、限流)                       │
└─────────────────────────────────────────────────────────┘
```

### 2.2 数据模型层次

```python
# Level 1: API 原始响应模型 (provider/footystats/models.py)
class APIResponse(BaseModel):
    raw_data: Dict[str, Any]  # 保留原始数据
    meta: APIMeta  # API 元数据

# Level 2: 领域模型 (domain/models.py)
class Team(BaseModel):
    """球队领域模型"""
    id: str
    name: str
    stats: TeamStats
    raw_data: Dict[str, Any]  # 保留原始数据访问

# Level 3: 业务模型 (aggregator/schema.py)
class TeamStats(BaseModel):
    """业务分析用统计模型"""
    xg_home: float
    xg_away: float
    # ...
```

## 3. 数据模型设计

### 3.1 基础模型 (provider/footystats/models.py)

#### 3.1.1 通用响应模型
```python
class FootyStatsMeta(BaseModel):
    """API 元数据"""
    endpoint: str
    timestamp: datetime
    api_version: str = "1.0"
    rate_limit_remaining: Optional[int] = None

class FootyStatsResponse(BaseModel, Generic[T]):
    """通用 API 响应模型"""
    data: T
    meta: FootyStatsMeta
    raw_data: Dict[str, Any]  # 保留原始 JSON
    
    @classmethod
    def from_api_response(cls, raw: Dict[str, Any], endpoint: str) -> Self:
        """从 API 原始响应创建"""
        return cls(
            data=raw,  # 子类会覆盖这个
            meta=FootyStatsMeta(
                endpoint=endpoint,
                timestamp=datetime.now(),
            ),
            raw_data=raw
        )
```

#### 3.1.2 联赛数据模型
```python
class League(BaseModel):
    """联赛基础信息"""
    id: str
    name: str
    country_id: int
    country_name: str
    is_cup: bool
    current_season_id: Optional[str] = None
    
class Season(BaseModel):
    """联赛赛季信息"""
    id: str
    league_id: str
    year: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: bool = False

class LeagueListResponse(FootyStatsResponse):
    """联赛列表响应"""
    data: List[League]
```

#### 3.1.3 比赛数据模型（基于真实 API）

```python
class Match(BaseModel):
    """比赛详情 - 基于 FootyStats 实际 API 响应"""
    # 基础信息
    id: str = Field(alias="id")  # API 使用 "id"
    season: str = Field(default="", alias="season")  # "2019/2020"
    status: str = Field(default="incomplete", alias="status")  # complete/suspended/canceled/incomplete
    round_id: Optional[str] = Field(None, alias="roundID")
    game_week: Optional[int] = Field(None, alias="game_week")
    
    # 球队 ID - API 使用 homeID/awayID 格式
    home_team_id: str = Field(default="", alias="homeID")
    away_team_id: str = Field(default="", alias="awayID")
    
    # 比分
    home_goals: Optional[int] = Field(None, alias="homeGoalCount")
    away_goals: Optional[int] = Field(None, alias="awayGoalCount")
    
    # 角球 - API 使用 team_a/team_b 格式
    home_corners: Optional[int] = Field(None, alias="team_a_corners")
    away_corners: Optional[int] = Field(None, alias="team_b_corners")
    
    # 射正
    home_shots_on_target: Optional[int] = Field(None, alias="team_a_shotsOnTarget")
    away_shots_on_target: Optional[int] = Field(None, alias="team_b_shotsOnTarget")
    
    # 控球率
    home_possession: Optional[float] = Field(None, alias="team_a_possession")
    away_possession: Optional[float] = Field(None, alias="team_b_possession")
    
    # 赔率 - API 使用 odds_ft_x 格式
    odds_home: Optional[float] = Field(None, alias="odds_ft_1")
    odds_draw: Optional[float] = Field(None, alias="odds_ft_x")
    odds_away: Optional[float] = Field(None, alias="odds_ft_2")
    
    # 双方进球和大球
    btts: Optional[bool] = Field(None, alias="btts")
    over_2_5: Optional[bool] = Field(None, alias="over25")
    
    # 高级数据（比赛详情端点返回）
    league_name: Optional[str] = None
    home_team_name: Optional[str] = None
    away_team_name: Optional[str] = None
    start_date: Optional[str] = None
    start_time: Optional[str] = None
    
    # 阵容、交锋记录、赔率对比等（详情端点）
    lineups: Optional[Dict[str, Any]] = None
    h2h: Optional[Dict[str, Any]] = None
    odds_comparison: Optional[Dict[str, Any]] = None
    trends: Optional[str] = None
    weather: Optional[Dict[str, Any]] = None
    tv_stations: Optional[List[str]] = None
    
    raw_data: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        populate_by_name = True  # 支持别名

class MatchListResponse(FootyStatsResponse):
    """比赛列表响应"""
    data: List[Match]
    pager: Optional[Pagination] = None
```

#### 3.1.4 球队数据模型（基于真实 API）

```python
class TeamRecord(BaseModel):
    """球队记录（主场/客场）"""
    played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0

class LastXStats(BaseModel):
    """最近 X 场比赛统计 - 基于 API 实际响应"""
    # 基础统计
    wins_num_overall: int = Field(0, alias="seasonWinsNum_overall")
    draws_num_overall: int = Field(0, alias="seasonDrawsNum_overall")
    losses_num_overall: int = Field(0, alias="seasonLossesNum_overall")
    matches_played_overall: int = Field(0, alias="seasonMatchesPlayed_overall")
    
    # 进球统计
    goals_total_overall: int = Field(0, alias="seasonGoalsTotal_overall")
    conceded_num_overall: int = Field(0, alias="seasonConcededNum_overall")
    
    # 零封和 BTTS
    clean_sheets_overall: int = Field(0, alias="seasonCS_overall")
    clean_sheet_percentage_overall: float = Field(0.0, alias="seasonCSPercentage_overall")
    btts_overall: int = Field(0, alias="seasonBTTS_overall")
    btts_percentage_overall: float = Field(0.0, alias="seasonBTTSPercentage_overall")
    
    # 场均数据
    ppg_overall: float = Field(0.0, alias="seasonPPG_overall")
    avg_goals_overall: float = Field(0.0, alias="seasonAVG_overall")
    win_percentage_overall: float = Field(0.0, alias="winPercentage_overall")
    
    # 其他
    clean_sheet_num: int = 0
    failed_to_score_num: int = 0
    
    class Config:
        populate_by_name = True

class Team(BaseModel):
    """球队详情 - 基于 FootyStats 实际 API 响应"""
    # 基础信息
    team_id: int = Field(alias="team_id")
    team_name: str = Field(alias="team_name")
    league: Optional[str] = None
    season: Optional[str] = None
    
    # 排名和积分
    position: Optional[int] = None
    points: Optional[int] = None
    
    # 比赛记录
    played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    
    # 进球
    goals_for: int = Field(0, alias="goalsFor")
    goals_against: int = Field(0, alias="goalsAgainst")
    goal_difference: int = Field(0, alias="goalDifference")
    
    # 主场/客场记录
    home_record: Optional[TeamRecord] = None
    away_record: Optional[TeamRecord] = None
    
    # 近期状态
    form: Optional[str] = None  # "WWLWW" 格式
    
    # 高级统计（联赛球队端点）
    xg_for: Optional[float] = None
    xg_against: Optional[float] = None
    possession_avg: Optional[float] = None
    shots_per_game: Optional[float] = None
    shots_on_target_per_game: Optional[float] = None
    
    # 最近 X 场统计（lastx 端点）
    last_5_stats: Optional[LastXStats] = None
    last_6_stats: Optional[LastXStats] = None
    last_10_stats: Optional[LastXStats] = None
    
    # 球队详情（team 端点）
    full_name: Optional[str] = None
    country: Optional[str] = None
    founded: Optional[int] = None
    image: Optional[str] = None
    url: Optional[str] = None
    
    raw_data: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        populate_by_name = True

class TeamResponse(FootyStatsResponse):
    """球队详情响应"""
    data: Team
```

#### 3.1.5 球员数据模型
```python
class PlayerStats(BaseModel):
    """球员统计数据"""
    appearances: int = 0
    goals: int = 0
    assists: int = 0
    minutes_played: int = 0
    yellow_cards: int = 0
    red_cards: int = 0
    shots_per_game: float = 0.0
    pass_accuracy: float = 0.0
    xg: float = 0.0
    xa: float = 0.0

class Player(BaseModel):
    """球员信息"""
    id: str
    name: str
    team_id: str
    team_name: str
    position: str
    age: Optional[int] = None
    nationality: Optional[str] = None
    stats: PlayerStats
    raw_data: Dict[str, Any] = Field(default_factory=dict)

class PlayerListResponse(FootyStatsResponse):
    """球员列表响应"""
    data: List[Player]
    pagination: Optional[Pagination] = None
```

#### 3.1.6 积分榜数据模型
```python
class StandingsEntry(BaseModel):
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
    form: List[str] = []
    xg_for: float = 0.0
    xg_against: float = 0.0

class StandingsTable(BaseModel):
    """积分榜"""
    season_id: str
    league_id: str
    league_name: str
    stage: str  # 'Regular Season', 'Playoffs', etc.
    type: str  # 'total', 'home', 'away'
    entries: List[StandingsEntry]

class StandingsResponse(FootyStatsResponse):
    """积分榜响应"""
    data: List[StandingsTable]  # 可能包含多个阶段/类型
```

#### 3.1.7 裁判数据模型
```python
class RefereeStats(BaseModel):
    """裁判统计"""
    matches_officiated: int = 0
    yellow_cards_per_match: float = 0.0
    red_cards_per_match: float = 0.0
    penalties_per_match: float = 0.0

class Referee(BaseModel):
    """裁判信息"""
    id: str
    name: str
    country: str
    stats: RefereeStats
    raw_data: Dict[str, Any] = Field(default_factory=dict)

class RefereeListResponse(FootyStatsResponse):
    """裁判列表响应"""
    data: List[Referee]
```

### 3.2 缓存数据模型 (datasource/cache_models.py)

```python
class CacheMetadata(BaseModel):
    """缓存元数据"""
    created_at: datetime
    updated_at: datetime
    source: str  # Provider 名称
    version: str  # 数据模型版本
    checksum: str  # 数据校验和

class CachedMatch(BaseModel):
    """缓存的比赛数据"""
    match: Match
    cache_meta: CacheMetadata
    access_count: int = 0
    last_accessed: Optional[datetime] = None

class CachedTeam(BaseModel):
    """缓存的球队数据"""
    team: Team
    cache_meta: CacheMetadata
    historical_stats: List[TeamStats] = []  # 历史统计
    
class CachedLeagueTable(BaseModel):
    """缓存的积分榜"""
    table: StandingsTable
    cache_meta: CacheMetadata
    snapshot_history: List[StandingsTable] = []  # 历史快照
```

## 4. Provider 层实现

### 4.1 增强的 Provider (provider/footystats/client.py)

```python
class FootyStatsProvider(BaseProvider):
    """FootyStats API 提供者 - 增强版"""
    
    BASE_URL = "https://api.football-data-api.com"
    DEFAULT_TIMEOUT = 30.0

    def __init__(self, api_key: str = "", timeout: float = None):
        super().__init__(api_key or settings.FOOTYSTATS_API_KEY, timeout)
        self._parser = FootyStatsParser()  # 解析器
        if not self.api_key:
            logger.warning("FootyStats API key not configured")

    async def _request_raw(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """发送原始请求（保留现有实现）"""
        # ... 现有实现保持不变
        pass

    # ========== 类型化的解析方法 ==========
    
    async def get_league_list_typed(
        self,
        chosen_leagues_only: bool = False,
        country: Optional[int] = None
    ) -> Optional[LeagueListResponse]:
        """获取联赛列表（类型化版本）"""
        raw_data = await self.get_league_list(chosen_leagues_only, country)
        if not raw_data:
            return None
        return self._parser.parse_league_list(raw_data)

    async def get_match_details_typed(
        self,
        match_id: int
    ) -> Optional[MatchResponse]:
        """获取比赛详情（类型化版本）"""
        raw_data = await self.get_match_details(match_id)
        if not raw_data:
            return None
        return self._parser.parse_match_details(raw_data)

    async def get_team_typed(
        self,
        team_id: int
    ) -> Optional[TeamResponse]:
        """获取球队详情（类型化版本）"""
        raw_data = await self.get_team(team_id)
        if not raw_data:
            return None
        return self._parser.parse_team(raw_data)

    # ... 其他端点的类型化版本
```

### 4.2 数据解析器 (provider/footystats/parser.py)

```python
"""FootyStats API 响应解析器"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from .models import (
    League, Season, Match, MatchTeam, MatchScore, MatchOdds,
    Team, TeamStats, TeamForm,
    Player, PlayerStats,
    StandingsTable, StandingsEntry,
    Referee, RefereeStats,
    LeagueListResponse, MatchResponse, TeamResponse,
    FootyStatsMeta,
)
from utils.logger import logger


class FootyStatsParser:
    """FootyStats API 响应解析器"""
    
    @staticmethod
    def _safe_get(data: Dict, *keys, default=None):
        """安全获取嵌套字典值"""
        for key in keys:
            if isinstance(data, dict):
                data = data.get(key, default)
            else:
                return default
        return data if data is not None else default
    
    @staticmethod
    def _parse_datetime(date_str: str, time_str: str = "") -> Optional[datetime]:
        """解析日期时间字符串"""
        if not date_str:
            return None
        try:
            if time_str:
                return datetime.fromisoformat(f"{date_str}T{time_str}")
            return datetime.fromisoformat(date_str)
        except (ValueError, TypeError):
            return None
    
    def parse_league_list(self, raw: Dict[str, Any]) -> LeagueListResponse:
        """解析联赛列表"""
        leagues = []
        data_list = raw.get("data", raw.get("leagues", []))
        
        if not isinstance(data_list, list):
            data_list = [data_list]
        
        for item in data_list:
            try:
                league = League(
                    id=str(self._safe_get(item, "id", "league_id", default="")),
                    name=self._safe_get(item, "name", "league_name", default=""),
                    country_id=int(self._safe_get(item, "country_id", default=0)),
                    country_name=self._safe_get(item, "country", "country_name", default=""),
                    is_cup=bool(self._safe_get(item, "is_cup", default=False)),
                    current_season_id=str(self._safe_get(item, "current_season_id", default=None)),
                )
                leagues.append(league)
            except Exception as e:
                logger.warning(f"Error parsing league: {e}")
                continue
        
        return LeagueListResponse(
            data=leagues,
            meta=FootyStatsMeta(
                endpoint="/league-list",
                timestamp=datetime.now(),
            ),
            raw_data=raw
        )
    
    def parse_match_details(self, raw: Dict[str, Any]) -> MatchResponse:
        """解析比赛详情"""
        data = raw.get("data", raw)
        
        try:
            # 解析球队
            home_team = MatchTeam(
                id=str(self._safe_get(data, "home_id", "homeTeam", "id", default="")),
                name=self._safe_get(data, "home_name", "homeTeam", "name", default=""),
                short_name=self._safe_get(data, "home_short_name", default=None),
                logo_url=self._safe_get(data, "home_logo", default=None),
            )
            
            away_team = MatchTeam(
                id=str(self._safe_get(data, "away_id", "awayTeam", "id", default="")),
                name=self._safe_get(data, "away_name", "awayTeam", "name", default=""),
                short_name=self._safe_get(data, "away_short_name", default=None),
                logo_url=self._safe_get(data, "away_logo", default=None),
            )
            
            # 解析比分
            score = MatchScore(
                home=self._safe_get(data, "home_score", default=None),
                away=self._safe_get(data, "away_score", default=None),
                halftime_home=self._safe_get(data, "ht_score_home", default=None),
                halftime_away=self._safe_get(data, "ht_score_away", default=None),
                fulltime_home=self._safe_get(data, "ft_score_home", default=None),
                fulltime_away=self._safe_get(data, "ft_score_away", default=None),
            )
            
            # 解析赔率
            odds = None
            if self._safe_get(data, "odds_home") is not None:
                odds = MatchOdds(
                    opening_home=self._safe_get(data, "opening_odds_home"),
                    opening_draw=self._safe_get(data, "opening_odds_draw"),
                    opening_away=self._safe_get(data, "opening_odds_away"),
                    current_home=self._safe_get(data, "odds_home"),
                    current_draw=self._safe_get(data, "odds_draw"),
                    current_away=self._safe_get(data, "odds_away"),
                )
            
            # 创建比赛对象
            match = Match(
                id=str(self._safe_get(data, "match_id", "id", default="")),
                season_id=str(self._safe_get(data, "season_id", default="")),
                league_id=str(self._safe_get(data, "league_id", default="")),
                league_name=self._safe_get(data, "competition", "league_name", default=""),
                round=self._safe_get(data, "round", default=None),
                stage=self._safe_get(data, "stage", default=None),
                home_team=home_team,
                away_team=away_team,
                score=score,
                odds=odds,
                kickoff_time=self._parse_datetime(
                    self._safe_get(data, "start_date", "date", default=""),
                    self._safe_get(data, "start_time", "time", default="")
                ),
                status=self._parse_status(self._safe_get(data, "status", default="SCHEDULED")),
                venue=self._safe_get(data, "venue", default=None),
                referee_id=str(self._safe_get(data, "referee_id", default=None)),
                home_xg=self._safe_get(data, "home_xg", default=None),
                away_xg=self._safe_get(data, "away_xg", default=None),
                home_possession=self._safe_get(data, "home_possession", default=None),
                away_possession=self._safe_get(data, "away_possession", default=None),
                raw_data=data,
            )
            
            return MatchResponse(
                data=match,
                meta=FootyStatsMeta(
                    endpoint="/match",
                    timestamp=datetime.now(),
                ),
                raw_data=raw
            )
        except Exception as e:
            logger.error(f"Error parsing match details: {e}")
            return None
    
    def parse_team(self, raw: Dict[str, Any]) -> TeamResponse:
        """解析球队详情"""
        data = raw.get("data", raw)
        
        try:
            # 解析统计数据
            stats = TeamStats(
                played=int(self._safe_get(data, "played", "games", default=0)),
                won=int(self._safe_get(data, "won", "wins", default=0)),
                drawn=int(self._safe_get(data, "drawn", "draws", default=0)),
                lost=int(self._safe_get(data, "lost", "losses", default=0)),
                goals_for=int(self._safe_get(data, "goals_for", "scored", default=0)),
                goals_against=int(self._safe_get(data, "goals_against", "conceded", default=0)),
                points=int(self._safe_get(data, "points", default=0)),
                
                xg_for=float(self._safe_get(data, "xg_for", "xgFor", default=0.0)),
                xg_against=float(self._safe_get(data, "xg_against", "xgAgainst", default=0.0)),
                xg_home=float(self._safe_get(data, "season_xg_home", default=0.0)),
                xg_away=float(self._safe_get(data, "season_xg_away", default=0.0)),
                xga_home=float(self._safe_get(data, "season_xga_home", default=0.0)),
                xga_away=float(self._safe_get(data, "season_xga_away", default=0.0)),
                
                possession_home=float(self._safe_get(data, "season_possession_home", default=0.0)),
                possession_away=float(self._safe_get(data, "season_possession_away", default=0.0)),
                
                # ... 其他字段
            )
            
            # 解析近期状态
            form = TeamForm(
                last_5=self._safe_get(data, "recent_form", "last_5", default=[]),
                last_6=self._safe_get(data, "last_6", default=[]),
                last_10=self._safe_get(data, "last_10", default=[]),
                form_score=self._calculate_form_score(
                    self._safe_get(data, "recent_form", default=[])
                ),
            )
            
            team = Team(
                id=str(self._safe_get(data, "team_id", "id", default="")),
                name=self._safe_get(data, "team_name", "name", default=""),
                short_name=self._safe_get(data, "short_name", default=None),
                country=self._safe_get(data, "country", default=""),
                founded=self._safe_get(data, "founded", default=None),
                venue=self._safe_get(data, "venue", default=None),
                logo_url=self._safe_get(data, "logo_url", default=None),
                stats=stats,
                form=form,
                league_position=self._safe_get(data, "league_position", default=None),
                raw_data=data,
            )
            
            return TeamResponse(
                data=team,
                meta=FootyStatsMeta(
                    endpoint="/team",
                    timestamp=datetime.now(),
                ),
                raw_data=raw
            )
        except Exception as e:
            logger.error(f"Error parsing team data: {e}")
            return None
    
    @staticmethod
    def _calculate_form_score(form: List[str]) -> float:
        """计算状态评分（0-100）"""
        if not form:
            return 0.0
        
        score_map = {'W': 3, 'D': 1, 'L': 0}
        weights = [1.0, 0.9, 0.8, 0.7, 0.6]  # 近期权重更高
        
        total = 0
        weight_sum = 0
        for i, result in enumerate(form[:5]):
            weight = weights[i] if i < len(weights) else 0.5
            total += score_map.get(result, 0) * weight
            weight_sum += weight
        
        return (total / weight_sum) / 3 * 100 if weight_sum > 0 else 0.0
    
    def _parse_status(self, status_str: str) -> str:
        """解析比赛状态"""
        status_mapping = {
            'SCHEDULED': 'SCHEDULED',
            'LIVE': 'LIVE',
            'HT': 'HALFTIME',
            'FT': 'FINISHED',
            'POSTPONED': 'POSTPONED',
            'CANCELLED': 'CANCELLED',
        }
        return status_mapping.get(status_str.upper(), 'SCHEDULED')
    
    # ... 其他解析方法
```

## 5. DataSource 层实现

### 5.1 增强的 DataSource (datasource/match/match_datasource.py)

```python
from typing import Optional, List, Dict, Any
from datasource.base import DataSource, DataCapability
from datasource.types import DataSourceType, Match, MatchType, MatchStatus
from datasource.cache_models import CachedMatch, CacheMetadata
from provider.footystats.models import Match as FootyStatsMatch
from provider.footystats.client import FootyStatsProvider
from utils.logger import logger
import hashlib
import json


class MatchDataSource(DataSource[Match]):
    def __init__(self, providers: List[BaseProvider] = None):
        super().__init__(providers)
        self._cache_ttl = 30.0
        self._history_cache: Dict[str, List[CachedMatch]] = {}  # 历史缓存
    
    @property
    def data_type(self) -> DataSourceType:
        return DataSourceType.MATCH
    
    # ... capabilities 方法保持不变
    
    async def fetch(self, **params) -> Optional[Match]:
        match_id = params.get("match_id")
        if not match_id:
            logger.error("match_id is required")
            return None
        
        cache_key = self._cache_key(**params)
        
        # 尝试从缓存获取
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            # 更新访问计数
            await self._update_cache_access(cache_key)
            return self._convert_to_domain(cached)
        
        # 从 Provider 获取
        raw_data = await self._try_providers("get_match", match_id=match_id)
        if raw_data is None:
            return None
        
        # 解析并缓存
        match = self.parse(raw_data)
        if match:
            self._set_cache(cache_key, match)
            # 添加到历史缓存
            await self._add_to_history(match_id, match, raw_data)
        
        return match
    
    async def _add_to_history(self, match_id: str, match: Match, raw_data: Dict):
        """添加到历史缓存"""
        if match_id not in self._history_cache:
            self._history_cache[match_id] = []
        
        cached = CachedMatch(
            match=match,
            cache_meta=CacheMetadata(
                created_at=datetime.now(),
                updated_at=datetime.now(),
                source="footystats",
                version="1.0",
                checksum=self._compute_checksum(raw_data)
            ),
            access_count=1,
            last_accessed=datetime.now()
        )
        
        self._history_cache[match_id].append(cached)
        
        # 限制历史版本数量
        if len(self._history_cache[match_id]) > 10:
            self._history_cache[match_id] = self._history_cache[match_id][-10:]
    
    def _compute_checksum(self, data: Dict) -> str:
        """计算数据校验和"""
        return hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()
    
    async def _update_cache_access(self, cache_key: str):
        """更新缓存访问记录"""
        # 可以在这里添加访问统计逻辑
        pass
    
    def _convert_to_domain(self, cached: CachedMatch) -> Match:
        """转换为领域模型"""
        return cached.match
    
    def get_history(self, match_id: str) -> List[Match]:
        """获取比赛历史数据"""
        if match_id not in self._history_cache:
            return []
        return [cm.match for cm in self._history_cache[match_id]]
    
    def parse(self, raw_data: Dict[str, Any]) -> Optional[Match]:
        """解析比赛数据（保持现有实现）"""
        # ... 现有实现
        pass
```

### 5.2 球队 DataSource (datasource/team/team_datasource.py)

```python
class TeamDataSource(DataSource[Team]):
    def __init__(self, providers: List[BaseProvider] = None):
        super().__init__(providers)
        self._cache_ttl = 3600.0
        self._historical_stats: Dict[str, List[TeamStats]] = {}  # 历史统计
    
    async def fetch(self, **params) -> Optional[Team]:
        team_id = params.get("team_id")
        team_name = params.get("team_name")
        
        if not team_id and not team_name:
            logger.error("team_id or team_name is required")
            return None
        
        cache_key = self._cache_key(**params)
        cached = self._get_from_cache(cache_key)
        
        if cached is not None:
            return cached
        
        # 获取数据
        team = None
        raw_data = None
        
        if team_id:
            raw_data = await self._try_providers("get_team", team_id=team_id)
            if raw_data:
                team = self.parse(raw_data)
        
        if team:
            # 积累历史统计
            await self._accumulate_stats(team.id, team.stats, raw_data)
            
            #  enrich 数据
            await self._enrich_team_data(team, params)
            
            self._set_cache(cache_key, team)
        
        return team
    
    async def _accumulate_stats(self, team_id: str, stats: TeamStats, raw_data: Dict):
        """积累球队历史统计"""
        if team_id not in self._historical_stats:
            self._historical_stats[team_id] = []
        
        # 添加时间戳
        timestamped_stats = {
            **stats.model_dump(),
            'timestamp': datetime.now().isoformat(),
            'source': 'footystats'
        }
        
        self._historical_stats[team_id].append(timestamped_stats)
        
        # 限制历史记录数量
        if len(self._historical_stats[team_id]) > 50:
            self._historical_stats[team_id] = self._historical_stats[team_id][-50:]
    
    def get_stats_history(self, team_id: str) -> List[Dict]:
        """获取球队历史统计"""
        return self._historical_stats.get(team_id, [])
    
    def get_stats_trend(self, team_id: str, metric: str) -> Optional[Dict]:
        """获取统计指标趋势"""
        history = self.get_stats_history(team_id)
        if not history:
            return None
        
        values = [h.get(metric) for h in history if h.get(metric) is not None]
        if not values:
            return None
        
        return {
            'metric': metric,
            'current': values[-1],
            'average': sum(values) / len(values),
            'min': min(values),
            'max': max(values),
            'trend': 'up' if len(values) > 1 and values[-1] > values[-2] else 'down'
        }
```

## 6. 缓存管理

### 6.1 缓存配置 (config/settings.py)

```python
class CacheSettings(BaseModel):
    """缓存配置"""
    # TTL 配置（秒）
    MATCH_CACHE_TTL: int = 30  # 比赛数据 30 秒
    TEAM_CACHE_TTL: int = 3600  # 球队数据 1 小时
    LEAGUE_CACHE_TTL: int = 86400  # 联赛数据 24 小时
    PLAYER_CACHE_TTL: int = 7200  # 球员数据 2 小时
    
    # 历史缓存配置
    MAX_HISTORY_SIZE: int = 50  # 每个实体最大历史版本数
    ENABLE_HISTORY: bool = True
    
    # 缓存清理
    AUTO_CLEAN_INTERVAL: int = 3600  # 自动清理间隔（秒）
    CLEAN_THRESHOLD: int = 1000  # 触发清理的缓存条目数

# 在 settings 中添加
CACHE = CacheSettings()
```

### 6.2 缓存管理器 (datasource/cache_manager.py)

```python
"""缓存管理器"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from utils.logger import logger
from config.settings import CACHE


class CacheManager:
    """全局缓存管理器"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._cache: Dict[str, Dict[str, Any]] = {}
            self._access_times: Dict[str, datetime] = {}
            self._hit_count = 0
            self._miss_count = 0
            self._initialized = True
            self._start_clean_task()
    
    def _start_clean_task(self):
        """启动定期清理任务"""
        asyncio.create_task(self._periodic_clean())
    
    async def _periodic_clean(self):
        """定期清理过期缓存"""
        while True:
            await asyncio.sleep(CACHE.AUTO_CLEAN_INTERVAL)
            await self.clean_expired()
    
    async def clean_expired(self):
        """清理过期缓存"""
        now = datetime.now()
        expired_keys = []
        
        for key, cached in self._cache.items():
            ttl = self._get_ttl_for_key(key)
            if now - cached['time'] > timedelta(seconds=ttl):
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._cache[key]
            if key in self._access_times:
                del self._access_times[key]
        
        if expired_keys:
            logger.debug(f"Cleaned {len(expired_keys)} expired cache entries")
    
    def _get_ttl_for_key(self, key: str) -> int:
        """根据键类型获取 TTL"""
        if 'match' in key.lower():
            return CACHE.MATCH_CACHE_TTL
        elif 'team' in key.lower():
            return CACHE.TEAM_CACHE_TTL
        elif 'league' in key.lower():
            return CACHE.LEAGUE_CACHE_TTL
        elif 'player' in key.lower():
            return CACHE.PLAYER_CACHE_TTL
        else:
            return 300  # 默认 5 分钟
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if key not in self._cache:
            self._miss_count += 1
            return None
        
        cached = self._cache[key]
        ttl = self._get_ttl_for_key(key)
        
        if datetime.now() - cached['time'] > timedelta(seconds=ttl):
            # 过期
            del self._cache[key]
            self._miss_count += 1
            return None
        
        # 命中
        self._hit_count += 1
        self._access_times[key] = datetime.now()
        return cached['data']
    
    def set(self, key: str, data: Any, ttl: Optional[int] = None):
        """设置缓存"""
        self._cache[key] = {
            'data': data,
            'time': datetime.now(),
            'ttl': ttl
        }
        logger.debug(f"Cache set: {key}")
    
    def delete(self, key: str):
        """删除缓存"""
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"Cache deleted: {key}")
    
    def clear(self):
        """清空所有缓存"""
        self._cache.clear()
        self._access_times.clear()
        logger.info("Cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total = self._hit_count + self._miss_count
        hit_rate = self._hit_count / total if total > 0 else 0
        
        return {
            'size': len(self._cache),
            'hit_count': self._hit_count,
            'miss_count': self._miss_count,
            'hit_rate': f"{hit_rate:.2%}",
        }


# 全局实例
cache_manager = CacheManager()
```

## 7. 使用示例

### 7.1 使用类型化 Provider

```python
# 初始化
provider = FootyStatsProvider()

# 获取类型化数据
match_response = await provider.get_match_details_typed(12345)
if match_response:
    # 访问结构化数据
    match = match_response.data
    print(f"{match.home_team.name} vs {match.away_team.name}")
    print(f"Kickoff: {match.kickoff_time}")
    
    # 访问原始数据
    raw = match_response.raw_data
    print(f"Raw API response: {raw.keys()}")
    
    # 访问元数据
    meta = match_response.meta
    print(f"API Endpoint: {meta.endpoint}")
```

### 7.2 使用 DataSource 和历史缓存

```python
# 初始化 DataSource
match_ds = MatchDataSource(providers=[provider])

# 获取比赛数据
match = await match_ds.fetch(match_id="12345")

# 获取历史数据
history = match_ds.get_history("12345")
print(f"Found {len(history)} historical versions")

# 球队数据
team_ds = TeamDataSource(providers=[provider])
team = await team_ds.fetch(team_id="678")

# 获取统计趋势
trend = team_ds.get_stats_trend("678", "xg_for")
print(f"XG Trend: {trend}")
```

### 7.3 缓存统计

```python
from datasource.cache_manager import cache_manager

# 查看缓存统计
stats = cache_manager.get_stats()
print(f"Cache size: {stats['size']}")
print(f"Hit rate: {stats['hit_rate']}")
```

## 8. 实施步骤

### Phase 1: 数据模型定义（1-2 周）
- [ ] 创建 `provider/footystats/models.py`
- [ ] 定义所有 16 个端点的响应模型
- [ ] 定义缓存数据模型 `datasource/cache_models.py`
- [ ] 编写单元测试验证模型

### Phase 2: Parser 实现（2-3 周）
- [ ] 创建 `provider/footystats/parser.py`
- [ ] 实现所有端点的解析方法
- [ ] 处理边界情况和错误
- [ ] 编写解析测试

### Phase 3: Provider 增强（1-2 周）
- [ ] 在 `FootyStatsProvider` 中添加类型化方法
- [ ] 集成 Parser
- [ ] 保持向后兼容（保留现有方法）
- [ ] 集成测试

### Phase 4: DataSource 增强（2-3 周）
- [ ] 增强 `MatchDataSource` 支持历史缓存
- [ ] 增强 `TeamDataSource` 支持统计积累
- [ ] 实现其他 DataSource 的增强
- [ ] 集成测试

### Phase 5: 缓存管理（1-2 周）
- [ ] 实现 `CacheManager`
- [ ] 配置 TTL 和清理策略
- [ ] 添加缓存统计和监控
- [ ] 性能测试

### Phase 6: 文档和迁移（1 周）
- [ ] 更新 API 文档
- [ ] 编写迁移指南
- [ ] 示例代码
- [ ] 团队培训

## 9. 注意事项

### 9.1 性能考虑
1. **解析开销**：Pydantic 模型解析会增加 CPU 开销，建议：
   - 使用 `model_config = ConfigDict(frozen=True)` 启用不可变模型
   - 对大数据集使用流式解析
   
2. **内存管理**：历史缓存会占用更多内存：
   - 设置合理的 `MAX_HISTORY_SIZE`
   - 实现 LRU 淘汰策略
   - 考虑使用外部缓存（Redis）

### 9.2 数据一致性
1. **版本控制**：数据模型变更时：
   - 增加模型版本号
   - 实现数据迁移逻辑
   - 保持向后兼容

2. **校验和验证**：
   - 定期验证缓存数据完整性
   - 检测 API 数据结构变更

### 9.3 错误处理
1. **解析失败**：
   - 记录详细错误日志
   - 降级到原始数据访问
   - 告警机制

2. **缓存失效**：
   - 优雅降级到直接 API 调用
   - 实现断路器模式

## 10. 未来扩展

### 10.1 持久化存储
- 考虑将历史缓存持久化到数据库
- 支持数据分析和趋势预测

### 10.2 分布式缓存
- 使用 Redis 实现分布式缓存
- 支持多实例共享缓存

### 10.3 数据湖
- 积累的数据可以导入数据湖
- 支持机器学习和高级分析

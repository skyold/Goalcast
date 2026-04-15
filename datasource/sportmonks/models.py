"""Sportmonks 数据模型定义"""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime


@dataclass
class Match:
    """比赛模型"""
    match_id: int
    date: str
    time: str
    status: str
    league_id: int
    league_name: str
    home_team_id: int
    home_team_name: str
    away_team_id: int
    away_team_name: str
    home_score: int = 0
    away_score: int = 0
    venue_id: Optional[int] = None
    referee_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class Team:
    """球队模型"""
    team_id: int
    name: str
    short_name: Optional[str] = None
    logo: Optional[str] = None
    country: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class Player:
    """球员模型"""
    player_id: int
    name: str
    position: Optional[str] = None
    team_id: Optional[int] = None
    nationality: Optional[str] = None
    birth_date: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class League:
    """联赛模型"""
    league_id: int
    name: str
    country: Optional[str] = None
    season_id: Optional[int] = None
    season_name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class XGData:
    """预期进球数据模型"""
    match_id: int
    home_xg: float
    away_xg: float
    home_xg_against: Optional[float] = None
    away_xg_against: Optional[float] = None
    source: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class Odds:
    """赔率数据模型"""
    match_id: int
    home_win: float
    draw: float
    away_win: float
    id: Optional[int] = None
    over_25: Optional[float] = None
    under_25: Optional[float] = None
    btts_yes: Optional[float] = None
    btts_no: Optional[float] = None
    # 亚盘（Asian Handicap）字段
    # ah_line: 让球线，正值表示主队让球（如 -0.5/-1/-1.5），负值表示客队让球（如 +0.5/+1）
    # 四分之一盘：0.25 / 0.75 表示上下盘各半（如 -0.25 = 平手/受让半球）
    ah_line: Optional[float] = None       # 主队让球线，例如 -0.5, -1.0, +0.5
    ah_home_odds: Optional[float] = None  # 主队（让球后）赔率
    ah_away_odds: Optional[float] = None  # 客队（受让后）赔率
    bookmaker: Optional[str] = None
    timestamp: Optional[datetime] = None
    created_at: Optional[datetime] = None


@dataclass
class TeamForm:
    """球队状态模型"""
    team_id: int
    match_id: int
    form_5: str
    form_10: str
    goals_for: int
    goals_against: int
    points: int
    id: Optional[int] = None
    created_at: Optional[datetime] = None


@dataclass
class HeadToHead:
    """交锋记录模型"""
    home_team_id: int
    away_team_id: int
    matches: int
    home_wins: int
    draws: int
    away_wins: int
    home_goals: int
    away_goals: int
    id: Optional[int] = None
    created_at: Optional[datetime] = None


@dataclass
class Standings:
    """积分榜模型"""
    league_id: int
    team_id: int
    position: int
    points: int
    matches_played: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    goal_difference: int
    id: Optional[int] = None
    season_id: Optional[int] = None
    created_at: Optional[datetime] = None


@dataclass
class SportmonksMatchData:
    """
    V4.0 专用数据容器。

    由 goalcast_sm_fetch MCP 工具填充，直连 SportmonksResolver，
    完全绕过 DataFusion 和 MatchContext 归一化层。
    所有 Sportmonks 专有字段（亚盘、预测、赔率时序）原生保留，不被截断。
    """

    # ── 比赛基本信息 ───────────────────────────────────────────
    fixture_id: int
    home_team: str
    away_team: str
    home_team_id: int
    away_team_id: int
    league: str
    season_id: int
    season: str          # 用于 Understat 查询，如 "2025"
    match_date: str      # YYYY-MM-DD
    kickoff_time: str    # ISO 字符串

    # ── xG 数据（fallback 链: sportmonks_direct → understat_direct → league_avg）
    xg_home_for: float = 0.0
    xg_home_against: float = 0.0
    xg_away_for: float = 0.0
    xg_away_against: float = 0.0
    xg_source: str = "league_avg"   # "sportmonks_direct" | "understat_direct" | "league_avg"
    xg_quality: float = 0.35

    # ── 积分榜（主客分离，None 表示不可用）─────────────────────
    home_standing: Optional[Dict[str, Any]] = None
    # 期望键: position, points, wins, draws, losses, goals_for, goals_against, goal_difference
    away_standing: Optional[Dict[str, Any]] = None

    # ── 欧盘赔率（1X2）──────────────────────────────────────────
    odds_home_win: Optional[float] = None
    odds_draw: Optional[float] = None
    odds_away_win: Optional[float] = None
    odds_bookmaker: Optional[str] = None

    # ── 亚盘赔率（Sportmonks 专有，完整保留）──────────────────────
    # ah_line: 让球线（主队视角）如 -0.5 表示主队让半球，+0.5 表示主队受让半球
    ah_line: Optional[float] = None
    ah_home_odds: Optional[float] = None
    ah_away_odds: Optional[float] = None

    # ── 赔率变动时序（48h，L3 权重从 8% 提升至 20% 的触发条件）──
    odds_movement: Optional[List[Dict[str, Any]]] = None
    # 期望元素: {time: str, home: float, draw: float, away: float}

    # ── 阵容（V4.0 L6 贝叶斯更新触发条件）──────────────────────
    lineups: Optional[Dict[str, Any]] = None
    # 期望键: home_formation, away_formation, confirmed (bool)

    # ── 交锋记录 H2H ────────────────────────────────────────────
    h2h: Optional[Dict[str, Any]] = None
    # 期望键: entries (list), home_wins, draws, away_wins, home_goals, away_goals

    # ── Sportmonks 官方预测（V4.0 L7 校准层）──────────────────────
    predictions: Optional[Dict[str, Any]] = None
    # 期望键: home_win (float 0-1), draw (float 0-1), away_win (float 0-1)

    # ── 数据质量元数据 ─────────────────────────────────────────
    overall_quality: float = 0.0
    data_gaps: List[str] = field(default_factory=list)
    # 标准缺失标签: "lineups", "odds_movement", "predictions", "h2h",
    #              "standings", "odds", "xg"

    def to_dict(self) -> Dict[str, Any]:
        """序列化为 dict，供 MCP 工具返回给 Skill 层。"""
        return {
            "fixture_id": self.fixture_id,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "home_team_id": self.home_team_id,
            "away_team_id": self.away_team_id,
            "league": self.league,
            "season_id": self.season_id,
            "season": self.season,
            "match_date": self.match_date,
            "kickoff_time": self.kickoff_time,
            "xg": {
                "home_xg_for": self.xg_home_for,
                "home_xg_against": self.xg_home_against,
                "away_xg_for": self.xg_away_for,
                "away_xg_against": self.xg_away_against,
                "source": self.xg_source,
                "quality": self.xg_quality,
            },
            "home_standing": self.home_standing,
            "away_standing": self.away_standing,
            "odds": {
                "home_win": self.odds_home_win,
                "draw": self.odds_draw,
                "away_win": self.odds_away_win,
                "bookmaker": self.odds_bookmaker,
            } if self.odds_home_win is not None else None,
            "asian_handicap": {
                "ah_line": self.ah_line,
                "ah_home_odds": self.ah_home_odds,
                "ah_away_odds": self.ah_away_odds,
            } if self.ah_line is not None else None,
            "odds_movement": self.odds_movement,
            "lineups": self.lineups,
            "h2h": self.h2h,
            "predictions": self.predictions,
            "overall_quality": self.overall_quality,
            "data_gaps": self.data_gaps,
        }


def _to_jsonable(value: Any) -> Any:
    """将 dataclass/tuple 递归转换为 JSON 友好的结构。"""
    if hasattr(value, "__dataclass_fields__"):
        return _to_jsonable(asdict(value))
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(item) for item in value]
    return value


@dataclass
class SportmonksFixtureSummary:
    """日期级比赛摘要，供 today/fixtures 列表与预热汇总使用。"""

    fixture_id: int
    match_date: str
    kickoff_time: str
    league_id: int
    league_name: str
    season_id: int
    home_team_id: int
    home_team_name: str
    away_team_id: int
    away_team_name: str
    cache_status: str
    last_updated_at: Optional[str] = None
    league_country_id: Optional[int] = None
    league_short_code: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return _to_jsonable(self)


@dataclass
class SportmonksMatchSnapshot:
    """Sportmonks 独立数据层的单场比赛快照。"""

    fixture_id: int
    match_date: str
    kickoff_time: str
    league: str
    season_id: int
    home_team: str
    away_team: str
    home_team_id: int
    away_team_id: int
    xg: Optional[Dict[str, Any]] = None
    standings: Optional[Dict[str, Any]] = None
    odds: Optional[Dict[str, Any]] = None
    asian_handicap: Optional[Dict[str, Any]] = None
    odds_movement: Optional[Dict[str, Any]] = None
    lineups: Optional[Dict[str, Any]] = None
    h2h: Optional[Dict[str, Any]] = None
    predictions: Optional[Dict[str, Any]] = None
    available_layers: Tuple[str, ...] = field(default_factory=tuple)
    missing_layers: Tuple[str, ...] = field(default_factory=tuple)
    cache_status: str = "missing"
    overall_quality: float = 0.0
    warmed_at: Optional[str] = None
    updated_at: Optional[str] = None
    expires_at: Optional[str] = None
    source_versions: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _to_jsonable(self)


@dataclass
class SportmonksWarmupResult:
    """批量预热结果摘要。"""

    date: str
    leagues: List[str]
    fixtures_found: int
    fixtures_warmed: int
    fixtures_partial: int
    fixtures_failed: int
    output_path: str
    results: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return _to_jsonable(self)

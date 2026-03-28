"""
数据类型定义

只保留 FootyStats API 提供的字段
数据分类：Match（比赛信息）、Odds（市场数据）、Team（队伍信息）、StandingsEntry（排名信息）
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class DataSourceType(Enum):
    MATCH = "match"
    TEAM = "team"
    LEAGUE = "league"  # 新增：联赛数据
    ODDS = "odds"
    STANDINGS = "standings"
    ELO = "elo"
    WEATHER = "weather"
    INJURY = "injury"


class MatchType(Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class MatchStatus(Enum):
    SCHEDULED = "SCHEDULED"
    TIMED = "TIMED"
    LIVE = "LIVE"
    IN_PLAY = "IN_PLAY"
    PAUSED = "PAUSED"
    FINISHED = "FINISHED"
    POSTPONED = "POSTPONED"
    SUSPENDED = "SUSPENDED"
    CANCELED = "CANCELED"


@dataclass
class MatchStats:
    """单场比赛统计数据"""
    possession: Optional[float] = None
    shots: Optional[int] = None
    shots_on_target: Optional[int] = None
    corners: Optional[int] = None
    fouls: Optional[int] = None
    yellow_cards: Optional[int] = None
    red_cards: Optional[int] = None
    xg: Optional[float] = None


@dataclass
class Match:
    """比赛实体 - 只包含比赛本身的数据"""
    match_id: str
    home_team: str
    away_team: str
    home_team_id: Optional[str] = None
    away_team_id: Optional[str] = None
    competition: str = ""
    competition_id: Optional[int] = None
    season: Optional[str] = None
    game_week: Optional[int] = None
    status: MatchStatus = MatchStatus.SCHEDULED
    kickoff_time: Optional[datetime] = None
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    venue: Optional[str] = None

    home_stats: Optional[MatchStats] = field(default=None, repr=False)
    away_stats: Optional[MatchStats] = field(default=None, repr=False)

    home_xg_prematch: Optional[float] = None
    away_xg_prematch: Optional[float] = None
    total_xg_prematch: Optional[float] = None

    home_odds: Optional[float] = None
    draw_odds: Optional[float] = None
    away_odds: Optional[float] = None
    over_25_odds: Optional[float] = None
    under_25_odds: Optional[float] = None
    btts_yes_odds: Optional[float] = None
    btts_no_odds: Optional[float] = None

    btts_potential: Optional[int] = None
    o25_potential: Optional[int] = None
    o35_potential: Optional[int] = None
    u25_potential: Optional[int] = None
    corners_potential: Optional[float] = None
    avg_potential: Optional[float] = None

    home_ppg: Optional[float] = None
    away_ppg: Optional[float] = None
    pre_match_home_ppg: Optional[float] = None
    pre_match_away_ppg: Optional[float] = None

    raw_data: Optional[Dict[str, Any]] = field(default=None, repr=False)

    def __repr__(self) -> str:
        return f"<Match {self.home_team} vs {self.away_team} ({self.status.value})>"


@dataclass
class League:
    """联赛实体 - 包含联赛和国家信息"""
    league_id: str
    name: str
    country: str
    season: Optional[str] = None
    season_id: Optional[int] = None
    
    def __repr__(self) -> str:
        return f"<League {self.name} ({self.country})>"


@dataclass
class Odds:
    match_id: str
    home: float
    draw: float
    away: float
    bookmaker: str = ""
    timestamp: Optional[datetime] = None

    def __repr__(self) -> str:
        return f"<Odds {self.home}/{self.draw}/{self.away} ({self.bookmaker})>"


@dataclass
class Team:
    team_id: str
    name: str
    xg_home: Optional[float] = None
    xg_away: Optional[float] = None
    xga_home: Optional[float] = None
    xga_away: Optional[float] = None
    shots: Optional[int] = None
    shots_on_target: Optional[int] = None
    ppg: Optional[float] = None
    position: Optional[int] = None
    played: Optional[int] = None
    won: Optional[int] = None
    drawn: Optional[int] = None
    lost: Optional[int] = None
    goals_for: Optional[int] = None
    goals_against: Optional[int] = None
    goal_difference: Optional[int] = None
    points: Optional[int] = None
    recent_xg: Optional[float] = None
    recent_xga: Optional[float] = None
    possession: Optional[float] = None
    dangerous_attacks: Optional[float] = None
    country: Optional[str] = None
    founded: Optional[int] = None
    venue: Optional[str] = None

    def __repr__(self) -> str:
        return f"<Team {self.name} (#{self.position})>"


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

    def __repr__(self) -> str:
        return f"<StandingsEntry #{self.position} {self.team_name} ({self.points} pts)>"


@dataclass
class Elo:
    team_id: str
    rating: float
    timestamp: Optional[datetime] = None

    def __repr__(self) -> str:
        return f"<Elo {self.rating}>"


@dataclass
class Weather:
    wind_speed: float = 0.0
    rainfall: float = 0.0
    condition: str = "Unknown"
    xg_adjustment: float = 0.0
    timestamp: Optional[datetime] = None

    def __repr__(self) -> str:
        return f"<Weather {self.condition}>"


class InjurySeverity(Enum):
    MINOR = "minor"
    MODERATE = "moderate"
    SEVERE = "severe"
    OUT = "out"


@dataclass
class Injury:
    player_id: str
    player_name: str
    team_id: str
    injury_type: str
    severity: InjurySeverity = InjurySeverity.MINOR
    expected_return: Optional[datetime] = None

    def __repr__(self) -> str:
        return f"<Injury {self.player_name} ({self.severity.value})>"


@dataclass
class Lineup:
    match_id: str
    team_id: str
    formation: str = ""
    players: List[str] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"<Lineup {self.formation}>"


def compute_xg_adjustment(weather: Optional[Weather] = None) -> float:
    """计算天气对 xG 的调整系数"""
    if not weather:
        return 0.0
    return weather.xg_adjustment


def classify_player_importance(player_id: str) -> str:
    """分类球员重要性"""
    return "normal"

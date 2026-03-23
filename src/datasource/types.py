from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class DataSourceType(Enum):
    MATCH = "match"
    TEAM = "team"
    STANDINGS = "standings"
    ODDS = "odds"
    ELO = "elo"
    WEATHER = "weather"


class MatchType(Enum):
    LEAGUE = "A"
    CUP = "B"
    TWO_LEG = "C"
    CRUCIAL = "D"


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

    def __repr__(self) -> str:
        return f"<Match {self.home_team} vs {self.away_team} ({self.status.value})>"


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
    goal_difference: Optional[int] = None
    points: Optional[int] = None
    
    recent_form: List[str] = field(default_factory=list)
    recent_xg: Optional[float] = None
    recent_xga: Optional[float] = None
    
    possession: Optional[float] = None
    ppda: Optional[float] = None
    
    elo: Optional[float] = None
    
    injuries: List[str] = field(default_factory=list)
    
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
    form: List[str] = field(default_factory=list)
    competition: Optional[str] = None

    def __repr__(self) -> str:
        return f"<StandingsEntry #{self.position} {self.team_name} ({self.points} pts)>"


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
    
    home_prob_fair: Optional[float] = None
    draw_prob_fair: Optional[float] = None
    away_prob_fair: Optional[float] = None

    def calculate_implied_probabilities(self):
        total = 1 / self.home + 1 / self.draw + 1 / self.away
        self.home_prob = (1 / self.home) / total
        self.draw_prob = (1 / self.draw) / total
        self.away_prob = (1 / self.away) / total
        
        self.home_prob_fair = 1 / self.home / total
        self.draw_prob_fair = 1 / self.draw / total
        self.away_prob_fair = 1 / self.away / total

    def __repr__(self) -> str:
        return f"<Odds {self.home}/{self.draw}/{self.away} ({self.bookmaker})>"


@dataclass
class Elo:
    team_name: str
    elo: float
    date: Optional[datetime] = None
    rank: Optional[int] = None
    country: Optional[str] = None
    level: Optional[float] = None

    def __repr__(self) -> str:
        return f"<Elo {self.team_name}: {self.elo:.1f}>"


@dataclass
class Weather:
    condition: str
    wind_speed: float
    rain_1h: float
    temperature: Optional[float] = None
    humidity: Optional[int] = None
    pressure: Optional[int] = None
    visibility: Optional[int] = None
    xg_adjustment: float = 0.0

    def calculate_xg_adjustment(self) -> float:
        adjustment = 0.0
        
        if self.wind_speed > 8:
            adjustment -= 0.10
        
        if self.rain_1h > 5:
            adjustment -= 0.10
        
        if self.condition.lower() in ["snow", "fog", "mist", "haze"]:
            adjustment -= 0.10
        
        self.xg_adjustment = adjustment
        return adjustment

    def __repr__(self) -> str:
        return f"<Weather {self.condition}, wind={self.wind_speed}m/s, rain={self.rain_1h}mm>"

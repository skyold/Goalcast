"""
数据类型定义

只保留 FootyStats API 提供的字段
数据分类：Match（比赛信息）、Odds（市场数据）、Team（队伍信息）、StandingsEntry（排名信息）
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from enum import Enum


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
    status: MatchStatus = MatchStatus.SCHEDULED
    kickoff_time: Optional[datetime] = None
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    venue: Optional[str] = None

    def __repr__(self) -> str:
        return f"<Match {self.home_team} vs {self.away_team} ({self.status.value})>"


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

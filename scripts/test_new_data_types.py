#!/usr/bin/env python3
import sys
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Tuple, Dict
from enum import Enum


class DataSourceType(Enum):
    MATCH = "match"
    TEAM = "team"
    STANDINGS = "standings"
    ODDS = "odds"
    ELO = "elo"
    WEATHER = "weather"
    INJURY = "injury"
    LINEUP = "lineup"


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


class InjurySeverity(Enum):
    LONG_TERM = "long_term"
    MEDIUM_TERM = "medium_term"
    SHORT_TERM = "short_term"
    SUSPENSION = "suspension"
    UNKNOWN = "unknown"


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
    first_leg_score: Optional[Tuple[int, int]] = None


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
    dangerous_attacks: Optional[int] = None
    elo: Optional[float] = None
    injuries: List[str] = field(default_factory=list)
    injury_details: List['Injury'] = field(default_factory=list)
    schedule_density_7d: Optional[int] = None
    country: Optional[str] = None
    founded: Optional[int] = None
    venue: Optional[str] = None


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
    opening_odds: Optional['Odds'] = None

    def calculate_implied_probabilities(self):
        total = 1 / self.home + 1 / self.draw + 1 / self.away
        self.home_prob = (1 / self.home) / total
        self.draw_prob = (1 / self.draw) / total
        self.away_prob = (1 / self.away) / total
        self.home_prob_fair = 1 / self.home / total
        self.draw_prob_fair = 1 / self.draw / total
        self.away_prob_fair = 1 / self.away / total

    def calculate_movement(self) -> Dict[str, float]:
        if not self.opening_odds:
            return {}
        return {
            "home_movement": round((self.home - self.opening_odds.home) / self.opening_odds.home * 100, 2),
            "draw_movement": round((self.draw - self.opening_odds.draw) / self.opening_odds.draw * 100, 2),
            "away_movement": round((self.away - self.opening_odds.away) / self.opening_odds.away * 100, 2),
        }


@dataclass
class Elo:
    team_name: str
    elo: float
    date: Optional[datetime] = None
    rank: Optional[int] = None
    country: Optional[str] = None
    level: Optional[float] = None

    def calculate_win_probability(self, opponent_elo: float) -> float:
        return 1 / (1 + 10 ** ((opponent_elo - self.elo) / 400))


@dataclass
class Injury:
    player_name: str
    team_name: str
    injury_type: str
    severity: InjurySeverity = InjurySeverity.UNKNOWN
    position: str = ""
    expected_return: Optional[str] = None
    injury_date: Optional[str] = None
    is_key_player: bool = False
    market_value: Optional[float] = None

    def calculate_xg_adjustment(self) -> float:
        adjustments = {
            InjurySeverity.LONG_TERM: -0.30 if self.is_key_player else -0.15,
            InjurySeverity.MEDIUM_TERM: -0.20 if self.is_key_player else -0.10,
            InjurySeverity.SHORT_TERM: -0.10 if self.is_key_player else -0.05,
            InjurySeverity.SUSPENSION: -0.15 if self.is_key_player else -0.05,
            InjurySeverity.UNKNOWN: 0.0,
        }
        return adjustments.get(self.severity, 0.0)


@dataclass
class Lineup:
    team_id: str
    team_name: str
    match_id: str
    formation: Optional[str] = None
    starting_xi: List[str] = field(default_factory=list)
    substitutes: List[str] = field(default_factory=list)
    is_confirmed: bool = False
    source: str = ""
    last_updated: Optional[datetime] = None


def compute_xg_adjustment(injuries: List[Injury]) -> float:
    total = 0.0
    for injury in injuries:
        total += injury.calculate_xg_adjustment()
    return max(total, -0.50)


def classify_player_importance(
    injuries: List[Injury],
    team_rank: Optional[Dict[str, int]] = None,
    market_value_threshold: float = 20.0,
) -> List[Injury]:
    for injury in injuries:
        if injury.market_value and injury.market_value >= market_value_threshold:
            injury.is_key_player = True
        elif team_rank and injury.player_name in team_rank:
            injury.is_key_player = team_rank[injury.player_name] <= 5
        elif injury.position in ["ST", "CF", "CAM", "GK"]:
            injury.is_key_player = True
    return injuries


def test_injury_dataclass():
    print("\n=== Testing Injury dataclass ===")
    
    injury = Injury(
        player_name="Erling Haaland",
        team_name="Manchester City",
        injury_type="Ankle",
        severity=InjurySeverity.MEDIUM_TERM,
        position="ST",
        expected_return="3 weeks",
        is_key_player=True,
    )
    
    print(f"Injury: {injury}")
    print(f"xG adjustment: {injury.calculate_xg_adjustment()}")
    assert injury.calculate_xg_adjustment() == -0.20
    print("✓ Injury dataclass test passed")


def test_lineup_dataclass():
    print("\n=== Testing Lineup dataclass ===")
    
    lineup = Lineup(
        team_id="123",
        team_name="Arsenal",
        match_id="456",
        formation="4-3-3",
        starting_xi=["Raya", "White", "Saliba", "Gabriel", "Zinchenko", 
                     "Odegaard", "Rice", "Havertz", "Saka", "Martinelli", "Jesus"],
        is_confirmed=True,
        source="official",
    )
    
    print(f"Lineup: {lineup}")
    assert lineup.is_confirmed == True
    assert len(lineup.starting_xi) == 11
    print("✓ Lineup dataclass test passed")


def test_compute_xg_adjustment():
    print("\n=== Testing compute_xg_adjustment ===")
    
    injuries = [
        Injury("Player A", "Team", "Knee", InjurySeverity.LONG_TERM, is_key_player=True),
        Injury("Player B", "Team", "Ankle", InjurySeverity.MEDIUM_TERM, is_key_player=False),
        Injury("Player C", "Team", "Suspension", InjurySeverity.SUSPENSION, is_key_player=True),
    ]
    
    adjustment = compute_xg_adjustment(injuries)
    expected = -0.30 - 0.10 - 0.15
    print(f"Total xG adjustment: {adjustment}")
    assert adjustment == round(max(expected, -0.50), 2)
    print("✓ compute_xg_adjustment test passed")


def test_classify_player_importance():
    print("\n=== Testing classify_player_importance ===")
    
    injuries = [
        Injury("Star Player", "Team", "Knee", InjurySeverity.LONG_TERM, position="ST"),
        Injury("Regular Player", "Team", "Ankle", InjurySeverity.SHORT_TERM, position="MF"),
        Injury("Goalkeeper", "Team", "Hand", InjurySeverity.MEDIUM_TERM, position="GK"),
    ]
    
    classified = classify_player_importance(injuries)
    
    print(f"Star Player is_key_player: {classified[0].is_key_player}")
    print(f"Regular Player is_key_player: {classified[1].is_key_player}")
    print(f"Goalkeeper is_key_player: {classified[2].is_key_player}")
    
    assert classified[0].is_key_player == True
    assert classified[1].is_key_player == False
    assert classified[2].is_key_player == True
    print("✓ classify_player_importance test passed")


def test_elo_win_probability():
    print("\n=== Testing Elo.calculate_win_probability ===")
    
    home_elo = Elo("Arsenal", 1850.0)
    away_elo = Elo("Chelsea", 1750.0)
    
    home_win_prob = home_elo.calculate_win_probability(away_elo.elo)
    
    print(f"Arsenal Elo: {home_elo.elo}")
    print(f"Chelsea Elo: {away_elo.elo}")
    print(f"Arsenal win probability vs Chelsea: {home_win_prob:.2%}")
    
    expected = 1 / (1 + 10 ** ((1750 - 1850) / 400))
    assert abs(home_win_prob - expected) < 0.001
    print("✓ Elo.calculate_win_probability test passed")


def test_odds_movement():
    print("\n=== Testing Odds.calculate_movement ===")
    
    opening = Odds(home=2.00, draw=3.40, away=4.00, bookmaker="Bet365")
    current = Odds(home=1.80, draw=3.50, away=4.50, bookmaker="Bet365", opening_odds=opening)
    
    movement = current.calculate_movement()
    
    print(f"Opening odds: {opening.home}/{opening.draw}/{opening.away}")
    print(f"Current odds: {current.home}/{current.draw}/{current.away}")
    print(f"Movement: {movement}")
    
    assert movement["home_movement"] == -10.0
    assert movement["away_movement"] == 12.5
    print("✓ Odds.calculate_movement test passed")


def test_match_first_leg_score():
    print("\n=== Testing Match.first_leg_score ===")
    
    match = Match(
        match_id="12345",
        home_team="Arsenal",
        away_team="Bayern Munich",
        competition="Champions League",
        match_type=MatchType.TWO_LEG,
        first_leg_score=(2, 1),
    )
    
    print(f"Match: {match}")
    print(f"Match type: {match.match_type.value}")
    print(f"First leg score: {match.first_leg_score}")
    
    assert match.first_leg_score == (2, 1)
    assert match.match_type == MatchType.TWO_LEG
    print("✓ Match.first_leg_score test passed")


def test_team_new_fields():
    print("\n=== Testing Team new fields ===")
    
    team = Team(
        team_id="1",
        name="Arsenal",
        dangerous_attacks=45,
        schedule_density_7d=3,
        injury_details=[
            Injury("Saka", "Arsenal", "Hamstring", InjurySeverity.SHORT_TERM, is_key_player=True),
        ],
    )
    
    print(f"Team: {team}")
    print(f"Dangerous attacks: {team.dangerous_attacks}")
    print(f"Schedule density 7d: {team.schedule_density_7d}")
    print(f"Injury details count: {len(team.injury_details)}")
    
    assert team.dangerous_attacks == 45
    assert team.schedule_density_7d == 3
    assert len(team.injury_details) == 1
    print("✓ Team new fields test passed")


def main():
    print("=" * 60)
    print("Testing new data types and methods")
    print("=" * 60)
    
    test_injury_dataclass()
    test_lineup_dataclass()
    test_compute_xg_adjustment()
    test_classify_player_importance()
    test_elo_win_probability()
    test_odds_movement()
    test_match_first_leg_score()
    test_team_new_fields()
    
    print("\n" + "=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)


if __name__ == "__main__":
    main()

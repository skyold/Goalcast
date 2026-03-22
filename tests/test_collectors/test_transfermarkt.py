import pytest
from src.collectors.transfermarkt import (
    InjuryItem,
    classify_player_importance,
    compute_xg_adjustment,
)


def test_injury_item_creation():
    injury = InjuryItem(
        player_name="John Doe",
        position="ST",
        injury_type="Hamstring",
        injury_date="2024-01-15",
        expected_return="3 weeks",
        severity="medium_term",
    )
    
    assert injury.player_name == "John Doe"
    assert injury.position == "ST"
    assert injury.severity == "medium_term"
    assert injury.is_key_player == False


def test_classify_player_importance():
    injuries = [
        InjuryItem("Player A", "ST", "Knee", "", "months", "long_term", market_value=50.0),
        InjuryItem("Player B", "GK", "Ankle", "", "weeks", "medium_term"),
        InjuryItem("Player C", "MF", "Muscle", "", "days", "short_term"),
    ]
    
    team_rank = {"Player A": 1, "Player B": 5, "Player C": 10}
    
    result = classify_player_importance(injuries, team_rank)
    
    assert result[0].is_key_player == True
    assert result[1].is_key_player == True
    assert result[2].is_key_player == False


def test_compute_xg_adjustment_long_term_key():
    injuries = [
        InjuryItem("Star", "ST", "ACL", "", "out for season", "long_term", is_key_player=True),
    ]
    
    adjustment = compute_xg_adjustment(injuries)
    
    assert adjustment == -0.30


def test_compute_xg_adjustment_multiple():
    injuries = [
        InjuryItem("Player A", "ST", "Knee", "", "months", "long_term", is_key_player=True),
        InjuryItem("Player B", "MF", "Ankle", "", "weeks", "medium_term", is_key_player=False),
        InjuryItem("Player C", "DF", "Suspension", "", "1 match", "suspension", is_key_player=True),
    ]
    
    adjustment = compute_xg_adjustment(injuries)
    
    expected = -0.30 - 0.10 - 0.15
    assert adjustment == round(max(expected, -0.50), 2)


def test_compute_xg_adjustment_cap():
    injuries = [
        InjuryItem("P1", "ST", "Injury", "", "months", "long_term", is_key_player=True),
        InjuryItem("P2", "MF", "Injury", "", "months", "long_term", is_key_player=True),
        InjuryItem("P3", "DF", "Injury", "", "months", "long_term", is_key_player=True),
    ]
    
    adjustment = compute_xg_adjustment(injuries)
    
    assert adjustment == -0.50

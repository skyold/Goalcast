import pytest
from src.collectors.understat import compute_recent_form, compute_ppda_season


def test_compute_recent_form_empty():
    result = compute_recent_form([], "Team A", 5)
    
    assert result["form"] == []
    assert result["xg_sum"] == 0.0
    assert result["xga_sum"] == 0.0
    assert result["wins"] == 0


def test_compute_recent_form_wins():
    matches = [
        {"home_team": "Team A", "away_team": "Team B", "home_goals": 2, "away_goals": 1, "home_xg": 1.8, "away_xg": 0.9},
        {"home_team": "Team C", "away_team": "Team A", "home_goals": 0, "away_goals": 3, "home_xg": 0.5, "away_xg": 2.1},
        {"home_team": "Team A", "away_team": "Team D", "home_goals": 1, "away_goals": 1, "home_xg": 1.2, "away_xg": 1.1},
    ]
    
    result = compute_recent_form(matches, "Team A", 5)
    
    assert result["form"] == ["W", "W", "D"]
    assert result["wins"] == 2
    assert result["draws"] == 1
    assert result["losses"] == 0
    assert result["points"] == 7
    assert result["xg_sum"] == pytest.approx(1.8 + 2.1 + 1.2, 0.01)
    assert result["xga_sum"] == pytest.approx(0.9 + 0.5 + 1.1, 0.01)


def test_compute_recent_form_losses():
    matches = [
        {"home_team": "Team A", "away_team": "Team B", "home_goals": 0, "away_goals": 2, "home_xg": 0.5, "away_xg": 1.8},
        {"home_team": "Team C", "away_team": "Team A", "home_goals": 3, "away_goals": 1, "home_xg": 2.2, "away_xg": 0.8},
    ]
    
    result = compute_recent_form(matches, "Team A", 5)
    
    assert result["form"] == ["L", "L"]
    assert result["wins"] == 0
    assert result["losses"] == 2
    assert result["points"] == 0


def test_compute_ppda_season():
    team_stats = {
        "ppda_att": 10.0,
        "ppda_def": 8.0,
    }
    
    result = compute_ppda_season(team_stats)
    
    assert result["ppda"] == 0.8
    assert result["ppda_att"] == 10.0
    assert result["ppda_def"] == 8.0


def test_compute_ppda_season_zero():
    team_stats = {
        "ppda_att": 0,
        "ppda_def": 0,
    }
    
    result = compute_ppda_season(team_stats)
    
    assert result["ppda"] == 0.0

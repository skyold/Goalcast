"""Tests for provider.oddalerts.feature_extractor."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))

from provider.oddalerts.feature_extractor import (
    extract_team_lambdas,
    extract_market_odds,
    extract_trend_priors,
)


def test_extract_team_lambdas_from_season_stats():
    home_stats = {"goals_for_avg": 2.1, "goals_against_avg": 0.8, "xg_for": 2.24}
    away_stats = {"goals_for_avg": 1.4, "goals_against_avg": 1.3, "xg_for": 1.05}
    out = extract_team_lambdas(home_stats, away_stats)
    assert 1.0 < out["home_lambda"] < 3.0
    assert 0.5 < out["away_lambda"] < 2.0
    assert out["source"] == "oddalerts_stats"


def test_extract_team_lambdas_prefers_xg_over_goals_avg():
    """If xg_for is present, it should be used; goals_for_avg is fallback."""
    home_with_xg = {"xg_for": 2.5, "goals_for_avg": 1.0, "goals_against_avg": 1.0}
    away_with_xg = {"xg_for": 1.0, "goals_for_avg": 2.5, "goals_against_avg": 1.0}
    out = extract_team_lambdas(home_with_xg, away_with_xg)
    # Home lambda should be higher because home.xg_for is 2.5 (not 1.0 from goals_for_avg)
    assert out["home_lambda"] > out["away_lambda"]


def test_extract_team_lambdas_missing_data_returns_none():
    assert extract_team_lambdas({}, {}) is None
    assert extract_team_lambdas({"xg_for": 1.0}, {}) is None  # away has nothing


def test_extract_market_odds_picks_closing_1x2():
    odds_history = {
        "markets": {
            "ft_result": {
                "Bet365": {
                    "home": {"closing": 1.72, "opening": 1.87, "peak": 1.90},
                    "draw": {"closing": 3.85},
                    "away": {"closing": 4.60},
                }
            }
        }
    }
    out = extract_market_odds(odds_history, market="ft_result", bookmaker="Bet365")
    assert out == {"H": 1.72, "D": 3.85, "A": 4.60}


def test_extract_market_odds_missing_market_returns_none():
    assert extract_market_odds({}) is None
    assert extract_market_odds({"markets": {}}) is None
    assert extract_market_odds({"markets": {"ft_result": {}}}) is None


def test_extract_market_odds_alternate_bookmaker():
    odds_history = {
        "markets": {
            "ft_result": {
                "Pinnacle": {
                    "home": {"closing": 1.74},
                    "draw": {"closing": 3.80},
                    "away": {"closing": 4.55},
                }
            }
        }
    }
    out = extract_market_odds(odds_history, bookmaker="Pinnacle")
    assert out["H"] == 1.74


def test_extract_trend_priors():
    trends = {"homeWin": 0.621, "awayWin": 0.182, "btts": 0.554}
    out = extract_trend_priors(trends)
    assert out["H"] == 0.621
    assert out["A"] == 0.182
    assert abs(out["D"] - (1 - 0.621 - 0.182)) < 1e-9


def test_extract_trend_priors_handles_missing_or_zero():
    out = extract_trend_priors({})
    assert out == {"H": 0.0, "D": 1.0, "A": 0.0}

    out2 = extract_trend_priors({"homeWin": 0.6, "awayWin": 0.5})  # impossibly large sum
    # D should clamp to 0, not go negative
    assert out2["D"] == 0.0

"""Tests for poisson_from_oddalerts wrapper."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from analytics.poisson import poisson_from_oddalerts


def test_poisson_from_oddalerts_returns_full_distribution():
    home_stats = {"xg_for": 2.0, "goals_against_avg": 1.0}
    away_stats = {"xg_for": 1.0, "goals_against_avg": 1.0}
    result = poisson_from_oddalerts(home_stats, away_stats)
    assert result is not None
    assert "home_win_pct" in result
    assert "draw_pct" in result
    assert "away_win_pct" in result
    total = result["home_win_pct"] + result["draw_pct"] + result["away_win_pct"]
    # Top-6 grid covers ~99.9% of mass; allow 1% tolerance.
    assert abs(total - 100.0) < 1.0


def test_poisson_from_oddalerts_missing_data_returns_none():
    assert poisson_from_oddalerts({}, {}) is None


def test_poisson_from_oddalerts_higher_xg_home_implies_higher_home_win():
    strong_home = {"xg_for": 2.5, "goals_against_avg": 0.5}
    weak_away = {"xg_for": 0.8, "goals_against_avg": 2.0}
    result = poisson_from_oddalerts(strong_home, weak_away)
    assert result["home_win_pct"] > result["away_win_pct"]
    assert result["home_win_pct"] > 50  # clearly favored


def test_poisson_from_oddalerts_max_goals_threading():
    """max_goals parameter should be forwarded to poisson_distribution."""
    home_stats = {"xg_for": 2.0, "goals_against_avg": 1.0}
    away_stats = {"xg_for": 1.0, "goals_against_avg": 1.0}
    r4 = poisson_from_oddalerts(home_stats, away_stats, max_goals=4)
    r6 = poisson_from_oddalerts(home_stats, away_stats, max_goals=6)
    # Different grids → slightly different totals
    assert r4 is not None and r6 is not None
    assert len(r4["score_matrix"]) == 5   # 0..4 inclusive
    assert len(r6["score_matrix"]) == 7   # 0..6 inclusive

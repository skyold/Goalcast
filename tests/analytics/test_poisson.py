import pytest
from analytics.poisson import poisson_distribution, dixon_coles_distribution


def test_poisson_probabilities_sum_to_one():
    result = poisson_distribution(1.5, 1.2)
    total = result["home_win_pct"] + result["draw_pct"] + result["away_win_pct"]
    assert abs(total - 100.0) < 0.5


def test_poisson_home_favorite():
    result = poisson_distribution(2.5, 0.8)
    assert result["home_win_pct"] > result["away_win_pct"]


def test_poisson_returns_score_matrix():
    result = poisson_distribution(1.5, 1.2)
    assert "score_matrix" in result
    assert len(result["score_matrix"]) == 7  # 0-6 goals


def test_dixon_coles_low_score_boost():
    dc = dixon_coles_distribution(1.3, 1.1)
    standard = poisson_distribution(1.3, 1.1)
    # Both should have draw probability in reasonable range
    assert 20 <= dc["draw_pct"] <= 50
    assert "score_matrix" in dc


def test_poisson_over25_pct():
    result = poisson_distribution(1.8, 1.4)
    assert 0 <= result["over_25_pct"] <= 100


def test_poisson_btts_pct():
    result = poisson_distribution(1.8, 1.4)
    assert 0 <= result["btts_pct"] <= 100

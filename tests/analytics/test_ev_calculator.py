"""
Tests for analytics.ev_calculator module.

Covers:
- calculate_ev: positive/negative edge, invalid inputs
- calculate_kelly: positive stake, zero/negative EV returns 0
- calculate_risk_adjusted_ev: result is <= raw EV for positive values
- best_bet_recommendation: returns expected keys and correct ratings
"""

import pytest
from analytics.ev_calculator import (
    best_bet_recommendation,
    calculate_ev,
    calculate_kelly,
    calculate_risk_adjusted_ev,
)


# ---------------------------------------------------------------------------
# calculate_ev
# ---------------------------------------------------------------------------


def test_ev_positive_when_model_probability_exceeds_implied():
    # Model says 60% (implied odds = 1/0.6 = 1.667), market offers 2.0
    result = calculate_ev(model_probability=60.0, market_odds=2.0)
    assert result["ev"] > 0
    assert result["is_value"] is True


def test_ev_negative_when_model_probability_below_implied():
    # Model says 40% (implied odds = 2.5), market only offers 2.0
    result = calculate_ev(model_probability=40.0, market_odds=2.0)
    assert result["ev"] < 0
    assert result["is_value"] is False


def test_ev_returns_required_keys():
    result = calculate_ev(model_probability=50.0, market_odds=2.10)
    assert "ev" in result
    assert "ev_pct" in result
    assert "is_value" in result
    assert "break_even_odds" in result


def test_ev_invalid_odds_returns_error():
    result = calculate_ev(model_probability=50.0, market_odds=0.0)
    assert result["ev"] == 0.0
    assert result["is_value"] is False
    assert "error" in result


def test_ev_negative_odds_returns_error():
    result = calculate_ev(model_probability=50.0, market_odds=-1.5)
    assert "error" in result


def test_ev_break_even_odds_correct():
    # For 50% model probability, break-even is 1/0.5 = 2.0
    result = calculate_ev(model_probability=50.0, market_odds=2.0)
    assert abs(result["break_even_odds"] - 2.0) < 0.001


def test_ev_pct_is_ev_times_100():
    result = calculate_ev(model_probability=55.0, market_odds=2.0)
    assert abs(result["ev_pct"] - result["ev"] * 100) < 0.01


# ---------------------------------------------------------------------------
# calculate_kelly
# ---------------------------------------------------------------------------


def test_kelly_recommends_bet_with_positive_edge():
    # 60% model probability vs 2.0 odds => positive edge
    result = calculate_kelly(model_probability=60.0, market_odds=2.0)
    assert result["recommended"] is True
    assert result["fractional_kelly_pct"] > 0


def test_kelly_returns_zero_when_ev_is_negative():
    # 40% vs 2.0 odds => negative edge
    result = calculate_kelly(model_probability=40.0, market_odds=2.0)
    assert result["recommended"] is False
    assert result["fractional_kelly_pct"] == 0.0
    assert result["full_kelly_pct"] == 0.0


def test_kelly_stake_computed_when_bankroll_provided():
    result = calculate_kelly(
        model_probability=60.0,
        market_odds=2.0,
        bankroll=1000.0,
    )
    assert result["stake"] is not None
    assert result["stake"] > 0


def test_kelly_no_stake_without_bankroll():
    result = calculate_kelly(model_probability=60.0, market_odds=2.0)
    assert result["stake"] is None


def test_kelly_fractional_is_quarter_of_full():
    result = calculate_kelly(
        model_probability=60.0,
        market_odds=2.0,
        fraction=0.25,
    )
    assert abs(result["fractional_kelly_pct"] - result["full_kelly_pct"] * 0.25) < 0.001


def test_kelly_invalid_odds_returns_error():
    result = calculate_kelly(model_probability=60.0, market_odds=1.0)
    assert result["recommended"] is False
    assert "error" in result


def test_kelly_returns_required_keys():
    result = calculate_kelly(model_probability=50.0, market_odds=2.5)
    for key in ("full_kelly_pct", "fractional_kelly_pct", "stake", "ev", "recommended"):
        assert key in result


# ---------------------------------------------------------------------------
# calculate_risk_adjusted_ev
# ---------------------------------------------------------------------------


def test_risk_adjusted_ev_lte_raw_ev_for_positive():
    raw = 0.15
    adjusted = calculate_risk_adjusted_ev(raw_ev=raw, lineup_uncertainty=True)
    assert adjusted <= raw


def test_risk_adjusted_ev_all_flags_reduces_significantly():
    raw = 0.20
    adjusted = calculate_risk_adjusted_ev(
        raw_ev=raw,
        lineup_uncertainty=True,
        market_low_confidence=True,
        data_quality="low",
    )
    # 0.20 × 0.85 × 0.90 × 0.80 ≈ 0.1224
    assert adjusted < raw * 0.7


def test_risk_adjusted_ev_no_flags_unchanged():
    raw = 0.10
    adjusted = calculate_risk_adjusted_ev(raw_ev=raw)
    assert adjusted == pytest.approx(raw, abs=0.0001)


def test_risk_adjusted_ev_negative_raw_stays_negative():
    raw = -0.05
    adjusted = calculate_risk_adjusted_ev(raw_ev=raw, lineup_uncertainty=True)
    assert adjusted < 0


def test_risk_adjusted_ev_data_quality_high_no_penalty():
    raw = 0.12
    adjusted = calculate_risk_adjusted_ev(raw_ev=raw, data_quality="high")
    assert adjusted == pytest.approx(raw, abs=0.0001)


# ---------------------------------------------------------------------------
# best_bet_recommendation
# ---------------------------------------------------------------------------


def test_best_bet_returns_required_keys():
    result = best_bet_recommendation(ev_home=0.10, ev_draw=0.02, ev_away=0.05)
    for key in ("best_bet", "bet_rating", "max_ev", "max_ev_direction"):
        assert key in result


def test_best_bet_picks_highest_ev_direction():
    result = best_bet_recommendation(ev_home=0.03, ev_draw=0.01, ev_away=0.12)
    assert result["max_ev_direction"] == "away"
    assert result["best_bet"] == "客胜"


def test_best_bet_recommends_when_ev_above_threshold():
    result = best_bet_recommendation(ev_home=0.12, ev_draw=0.01, ev_away=0.02)
    assert result["bet_rating"] == "推荐"


def test_best_bet_small_stake_in_mid_range():
    result = best_bet_recommendation(ev_home=0.06, ev_draw=0.01, ev_away=0.02)
    assert result["bet_rating"] == "小注"


def test_best_bet_not_recommended_when_all_ev_negative():
    result = best_bet_recommendation(ev_home=-0.05, ev_draw=-0.02, ev_away=-0.10)
    assert result["best_bet"] == "不推荐"
    assert result["bet_rating"] == "不推荐"


def test_best_bet_risk_adjusted_uses_adj_evs():
    # Raw EVs all low, but adjusted EVs are high
    result = best_bet_recommendation(
        ev_home=0.02,
        ev_draw=0.01,
        ev_away=0.01,
        risk_adjusted=True,
        ev_adj_home=0.15,
        ev_adj_draw=0.05,
        ev_adj_away=0.03,
        confidence=75,
    )
    assert result["max_ev_direction"] == "home"
    assert result["bet_rating"] == "推荐"


def test_best_bet_risk_adjusted_not_recommended_low_confidence():
    result = best_bet_recommendation(
        ev_home=0.12,
        ev_draw=0.01,
        ev_away=0.01,
        risk_adjusted=True,
        ev_adj_home=0.12,
        ev_adj_draw=0.01,
        ev_adj_away=0.01,
        confidence=50,  # Below 70 threshold
    )
    # EV > 0.10 but confidence <= 70 → not 推荐
    assert result["bet_rating"] != "推荐"

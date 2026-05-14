"""Tests for ev_from_oddalerts wrapper."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from analytics.ev_calculator import ev_from_oddalerts


_ODDS = {
    "markets": {
        "ft_result": {
            "Bet365": {
                "home": {"closing": 1.72},
                "draw": {"closing": 3.85},
                "away": {"closing": 4.60},
            }
        }
    }
}


def test_ev_from_oddalerts_positive_when_model_outperforms_market():
    model_probs = {"H": 0.62, "D": 0.20, "A": 0.18}
    result = ev_from_oddalerts(model_probs, _ODDS)
    assert result is not None
    # 0.62 * 1.72 - 1 = +6.64%
    assert result["H"]["ev"] > 0.05
    assert result["H"]["ev"] < 0.10


def test_ev_from_oddalerts_negative_when_market_more_efficient():
    model_probs = {"H": 0.30, "D": 0.30, "A": 0.40}
    result = ev_from_oddalerts(model_probs, _ODDS)
    # 0.30 * 1.72 - 1 = -0.484 (very negative)
    assert result["H"]["ev"] < 0


def test_ev_from_oddalerts_returns_all_three_directions():
    model_probs = {"H": 0.40, "D": 0.30, "A": 0.30}
    result = ev_from_oddalerts(model_probs, _ODDS)
    assert set(result.keys()) == {"H", "D", "A"}
    for d in ("H", "D", "A"):
        assert "ev" in result[d]
        assert "kelly" in result[d]
        assert "model_prob" in result[d]
        assert "odds" in result[d]


def test_ev_from_oddalerts_kelly_is_decimal_not_percent():
    """Kelly fraction should be 0-1 decimal (consistent with model_prob)."""
    model_probs = {"H": 0.80, "D": 0.10, "A": 0.10}  # huge edge → kelly recommended
    result = ev_from_oddalerts(model_probs, _ODDS)
    # Full Kelly for 80% on 1.72: (0.72 * 0.80 - 0.20) / 0.72 = 0.522; quarter = 0.131
    # Expected kelly returned ~0.13, NOT 13.0
    assert 0 < result["H"]["kelly"] < 0.5


def test_ev_from_oddalerts_missing_odds_returns_none():
    assert ev_from_oddalerts({"H": 0.5, "D": 0.3, "A": 0.2}, {}) is None
    assert ev_from_oddalerts({"H": 0.5, "D": 0.3, "A": 0.2}, {"markets": {}}) is None


def test_ev_from_oddalerts_alternate_bookmaker():
    odds = {
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
    result = ev_from_oddalerts({"H": 0.6, "D": 0.25, "A": 0.15}, odds, bookmaker="Pinnacle")
    assert result is not None
    assert result["H"]["odds"] == 1.74

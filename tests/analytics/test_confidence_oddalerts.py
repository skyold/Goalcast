"""Tests for confidence_from_oddalerts wrapper."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from analytics.confidence import confidence_from_oddalerts


def test_confidence_high_when_model_and_trends_agree():
    model_probs = {"H": 0.62, "D": 0.20, "A": 0.18}
    trends = {"homeWin": 0.621, "awayWin": 0.182}   # virtually identical
    out = confidence_from_oddalerts(model_probs, trends, odds_history_present=True)
    assert out["agreement"] is True
    assert out["stars"] >= 4
    assert "score" in out


def test_confidence_low_when_model_disagrees_with_trends():
    model_probs = {"H": 0.30, "D": 0.20, "A": 0.50}  # picks A with 0.50
    trends = {"homeWin": 0.621, "awayWin": 0.182}     # prior on A is much lower (~0.18)
    out = confidence_from_oddalerts(model_probs, trends, odds_history_present=True)
    assert out["agreement"] is False
    assert out["stars"] <= 3


def test_confidence_stars_in_valid_range():
    """Stars must be in [0, 5] regardless of input."""
    out = confidence_from_oddalerts(
        {"H": 0.5, "D": 0.3, "A": 0.2},
        {"homeWin": 0.5, "awayWin": 0.2},
        odds_history_present=False,
    )
    assert 0 <= out["stars"] <= 5


def test_confidence_score_in_clamped_range():
    """Underlying calculate_confidence clamps to [30, 90]."""
    out = confidence_from_oddalerts(
        {"H": 0.4, "D": 0.3, "A": 0.3},
        {"homeWin": 0.4, "awayWin": 0.3},
        odds_history_present=True,
    )
    assert 30 <= out["score"] <= 90


def test_confidence_pick_is_top_probability():
    """Agreement compares model's top pick against the same direction's prior."""
    # Model picks D (highest at 0.50), trends.D = 1 - 0.30 - 0.20 = 0.50. Match!
    model_probs = {"H": 0.30, "D": 0.50, "A": 0.20}
    trends = {"homeWin": 0.30, "awayWin": 0.20}
    out = confidence_from_oddalerts(model_probs, trends, odds_history_present=True)
    assert out["agreement"] is True


def test_confidence_returns_dict_shape():
    out = confidence_from_oddalerts(
        {"H": 0.5, "D": 0.3, "A": 0.2},
        {"homeWin": 0.5, "awayWin": 0.2},
    )
    assert set(out.keys()) == {"score", "stars", "agreement"}
    assert isinstance(out["score"], int)
    assert isinstance(out["stars"], int)
    assert isinstance(out["agreement"], bool)

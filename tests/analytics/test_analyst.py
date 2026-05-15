import pytest
from analytics.analyst import generate_summary


def test_summary_strong_pick():
    out = generate_summary({
        "pick": "H",
        "model_prob": {"H": 0.62, "D": 0.2, "A": 0.18},
        "ev": 0.064, "kelly": 0.041, "confidence_stars": 4,
    })
    assert out is not None
    assert "主胜" in out
    assert "62.0%" in out
    assert "+6.4%" in out
    assert "重点关注" in out


def test_summary_weak_signal():
    out = generate_summary({
        "pick": "D",
        "model_prob": {"H": 0.3, "D": 0.4, "A": 0.3},
        "ev": 0.005, "kelly": 0.0, "confidence_stars": 1,
    })
    assert "观望" in out


def test_summary_negative_ev():
    out = generate_summary({
        "pick": "A",
        "model_prob": {"H": 0.5, "D": 0.3, "A": 0.2},
        "ev": -0.02, "kelly": 0.0, "confidence_stars": 2,
    })
    assert "观望" in out


def test_summary_returns_none_on_missing_fields():
    assert generate_summary(None) is None
    assert generate_summary({}) is None
    assert generate_summary({"pick": "X"}) is None  # unknown pick
    assert generate_summary({"pick": "H"}) is None  # missing prob/ev

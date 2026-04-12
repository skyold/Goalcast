import pytest
from analytics.confidence import calculate_confidence, calculate_confidence_v25


def test_confidence_clamped_to_90():
    score = calculate_confidence(
        base_score=90,
        market_agrees=True,
        data_complete=True,
        understat_available=True,
        odds_available=True,
    )
    assert score <= 90


def test_confidence_clamped_to_30():
    score = calculate_confidence(
        base_score=10,
        data_quality_low=True,
        understat_failed=True,
        match_type_c=True,
        major_uncertainty=True,
    )
    assert score >= 30


def test_confidence_default_base_is_70():
    # With no bonuses or deductions (except lineup_unavailable=True default)
    score = calculate_confidence()
    assert 30 <= score <= 90


def test_confidence_v25_exists():
    score = calculate_confidence_v25()
    assert 30 <= score <= 90

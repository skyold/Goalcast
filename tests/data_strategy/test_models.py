from data_strategy.models import (
    MatchContext, XGStats, OddsSnapshot, TeamFormWindow,
    StandingsEntry, get_understat_league_code,
)
from data_strategy.quality import compute_overall_quality, quality_to_label


def test_understat_league_code_premier_league():
    assert get_understat_league_code("Premier League") == "EPL"

def test_understat_league_code_la_liga():
    assert get_understat_league_code("La Liga") == "La_liga"

def test_understat_league_code_unknown():
    assert get_understat_league_code("Fake League") is None

def test_compute_overall_quality_all_high():
    q = compute_overall_quality(0.95, 0.85, 0.90, 0.90)
    assert 0.85 < q <= 1.0

def test_compute_overall_quality_all_missing():
    q = compute_overall_quality(0.0, 0.0, 0.0, 0.0)
    assert q == 0.0

def test_compute_overall_quality_partial():
    # Only xG available (weight 0.35)
    q = compute_overall_quality(0.95, 0.0, 0.0, 0.0)
    assert 0.30 < q < 0.40  # ~0.35 * 0.95

def test_quality_to_label_high():
    assert quality_to_label(0.80) == "high"

def test_quality_to_label_medium():
    assert quality_to_label(0.60) == "medium"

def test_quality_to_label_low():
    assert quality_to_label(0.30) == "low"

def test_quality_to_label_minimal():
    assert quality_to_label(0.10) == "minimal"

def test_xg_stats_frozen():
    import pytest
    xg = XGStats(
        home_xg_for=1.8, home_xg_against=1.0,
        away_xg_for=1.2, away_xg_against=1.4,
        source="understat_direct", quality=0.95,
    )
    with pytest.raises(Exception):
        xg.home_xg_for = 2.0

def test_odds_snapshot_frozen():
    import pytest
    odds = OddsSnapshot(home_win=1.85, draw=3.50, away_win=4.20, source="footystats", quality=0.90)
    with pytest.raises(Exception):
        odds.home_win = 2.0

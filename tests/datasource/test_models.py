from datasource.datafusion.models import (
    MatchContext, XGStats, OddsSnapshot, TeamFormWindow,
    StandingsEntry, get_understat_league_code,
)
from datasource.datafusion.quality import compute_overall_quality, quality_to_label


def test_understat_league_code_premier_league():
    assert get_understat_league_code("Premier League") == "EPL"

def test_understat_league_code_la_liga():
    assert get_understat_league_code("La Liga") == "La_Liga"
    assert get_understat_league_code("Spanish La Liga") == "La_Liga"

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


# ── Task 4 tests: new value objects ──────────────────────────

from datasource.datafusion.models import MatchLineups, OddsMovement, H2HEntry

def test_match_lineups_frozen():
    import pytest
    lu = MatchLineups(
        home_formation="4-3-3",
        away_formation="4-4-2",
        home_confirmed=True,
        away_confirmed=False,
    )
    with pytest.raises(Exception):  # FrozenInstanceError
        lu.home_formation = "4-2-3-1"

def test_match_lineups_optional_formation():
    lu = MatchLineups(
        home_formation=None,
        away_formation="4-4-2",
        home_confirmed=False,
        away_confirmed=True,
    )
    assert lu.home_formation is None
    assert lu.away_confirmed is True

def test_odds_movement_frozen():
    import pytest
    om = OddsMovement(
        home_open=2.10, home_current=1.95,
        draw_open=3.40, draw_current=3.50,
        away_open=3.20, away_current=3.40,
        movement_hours=48,
    )
    with pytest.raises(Exception):
        om.home_current = 2.0

def test_odds_movement_direction():
    om = OddsMovement(
        home_open=2.10, home_current=1.90,
        draw_open=3.40, draw_current=3.50,
        away_open=3.80, away_current=4.00,
        movement_hours=24,
    )
    # Home odds shortened (favourite strengthened)
    assert om.home_current < om.home_open

def test_h2h_entry_frozen():
    import pytest
    entry = H2HEntry(
        date="2025-10-20",
        home_team="Arsenal",
        away_team="Chelsea",
        home_goals=2,
        away_goals=1,
    )
    with pytest.raises(Exception):
        entry.home_goals = 3

def test_h2h_entry_draw():
    entry = H2HEntry(date="2025-09-15", home_team="Liverpool", away_team="Man City", home_goals=1, away_goals=1)
    assert entry.home_goals == entry.away_goals


# ── Task 5 tests: updated MatchContext ───────────────────────

import time

def _make_minimal_ctx(**overrides):
    defaults = dict(
            data_provider="footystats",
            match_id="1234",
            league="Premier League",
            home_team="Arsenal",
            home_team_id="86",
            away_team="Chelsea",
            away_team_id="83",
            season_id="1980",
            match_date="2026-04-12",
            xg=None,
            home_form_5=None, home_form_10=None,
            away_form_5=None, away_form_10=None,
            form_source="missing", form_quality=0.0,
            home_standing=None, away_standing=None,
            total_teams=0,
            standings_source="missing", standings_quality=0.0,
            odds=None,
            asian_handicap=None,
            lineups=None,
            odds_movement=None,
            head_to_head=None,
            predictions=None,
            data_gaps=("xg", "form", "lineups"),
            overall_quality=0.0,
            sources={},
            resolved_at=time.time(),
        )
    defaults.update(overrides)
    return MatchContext(**defaults)

def test_match_context_has_data_provider():
    ctx = _make_minimal_ctx(data_provider="sportmonks")
    assert ctx.data_provider == "sportmonks"

def test_match_context_footystats_provider():
    ctx = _make_minimal_ctx(data_provider="footystats")
    assert ctx.data_provider == "footystats"

def test_match_context_lineups_none():
    ctx = _make_minimal_ctx(lineups=None)
    assert ctx.lineups is None

def test_match_context_lineups_set():
    lu = MatchLineups(home_formation="4-3-3", away_formation="4-4-2",
                      home_confirmed=True, away_confirmed=False)
    ctx = _make_minimal_ctx(lineups=lu)
    assert ctx.lineups.home_formation == "4-3-3"

def test_match_context_odds_movement_none():
    ctx = _make_minimal_ctx(odds_movement=None)
    assert ctx.odds_movement is None

def test_match_context_head_to_head_none():
    ctx = _make_minimal_ctx(head_to_head=None)
    assert ctx.head_to_head is None

def test_match_context_to_dict_includes_data_provider():
    ctx = _make_minimal_ctx(data_provider="footystats")
    d = ctx.to_dict()
    assert d["data_provider"] == "footystats"

def test_match_context_to_dict_with_lineups():
    lu = MatchLineups(home_formation="4-3-3", away_formation="4-4-2",
                      home_confirmed=True, away_confirmed=False)
    ctx = _make_minimal_ctx(lineups=lu)
    d = ctx.to_dict()
    assert d["lineups"]["home_formation"] == "4-3-3"
    assert d["lineups"]["home_confirmed"] is True

def test_match_context_to_dict_lineups_none():
    ctx = _make_minimal_ctx(lineups=None)
    d = ctx.to_dict()
    assert d["lineups"] is None

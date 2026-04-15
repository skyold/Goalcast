import json

from data_strategy.sportmonks.models import (
    SportmonksFixtureSummary,
    SportmonksMatchSnapshot,
    SportmonksWarmupResult,
)


def test_fixture_summary_to_dict_is_json_serializable():
    fixture = SportmonksFixtureSummary(
        fixture_id=19374628,
        match_date="2026-04-15",
        kickoff_time="2026-04-15T19:00:00Z",
        league_id=8,
        league_name="Premier League",
        season_id=23614,
        home_team_id=1,
        home_team_name="Arsenal",
        away_team_id=2,
        away_team_name="Chelsea",
        cache_status="fresh",
        last_updated_at="2026-04-15T10:00:00Z",
    )

    payload = fixture.to_dict()

    assert payload["fixture_id"] == 19374628
    assert payload["league_name"] == "Premier League"
    json.dumps(payload)


def test_match_snapshot_to_dict_contains_cache_metadata():
    snapshot = SportmonksMatchSnapshot(
        fixture_id=19374628,
        match_date="2026-04-15",
        kickoff_time="2026-04-15T19:00:00Z",
        league="Premier League",
        season_id=23614,
        home_team="Arsenal",
        away_team="Chelsea",
        home_team_id=1,
        away_team_id=2,
        xg={"home_xg_for": 1.8, "away_xg_for": 1.1},
        standings=None,
        odds={"home_win": 1.91, "draw": 3.45, "away_win": 4.10},
        asian_handicap=None,
        odds_movement=None,
        lineups=None,
        h2h=None,
        predictions=None,
        available_layers=("xg", "odds"),
        missing_layers=("lineups", "predictions"),
        cache_status="partial",
        overall_quality=0.74,
        warmed_at="2026-04-15T10:00:00Z",
        updated_at="2026-04-15T10:15:00Z",
        expires_at="2026-04-15T12:15:00Z",
        source_versions={"sportmonks": "v3"},
    )

    payload = snapshot.to_dict()

    assert payload["cache_status"] == "partial"
    assert payload["available_layers"] == ["xg", "odds"]
    assert payload["missing_layers"] == ["lineups", "predictions"]
    json.dumps(payload)


def test_warmup_result_to_dict_includes_counts():
    result = SportmonksWarmupResult(
        date="2026-04-15",
        leagues=["Premier League", "Championship", "Serie A"],
        fixtures_found=24,
        fixtures_warmed=20,
        fixtures_partial=3,
        fixtures_failed=1,
        output_path="data/cache/sportmonks/2026-04-15",
        results=[{"fixture_id": 1, "cache_status": "fresh"}],
    )

    payload = result.to_dict()

    assert payload["fixtures_found"] == 24
    assert payload["fixtures_failed"] == 1
    json.dumps(payload)

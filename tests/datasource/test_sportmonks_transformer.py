from datasource.sportmonks.transformer import build_match_snapshot


def test_build_match_snapshot_marks_partial_when_layers_missing():
    raw_layers = {
        "fixture": {
            "id": 19374628,
            "starting_at": "2026-04-15T19:00:00Z",
            "league": {"name": "Premier League"},
            "season_id": 23614,
            "participants": [
                {"id": 1, "name": "Arsenal", "meta": {"location": "home"}},
                {"id": 2, "name": "Chelsea", "meta": {"location": "away"}},
            ],
        },
        "xg": {"home_xg_for": 1.8, "away_xg_for": 1.1},
        "odds": {"home_win": 1.91, "draw": 3.45, "away_win": 4.10},
        "lineups": None,
        "predictions": None,
    }

    snapshot = build_match_snapshot(raw_layers)

    assert snapshot.fixture_id == 19374628
    assert snapshot.cache_status == "partial"
    assert "xg" in snapshot.available_layers
    assert "lineups" in snapshot.missing_layers
    assert snapshot.home_team == "Arsenal"


def test_build_match_snapshot_merges_existing_layers():
    raw_layers = {
        "fixture": {
            "id": 19374628,
            "starting_at": "2026-04-15T19:00:00Z",
            "league": {"name": "Premier League"},
            "season_id": 23614,
            "participants": [
                {"id": 1, "name": "Arsenal", "meta": {"location": "home"}},
                {"id": 2, "name": "Chelsea", "meta": {"location": "away"}},
            ],
        },
        "lineups": {
            "home_formation": "4-3-3",
            "away_formation": "4-4-2",
        },
    }
    existing_snapshot = {
        "fixture_id": 19374628,
        "match_date": "2026-04-15",
        "kickoff_time": "2026-04-15T19:00:00Z",
        "league": "Premier League",
        "season_id": 23614,
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "home_team_id": 1,
        "away_team_id": 2,
        "xg": {"home_xg_for": 1.8, "away_xg_for": 1.1},
        "standings": None,
        "odds": {"home_win": 1.91, "draw": 3.45, "away_win": 4.10},
        "asian_handicap": None,
        "odds_movement": None,
        "lineups": None,
        "h2h": None,
        "predictions": None,
        "available_layers": ["xg", "odds"],
        "missing_layers": ["lineups"],
        "cache_status": "partial",
        "overall_quality": 0.7,
        "warmed_at": "2026-04-15T10:00:00Z",
        "updated_at": "2026-04-15T10:05:00Z",
        "expires_at": "2026-04-15T12:05:00Z",
        "source_versions": {"sportmonks": "v3"},
    }

    snapshot = build_match_snapshot(raw_layers, existing_snapshot=existing_snapshot)

    assert snapshot.xg == {"home_xg_for": 1.8, "away_xg_for": 1.1}
    assert snapshot.lineups["home_formation"] == "4-3-3"
    assert "lineups" in snapshot.available_layers

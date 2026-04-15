import json
from pathlib import Path

from data_strategy.sportmonks.store import SportmonksStore


def test_write_and_read_fixtures(tmp_path: Path):
    store = SportmonksStore(base_dir=tmp_path)
    fixtures = [
        {
            "fixture_id": 19374628,
            "home_team_name": "Arsenal",
            "away_team_name": "Chelsea",
            "league_name": "Premier League",
            "cache_status": "fresh",
        }
    ]

    store.write_fixtures("2026-04-15", fixtures)
    loaded = store.read_fixtures("2026-04-15")

    assert loaded == fixtures


def test_write_match_creates_expected_layout(tmp_path: Path):
    store = SportmonksStore(base_dir=tmp_path)
    snapshot = {
        "fixture_id": 19374628,
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "cache_status": "fresh",
    }

    store.write_match(
        fixture_id=19374628,
        date="2026-04-15",
        snapshot=snapshot,
        home_team="Arsenal",
        away_team="Chelsea",
    )

    match_dir = tmp_path / "2026-04-15" / "Arsenal__Chelsea__19374628"
    assert match_dir.exists()
    assert json.loads((match_dir / "match.json").read_text())["fixture_id"] == 19374628


def test_find_match_dir_by_fixture_id(tmp_path: Path):
    store = SportmonksStore(base_dir=tmp_path)
    store.write_match(
        fixture_id=19374628,
        date="2026-04-15",
        snapshot={"fixture_id": 19374628},
        home_team="Arsenal",
        away_team="Chelsea",
    )

    match_dir = store.find_match_dir(fixture_id=19374628, date="2026-04-15")

    assert match_dir is not None
    assert match_dir.name.endswith("__19374628")


def test_write_raw_layer_creates_raw_directory(tmp_path: Path):
    store = SportmonksStore(base_dir=tmp_path)
    store.write_match(
        fixture_id=19374628,
        date="2026-04-15",
        snapshot={"fixture_id": 19374628},
        home_team="Arsenal",
        away_team="Chelsea",
    )

    store.write_raw_layer(
        fixture_id=19374628,
        date="2026-04-15",
        layer="odds",
        payload={"data": [{"odds": {"home": 1.91}}]},
    )

    raw_path = (
        tmp_path
        / "2026-04-15"
        / "Arsenal__Chelsea__19374628"
        / "raw"
        / "odds.json"
    )
    assert raw_path.exists()
    assert json.loads(raw_path.read_text())["data"][0]["odds"]["home"] == 1.91

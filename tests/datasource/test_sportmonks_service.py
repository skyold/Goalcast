from unittest.mock import AsyncMock, MagicMock

import pytest

from datasource.sportmonks.models import SportmonksFixtureSummary
from datasource.sportmonks.service import SportmonksDataService


class FakeCollector:
    def __init__(self):
        self.override_layers = {}

    async def get_fixtures_by_date(self, date: str):
        return [
            {
                "id": 1,
                "starting_at": f"{date}T19:00:00Z",
                "league": {"id": 8, "name": "Premier League"},
                "season_id": 23614,
                "participants": [
                    {"id": 1, "name": "Arsenal", "meta": {"location": "home"}},
                    {"id": 2, "name": "Chelsea", "meta": {"location": "away"}},
                ],
            },
            {
                "id": 2,
                "starting_at": f"{date}T19:45:00Z",
                "league": {"id": 9, "name": "Serie A"},
                "season_id": 23615,
                "participants": [
                    {"id": 3, "name": "Inter", "meta": {"location": "home"}},
                    {"id": 4, "name": "Milan", "meta": {"location": "away"}},
                ],
            },
        ]

    async def collect_match_layers(self, fixture: dict):
        payload = {
            "fixture": fixture,
            "xg": {"home_xg_for": 1.8, "away_xg_for": 1.1},
            "standings": {"data": [{"position": 1}, {"position": 4}]},
            "odds": {"home_win": 1.91, "draw": 3.45, "away_win": 4.10},
            "asian_handicap": {"home": -0.5, "away": 0.5},
            "odds_movement": {"home_open": 1.95, "home_current": 1.91},
            "lineups": {"home_formation": "4-3-3", "away_formation": "4-4-2"},
            "h2h": [{"date": "2026-01-01", "score": "2-1"}],
            "predictions": {"home": 0.52, "draw": 0.25, "away": 0.23},
        }
        payload.update(self.override_layers)
        return payload


class AmbiguousLeagueCollector:
    async def get_fixtures_by_date(self, date: str):
        return [
            {
                "id": 10,
                "starting_at": f"{date}T15:00:00Z",
                "league": {"id": 830, "name": "Premier League", "country_id": 886, "short_code": "EGY D1"},
                "season_id": 26148,
                "participants": [
                    {"id": 250630, "name": "Modern Sport FC", "meta": {"location": "home"}},
                    {"id": 16473, "name": "El Gounah", "meta": {"location": "away"}},
                ],
            },
            {
                "id": 11,
                "starting_at": f"{date}T19:00:00Z",
                "league": {"id": 8, "name": "Premier League", "country_id": 462, "short_code": "ENG PR"},
                "season_id": 25647,
                "participants": [
                    {"id": 1, "name": "Arsenal", "meta": {"location": "home"}},
                    {"id": 2, "name": "Chelsea", "meta": {"location": "away"}},
                ],
            },
            {
                "id": 12,
                "starting_at": f"{date}T20:00:00Z",
                "league": {"id": 9, "name": "Championship", "country_id": 462, "short_code": "UK CHAMP"},
                "season_id": 25648,
                "participants": [
                    {"id": 5, "name": "Portsmouth", "meta": {"location": "home"}},
                    {"id": 116, "name": "Ipswich Town", "meta": {"location": "away"}},
                ],
            },
        ]

    async def collect_match_layers(self, fixture: dict):
        return {
            "fixture": fixture,
            "xg": {"home_xg_for": 1.5, "away_xg_for": 1.1},
            "standings": {"data": []},
            "odds": {"home_win": 2.0, "draw": 3.3, "away_win": 3.8},
            "asian_handicap": {"home": -0.25, "away": 0.25},
            "odds_movement": {"home_open": 2.05, "home_current": 2.0},
            "lineups": {"home_formation": "4-3-3", "away_formation": "4-2-3-1"},
            "h2h": [],
            "predictions": {"home": 0.48, "draw": 0.27, "away": 0.25},
        }


@pytest.mark.asyncio
async def test_get_todays_matches_delegates_to_get_fixtures():
    service = SportmonksDataService(store=object(), collector=object())
    expected = [
        SportmonksFixtureSummary(
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
    ]
    service.get_fixtures = AsyncMock(return_value=expected)

    result = await service.get_todays_matches(leagues=["Premier League"], warm_if_missing=False)

    assert result == expected
    service.get_fixtures.assert_awaited_once()
    assert service.get_fixtures.await_args.kwargs["leagues"] == ["Premier League"]
    assert service.get_fixtures.await_args.kwargs["warm_if_missing"] is False


@pytest.mark.asyncio
async def test_get_matches_defaults_to_today_and_auto_warm():
    service = SportmonksDataService(store=object(), collector=object())
    expected = [
        SportmonksFixtureSummary(
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
    ]
    service.get_fixtures = AsyncMock(return_value=expected)

    result = await service.get_matches(leagues=["Premier League"])

    assert result == expected
    service.get_fixtures.assert_awaited_once()
    assert service.get_fixtures.await_args.kwargs["warm_if_missing"] is True
    assert service.get_fixtures.await_args.kwargs["leagues"] == ["Premier League"]
    assert service.get_fixtures.await_args.kwargs["date"] is not None


@pytest.mark.asyncio
async def test_get_match_reads_existing_snapshot_from_store():
    store = MagicMock()
    store.read_match.return_value = {
        "fixture_id": 19374628,
        "match_date": "2026-04-15",
        "kickoff_time": "2026-04-15T19:00:00Z",
        "league": "Premier League",
        "season_id": 23614,
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "home_team_id": 1,
        "away_team_id": 2,
        "xg": {"home_xg_for": 1.8},
        "standings": None,
        "odds": None,
        "asian_handicap": None,
        "odds_movement": None,
        "lineups": None,
        "h2h": None,
        "predictions": None,
        "available_layers": ["xg"],
        "missing_layers": ["lineups"],
        "cache_status": "fresh",
        "overall_quality": 0.72,
        "warmed_at": "2026-04-15T10:00:00Z",
        "updated_at": "2026-04-15T10:15:00Z",
        "expires_at": "2026-04-15T12:15:00Z",
        "source_versions": {"sportmonks": "v3"},
    }
    service = SportmonksDataService(store=store, collector=object())

    snapshot = await service.get_match(fixture_id=19374628, date="2026-04-15", refresh_if_stale=False)

    assert snapshot.fixture_id == 19374628
    assert snapshot.cache_status == "fresh"
    store.read_match.assert_called_once_with(19374628, "2026-04-15")


@pytest.mark.asyncio
async def test_get_match_for_analysis_prefetches_on_missing_snapshot_then_returns_data():
    snapshot_payload = {
        "fixture_id": 19374628,
        "match_date": "2026-04-15",
        "kickoff_time": "2026-04-15T19:00:00Z",
        "league": "Premier League",
        "season_id": 23614,
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "home_team_id": 1,
        "away_team_id": 2,
        "xg": {"home_xg_for": 1.8},
        "standings": None,
        "odds": None,
        "asian_handicap": None,
        "odds_movement": None,
        "lineups": None,
        "h2h": None,
        "predictions": None,
        "available_layers": ["xg"],
        "missing_layers": [],
        "cache_status": "fresh",
        "overall_quality": 0.72,
        "warmed_at": "2026-04-15T10:00:00Z",
        "updated_at": "2026-04-15T10:15:00Z",
        "expires_at": "2026-04-15T12:15:00Z",
        "source_versions": {"sportmonks": "v3"},
    }
    store = MagicMock()
    store.read_match.side_effect = [None, snapshot_payload]
    service = SportmonksDataService(store=store, collector=object())
    service.prefetch = AsyncMock()

    result = await service.get_match_for_analysis(
        fixture_id=19374628,
        match_date="2026-04-15",
    )

    assert result["fixture_id"] == 19374628
    service.prefetch.assert_awaited_once_with(
        date="2026-04-15",
        leagues=None,
        refresh_stale=False,
    )


@pytest.mark.asyncio
async def test_get_match_refreshes_when_snapshot_is_stale(tmp_path):
    from datasource.sportmonks.store import SportmonksStore

    collector = FakeCollector()
    store = SportmonksStore(base_dir=tmp_path)
    service = SportmonksDataService(store=store, collector=collector)
    await service.prefetch("2026-04-15", leagues=["Premier League"], refresh_stale=False)

    match_dir = store.find_match_dir(1, "2026-04-15")
    assert match_dir is not None
    payload = store.read_match(1, "2026-04-15")
    payload["cache_status"] = "stale"
    store.write_match(
        fixture_id=1,
        date="2026-04-15",
        snapshot=payload,
        home_team="Arsenal",
        away_team="Chelsea",
    )

    collector.override_layers = {
        "lineups": {"home_formation": "3-4-3", "away_formation": "4-2-3-1"},
    }

    snapshot = await service.get_match(fixture_id=1, date="2026-04-15", refresh_if_stale=True)

    assert snapshot.lineups["home_formation"] == "3-4-3"
    assert snapshot.cache_status == "fresh"


@pytest.mark.asyncio
async def test_get_fixtures_reads_store_and_filters_leagues():
    store = MagicMock()
    store.read_fixtures.return_value = [
        {
            "fixture_id": 1,
            "match_date": "2026-04-15",
            "kickoff_time": "2026-04-15T19:00:00Z",
            "league_id": 8,
            "league_name": "Premier League",
            "season_id": 23614,
            "home_team_id": 1,
            "home_team_name": "Arsenal",
            "away_team_id": 2,
            "away_team_name": "Chelsea",
            "cache_status": "fresh",
            "last_updated_at": "2026-04-15T10:00:00Z",
        },
        {
            "fixture_id": 2,
            "match_date": "2026-04-15",
            "kickoff_time": "2026-04-15T19:45:00Z",
            "league_id": 9,
            "league_name": "Serie A",
            "season_id": 23615,
            "home_team_id": 3,
            "home_team_name": "Inter",
            "away_team_id": 4,
            "away_team_name": "Milan",
            "cache_status": "fresh",
            "last_updated_at": "2026-04-15T10:05:00Z",
        },
    ]
    service = SportmonksDataService(store=store, collector=object())

    fixtures = await service.get_fixtures("2026-04-15", leagues=["Premier League"], warm_if_missing=False)

    assert len(fixtures) == 1
    assert fixtures[0].league_name == "Premier League"
    assert fixtures[0].fixture_id == 1
    store.read_fixtures.assert_called_once_with("2026-04-15")


@pytest.mark.asyncio
async def test_get_fixtures_uses_precise_league_mapping_for_cached_index():
    store = MagicMock()
    store.read_fixtures.return_value = [
        {
            "fixture_id": 10,
            "match_date": "2026-04-14",
            "kickoff_time": "2026-04-14 15:00:00",
            "league_id": 830,
            "league_name": "Premier League",
            "league_country_id": 886,
            "league_short_code": "EGY D1",
            "season_id": 26148,
            "home_team_id": 250630,
            "home_team_name": "Modern Sport FC",
            "away_team_id": 16473,
            "away_team_name": "El Gounah",
            "cache_status": "partial",
            "last_updated_at": "2026-04-15T10:00:00Z",
        },
        {
            "fixture_id": 11,
            "match_date": "2026-04-14",
            "kickoff_time": "2026-04-14 19:00:00",
            "league_id": 8,
            "league_name": "Premier League",
            "league_country_id": 462,
            "league_short_code": "ENG PR",
            "season_id": 25647,
            "home_team_id": 1,
            "home_team_name": "Arsenal",
            "away_team_id": 2,
            "away_team_name": "Chelsea",
            "cache_status": "partial",
            "last_updated_at": "2026-04-15T10:00:00Z",
        },
    ]
    service = SportmonksDataService(store=store, collector=object())

    fixtures = await service.get_fixtures("2026-04-14", leagues=["Premier League"], warm_if_missing=False)

    assert len(fixtures) == 1
    assert fixtures[0].fixture_id == 11


@pytest.mark.asyncio
async def test_get_fixtures_prefetches_when_cache_missing_and_warm_enabled(tmp_path):
    from datasource.sportmonks.store import SportmonksStore

    store = SportmonksStore(base_dir=tmp_path)
    collector = FakeCollector()
    service = SportmonksDataService(store=store, collector=collector)

    fixtures = await service.get_fixtures("2026-04-15", leagues=["Premier League"], warm_if_missing=True)

    assert len(fixtures) == 1
    assert fixtures[0].fixture_id == 1
    assert store.read_fixtures("2026-04-15")[0]["fixture_id"] == 1


@pytest.mark.asyncio
async def test_prefetch_writes_fixtures_and_match_snapshots(tmp_path):
    from datasource.sportmonks.store import SportmonksStore

    store = SportmonksStore(base_dir=tmp_path)
    service = SportmonksDataService(store=store, collector=FakeCollector())

    result = await service.prefetch("2026-04-15", leagues=["Premier League"], refresh_stale=False)

    assert result.fixtures_found == 1
    assert result.fixtures_warmed == 1
    fixtures = store.read_fixtures("2026-04-15")
    assert len(fixtures) == 1
    assert fixtures[0]["league_name"] == "Premier League"

    snapshot = store.read_match(1, "2026-04-15")
    assert snapshot is not None
    assert snapshot["fixture_id"] == 1
    assert snapshot["home_team"] == "Arsenal"


@pytest.mark.asyncio
async def test_prefetch_uses_precise_league_mapping_for_english_premier_league(tmp_path):
    from datasource.sportmonks.store import SportmonksStore

    store = SportmonksStore(base_dir=tmp_path)
    service = SportmonksDataService(store=store, collector=AmbiguousLeagueCollector())

    result = await service.prefetch("2026-04-14", leagues=["Premier League", "Championship"], refresh_stale=False)

    assert result.fixtures_found == 2
    fixtures = store.read_fixtures("2026-04-14")
    assert len(fixtures) == 2
    assert {item["fixture_id"] for item in fixtures} == {11, 12}
    assert all(item["fixture_id"] != 10 for item in fixtures)


@pytest.mark.asyncio
async def test_get_cache_status_summarizes_date_cache(tmp_path):
    from datasource.sportmonks.store import SportmonksStore

    store = SportmonksStore(base_dir=tmp_path)
    service = SportmonksDataService(store=store, collector=FakeCollector())
    await service.prefetch("2026-04-15", leagues=["Premier League", "Serie A"], refresh_stale=False)

    status = await service.get_cache_status(date="2026-04-15")

    assert status["date"] == "2026-04-15"
    assert status["total_fixtures"] == 2
    assert status["status_counts"]["fresh"] >= 1


@pytest.mark.asyncio
async def test_refresh_match_updates_selected_layers_and_preserves_existing_snapshot(tmp_path):
    from datasource.sportmonks.store import SportmonksStore

    collector = FakeCollector()
    store = SportmonksStore(base_dir=tmp_path)
    service = SportmonksDataService(store=store, collector=collector)
    await service.prefetch("2026-04-15", leagues=["Premier League"], refresh_stale=False)

    collector.override_layers = {
        "lineups": {"home_formation": "3-4-3", "away_formation": "4-2-3-1"},
        "xg": None,
        "odds": None,
        "standings": None,
        "asian_handicap": None,
        "odds_movement": None,
        "h2h": None,
        "predictions": None,
    }

    refreshed = await service.refresh_match(
        fixture_id=1,
        date="2026-04-15",
        layers=["lineups"],
    )

    assert refreshed.lineups["home_formation"] == "3-4-3"
    assert refreshed.xg["home_xg_for"] == 1.8


@pytest.mark.asyncio
async def test_get_cache_status_returns_fixture_level_meta(tmp_path):
    from datasource.sportmonks.store import SportmonksStore

    store = SportmonksStore(base_dir=tmp_path)
    service = SportmonksDataService(store=store, collector=FakeCollector())
    await service.prefetch("2026-04-15", leagues=["Premier League"], refresh_stale=False)

    status = await service.get_cache_status(date="2026-04-15", fixture_id=1)

    assert status["fixture_id"] == 1
    assert status["cache_status"] == "fresh"
    assert status["meta"]["fixture_id"] == 1

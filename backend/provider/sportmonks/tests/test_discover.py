from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from provider.models import ProviderFixture
from provider.sportmonks.client import SportmonksProvider


def _make_fixture(fid: int, home: str, away: str, starting_at: str, league_name: str = "EPL") -> dict:
    return {
        "id": fid,
        "starting_at": starting_at,
        "participants": [
            {"name": home, "meta": {"location": "home"}},
            {"name": away, "meta": {"location": "away"}},
        ],
        "league": {"id": 8, "name": league_name},
    }


@pytest.fixture
def provider():
    p = SportmonksProvider(api_key="test-key")
    return p


@pytest.mark.asyncio
async def test_returns_provider_fixtures(provider):
    raw = _make_fixture(101, "Arsenal", "Chelsea", "2026-05-10 15:00:00")
    provider.get_fixtures_by_date = AsyncMock(return_value={"data": [raw]})

    result = await provider.discover_fixtures(league_ids=[], dates=["2026-05-10"])

    assert len(result) == 1
    pf = result[0]
    assert isinstance(pf, ProviderFixture)
    assert pf.fixture_id == 101
    assert pf.home_team == "Arsenal"
    assert pf.away_team == "Chelsea"
    assert pf.provider == "sportmonks"
    assert pf.league_name == "EPL"


@pytest.mark.asyncio
async def test_kickoff_unix_conversion(provider):
    raw = _make_fixture(102, "A", "B", "2026-05-10 15:00:00")
    provider.get_fixtures_by_date = AsyncMock(return_value={"data": [raw]})

    result = await provider.discover_fixtures(league_ids=[], dates=["2026-05-10"])

    from datetime import datetime, timezone
    expected = int(datetime(2026, 5, 10, 15, 0, 0, tzinfo=timezone.utc).timestamp())
    assert result[0].kickoff_unix == expected


@pytest.mark.asyncio
async def test_deduplication_across_dates(provider):
    raw = _make_fixture(103, "A", "B", "2026-05-10 15:00:00")
    provider.get_fixtures_by_date = AsyncMock(return_value={"data": [raw]})

    result = await provider.discover_fixtures(league_ids=[], dates=["2026-05-10", "2026-05-10"])

    assert len(result) == 1


@pytest.mark.asyncio
async def test_league_id_filter_passed_to_api(provider):
    provider.get_fixtures_by_date = AsyncMock(return_value={"data": []})

    await provider.discover_fixtures(league_ids=[8, 82], dates=["2026-05-10"])

    _, kwargs = provider.get_fixtures_by_date.call_args
    assert kwargs.get("filters") == "filterFixturesByLeagueIds:8,82"


@pytest.mark.asyncio
async def test_no_filter_when_league_ids_empty(provider):
    provider.get_fixtures_by_date = AsyncMock(return_value={"data": []})

    await provider.discover_fixtures(league_ids=[], dates=["2026-05-10"])

    _, kwargs = provider.get_fixtures_by_date.call_args
    assert kwargs.get("filters") is None


@pytest.mark.asyncio
async def test_multiple_dates_aggregated(provider):
    day1 = _make_fixture(201, "A", "B", "2026-05-10 12:00:00")
    day2 = _make_fixture(202, "C", "D", "2026-05-11 15:00:00")

    async def mock_by_date(date, include=None, filters=None):
        if date == "2026-05-10":
            return {"data": [day1]}
        return {"data": [day2]}

    provider.get_fixtures_by_date = mock_by_date

    result = await provider.discover_fixtures(league_ids=[], dates=["2026-05-10", "2026-05-11"])

    assert len(result) == 2
    ids = {pf.fixture_id for pf in result}
    assert ids == {201, 202}


@pytest.mark.asyncio
async def test_api_failure_skips_date(provider):
    provider.get_fixtures_by_date = AsyncMock(return_value=None)

    result = await provider.discover_fixtures(league_ids=[], dates=["2026-05-10"])

    assert result == []


@pytest.mark.asyncio
async def test_raw_stored_on_fixture(provider):
    raw = _make_fixture(104, "X", "Y", "2026-05-10 20:00:00")
    provider.get_fixtures_by_date = AsyncMock(return_value={"data": [raw]})

    result = await provider.discover_fixtures(league_ids=[], dates=["2026-05-10"])

    assert result[0].raw is raw

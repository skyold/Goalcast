from __future__ import annotations

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock

from provider.models import ProviderFixture
from provider.oddalerts.client import OddAlertsProvider


def _unix(date_str: str) -> int:
    return int(datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


def _trend_item(fid: int, home: str, away: str, unix: int, comp_id: int = 1, comp_name: str = "EPL") -> dict:
    return {
        "id": fid,
        "home_name": home,
        "away_name": away,
        "unix": unix,
        "competition_id": comp_id,
        "competition_name": comp_name,
    }


@pytest.fixture
def provider():
    return OddAlertsProvider(api_key="test-key")


@pytest.mark.asyncio
async def test_uses_tier1_when_between_returns_data(provider):
    fixture_unix = _unix("2026-05-10") + 54000
    item = {"id": 501, "home_name": "A", "away_name": "B", "unix": fixture_unix, "competition_id": 1, "competition_name": "EPL"}
    provider.get_fixtures_between = AsyncMock(return_value={"data": [item]})
    provider.get_trends = AsyncMock()

    result = await provider.discover_fixtures(league_ids=[], dates=["2026-05-10"])

    assert len(result) == 1
    assert result[0].fixture_id == 501
    provider.get_trends.assert_not_called()


@pytest.mark.asyncio
async def test_falls_back_to_trends_when_tier1_empty(provider):
    provider.get_fixtures_between = AsyncMock(return_value={"data": []})

    fixture_unix = _unix("2026-05-10") + 54000
    item = _trend_item(601, "Arsenal", "Chelsea", fixture_unix)
    provider.get_trends = AsyncMock(return_value={"data": [item], "meta": {"current_page": 1, "last_page": 1}})

    result = await provider.discover_fixtures(league_ids=[], dates=["2026-05-10"])

    assert len(result) == 1
    assert result[0].fixture_id == 601
    assert result[0].home_team == "Arsenal"
    assert result[0].provider == "oddalerts"


@pytest.mark.asyncio
async def test_deduplication_across_trends_markets(provider):
    provider.get_fixtures_between = AsyncMock(return_value={"data": []})

    fixture_unix = _unix("2026-05-10") + 54000
    item = _trend_item(700, "X", "Y", fixture_unix)
    provider.get_trends = AsyncMock(return_value={"data": [item], "meta": {"current_page": 1, "last_page": 1}})

    result = await provider.discover_fixtures(league_ids=[], dates=["2026-05-10"])

    # Three markets all return the same fixture — should deduplicate to 1
    assert len(result) == 1


@pytest.mark.asyncio
async def test_filters_by_league_id(provider):
    provider.get_fixtures_between = AsyncMock(return_value={"data": []})

    fixture_unix = _unix("2026-05-10") + 54000
    epl_item = _trend_item(801, "A", "B", fixture_unix, comp_id=10)
    other_item = _trend_item(802, "C", "D", fixture_unix, comp_id=99)
    provider.get_trends = AsyncMock(return_value={
        "data": [epl_item, other_item],
        "meta": {"current_page": 1, "last_page": 1},
    })

    result = await provider.discover_fixtures(league_ids=[10], dates=["2026-05-10"])

    assert len(result) == 1
    assert result[0].fixture_id == 801


@pytest.mark.asyncio
async def test_filters_outside_date_range(provider):
    provider.get_fixtures_between = AsyncMock(return_value={"data": []})

    in_range_unix = _unix("2026-05-10") + 54000
    out_of_range_unix = _unix("2026-05-12") + 54000
    items = [
        _trend_item(901, "A", "B", in_range_unix),
        _trend_item(902, "C", "D", out_of_range_unix),
    ]
    provider.get_trends = AsyncMock(return_value={"data": items, "meta": {"current_page": 1, "last_page": 1}})

    result = await provider.discover_fixtures(league_ids=[], dates=["2026-05-10"])

    assert len(result) == 1
    assert result[0].fixture_id == 901


@pytest.mark.asyncio
async def test_empty_dates_returns_empty(provider):
    result = await provider.discover_fixtures(league_ids=[], dates=[])
    assert result == []


@pytest.mark.asyncio
async def test_league_name_populated(provider):
    provider.get_fixtures_between = AsyncMock(return_value={"data": []})

    fixture_unix = _unix("2026-05-10") + 54000
    item = _trend_item(1001, "A", "B", fixture_unix, comp_name="Bundesliga")
    provider.get_trends = AsyncMock(return_value={"data": [item], "meta": {"current_page": 1, "last_page": 1}})

    result = await provider.discover_fixtures(league_ids=[], dates=["2026-05-10"])

    assert result[0].league_name == "Bundesliga"

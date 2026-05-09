import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from provider.models import ProviderFixture


def _make_fixture(provider: str, fid: int, home: str, away: str, ts: int) -> ProviderFixture:
    return ProviderFixture(
        provider=provider, fixture_id=fid,
        home_team=home, away_team=away,
        kickoff_unix=ts, league_name="Test League",
    )


@pytest.mark.asyncio
async def test_discover_merges_two_providers():
    ts = 1715000000
    prov_a = MagicMock()
    prov_a.name = "oddalerts"
    prov_a.discover_fixtures = AsyncMock(return_value=[
        _make_fixture("oddalerts", 1, "Arsenal", "Chelsea", ts),
    ])
    prov_a.close = AsyncMock()

    prov_b = MagicMock()
    prov_b.name = "sportmonks"
    prov_b.discover_fixtures = AsyncMock(return_value=[
        _make_fixture("sportmonks", 99, "Arsenal", "Chelsea", ts),
    ])
    prov_b.close = AsyncMock()

    with patch("pipeline.discovery.registry.get_active_providers", return_value=[prov_a, prov_b]):
        from pipeline.discovery import discover_fixtures
        results = await discover_fixtures(dates=["2025-05-10"])

    assert len(results) == 1
    assert results[0].provider_ids == {"oddalerts": 1, "sportmonks": 99}


@pytest.mark.asyncio
async def test_discover_no_providers_returns_empty():
    with patch("pipeline.discovery.registry.get_active_providers", return_value=[]):
        from pipeline.discovery import discover_fixtures
        results = await discover_fixtures(dates=["2025-05-10"])
    assert results == []


@pytest.mark.asyncio
async def test_discover_provider_failure_is_skipped():
    ts = 1715000000
    prov_a = MagicMock()
    prov_a.name = "oddalerts"
    prov_a.discover_fixtures = AsyncMock(side_effect=Exception("API down"))
    prov_a.close = AsyncMock()

    prov_b = MagicMock()
    prov_b.name = "sportmonks"
    prov_b.discover_fixtures = AsyncMock(return_value=[
        _make_fixture("sportmonks", 99, "Arsenal", "Chelsea", ts),
    ])
    prov_b.close = AsyncMock()

    with patch("pipeline.discovery.registry.get_active_providers", return_value=[prov_a, prov_b]):
        from pipeline.discovery import discover_fixtures
        results = await discover_fixtures(dates=["2025-05-10"])

    assert len(results) == 1
    assert "sportmonks" in results[0].provider_ids

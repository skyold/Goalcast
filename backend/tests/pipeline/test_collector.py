import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_collect_returns_data_keyed_by_provider():
    prov = MagicMock()
    prov.name = "oddalerts"
    prov.collect_match = AsyncMock(return_value={"_meta": {}, "fixture": {"id": 1}})
    prov.close = AsyncMock()

    with patch("pipeline.collector.registry.get_active_providers", return_value=[prov]):
        from pipeline.collector import collect_match_data
        result = await collect_match_data({"oddalerts": 1})

    assert "oddalerts" in result
    assert result["oddalerts"]["fixture"]["id"] == 1


@pytest.mark.asyncio
async def test_collect_skips_provider_not_in_ids():
    prov = MagicMock()
    prov.name = "sportmonks"
    prov.collect_match = AsyncMock(return_value={"_meta": {}})
    prov.close = AsyncMock()

    with patch("pipeline.collector.registry.get_active_providers", return_value=[prov]):
        from pipeline.collector import collect_match_data
        result = await collect_match_data({"oddalerts": 1})

    assert "sportmonks" not in result


@pytest.mark.asyncio
async def test_collect_provider_failure_excluded():
    prov = MagicMock()
    prov.name = "oddalerts"
    prov.collect_match = AsyncMock(side_effect=Exception("timeout"))
    prov.close = AsyncMock()

    with patch("pipeline.collector.registry.get_active_providers", return_value=[prov]):
        from pipeline.collector import collect_match_data
        result = await collect_match_data({"oddalerts": 1})

    assert result == {}

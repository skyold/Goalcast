from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from agents.core.data_collector import collect_all, collect_sportmonks, collect_oddalerts


@pytest.fixture
def executor():
    ex = MagicMock()
    ex._tool_goalcast_sportmonks_get_match = AsyncMock(
        return_value={"data": {"fixture_id": 123, "name": "A vs B"}}
    )
    return ex


@pytest.mark.asyncio
async def test_collect_all_routes_sportmonks_id(executor):
    result = await collect_all(executor, provider_ids={"sportmonks": 123})

    assert "sportmonks" in result
    executor._tool_goalcast_sportmonks_get_match.assert_awaited_once_with(fixture_id=123)


@pytest.mark.asyncio
async def test_collect_all_skips_provider_when_id_absent(executor):
    result = await collect_all(executor, provider_ids={"sportmonks": 123})

    assert "oddalerts" not in result


@pytest.mark.asyncio
async def test_collect_all_collects_oddalerts_when_id_present(executor):
    with patch("agents.core.data_collector.collect_oddalerts", new_callable=AsyncMock) as mock_oa:
        mock_oa.return_value = {"_meta": {}, "fixture": {}}
        result = await collect_all(executor, provider_ids={"sportmonks": 123, "oddalerts": 456})

    assert "oddalerts" in result
    mock_oa.assert_awaited_once_with(456)


@pytest.mark.asyncio
async def test_collect_all_empty_provider_ids(executor):
    result = await collect_all(executor, provider_ids={})
    assert result == {}


@pytest.mark.asyncio
async def test_collect_all_provider_filter(executor):
    with patch("agents.core.data_collector.collect_oddalerts", new_callable=AsyncMock) as mock_oa:
        mock_oa.return_value = {"_meta": {}}
        result = await collect_all(
            executor,
            provider_ids={"sportmonks": 123, "oddalerts": 456},
            providers=["sportmonks"],
        )

    assert "sportmonks" in result
    assert "oddalerts" not in result
    mock_oa.assert_not_awaited()


@pytest.mark.asyncio
async def test_collect_sportmonks_returns_none_on_failure():
    ex = MagicMock()
    ex._tool_goalcast_sportmonks_get_match = AsyncMock(return_value=None)
    ex._tool_goalcast_sportmonks_resolve_match = AsyncMock(return_value=None)

    result = await collect_sportmonks(ex, fixture_id=999)

    assert result is None


@pytest.mark.asyncio
async def test_collect_all_handles_provider_exception(executor):
    with patch("agents.core.data_collector.collect_oddalerts", new_callable=AsyncMock) as mock_oa:
        mock_oa.side_effect = RuntimeError("network error")
        result = await collect_all(executor, provider_ids={"sportmonks": 123, "oddalerts": 456})

    assert "sportmonks" in result
    assert "oddalerts" not in result

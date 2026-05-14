import pytest
from unittest.mock import AsyncMock, patch
from agents.core.data_collector import collect_all


@pytest.mark.asyncio
async def test_collect_all_uses_only_oddalerts():
    fake = {
        "fixture": {"id": 1, "name": "A vs B", "starting_at": "2026-05-14T20:00:00Z",
                    "participants": [
                        {"id": 11, "name": "A", "meta": {"location": "home"}},
                        {"id": 22, "name": "B", "meta": {"location": "away"}},
                    ]},
        "odds_history": {"markets": {"ft_result": {"Bet365": {
            "home": {"closing": 1.72}, "draw": {"closing": 3.85}, "away": {"closing": 4.60}
        }}}},
        "h2h": [],
        "stats_home": {"xg_for": 2.0, "goals_against_avg": 1.0},
        "stats_away": {"xg_for": 1.0, "goals_against_avg": 1.0},
        "trends": {"homeWin": 0.62, "awayWin": 0.18},
    }
    with patch("agents.core.data_collector.collect_oddalerts", AsyncMock(return_value=fake)):
        out = await collect_all(oa_fixture_id=1)
    assert out is not None
    assert out["source"] == "oddalerts"
    assert "fixture" in out and "odds_history" in out
    assert "sportmonks" not in out and "footystats" not in out


@pytest.mark.asyncio
async def test_collect_all_returns_none_when_provider_returns_none():
    with patch("agents.core.data_collector.collect_oddalerts", AsyncMock(return_value=None)):
        out = await collect_all(oa_fixture_id=1)
    assert out is None


@pytest.mark.asyncio
async def test_collect_all_returns_none_when_fixture_key_missing():
    with patch("agents.core.data_collector.collect_oddalerts", AsyncMock(return_value={"odds_history": {}})):
        out = await collect_all(oa_fixture_id=1)
    assert out is None

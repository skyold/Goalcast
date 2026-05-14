import pytest
from unittest.mock import AsyncMock, patch
from agents.core.data_collector import collect_all


@pytest.mark.asyncio
async def test_collect_all_attaches_analysis():
    bundle = {
        "fixture": {"id": 1, "name": "A vs B", "starting_at": "2026-05-14T20:00:00Z",
                    "participants": [
                        {"id": 11, "name": "A", "meta": {"location": "home"}},
                        {"id": 22, "name": "B", "meta": {"location": "away"}},
                    ], "league": {"id": 8, "name": "PL"}},
        "odds_history": {"markets": {"ft_result": {"Bet365": {
            "home": {"closing": 1.72}, "draw": {"closing": 3.85}, "away": {"closing": 4.60}}}}},
        "h2h": [],
        "stats_home": {"xg_for": 2.0, "goals_against_avg": 1.0},
        "stats_away": {"xg_for": 1.0, "goals_against_avg": 1.0},
        "trends": {"homeWin": 0.62, "awayWin": 0.18},
    }
    with patch("agents.core.data_collector.collect_oddalerts", AsyncMock(return_value=bundle)):
        out = await collect_all(oa_fixture_id=1)
    assert out["analysis"] is not None
    a = out["analysis"]
    assert "model_prob" in a and "H" in a["model_prob"]
    assert "ev" in a and "kelly" in a
    assert a["confidence_stars"] >= 0
    assert a["pick"] in ("H", "D", "A")
    assert isinstance(a["ev"], float)
    assert isinstance(a["kelly"], float)
    assert isinstance(a["odds"], (int, float))
    assert "market_prob" in a and set(a["market_prob"].keys()) == {"H", "D", "A"}
    assert a["analyzed_at"]  # non-empty ISO string
    assert a["analyst_summary"] is None
    assert a["reviewer_verdict"] is None
    assert a["run_id"] is None

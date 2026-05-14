import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_one_rd_cycle_writes_match_store(tmp_path, monkeypatch):
    # Redirect match_store output to tmp
    from agents.core import match_store
    monkeypatch.setattr(match_store, "MATCHES_DIR", tmp_path / "matches")

    bundle = {
        "fixture": {
            "id": 1,
            "name": "A vs B",
            "starting_at": "2026-05-14T20:00:00Z",
            "participants": [
                {"id": 11, "name": "A", "meta": {"location": "home"}},
                {"id": 22, "name": "B", "meta": {"location": "away"}},
            ],
            "league": {"id": 8, "name": "PL"},
        },
        "odds_history": {
            "markets": {
                "ft_result": {
                    "Bet365": {
                        "home": {"closing": 1.72},
                        "draw": {"closing": 3.85},
                        "away": {"closing": 4.60},
                    }
                }
            }
        },
        "h2h": [],
        "stats_home": {"xg_for": 2.0, "goals_against_avg": 1.0},
        "stats_away": {"xg_for": 1.0, "goals_against_avg": 1.0},
        "trends": {"homeWin": 0.62, "awayWin": 0.18},
    }

    with patch(
        "provider.oddalerts.client.OddAlertsProvider.collect_fixture_data",
        AsyncMock(return_value=bundle),
    ), patch(
        "provider.oddalerts.client.OddAlertsProvider.get_dropping_odds",
        AsyncMock(
            return_value={
                "data": [
                    {
                        "id": 1,
                        "drop_percentage": -8.0,
                        "starting_at": "2026-05-14T20:00:00Z",
                        "league": {"id": 8, "name": "PL"},
                    }
                ]
            }
        ),
    ):
        from agents.core.orchestrator import Orchestrator
        orch = Orchestrator()
        result = await orch.run_once()
        assert result["processed"] == 1

    recent = match_store.list_recent(limit=10)
    assert len(recent) >= 1
    assert recent[0].get("analysis") is not None

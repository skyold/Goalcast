import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.core.events import EventEmitter


@pytest.mark.asyncio
async def test_event_emitter_continues_when_one_subscriber_fails():
    received = []
    emitter = EventEmitter()

    async def broken(_event_name: str, _payload: dict):
        raise RuntimeError("socket already closed")

    async def healthy(event_name: str, payload: dict):
        received.append((event_name, payload))

    emitter.subscribe(broken)
    emitter.subscribe(healthy)

    await emitter.emit("pipeline_start", {"message": "ok"})

    assert received == [("pipeline_start", {"message": "ok"})]


@pytest.mark.asyncio
async def test_event_emitter_unsubscribe_removes_callback():
    received = []
    emitter = EventEmitter()

    async def callback(event_name: str, payload: dict):
        received.append((event_name, payload))

    emitter.subscribe(callback)
    emitter.unsubscribe(callback)

    await emitter.emit("matches_found", {"total": 1})

    assert received == []


@pytest.mark.asyncio
async def test_fetch_and_prepare_emits_renderable_matches(tmp_path, monkeypatch):
    from agents.core import match_store, orchestrator

    monkeypatch.setattr(match_store, "MATCHES_DIR", tmp_path)

    class FakeExecutor:
        async def _tool_goalcast_sportmonks_get_matches(self, date=None, league_ids=None):
            return {
                "ok": True,
                "count": 1,
                "data": [
                    {
                        "fixture_id": 101,
                        "home_team": "Man City",
                        "away_team": "Arsenal",
                        "league": "Premier League",
                        "starting_at": "2026-04-30T19:00:00+08:00",
                    }
                ],
            }

        async def _tool_goalcast_sportmonks_get_match(self, fixture_id, match_date=None):
            return {"ok": True, "data": {"fixture_id": fixture_id, "odds": []}}

    emitted = []
    emitter = EventEmitter()

    async def track(name: str, payload: dict):
        emitted.append((name, payload))

    emitter.subscribe(track)

    orch = orchestrator.Orchestrator(adapter=AsyncMock(), emitter=emitter)

    monkeypatch.setattr(
        "agents.adapters.tool_executor.ToolExecutor",
        lambda: FakeExecutor(),
    )

    count = await orch._fetch_and_prepare(leagues=None, date="2026-04-30", models=["v4.0"])

    assert count == 1
    event_name, payload = emitted[-1]
    assert event_name == "matches_found"
    assert payload["total"] == 1
    assert len(payload["matches"]) == 1
    assert payload["matches"][0]["home_team"] == "Man City"
    assert payload["matches"][0]["away_team"] == "Arsenal"
    assert payload["matches"][0]["match_id"].startswith("MC-")


@pytest.mark.asyncio
async def test_trader_loop_emits_match_result_ready(monkeypatch):
    from agents.core import orchestrator

    emitted = []
    emitter = EventEmitter()

    async def track(name: str, payload: dict):
        emitted.append((name, payload))

    emitter.subscribe(track)

    orch = orchestrator.Orchestrator(adapter=AsyncMock(), emitter=emitter)
    orch.pipeline.run_trader_step = AsyncMock(
        return_value={
            "recommendation": "Home -0.5",
            "ev": 1.08,
            "predictions": {"home_win": 0.55, "draw": 0.24, "away_win": 0.21},
        }
    )

    records = [{"match_id": "MC-TEST-TRADER"}]

    def fake_claim_oldest(_statuses, _new_status):
        if records:
            return records.pop(0)
        return None

    async def fake_sleep(_seconds: float):
        orch.stop_event.set()

    monkeypatch.setattr(orchestrator.match_store, "claim_oldest", fake_claim_oldest)
    monkeypatch.setattr(orch, "_sleep", fake_sleep)

    await orch._trader_loop()

    event_names = [name for name, _payload in emitted]
    assert "match_step_start" in event_names
    assert "match_result_ready" in event_names

    ready_payload = next(payload for name, payload in emitted if name == "match_result_ready")
    assert ready_payload["match_id"] == "MC-TEST-TRADER"
    assert ready_payload["recommendation"] == "Home -0.5"
    assert ready_payload["ev"] == 1.08

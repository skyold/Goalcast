import asyncio
import importlib
import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.mark.asyncio
async def test_orchestrator_run_returns_promptly_when_no_matches(tmp_path, monkeypatch):
    from agents.core import match_store
    from agents.core.orchestrator import Orchestrator

    monkeypatch.setattr(match_store, "MATCHES_DIR", tmp_path)

    orch = Orchestrator(adapter=AsyncMock())
    orch._fetch_and_prepare = AsyncMock(return_value=0)

    result = await asyncio.wait_for(
        orch.run(leagues=["Premier League"], date="2026-04-29"),
        timeout=0.1,
    )

    assert result["prepared"] == 0
    assert result["reviewed"] == 0
    assert result["reported"] == 0


@pytest.mark.asyncio
async def test_orchestrator_run_aborts_stale_active_matches(tmp_path, monkeypatch):
    from agents.core import match_store
    from agents.core.orchestrator import Orchestrator

    monkeypatch.setattr(match_store, "MATCHES_DIR", tmp_path)
    match_store.save(
        {
            "match_id": "MC-STALE-001",
            "status": "pending",
            "orchestrator": {"prepared_at": "2026-04-29T10:00:00+08:00"},
        }
    )

    orch = Orchestrator(adapter=AsyncMock())
    orch._fetch_and_prepare = AsyncMock(return_value=0)

    result = await asyncio.wait_for(
        orch.run(leagues=["Premier League"], date="2026-04-29"),
        timeout=0.1,
    )

    assert result["prepared"] == 0
    assert match_store.load("MC-STALE-001")["status"] == "aborted"


@pytest.mark.asyncio
async def test_fetch_raw_data_uses_sportmonks_get_match():
    from agents.core.orchestrator import Orchestrator

    class FakeExecutor:
        async def _tool_goalcast_sportmonks_get_match(self, fixture_id, match_date=None):
            return {"ok": True, "data": {"fixture_id": fixture_id, "source": "sportmonks"}}

    orch = Orchestrator(adapter=AsyncMock())
    raw_data = await orch._fetch_raw_data_for_models(FakeExecutor(), 12345, ["v4.0"])

    assert raw_data["sportmonks"]["fixture_id"] == 12345
    assert raw_data["sportmonks"]["source"] == "sportmonks"


@pytest.mark.asyncio
async def test_orchestrator_run_completes_with_small_reviewed_batch(tmp_path, monkeypatch):
    from agents.core import match_store, orchestrator

    monkeypatch.setattr(match_store, "MATCHES_DIR", tmp_path)

    match_store.save(
        {
            "match_id": "MC-REVIEWED-1",
            "status": "reviewed",
            "review": {"verdict": "approved"},
        }
    )

    orch = orchestrator.Orchestrator(adapter=AsyncMock())
    orch._fetch_and_prepare = AsyncMock(return_value=0)
    orch._analyst_loop = AsyncMock(return_value=None)
    orch._trader_loop = AsyncMock(return_value=None)
    orch._reviewer_loop = AsyncMock(return_value=None)

    async def fake_reporter(match_ids):
        for match_id in match_ids:
            match_store.finalize(match_id, report_ref="reports/test.md")
        return "reports/test.md"

    orch.pipeline.run_reporter_step = AsyncMock(side_effect=fake_reporter)

    result = await asyncio.wait_for(
        orch.run(leagues=None, date="2026-04-29"),
        timeout=0.1,
    )

    assert result["reported"] == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method_name", "expected_role"),
    [
        ("run_analyst_step", "agents/roles/analyst"),
        ("run_trader_step", "agents/roles/trader"),
        ("run_reviewer_step", "agents/roles/reviewer"),
        ("run_reporter_step", "agents/roles/reporter"),
    ],
)
async def test_pipeline_uses_full_role_paths(method_name, expected_role, tmp_path, monkeypatch):
    from agents.adapters.adapter import AgentResult
    from agents.core import match_store
    from agents.core.pipeline import MatchPipeline

    monkeypatch.setattr(match_store, "MATCHES_DIR", tmp_path)

    class FakeAdapter:
        def __init__(self):
            self.calls = []

        async def run_agent(self, role_path, user_message, context=None):
            self.calls.append(role_path)
            if role_path.endswith("reviewer"):
                return AgentResult(role_path, "VERDICT: approved", [], 1)
            if role_path.endswith("reporter"):
                return AgentResult(role_path, "# Report", [], 1)
            return AgentResult(role_path, "{}", [], 1)

    match_id = "MC-FULL-PATH"
    match_store.save(
        {
            "match_id": match_id,
            "status": "traded",
            "metadata": {
                "match_id": match_id,
                "requested_models": ["v4.0"],
                "home_team": "A",
                "away_team": "B",
                "league": "L",
                "kickoff_time": "2026-04-30T19:00:00+08:00",
            },
            "raw_data": {"sportmonks": {"fixture_id": 1}},
            "analysis": {"v4.0": {"home_xg": 1.2}},
            "trading": {"results": {"recommendation": "Home -0.25"}},
            "review": {"verdict": "approved"},
        }
    )

    adapter = FakeAdapter()
    pipeline = MatchPipeline(adapter)

    if method_name == "run_analyst_step":
        match_store.update_status(match_id, "pending")
        await pipeline.run_analyst_step({"match_id": match_id})
    elif method_name == "run_trader_step":
        match_store.update_status(match_id, "analyzed")
        await pipeline.run_trader_step({"match_id": match_id})
    elif method_name == "run_reviewer_step":
        await pipeline.run_reviewer_step({"match_id": match_id})
    else:
        await pipeline.run_reporter_step([match_id])

    assert adapter.calls[0] == expected_role


@pytest.mark.asyncio
async def test_handle_user_request_passes_models_to_orchestrator(monkeypatch):
    fake_fastapi = types.ModuleType("fastapi")

    class FakeFastAPI:
        def websocket(self, _path):
            def decorator(func):
                return func
            return decorator

    fake_fastapi.FastAPI = FakeFastAPI
    fake_fastapi.WebSocket = object

    class FakeWebSocketDisconnect(Exception):
        pass

    fake_fastapi.WebSocketDisconnect = FakeWebSocketDisconnect

    fake_adapter_module = types.ModuleType("agents.adapters.adapter")

    class FakeClaudeAdapter:
        pass

    fake_adapter_module.ClaudeAdapter = FakeClaudeAdapter

    fake_intent_module = types.ModuleType("agents.web.intent")

    async def fake_parse_intent(_text, _adapter):
        return {"leagues": ["Premier League"], "date": "2026-04-29", "models": ["v3.0", "v4.0"]}

    fake_intent_module.parse_intent = fake_parse_intent

    fake_orch_module = types.ModuleType("agents.core.orchestrator")
    captured = {}

    class FakeOrchestrator:
        def __init__(self, adapter=None, semi_mode=False, emitter=None):
            captured["adapter"] = adapter
            captured["semi_mode"] = semi_mode
            captured["emitter"] = emitter

        async def run(self, leagues=None, date=None, max_matches=None, models=None):
            captured["run"] = {
                "leagues": leagues,
                "date": date,
                "max_matches": max_matches,
                "models": models,
            }
            return {"prepared": 0, "reviewed": 0, "reported": 0}

    fake_orch_module.Orchestrator = FakeOrchestrator

    monkeypatch.setitem(sys.modules, "fastapi", fake_fastapi)
    monkeypatch.setitem(sys.modules, "agents.adapters.adapter", fake_adapter_module)
    monkeypatch.setitem(sys.modules, "agents.web.intent", fake_intent_module)
    monkeypatch.setitem(sys.modules, "agents.core.orchestrator", fake_orch_module)
    sys.modules.pop("agents.web.server", None)

    server = importlib.import_module("agents.web.server")

    class DummyEmitter:
        async def emit(self, _name, _payload):
            return None

    await server.handle_user_request("分析今天英超", DummyEmitter())

    assert captured["run"]["models"] == ["v3.0", "v4.0"]

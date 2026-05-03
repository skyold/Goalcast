import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.adapters.adapter import AgentResult


class FakeAdapter:
    def __init__(self):
        self.run_agent = AsyncMock(return_value=AgentResult("x", "{}", [], 1))


class FakeExecutor:
    def __init__(self, fixtures=None):
        self.fixtures = fixtures or []

    async def _tool_goalcast_sportmonks_get_matches(self, date=None, league_ids=None):
        return {"ok": True, "count": len(self.fixtures), "data": self.fixtures}


class TestOrchestratorInit:
    def test_init_creates_pipeline(self):
        from agents.core.orchestrator import Orchestrator

        orch = Orchestrator(FakeAdapter())
        assert orch.adapter is not None
        assert orch.pipeline is not None
        assert orch.semi_mode is False

    def test_semi_mode(self):
        from agents.core.orchestrator import Orchestrator

        orch = Orchestrator(FakeAdapter(), semi_mode=True)
        assert orch.semi_mode is True


class TestResolveLeagueIds:
    def test_returns_none_when_file_missing(self, monkeypatch):
        from agents.core import orchestrator

        monkeypatch.setattr(
            orchestrator, "LEAGUES_JSON_PATH",
            Path("/nonexistent/path/leagues.json"),
        )
        orch = orchestrator.Orchestrator(FakeAdapter())
        result = orch._resolve_league_ids(["英超"])
        assert result is None

    def test_returns_ids_from_dict_style_leagues(self, tmp_path):
        from agents.core import orchestrator

        test_json = tmp_path / "sportmonks_leagues.json"
        test_json.write_text(json.dumps({
            "Premier League": {"id": 8, "name": "Premier League"},
        }), encoding="utf-8")
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr(orchestrator, "LEAGUES_JSON_PATH", test_json)

        orch = orchestrator.Orchestrator(FakeAdapter())
        result = orch._resolve_league_ids(["英超"])

    def test_fuzzy_name_matching(self, tmp_path, monkeypatch):
        from agents.core import orchestrator

        test_json = tmp_path / "leagues.json"
        test_json.write_text(json.dumps({
            "Premier League": {"id": 8},
            "La Liga": {"id": 564},
        }), encoding="utf-8")
        monkeypatch.setattr(orchestrator, "LEAGUES_JSON_PATH", test_json)

        orch = orchestrator.Orchestrator(FakeAdapter())
        result = orch._resolve_league_ids(["premier"])
        assert result == [8]

        result2 = orch._resolve_league_ids(["Premier League", "liga"])
        assert sorted(result2) == [8, 564]

    def test_no_match_returns_none(self, tmp_path, monkeypatch):
        from agents.core import orchestrator

        test_json = tmp_path / "leagues.json"
        test_json.write_text(json.dumps({
            "Premier League": {"id": 8},
        }), encoding="utf-8")
        monkeypatch.setattr(orchestrator, "LEAGUES_JSON_PATH", test_json)

        orch = orchestrator.Orchestrator(FakeAdapter())
        result = orch._resolve_league_ids(["中超"])
        assert result is None

    def test_uses_fallback_league_path_when_primary_missing(self, tmp_path, monkeypatch):
        from agents.core import orchestrator

        fallback_json = tmp_path / "skills_leagues.json"
        fallback_json.write_text(json.dumps({
            "8": {"id": 8, "name": "Premier League"},
        }), encoding="utf-8")

        monkeypatch.setattr(
            orchestrator,
            "LEAGUES_JSON_CANDIDATE_PATHS",
            [Path("/nonexistent/primary.json"), fallback_json],
        )

        orch = orchestrator.Orchestrator(FakeAdapter())
        result = orch._resolve_league_ids(["Premier League"])

        assert result == [8]

    def test_accepts_numeric_league_ids_directly(self, tmp_path, monkeypatch):
        from agents.core import orchestrator

        test_json = tmp_path / "leagues.json"
        test_json.write_text(json.dumps({
            "Premier League": {"id": 8},
        }), encoding="utf-8")
        monkeypatch.setattr(orchestrator, "LEAGUES_JSON_PATH", test_json)
        monkeypatch.setattr(orchestrator, "LEAGUES_JSON_CANDIDATE_PATHS", None)

        orch = orchestrator.Orchestrator(FakeAdapter())
        assert orch._resolve_league_ids([8]) == [8]
        assert orch._resolve_league_ids(["8"]) == [8]


@pytest.mark.asyncio
class TestFetchAndPrepare:
    async def test_returns_zero_when_league_not_found(self, tmp_path, monkeypatch):
        from agents.core import orchestrator

        test_json = tmp_path / "leagues.json"
        test_json.write_text(json.dumps({"Premier League": {"id": 8}}), encoding="utf-8")
        monkeypatch.setattr(orchestrator, "LEAGUES_JSON_PATH", test_json)

        orch = orchestrator.Orchestrator(FakeAdapter())
        orch._resolve_league_ids = lambda leagues: None

        result = await orch._fetch_and_prepare(["中超"], "2026-04-28")
        assert result == 0

    async def test_saves_fixtures_to_match_store(self, tmp_path, monkeypatch):
        from agents.core import orchestrator, match_store

        test_json = tmp_path / "leagues.json"
        test_json.write_text(json.dumps({"Premier League": {"id": 8}}), encoding="utf-8")
        monkeypatch.setattr(orchestrator, "LEAGUES_JSON_PATH", test_json)
        monkeypatch.setattr(match_store, "MATCHES_DIR", tmp_path)

        orch = orchestrator.Orchestrator(FakeAdapter())
        orch._resolve_league_ids = lambda leagues: [8]

        mock_executor = FakeExecutor(fixtures=[
            {
                "fixture_id": 100,
                "home_team": "Man City",
                "away_team": "Arsenal",
                "league": "Premier League",
                "starting_at": "2026-04-30T19:00:00+08:00",
            },
            {
                "fixture_id": 200,
                "home_team": "Liverpool",
                "away_team": "Chelsea",
                "league": "Premier League",
                "starting_at": "2026-04-30T21:00:00+08:00",
            },
        ])

        with patch(
            "agents.adapters.tool_executor.ToolExecutor",
            return_value=mock_executor,
        ):
            result = await orch._fetch_and_prepare(["英超"], "2026-04-28")

        assert result == 2
        all_matches = match_store.list_all()
        assert len(all_matches) == 2
        assert all(m["status"] == "pending" for m in all_matches)
        home_teams = sorted(m["orchestrator"]["home_team"] for m in all_matches)
        assert home_teams == ["Liverpool", "Man City"]


class TestRunStandalone:
    @pytest.mark.asyncio
    async def test_delegates_to_adapter(self):
        from agents.core.orchestrator import run_standalone

        adapter = FakeAdapter()
        result = await run_standalone(adapter, "analyst", "分析比赛")

        adapter.run_agent.assert_called_once_with("analyst", "分析比赛")


class TestOrchestratorLoops:
    @pytest.mark.asyncio
    async def test_analyst_loop_claims_and_processes(self, tmp_path, monkeypatch):
        from agents.core import orchestrator, match_store

        monkeypatch.setattr(match_store, "MATCHES_DIR", tmp_path)

        record = {
            "schema_version": "1.0",
            "match_id": "MC-LOOP-001",
            "status": "pending",
            "orchestrator": {
                "home_team": "A", "away_team": "B", "league": "L",
                "fixture_id": 1, "prepared_at": "2026-04-28T10:00:00+08:00",
            },
        }
        match_store.save(record)

        adapter = FakeAdapter()
        adapter.run_agent.return_value = AgentResult(
            "analyst",
            '{"home_xg":1.5,"away_xg":1.0,"confidence":80}',
            [],
            1,
        )
        orch = orchestrator.Orchestrator(adapter)

        async def run_once():
            claimed = match_store.claim_oldest(["pending"], "analyzing")
            if claimed:
                await orch.pipeline.run_analyst_step(claimed)
            orch.stop_event.set()

        await run_once()

        updated = match_store.load("MC-LOOP-001")
        assert updated["status"] == "analyzed"
        assert updated["analysis"]["home_xg"] == 1.5

    @pytest.mark.asyncio
    async def test_analyst_loop_error_reverts_status(self, tmp_path, monkeypatch):
        from agents.core import orchestrator, match_store

        monkeypatch.setattr(match_store, "MATCHES_DIR", tmp_path)

        record = {
            "schema_version": "1.0",
            "match_id": "MC-LOOP-ERR",
            "status": "pending",
            "orchestrator": {
                "home_team": "A", "away_team": "B", "league": "L",
                "fixture_id": 1, "prepared_at": "2026-04-28T10:00:00+08:00",
            },
        }
        match_store.save(record)

        adapter = FakeAdapter()
        adapter.run_agent.side_effect = RuntimeError("LLM 调用失败")
        orch = orchestrator.Orchestrator(adapter)
        orch.stop_event.set()

        await orch._analyst_loop()

        updated = match_store.load("MC-LOOP-ERR")
        assert updated["status"] == "pending"

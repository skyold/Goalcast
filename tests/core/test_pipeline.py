import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.core.pipeline import MatchPipeline
from agents.adapters.adapter import AgentResult


class FakeAdapter:
    def __init__(self, responses=None):
        self.responses = responses or {}
        self.calls = []

    async def run_agent(self, role_path, user_message, context=None):
        self.calls.append({
            "role_path": role_path,
            "user_message": user_message,
        })
        return self.responses.get(role_path, AgentResult(role_path, "{}", [], 1))


def _sample_record(match_id="MC-TEST-001", status="pending"):
    return {
        "match_id": match_id,
        "status": status,
        "orchestrator": {
            "home_team": "Man City",
            "away_team": "Arsenal",
            "league": "Premier League",
            "data_source": "sportmonks",
            "model_version": "v4.0",
            "kickoff_time": "2026-04-30T19:00:00+08:00",
            "fixture_id": 12345,
        },
    }


@pytest.fixture
def tmp_matches_dir(monkeypatch):
    with tempfile.TemporaryDirectory() as td:
        from agents.core import match_store
        monkeypatch.setattr(match_store, "MATCHES_DIR", Path(td))
        yield td


class TestParseAnalysisOutput:
    def test_parses_valid_json(self):
        p = MatchPipeline(FakeAdapter())
        text = 'some text before {"home_xg":1.8,"away_xg":1.1,"confidence":78} after'
        result = p._parse_analysis_output(text, {})
        assert result["home_xg"] == 1.8
        assert result["away_xg"] == 1.1
        assert result["confidence"] == 78

    def test_fallback_on_invalid_json(self):
        p = MatchPipeline(FakeAdapter())
        text = "no json here"
        result = p._parse_analysis_output(text, {})
        assert result["home_xg"] == 0.0
        assert result["away_xg"] == 0.0
        assert result["note"].startswith("failed")

    def test_fallback_on_malformed_json(self):
        p = MatchPipeline(FakeAdapter())
        text = '{"home_xg": 1.8, broken'
        result = p._parse_analysis_output(text, {})
        assert result["note"].startswith("failed")


class TestParseTradeOutput:
    def test_parses_valid_json(self):
        p = MatchPipeline(FakeAdapter())
        text = '{"direction":"home","stake":2.5,"ah_line":-0.5}'
        result = p._parse_trade_output(text)
        assert result["direction"] == "home"
        assert result["stake"] == 2.5

    def test_fallback_on_invalid(self):
        p = MatchPipeline(FakeAdapter())
        result = p._parse_trade_output("not json")
        assert result["note"].startswith("failed")


class TestParseVerdict:
    def test_approved_from_english(self):
        p = MatchPipeline(FakeAdapter())
        assert p._parse_verdict("VERDICT: approved") == "approved"

    def test_feedback_from_english(self):
        p = MatchPipeline(FakeAdapter())
        assert p._parse_verdict("VERDICT: feedback\nissues: ...") == "feedback"

    def test_rejected_from_english(self):
        p = MatchPipeline(FakeAdapter())
        assert p._parse_verdict("VERDICT: rejected") == "rejected"

    def test_approved_case_insensitive(self):
        p = MatchPipeline(FakeAdapter())
        assert p._parse_verdict("Verdict: APPROVED") == "approved"

    def test_approved_from_chinese(self):
        p = MatchPipeline(FakeAdapter())
        assert p._parse_verdict("审核通过，各项指标正常") == "approved"

    def test_feedback_from_chinese(self):
        p = MatchPipeline(FakeAdapter())
        assert p._parse_verdict("建议打回，修正凯利注额") == "feedback"

    def test_defaults_to_rejected_when_unclear(self):
        p = MatchPipeline(FakeAdapter())
        assert p._parse_verdict("无法确定") == "rejected"


class TestBuildAnalystPrompt:
    def test_contains_key_fields(self):
        p = MatchPipeline(FakeAdapter())
        prompt = p._build_analyst_prompt({
            "home_team": "Man City",
            "away_team": "Arsenal",
            "league": "Premier League",
            "fixture_id": 12345,
            "model_version": "v4.0",
        })
        assert "Man City vs Arsenal" in prompt
        assert "Premier League" in prompt
        assert "12345" in prompt
        assert "goalcast_sportmonks_get_match" in prompt
        assert "goalcast_calculate_poisson" in prompt

    def test_defaults_model_version(self):
        p = MatchPipeline(FakeAdapter())
        prompt = p._build_analyst_prompt({
            "home_team": "A", "away_team": "B", "league": "L",
        })
        assert "v4.0" in prompt


@pytest.mark.asyncio
class TestRunAnalystStep:
    async def test_runs_and_appends_layer(self, tmp_matches_dir):
        from agents.core import match_store

        record = _sample_record("MC-TEST-A1")
        match_store.save(record)

        adapter = FakeAdapter({
            "analyst": AgentResult(
                "analyst",
                '{"home_xg":1.8,"away_xg":1.1,"confidence":78}',
                [],
                1,
            ),
        })
        p = MatchPipeline(adapter)
        result = await p.run_analyst_step(record)

        assert result["home_xg"] == 1.8
        assert result["away_xg"] == 1.1
        assert "analyzed_at" in result

        updated = match_store.load("MC-TEST-A1")
        assert updated["status"] == "analyzed"
        assert updated["analysis"]["home_xg"] == 1.8

    async def test_fallback_on_bad_output(self, tmp_matches_dir):
        from agents.core import match_store

        record = _sample_record("MC-TEST-A2")
        match_store.save(record)

        adapter = FakeAdapter({
            "analyst": AgentResult("analyst", "garbage output no json", [], 1),
        })
        p = MatchPipeline(adapter)
        result = await p.run_analyst_step(record)

        assert result["home_xg"] == 0.0
        assert result["note"].startswith("failed")

        updated = match_store.load("MC-TEST-A2")
        assert updated["status"] == "analyzed"


@pytest.mark.asyncio
class TestRunTraderStep:
    async def test_runs_and_appends_trade_layer(self, tmp_matches_dir):
        from agents.core import match_store

        record = _sample_record("MC-TEST-T1", "analyzed")
        record["analysis"] = {"home_xg": 1.8, "away_xg": 1.1}
        match_store.save(record)

        adapter = FakeAdapter({
            "trader": AgentResult(
                "trader",
                '{"direction":"home","stake":2.5,"ah_line":-0.5}',
                [],
                1,
            ),
        })
        p = MatchPipeline(adapter)
        result = await p.run_trader_step(record)

        assert result["direction"] == "home"
        assert result["stake"] == 2.5
        assert "traded_at" in result

        updated = match_store.load("MC-TEST-T1")
        assert updated["status"] == "traded"
        assert updated["trade"]["direction"] == "home"

    async def test_fallback_on_bad_output(self, tmp_matches_dir):
        from agents.core import match_store

        record = _sample_record("MC-TEST-T2", "analyzed")
        record["analysis"] = {"home_xg": 1.0}
        match_store.save(record)

        adapter = FakeAdapter({
            "trader": AgentResult("trader", "no json", [], 1),
        })
        p = MatchPipeline(adapter)
        result = await p.run_trader_step(record)

        assert result["note"].startswith("failed")
        updated = match_store.load("MC-TEST-T2")
        assert updated["status"] == "traded"


@pytest.mark.asyncio
class TestRunReviewerStep:
    async def test_approved_writes_review_and_stays_reviewed(self, tmp_matches_dir):
        from agents.core import match_store

        record = _sample_record("MC-TEST-R1", "traded")
        record["analysis"] = {"home_xg": 1.8}
        record["trade"] = {"direction": "home", "stake": 2.5}
        match_store.save(record)

        adapter = FakeAdapter({
            "reviewer": AgentResult(
                "reviewer",
                "VERDICT: approved\n一切正常",
                [],
                1,
            ),
        })
        p = MatchPipeline(adapter)
        verdict = await p.run_reviewer_step(record)

        assert verdict == "approved"
        updated = match_store.load("MC-TEST-R1")
        assert updated["status"] == "reviewed"
        assert updated["review"]["verdict"] == "approved"

    async def test_feedback_sets_status_to_feedback(self, tmp_matches_dir):
        from agents.core import match_store

        record = _sample_record("MC-TEST-R2", "traded")
        record["analysis"] = {"home_xg": 0.5}
        record["trade"] = {"direction": "home", "stake": 10}
        match_store.save(record)

        adapter = FakeAdapter({
            "reviewer": AgentResult(
                "reviewer",
                "VERDICT: feedback\n注额过高",
                [],
                1,
            ),
        })
        p = MatchPipeline(adapter)
        verdict = await p.run_reviewer_step(record)

        assert verdict == "feedback"
        updated = match_store.load("MC-TEST-R2")
        assert updated["status"] == "feedback"

    async def test_rejected_sets_status_to_rejected(self, tmp_matches_dir):
        from agents.core import match_store

        record = _sample_record("MC-TEST-R3", "traded")
        record["analysis"] = {}
        record["trade"] = {}
        match_store.save(record)

        adapter = FakeAdapter({
            "reviewer": AgentResult(
                "reviewer", "VERDICT: rejected", [], 1,
            ),
        })
        p = MatchPipeline(adapter)
        verdict = await p.run_reviewer_step(record)

        assert verdict == "rejected"
        updated = match_store.load("MC-TEST-R3")
        assert updated["status"] == "rejected"


@pytest.mark.asyncio
class TestRunReporterStep:
    async def test_generates_report_and_finalizes(self, tmp_matches_dir):
        from agents.core import match_store

        record = _sample_record("MC-TEST-RP1", "reviewed")
        record["analysis"] = {"home_xg": 1.8, "away_xg": 1.1}
        record["trade"] = {"direction": "home", "stake": 2.5}
        record["review"] = {"verdict": "approved"}
        match_store.save(record)

        adapter = FakeAdapter({
            "reporter": AgentResult(
                "reporter",
                "# Match Report\n## Analysis\nGood game",
                [],
                1,
            ),
        })
        p = MatchPipeline(adapter)
        ref = await p.run_reporter_step(["MC-TEST-RP1"])

        assert "reports/" in ref
        updated = match_store.load("MC-TEST-RP1")
        assert updated["status"] == "reported"
        assert updated["report_ref"] == ref

    async def test_filters_out_non_approved(self, tmp_matches_dir):
        from agents.core import match_store

        r1 = _sample_record("MC-TEST-RP2", "reviewed")
        r1["analysis"] = {"home_xg": 1.0}
        r1["trade"] = {"direction": "home"}
        r1["review"] = {"verdict": "approved"}
        match_store.save(r1)

        r2 = _sample_record("MC-TEST-RP3", "reviewed")
        r2["analysis"] = {"home_xg": 0.5}
        r2["trade"] = {"direction": "away"}
        r2["review"] = {"verdict": "feedback"}
        match_store.save(r2)

        adapter = FakeAdapter({
            "reporter": AgentResult("reporter", "# Report", [], 1),
        })
        p = MatchPipeline(adapter)
        ref = await p.run_reporter_step(["MC-TEST-RP2", "MC-TEST-RP3"])

        assert "reports/" in ref
        updated_approved = match_store.load("MC-TEST-RP2")
        assert updated_approved["status"] == "reported"
        updated_feedback = match_store.load("MC-TEST-RP3")
        assert updated_feedback["status"] == "reviewed"

    async def test_returns_empty_when_no_records_found(self, tmp_matches_dir):
        p = MatchPipeline(FakeAdapter())
        ref = await p.run_reporter_step(["MC-NONEXISTENT"])
        assert ref == ""

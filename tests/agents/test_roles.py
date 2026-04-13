import pytest
from agents.core.state import WorkflowState
from agents.roles.gatherer import DataGatherer
from data_strategy.models import MatchContext

@pytest.mark.asyncio
async def test_gatherer_agent(monkeypatch):
    class MockFusion:
        async def resolve_match(self, match_id):
            return MatchContext(
                data_provider="mock", match_id=match_id, league="Mock",
                home_team="A", home_team_id="1", away_team="B", away_team_id="2",
                season_id="1", match_date="2026-01-01",
                xg=None, home_form_5=None, home_form_10=None, away_form_5=None, away_form_10=None,
                form_source="", form_quality=0.0, home_standing=None, away_standing=None,
                total_teams=20, standings_source="", standings_quality=0.0, odds=None,
                lineups=None, odds_movement=None, head_to_head=None,
                data_gaps=(), overall_quality=1.0, sources={}, resolved_at=0.0
            )
            
    monkeypatch.setattr("agents.roles.gatherer.DataFusion", MockFusion)
    
    state = WorkflowState(task_id="t1", metadata={"match_ids": ["m1", "m2"]})
    gatherer = DataGatherer("gatherer")
    new_state = await gatherer.execute(state)
    
    assert new_state.current_step == "GATHER_DATA"
    assert len(new_state.match_contexts) == 2
    assert new_state.match_contexts[0].match_id == "m1"

from agents.roles.analyst import Analyst

@pytest.mark.asyncio
async def test_analyst_agent(monkeypatch):
    async def mock_generate_response(*args, **kwargs):
        return "Analysis output for match"
        
    monkeypatch.setattr("agents.roles.analyst.generate_response", mock_generate_response)
    
    state = WorkflowState(task_id="t1")
    state.match_contexts = [
        MatchContext(
            data_provider="mock", match_id="m1", league="Mock",
            home_team="A", home_team_id="1", away_team="B", away_team_id="2",
            season_id="1", match_date="2026-01-01",
            xg=None, home_form_5=None, home_form_10=None, away_form_5=None, away_form_10=None,
            form_source="", form_quality=0.0, home_standing=None, away_standing=None,
            total_teams=20, standings_source="", standings_quality=0.0, odds=None,
            lineups=None, odds_movement=None, head_to_head=None,
            data_gaps=(), overall_quality=1.0, sources={}, resolved_at=0.0
        )
    ]
    
    analyst = Analyst("analyst")
    new_state = await analyst.execute(state)
    
    assert new_state.current_step == "ANALYZE"
    assert "m1" in new_state.analysis_results
    assert new_state.analysis_results["m1"] == "Analysis output for match"

from agents.roles.supervisor import Supervisor
from agents.roles.reviewer import Reviewer

@pytest.mark.asyncio
async def test_supervisor_agent(monkeypatch):
    async def mock_generate_response(*args, **kwargs):
        return "PASS: The analysis is solid."
    monkeypatch.setattr("agents.roles.supervisor.generate_response", mock_generate_response)
    
    state = WorkflowState(task_id="t1", analysis_results={"m1": "Good match"})
    supervisor = Supervisor("supervisor")
    new_state = await supervisor.execute(state)
    assert new_state.current_step == "SUPERVISE"

@pytest.mark.asyncio
async def test_reviewer_agent(monkeypatch):
    async def mock_generate_response(*args, **kwargs):
        return "Review Report: Accurate"
    monkeypatch.setattr("agents.roles.reviewer.generate_response", mock_generate_response)
    
    state = WorkflowState(task_id="t1", analysis_results={"m1": "Good match"})
    reviewer = Reviewer("reviewer")
    new_state = await reviewer.execute(state)
    assert new_state.current_step == "REVIEW"
    assert "m1" in new_state.review_results

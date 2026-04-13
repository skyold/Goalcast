import pytest
from agents.core.state import WorkflowState
from agents.core.base import BaseAgent
from data_strategy.models import MatchContext

def test_workflow_state_initialization():
    state = WorkflowState(task_id="test-123")
    assert state.task_id == "test-123"
    assert state.match_contexts == []
    assert state.current_step == "INIT"

@pytest.mark.asyncio
async def test_base_agent_interface():
    class DummyAgent(BaseAgent):
        async def execute(self, state: WorkflowState) -> WorkflowState:
            state.current_step = "DUMMY_DONE"
            return state
            
    agent = DummyAgent("dummy")
    state = WorkflowState(task_id="1")
    new_state = await agent.execute(state)
    assert new_state.current_step == "DUMMY_DONE"

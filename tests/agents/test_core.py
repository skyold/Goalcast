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

from agents.core.coordinator import Coordinator

@pytest.mark.asyncio
async def test_coordinator_flow():
    class Step1Agent(BaseAgent):
        async def execute(self, state: WorkflowState) -> WorkflowState:
            state.current_step = "STEP_1"
            return state
            
    class Step2Agent(BaseAgent):
        async def execute(self, state: WorkflowState) -> WorkflowState:
            state.current_step = "STEP_2"
            return state
            
    coordinator = Coordinator()
    coordinator.add_agent("STEP_1", Step1Agent("agent1"))
    coordinator.add_agent("STEP_2", Step2Agent("agent2"))
    
    state = WorkflowState(task_id="coord-1")
    final_state = await coordinator.run(state, sequence=["STEP_1", "STEP_2"])
    
    assert final_state.current_step == "STEP_2"

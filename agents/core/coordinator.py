from typing import Dict, List
from agents.core.base import BaseAgent
from agents.core.state import WorkflowState
import logging

logger = logging.getLogger(__name__)

class Coordinator:
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}

    def add_agent(self, step_name: str, agent: BaseAgent):
        self.agents[step_name] = agent

    async def run(self, state: WorkflowState, sequence: List[str]) -> WorkflowState:
        logger.info(f"Starting workflow {state.task_id} with sequence: {sequence}")
        for step in sequence:
            if step not in self.agents:
                state.errors.append(f"Agent for step {step} not found.")
                break
            
            agent = self.agents[step]
            try:
                state = await agent.execute(state)
            except Exception as e:
                logger.error(f"Error in step {step}: {e}")
                state.errors.append(str(e))
                break
                
        logger.info(f"Workflow {state.task_id} finished at step {state.current_step}")
        return state

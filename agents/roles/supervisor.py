from agents.core.base import BaseAgent
from agents.core.state import WorkflowState
from agents.llm_router import generate_response

class Supervisor(BaseAgent):
    async def execute(self, state: WorkflowState) -> WorkflowState:
        for match_id, analysis in state.analysis_results.items():
            prompt = f"Review this analysis for logical consistency: {analysis}"
            try:
                await generate_response(prompt, system_prompt="You are a strict QA supervisor.")
            except Exception as e:
                state.errors.append(f"Supervisor check failed for {match_id}: {str(e)}")
                
        state.current_step = "SUPERVISE"
        return state

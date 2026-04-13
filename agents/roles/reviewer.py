from agents.core.base import BaseAgent
from agents.core.state import WorkflowState
from agents.llm_router import generate_response

class Reviewer(BaseAgent):
    async def execute(self, state: WorkflowState) -> WorkflowState:
        for match_id, analysis in state.analysis_results.items():
            prompt = f"Create a post-match review report for prediction: {analysis}"
            try:
                result = await generate_response(prompt, system_prompt="You are a post-match reviewer.")
                state.review_results[match_id] = result
            except Exception as e:
                state.errors.append(f"Review failed for {match_id}: {str(e)}")
                
        state.current_step = "REVIEW"
        return state

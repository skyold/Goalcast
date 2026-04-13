import json
from agents.core.base import BaseAgent
from agents.core.state import WorkflowState
from agents.llm_router import generate_response

class Analyst(BaseAgent):
    async def execute(self, state: WorkflowState) -> WorkflowState:
        for context in state.match_contexts:
            prompt = f"Analyze this match data: {json.dumps(context.to_dict())}"
            try:
                result = await generate_response(prompt, system_prompt="You are a football analyst.")
                state.analysis_results[context.match_id] = result
            except Exception as e:
                state.errors.append(f"Analysis failed for {context.match_id}: {str(e)}")
                
        state.current_step = "ANALYZE"
        return state

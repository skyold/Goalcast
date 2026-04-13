from agents.core.directory_agent import DirectoryAgent, DirectoryAgentLoader
from agents.core.state import WorkflowState
from agents.llm_router import generate_response

class Reviewer(DirectoryAgent):
    def __init__(self, name: str, role_dir: str = "agents/roles/reviewer"):
        super().__init__(name, role_dir)
        
    async def execute(self, state: WorkflowState) -> WorkflowState:
        for match_id, analysis in state.analysis_results.items():
            prompt = f"Create a post-match review report for prediction: {analysis}"
            try:
                result = await generate_response(
                    prompt=prompt, 
                    system_prompt=self.config.system_prompt,
                    tools=self.config.tools.get("builtin", {}).get("include", [])
                )
                state.review_results[match_id] = result
            except Exception as e:
                state.errors.append(f"Review failed for {match_id}: {str(e)}")
                
        state.current_step = "REVIEW"
        return state
from agents.core.directory_agent import DirectoryAgent, DirectoryAgentLoader
from agents.core.state import WorkflowState
from agents.llm_router import generate_response

class Supervisor(DirectoryAgent):
    def __init__(self, name: str, role_dir: str = "agents/roles/supervisor"):
        super().__init__(name, role_dir)
        
    async def execute(self, state: WorkflowState) -> WorkflowState:
        for match_id, analysis in state.analysis_results.items():
            prompt = f"Review this analysis for logical consistency: {analysis}"
            try:
                await generate_response(
                    prompt=prompt, 
                    system_prompt=self.config.system_prompt,
                    tools=self.config.tools.get("builtin", {}).get("include", [])
                )
            except Exception as e:
                state.errors.append(f"Supervisor check failed for {match_id}: {str(e)}")
                
        state.current_step = "SUPERVISE"
        return state
import json
from agents.core.directory_agent import DirectoryAgent, DirectoryAgentLoader
from agents.core.state import WorkflowState
from agents.llm_router import generate_response

class Analyst(DirectoryAgent):
    def __init__(self, name: str, role_dir: str = "agents/roles/analyst"):
        super().__init__(name, role_dir)
        
    async def execute(self, state: WorkflowState) -> WorkflowState:
        for context in state.match_contexts:
            prompt = f"Analyze this match data: {json.dumps(context.to_dict())}"
            try:
                result = await generate_response(
                    prompt=prompt, 
                    system_prompt=self.config.system_prompt,
                    tools=self.config.tools.get("builtin", {}).get("include", [])
                )
                state.analysis_results[context.match_id] = result
            except Exception as e:
                state.errors.append(f"Analysis failed for {context.match_id}: {str(e)}")
                
        state.current_step = "ANALYZE"
        return state
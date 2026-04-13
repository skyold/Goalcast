from agents.core.base import BaseAgent
from agents.core.state import WorkflowState
from data_strategy.fusion import DataFusion

class DataGatherer(BaseAgent):
    async def execute(self, state: WorkflowState) -> WorkflowState:
        fusion = DataFusion()
        match_ids = state.metadata.get("match_ids", [])
        
        for match_id in match_ids:
            try:
                context = await fusion.resolve_match(match_id)
                if context:
                    state.match_contexts.append(context)
            except Exception as e:
                state.errors.append(f"Failed to gather data for {match_id}: {str(e)}")
                
        state.current_step = "GATHER_DATA"
        return state

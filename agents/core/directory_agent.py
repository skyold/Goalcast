from dataclasses import dataclass, field
from typing import Dict, Any, List
from agents.core.base import BaseAgent
from agents.core.state import WorkflowState
from utils.config_parser import load_jsonc, merge_markdown_files
from agents.llm_router import generate_response
import json

@dataclass
class AgentConfig:
    system_prompt: str
    tools: Dict[str, Any] = field(default_factory=dict)

class DirectoryAgentLoader:
    MD_ORDER = [
        "IDENTITY.md",
        "AGENTS.md",
        "SOUL.md",
        "MEMORY.md",
        "TOOLS.md",
        "USER.md",
        "BOOTSTRAP.md",
        "HEARTBEAT.md"
    ]
    
    @staticmethod
    def load(role_dir: str) -> AgentConfig:
        system_prompt = merge_markdown_files(role_dir, DirectoryAgentLoader.MD_ORDER)
        tools = load_jsonc(f"{role_dir}/tool-registry.jsonc")
        return AgentConfig(system_prompt=system_prompt, tools=tools)

class DirectoryAgent(BaseAgent):
    def __init__(self, name: str, role_dir: str):
        super().__init__(name)
        self.role_dir = role_dir
        self.config = DirectoryAgentLoader.load(role_dir)
        
    async def execute(self, state: WorkflowState) -> WorkflowState:
        context_data = [ctx.to_dict() for ctx in state.match_contexts]
        prompt = f"Current Task: {state.task_id}\nContext Data: {json.dumps(context_data)}"
        
        try:
            result = await generate_response(
                prompt=prompt,
                system_prompt=self.config.system_prompt,
                tools=self.config.tools.get("builtin", {}).get("include", [])
            )
            state.metadata[f"{self.name}_result"] = result
        except Exception as e:
            state.errors.append(f"{self.name} failed: {str(e)}")
            
        state.current_step = f"{self.name}_DONE"
        return state
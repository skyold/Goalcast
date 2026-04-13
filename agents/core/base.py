from abc import ABC, abstractmethod
from agents.core.state import WorkflowState

class BaseAgent(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def execute(self, state: WorkflowState) -> WorkflowState:
        """Execute agent logic and return updated state."""
        pass

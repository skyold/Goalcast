from dataclasses import dataclass, field
from typing import List, Dict, Any
from datasource.datafusion.models import MatchContext

@dataclass
class WorkflowState:
    task_id: str
    match_contexts: List[MatchContext] = field(default_factory=list)
    analysis_results: Dict[str, Any] = field(default_factory=dict)
    review_results: Dict[str, Any] = field(default_factory=dict)
    current_step: str = "INIT"
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

# Multi-Agent Framework Design

## Overview
This document outlines the design for a custom, lightweight multi-agent orchestration framework within the Goalcast project. The goal is to integrate existing data collection tools (MCP, data providers), analysis methods (`skills`), and LLM capabilities into an automated, scheduled pipeline.

## Architectural Pattern
The framework uses a **Hierarchical State Machine** pattern. A `Coordinator` acts as the state manager, invoking specialized Agents in a predefined sequence (e.g., Gather Data -> Analyze -> Supervise -> Review). Context and data are passed between Agents via a strongly-typed `WorkflowState` object.

## Core Components & Directory Structure
The new framework will be placed in a new top-level `agents/` directory:

```text
Goalcast/
├── agents/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── base.py         # BaseAgent abstract class
│   │   ├── state.py        # WorkflowState dataclass
│   │   └── coordinator.py  # State machine runner
│   ├── roles/
│   │   ├── __init__.py
│   │   ├── gatherer.py     # DataGatherer Agent
│   │   ├── analyst.py      # Analyst Agent
│   │   ├── supervisor.py   # Supervisor Agent
│   │   └── reviewer.py     # Reviewer Agent
│   ├── scheduler.py        # APScheduler wrapper
│   └── llm_router.py       # LiteLLM or multi-model routing helper
```

## Data Flow & Context Contract
To ensure maximum compatibility with the existing codebase, the interface between the `DataGatherer` and `Analyst` agents will strictly rely on `data_strategy.models.MatchContext`.

### WorkflowState
The state object passed along the pipeline:

```python
from dataclasses import dataclass, field
from typing import List, Dict, Any
from data_strategy.models import MatchContext

@dataclass
class WorkflowState:
    task_id: str
    match_contexts: List[MatchContext] = field(default_factory=list)
    analysis_results: Dict[str, Any] = field(default_factory=dict)
    review_results: Dict[str, Any] = field(default_factory=dict)
    current_step: str = "INIT"
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
```

## Agent Roles & Responsibilities

1. **Coordinator (协调者)**
   - **Responsibility:** Initializes `WorkflowState` and executes the state machine loop.
   - **Flow:** `GATHER_DATA -> ANALYZE -> SUPERVISE -> REVIEW -> DONE`.
   - **Error Handling:** If an agent encounters a fatal error, it logs the error to `WorkflowState.errors` and the Coordinator decides whether to halt or retry.

2. **DataGatherer (数据获取)**
   - **Responsibility:** Calls the existing `DataFusion` layer (which orchestrates FootyStats, SportMonks, Understat providers).
   - **Output:** Appends generated `MatchContext` instances to `WorkflowState.match_contexts`.

3. **Analyst (分析)**
   - **Responsibility:** Iterates over `WorkflowState.match_contexts`. Feeds the data to the existing `skills` (v2.5/v3.0 models) via LLM prompts.
   - **Output:** Stores analysis predictions in `WorkflowState.analysis_results`.

4. **Supervisor (监督)**
   - **Responsibility:** Acts as a quality gate. Uses an LLM prompt to evaluate the Analyst's output for logical consistency, data gaps ignored, or hallucination.
   - **Output:** If the output fails validation, the Supervisor can push the state back to `ANALYZE` with feedback. Otherwise, it proceeds.

5. **Reviewer (复盘)**
   - **Responsibility:** Compares past predictions with actual match results to generate performance reports and updates the knowledge base.

## LLM Integration
- **Model Agnostic:** The `llm_router.py` will wrap LiteLLM (or a similar multi-provider approach) to allow seamless switching between Anthropic (Claude 3.5 Sonnet) and OpenAI (GPT-4o).
- **Prompt Injection:** Agents will construct their prompts by combining role-specific instructions with the data from `WorkflowState`.

## Scheduling Mechanism
- **Tool:** `APScheduler`
- **Responsibility:** A background process (daemon) will run `agents/scheduler.py`.
- **Triggers:** Cron-like expressions (e.g., daily at 10:00 AM) will instantiate a `Coordinator` and trigger the pipeline for a specific set of matches (e.g., "today's top league matches").

## Testing Strategy
- Unit tests for the `Coordinator` to ensure proper state transitions.
- Mocking the LLM responses for the `Analyst` and `Supervisor` agents.
- Ensuring `DataGatherer` correctly maps provider outputs to `MatchContext` (verifying existing tests still pass).

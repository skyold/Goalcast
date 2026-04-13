# Multi-Agent Framework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a custom lightweight multi-agent orchestration framework that integrates data collection, analysis skills, and LLM evaluations via a hierarchical state machine.

**Architecture:** A Coordinator runs a sequential state machine (`GATHER_DATA -> ANALYZE -> SUPERVISE -> REVIEW`), passing a strongly-typed `WorkflowState` object containing `MatchContext` instances to specialized Agent roles.

**Tech Stack:** Python 3.10+, `dataclasses`, `apscheduler`, `litellm` (or equivalent multi-model router), existing Goalcast models (`MatchContext`).

---

### Task 1: Core State and Base Agent

**Files:**
- Create: `agents/__init__.py`
- Create: `agents/core/__init__.py`
- Create: `agents/core/state.py`
- Create: `agents/core/base.py`
- Test: `tests/agents/test_core.py`

- [x] **Step 1: Write the failing test**

Create `tests/agents/test_core.py`:
```python
import pytest
from agents.core.state import WorkflowState
from agents.core.base import BaseAgent
from data_strategy.models import MatchContext

def test_workflow_state_initialization():
    state = WorkflowState(task_id="test-123")
    assert state.task_id == "test-123"
    assert state.match_contexts == []
    assert state.current_step == "INIT"

@pytest.mark.asyncio
async def test_base_agent_interface():
    class DummyAgent(BaseAgent):
        async def execute(self, state: WorkflowState) -> WorkflowState:
            state.current_step = "DUMMY_DONE"
            return state
            
    agent = DummyAgent("dummy")
    state = WorkflowState(task_id="1")
    new_state = await agent.execute(state)
    assert new_state.current_step == "DUMMY_DONE"
```

- [x] **Step 2: Run test to verify it fails**

Run: `pytest tests/agents/test_core.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agents.core.state'`

- [x] **Step 3: Write minimal implementation**

Create `agents/__init__.py` and `agents/core/__init__.py` (empty files).

Create `agents/core/state.py`:
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

Create `agents/core/base.py`:
```python
from abc import ABC, abstractmethod
from agents.core.state import WorkflowState

class BaseAgent(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def execute(self, state: WorkflowState) -> WorkflowState:
        """Execute agent logic and return updated state."""
        pass
```

- [x] **Step 4: Run test to verify it passes**

Run: `pytest tests/agents/test_core.py -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add agents/ tests/agents/
git commit -m "feat(agents): add core WorkflowState and BaseAgent"
```

---

### Task 2: Coordinator State Machine

**Files:**
- Create: `agents/core/coordinator.py`
- Modify: `tests/agents/test_core.py`

- [x] **Step 1: Write the failing test**

Append to `tests/agents/test_core.py`:
```python
from agents.core.coordinator import Coordinator

@pytest.mark.asyncio
async def test_coordinator_flow():
    class Step1Agent(BaseAgent):
        async def execute(self, state: WorkflowState) -> WorkflowState:
            state.current_step = "STEP_1"
            return state
            
    class Step2Agent(BaseAgent):
        async def execute(self, state: WorkflowState) -> WorkflowState:
            state.current_step = "STEP_2"
            return state
            
    coordinator = Coordinator()
    coordinator.add_agent("STEP_1", Step1Agent("agent1"))
    coordinator.add_agent("STEP_2", Step2Agent("agent2"))
    
    state = WorkflowState(task_id="coord-1")
    final_state = await coordinator.run(state, sequence=["STEP_1", "STEP_2"])
    
    assert final_state.current_step == "STEP_2"
```

- [x] **Step 2: Run test to verify it fails**

Run: `pytest tests/agents/test_core.py::test_coordinator_flow -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agents.core.coordinator'`

- [x] **Step 3: Write minimal implementation**

Create `agents/core/coordinator.py`:
```python
from typing import Dict, List
from agents.core.base import BaseAgent
from agents.core.state import WorkflowState
import logging

logger = logging.getLogger(__name__)

class Coordinator:
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}

    def add_agent(self, step_name: str, agent: BaseAgent):
        self.agents[step_name] = agent

    async def run(self, state: WorkflowState, sequence: List[str]) -> WorkflowState:
        logger.info(f"Starting workflow {state.task_id} with sequence: {sequence}")
        for step in sequence:
            if step not in self.agents:
                state.errors.append(f"Agent for step {step} not found.")
                break
            
            agent = self.agents[step]
            try:
                state = await agent.execute(state)
            except Exception as e:
                logger.error(f"Error in step {step}: {e}")
                state.errors.append(str(e))
                break
                
        logger.info(f"Workflow {state.task_id} finished at step {state.current_step}")
        return state
```

- [x] **Step 4: Run test to verify it passes**

Run: `pytest tests/agents/test_core.py -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add agents/core/coordinator.py tests/agents/test_core.py
git commit -m "feat(agents): implement Coordinator state machine"
```

---

### Task 3: LLM Router Helper

**Files:**
- Create: `agents/llm_router.py`
- Test: `tests/agents/test_llm_router.py`

- [x] **Step 1: Write the failing test**

Create `tests/agents/test_llm_router.py`:
```python
import pytest
from agents.llm_router import generate_response

@pytest.mark.asyncio
async def test_generate_response(monkeypatch):
    async def mock_acompletion(*args, **kwargs):
        class MockMessage:
            content = "Mocked LLM Response"
        class MockChoice:
            message = MockMessage()
        class MockResponse:
            choices = [MockChoice()]
        return MockResponse()
        
    monkeypatch.setattr("agents.llm_router.acompletion", mock_acompletion)
    
    response = await generate_response("Test prompt", model="gpt-4o-mini")
    assert response == "Mocked LLM Response"
```

- [x] **Step 2: Run test to verify it fails**

Run: `pytest tests/agents/test_llm_router.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [x] **Step 3: Write minimal implementation**

Create `agents/llm_router.py`:
```python
import os
from litellm import acompletion
from typing import Optional

async def generate_response(prompt: str, model: str = "gpt-4o-mini", system_prompt: Optional[str] = None) -> str:
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    response = await acompletion(
        model=model,
        messages=messages
    )
    return response.choices[0].message.content
```

- [x] **Step 4: Run test to verify it passes**

Note: Ensure `litellm` is added to requirements.txt if not present. Run test:
Run: `pytest tests/agents/test_llm_router.py -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
echo "litellm>=1.0.0" >> requirements.txt
git add agents/llm_router.py tests/agents/test_llm_router.py requirements.txt
git commit -m "feat(agents): add LLM router using litellm"
```

---

### Task 4: Gatherer Agent

**Files:**
- Create: `agents/roles/__init__.py`
- Create: `agents/roles/gatherer.py`
- Test: `tests/agents/test_roles.py`

- [x] **Step 1: Write the failing test**

Create `tests/agents/test_roles.py`:
```python
import pytest
from agents.core.state import WorkflowState
from agents.roles.gatherer import DataGatherer
from data_strategy.models import MatchContext

@pytest.mark.asyncio
async def test_gatherer_agent(monkeypatch):
    class MockFusion:
        async def resolve_match(self, match_id):
            return MatchContext(
                data_provider="mock", match_id=match_id, league="Mock",
                home_team="A", home_team_id="1", away_team="B", away_team_id="2",
                season_id="1", match_date="2026-01-01",
                xg=None, home_form_5=None, home_form_10=None, away_form_5=None, away_form_10=None,
                form_source="", form_quality=0.0, home_standing=None, away_standing=None,
                total_teams=20, standings_source="", standings_quality=0.0, odds=None,
                lineups=None, odds_movement=None, head_to_head=None,
                data_gaps=(), overall_quality=1.0, sources={}, resolved_at=0.0
            )
            
    monkeypatch.setattr("agents.roles.gatherer.DataFusion", MockFusion)
    
    state = WorkflowState(task_id="t1", metadata={"match_ids": ["m1", "m2"]})
    gatherer = DataGatherer("gatherer")
    new_state = await gatherer.execute(state)
    
    assert new_state.current_step == "GATHER_DATA"
    assert len(new_state.match_contexts) == 2
    assert new_state.match_contexts[0].match_id == "m1"
```

- [x] **Step 2: Run test to verify it fails**

Run: `pytest tests/agents/test_roles.py::test_gatherer_agent -v`
Expected: FAIL

- [x] **Step 3: Write minimal implementation**

Create `agents/roles/__init__.py` (empty).
Create `agents/roles/gatherer.py`:
```python
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
```

- [x] **Step 4: Run test to verify it passes**

Run: `pytest tests/agents/test_roles.py::test_gatherer_agent -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add agents/roles/gatherer.py tests/agents/test_roles.py agents/roles/__init__.py
git commit -m "feat(agents): implement DataGatherer agent"
```

---

### Task 5: Analyst Agent

**Files:**
- Create: `agents/roles/analyst.py`
- Modify: `tests/agents/test_roles.py`

- [x] **Step 1: Write the failing test**

Append to `tests/agents/test_roles.py`:
```python
from agents.roles.analyst import Analyst

@pytest.mark.asyncio
async def test_analyst_agent(monkeypatch):
    async def mock_generate_response(*args, **kwargs):
        return "Analysis output for match"
        
    monkeypatch.setattr("agents.roles.analyst.generate_response", mock_generate_response)
    
    state = WorkflowState(task_id="t1")
    state.match_contexts = [
        MatchContext(
            data_provider="mock", match_id="m1", league="Mock",
            home_team="A", home_team_id="1", away_team="B", away_team_id="2",
            season_id="1", match_date="2026-01-01",
            xg=None, home_form_5=None, home_form_10=None, away_form_5=None, away_form_10=None,
            form_source="", form_quality=0.0, home_standing=None, away_standing=None,
            total_teams=20, standings_source="", standings_quality=0.0, odds=None,
            lineups=None, odds_movement=None, head_to_head=None,
            data_gaps=(), overall_quality=1.0, sources={}, resolved_at=0.0
        )
    ]
    
    analyst = Analyst("analyst")
    new_state = await analyst.execute(state)
    
    assert new_state.current_step == "ANALYZE"
    assert "m1" in new_state.analysis_results
    assert new_state.analysis_results["m1"] == "Analysis output for match"
```

- [x] **Step 2: Run test to verify it fails**

Run: `pytest tests/agents/test_roles.py::test_analyst_agent -v`
Expected: FAIL

- [x] **Step 3: Write minimal implementation**

Create `agents/roles/analyst.py`:
```python
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
```

- [x] **Step 4: Run test to verify it passes**

Run: `pytest tests/agents/test_roles.py::test_analyst_agent -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add agents/roles/analyst.py tests/agents/test_roles.py
git commit -m "feat(agents): implement Analyst agent"
```

---

### Task 6: Supervisor and Reviewer Agents

**Files:**
- Create: `agents/roles/supervisor.py`
- Create: `agents/roles/reviewer.py`
- Modify: `tests/agents/test_roles.py`

- [x] **Step 1: Write the failing test**

Append to `tests/agents/test_roles.py`:
```python
from agents.roles.supervisor import Supervisor
from agents.roles.reviewer import Reviewer

@pytest.mark.asyncio
async def test_supervisor_agent(monkeypatch):
    async def mock_generate_response(*args, **kwargs):
        return "PASS: The analysis is solid."
    monkeypatch.setattr("agents.roles.supervisor.generate_response", mock_generate_response)
    
    state = WorkflowState(task_id="t1", analysis_results={"m1": "Good match"})
    supervisor = Supervisor("supervisor")
    new_state = await supervisor.execute(state)
    assert new_state.current_step == "SUPERVISE"

@pytest.mark.asyncio
async def test_reviewer_agent(monkeypatch):
    async def mock_generate_response(*args, **kwargs):
        return "Review Report: Accurate"
    monkeypatch.setattr("agents.roles.reviewer.generate_response", mock_generate_response)
    
    state = WorkflowState(task_id="t1", analysis_results={"m1": "Good match"})
    reviewer = Reviewer("reviewer")
    new_state = await reviewer.execute(state)
    assert new_state.current_step == "REVIEW"
    assert "m1" in new_state.review_results
```

- [x] **Step 2: Run test to verify it fails**

Run: `pytest tests/agents/test_roles.py::test_supervisor_agent tests/agents/test_roles.py::test_reviewer_agent -v`
Expected: FAIL

- [x] **Step 3: Write minimal implementation**

Create `agents/roles/supervisor.py`:
```python
from agents.core.base import BaseAgent
from agents.core.state import WorkflowState
from agents.llm_router import generate_response

class Supervisor(BaseAgent):
    async def execute(self, state: WorkflowState) -> WorkflowState:
        for match_id, analysis in state.analysis_results.items():
            prompt = f"Review this analysis for logical consistency: {analysis}"
            try:
                await generate_response(prompt, system_prompt="You are a strict QA supervisor.")
            except Exception as e:
                state.errors.append(f"Supervisor check failed for {match_id}: {str(e)}")
                
        state.current_step = "SUPERVISE"
        return state
```

Create `agents/roles/reviewer.py`:
```python
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
```

- [x] **Step 4: Run test to verify it passes**

Run: `pytest tests/agents/test_roles.py::test_supervisor_agent tests/agents/test_roles.py::test_reviewer_agent -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add agents/roles/supervisor.py agents/roles/reviewer.py tests/agents/test_roles.py
git commit -m "feat(agents): implement Supervisor and Reviewer agents"
```

---

### Task 7: Scheduler

**Files:**
- Create: `agents/scheduler.py`
- Test: `tests/agents/test_scheduler.py`

- [x] **Step 1: Write the failing test**

Create `tests/agents/test_scheduler.py`:
```python
import pytest
from agents.scheduler import start_scheduler

def test_scheduler_initialization(monkeypatch):
    class MockScheduler:
        def add_job(self, *args, **kwargs):
            self.job_added = True
        def start(self):
            self.started = True
            
    mock_instance = MockScheduler()
    monkeypatch.setattr("agents.scheduler.AsyncIOScheduler", lambda: mock_instance)
    
    scheduler = start_scheduler()
    assert mock_instance.started
    assert mock_instance.job_added
```

- [x] **Step 2: Run test to verify it fails**

Run: `pytest tests/agents/test_scheduler.py -v`
Expected: FAIL

- [x] **Step 3: Write minimal implementation**

Create `agents/scheduler.py`:
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
from agents.core.coordinator import Coordinator
from agents.core.state import WorkflowState
import logging

logger = logging.getLogger(__name__)

async def scheduled_task():
    logger.info("Scheduled task triggered.")
    # Implementation of pipeline dispatch goes here
    pass

def start_scheduler():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(scheduled_task, 'cron', hour=10, minute=0)
    scheduler.start()
    return scheduler

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    scheduler = start_scheduler()
    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass
```

- [x] **Step 4: Run test to verify it passes**

Add `apscheduler` to requirements if not present.
Run: `pytest tests/agents/test_scheduler.py -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
echo "apscheduler>=3.10.0" >> requirements.txt
git add agents/scheduler.py tests/agents/test_scheduler.py requirements.txt
git commit -m "feat(agents): add APScheduler integration"
```

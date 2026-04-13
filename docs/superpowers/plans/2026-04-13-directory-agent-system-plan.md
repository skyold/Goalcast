# Directory-Compatible Agent System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a system that parses Phoenix-style Markdown and JSONC configuration directories to dynamically configure and execute LLM-based Agents.

**Architecture:** A `DirectoryAgentLoader` parses `.md` and `.jsonc` files from a given directory to construct a system prompt and tool list. `DirectoryAgent` (inheriting from `BaseAgent`) uses this loader to configure itself. Existing hardcoded agents are refactored to use this dynamic configuration.

**Tech Stack:** Python 3.10+, `litellm`, `dataclasses`, `json` (with regex for JSONC stripping).

---

### Task 1: Configuration Parser Utility

**Files:**
- Create: `utils/config_parser.py`
- Test: `tests/utils/test_config_parser.py`

- [ ] **Step 1: Write the failing test for JSONC parsing**

Create `tests/utils/test_config_parser.py`:
```python
import pytest
from utils.config_parser import load_jsonc, merge_markdown_files
import os

def test_load_jsonc(tmp_path):
    jsonc_content = """
    {
        // This is a comment
        "builtin": {"include": ["read", "write"]}
    }
    """
    file_path = tmp_path / "test.jsonc"
    file_path.write_text(jsonc_content)
    
    result = load_jsonc(str(file_path))
    assert "builtin" in result
    assert "include" in result["builtin"]
    assert "read" in result["builtin"]["include"]

def test_merge_markdown_files(tmp_path):
    (tmp_path / "IDENTITY.md").write_text("# Identity\nI am a bot.")
    (tmp_path / "SOUL.md").write_text("# Soul\nI am helpful.")
    
    # Missing file should be ignored
    result = merge_markdown_files(str(tmp_path), ["IDENTITY.md", "MISSING.md", "SOUL.md"])
    assert "# Identity" in result
    assert "I am a bot." in result
    assert "# Soul" in result
    assert "I am helpful." in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/utils/test_config_parser.py -v`
Expected: FAIL with `ModuleNotFoundError` or `ImportError`.

- [ ] **Step 3: Write minimal implementation**

Create `utils/config_parser.py`:
```python
import json
import re
import os
from typing import List, Dict, Any

def load_jsonc(file_path: str) -> Dict[str, Any]:
    """Load JSONC file by stripping comments before parsing."""
    if not os.path.exists(file_path):
        return {}
        
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Remove single-line comments (//) and multi-line comments (/* */)
    content = re.sub(r'//.*', '', content)
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSONC in {file_path}: {e}")

def merge_markdown_files(directory: str, file_names: List[str]) -> str:
    """Merge content of specified markdown files in order."""
    merged_content = []
    
    for file_name in file_names:
        file_path = os.path.join(directory, file_name)
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                merged_content.append(f.read().strip())
                
    return "\n\n".join(merged_content)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/utils/test_config_parser.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add utils/config_parser.py tests/utils/test_config_parser.py
git commit -m "feat(utils): add config_parser for JSONC and Markdown merging"
```

---

### Task 2: Directory Agent Loader and Base Class

**Files:**
- Create: `agents/core/directory_agent.py`
- Test: `tests/agents/test_directory_agent.py`

- [ ] **Step 1: Write the failing test**

Create `tests/agents/test_directory_agent.py`:
```python
import pytest
from agents.core.directory_agent import DirectoryAgentLoader, DirectoryAgent
from agents.core.state import WorkflowState
import os

@pytest.fixture
def mock_role_dir(tmp_path):
    role_dir = tmp_path / "mock_role"
    role_dir.mkdir()
    (role_dir / "IDENTITY.md").write_text("I am a mock agent.")
    (role_dir / "tool-registry.jsonc").write_text('{"builtin": {"include": ["read"]}}')
    return str(role_dir)

def test_loader(mock_role_dir):
    config = DirectoryAgentLoader.load(mock_role_dir)
    assert "I am a mock agent." in config.system_prompt
    assert "read" in config.tools["builtin"]["include"]

@pytest.mark.asyncio
async def test_directory_agent(mock_role_dir, monkeypatch):
    async def mock_generate_response(prompt, model, system_prompt, tools=None):
        assert "mock agent" in system_prompt
        return "Processed"
        
    monkeypatch.setattr("agents.core.directory_agent.generate_response", mock_generate_response)
    
    agent = DirectoryAgent(name="test", role_dir=mock_role_dir)
    state = WorkflowState(task_id="1")
    new_state = await agent.execute(state)
    assert new_state.current_step == "test_DONE"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/agents/test_directory_agent.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

Create `agents/core/directory_agent.py`:
```python
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
            # We pass tools to generate_response (will be implemented in next task)
            result = await generate_response(
                prompt=prompt,
                system_prompt=self.config.system_prompt,
                tools=self.config.tools.get("builtin", {}).get("include", [])
            )
            # Default behavior: store in metadata to avoid hardcoding role-specific logic
            state.metadata[f"{self.name}_result"] = result
        except Exception as e:
            state.errors.append(f"{self.name} failed: {str(e)}")
            
        state.current_step = f"{self.name}_DONE"
        return state
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/agents/test_directory_agent.py -v`
Expected: PASS (we haven't added tools to llm_router yet, but python allows arbitrary kwargs if we use `**kwargs` or we just need to update llm_router signature. Let's fix `llm_router.py` signature first to avoid crash if `generate_response` doesn't take `tools`.)

Wait, we should update `llm_router.py` in the same step to avoid breaking tests.

Modify `agents/llm_router.py`:
```python
import os
from litellm import acompletion
from typing import Optional, List, Any

async def generate_response(prompt: str, model: str = "gpt-4o-mini", system_prompt: Optional[str] = None, tools: Optional[List[Any]] = None) -> str:
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    # LiteLLM tools integration is basic here, just passing it along if provided
    kwargs = {}
    if tools and len(tools) > 0:
        # Note: in a real implementation, these would be proper OpenAI tool schemas.
        # For now we just accept the parameter to satisfy the signature.
        pass
        
    response = await acompletion(
        model=model,
        messages=messages,
        **kwargs
    )
    return response.choices[0].message.content
```

Run test again: `pytest tests/agents/test_directory_agent.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agents/core/directory_agent.py tests/agents/test_directory_agent.py agents/llm_router.py
git commit -m "feat(agents): implement DirectoryAgentLoader and DirectoryAgent"
```

---

### Task 3: Refactor Analyst to Use DirectoryAgent

**Files:**
- Modify: `agents/roles/analyst.py`
- Modify: `tests/agents/test_roles.py`

- [ ] **Step 1: Write the failing test**

Modify `tests/agents/test_roles.py` to check for `DirectoryAgent` usage in `Analyst`. Since `Analyst` now inherits from `DirectoryAgent` or initializes it, we should update the test.

Update `tests/agents/test_roles.py`'s `test_analyst_agent`:
```python
from agents.roles.analyst import Analyst
from agents.core.directory_agent import AgentConfig

@pytest.mark.asyncio
async def test_analyst_agent(monkeypatch):
    async def mock_generate_response(*args, **kwargs):
        return "Analysis output for match"
        
    monkeypatch.setattr("agents.roles.analyst.generate_response", mock_generate_response)
    
    # Mock the loader so it doesn't read the real file system
    monkeypatch.setattr("agents.roles.analyst.DirectoryAgentLoader.load", lambda x: AgentConfig(system_prompt="Mocked Analyst"))
    
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
    
    analyst = Analyst("analyst", "agents/roles/analyst")
    new_state = await analyst.execute(state)
    
    assert new_state.current_step == "ANALYZE"
    assert "m1" in new_state.analysis_results
    assert new_state.analysis_results["m1"] == "Analysis output for match"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/agents/test_roles.py::test_analyst_agent -v`
Expected: FAIL (because Analyst `__init__` signature changed and it's not using DirectoryAgentLoader).

- [ ] **Step 3: Write minimal implementation**

Modify `agents/roles/analyst.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/agents/test_roles.py::test_analyst_agent -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agents/roles/analyst.py tests/agents/test_roles.py
git commit -m "refactor(agents): migrate Analyst to use DirectoryAgent"
```

---

### Task 4: Refactor Supervisor and Reviewer to Use DirectoryAgent

**Files:**
- Modify: `agents/roles/supervisor.py`
- Modify: `agents/roles/reviewer.py`
- Modify: `tests/agents/test_roles.py`

- [ ] **Step 1: Write the failing test**

Update `tests/agents/test_roles.py`'s `test_supervisor_agent` and `test_reviewer_agent` to mock `DirectoryAgentLoader.load`:
```python
@pytest.mark.asyncio
async def test_supervisor_agent(monkeypatch):
    async def mock_generate_response(*args, **kwargs):
        return "PASS: The analysis is solid."
    monkeypatch.setattr("agents.roles.supervisor.generate_response", mock_generate_response)
    monkeypatch.setattr("agents.roles.supervisor.DirectoryAgentLoader.load", lambda x: AgentConfig(system_prompt="Mocked Supervisor"))
    
    state = WorkflowState(task_id="t1", analysis_results={"m1": "Good match"})
    supervisor = Supervisor("supervisor", "agents/roles/supervisor")
    new_state = await supervisor.execute(state)
    assert new_state.current_step == "SUPERVISE"

@pytest.mark.asyncio
async def test_reviewer_agent(monkeypatch):
    async def mock_generate_response(*args, **kwargs):
        return "Review Report: Accurate"
    monkeypatch.setattr("agents.roles.reviewer.generate_response", mock_generate_response)
    monkeypatch.setattr("agents.roles.reviewer.DirectoryAgentLoader.load", lambda x: AgentConfig(system_prompt="Mocked Reviewer"))
    
    state = WorkflowState(task_id="t1", analysis_results={"m1": "Good match"})
    reviewer = Reviewer("reviewer", "agents/roles/reviewer")
    new_state = await reviewer.execute(state)
    assert new_state.current_step == "REVIEW"
    assert "m1" in new_state.review_results
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/agents/test_roles.py::test_supervisor_agent tests/agents/test_roles.py::test_reviewer_agent -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

Modify `agents/roles/supervisor.py`:
```python
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
```

Modify `agents/roles/reviewer.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/agents/test_roles.py::test_supervisor_agent tests/agents/test_roles.py::test_reviewer_agent -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agents/roles/supervisor.py agents/roles/reviewer.py tests/agents/test_roles.py
git commit -m "refactor(agents): migrate Supervisor and Reviewer to DirectoryAgent"
```

# Goalcast Orchestrator UI Gateway Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个基于 FastAPI 和 WebSocket 的 UI Gateway，通过 EventEmitter 实时推送 Orchestrator 的黑板分析进度，支持自然语言触发和全链路状态监控。

**Architecture:** 
引入一个基于 `asyncio` 的 `EventEmitter` 用于解耦状态同步；在 `Orchestrator` 生命周期节点（准备赛程、Agent开始、Agent完成）植入事件触发；使用 FastAPI 提供 `/ws/chat` WebSocket 接口，串联意图解析、任务调度与流式事件下发。

**Tech Stack:** Python 3.10+, FastAPI, WebSockets, asyncio, pytest, pytest-asyncio

---

### Task 1: Event Bus Implementation

**Files:**
- Create: `agents/core/events.py`
- Create: `tests/core/test_events.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_events.py
import asyncio
import pytest
from agents.core.events import EventEmitter

@pytest.mark.asyncio
async def test_event_emitter_subscribe_and_emit():
    emitter = EventEmitter()
    received = []

    async def callback(event_name: str, payload: dict):
        received.append((event_name, payload))

    emitter.subscribe(callback)
    
    await emitter.emit("test_event", {"key": "value"})
    
    # Allow event loop to process
    await asyncio.sleep(0.01)
    
    assert len(received) == 1
    assert received[0][0] == "test_event"
    assert received[0][1] == {"key": "value"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_events.py -v`
Expected: FAIL with ModuleNotFoundError for `agents.core.events`

- [ ] **Step 3: Write minimal implementation**

```python
# agents/core/events.py
import asyncio
from typing import Callable, Awaitable, List

class EventEmitter:
    def __init__(self):
        self._subscribers: List[Callable[[str, dict], Awaitable[None]]] = []

    def subscribe(self, callback: Callable[[str, dict], Awaitable[None]]):
        self._subscribers.append(callback)

    async def emit(self, event_name: str, payload: dict):
        tasks = [callback(event_name, payload) for callback in self._subscribers]
        if tasks:
            await asyncio.gather(*tasks)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_events.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/core/test_events.py agents/core/events.py
git commit -m "feat(core): implement EventEmitter for pub/sub"
```

### Task 2: Inject EventEmitter into Orchestrator

**Files:**
- Modify: `agents/core/orchestrator.py`
- Create: `tests/core/test_orchestrator_events.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_orchestrator_events.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from agents.core.orchestrator import Orchestrator
from agents.core.events import EventEmitter

@pytest.mark.asyncio
async def test_orchestrator_emits_events():
    adapter = MagicMock()
    emitter = EventEmitter()
    
    # Track emitted events
    emitted = []
    async def track(name, payload):
        emitted.append(name)
    emitter.subscribe(track)

    orch = Orchestrator(adapter, semi_mode=False, emitter=emitter)
    
    # Mock fetch to return 0 to end fast
    orch._fetch_and_prepare = AsyncMock(return_value=0)
    
    await orch.run(leagues=["Premier League"], date="2026-04-29")
    
    # We expect 'pipeline_start' to be emitted at run, and 'pipeline_complete'
    assert "pipeline_start" in emitted
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_orchestrator_events.py -v`
Expected: FAIL because `Orchestrator` doesn't take `emitter` parameter and doesn't emit.

- [ ] **Step 3: Write minimal implementation**

```python
# Modify agents/core/orchestrator.py
# Add emitter to __init__ and emit basic pipeline events.

# (Assuming existing Orchestrator class structure)
# In agents/core/orchestrator.py:
# 1. Import EventEmitter
# from agents.core.events import EventEmitter

# 2. Modify __init__:
# def __init__(self, adapter, semi_mode: bool = False, emitter: EventEmitter | None = None):
#     self.adapter = adapter
#     self.semi_mode = semi_mode
#     self.stop_event = asyncio.Event()
#     self.pipeline = MatchPipeline(adapter, semi_mode)
#     self.emitter = emitter or EventEmitter()

# 3. Add to start of run():
# await self.emitter.emit("pipeline_start", {"message": "Starting pipeline..."})

# 4. In _fetch_and_prepare, right before return count, add:
# await self.emitter.emit("matches_found", {"total": count, "matches": []})

# 5. In _analyst_loop, when claiming a record:
# await self.emitter.emit("match_step_start", {"match_id": record["match_id"], "step": "analyst"})
```
*(Apply the exact diffs to `agents/core/orchestrator.py` during execution)*

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_orchestrator_events.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/core/test_orchestrator_events.py agents/core/orchestrator.py
git commit -m "feat(orchestrator): inject EventEmitter and basic lifecycle events"
```

### Task 3: LLM Intent Parser Module

**Files:**
- Create: `agents/web/intent.py`
- Create: `tests/web/test_intent.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/web/test_intent.py
import pytest
from unittest.mock import AsyncMock
from agents.web.intent import parse_intent

@pytest.mark.asyncio
async def test_parse_intent():
    mock_adapter = AsyncMock()
    # Simulate LLM returning JSON string
    mock_adapter.run_agent.return_value = '{"leagues": ["Premier League"], "date": "2026-04-29", "models": ["v4.0"]}'
    
    result = await parse_intent("分析今天英超", mock_adapter)
    assert result["leagues"] == ["Premier League"]
    assert result["date"] == "2026-04-29"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/web/test_intent.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Write minimal implementation**

```python
# agents/web/intent.py
import json

async def parse_intent(text: str, adapter) -> dict:
    prompt = f"""
    Parse the following user request into JSON.
    Format: {{"leagues": [], "date": "YYYY-MM-DD", "models": []}}
    Request: {text}
    Return ONLY valid JSON.
    """
    # Assuming adapter has run_agent or similar call
    response_text = await adapter.run_agent("roles/orchestrator", prompt)
    
    # Strip potential markdown code blocks
    cleaned = response_text.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {"leagues": [], "date": None, "models": ["v4.0"]}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/web/test_intent.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/web/test_intent.py agents/web/intent.py
git commit -m "feat(web): add LLM intent parser"
```

### Task 4: FastAPI Web Server & WebSocket Endpoint

**Files:**
- Create: `agents/web/server.py`
- Create: `tests/web/test_server.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/web/test_server.py
import pytest
from fastapi.testclient import TestClient
from agents.web.server import app

def test_websocket_chat():
    client = TestClient(app)
    with client.websocket_connect("/ws/chat") as websocket:
        websocket.send_text("Hello")
        data = websocket.receive_json()
        assert data["type"] == "chat_chunk"
        assert "正在处理" in data["payload"]["text"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/web/test_server.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Write minimal implementation**

```python
# agents/web/server.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from agents.core.events import EventEmitter
import asyncio
import json

app = FastAPI()
global_emitter = EventEmitter()

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    
    # Setup listener for this connection
    async def on_event(name: str, payload: dict):
        await websocket.send_json({"type": name, "payload": payload})
        
    global_emitter.subscribe(on_event)
    
    try:
        while True:
            text = await websocket.receive_text()
            # Send immediate ack
            await websocket.send_json({
                "type": "chat_chunk", 
                "payload": {"text": f"正在处理您的请求: {text}"}
            })
            # In a real scenario, this would spawn parse_intent & orchestrator.run
            # asyncio.create_task(handle_user_request(text, global_emitter))
    except WebSocketDisconnect:
        pass
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/web/test_server.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/web/test_server.py agents/web/server.py
git commit -m "feat(web): add FastAPI WebSocket chat endpoint"
```

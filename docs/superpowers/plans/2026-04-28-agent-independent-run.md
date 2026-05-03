# Goalcast Agent 独立运行改造 —— 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 Goalcast 的 6 个 Agent 都能像 yclake 一样独立运行，通过单文件（`data/matches/{match_id}.json`）追踪每场比赛的完整生命周期，形成 Orchestrator→Analyst→Trader→Reviewer→Reporter→Backtester 的 RD 循环。

**Architecture:** 新增 `agents/adapters/` 层实现 Agentic Loop（tool_use ↔ tool_result 多轮推理），新增 `agents/core/match_store.py` 实现单文件生命周期追踪（对齐 yclake 的 hypothesis_store），新增 `agents/core/pipeline.py` 和 `agents/core/orchestrator.py` 实现异步并行 RD 循环，新增 `main.py` 提供 CLI 入口。改造 `DirectoryAgentLoader` 支持返回 `AgentDefinition`（包含工具权限信息），更新各 Agent 角色文件适配独立运行模式。

**Tech Stack:** Python 3.10+, Anthropic Python SDK (已有依赖 anthropic==0.38.0), asyncio, 复用现有 MCP 工具和 Skill 系统。

---

## 文件结构

```
Goalcast/
├── agents/
│   ├── adapters/                        ← 新建目录
│   │   ├── __init__.py                  ← Task 2
│   │   ├── adapter.py                   ← Task 3: Agentic Loop
│   │   └── tool_executor.py             ← Task 4: MCP 工具执行器
│   ├── core/
│   │   ├── base.py                      ← 不改
│   │   ├── directory_agent.py           ← Task 7: 改造为支持 AgentDefinition
│   │   ├── state.py                     ← 不改（保留兼容，新代码不用）
│   │   ├── coordinator.py               ← 保留但不改（旧流水线兼容）
│   │   ├── match_store.py               ← Task 1: 单文件生命周期存储
│   │   ├── pipeline.py                  ← Task 5: RD 循环步骤
│   │   └── orchestrator.py              ← Task 6: 异步并行 RD 循环
│   ├── llm_router.py                    ← 不改（保留兼容）
│   └── roles/
│       ├── orchestrator/
│       │   ├── AGENTS.md                ← Task 9: 更新为总管角色
│       │   └── tool-registry.jsonc      ← Task 8: 更新工具引用
│       ├── analyst/
│       │   ├── AGENTS.md                ← Task 9
│       │   └── tool-registry.jsonc      ← Task 8
│       ├── trader/
│       │   ├── AGENTS.md                ← Task 9
│       │   └── tool-registry.jsonc      ← Task 8
│       ├── reviewer/
│       │   ├── AGENTS.md                ← Task 9 (新增赛前审核)
│       │   └── tool-registry.jsonc      ← Task 8
│       ├── reporter/
│       │   ├── AGENTS.md                ← Task 9
│       │   └── tool-registry.jsonc      ← Task 8
│       └── backtester/
│           ├── AGENTS.md                ← Task 9
│           └── tool-registry.jsonc      ← Task 8
├── data/matches/                        ← 新建目录：单文件比赛追踪
├── main.py                              ← Task 10: CLI 入口
└── tests/
    └── core/
        ├── test_match_store.py           ← Task 1 伴随
        └── test_adapter.py               ← Task 3 伴随
```

---

### Task 1: match_store.py —— 单文件比赛生命周期存储

**Files:**
- Create: `agents/core/match_store.py`
- Create: `tests/core/test_match_store.py`

- [ ] **Step 1: 编写测试文件**

```python
# tests/core/test_match_store.py
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.core import match_store


def _sample_match(match_id: str) -> dict:
    return {
        "schema_version": "1.0",
        "match_id": match_id,
        "status": "pending",
        "orchestrator": {
            "home_team": "Manchester City",
            "away_team": "Arsenal",
            "league": "Premier League",
            "kickoff_time": "2026-04-30T19:00:00+08:00",
            "data_source": "sportmonks",
            "model_version": "v4.0",
            "prepared_at": "2026-04-28T10:00:00+08:00",
        },
    }


def test_generate_match_id_format():
    match_id = match_store.generate_match_id()
    assert re.fullmatch(r"MC-\d{8}-\d{6}-[A-F0-9]{8}", match_id)


def test_save_and_load(tmp_path, monkeypatch):
    monkeypatch.setattr(match_store, "MATCHES_DIR", tmp_path)

    record = _sample_match("MC-20260428-100000-A1B2C3D4")
    match_store.save(record)

    loaded = match_store.load(record["match_id"])
    assert loaded is not None
    assert loaded["match_id"] == record["match_id"]
    assert loaded["orchestrator"]["home_team"] == "Manchester City"
    assert loaded["status"] == "pending"


def test_append_layer_and_status_transition(tmp_path, monkeypatch):
    monkeypatch.setattr(match_store, "MATCHES_DIR", tmp_path)

    match_id = "MC-20260428-100000-A1B2C3D4"
    match_store.save(_sample_match(match_id))

    # Analyst 追加分析层
    match_store.append_layer(
        match_id,
        "analysis",
        {
            "home_xg": 1.82,
            "away_xg": 1.15,
            "confidence": 78,
            "analyzed_at": "2026-04-28T10:05:00+08:00",
        },
    )
    record = match_store.load(match_id)
    assert record["status"] == "analyzed"
    assert record["analysis"]["home_xg"] == 1.82

    # Trader 追加交易层
    match_store.append_layer(
        match_id,
        "trade",
        {
            "direction": "home",
            "ah_line": -0.5,
            "best_odds": 1.91,
            "stake": 2.5,
            "traded_at": "2026-04-28T10:08:00+08:00",
        },
    )
    record = match_store.load(match_id)
    assert record["status"] == "traded"
    assert record["trade"]["stake"] == 2.5

    # Reviewer 追加审核层
    match_store.append_layer(
        match_id,
        "review",
        {
            "verdict": "approved",
            "checks": {"confidence": "pass", "ev": "pass"},
            "reviewed_at": "2026-04-28T10:12:00+08:00",
        },
    )
    record = match_store.load(match_id)
    assert record["status"] == "reviewed"
    assert record["review"]["verdict"] == "approved"


def test_update_status(tmp_path, monkeypatch):
    monkeypatch.setattr(match_store, "MATCHES_DIR", tmp_path)

    match_id = "MC-20260428-100000-A1B2C3D4"
    match_store.save(_sample_match(match_id))

    match_store.update_status(match_id, "feedback")
    record = match_store.load(match_id)
    assert record["status"] == "feedback"


def test_claim_oldest(tmp_path, monkeypatch):
    monkeypatch.setattr(match_store, "MATCHES_DIR", tmp_path)

    # 写入两场比赛
    r1 = _sample_match("MC-20260428-100000-AAAAAAAA")
    r1["orchestrator"]["prepared_at"] = "2026-04-28T09:00:00+08:00"
    match_store.save(r1)

    r2 = _sample_match("MC-20260428-101000-BBBBBBBB")
    r2["orchestrator"]["prepared_at"] = "2026-04-28T08:00:00+08:00"
    match_store.save(r2)

    # 认领最早的 pending
    claimed = match_store.claim_oldest(["pending"], "analyzing")
    assert claimed is not None
    assert claimed["match_id"] == "MC-20260428-101000-BBBBBBBB"
    assert claimed["status"] == "analyzing"

    # 确认文件也更新了
    loaded = match_store.load("MC-20260428-101000-BBBBBBBB")
    assert loaded["status"] == "analyzing"


def test_list_all(tmp_path, monkeypatch):
    monkeypatch.setattr(match_store, "MATCHES_DIR", tmp_path)

    match_store.save(_sample_match("MC-20260428-100000-AAAAAAAA"))
    match_store.save(_sample_match("MC-20260428-101000-BBBBBBBB"))

    all_records = match_store.list_all()
    assert len(all_records) == 2

    pending_records = match_store.list_all(status="pending")
    assert len(pending_records) == 2


def test_finalize(tmp_path, monkeypatch):
    monkeypatch.setattr(match_store, "MATCHES_DIR", tmp_path)

    match_id = "MC-20260428-100000-A1B2C3D4"
    match_store.save(_sample_match(match_id))

    match_store.finalize(match_id, report_ref="data/reports/2026-04-30.md")
    record = match_store.load(match_id)
    assert record["status"] == "reported"
    assert record["report_ref"] == "data/reports/2026-04-30.md"


def test_load_nonexistent():
    result = match_store.load("MC-NONEXISTENT")
    assert result is None
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast && python -m pytest tests/core/test_match_store.py -v
```

期望: 全部 FAIL（模块未创建）

- [ ] **Step 3: 实现 match_store.py**

```python
# agents/core/match_store.py
"""
单场比赛的完整生命周期存储。
一场比赛一个 JSON 文件，所有 Agent 的输出都追加到同一个文件。
对齐 yclake 的 hypothesis_store 模式。
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

MATCHES_DIR = Path(__file__).parent.parent.parent / "data" / "matches"
_CST = timezone(timedelta(hours=8))

_STATUS_MAP = {
    "analysis": "analyzed",
    "trade": "traded",
    "review": "reviewed",
    "post_match": "completed",
}


def now_iso() -> str:
    return datetime.now(_CST).isoformat()


def generate_match_id() -> str:
    ts = datetime.now(_CST).strftime("%Y%m%d-%H%M%S")
    uid = uuid.uuid4().hex[:8].upper()
    return f"MC-{ts}-{uid}"


def save(record: dict) -> str:
    MATCHES_DIR.mkdir(parents=True, exist_ok=True)
    match_id = record["match_id"]
    _write(match_id, record)
    logger.info("[MatchStore] 比赛已保存: %s", match_id)
    return match_id


def load(match_id: str) -> dict | None:
    filepath = MATCHES_DIR / f"{match_id}.json"
    if not filepath.exists():
        return None
    try:
        return json.loads(filepath.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.warning("[MatchStore] 比赛 JSON 损坏: %s", match_id)
        return None


def append_layer(match_id: str, layer_name: str, layer_data: dict) -> None:
    record = load(match_id)
    if record is None:
        return
    record[layer_name] = layer_data
    if layer_name in _STATUS_MAP:
        record["status"] = _STATUS_MAP[layer_name]
    _write(match_id, record)
    logger.info(
        "[MatchStore] 比赛 %s 追加层 %s, 状态 → %s",
        match_id,
        layer_name,
        record["status"],
    )


def update_status(match_id: str, status: str) -> None:
    record = load(match_id)
    if record is None:
        return
    record["status"] = status
    _write(match_id, record)
    logger.info("[MatchStore] 比赛 %s 状态 → %s", match_id, status)


def claim_oldest(status_list: list[str], new_status: str) -> dict | None:
    MATCHES_DIR.mkdir(parents=True, exist_ok=True)
    candidates: list[tuple[str, dict]] = []

    for fp in MATCHES_DIR.glob("MC-*.json"):
        try:
            record = json.loads(fp.read_text(encoding="utf-8"))
            if record.get("status") in status_list:
                prepared = (
                    record.get("orchestrator", {}).get("prepared_at", "")
                    or record.get("created_at", "")
                    or "9999"
                )
                candidates.append((prepared, record))
        except json.JSONDecodeError:
            continue

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0])
    target = candidates[0][1]
    target["status"] = new_status
    _write(target["match_id"], target)
    logger.info("[MatchStore] 认领比赛 %s: %s → %s", target["match_id"], status_list, new_status)
    return target


def list_all(status: str | None = None) -> list[dict]:
    MATCHES_DIR.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    for fp in sorted(MATCHES_DIR.glob("MC-*.json")):
        try:
            record = json.loads(fp.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if status is None or record.get("status") == status:
            results.append(record)
    return results


def count_by_status(status_list: list[str]) -> int:
    MATCHES_DIR.mkdir(parents=True, exist_ok=True)
    count = 0
    for fp in MATCHES_DIR.glob("MC-*.json"):
        try:
            record = json.loads(fp.read_text(encoding="utf-8"))
            if record.get("status") in status_list:
                count += 1
        except json.JSONDecodeError:
            continue
    return count


def finalize(match_id: str, report_ref: str = "") -> None:
    record = load(match_id)
    if record is None:
        return
    record["status"] = "reported"
    record["report_ref"] = report_ref
    _write(match_id, record)
    logger.info("[MatchStore] 比赛 %s 已完成 (reported)", match_id)


def _write(match_id: str, record: dict) -> None:
    MATCHES_DIR.mkdir(parents=True, exist_ok=True)
    filepath = MATCHES_DIR / f"{match_id}.json"
    filepath.write_text(
        json.dumps(record, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast && python -m pytest tests/core/test_match_store.py -v
```

期望: 全部 PASS

- [ ] **Step 5: 验证 match_store 模块可导入**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast && python -c "from agents.core.match_store import save, load, append_layer, claim_oldest, list_all; print('OK')"
```

---

### Task 2: agents/adapters/__init__.py

**Files:**
- Create: `agents/adapters/__init__.py`

- [ ] **Step 1: 创建包文件**

```python
# agents/adapters/__init__.py
from agents.adapters.adapter import ClaudeAdapter, AgentResult
from agents.adapters.tool_executor import ToolExecutor

__all__ = ["ClaudeAdapter", "AgentResult", "ToolExecutor"]
```

- [ ] **Step 2: 验证导入**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast && python -c "from agents.adapters import ClaudeAdapter, AgentResult, ToolExecutor; print('OK')"
```

期望: ImportError（adapter.py 和 tool_executor.py 尚未创建）——确认包路径正确即可

---

### Task 3: adapter.py —— Agentic Loop 核心

**Files:**
- Create: `agents/adapters/adapter.py`
- Create: `tests/core/test_adapter.py`

- [ ] **Step 1: 编写测试**

```python
# tests/core/test_adapter.py
import pytest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.adapters import AgentResult


class FakeLoader:
    """模拟 DirectoryAgentLoader，返回固定的 AgentDefinition"""
    def __init__(self, system_prompt: str = "", allowed_tools: list[str] | None = None):
        self.system_prompt = system_prompt
        self.allowed_tools = allowed_tools or []

    def load_agent(self, role_path: str):
        from agents.core.directory_agent import AgentDefinition
        return AgentDefinition(
            role_path=role_path,
            system_prompt=self.system_prompt,
            tool_registry={"mcp": [{"name": t} for t in self.allowed_tools]},
        )


class FakeExecutor:
    """模拟 ToolExecutor，返回固定结果"""
    def __init__(self, responses: dict[str, dict] | None = None):
        self.responses = responses or {}
        self.calls: list[dict] = []

    async def execute(self, tool_name: str, params: dict) -> dict:
        self.calls.append({"tool": tool_name, "params": params})
        return self.responses.get(tool_name, {"ok": True})


@pytest.mark.asyncio
async def test_adapter_agent_result_dataclass():
    result = AgentResult(
        role_path="analyst",
        final_text="分析完成",
        tool_calls=[],
        rounds=1,
    )
    assert result.role_path == "analyst"
    assert result.final_text == "分析完成"
    assert result.rounds == 1


@pytest.mark.asyncio
async def test_adapter_loads_agent_definition(monkeypatch):
    from agents.adapters import ClaudeAdapter

    loader = FakeLoader(system_prompt="You are an analyst")
    adapter = ClaudeAdapter(loader=loader, executor=FakeExecutor())

    assert adapter.loader is loader
```

- [ ] **Step 2: 运行测试确认失败（模块不存在）**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast && python -m pytest tests/core/test_adapter.py -v
```

- [ ] **Step 3: 实现 adapter.py**

```python
# agents/adapters/adapter.py
"""
Agentic Loop 适配器 —— 实现多轮 tool_use ↔ tool_result 循环。
参考 yclake 的 ClaudeAdapter，使用 Anthropic Python SDK。
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 20
DEFAULT_MODEL = "claude-sonnet-4-20250514"
DEFAULT_MAX_TOKENS = 16384


@dataclass
class AgentResult:
    role_path: str
    final_text: str
    tool_calls: list[dict]
    rounds: int


class ClaudeAdapter:
    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        executor: Any = None,
        loader: Any = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ):
        self.model = model or DEFAULT_MODEL
        self.max_tokens = max_tokens

        import anthropic
        import os

        client_kwargs = {}
        resolved_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if resolved_key:
            client_kwargs["api_key"] = resolved_key
        if base_url:
            client_kwargs["base_url"] = base_url
        self.client = anthropic.AsyncAnthropic(**client_kwargs)

        from agents.adapters.tool_executor import ToolExecutor
        from agents.core.directory_agent import DirectoryAgentLoader

        self.executor = executor or ToolExecutor()
        self.loader = loader or DirectoryAgentLoader()

    async def run_agent(
        self, role_path: str, user_message: str, context: dict | None = None
    ) -> AgentResult:
        agent_def = self.loader.load_agent(role_path)

        schemas = get_schemas_for_tools(agent_def.allowed_mcp_tools)

        messages: list[dict] = []
        if context:
            messages.append({
                "role": "user",
                "content": f"Context:\n{json.dumps(context, ensure_ascii=False, indent=2)}",
            })
        messages.append({"role": "user", "content": user_message})

        tool_calls_log: list[dict] = []
        rounds = 0

        while rounds < MAX_TOOL_ROUNDS:
            rounds += 1
            logger.info(
                "[ClaudeAdapter] 第 %d 轮推理 | 角色: %s | 工具数: %d",
                rounds, role_path, len(schemas),
            )

            request_kwargs = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "system": agent_def.system_prompt,
                "messages": messages,
            }
            if schemas:
                request_kwargs["tools"] = schemas

            response = await self.client.messages.create(**request_kwargs)

            assistant_content = []
            for block in response.content:
                if hasattr(block, "type"):
                    assistant_content.append({
                        "type": block.type,
                        "text": getattr(block, "text", None),
                        "name": getattr(block, "name", None),
                        "input": getattr(block, "input", None),
                        "id": getattr(block, "id", None),
                    })
                else:
                    assistant_content.append({"type": "text", "text": str(block)})

            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
                final_text = _extract_text(response)
                logger.info(
                    "[ClaudeAdapter] 完成 | 角色: %s | 轮数: %d | 工具调用: %d",
                    role_path, rounds, len(tool_calls_log),
                )
                return AgentResult(
                    role_path=role_path,
                    final_text=final_text,
                    tool_calls=tool_calls_log,
                    rounds=rounds,
                )

            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if hasattr(block, "type") and block.type == "tool_use":
                        tool_name = block.name
                        tool_input = block.input if block.input else {}
                        result = await self.executor.execute(tool_name, tool_input)
                        tool_calls_log.append({
                            "tool": tool_name,
                            "input": tool_input,
                            "result": result,
                        })
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result, ensure_ascii=False),
                        })
                messages.append({"role": "user", "content": tool_results})
                continue

            logger.warning(
                "[ClaudeAdapter] 未知 stop_reason: %s | 角色: %s",
                response.stop_reason, role_path,
            )
            return AgentResult(
                role_path=role_path,
                final_text=_extract_text(response),
                tool_calls=tool_calls_log,
                rounds=rounds,
            )

        logger.error(
            "[ClaudeAdapter] 超出最大轮数 %d | 角色: %s",
            MAX_TOOL_ROUNDS, role_path,
        )
        return AgentResult(
            role_path=role_path,
            final_text="[MAX_ROUNDS_EXCEEDED] Agent 推理轮数超出上限。",
            tool_calls=tool_calls_log,
            rounds=MAX_TOOL_ROUNDS,
        )


def get_schemas_for_tools(tool_names: list[str]) -> list[dict]:
    from agents.adapters.tool_executor import TOOL_SCHEMAS

    schemas = []
    for name in tool_names:
        if name in TOOL_SCHEMAS:
            schemas.append(TOOL_SCHEMAS[name])
        else:
            logger.warning("[ClaudeAdapter] 未知工具名: %s", name)
    return schemas


def _extract_text(response) -> str:
    for block in response.content:
        if hasattr(block, "type") and block.type == "text":
            return block.text
    return ""
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast && python -m pytest tests/core/test_adapter.py -v
```

---

### Task 4: tool_executor.py —— MCP 工具执行器

**Files:**
- Create: `agents/adapters/tool_executor.py`

- [ ] **Step 1: 实现 tool_executor.py**

```python
# agents/adapters/tool_executor.py
"""
MCP 工具执行器 —— 将 Agentic Loop 中的工具调用路由到 Goalcast MCP 工具。
所有 _tool_* 方法复用现有 MCP 工具实现，不做重复逻辑。
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ── 工具 Schema 注册表 ──────────────────────────────────────────────────
# Anthropic Tool Use 格式。只定义各 Agent 实际会用到的工具。

TOOL_SCHEMAS: dict[str, dict] = {
    "goalcast_sportmonks_get_matches": {
        "name": "goalcast_sportmonks_get_matches",
        "description": "读取指定日期（默认今天）的比赛列表，可按联赛 ID (league_ids) 过滤。",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "日期 (YYYY-MM-DD)，默认今天"},
                "league_ids": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "联赛 ID 列表，用于过滤",
                },
            },
        },
    },
    "goalcast_sportmonks_get_match": {
        "name": "goalcast_sportmonks_get_match",
        "description": "读取单场 Sportmonks 比赛详情（分析契约），仅需 fixture_id。",
        "input_schema": {
            "type": "object",
            "properties": {
                "fixture_id": {"type": "integer", "description": "Sportmonks fixture ID"},
                "match_date": {"type": "string", "description": "比赛日期 (YYYY-MM-DD)，可选"},
            },
            "required": ["fixture_id"],
        },
    },
    "goalcast_footystats_resolve_match": {
        "name": "goalcast_footystats_resolve_match",
        "description": "基于 FootyStats + Understat 的 DataFusion 单场编排入口。",
        "input_schema": {
            "type": "object",
            "properties": {
                "match_id": {"type": "string"},
                "home_team": {"type": "string"},
                "home_team_id": {"type": "string"},
                "away_team": {"type": "string"},
                "away_team_id": {"type": "string"},
                "season_id": {"type": "string"},
                "league": {"type": "string"},
                "match_date": {"type": "string"},
                "season": {"type": "string"},
            },
            "required": ["match_id", "home_team", "home_team_id", "away_team", "away_team_id", "season_id", "league"],
        },
    },
    "goalcast_footystats_get_todays_matches": {
        "name": "goalcast_footystats_get_todays_matches",
        "description": "获取 FootyStats 今日或指定日期赛程。",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "日期 (YYYY-MM-DD)，默认今天"},
                "league_filter": {"type": "string", "description": "联赛名称过滤"},
            },
        },
    },
    "goalcast_calculate_poisson": {
        "name": "goalcast_calculate_poisson",
        "description": "使用泊松分布或 Dixon-Coles 分布计算比分概率矩阵。",
        "input_schema": {
            "type": "object",
            "properties": {
                "home_lambda": {"type": "number", "description": "主队进球期望"},
                "away_lambda": {"type": "number", "description": "客队进球期望"},
                "max_goals": {"type": "integer", "description": "最大进球数，默认 6"},
                "model": {"type": "string", "description": "模型: standard 或 dixon_coles"},
                "rho": {"type": "number", "description": "Dixon-Coles 相关系数，默认 -0.13"},
            },
            "required": ["home_lambda", "away_lambda"],
        },
    },
    "goalcast_calculate_ah_prob": {
        "name": "goalcast_calculate_ah_prob",
        "description": "从比分矩阵计算亚盘覆盖率概率。",
        "input_schema": {
            "type": "object",
            "properties": {
                "score_matrix": {"type": "array", "description": "比分概率矩阵"},
                "ah_line": {"type": "number", "description": "亚盘线，如 -0.5"},
            },
            "required": ["score_matrix", "ah_line"],
        },
    },
    "goalcast_calculate_ev": {
        "name": "goalcast_calculate_ev",
        "description": "计算单方向的期望值。",
        "input_schema": {
            "type": "object",
            "properties": {
                "model_probability": {"type": "number"},
                "market_odds": {"type": "number"},
            },
            "required": ["model_probability", "market_odds"],
        },
    },
    "goalcast_calculate_kelly": {
        "name": "goalcast_calculate_kelly",
        "description": "计算凯利准则投注建议。",
        "input_schema": {
            "type": "object",
            "properties": {
                "model_probability": {"type": "number"},
                "market_odds": {"type": "number"},
                "fraction": {"type": "number", "description": "凯利分数，默认 0.25"},
                "bankroll": {"type": "number", "description": "总资金，可选"},
            },
            "required": ["model_probability", "market_odds"],
        },
    },
    "goalcast_calculate_risk_adjusted_ev": {
        "name": "goalcast_calculate_risk_adjusted_ev",
        "description": "计算风险调整后的 EV。",
        "input_schema": {
            "type": "object",
            "properties": {
                "raw_ev": {"type": "number"},
                "lineup_uncertainty": {"type": "boolean", "description": "阵容不确定性"},
                "market_low_confidence": {"type": "boolean", "description": "市场置信度低"},
                "data_quality": {"type": "string", "description": "数据质量: low/medium/high"},
            },
            "required": ["raw_ev"],
        },
    },
    "goalcast_calculate_confidence": {
        "name": "goalcast_calculate_confidence",
        "description": "计算比赛预测置信度。",
        "input_schema": {
            "type": "object",
            "properties": {
                "method": {"type": "string", "description": "方法: v2.5 或 v3.0"},
                "base_score": {"type": "integer"},
                "market_agrees": {"type": "boolean"},
                "data_complete": {"type": "boolean"},
                "understat_available": {"type": "boolean"},
                "odds_available": {"type": "boolean"},
                "lineup_unavailable": {"type": "boolean"},
                "xG_proxy_used": {"type": "boolean"},
                "market_disagrees": {"type": "boolean"},
                "data_quality_low": {"type": "boolean"},
                "understat_failed": {"type": "boolean"},
                "match_type_c": {"type": "boolean"},
                "major_uncertainty": {"type": "boolean"},
                "market_downgraded": {"type": "boolean"},
                "prediction_diverged": {"type": "boolean"},
            },
        },
    },
    "goalcast_run_review": {
        "name": "goalcast_run_review",
        "description": "执行赛后复盘。自动拉取实际赛果并与预测对比。",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    "goalcast_run_backtest": {
        "name": "goalcast_run_backtest",
        "description": "执行历史预测回测。计算 ROI、命中率、Brier Score 等。",
        "input_schema": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "开始日期 (YYYY-MM-DD)"},
                "end_date": {"type": "string", "description": "结束日期 (YYYY-MM-DD)"},
                "method": {"type": "string", "description": "模型版本，如 v4.0"},
            },
        },
    },
}


class ToolExecutor:
    """执行 Goalcast MCP 工具。通过 getattr 动态分发到 _tool_* 方法。"""

    async def execute(self, tool_name: str, params: dict) -> dict:
        handler = getattr(self, f"_tool_{tool_name}", None)
        if handler is None:
            logger.warning("[ToolExecutor] 未知工具: %s", tool_name)
            return {"error": f"unknown tool: {tool_name}"}
        try:
            result = await handler(**params)
            return _serialize_result(result)
        except Exception as exc:
            logger.error("[ToolExecutor] 工具执行异常 %s: %s", tool_name, exc)
            return {"error": str(exc), "tool": tool_name}

    # ── Sportmonks 工具 ──────────────────────────────────────────────

    async def _tool_goalcast_sportmonks_get_matches(
        self, date: str | None = None, league_ids: list[int] | None = None
    ) -> dict:
        from mcp_server.tools.sportmonks import _get_sportmonks_service
        service = _get_sportmonks_service()
        fixtures = await service.get_matches(date=date, league_ids=league_ids)
        from mcp_server.tools.sportmonks import _serialize
        data = _serialize(fixtures)
        return {"ok": True, "count": len(data), "data": data}

    async def _tool_goalcast_sportmonks_get_match(
        self, fixture_id: int, match_date: str | None = None
    ) -> dict:
        from mcp_server.tools.sportmonks import _get_sportmonks_service, _serialize
        service = _get_sportmonks_service()
        payload = await service.get_match_for_analysis(
            fixture_id=fixture_id, match_date=match_date
        )
        return {"ok": True, "data": _serialize(payload)}

    # ── FootyStats 工具 ─────────────────────────────────────────────

    async def _tool_goalcast_footystats_resolve_match(self, **params) -> dict:
        from datasource.datafusion.fusion import DataFusion
        from mcp_server.internal import get_footystats, get_understat

        fusion = DataFusion(footystats=get_footystats(), understat=get_understat())
        context = await fusion.build(
            fixture_id=params.get("match_id", ""),
            match_id=params.get("match_id", ""),
            home_team=params.get("home_team", ""),
            home_team_id=str(params.get("home_team_id", "")),
            away_team=params.get("away_team", ""),
            away_team_id=str(params.get("away_team_id", "")),
            season_id=str(params.get("season_id", "")),
            league=params.get("league", ""),
            match_date=params.get("match_date"),
            season=params.get("season"),
        )
        return context.to_dict()

    async def _tool_goalcast_footystats_get_todays_matches(
        self, date: str | None = None, league_filter: str | None = None
    ) -> list:
        import datetime as dt
        from mcp_server.internal import get_footystats, handle_api_call, _normalize_footystats_fixtures

        target_date = date or dt.date.today().isoformat()
        raw = await handle_api_call(
            "FootyStats",
            get_footystats().get_todays_matches(target_date, timezone=None),
        )
        return _normalize_footystats_fixtures(raw, league_filter)

    # ── Quant 工具 ──────────────────────────────────────────────────

    async def _tool_goalcast_calculate_poisson(
        self, home_lambda: float, away_lambda: float,
        max_goals: int = 6, model: str = "standard", rho: float = -0.13,
    ):
        from analytics.poisson import poisson_distribution, dixon_coles_distribution
        if model == "dixon_coles":
            return dixon_coles_distribution(home_lambda, away_lambda, max_goals, rho)
        return poisson_distribution(home_lambda, away_lambda, max_goals)

    async def _tool_goalcast_calculate_ah_prob(
        self, score_matrix: list, ah_line: float,
    ):
        from analytics.poisson import calculate_ah_probability
        return calculate_ah_probability(score_matrix, ah_line)

    async def _tool_goalcast_calculate_ev(
        self, model_probability: float, market_odds: float,
    ):
        from analytics.ev_calculator import calculate_ev
        return calculate_ev(model_probability, market_odds)

    async def _tool_goalcast_calculate_kelly(
        self, model_probability: float, market_odds: float,
        fraction: float = 0.25, bankroll: float | None = None,
    ):
        from analytics.ev_calculator import calculate_kelly
        return calculate_kelly(model_probability, market_odds, fraction, bankroll)

    async def _tool_goalcast_calculate_risk_adjusted_ev(
        self, raw_ev: float, lineup_uncertainty: bool = False,
        market_low_confidence: bool = False, data_quality: str = "medium",
    ):
        from analytics.ev_calculator import calculate_risk_adjusted_ev
        risk_adjusted_ev = calculate_risk_adjusted_ev(
            raw_ev, lineup_uncertainty, market_low_confidence, data_quality,
        )
        return {
            "raw_ev": raw_ev,
            "risk_adjusted_ev": risk_adjusted_ev,
            "recommendation": "bet" if risk_adjusted_ev > 0.05 else "no_bet",
        }

    async def _tool_goalcast_calculate_confidence(self, **params):
        from analytics.confidence import calculate_confidence, calculate_confidence_v25, confidence_breakdown
        method = params.pop("method", "v3.0")
        if method == "v2.5":
            score = calculate_confidence_v25(**params)
        else:
            score = calculate_confidence(**params)
        return {"confidence": score, "breakdown": confidence_breakdown(**params)}

    # ── Evaluation 工具 ─────────────────────────────────────────────

    async def _tool_goalcast_run_review(self) -> dict:
        import scripts.review_engine as re
        try:
            await re.review_matches()
            return {
                "status": "success",
                "message": "Review completed. Check data/results and diary/.",
            }
        except Exception as exc:
            return {"status": "error", "error": "REVIEW_ERROR", "message": str(exc)}

    async def _tool_goalcast_run_backtest(
        self, start_date: str | None = None,
        end_date: str | None = None, method: str | None = None,
    ) -> dict:
        import datetime as dt
        import json as _json
        import scripts.backtest_engine as bt

        today = dt.date.today().isoformat()
        effective_start = start_date or today
        effective_end = end_date or today

        predictions = bt.load_predictions(effective_start, effective_end, method)
        results = bt.load_results()
        if not predictions:
            return {
                "status": "warning",
                "message": f"No predictions for {effective_start} to {effective_end}.",
            }
        report = bt.generate_report(predictions, results, effective_start, effective_end)
        output_path = bt.BACKTESTS_DIR / f"backtest_{effective_start}_to_{effective_end}.json"
        bt.BACKTESTS_DIR.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            _json.dump(report, f, indent=2, ensure_ascii=False)
        bt.generate_markdown_report(report, str(output_path))
        report["status"] = "success"
        report["saved_to"] = str(output_path)
        return report


def _serialize_result(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, list):
        return [_serialize_result(item) for item in value]
    if isinstance(value, dict):
        return {k: _serialize_result(v) for k, v in value.items()}
    return value
```

- [ ] **Step 2: 确认 Sportmonks 工具所需的私有接口**

检查 `mcp_server/tools/sportmonks.py` 是否有 `_get_sportmonks_service` 辅助函数。如果没有，需要在 tool_executor 中自行初始化服务。

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast && grep -n "_get_sportmonks_service\|service_factory" mcp_server/tools/sportmonks.py
```

- [ ] **Step 3: 验证 tool_executor 可导入**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast && python -c "from agents.adapters.tool_executor import ToolExecutor, TOOL_SCHEMAS; print(f'TOOL_SCHEMAS: {len(TOOL_SCHEMAS)} tools'); print('OK')"
```

---

### Task 5: pipeline.py —— RD 循环步骤

**Files:**
- Create: `agents/core/pipeline.py`

- [ ] **Step 1: 实现 pipeline.py**

```python
# agents/core/pipeline.py
"""
RD 循环流水线步骤：Analyst → Trader → Reviewer → Reporter。
每个步骤由对应的 Agent 独立执行，通过 match_store 读取/写入比赛文件。
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from agents.core import match_store

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
_CST = timezone(timedelta(hours=8))


def _now_iso() -> str:
    return datetime.now(_CST).isoformat()


class MatchPipeline:
    def __init__(self, adapter, semi_mode: bool = False):
        self.adapter = adapter
        self.semi_mode = semi_mode

    # ── Analyst 步骤 ────────────────────────────────────────────────

    async def run_analyst_step(self, record: dict) -> dict:
        match_id = record["match_id"]
        orche = record.get("orchestrator", {})
        prompt = self._build_analyst_prompt(orche)
        result = await self.adapter.run_agent("analyst", prompt)
        analysis = self._parse_analysis_output(result.final_text, orche)
        analysis["analyzed_at"] = _now_iso()
        match_store.append_layer(match_id, "analysis", analysis)
        logger.info("[Pipeline] Analyst 完成: %s", match_id)
        return analysis

    def _build_analyst_prompt(self, orche: dict) -> str:
        model_ver = orche.get("model_version", "v4.0")
        return (
            f"分析以下比赛:\n"
            f"- 赛事: {orche.get('home_team')} vs {orche.get('away_team')}\n"
            f"- 联赛: {orche.get('league')}\n"
            f"- 数据源: {orche.get('data_source', 'sportmonks')}\n"
            f"- 模型版本: {model_ver}\n"
            f"- 开球时间: {orche.get('kickoff_time')}\n"
            f"- fixture_id: {orche.get('fixture_id')}\n"
            f"\n请调用 goalcast_sportmonks_get_match 获取比赛详情，"
            f"然后依次调用 goalcast_calculate_poisson / goalcast_calculate_ah_prob / "
            f"goalcast_calculate_ev / goalcast_calculate_confidence 等工具执行完整量化分析。"
            f"最终以 JSON 格式输出分析结果，包含 home_xg, away_xg, ah_recommendation, confidence 等字段。"
        )

    def _parse_analysis_output(self, text: str, orche: dict) -> dict:
        json_match = re.search(r"\{[\s\S]*\}", text)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        return {
            "home_xg": 0.0,
            "away_xg": 0.0,
            "raw_output": text[:2000],
            "note": "failed to parse structured JSON from agent output",
        }

    # ── Trader 步骤 ─────────────────────────────────────────────────

    async def run_trader_step(self, record: dict) -> dict:
        match_id = record["match_id"]
        analysis = record.get("analysis", {})
        orche = record.get("orchestrator", {})
        prompt = (
            f"基于以下比赛分析结果做出交易决策:\n"
            f"比赛: {orche.get('home_team')} vs {orche.get('away_team')}\n"
            f"分析结果:\n{json.dumps(analysis, ensure_ascii=False, indent=2)}\n"
            f"\n请调用 goalcast_calculate_kelly / goalcast_calculate_risk_adjusted_ev 等工具，"
            f"生成亚盘方向的交易指令。最终以 JSON 格式输出交易决策。"
        )
        result = await self.adapter.run_agent("trader", prompt)
        trade = self._parse_trade_output(result.final_text)
        trade["traded_at"] = _now_iso()
        match_store.append_layer(match_id, "trade", trade)
        logger.info("[Pipeline] Trader 完成: %s", match_id)
        return trade

    def _parse_trade_output(self, text: str) -> dict:
        json_match = re.search(r"\{[\s\S]*\}", text)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        return {"raw_output": text[:2000], "note": "failed to parse structured JSON"}

    # ── Reviewer 步骤 ───────────────────────────────────────────────

    async def run_reviewer_step(self, record: dict) -> str:
        match_id = record["match_id"]
        analysis = record.get("analysis", {})
        trade = record.get("trade", {})
        orche = record.get("orchestrator", {})
        prompt = (
            f"审核以下比赛的预测和交易决策:\n"
            f"比赛: {orche.get('home_team')} vs {orche.get('away_team')}\n"
            f"分析:\n{json.dumps(analysis, ensure_ascii=False, indent=2)}\n"
            f"交易:\n{json.dumps(trade, ensure_ascii=False, indent=2)}\n"
            f"\n请检查 xG ↔ AH 方向是否一致、赔率是否合理、凯利注额是否审慎。"
            f"输出审核结论: VERDICT: approved | feedback | rejected\n"
            f"如果 feedback，说明具体改进建议。"
        )
        result = await self.adapter.run_agent("reviewer", prompt)
        verdict = self._parse_verdict(result.final_text)
        review_data = {
            "verdict": verdict,
            "checks": {},
            "notes": result.final_text[:1000],
            "reviewed_at": _now_iso(),
        }
        match_store.append_layer(match_id, "review", review_data)

        if verdict == "feedback":
            match_store.update_status(match_id, "feedback")
            logger.info("[Pipeline] Reviewer 打回: %s", match_id)
        elif verdict == "rejected":
            match_store.update_status(match_id, "rejected")
            logger.info("[Pipeline] Reviewer 拒绝: %s", match_id)
        else:
            logger.info("[Pipeline] Reviewer 通过: %s", match_id)
        return verdict

    def _parse_verdict(self, text: str) -> str:
        m = re.search(r"VERDICT:\s*(approved|feedback|rejected)", text, re.IGNORECASE)
        if m:
            return m.group(1).lower()
        if "通过" in text or "approved" in text.lower():
            return "approved"
        if "打回" in text or "feedback" in text.lower():
            return "feedback"
        return "rejected"

    # ── Reporter 步骤 ───────────────────────────────────────────────

    async def run_reporter_step(self, match_ids: list[str]) -> str:
        records = []
        for mid in match_ids:
            r = match_store.load(mid)
            if r and r.get("review", {}).get("verdict") == "approved":
                records.append(r)

        if not records:
            logger.warning("[Pipeline] Reporter 无已审核比赛可报告")
            return ""

        prompt = (
            f"为以下 {len(records)} 场已审核通过的比赛生成赛事洞察报告:\n"
            f"{json.dumps(records, ensure_ascii=False, indent=2)}\n"
            f"\n请以 Markdown 格式输出结构化报告，包含赛事摘要、xG 分析、亚盘推荐、风险提示。"
        )
        result = await self.adapter.run_agent("reporter", prompt)
        report_content = result.final_text

        today = datetime.now(_CST).strftime("%Y-%m-%d")
        reports_dir = match_store.MATCHES_DIR.parent / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        report_path = reports_dir / f"{today}.md"
        report_path.write_text(report_content, encoding="utf-8")
        report_ref = str(report_path.relative_to(match_store.MATCHES_DIR.parent))

        for mid in match_ids:
            match_store.finalize(mid, report_ref=report_ref)

        logger.info("[Pipeline] Reporter 完成: %s (%d 场比赛)", report_ref, len(records))
        return report_ref
```

- [ ] **Step 2: 验证 pipeline 模块可导入**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast && python -c "from agents.core.pipeline import MatchPipeline; print('OK')"
```

---

### Task 6: orchestrator.py —— 异步并行 RD 循环

**Files:**
- Create: `agents/core/orchestrator.py`

- [ ] **Step 1: 实现 orchestrator.py**

```python
# agents/core/orchestrator.py
"""
异步并行 RD 循环编排器。
4 路 asyncio.Task 通过 match_store 解耦：
  _orchestrator_loop → _analyst_loop → _trader_loop → _reviewer_loop → _reporter_loop
"""

from __future__ import annotations

import asyncio
import json
import logging
import signal
from pathlib import Path
from typing import Any

from agents.core import match_store
from agents.core.pipeline import MatchPipeline

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 600
IDLE_SLEEP_SECONDS = 5
BACKLOG_LIMIT = 20

LEAGUES_JSON_PATH = Path(__file__).parent.parent / "roles" / "analyst" / "sportmonks_leagues.json"


class Orchestrator:
    def __init__(self, adapter, semi_mode: bool = False):
        self.adapter = adapter
        self.semi_mode = semi_mode
        self.stop_event = asyncio.Event()
        self.pipeline = MatchPipeline(adapter, semi_mode)

    async def run(
        self,
        leagues: list[str] | None = None,
        date: str | None = None,
        max_matches: int | None = None,
    ) -> dict:
        signal.signal(signal.SIGINT, lambda s, f: self.stop_event.set())
        signal.signal(signal.SIGTERM, lambda s, f: self.stop_event.set())

        fetched = await self._fetch_and_prepare(leagues, date)
        logger.info("[Orchestrator] 已准备 %d 场比赛", fetched)

        tasks = [
            asyncio.create_task(self._analyst_loop()),
            asyncio.create_task(self._trader_loop()),
            asyncio.create_task(self._reviewer_loop()),
            asyncio.create_task(self._reporter_loop()),
        ]

        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

        reviewed = match_store.list_all(status="reviewed")
        reported = match_store.list_all(status="reported")
        return {
            "prepared": fetched,
            "reviewed": len(reviewed),
            "reported": len(reported),
        }

    async def _fetch_and_prepare(
        self, leagues: list[str] | None, date: str | None
    ) -> int:
        from agents.adapters.tool_executor import ToolExecutor

        executor = ToolExecutor()
        from datetime import datetime, timedelta, timezone
        _CST = timezone(timedelta(hours=8))
        today = date or datetime.now(_CST).strftime("%Y-%m-%d")

        league_ids = None
        if leagues:
            league_ids = self._resolve_league_ids(leagues)
            if not league_ids:
                logger.warning("[Orchestrator] 联赛字典中未找到: %s", leagues)
                return 0

        result = await executor._tool_goalcast_sportmonks_get_matches(
            date=today, league_ids=league_ids,
        )
        fixtures = result.get("data", [])

        count = 0
        for fixture in fixtures:
            match_id = match_store.generate_match_id()
            record = {
                "schema_version": "1.0",
                "match_id": match_id,
                "status": "pending",
                "orchestrator": {
                    "fixture_id": fixture.get("fixture_id", fixture.get("id")),
                    "home_team": fixture.get("home_team", fixture.get("name", "").split(" vs ")[0]),
                    "away_team": fixture.get("away_team", fixture.get("name", "").split(" vs ")[-1]),
                    "league": fixture.get("league", fixture.get("league_name", "")),
                    "kickoff_time": fixture.get("kickoff_time", fixture.get("starting_at", "")),
                    "data_source": "sportmonks",
                    "model_version": "v4.0",
                    "prepared_at": datetime.now(_CST).isoformat(),
                },
            }
            match_store.save(record)
            count += 1
        return count

    def _resolve_league_ids(self, leagues: list[str]) -> list[int] | None:
        if not LEAGUES_JSON_PATH.exists():
            return None
        try:
            league_dict = json.loads(LEAGUES_JSON_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, IOError):
            return None

        ids = []
        for name in leagues:
            name_lower = name.lower()
            for key, value in league_dict.items():
                if name_lower in key.lower() or name_lower in str(value).lower():
                    if isinstance(value, dict) and "id" in value:
                        ids.append(value["id"])
                    elif isinstance(value, (int, float)):
                        ids.append(int(value))
        return list(set(ids)) if ids else None

    async def _analyst_loop(self):
        while not self.stop_event.is_set():
            record = match_store.claim_oldest(["pending"], "analyzing")
            if record is None:
                await self._sleep(IDLE_SLEEP_SECONDS)
                continue
            try:
                await self.pipeline.run_analyst_step(record)
            except Exception as exc:
                logger.error("[Orchestrator] Analyst 异常: %s", exc)
                match_store.update_status(record["match_id"], "pending")

    async def _trader_loop(self):
        while not self.stop_event.is_set():
            record = match_store.claim_oldest(
                ["analyzed", "feedback"], "trading"
            )
            if record is None:
                await self._sleep(IDLE_SLEEP_SECONDS)
                continue
            try:
                await self.pipeline.run_trader_step(record)
            except Exception as exc:
                logger.error("[Orchestrator] Trader 异常: %s", exc)
                match_store.update_status(record["match_id"], "analyzed")

    async def _reviewer_loop(self):
        while not self.stop_event.is_set():
            record = match_store.claim_oldest(["traded"], "reviewing")
            if record is None:
                await self._sleep(IDLE_SLEEP_SECONDS)
                continue
            try:
                await self.pipeline.run_reviewer_step(record)
            except Exception as exc:
                logger.error("[Orchestrator] Reviewer 异常: %s", exc)
                match_store.update_status(record["match_id"], "traded")

    async def _reporter_loop(self):
        batch_size = 10
        while not self.stop_event.is_set():
            reviewed = match_store.list_all(status="reviewed")
            if len(reviewed) < batch_size:
                await self._sleep(IDLE_SLEEP_SECONDS * 2)
                continue
            batch = reviewed[:batch_size]
            match_ids = [r["match_id"] for r in batch]
            try:
                await self.pipeline.run_reporter_step(match_ids)
            except Exception as exc:
                logger.error("[Orchestrator] Reporter 异常: %s", exc)
            await self._sleep(IDLE_SLEEP_SECONDS)

    async def _sleep(self, seconds: float):
        try:
            await asyncio.wait_for(
                self.stop_event.wait(), timeout=seconds
            )
        except asyncio.TimeoutError:
            pass


async def run_standalone(
    adapter: Any,
    role_path: str,
    user_message: str,
) -> Any:
    return await adapter.run_agent(role_path, user_message)
```

- [ ] **Step 2: 验证 orchestrator 模块可导入**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast && python -c "from agents.core.orchestrator import Orchestrator; print('OK')"
```

---

### Task 7: directory_agent.py 改造 —— 支持 AgentDefinition

**Files:**
- Modify: `agents/core/directory_agent.py`

- [ ] **Step 1: 在现有 AgentConfig 后追加 AgentDefinition 并新增 load_agent 方法**

原文件保持不变，在 `DirectoryAgentLoader` 类中新增 `load_agent` 方法。在 `DirectoryAgent` 类中也新增 `load_agent` 方法。

```python
# 在 AgentConfig 类之后新增（第12行之后）:
@dataclass
class AgentDefinition:
    role_path: str
    system_prompt: str
    tool_registry: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def role_name(self) -> str:
        return self.role_path.split("/")[-1] if "/" in self.role_path else self.role_path
    
    @property
    def allowed_mcp_tools(self) -> List[str]:
        mcp_tools = self.tool_registry.get("mcp", [])
        return [t["name"] for t in mcp_tools if isinstance(t, dict) and "name" in t]
    
    @property
    def allowed_builtin_tools(self) -> List[str]:
        return self.tool_registry.get("builtin", {}).get("include", [])
    
    @property
    def allowed_tools(self) -> List[str]:
        return self.allowed_mcp_tools + self.allowed_builtin_tools


# DirectoryAgentLoader 新增方法 (在第30行之后):
    @staticmethod
    def load_agent(role_dir: str) -> AgentDefinition:
        config = DirectoryAgentLoader.load(role_dir)
        return AgentDefinition(
            role_path=role_dir,
            system_prompt=config.system_prompt,
            tool_registry=config.tools,
        )

# DirectoryAgent 新增方法 (在第53行之后):
    def load_agent(self) -> AgentDefinition:
        return DirectoryAgentLoader.load_agent(self.role_dir)
```

- [ ] **Step 2: 应用修改**

SearchReplace 精确定位并替换：

**第一个替换**（第11-12行之间插入 AgentDefinition）:
- SEARCH: `from agents.llm_router import generate_response\nimport json\n\n@dataclass\nclass AgentConfig:`
- 在 `@dataclass\nclass AgentConfig:` 之后插入 AgentDefinition

**第二个替换**（在 `DirectoryAgentLoader.load` 方法后插入 `load_agent`）:
- SEARCH: `return AgentConfig(system_prompt=system_prompt, tools=tools)\n\nclass DirectoryAgent`
- 在 `return AgentConfig...` 后插入 `load_agent` 静态方法

**第三个替换**（在 `DirectoryAgent.execute` 方法后插入 `load_agent`）:
- SEARCH: `state.current_step = f"{self.name}_DONE"\n        return state`
- 之后插入 `load_agent` 实例方法

- [ ] **Step 3: 验证导入和功能**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast && python -c "
from agents.core.directory_agent import AgentDefinition, DirectoryAgentLoader
agent_def = DirectoryAgentLoader.load_agent('backend/agents/roles/orchestrator')
print(f'Role: {agent_def.role_name}')
print(f'System prompt length: {len(agent_def.system_prompt)}')
print(f'MCP tools: {agent_def.allowed_mcp_tools}')
print(f'Builtin tools: {agent_def.allowed_builtin_tools}')
print('OK')
"
```

---

### Task 8: 更新 6 个 Agent 的 tool-registry.jsonc

**Files:**
- Modify: `backend/agents/roles/orchestrator/tool-registry.jsonc`
- Modify: `backend/agents/roles/analyst/tool-registry.jsonc`
- Modify: `backend/agents/roles/trader/tool-registry.jsonc`
- Modify: `backend/agents/roles/reviewer/tool-registry.jsonc`
- Modify: `backend/agents/roles/reporter/tool-registry.jsonc`
- Modify: `backend/agents/roles/backtester/tool-registry.jsonc`

- [ ] **Step 1: Orchestrator 工具注册**

```jsonc
{
  "version": 1,
  "preset": "none",
  "builtin": {"include":["web_search","web_fetch","memory_search","memory_get"],"exclude":[]},
  "mcp": [
    {"name": "goalcast_sportmonks_get_matches"},
    {"name": "goalcast_sportmonks_get_match"},
    {"name": "goalcast_footystats_get_todays_matches"}
  ],
  "conditional": [],
  "notes": "Orchestrator: 总管，负责赛程拉取、联赛校验、数据准备。"
}
```

- [ ] **Step 2: Analyst 工具注册**

```jsonc
{
  "version": 1,
  "preset": "none",
  "builtin": {"include":["web_search","web_fetch"],"exclude":[]},
  "mcp": [
    {"name": "goalcast_sportmonks_get_match"},
    {"name": "goalcast_footystats_resolve_match"},
    {"name": "goalcast_calculate_poisson"},
    {"name": "goalcast_calculate_ah_prob"},
    {"name": "goalcast_calculate_ev"},
    {"name": "goalcast_calculate_confidence"}
  ],
  "conditional": [],
  "notes": "Analyst: 量化分析，获取比赛详情 + 执行泊松/EV/置信度计算。"
}
```

- [ ] **Step 3: Trader 工具注册**

```jsonc
{
  "version": 1,
  "preset": "none",
  "builtin": {"include":["web_search","web_fetch"],"exclude":[]},
  "mcp": [
    {"name": "goalcast_calculate_kelly"},
    {"name": "goalcast_calculate_risk_adjusted_ev"},
    {"name": "goalcast_calculate_ev"}
  ],
  "conditional": [],
  "notes": "Trader: 交易决策，执行凯利计算和风控评估。"
}
```

- [ ] **Step 4: Reviewer 工具注册**

```jsonc
{
  "version": 1,
  "preset": "none",
  "builtin": {"include":["web_search","web_fetch"],"exclude":[]},
  "mcp": [
    {"name": "goalcast_run_review"},
    {"name": "goalcast_calculate_ev"}
  ],
  "conditional": [],
  "notes": "Reviewer: 赛前审核预测+交易合理性，赛后拉取赛果复盘。"
}
```

- [ ] **Step 5: Reporter 工具注册**

```jsonc
{
  "version": 1,
  "preset": "none",
  "builtin": {"include":["web_search","web_fetch"],"exclude":[]},
  "mcp": [],
  "conditional": [],
  "notes": "Reporter: 报告生成，读取已审核比赛生成 Markdown 洞察报告。不直接调用数据 MCP 工具。"
}
```

- [ ] **Step 6: Backtester 工具注册**

```jsonc
{
  "version": 1,
  "preset": "none",
  "builtin": {"include":["web_search","web_fetch"],"exclude":[]},
  "mcp": [
    {"name": "goalcast_run_backtest"}
  ],
  "conditional": [],
  "notes": "Backtester: 批量回测历史预测，计算 ROI/Hit Rate/Brier Score。"
}
```

- [ ] **Step 7: 验证所有工具注册可被 loader 正确解析**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast && python -c "
from agents.core.directory_agent import DirectoryAgentLoader
roles = ['orchestrator','analyst','trader','reviewer','reporter','backtester']
for role in roles:
    path = f'agents/roles/{role}'
    agent_def = DirectoryAgentLoader.load_agent(path)
    print(f'{role}: mcp_tools={agent_def.allowed_mcp_tools}')
print('All roles loaded successfully')
"
```

---

### Task 9: 更新 6 个 Agent 的 AGENTS.md

**Files:**
- Modify: `backend/agents/roles/orchestrator/AGENTS.md`
- Modify: `backend/agents/roles/analyst/AGENTS.md`
- Modify: `backend/agents/roles/trader/AGENTS.md`
- Modify: `backend/agents/roles/reviewer/AGENTS.md`
- Modify: `backend/agents/roles/reporter/AGENTS.md`
- Modify: `backend/agents/roles/backtester/AGENTS.md`

- [ ] **Step 1: Orchestrator AGENTS.md —— 从"调度执行者"改为"总管/环境感知"**

在每个 AGENTS.md 文件末尾追加 `## 独立运行模式` 章节。内容：

**Orchestrator**:
```markdown
## 独立运行模式

作为总管，你的核心职责是：
1. 接收用户请求（联赛名、日期），校验联赛字典 `agents/roles/analyst/sportmonks_leagues.json`
2. 调用 `goalcast_sportmonks_get_matches` 拉取赛程
3. 将每场比赛写入 `data/matches/{match_id}.json`（status: pending）
4. 后续由 Analyst → Trader → Reviewer → Reporter 循环自动完成

你不需要亲自做分析。你的输出是结构化的 pending 比赛文件。
```

**Analyst**:
```markdown
## 独立运行模式

你的输入是 `data/matches/` 中 `status=pending` 的比赛文件。
你的任务：
1. 读取比赛的 `orchestrator` 字段获取 fixture_id 等参数
2. 调用 `goalcast_sportmonks_get_match` 获取比赛详情
3. 依次调用量化工具 (poisson → ah_prob → ev → confidence) 完成分析
4. 将分析结果写入同一文件的 `analysis` 字段

输出格式: JSON，包含 home_xg, away_xg, ah_recommendation, confidence 等字段。
```

**Trader**:
```markdown
## 独立运行模式

你的输入是 `data/matches/` 中 `status=analyzed`（或 feedback）的比赛文件。
你的任务：
1. 读取 `analysis` 字段获取预测概率和推荐方向
2. 调用 `goalcast_calculate_kelly` 计算凯利注额
3. 调用 `goalcast_calculate_risk_adjusted_ev` 评估风险
4. 将交易决策写入同一文件的 `trade` 字段

输出格式: JSON，包含 direction, ah_line, best_odds, stake 等字段。
```

**Reviewer**:
```markdown
## 独立运行模式

你有两种模式：

### 赛前审核
输入是 `data/matches/` 中 `status=traded` 的比赛文件。
1. 校验 xG ↔ AH 方向是否自洽
2. 校验赔率区间是否合理
3. 校验凯利注额是否审慎
4. 输出 VERDICT: approved | feedback | rejected
   - approved → 比赛进入 Reporter 队列
   - feedback → 比赛回到 Trader 重试（最多3次）
   - rejected → 比赛标记为废弃

### 赛后复盘
调用 `goalcast_run_review` 拉取实际赛果，比对预测。
```

**Reporter**:
```markdown
## 独立运行模式

你的输入是 `data/matches/` 中 `status=reviewed`（verdict=approved）的比赛文件。
你的任务：
1. 批量读取已审核通过的比赛
2. 重构叙事逻辑（xG 解读、亚盘推荐、风险提示）
3. 生成结构化 Markdown 报告
4. 保存到 `data/reports/{date}.md`

报告模板应包含: 赛事摘要 → xG 分析 → 亚盘推荐 → 风险提示。
```

**Backtester**:
```markdown
## 独立运行模式

你的输入是指定的日期范围。
你的任务：
1. 调用 `goalcast_run_backtest` 执行全量历史回测
2. 汇总 ROI、Hit Rate、Brier Score、Sharpe 等指标
3. 按联赛/模型版本分组统计
4. 输出保存到 `data/backtests/` 目录
```

- [ ] **Step 2: 验证所有角色仍可被正确加载**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast && python -c "
from agents.core.directory_agent import DirectoryAgentLoader
for role in ['orchestrator','analyst','trader','reviewer','reporter','backtester']:
    config = DirectoryAgentLoader.load(f'agents/roles/{role}')
    assert '独立运行模式' in config.system_prompt, f'{role} missing 独立运行模式'
    print(f'{role}: OK ({len(config.system_prompt)} chars)')
"
```

---

### Task 10: main.py —— CLI 入口

**Files:**
- Create: `main.py`

- [ ] **Step 1: 实现 main.py**

```python
#!/usr/bin/env python3
"""
Goalcast CLI —— 足球量化分析系统。

Subcommands:
  run      一键启动 RD 循环（Orchestrator → Analyst → Trader → Reviewer → Reporter）
  analyze  单独跑 Analyst
  trade    单独跑 Trader
  review   单独跑 Reviewer
  report   单独跑 Reporter
  backtest 单独跑 Backtester
  status   查看系统状态
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

from dotenv import load_dotenv

load_dotenv()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="goalcast",
        description="Goalcast 足球量化分析系统",
    )
    subparsers = parser.add_subparsers(dest="command")

    # run
    run_parser = subparsers.add_parser("run", help="一键启动 RD 循环")
    run_parser.add_argument("--leagues", nargs="+", default=["英超"], help="目标联赛")
    run_parser.add_argument("--date", help="日期 (YYYY-MM-DD)，默认今天")
    run_parser.add_argument("--mode", choices=["full", "semi"], default="full")
    run_parser.add_argument("--model", default=None, help="Claude 模型名")

    # analyze
    analyze_parser = subparsers.add_parser("analyze", help="单独跑 Analyst")
    analyze_parser.add_argument("--match-file", required=True, help="比赛 JSON 文件路径")
    analyze_parser.add_argument("--model", default=None)

    # trade
    trade_parser = subparsers.add_parser("trade", help="单独跑 Trader")
    trade_parser.add_argument("--match-file", required=True)
    trade_parser.add_argument("--model", default=None)

    # review
    review_parser = subparsers.add_parser("review", help="单独跑 Reviewer")
    review_parser.add_argument("--match-file", required=True)
    review_parser.add_argument("--model", default=None)

    # report
    report_parser = subparsers.add_parser("report", help="单独跑 Reporter")
    report_parser.add_argument("--match-files", nargs="+", required=True)
    report_parser.add_argument("--model", default=None)

    # backtest
    backtest_parser = subparsers.add_parser("backtest", help="单独跑 Backtester")
    backtest_parser.add_argument("--start-date", default=None)
    backtest_parser.add_argument("--end-date", default=None)
    backtest_parser.add_argument("--method", default=None)

    # status
    subparsers.add_parser("status", help="查看系统状态")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    asyncio.run(_dispatch(args))


async def _dispatch(args: argparse.Namespace) -> None:
    from agents.adapters import ClaudeAdapter, ToolExecutor
    from agents.core.directory_agent import DirectoryAgentLoader

    loader = DirectoryAgentLoader()
    executor = ToolExecutor()

    model = getattr(args, "model", None) or os.environ.get(
        "GOALCAST_MODEL", "claude-sonnet-4-20250514"
    )

    if args.command == "run":
        from agents.core.orchestrator import Orchestrator

        adapter = ClaudeAdapter(model=model, executor=executor, loader=loader)
        orch = Orchestrator(adapter, semi_mode=(args.mode == "semi"))
        result = await orch.run(leagues=args.leagues, date=args.date)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == "analyze":
        adapter = ClaudeAdapter(model=model, executor=executor, loader=loader)
        from agents.core import match_store
        record = match_store.load_from_file(args.match_file)
        if record is None:
            record = json.loads(open(args.match_file, encoding="utf-8").read())
        from agents.core.pipeline import MatchPipeline
        pipeline = MatchPipeline(adapter)
        result = await pipeline.run_analyst_step(record)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == "trade":
        adapter = ClaudeAdapter(model=model, executor=executor, loader=loader)
        from agents.core import match_store
        record = match_store.load_from_file(args.match_file)
        if record is None:
            record = json.loads(open(args.match_file, encoding="utf-8").read())
        from agents.core.pipeline import MatchPipeline
        pipeline = MatchPipeline(adapter)
        result = await pipeline.run_trader_step(record)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == "review":
        adapter = ClaudeAdapter(model=model, executor=executor, loader=loader)
        from agents.core import match_store
        record = match_store.load_from_file(args.match_file)
        if record is None:
            record = json.loads(open(args.match_file, encoding="utf-8").read())
        from agents.core.pipeline import MatchPipeline
        pipeline = MatchPipeline(adapter)
        result = await pipeline.run_reviewer_step(record)
        print(f"Verdict: {result}")

    elif args.command == "report":
        adapter = ClaudeAdapter(model=model, executor=executor, loader=loader)
        from agents.core.pipeline import MatchPipeline
        pipeline = MatchPipeline(adapter)
        result = await pipeline.run_reporter_step(args.match_files)
        print(f"Report saved: {result}")

    elif args.command == "backtest":
        result = await executor._tool_goalcast_run_backtest(
            start_date=args.start_date,
            end_date=args.end_date,
            method=args.method,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == "status":
        from agents.core import match_store
        statuses = ["pending", "analyzed", "traded", "reviewed", "reported", "feedback", "rejected"]
        print("=== Goalcast 系统状态 ===")
        for s in statuses:
            count = match_store.count_by_status([s])
            if count > 0:
                print(f"  {s}: {count}")
        all_records = match_store.list_all()
        if not all_records:
            print("  (无比赛记录)")
        print(f"  总计: {len(all_records)} 场比赛")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 验证 CLI 可正常运行（help 输出）**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast && python main.py --help
```

期望：显示所有子命令。

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast && python main.py run --help
cd /Users/zhengningdai/workspace/skyold/Goalcast && python main.py status
```

- [ ] **Step 3: match_store 增加 load_from_file 接口**

```bash
# 在 agents/core/match_store.py 中追加:
def load_from_file(filepath: str) -> dict | None:
    """从指定文件路径加载比赛记录（用于 CLI 单独运行模式）。"""
    try:
        return json.loads(Path(filepath).read_text(encoding="utf-8"))
    except (json.JSONDecodeError, IOError):
        return None
```

---

### Task 11: 集成验证

- [ ] **Step 1: 端到端导入验证**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast && python -c "
from agents.core.match_store import save, load, append_layer, claim_oldest, list_all, finalize
from agents.adapters import ClaudeAdapter, AgentResult, ToolExecutor
from agents.adapters.tool_executor import TOOL_SCHEMAS
from agents.core.directory_agent import AgentDefinition, DirectoryAgentLoader
from agents.core.pipeline import MatchPipeline
from agents.core.orchestrator import Orchestrator
print('All imports successful')
print(f'Tools: {len(TOOL_SCHEMAS)}')
"
```

- [ ] **Step 2: 运行 match_store 测试**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast && python -m pytest tests/core/test_match_store.py -v
```

- [ ] **Step 3: 运行 adapter 测试**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast && python -m pytest tests/core/test_adapter.py -v
```

- [ ] **Step 4: 运行现有全量测试确保无回归**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast && python -m pytest tests/ -v --tb=short
```

---

## Self-Review

1. **Spec coverage**: 设计中的所有需求都已覆盖：match_store（单文件追踪）、adapter（Agentic Loop）、tool_executor（12 个 MCP 工具）、pipeline（4 步骤）、orchestrator（4 路异步循环）、main.py（6 子命令 CLI）、directory_agent 改造（AgentDefinition）、角色文件更新（tool-registry + AGENTS.md）

2. **Placeholder scan**: 无 TBD、TODO 或"implement later"

3. **Type consistency**: AgentResult 在两个地方定义一致（adapter.py 的 dataclass + adapters/__init__.py 的 re-export）；MatchPipeline 的方法签名在 pipeline.py 和 orchestrator.py 中的调用一致；match_store 的接口在 pipeline.py 和 orchestrator.py 中使用一致

4. **与 yclake 一致性**: match_store ↔ hypothesis_store、pipeline ↔ rd_pipeline、orchestrator ↔ rd_orchestrator、adapter ↔ ClaudeAdapter，模式完全对齐

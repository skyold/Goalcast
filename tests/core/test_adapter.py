import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.adapters.adapter import (
    AgentResult,
    ClaudeAdapter,
    get_schemas_for_tools,
    _extract_text,
    MAX_TOOL_ROUNDS,
)


class FakeLoader:
    def __init__(self, system_prompt="", allowed_tools=None):
        self._system_prompt = system_prompt
        self._allowed_tools = allowed_tools or []
        self.last_role_path = None

    def load_agent(self, role_path: str):
        from agents.core.directory_agent import AgentDefinition

        self.last_role_path = role_path
        return AgentDefinition(
            role_path=role_path,
            system_prompt=self._system_prompt,
            tool_registry={
                "mcp": [{"name": t} for t in self._allowed_tools],
                "builtin": {"include": []},
            },
        )


class FakeExecutor:
    def __init__(self, responses=None):
        self.responses = responses or {}
        self.calls = []

    async def execute(self, tool_name, params):
        self.calls.append({"tool": tool_name, "params": params})
        return self.responses.get(tool_name, {"ok": True, "result": "mock"})


def _make_tool_use_block(name, input_data, block_id="toolu_001"):
    block = MagicMock()
    block.type = "tool_use"
    block.name = name
    block.input = input_data
    block.id = block_id
    return block


def _make_text_block(text):
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


def _make_response(stop_reason, content_blocks):
    response = MagicMock()
    response.stop_reason = stop_reason
    response.content = content_blocks
    return response


class TestAgentResult:
    def test_dataclass_fields(self):
        result = AgentResult(
            role_path="analyst",
            final_text="done",
            tool_calls=[{"tool": "x"}],
            rounds=3,
        )
        assert result.role_path == "analyst"
        assert result.final_text == "done"
        assert len(result.tool_calls) == 1
        assert result.rounds == 3


class TestGetSchemasForTools:
    def test_known_tools_return_schemas(self):
        schemas = get_schemas_for_tools([
            "goalcast_calculate_poisson",
            "goalcast_calculate_ev",
        ])
        assert len(schemas) == 2
        assert schemas[0]["name"] == "goalcast_calculate_poisson"

    def test_unknown_tool_skipped(self):
        schemas = get_schemas_for_tools(["nonexistent_tool"])
        assert len(schemas) == 0

    def test_mixed_known_and_unknown(self):
        schemas = get_schemas_for_tools(
            ["goalcast_calculate_ev", "unknown_tool_xyz"]
        )
        assert len(schemas) == 1
        assert schemas[0]["name"] == "goalcast_calculate_ev"

    def test_empty_list(self):
        schemas = get_schemas_for_tools([])
        assert schemas == []


class TestExtractText:
    def test_extracts_text_from_text_block(self):
        response = _make_response("end_turn", [_make_text_block("hello world")])
        assert _extract_text(response) == "hello world"

    def test_skips_non_text_blocks(self):
        response = _make_response(
            "end_turn",
            [_make_tool_use_block("x", {}), _make_text_block("result")],
        )
        assert _extract_text(response) == "result"

    def test_no_text_returns_empty(self):
        response = _make_response("end_turn", [])
        assert _extract_text(response) == ""


class TestClaudeAdapterInit:
    @patch("anthropic.AsyncAnthropic")
    def test_default_model(self, mock_client_cls):
        mock_client_cls.return_value = MagicMock()
        adapter = ClaudeAdapter(
            executor=FakeExecutor(),
            loader=FakeLoader("sys prompt"),
        )
        assert adapter.model == "claude-sonnet-4-20250514"
        assert adapter.max_tokens == 16384
        assert isinstance(adapter.executor, FakeExecutor)
        assert isinstance(adapter.loader, FakeLoader)

    @patch("anthropic.AsyncAnthropic")
    def test_custom_model_and_tokens(self, mock_client_cls):
        mock_client_cls.return_value = MagicMock()
        adapter = ClaudeAdapter(
            model="claude-haiku",
            max_tokens=1024,
            executor=FakeExecutor(),
            loader=FakeLoader(),
        )
        assert adapter.model == "claude-haiku"
        assert adapter.max_tokens == 1024


@pytest.mark.asyncio
class TestClaudeAdapterRunAgent:
    @patch("anthropic.AsyncAnthropic")
    async def test_end_turn_immediately(self, mock_cls):
        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        mock_client.messages.create = AsyncMock(
            return_value=_make_response("end_turn", [_make_text_block("分析结果: OK")])
        )

        adapter = ClaudeAdapter(
            executor=FakeExecutor(),
            loader=FakeLoader("系统提示", ["goalcast_calculate_ev"]),
        )

        result = await adapter.run_agent("analyst", "分析这场比赛")

        assert result.role_path == "analyst"
        assert result.final_text == "分析结果: OK"
        assert result.rounds == 1
        assert len(result.tool_calls) == 0

    @patch("anthropic.AsyncAnthropic")
    async def test_tool_use_then_end_turn(self, mock_cls):
        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        call_count = [0]

        async def side_effect(**kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return _make_response(
                    "tool_use",
                    [_make_tool_use_block(
                        "goalcast_calculate_ev",
                        {"model_probability": 0.6, "market_odds": 1.9},
                    )],
                )
            else:
                return _make_response(
                    "end_turn",
                    [_make_text_block("EV 计算结果: +0.14")],
                )

        mock_client.messages.create = AsyncMock(side_effect=side_effect)

        executor = FakeExecutor({"goalcast_calculate_ev": {"ev": 0.14}})
        adapter = ClaudeAdapter(
            executor=executor,
            loader=FakeLoader("sys", ["goalcast_calculate_ev"]),
        )

        result = await adapter.run_agent("trader", "做个交易")

        assert result.rounds == 2
        assert result.final_text == "EV 计算结果: +0.14"
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0]["tool"] == "goalcast_calculate_ev"
        assert result.tool_calls[0]["input"]["model_probability"] == 0.6
        assert result.tool_calls[0]["result"] == {"ev": 0.14}
        assert len(executor.calls) == 1

    @patch("anthropic.AsyncAnthropic")
    async def test_max_rounds_exceeded(self, mock_cls):
        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        mock_client.messages.create = AsyncMock(
            return_value=_make_response(
                "tool_use",
                [_make_tool_use_block("goalcast_calculate_ev", {"model_probability": 0.5, "market_odds": 2.0})],
            )
        )

        executor = FakeExecutor()
        adapter = ClaudeAdapter(
            executor=executor,
            loader=FakeLoader("sys", ["goalcast_calculate_ev"]),
        )

        result = await adapter.run_agent("trader", "loop")

        assert result.rounds == MAX_TOOL_ROUNDS
        assert "[MAX_ROUNDS_EXCEEDED]" in result.final_text

    @patch("anthropic.AsyncAnthropic")
    async def test_context_is_prepended(self, mock_cls):
        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        captured_messages = []

        async def capture(**kwargs):
            captured_messages.append(kwargs.get("messages", []))
            return _make_response("end_turn", [_make_text_block("done")])

        mock_client.messages.create = AsyncMock(side_effect=capture)

        adapter = ClaudeAdapter(
            executor=FakeExecutor(),
            loader=FakeLoader("sys"),
        )

        await adapter.run_agent(
            "analyst", "分析", context={"match": "City vs Arsenal"}
        )

        msgs = captured_messages[0]
        context_msg = msgs[0]
        assert "City vs Arsenal" in context_msg["content"]
        user_msg = msgs[1]
        assert user_msg["content"] == "分析"

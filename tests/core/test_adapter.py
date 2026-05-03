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


@pytest.fixture(autouse=True)
def _clear_llm_env(monkeypatch):
    for key in [
        "LLM_PROVIDER",
        "LLM_API_KEY",
        "LLM_BASE_URL",
        "LLM_MODEL",
        "ANTHROPIC_API_KEY",
    ]:
        monkeypatch.delenv(key, raising=False)


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


def _make_openai_tool_call(name, arguments, call_id="call_001"):
    fn = MagicMock()
    fn.name = name
    fn.arguments = json.dumps(arguments)

    tool_call = MagicMock()
    tool_call.id = call_id
    tool_call.function = fn
    return tool_call


def _make_openai_response(content=None, tool_calls=None):
    message = MagicMock()
    message.content = content
    message.tool_calls = tool_calls

    choice = MagicMock()
    choice.message = message

    response = MagicMock()
    response.choices = [choice]
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

    @patch("anthropic.AsyncAnthropic")
    def test_falls_back_to_generic_llm_env_vars(self, mock_client_cls, monkeypatch):
        mock_client_cls.return_value = MagicMock()
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setenv("LLM_API_KEY", "test-key")
        monkeypatch.setenv("LLM_BASE_URL", "https://example.invalid")
        monkeypatch.setenv("LLM_MODEL", "claude-custom")

        adapter = ClaudeAdapter(
            executor=FakeExecutor(),
            loader=FakeLoader(),
        )

        assert adapter.model == "claude-custom"
        mock_client_cls.assert_called_once_with(
            api_key="test-key",
            base_url="https://example.invalid",
        )

    @patch("anthropic.AsyncAnthropic")
    def test_explicit_args_override_generic_llm_env_vars(self, mock_client_cls, monkeypatch):
        mock_client_cls.return_value = MagicMock()
        monkeypatch.setenv("LLM_API_KEY", "env-key")
        monkeypatch.setenv("LLM_BASE_URL", "https://env.invalid")
        monkeypatch.setenv("LLM_MODEL", "env-model")

        adapter = ClaudeAdapter(
            model="arg-model",
            api_key="arg-key",
            base_url="https://arg.invalid",
            executor=FakeExecutor(),
            loader=FakeLoader(),
        )

        assert adapter.model == "arg-model"
        mock_client_cls.assert_called_once_with(
            api_key="arg-key",
            base_url="https://arg.invalid",
        )

    @patch("openai.AsyncOpenAI")
    def test_openai_provider_uses_openai_client(self, mock_client_cls, monkeypatch):
        mock_client_cls.return_value = MagicMock()
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setenv("LLM_API_KEY", "openai-key")
        monkeypatch.setenv("LLM_BASE_URL", "https://openai.example/v1")
        monkeypatch.setenv("LLM_MODEL", "gpt-4o-mini")

        adapter = ClaudeAdapter(
            executor=FakeExecutor(),
            loader=FakeLoader(),
        )

        assert adapter.model == "gpt-4o-mini"
        assert adapter.provider == "openai"
        mock_client_cls.assert_called_once_with(
            api_key="openai-key",
            base_url="https://openai.example/v1",
        )


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

    @patch("openai.AsyncOpenAI")
    async def test_openai_tool_call_then_final_text(self, mock_cls, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        mock_client.chat.completions.create = AsyncMock(
            side_effect=[
                _make_openai_response(
                    tool_calls=[
                        _make_openai_tool_call(
                            "goalcast_calculate_ev",
                            {"model_probability": 0.61, "market_odds": 1.95},
                        )
                    ]
                ),
                _make_openai_response(content="OpenAI EV 计算完成"),
            ]
        )

        executor = FakeExecutor({"goalcast_calculate_ev": {"ev": 0.19}})
        adapter = ClaudeAdapter(
            executor=executor,
            loader=FakeLoader("sys", ["goalcast_calculate_ev"]),
        )

        result = await adapter.run_agent("trader", "做个交易")

        assert result.final_text == "OpenAI EV 计算完成"
        assert result.rounds == 2
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0]["tool"] == "goalcast_calculate_ev"
        assert executor.calls[0]["params"]["model_probability"] == 0.61

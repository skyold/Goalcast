"""
Agentic Loop 适配器 —— 实现多轮 tool_use ↔ tool_result 循环。
参考 yclake 的 ClaudeAdapter，使用 Anthropic Python SDK。
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
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
        import os

        resolved_model = model or os.environ.get("LLM_MODEL") or DEFAULT_MODEL
        self.model = resolved_model
        self.max_tokens = max_tokens
        self.provider = (os.environ.get("LLM_PROVIDER") or "anthropic").lower()

        client_kwargs = {}
        resolved_key = (
            api_key
            or os.environ.get("ANTHROPIC_API_KEY")
            or os.environ.get("LLM_API_KEY")
        )
        if resolved_key:
            client_kwargs["api_key"] = resolved_key
        resolved_base_url = base_url or os.environ.get("LLM_BASE_URL")
        if resolved_base_url:
            client_kwargs["base_url"] = resolved_base_url
        if self.provider == "openai":
            import openai

            self.client = openai.AsyncOpenAI(**client_kwargs)
        else:
            import anthropic

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

        if self.provider == "openai":
            return await self._run_openai_agent(role_path, agent_def.system_prompt, schemas, messages)
        return await self._run_anthropic_agent(role_path, agent_def.system_prompt, schemas, messages)

    async def _run_anthropic_agent(
        self,
        role_path: str,
        system_prompt: str,
        schemas: list[dict],
        messages: list[dict],
    ) -> AgentResult:
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
                "system": system_prompt,
                "messages": messages,
            }
            if schemas:
                request_kwargs["tools"] = schemas

            response = await self.client.messages.create(**request_kwargs)

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

    async def _run_openai_agent(
        self,
        role_path: str,
        system_prompt: str,
        schemas: list[dict],
        messages: list[dict],
    ) -> AgentResult:
        tool_calls_log: list[dict] = []
        rounds = 0

        openai_messages = []
        if system_prompt:
            openai_messages.append({"role": "system", "content": system_prompt})
        openai_messages.extend(messages)

        while rounds < MAX_TOOL_ROUNDS:
            rounds += 1
            logger.info(
                "[ClaudeAdapter/OpenAI] 第 %d 轮推理 | 角色: %s | 工具数: %d",
                rounds, role_path, len(schemas),
            )

            request_kwargs = {
                "model": self.model,
                "messages": openai_messages,
            }
            openai_tools = _to_openai_tools(schemas)
            if openai_tools:
                request_kwargs["tools"] = openai_tools
                request_kwargs["tool_choice"] = "auto"

            response = await self.client.chat.completions.create(**request_kwargs)
            message = response.choices[0].message

            assistant_message = {"role": "assistant"}
            if getattr(message, "content", None):
                assistant_message["content"] = message.content
            if getattr(message, "tool_calls", None):
                assistant_message["tool_calls"] = [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.function.name,
                            "arguments": call.function.arguments,
                        },
                    }
                    for call in message.tool_calls
                ]
            openai_messages.append(assistant_message)

            if getattr(message, "tool_calls", None):
                for call in message.tool_calls:
                    tool_name = call.function.name
                    tool_input = json.loads(call.function.arguments or "{}")
                    result = await self.executor.execute(tool_name, tool_input)
                    tool_calls_log.append({
                        "tool": tool_name,
                        "input": tool_input,
                        "result": result,
                    })
                    openai_messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.id,
                            "content": json.dumps(result, ensure_ascii=False),
                        }
                    )
                continue

            final_text = _extract_openai_text(message)
            logger.info(
                "[ClaudeAdapter/OpenAI] 完成 | 角色: %s | 轮数: %d | 工具调用: %d",
                role_path, rounds, len(tool_calls_log),
            )
            return AgentResult(
                role_path=role_path,
                final_text=final_text,
                tool_calls=tool_calls_log,
                rounds=rounds,
            )

        logger.error(
            "[ClaudeAdapter/OpenAI] 超出最大轮数 %d | 角色: %s",
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


def _extract_openai_text(message) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "\n".join(part for part in parts if part)
    return ""


def _to_openai_tools(schemas: list[dict]) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": schema["name"],
                "description": schema.get("description", ""),
                "parameters": schema.get("input_schema", {"type": "object", "properties": {}}),
            },
        }
        for schema in schemas
    ]

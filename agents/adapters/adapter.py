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

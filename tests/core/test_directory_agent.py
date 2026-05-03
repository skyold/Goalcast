import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.core.directory_agent import (
    AgentConfig,
    AgentDefinition,
    DirectoryAgentLoader,
)


class TestAgentConfig:
    def test_default_tools_is_empty_dict(self):
        cfg = AgentConfig(system_prompt="test")
        assert cfg.system_prompt == "test"
        assert cfg.tools == {}

    def test_custom_tools(self):
        cfg = AgentConfig(system_prompt="t", tools={"mcp": [{"name": "x"}]})
        assert cfg.tools["mcp"][0]["name"] == "x"


class TestAgentDefinition:
    def test_role_name_from_path(self):
        ad = AgentDefinition(
            role_path="agents/roles/analyst",
            system_prompt="p",
            tool_registry={},
        )
        assert ad.role_name == "analyst"

    def test_role_name_simple(self):
        ad = AgentDefinition(
            role_path="analyst",
            system_prompt="p",
            tool_registry={},
        )
        assert ad.role_name == "analyst"

    def test_allowed_mcp_tools_empty(self):
        ad = AgentDefinition(
            role_path="analyst",
            system_prompt="p",
            tool_registry={"mcp": []},
        )
        assert ad.allowed_mcp_tools == []

    def test_allowed_mcp_tools_extracts_names(self):
        ad = AgentDefinition(
            role_path="analyst",
            system_prompt="p",
            tool_registry={
                "mcp": [
                    {"name": "goalcast_calculate_ev"},
                    {"name": "goalcast_calculate_poisson"},
                ]
            },
        )
        assert ad.allowed_mcp_tools == [
            "goalcast_calculate_ev",
            "goalcast_calculate_poisson",
        ]

    def test_allowed_mcp_tools_skips_non_dict(self):
        ad = AgentDefinition(
            role_path="a",
            system_prompt="p",
            tool_registry={
                "mcp": [
                    {"name": "tool_a"},
                    "not_a_dict",
                    {"no_name": True},
                    {"name": "tool_b"},
                ]
            },
        )
        assert ad.allowed_mcp_tools == ["tool_a", "tool_b"]

    def test_allowed_builtin_tools(self):
        ad = AgentDefinition(
            role_path="a",
            system_prompt="p",
            tool_registry={
                "mcp": [],
                "builtin": {"include": ["web_search", "web_fetch"]},
            },
        )
        assert ad.allowed_builtin_tools == ["web_search", "web_fetch"]

    def test_allowed_builtin_tools_empty_when_missing(self):
        ad = AgentDefinition(role_path="a", system_prompt="p", tool_registry={})
        assert ad.allowed_builtin_tools == []

    def test_allowed_tools_combines_mcp_and_builtin(self):
        ad = AgentDefinition(
            role_path="a",
            system_prompt="p",
            tool_registry={
                "mcp": [{"name": "mcp_tool"}],
                "builtin": {"include": ["builtin_tool"]},
            },
        )
        assert sorted(ad.allowed_tools) == sorted(["mcp_tool", "builtin_tool"])


class TestDirectoryAgentLoaderLoad:
    def test_load_returns_agent_config(self):
        cfg = DirectoryAgentLoader.load("backend/agents/roles/analyst")
        assert isinstance(cfg, AgentConfig)
        assert len(cfg.system_prompt) > 100
        assert "Identity" in cfg.system_prompt or "身份" in cfg.system_prompt

    def test_load_returns_tools(self):
        cfg = DirectoryAgentLoader.load("backend/agents/roles/analyst")
        assert "mcp" in cfg.tools
        tool_names = [t["name"] for t in cfg.tools["mcp"]]
        assert "goalcast_calculate_poisson" in tool_names
        assert "goalcast_calculate_ev" in tool_names

    def test_load_nonexistent_role_returns_empty(self):
        cfg = DirectoryAgentLoader.load("backend/agents/roles/nonexistent_role")
        assert isinstance(cfg, AgentConfig)
        assert cfg.system_prompt == ""
        assert cfg.tools == {}


class TestDirectoryAgentLoaderLoadAgent:
    def test_load_agent_returns_agent_definition(self):
        ad = DirectoryAgentLoader.load_agent("backend/agents/roles/analyst")
        assert isinstance(ad, AgentDefinition)
        assert ad.role_path == "backend/agents/roles/analyst"
        assert ad.role_name == "analyst"
        assert len(ad.system_prompt) > 100

    def test_load_agent_allowed_mcp_tools(self):
        ad = DirectoryAgentLoader.load_agent("backend/agents/roles/analyst")
        assert "goalcast_calculate_poisson" in ad.allowed_mcp_tools
        assert "goalcast_sportmonks_get_match" in ad.allowed_mcp_tools

    def test_load_agent_all_six_roles(self):
        for role in [
            "orchestrator", "analyst", "trader",
            "reviewer", "reporter", "backtester",
        ]:
            role_dir = f"backend/agents/roles/{role}"
            ad = DirectoryAgentLoader.load_agent(role_dir)
            assert isinstance(ad, AgentDefinition)
            assert ad.role_name == role
            assert len(ad.system_prompt) > 50
            assert "独立运行模式" in ad.system_prompt, (
                f"{role} 缺少 独立运行模式 章节"
            )

    def test_load_agent_nonexistent_returns_empty(self):
        ad = DirectoryAgentLoader.load_agent("backend/agents/roles/nonexistent")
        assert isinstance(ad, AgentDefinition)
        assert ad.system_prompt == ""
        assert ad.allowed_mcp_tools == []

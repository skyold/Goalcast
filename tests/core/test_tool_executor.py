import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.adapters.tool_executor import (
    TOOL_SCHEMAS,
    ToolExecutor,
    _serialize_result,
)


class TestTOOLSCHEMAS:
    def test_count_is_twelve(self):
        assert len(TOOL_SCHEMAS) == 12

    def test_all_schemas_have_required_fields(self):
        for name, schema in TOOL_SCHEMAS.items():
            assert "name" in schema, f"{name}: missing 'name'"
            assert "description" in schema, f"{name}: missing 'description'"
            assert "input_schema" in schema, f"{name}: missing 'input_schema'"
            assert schema["input_schema"]["type"] == "object", (
                f"{name}: input_schema.type != 'object'"
            )

    def test_sportmonks_schemas_present(self):
        assert "goalcast_sportmonks_get_matches" in TOOL_SCHEMAS
        assert "goalcast_sportmonks_get_match" in TOOL_SCHEMAS
        assert (
            "fixture_id"
            in TOOL_SCHEMAS["goalcast_sportmonks_get_match"]["input_schema"][
                "required"
            ]
        )

    def test_footystats_schemas_present(self):
        assert "goalcast_footystats_resolve_match" in TOOL_SCHEMAS
        assert "goalcast_footystats_get_todays_matches" in TOOL_SCHEMAS
        assert len(
            TOOL_SCHEMAS["goalcast_footystats_resolve_match"]["input_schema"][
                "required"
            ]
        ) == 7

    def test_quant_schemas_present(self):
        for name in [
            "goalcast_calculate_poisson",
            "goalcast_calculate_ah_prob",
            "goalcast_calculate_ev",
            "goalcast_calculate_kelly",
            "goalcast_calculate_risk_adjusted_ev",
            "goalcast_calculate_confidence",
        ]:
            assert name in TOOL_SCHEMAS, f"missing {name}"

    def test_poisson_schema_requires_lambdas(self):
        required = TOOL_SCHEMAS["goalcast_calculate_poisson"]["input_schema"][
            "required"
        ]
        assert "home_lambda" in required
        assert "away_lambda" in required

    def test_evaluation_schemas_present(self):
        assert "goalcast_run_review" in TOOL_SCHEMAS
        assert "goalcast_run_backtest" in TOOL_SCHEMAS


class TestToolExecutorExecute:
    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error(self):
        executor = ToolExecutor()
        result = await executor.execute("nonexistent_tool", {})
        assert result["error"].startswith("unknown tool")

    @pytest.mark.asyncio
    async def test_execute_calls_handler(self):
        executor = ToolExecutor()
        result = await executor._tool_goalcast_calculate_ev(
            model_probability=0.55, market_odds=1.9
        )
        assert isinstance(result, (float, dict))

    @pytest.mark.asyncio
    async def test_execute_poisson(self):
        executor = ToolExecutor()
        result = await executor._tool_goalcast_calculate_poisson(
            home_lambda=1.5, away_lambda=1.0, max_goals=3
        )
        assert isinstance(result, list) or (
            isinstance(result, dict) and "home_win_pct" in result
        )

    @pytest.mark.asyncio
    async def test_execute_kelly(self):
        executor = ToolExecutor()
        result = await executor._tool_goalcast_calculate_kelly(
            model_probability=0.6, market_odds=1.9
        )
        assert isinstance(result, (float, dict))

    @pytest.mark.asyncio
    async def test_execute_risk_adjusted_ev(self):
        executor = ToolExecutor()
        result = await executor._tool_goalcast_calculate_risk_adjusted_ev(
            raw_ev=0.1
        )
        assert isinstance(result, dict)
        assert "raw_ev" in result
        assert "risk_adjusted_ev" in result

    @pytest.mark.asyncio
    async def test_execute_confidence(self):
        executor = ToolExecutor()
        result = await executor._tool_goalcast_calculate_confidence(
            method="v3.0", base_score=70, market_agrees=True,
        )
        assert isinstance(result, dict)
        assert "confidence" in result

    @pytest.mark.asyncio
    async def test_execute_ah_prob(self):
        executor = ToolExecutor()
        matrix = [[0.2, 0.15, 0.05], [0.15, 0.1, 0.05], [0.1, 0.05, 0.02]]
        result = await executor._tool_goalcast_calculate_ah_prob(
            score_matrix=matrix, ah_line=-0.5,
        )
        assert isinstance(result, (float, dict))


class TestSerializeResult:
    def test_primitives_pass_through(self):
        assert _serialize_result(42) == 42
        assert _serialize_result("hello") == "hello"
        assert _serialize_result(3.14) == 3.14
        assert _serialize_result(True) is True
        assert _serialize_result(None) is None

    def test_list_is_recursed(self):
        assert _serialize_result([1, 2, 3]) == [1, 2, 3]

    def test_dict_is_recursed(self):
        assert _serialize_result({"a": 1, "b": [2, 3]}) == {"a": 1, "b": [2, 3]}

    def test_to_dict_called(self):
        class WithToDict:
            def to_dict(self):
                return {"key": "value"}

        assert _serialize_result(WithToDict()) == {"key": "value"}

    def test_nested_to_dict(self):
        class Inner:
            def to_dict(self):
                return {"x": 1}

        assert _serialize_result([Inner()]) == [{"x": 1}]

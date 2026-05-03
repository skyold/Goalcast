"""
MCP 工具执行器 —— 将 Agentic Loop 中的工具调用路由到 Goalcast MCP 工具。
所有 _tool_* 方法复用现有 MCP 工具实现，不做重复逻辑。
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

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
            "required": [
                "match_id", "home_team", "home_team_id",
                "away_team", "away_team_id", "season_id", "league",
            ],
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


def _create_sportmonks_data_service():
    from datasource.sportmonks.service import SportmonksDataService
    from mcp_server.internal import get_sportmonks

    return SportmonksDataService(provider=get_sportmonks())


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
        from mcp_server.tools.sportmonks import _serialize

        service = _create_sportmonks_data_service()
        fixtures = await service.get_matches(date=date, league_ids=league_ids)
        data = _serialize(fixtures)
        return {"ok": True, "count": len(data), "data": data}

    async def _tool_goalcast_sportmonks_get_match(
        self, fixture_id: int, match_date: str | None = None
    ) -> dict:
        from mcp_server.tools.sportmonks import _serialize

        service = _create_sportmonks_data_service()
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
        from mcp_server.internal import (
            get_footystats,
            handle_api_call,
            _normalize_footystats_fixtures,
        )

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
        from analytics.confidence import (
            calculate_confidence,
            calculate_confidence_v25,
            confidence_breakdown,
        )
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
        report = bt.generate_report(
            predictions, results, effective_start, effective_end
        )
        output_path = (
            bt.BACKTESTS_DIR
            / f"backtest_{effective_start}_to_{effective_end}.json"
        )
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

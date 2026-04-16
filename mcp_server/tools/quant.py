"""Goalcast 量化 MCP 工具。"""

from __future__ import annotations

from typing import Any

from analytics.confidence import (
    calculate_confidence,
    calculate_confidence_v25,
    confidence_breakdown,
)
from analytics.ev_calculator import (
    calculate_ev,
    calculate_kelly,
    calculate_risk_adjusted_ev,
)
from analytics.poisson import (
    calculate_ah_probability,
    dixon_coles_distribution,
    poisson_distribution,
)


def register_goalcast_quant_tools(mcp: Any) -> None:
    """注册量化分析相关 MCP 工具。"""

    @mcp.tool()
    async def goalcast_calculate_poisson(
        home_lambda: float,
        away_lambda: float,
        max_goals: int = 6,
        model: str = "standard",
        rho: float = -0.13,
    ) -> Any:
        """Calculate score probability matrix using Poisson or Dixon-Coles distribution."""
        try:
            if model == "dixon_coles":
                return dixon_coles_distribution(home_lambda, away_lambda, max_goals, rho)
            return poisson_distribution(home_lambda, away_lambda, max_goals)
        except Exception as exc:
            return {"error": "POISSON_CALC_ERROR", "message": str(exc)}

    @mcp.tool()
    async def goalcast_calculate_ah_prob(
        score_matrix: list,
        ah_line: float,
    ) -> Any:
        """Calculate Asian Handicap coverage probability from a score matrix."""
        try:
            return calculate_ah_probability(score_matrix, ah_line)
        except Exception as exc:
            return {"error": "AH_PROB_CALC_ERROR", "message": str(exc)}

    @mcp.tool()
    async def goalcast_calculate_ev(
        model_probability: float,
        market_odds: float,
    ) -> Any:
        """Calculate Expected Value for a single direction."""
        try:
            return calculate_ev(model_probability, market_odds)
        except Exception as exc:
            return {"error": "EV_CALC_ERROR", "message": str(exc)}

    @mcp.tool()
    async def goalcast_calculate_kelly(
        model_probability: float,
        market_odds: float,
        fraction: float = 0.25,
        bankroll: float | None = None,
    ) -> Any:
        """Calculate Kelly Criterion stake recommendation."""
        try:
            return calculate_kelly(model_probability, market_odds, fraction, bankroll)
        except Exception as exc:
            return {"error": "KELLY_CALC_ERROR", "message": str(exc)}

    @mcp.tool()
    async def goalcast_calculate_risk_adjusted_ev(
        raw_ev: float,
        lineup_uncertainty: bool = False,
        market_low_confidence: bool = False,
        data_quality: str = "medium",
    ) -> Any:
        """Calculate risk-adjusted EV by applying multiplicative risk factors."""
        try:
            risk_adjusted_ev = calculate_risk_adjusted_ev(
                raw_ev,
                lineup_uncertainty,
                market_low_confidence,
                data_quality,
            )
            return {
                "raw_ev": raw_ev,
                "risk_adjusted_ev": risk_adjusted_ev,
                "recommendation": "bet" if risk_adjusted_ev > 0.05 else "no_bet",
            }
        except Exception as exc:
            return {"error": "RISK_EV_CALC_ERROR", "message": str(exc)}

    @mcp.tool()
    async def goalcast_calculate_confidence(
        method: str = "v3.0",
        base_score: int = 70,
        market_agrees: bool = False,
        data_complete: bool = False,
        understat_available: bool = False,
        odds_available: bool = False,
        lineup_unavailable: bool = True,
        xG_proxy_used: bool = False,
        market_disagrees: bool = False,
        data_quality_low: bool = False,
        understat_failed: bool = False,
        match_type_c: bool = False,
        major_uncertainty: bool = False,
        market_downgraded: bool = False,
        prediction_diverged: bool = False,
    ) -> Any:
        """Calculate confidence score for a match prediction."""
        try:
            kwargs = {
                "base_score": base_score,
                "market_agrees": market_agrees,
                "data_complete": data_complete,
                "understat_available": understat_available,
                "odds_available": odds_available,
                "lineup_unavailable": lineup_unavailable,
                "xG_proxy_used": xG_proxy_used,
                "market_disagrees": market_disagrees,
                "data_quality_low": data_quality_low,
                "understat_failed": understat_failed,
                "match_type_c": match_type_c,
                "major_uncertainty": major_uncertainty,
                "market_downgraded": market_downgraded,
                "prediction_diverged": prediction_diverged,
            }
            if method == "v2.5":
                final_score = calculate_confidence_v25(**kwargs)
            else:
                final_score = calculate_confidence(**kwargs)
            return {
                "confidence": final_score,
                "breakdown": confidence_breakdown(**kwargs),
            }
        except Exception as exc:
            return {"error": "CONFIDENCE_CALC_ERROR", "message": str(exc)}

"""
server.py — Goalcast MCP Server 接口层

仅包含对外暴露的 MCP 工具（10 个 @mcp.tool() 函数）。
内部实现、provider 包装和 helper 函数见 internal.py。

暴露的工具（V4.0 路径）：
  goalcast_sm_get_fixtures    — 获取指定联赛今日赛程
  goalcast_sm_fetch           — 单场完整数据（直连 SportmonksResolver）

暴露的工具（量化计算）：
  goalcast_calculate_poisson          — Dixon-Coles 分布
  goalcast_calculate_ah_prob          — 亚盘概率
  goalcast_calculate_ev               — 期望收益
  goalcast_calculate_kelly            — Kelly 仓位
  goalcast_calculate_risk_adjusted_ev — 风险调整 EV
  goalcast_calculate_confidence       — 置信度校准

暴露的工具（遗留 v2.5/v3.0 路径）：
  goalcast_resolve_match      — DataFusion 数据融合入口
  goalcast_get_todays_matches — 按 provider 获取今日赛程
"""
import os
from mcp.server.fastmcp import FastMCP

from internal import (
    # Provider 初始化
    get_footystats, get_sportmonks, get_understat, handle_api_call,
    # V4.0 helpers
    _SM_LEAGUE_KEYWORDS, _infer_season, _extract_standing_for_team,
    # 遗留 helpers
    _normalize_sportmonks_fixtures, _normalize_footystats_fixtures,
    goalcast_prefetch_today,
    # 所有内部 API 包装函数（供 DataFusion 间接使用）
    footystats_get_league_list, footystats_get_country_list,
    footystats_get_todays_matches, footystats_get_league_stats,
    footystats_get_league_matches, footystats_get_league_teams,
    footystats_get_league_tables, footystats_get_match_details,
    footystats_get_lineups, footystats_get_team_details,
    footystats_get_team_last_x_stats, footystats_get_btts_stats,
    footystats_get_over25_stats,
)
import asyncio
import datetime
from typing import Optional, List, Dict, Any

from analytics.poisson import poisson_distribution, dixon_coles_distribution, calculate_ah_probability
from analytics.ev_calculator import calculate_ev, calculate_kelly, calculate_risk_adjusted_ev, best_bet_recommendation
from analytics.confidence import calculate_confidence, calculate_confidence_v25, confidence_breakdown
from utils.logger import logger
from datasource.datafusion.fusion import DataFusion
from datasource.datafusion.resolvers.sportmonks_resolver import SportmonksResolver
from datasource.sportmonks.collector import SportmonksCollector
from datasource.sportmonks.models import SportmonksMatchData
from datasource.sportmonks.service import SportmonksDataService
from mcp_server.tools.goalcast_sportmonks import (
    legacy_goalcast_sm_fetch,
    legacy_goalcast_sm_get_fixtures,
    register_goalcast_sportmonks_tools,
)

mcp = FastMCP(
    "Goalcast Data Providers",
    host=os.environ.get("FASTMCP_HOST", "127.0.0.1"),
    port=int(os.environ.get("FASTMCP_PORT", "8000")),
)

_sportmonks_data_service: Optional[SportmonksDataService] = None


def get_sportmonks_data_service() -> SportmonksDataService:
    global _sportmonks_data_service
    if _sportmonks_data_service is None:
        _sportmonks_data_service = SportmonksDataService(
            collector=SportmonksCollector(get_sportmonks()),
        )
    return _sportmonks_data_service


register_goalcast_sportmonks_tools(mcp, service_factory=get_sportmonks_data_service)


# ══════════════════════════════════════════════════════════════════
#  MCP TOOLS — 以下为全部对外暴露的接口，共 10 个
# ══════════════════════════════════════════════════════════════════


@mcp.tool()
async def goalcast_sm_get_fixtures(
    leagues: List[str],
    date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    V4.0 专用：获取指定日期在目标联赛的所有比赛。

    一次调用返回多联赛赛程，每条记录包含 goalcast_sm_fetch 所需的全部 ID。
    内置联赛名称过滤，支持常见写法（不区分大小写子字符串匹配）。

    Args:
        leagues: 联赛名称列表，如 ["Premier League", "Championship", "Serie A"]
                 支持的名称见 _SM_LEAGUE_KEYWORDS 映射。
        date:    YYYY-MM-DD，默认今天。

    Returns:
        {
          "date": "YYYY-MM-DD",
          "count": N,
          "fixtures": [
            {
              "fixture_id": int,
              "home_team": str,  "home_team_id": int,
              "away_team": str,  "away_team_id": int,
              "season_id": int,
              "league": str,
              "kickoff_time": str,   # ISO 字符串
            }, ...
          ]
        }
    """
    target_date = date or datetime.date.today().isoformat()
    return await legacy_goalcast_sm_get_fixtures(
        get_sportmonks_data_service(),
        leagues=leagues,
        date=target_date,
    )


@mcp.tool()
async def goalcast_sm_fetch(
    fixture_id: int,
    home_team: str,
    home_team_id: int,
    away_team: str,
    away_team_id: int,
    season_id: int,
    league: str,
    match_date: str,
    season: Optional[str] = None,
) -> Dict[str, Any]:
    """
    V4.0 专用数据获取。直连 SportmonksResolver，完全跳过 DataFusion。

    并行拉取单场比赛的全部 V4.0 所需数据，返回 SportmonksMatchData 序列化字典。
    Sportmonks 专有字段（亚盘、赔率时序、官方预测、原生 xG）原生保留，不经归一化。

    Args:
        fixture_id:    Sportmonks fixture ID（来自 goalcast_sm_get_fixtures）
        home_team:     主队名称
        home_team_id:  主队 Sportmonks ID
        away_team:     客队名称
        away_team_id:  客队 Sportmonks ID
        season_id:     Sportmonks season ID
        league:        联赛名（如 "Premier League"）
        match_date:    YYYY-MM-DD
        season:        Understat 赛季年（如 "2025"）；不传时从 match_date 自动推断

    Returns:
        SportmonksMatchData.to_dict() — V4.0 九层分析直接消费的数据结构
    """
    return await legacy_goalcast_sm_fetch(
        get_sportmonks_data_service(),
        fixture_id=fixture_id,
        home_team=home_team,
        home_team_id=home_team_id,
        away_team=away_team,
        away_team_id=away_team_id,
        season_id=season_id,
        league=league,
        match_date=match_date,
        season=season or _infer_season(match_date),
    )


# ─── Quantitative Model Tools (Poisson, EV, Kelly, Confidence) ──────────

@mcp.tool()
async def goalcast_calculate_poisson(
    home_lambda: float,
    away_lambda: float,
    max_goals: int = 6,
    model: str = "standard",
    rho: float = -0.13,
) -> Any:
    """Calculate score probability matrix using Poisson or Dixon-Coles distribution.

    Args:
        home_lambda: Expected goals for home team (λ)
        away_lambda: Expected goals for away team (λ)
        max_goals: Maximum goals to model per side (default 6, covers 0-6)
        model: "standard" (v2.5) or "dixon_coles" (v3.0)
        rho: Dixon-Coles correction parameter (default -0.13, only used for dixon_coles)

    Returns:
        Score probability matrix with:
        - score_matrix: 2D array P(home_goals × away_goals)
        - home_win_pct / draw_pct / away_win_pct
        - top_scores: Top 5 most likely scorelines
        - over_25_pct / btts_pct
    """
    try:
        if model == "dixon_coles":
            result = dixon_coles_distribution(home_lambda, away_lambda, max_goals, rho)
        else:
            result = poisson_distribution(home_lambda, away_lambda, max_goals)
        return result
    except Exception as e:
        return {"error": "POISSON_CALC_ERROR", "message": str(e)}


@mcp.tool()
async def goalcast_calculate_ah_prob(
    score_matrix: list,
    ah_line: float,
) -> Any:
    """Calculate Asian Handicap coverage probability from a Poisson/Dixon-Coles score matrix.

    Derives the probability that each side covers the Asian Handicap line by summing
    the relevant cells of the score matrix returned by goalcast_calculate_poisson.

    Supports all standard AH line types:
      - Half-ball (±0.5, ±1.5, …): no push possible
      - Whole-ball (0, ±1, ±2, …): push (refund) possible on exact margin
      - Quarter-ball (±0.25, ±0.75, …): stake split across two adjacent lines

    Args:
        score_matrix: 2D list from goalcast_calculate_poisson result["score_matrix"].
                      matrix[i][j] = P(home=i goals, away=j goals).
        ah_line:      Home team handicap line.
                      Negative = home gives goals (e.g. -0.5 = home -½).
                      Positive = home receives goals (e.g. +0.5 = home +½).

    Returns:
        {
          "ah_line": float,
          "p_home_cover": float,    # raw probability (0-1)
          "p_away_cover": float,
          "p_push": float,          # refund probability (whole-ball lines only)
          "p_home_cover_pct": float,
          "p_away_cover_pct": float,
          "p_push_pct": float,
          "ah_type": "half" | "whole" | "quarter"
        }
    """
    try:
        return calculate_ah_probability(score_matrix, ah_line)
    except Exception as e:
        return {"error": "AH_PROB_CALC_ERROR", "message": str(e)}


@mcp.tool()
async def goalcast_calculate_ev(
    model_probability: float,
    market_odds: float,
) -> Any:
    """Calculate Expected Value for a single direction.

    EV = (model_probability / 100) × market_odds - 1

    Args:
        model_probability: Model's probability as percentage (0-100)
        market_odds: Decimal odds from bookmaker (e.g., 1.85, 3.50)

    Returns:
        EV calculation with break-even odds and value flag.
    """
    try:
        return calculate_ev(model_probability, market_odds)
    except Exception as e:
        return {"error": "EV_CALC_ERROR", "message": str(e)}


@mcp.tool()
async def goalcast_calculate_kelly(
    model_probability: float,
    market_odds: float,
    fraction: float = 0.25,
    bankroll: float = None,
) -> Any:
    """Calculate Kelly Criterion stake recommendation.

    f* = (b × p - q) / b where b = odds - 1, p = probability, q = 1 - p

    Args:
        model_probability: Model's probability as percentage (0-100)
        market_odds: Decimal odds
        fraction: Fraction of full Kelly (default 0.25 = quarter Kelly)
        bankroll: Optional total bankroll for absolute stake amount

    Returns:
        Kelly percentage and stake recommendation.
    """
    try:
        return calculate_kelly(model_probability, market_odds, fraction, bankroll)
    except Exception as e:
        return {"error": "KELLY_CALC_ERROR", "message": str(e)}


@mcp.tool()
async def goalcast_calculate_risk_adjusted_ev(
    raw_ev: float,
    lineup_uncertainty: bool = False,
    market_low_confidence: bool = False,
    data_quality: str = "medium",
) -> Any:
    """Calculate risk-adjusted EV by applying multiplicative risk factors.

    Risk multipliers:
    - lineup_uncertainty: × 0.85
    - market_low_confidence: × 0.90
    - data_quality=low: × 0.80

    Args:
        raw_ev: Raw expected value
        lineup_uncertainty: True if lineup data unavailable
        market_low_confidence: True if market analysis low confidence
        data_quality: "low", "medium", or "high"

    Returns:
        Risk-adjusted EV value.
    """
    try:
        ev_adj = calculate_risk_adjusted_ev(raw_ev, lineup_uncertainty, market_low_confidence, data_quality)
        return {"raw_ev": raw_ev, "risk_adjusted_ev": ev_adj, "recommendation": "bet" if ev_adj > 0.05 else "no_bet"}
    except Exception as e:
        return {"error": "RISK_EV_CALC_ERROR", "message": str(e)}


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
    """Calculate confidence score for a match prediction.

    Args:
        method: "v2.5" or "v3.0" or "v4.0" (affects weighting)
        base_score: Starting confidence (default 70)
        market_agrees: Market direction agrees with model
        data_complete: Both teams have recent form data
        understat_available: Direct xG from Understat available
        odds_available: Valid odds data available
        lineup_unavailable: Lineup data missing (expected, default True)
        xG_proxy_used: Using proxy instead of direct xG
        market_disagrees: Market odds contradict model
        data_quality_low: Form data unavailable
        understat_failed: Understat match lookup failed
        match_type_c: Type C match (second leg)
        major_uncertainty: Major pre-match uncertainty
        market_downgraded: Market layer downgraded
        prediction_diverged: Sportmonks prediction significantly diverges from model

    Returns:
        Confidence score [30-90] with detailed breakdown.
    """
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
            final = calculate_confidence_v25(**kwargs)
        else:
            final = calculate_confidence(**kwargs)

        breakdown = confidence_breakdown(**kwargs)
        return {"confidence": final, "breakdown": breakdown}
    except Exception as e:
        return {"error": "CONFIDENCE_CALC_ERROR", "message": str(e)}


# ── 数据策略层：单一入口工具 ──────────────────────────────────

@mcp.tool()
async def goalcast_resolve_match(
    match_id: str,
    home_team: str,
    home_team_id: str,
    away_team: str,
    away_team_id: str,
    season_id: str,
    league: str,
    match_date: Optional[str] = None,
    season: Optional[str] = None,
    data_provider: str = "footystats",
    fixture_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    数据策略层核心工具：并行采集并融合单场比赛所需的全部数据，
    返回结构化的 MatchContext 字典。

    Skill 应优先调用此工具（而非逐一调用 provider 工具），
    自动处理数据来源选择、fallback 链、缓存和质量评分。

    Args:
        match_id:      FootyStats 比赛 ID（Step 1 从 get_todays_matches 提取）
        home_team:     主队名称（如 "Arsenal"）
        home_team_id:  FootyStats 主队 ID（homeID 字段）
        away_team:     客队名称（如 "Chelsea"）
        away_team_id:  FootyStats 客队 ID（awayID 字段）
        season_id:     FootyStats competition/season ID（competition_id 字段，用于积分榜）
        league:        联赛名（如 "Premier League"，用于 Understat 映射 + 联赛参数）
        match_date:    比赛日期 YYYY-MM-DD（可选，帮助推断 Understat 赛季）
        season:        Understat 赛季年份（如 "2025"），不传时自动从 match_date 推断
        data_provider: 数据提供商，"footystats"（默认）或 "sportmonks"
        fixture_id:    Sportmonks fixture ID（当 data_provider="sportmonks" 时使用）；
                       不传时回退到 match_id

    Returns:
        MatchContext 序列化字典，包含以下顶层字段：
        - match_id, league, home_team, away_team, match_date
        - xg: {home_xg_for, home_xg_against, away_xg_for, away_xg_against, source, quality}
        - home_form_5 / home_form_10 / away_form_5 / away_form_10: 近况统计窗口
        - home_standing / away_standing: 积分榜状态
        - odds: {home_win, draw, away_win, source, quality}
        - data_gaps: 缺失数据项列表（如 ["lineups", "injuries", "odds_movement"]）
        - overall_quality: 综合质量评分 0.0–1.0
        - sources: 各层数据来源字典

    数据策略（自动处理，Skill 无需关心）：
        xG    : Understat 球队统计（6 大联赛）→ FootyStats 近况代理 → 联赛均值
        近况   : FootyStats get_team_last_x_stats（主/客并行）
        积分榜  : FootyStats get_league_tables → Sportmonks get_standings
        赔率   : FootyStats match_details → Sportmonks prematch_odds
        伤停/阵容: v1 标注缺失（data_gaps 中可见）
    """
    try:
        effective_fixture_id = fixture_id or match_id
        sportmonks = get_sportmonks() if data_provider == "sportmonks" else None

        fusion = DataFusion(
            data_provider=data_provider,
            footystats=get_footystats(),
            understat=get_understat(),
            sportmonks=sportmonks,
        )
        ctx = await fusion.build(
            fixture_id=str(effective_fixture_id),
            match_id=str(match_id),
            home_team=home_team,
            home_team_id=str(home_team_id),
            away_team=away_team,
            away_team_id=str(away_team_id),
            season_id=str(season_id),
            league=league,
            match_date=match_date,
            season=season,
        )
        return ctx.to_dict()
    except Exception as exc:
        logger.error(f"[goalcast_resolve_match] {exc}")
        return {
            "error": "RESOLVE_ERROR",
            "message": str(exc),
            "match_id": match_id,
            "home_team": home_team,
            "away_team": away_team,
        }


@mcp.tool()
async def goalcast_get_todays_matches(
    data_provider: str,
    date: Optional[str] = None,
    league_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    通过指定 data_provider 获取今日/指定日期的比赛列表。
    返回标准化 MatchSummary 列表，字段与 provider 无关。

    Args:
        data_provider: "sportmonks" | "footystats"
        date:          YYYY-MM-DD，默认今天
        league_filter: 联赛名过滤（子字符串匹配，不区分大小写）

    Returns:
        [{ home_team, away_team, competition, kickoff_time,
           match_id, home_team_id, away_team_id, season_id }, ...]
    """
    target_date = date or datetime.date.today().isoformat()

    try:
        if data_provider == "sportmonks":
            raw = await handle_api_call(
                "Sportmonks",
                get_sportmonks().get_fixtures_by_date(
                    target_date,
                    include="participants;scores;league;season",
                ),
            )
            return _normalize_sportmonks_fixtures(raw, league_filter)

        elif data_provider == "footystats":
            raw = await handle_api_call(
                "FootyStats",
                get_footystats().get_todays_matches(target_date, timezone=None),
            )
            return _normalize_footystats_fixtures(raw, league_filter)

        else:
            return [{"error": f"Unknown data_provider: {data_provider}"}]

    except Exception as exc:
        logger.error(f"[goalcast_get_todays_matches] {exc}")
        return [{"error": str(exc)}]




if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "sse":
        mcp.run(transport="sse")
    else:
        mcp.run()

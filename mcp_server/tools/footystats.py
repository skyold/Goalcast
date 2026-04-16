"""Goalcast FootyStats / DataFusion MCP 工具。"""

from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional

from datasource.datafusion.fusion import DataFusion
from utils.logger import logger

try:
    from internal import (
        get_footystats,
        get_understat,
        handle_api_call,
        _normalize_footystats_fixtures,
    )
except ImportError:
    from mcp_server.internal import (
        get_footystats,
        get_understat,
        handle_api_call,
        _normalize_footystats_fixtures,
    )


def register_goalcast_footystats_tools(mcp: Any) -> None:
    """注册 FootyStats 核心和 DataFusion 编排相关工具。"""

    @mcp.tool()
    async def goalcast_footystats_resolve_match(
        match_id: str,
        home_team: str,
        home_team_id: str,
        away_team: str,
        away_team_id: str,
        season_id: str,
        league: str,
        match_date: Optional[str] = None,
        season: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        基于 FootyStats + Understat 的 DataFusion 单场编排入口。

        该工具以 FootyStats 作为主数据源，负责统一组装近况、积分榜、赔率等信息，
        并在需要时结合 Understat 提供 xG 相关补充数据。
        """
        try:
            fusion = DataFusion(
                footystats=get_footystats(),
                understat=get_understat(),
            )
            context = await fusion.build(
                fixture_id=str(match_id),
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
            return context.to_dict()
        except Exception as exc:
            logger.error(f"[goalcast_footystats_resolve_match] {exc}")
            return {
                "error": "RESOLVE_ERROR",
                "message": str(exc),
                "match_id": match_id,
                "home_team": home_team,
                "away_team": away_team,
            }

    @mcp.tool()
    async def goalcast_footystats_get_todays_matches(
        date: Optional[str] = None,
        league_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """获取 FootyStats 今日或指定日期赛程，并返回标准化后的比赛摘要列表。"""
        target_date = date or datetime.date.today().isoformat()
        try:
            raw = await handle_api_call(
                "FootyStats",
                get_footystats().get_todays_matches(target_date, timezone=None),
            )
            return _normalize_footystats_fixtures(raw, league_filter)
        except Exception as exc:
            logger.error(f"[goalcast_footystats_get_todays_matches] {exc}")
            return [{"error": str(exc)}]

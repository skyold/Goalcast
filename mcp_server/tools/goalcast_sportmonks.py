"""独立的 Sportmonks MCP 工具注册模块。"""

from __future__ import annotations

from typing import Any, Callable

from data_strategy.sportmonks.models import SportmonksMatchData


def register_goalcast_sportmonks_tools(mcp: Any, service_factory: Callable[[], Any]) -> None:
    """向 MCP 注册 goalcast_sportmonks_* 工具。"""
    if service_factory is None:
        raise ValueError("service_factory is required")

    def _service() -> Any:
        return service_factory()

    @mcp.tool(
        description="读取今日比赛列表，可按联赛过滤；缓存缺失时可自动预热。"
    )
    async def goalcast_sportmonks_get_todays_matches(
        leagues: list[str] | None = None,
        warm_if_missing: bool = True,
    ) -> dict[str, Any]:
        """读取今日比赛列表，可按联赛过滤；缓存缺失时可自动预热。"""
        fixtures = await _service().get_todays_matches(
            leagues=leagues,
            warm_if_missing=warm_if_missing,
        )
        data = _serialize(fixtures)
        return {
            "ok": True,
            "count": len(data),
            "fixtures": data,
            "data": data,
        }

    @mcp.tool(
        description="预热今日比赛缓存，提前拉取 fixtures 与单场分层数据。"
    )
    async def goalcast_sportmonks_prefetch_today(
        leagues: list[str] | None = None,
        refresh_stale: bool = False,
    ) -> dict[str, Any]:
        """预热今日比赛缓存，提前拉取 fixtures 与单场分层数据。"""
        result = await _service().prefetch_today(
            leagues=leagues,
            refresh_stale=refresh_stale,
        )
        return {
            "ok": True,
            "data": _serialize(result),
        }

    @mcp.tool(
        description="读取指定日期的比赛列表，可按联赛过滤；必要时自动预热缓存。"
    )
    async def goalcast_sportmonks_get_fixtures(
        date: str | None = None,
        leagues: list[str] | None = None,
        warm_if_missing: bool = True,
    ) -> dict[str, Any]:
        """读取指定日期的比赛列表，可按联赛过滤；必要时自动预热缓存。"""
        fixtures = await _service().get_fixtures(
            date=date,
            leagues=leagues,
            warm_if_missing=warm_if_missing,
        )
        data = _serialize(fixtures)
        return {
            "ok": True,
            "count": len(data),
            "fixtures": data,
            "data": data,
        }

    @mcp.tool(
        description="预热指定日期的比赛缓存，并返回预热结果汇总。"
    )
    async def goalcast_sportmonks_prefetch(
        date: str | None = None,
        leagues: list[str] | None = None,
        refresh_stale: bool = False,
    ) -> dict[str, Any]:
        """预热指定日期的比赛缓存，并返回预热结果汇总。"""
        result = await _service().prefetch(
            date=date,
            leagues=leagues,
            refresh_stale=refresh_stale,
        )
        return {
            "ok": True,
            "data": _serialize(result),
        }

    @mcp.tool(
        description="读取单场比赛快照，返回 xG、赔率、阵容、H2H 等 Sportmonks 专属分层数据。"
    )
    async def goalcast_sportmonks_get_match(
        fixture_id: int,
        date: str | None = None,
        refresh_if_stale: bool = True,
    ) -> dict[str, Any]:
        """读取单场比赛快照，返回 xG、赔率、阵容、H2H 等 Sportmonks 专属分层数据。"""
        snapshot = await _service().get_match(
            fixture_id=fixture_id,
            date=date,
            refresh_if_stale=refresh_if_stale,
        )
        return {
            "ok": True,
            "cache_status": getattr(snapshot, "cache_status", None),
            "data": _serialize(snapshot),
        }

    @mcp.tool(
        description="强制刷新单场比赛缓存，可只刷新指定 layers。"
    )
    async def goalcast_sportmonks_refresh_match(
        fixture_id: int,
        date: str | None = None,
        layers: list[str] | None = None,
    ) -> dict[str, Any]:
        """强制刷新单场比赛缓存，可只刷新指定 layers。"""
        snapshot = await _service().refresh_match(
            fixture_id=fixture_id,
            date=date,
            layers=layers,
        )
        return {
            "ok": True,
            "cache_status": getattr(snapshot, "cache_status", None),
            "data": _serialize(snapshot),
        }

    @mcp.tool(
        description="查看日期级或单场级缓存状态，用于判断是否已预热以及哪些层仍缺失。"
    )
    async def goalcast_sportmonks_get_cache_status(
        date: str | None = None,
        fixture_id: int | None = None,
    ) -> dict[str, Any]:
        """查看日期级或单场级缓存状态，用于判断是否已预热以及哪些层仍缺失。"""
        payload = await _service().get_cache_status(date=date, fixture_id=fixture_id)
        return {
            "ok": True,
            "data": _serialize(payload),
        }


def _serialize(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, tuple):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    return value


async def legacy_goalcast_sm_get_fixtures(
    service: Any,
    leagues: list[str],
    date: str | None = None,
) -> dict[str, Any]:
    fixtures = await service.get_fixtures(
        date=date,
        leagues=leagues,
        warm_if_missing=True,
    )
    data = [_fixture_to_legacy(item) for item in fixtures]
    return {
        "date": date,
        "count": len(data),
        "fixtures": data,
    }


async def legacy_goalcast_sm_fetch(
    service: Any,
    fixture_id: int,
    home_team: str,
    home_team_id: int,
    away_team: str,
    away_team_id: int,
    season_id: int,
    league: str,
    match_date: str,
    season: str | None = None,
) -> dict[str, Any]:
    snapshot = await service.get_match(
        fixture_id=fixture_id,
        date=match_date,
        refresh_if_stale=True,
    )
    return _snapshot_to_legacy_match_data(
        snapshot=_serialize(snapshot),
        fixture_id=fixture_id,
        home_team=home_team,
        home_team_id=home_team_id,
        away_team=away_team,
        away_team_id=away_team_id,
        season_id=season_id,
        league=league,
        match_date=match_date,
        season=season,
    )


def _fixture_to_legacy(fixture: Any) -> dict[str, Any]:
    payload = _serialize(fixture)
    return {
        "fixture_id": payload.get("fixture_id"),
        "home_team": payload.get("home_team_name"),
        "home_team_id": payload.get("home_team_id"),
        "away_team": payload.get("away_team_name"),
        "away_team_id": payload.get("away_team_id"),
        "season_id": payload.get("season_id"),
        "league": payload.get("league_name"),
        "kickoff_time": payload.get("kickoff_time"),
    }


def _snapshot_to_legacy_match_data(
    snapshot: dict[str, Any],
    fixture_id: int,
    home_team: str,
    home_team_id: int,
    away_team: str,
    away_team_id: int,
    season_id: int,
    league: str,
    match_date: str,
    season: str | None = None,
) -> dict[str, Any]:
    xg = snapshot.get("xg") or {}
    odds = snapshot.get("odds") or {}
    asian_handicap = snapshot.get("asian_handicap") or {}
    predictions = snapshot.get("predictions") or {}
    lineups = snapshot.get("lineups")
    h2h = snapshot.get("h2h")
    if isinstance(h2h, list):
        h2h = {"entries": h2h}

    legacy = SportmonksMatchData(
        fixture_id=fixture_id,
        home_team=home_team,
        away_team=away_team,
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        league=league,
        season_id=season_id,
        season=season or "",
        match_date=match_date,
        kickoff_time=snapshot.get("kickoff_time", ""),
        xg_home_for=float(xg.get("home_xg_for", 0.0) or 0.0),
        xg_home_against=float(xg.get("home_xg_against", 0.0) or 0.0),
        xg_away_for=float(xg.get("away_xg_for", 0.0) or 0.0),
        xg_away_against=float(xg.get("away_xg_against", 0.0) or 0.0),
        xg_source=str(xg.get("source") or "sportmonks_snapshot"),
        xg_quality=float(xg.get("quality", 0.0) or 0.0),
        home_standing=_extract_side_standing(snapshot.get("standings"), "home"),
        away_standing=_extract_side_standing(snapshot.get("standings"), "away"),
        odds_home_win=odds.get("home_win"),
        odds_draw=odds.get("draw"),
        odds_away_win=odds.get("away_win"),
        odds_bookmaker=odds.get("bookmaker"),
        ah_line=(
            asian_handicap.get("ah_line", asian_handicap.get("home"))
            if isinstance(asian_handicap, dict)
            else None
        ),
        ah_home_odds=asian_handicap.get("ah_home_odds"),
        ah_away_odds=asian_handicap.get("ah_away_odds"),
        odds_movement=snapshot.get("odds_movement"),
        lineups=lineups,
        h2h=h2h,
        predictions=_normalize_predictions(predictions),
        overall_quality=float(snapshot.get("overall_quality", 0.0) or 0.0),
        data_gaps=list(snapshot.get("missing_layers") or snapshot.get("data_gaps") or []),
    )
    return legacy.to_dict()


def _extract_side_standing(standings: Any, side: str) -> Any:
    if not isinstance(standings, dict):
        return None
    if side in standings:
        return standings.get(side)
    return None


def _normalize_predictions(predictions: Any) -> Any:
    if not isinstance(predictions, dict):
        return predictions
    if {"home_win", "draw", "away_win"} <= set(predictions):
        return predictions
    if {"home", "draw", "away"} <= set(predictions):
        return {
            "home_win": predictions.get("home"),
            "draw": predictions.get("draw"),
            "away_win": predictions.get("away"),
        }
    return predictions

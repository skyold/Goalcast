"""Unified read endpoints over signals_snapshot.

Four surfaces:
  GET  /api/signals/catalog        — all registered signals with metadata +
                                     methodology + last-7-day aggregate stats
                                     (Phase 1 of PRD signal-catalog-and-subscriptions)
  GET  /api/signals/active         — top-N rows across ALL signals, ranked by strength
  GET  /api/signals/:type          — list one signal's recent rows, with fixture meta
  POST /api/signals/:type/backtest — historical replay of (signal × conditions)
                                     against FT outcomes (Phase 3)

GET endpoints attach team / competition labels at the SQL boundary so the
frontend renders without secondary fetches. JSON parsing of value_json happens
here (SQLite stores it as TEXT).
"""
from __future__ import annotations

import json
from typing import Annotated, Literal, Optional

import aiosqlite
from fastapi import APIRouter, Body, Depends, HTTPException, Query

from database import get_db
from services.auth import get_current_user_optional
from services.signals import REGISTERED
from services.signals.backtest import run_backtest

router = APIRouter()


SELECT_WITH_META = """
    SELECT s.fixture_id, s.signal_type, s.signal_version, s.waypoint,
           s.scope, s.value_json, s.strength, s.captured_at,
           f.home_team, f.away_team,
           th.name_zh AS home_team_zh, ta.name_zh AS away_team_zh,
           f.competition_id, f.competition_name,
           c.name_zh AS competition_name_zh,
           f.kickoff_utc, f.status
    FROM signals_snapshot s
    JOIN fixtures f ON f.id = s.fixture_id
    LEFT JOIN teams th ON th.id = f.home_team_id
    LEFT JOIN teams ta ON ta.id = f.away_team_id
    LEFT JOIN competitions c ON c.id = f.competition_id
"""


def _row_to_item(r: dict) -> dict:
    try:
        value = json.loads(r["value_json"])
    except (ValueError, TypeError):
        value = {}
    return {
        "fixture_id":          r["fixture_id"],
        "signal_type":         r["signal_type"],
        "signal_version":      r["signal_version"],
        "waypoint":            r["waypoint"],
        "scope":               r["scope"],
        "strength":            r["strength"],
        "captured_at":         r["captured_at"],
        "value":               value,
        "home_team":           r["home_team"],
        "away_team":           r["away_team"],
        "home_team_zh":        r["home_team_zh"],
        "away_team_zh":        r["away_team_zh"],
        "competition_id":      r["competition_id"],
        "competition_name":    r["competition_name"],
        "competition_name_zh": r["competition_name_zh"],
        "kickoff_utc":         r["kickoff_utc"],
        "fixture_status":      r["status"],
    }


@router.get("/signals/catalog")
async def get_catalog(
    locale: Annotated[Literal["zh", "en"], Query()] = "zh",
    db: aiosqlite.Connection = Depends(get_db),
):
    """Catalog of all registered signals with full metadata for the
    /insights/signals master-detail UI.

    Per signal returns:
      - identity:    signal_type, signal_version, scope
      - contract:    description, output_schema, strength_formula, failure_modes
                     (read directly from BaseSignal ClassVars)
      - docs:        methodology_md + methodology_updated_at (from
                     signal_methodology table; null if not seeded yet)
      - live stats:  stats_7d {triggered, avg_strength, max_strength} from
                     signals_snapshot last 7 days; null when zero rows

    `house_book` is reserved for Phase 4 of the signal-catalog PRD (per-signal
    House Books). It is intentionally always null in V1 so the frontend can
    bind to the shape immediately.
    """
    # 7-day aggregate stats per signal_type from signals_snapshot.
    async with db.execute(
        """SELECT signal_type,
                  COUNT(*)      AS triggered,
                  AVG(strength) AS avg_strength,
                  MAX(strength) AS max_strength
           FROM signals_snapshot
           WHERE captured_at >= datetime('now', '-7 days')
           GROUP BY signal_type"""
    ) as cur:
        stats_by_type: dict[str, dict] = {
            r["signal_type"]: {
                "triggered":    int(r["triggered"] or 0),
                "avg_strength": float(r["avg_strength"]) if r["avg_strength"] is not None else None,
                "max_strength": float(r["max_strength"]) if r["max_strength"] is not None else None,
            }
            for r in await cur.fetchall()
        }

    # Methodology bodies for requested locale.
    async with db.execute(
        "SELECT signal_type, body_md, updated_at FROM signal_methodology WHERE locale=?",
        (locale,),
    ) as cur:
        methodology_by_type: dict[str, dict] = {
            r["signal_type"]: {"body_md": r["body_md"], "updated_at": r["updated_at"]}
            for r in await cur.fetchall()
        }

    items: list[dict] = []
    for sig in REGISTERED:
        m = methodology_by_type.get(sig.signal_type)
        items.append({
            "signal_type":            sig.signal_type,
            "signal_version":         sig.signal_version,
            "scope":                  sig.scope,
            "description":            sig.description,
            "output_schema":          sig.output_schema,
            "strength_formula":       sig.strength_formula,
            "failure_modes":          sig.failure_modes,
            "methodology_md":         m["body_md"]    if m else None,
            "methodology_updated_at": m["updated_at"] if m else None,
            "stats_7d":               stats_by_type.get(sig.signal_type),
            "house_book":             None,  # Phase 4 of PRD signal-catalog-and-subscriptions
        })
    return {"locale": locale, "items": items, "count": len(items)}


@router.get("/signals/active")
async def get_active(
    waypoint: Annotated[Optional[str], Query()] = None,
    min_strength: Annotated[float, Query(ge=0, le=1)] = 0.3,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    only_upcoming: Annotated[bool, Query()] = True,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Cross-signal feed of currently-relevant rows, ranked by strength desc.

    Defaults tuned for the public landing view: only upcoming fixtures
    (status='NS'), strength >= 0.3, top 50 across all signal types."""
    sql = SELECT_WITH_META + "WHERE s.strength >= ?"
    params: list = [min_strength]
    if waypoint is not None:
        sql += " AND s.waypoint = ?"
        params.append(waypoint)
    if only_upcoming:
        sql += " AND f.status = 'NS'"
    sql += " ORDER BY s.strength DESC, s.captured_at DESC LIMIT ?"
    params.append(limit)
    async with db.execute(sql, params) as cur:
        rows = [dict(r) for r in await cur.fetchall()]
    return {"items": [_row_to_item(r) for r in rows], "count": len(rows)}


@router.get("/signals/{signal_type}")
async def get_by_type(
    signal_type: str,
    fixture_id: Annotated[Optional[int], Query()] = None,
    competition_id: Annotated[Optional[int], Query()] = None,
    waypoint: Annotated[Optional[str], Query()] = None,
    min_strength: Annotated[float, Query(ge=0, le=1)] = 0.0,
    only_upcoming: Annotated[bool, Query()] = True,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    db: aiosqlite.Connection = Depends(get_db),
):
    if not signal_type.startswith("GS-"):
        raise HTTPException(status_code=400, detail="signal_type must start with 'GS-'")
    sql = SELECT_WITH_META + "WHERE s.signal_type = ? AND s.strength >= ?"
    params: list = [signal_type, min_strength]
    if fixture_id is not None:
        sql += " AND s.fixture_id = ?"
        params.append(fixture_id)
    if competition_id is not None:
        sql += " AND f.competition_id = ?"
        params.append(competition_id)
    if waypoint is not None:
        sql += " AND s.waypoint = ?"
        params.append(waypoint)
    if only_upcoming:
        sql += " AND f.status = 'NS'"
    sql += " ORDER BY s.strength DESC, s.captured_at DESC LIMIT ?"
    params.append(limit)
    async with db.execute(sql, params) as cur:
        rows = [dict(r) for r in await cur.fetchall()]
    return {
        "signal_type": signal_type,
        "items": [_row_to_item(r) for r in rows],
        "count": len(rows),
    }


@router.post("/signals/{signal_type}/backtest")
async def post_backtest(
    signal_type: str,
    body: Annotated[dict, Body(...)] = ...,  # parsed below for explicit error shapes
    user: Optional[dict] = Depends(get_current_user_optional),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Replay historical signals_snapshot rows against FT outcomes through the
    same conditions evaluator used by the forward snapshot worker.

    Body schema (all keys optional with sensible defaults):
        {
          "conditions": {"strength_min": 0.5, "filters": [...]},
          "window":      "7d" | "14d" | "30d",     # default "30d"
          "match_scope": "all" | "my_leagues"      # default "all"
        }

    Returns BacktestResult (see services.signals.backtest):
        {signal_type, window, match_scope, considered_count, settled_count,
         roi_pct, hit_rate, max_drawdown_pct, equity_curve}
    """
    if not signal_type.startswith("GS-"):
        raise HTTPException(status_code=400, detail="signal_type must start with 'GS-'")

    if not isinstance(body, dict):
        raise HTTPException(status_code=422, detail="body must be a JSON object")

    conditions = body.get("conditions") or {}
    if not isinstance(conditions, dict):
        raise HTTPException(status_code=422, detail="conditions must be an object")

    window = body.get("window", "30d")
    if window not in ("7d", "14d", "30d"):
        raise HTTPException(status_code=422, detail="window must be one of '7d','14d','30d'")

    match_scope = body.get("match_scope", "all")
    if match_scope not in ("all", "my_leagues"):
        raise HTTPException(status_code=422, detail="match_scope must be 'all' or 'my_leagues'")
    if match_scope == "my_leagues" and user is None:
        raise HTTPException(status_code=401, detail="match_scope='my_leagues' requires login")

    user_id = user["id"] if user else None
    result = await run_backtest(
        db,
        signal_type=signal_type,
        conditions=conditions,
        window=window,         # type: ignore[arg-type]
        match_scope=match_scope,  # type: ignore[arg-type]
        user_id=user_id,
    )
    return result

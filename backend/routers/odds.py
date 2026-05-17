from typing import Annotated
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query
import aiosqlite
from database import get_db
from services.auth import get_current_user_optional, get_user_competition_prefs
from services.value_bets import compute_edge

router = APIRouter()

@router.get("/dropping-odds")
async def dropping_odds(
    min_drop: Annotated[float, Query()] = 10.0,
    market: Annotated[str | None, Query()] = None,
    db: aiosqlite.Connection = Depends(get_db),
    user: dict | None = Depends(get_current_user_optional),
):
    user_prefs = await get_user_competition_prefs(user, db)
    if user_prefs is not None and not user_prefs:
        return {"items": [], "synced_at": datetime.now(timezone.utc).isoformat()}
    params: list = [-abs(min_drop)]
    market_clause = ""
    if market:
        market_clause = "AND s.drop_market=?"
        params.append(market)
    prefs_clause = ""
    if user_prefs:
        ids = sorted(user_prefs)
        prefs_clause = f"AND f.competition_id IN ({','.join('?'*len(ids))})"
        params.extend(ids)
    sql = f"""
        SELECT s.*, f.home_team, f.away_team, f.competition_name, f.kickoff_utc,
               th.name_zh AS home_team_zh,
               ta.name_zh AS away_team_zh,
               c.name_zh  AS competition_name_zh
        FROM odds_snapshots s
        JOIN fixtures f ON f.id = s.fixture_id
        LEFT JOIN teams th ON th.id = f.home_team_id
        LEFT JOIN teams ta ON ta.id = f.away_team_id
        LEFT JOIN competitions c ON c.id = f.competition_id
        WHERE s.drop_pct<=? {market_clause} {prefs_clause}
        ORDER BY s.drop_pct ASC, s.recorded_at DESC LIMIT 100
    """
    async with db.execute(sql, params) as cur:
        rows = await cur.fetchall()
    return {"items": [dict(r) for r in rows], "synced_at": datetime.now(timezone.utc).isoformat()}

@router.get("/value-bets")
async def value_bets(
    min_edge: Annotated[float, Query()] = 5.0,
    db: aiosqlite.Connection = Depends(get_db),
    user: dict | None = Depends(get_current_user_optional),
):
    user_prefs = await get_user_competition_prefs(user, db)
    if user_prefs is not None and not user_prefs:
        return {"items": []}
    prefs_clause = ""
    prefs_params: list = []
    if user_prefs:
        ids = sorted(user_prefs)
        prefs_clause = f"AND f.competition_id IN ({','.join('?'*len(ids))})"
        prefs_params = ids
    sql = """
        SELECT f.id as fixture_id, f.home_team, f.away_team, f.competition_name, f.kickoff_utc,
               f.prob_home_win, f.prob_draw, f.prob_away_win,
               s.odds_home, s.odds_draw, s.odds_away,
               th.name_zh AS home_team_zh,
               ta.name_zh AS away_team_zh,
               c.name_zh  AS competition_name_zh
        FROM fixtures f
        LEFT JOIN teams th ON th.id = f.home_team_id
        LEFT JOIN teams ta ON ta.id = f.away_team_id
        LEFT JOIN competitions c ON c.id = f.competition_id
        LEFT JOIN (
            SELECT fixture_id, odds_home, odds_draw, odds_away FROM odds_snapshots
            WHERE (fixture_id, recorded_at) IN (
                SELECT fixture_id, MAX(recorded_at) FROM odds_snapshots GROUP BY fixture_id
            )
        ) s ON f.id=s.fixture_id
        WHERE f.status='pre' {prefs_clause} ORDER BY f.kickoff_utc
    """
    async with db.execute(sql.format(prefs_clause=prefs_clause), prefs_params) as cur:
        rows = await cur.fetchall()
    items = []
    for r in rows:
        d = dict(r)
        for sel, prob_k, odds_k in (("home","prob_home_win","odds_home"),
                                     ("draw","prob_draw","odds_draw"),
                                     ("away","prob_away_win","odds_away")):
            edge = compute_edge(d.get(prob_k), d.get(odds_k))
            if edge is not None and edge >= min_edge:
                items.append({"fixture_id": d["fixture_id"], "home_team": d["home_team"],
                               "away_team": d["away_team"], "competition_name": d["competition_name"],
                               "home_team_zh": d.get("home_team_zh"),
                               "away_team_zh": d.get("away_team_zh"),
                               "competition_name_zh": d.get("competition_name_zh"),
                               "kickoff_utc": d["kickoff_utc"], "selection": sel,
                               "edge_pct": edge, "prob": d[prob_k], "odds": d[odds_k]})
    items.sort(key=lambda x: x["edge_pct"], reverse=True)
    return {"items": items}

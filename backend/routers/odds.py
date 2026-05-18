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
    ignore_prefs: Annotated[bool, Query()] = False,
    db: aiosqlite.Connection = Depends(get_db),
    user: dict | None = Depends(get_current_user_optional),
):
    # `ignore_prefs=true` lets the dashboard show "all leagues" comparison KPIs
    # alongside the per-user filtered view.
    user_prefs = None if ignore_prefs else await get_user_competition_prefs(user, db)
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
    ignore_prefs: Annotated[bool, Query()] = False,
    db: aiosqlite.Connection = Depends(get_db),
    user: dict | None = Depends(get_current_user_optional),
):
    user_prefs = None if ignore_prefs else await get_user_competition_prefs(user, db)
    if user_prefs is not None and not user_prefs:
        return {"items": []}
    prefs_clause = ""
    prefs_params: list = []
    if user_prefs:
        ids = sorted(user_prefs)
        prefs_clause = f"AND f.competition_id IN ({','.join('?'*len(ids))})"
        prefs_params = ids
    # Probability source: `predictions` table (sims-based). `fixtures.prob_*`
    # columns exist on schema but are 100% NULL in observed data.
    # Odds source: Pinnacle (bookmaker_id=1) 1x2 (market_id=6) from
    # `bookmaker_odds`. `odds_snapshots.odds_*` columns are also 100% NULL —
    # the snapshot pipeline only writes drop_pct, not full odds.
    sql = f"""
        SELECT f.id as fixture_id, f.home_team, f.away_team, f.competition_name, f.kickoff_utc,
               th.name_zh AS home_team_zh,
               ta.name_zh AS away_team_zh,
               c.name_zh  AS competition_name_zh,
               p.simulations, p.home_win, p.draw, p.away_win,
               bo_h.current AS odds_home,
               bo_d.current AS odds_draw,
               bo_a.current AS odds_away
        FROM fixtures f
        JOIN predictions p ON p.fixture_id = f.id
        LEFT JOIN teams th ON th.id = f.home_team_id
        LEFT JOIN teams ta ON ta.id = f.away_team_id
        LEFT JOIN competitions c ON c.id = f.competition_id
        LEFT JOIN bookmaker_odds bo_h ON bo_h.fixture_id = f.id
            AND bo_h.bookmaker_id = 1 AND bo_h.market_id = 6 AND bo_h.outcome = 'home'
        LEFT JOIN bookmaker_odds bo_d ON bo_d.fixture_id = f.id
            AND bo_d.bookmaker_id = 1 AND bo_d.market_id = 6 AND bo_d.outcome = 'draw'
        LEFT JOIN bookmaker_odds bo_a ON bo_a.fixture_id = f.id
            AND bo_a.bookmaker_id = 1 AND bo_a.market_id = 6 AND bo_a.outcome = 'away'
        WHERE f.status='NS' AND p.simulations > 0
              AND bo_h.current IS NOT NULL
              AND bo_d.current IS NOT NULL
              AND bo_a.current IS NOT NULL
              {prefs_clause}
        ORDER BY f.kickoff_utc
    """
    async with db.execute(sql, prefs_params) as cur:
        rows = await cur.fetchall()
    items = []
    for r in rows:
        d = dict(r)
        sims = d["simulations"]
        if not sims:
            continue
        for sel, win_k, odds_k in (("home", "home_win", "odds_home"),
                                    ("draw", "draw",     "odds_draw"),
                                    ("away", "away_win", "odds_away")):
            prob = d[win_k] / sims
            odds = d[odds_k]
            edge = compute_edge(prob, odds)
            if edge is not None and edge >= min_edge:
                items.append({
                    "fixture_id": d["fixture_id"],
                    "home_team": d["home_team"], "away_team": d["away_team"],
                    "home_team_zh": d.get("home_team_zh"),
                    "away_team_zh": d.get("away_team_zh"),
                    "competition_name": d["competition_name"],
                    "competition_name_zh": d.get("competition_name_zh"),
                    "kickoff_utc": d["kickoff_utc"], "selection": sel,
                    "edge_pct": edge,
                    "prob": round(prob, 4),
                    "odds": odds,
                })
    items.sort(key=lambda x: x["edge_pct"], reverse=True)
    return {"items": items}

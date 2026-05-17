"""Phase 2 — analyst insights endpoints.

Mispricing = |model_probability - de-vigged market implied probability|.
- Model probability comes from `predictions` (simulation counts / total).
- Market implied probability is computed from Pinnacle (bookmaker_id=1) 1x2
  odds (market_id=6) with vig removed: raw_imp[i] / sum(raw_imp).
- For each fixture we emit one row per selection (home / draw / away) where
  |delta| >= min_abs_edge.
"""
from __future__ import annotations

from datetime import date as date_type
from typing import Annotated

import aiosqlite
from fastapi import APIRouter, Depends, Query

from database import get_db
from services.auth import get_current_user_optional, get_user_competition_prefs

router = APIRouter()


@router.get("/insights/mispricings")
async def list_mispricings(
    date: Annotated[str | None, Query()] = None,
    min_abs_edge: Annotated[float, Query(ge=0, le=100)] = 3.0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    db: aiosqlite.Connection = Depends(get_db),
    user: dict | None = Depends(get_current_user_optional),
):
    user_prefs = await get_user_competition_prefs(user, db)
    if user_prefs is not None and not user_prefs:
        return {"items": [], "date": date or str(date_type.today())}

    target = date or str(date_type.today())

    prefs_clause = ""
    prefs_params: list = []
    if user_prefs:
        ids = sorted(user_prefs)
        prefs_clause = f"AND f.competition_id IN ({','.join('?'*len(ids))})"
        prefs_params = ids

    sql = f"""
        SELECT f.id AS fixture_id, f.home_team, f.away_team,
               th.name_zh AS home_team_zh, ta.name_zh AS away_team_zh,
               f.competition_name, c.name_zh AS competition_name_zh,
               f.kickoff_utc, f.predictability,
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
        WHERE date(f.kickoff_utc) = ?
          AND f.status = 'NS'
          AND p.simulations > 0
          AND bo_h.current IS NOT NULL
          AND bo_d.current IS NOT NULL
          AND bo_a.current IS NOT NULL
          {prefs_clause}
    """
    params = [target, *prefs_params]
    async with db.execute(sql, params) as cur:
        rows = [dict(r) for r in await cur.fetchall()]

    items: list[dict] = []
    for r in rows:
        sims = r["simulations"]
        if not sims:
            continue
        oh, od, oa = r["odds_home"], r["odds_draw"], r["odds_away"]
        raw_sum = (1.0 / oh) + (1.0 / od) + (1.0 / oa)
        # De-vigged implied probability per selection.
        imp = {
            "home": (1.0 / oh) / raw_sum,
            "draw": (1.0 / od) / raw_sum,
            "away": (1.0 / oa) / raw_sum,
        }
        model = {
            "home": r["home_win"] / sims,
            "draw": r["draw"] / sims,
            "away": r["away_win"] / sims,
        }
        odds_map = {"home": oh, "draw": od, "away": oa}

        for sel in ("home", "draw", "away"):
            delta_pct = (model[sel] - imp[sel]) * 100.0
            if abs(delta_pct) < min_abs_edge:
                continue
            items.append({
                "fixture_id": r["fixture_id"],
                "home_team": r["home_team"], "home_team_zh": r["home_team_zh"],
                "away_team": r["away_team"], "away_team_zh": r["away_team_zh"],
                "competition_name": r["competition_name"],
                "competition_name_zh": r["competition_name_zh"],
                "kickoff_utc": r["kickoff_utc"],
                "predictability": r["predictability"],
                "selection": sel,
                "model_prob_pct": round(model[sel] * 100, 2),
                "market_prob_pct": round(imp[sel] * 100, 2),
                "delta_pct": round(delta_pct, 2),
                "odds": odds_map[sel],
            })

    items.sort(key=lambda x: abs(x["delta_pct"]), reverse=True)
    return {"items": items[:limit], "date": target}


@router.get("/insights/leagues/{competition_id}")
async def league_stats(
    competition_id: int,
    season_id: Annotated[int | None, Query()] = None,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Aggregate per-competition stats for finished (status='FT') fixtures.

    Returns goal/result distribution + a model_hit_rate measuring how often the
    model's top-probability pick agrees with the actual winner.
    """
    async with db.execute(
        "SELECT name_en, name_zh FROM competitions WHERE id=?", (competition_id,)
    ) as cur:
        comp_row = await cur.fetchone()
    comp_name = comp_row["name_en"] if comp_row else None
    comp_name_zh = comp_row["name_zh"] if comp_row else None

    season_clause = ""
    params: list = [competition_id]
    if season_id is not None:
        season_clause = " AND f.season_id = ?"
        params.append(season_id)

    # historical_predictions @ waypoint='kickoff' is the pre-game model state
    # captured by the snapshot pipeline (services/snapshot.py). Until the pipeline
    # has run a full kickoff cycle on a fixture, hp.* is NULL and the model_*
    # metrics fall back to None (handled below).
    async with db.execute(
        f"""SELECT f.id, f.score_home, f.score_away, f.predictability,
                   hp.simulations, hp.home_win_pct, hp.draw_pct, hp.away_win_pct
            FROM fixtures f
            LEFT JOIN historical_predictions hp
              ON hp.fixture_id = f.id AND hp.waypoint = 'kickoff'
            WHERE f.competition_id = ? AND f.status = 'FT'
                  AND f.score_home IS NOT NULL AND f.score_away IS NOT NULL
                  {season_clause}""",
        params,
    ) as cur:
        rows = [dict(r) for r in await cur.fetchall()]

    n = len(rows)
    if n == 0:
        return {
            "competition_id": competition_id,
            "competition_name": comp_name,
            "competition_name_zh": comp_name_zh,
            "season_id": season_id,
            "matches_played": 0,
            "avg_goals": 0.0,
            "home_win_pct": 0.0,
            "draw_pct": 0.0,
            "away_win_pct": 0.0,
            "model_hit_rate_pct": None,
            "upset_pct": None,
            "predicted_count": 0,
        }

    home_wins = sum(1 for r in rows if r["score_home"] > r["score_away"])
    draws = sum(1 for r in rows if r["score_home"] == r["score_away"])
    away_wins = sum(1 for r in rows if r["score_home"] < r["score_away"])
    total_goals = sum((r["score_home"] or 0) + (r["score_away"] or 0) for r in rows)

    # model_hit_rate + upset compare the model's pre-game top pick (snapshotted
    # at the 'kickoff' waypoint) to the actual outcome. predicted_count will
    # grow as the snapshot pipeline accumulates kickoff captures.
    model_total = 0
    model_hits = 0
    for r in rows:
        sims = r.get("simulations")
        if not sims:
            continue
        model_total += 1
        picks = {"home": r["home_win_pct"], "draw": r["draw_pct"], "away": r["away_win_pct"]}
        top = max(picks, key=picks.get)
        actual = (
            "home" if r["score_home"] > r["score_away"]
            else "away" if r["score_home"] < r["score_away"]
            else "draw"
        )
        if top == actual:
            model_hits += 1

    return {
        "competition_id": competition_id,
        "competition_name": comp_name,
        "competition_name_zh": comp_name_zh,
        "season_id": season_id,
        "matches_played": n,
        "avg_goals": round(total_goals / n, 2),
        "home_win_pct": round(home_wins / n * 100, 1),
        "draw_pct":     round(draws    / n * 100, 1),
        "away_win_pct": round(away_wins / n * 100, 1),
        "model_hit_rate_pct": round(model_hits / model_total * 100, 1) if model_total else None,
        "upset_pct":          round((model_total - model_hits) / model_total * 100, 1) if model_total else None,
        "predicted_count":    model_total,
    }

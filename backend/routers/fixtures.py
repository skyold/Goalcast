import json
from datetime import date as date_type
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query
import aiosqlite
from database import get_db

router = APIRouter()

_FT = {"FT", "AET", "FT_PEN", "AWD", "ABD"}
_LIVE = {"1H", "HT", "2H", "ET", "BT", "INT", "LIVE"}

def _norm_status(s: str) -> str:
    if s in _FT:
        return "ft"
    if s in _LIVE:
        return "live"
    return "pre"

def _norm_stats(raw: dict | None) -> dict | None:
    if not raw:
        return None
    return {
        "wins": raw.get("won_overall", 0),
        "draws": raw.get("drawn_overall", 0),
        "losses": raw.get("lost_overall", 0),
        "played": raw.get("played_overall", 0),
        "gf": raw.get("scored_overall", 0),
        "ga": raw.get("conceded_overall", 0),
        "goals_avg": float(raw.get("scored_overall_avg") or 0),
        "conceded_avg": float(raw.get("conceded_overall_avg") or 0),
        "win_pct_home": raw.get("won_home_per", 0),
        "win_pct_away": raw.get("won_away_per", 0),
        "form5": [],
    }

def _parse(row: aiosqlite.Row, with_h2h: bool = False) -> dict:
    d = dict(row)
    d["status"] = _norm_status(d.get("status", "NS"))
    for key in ("home_stats", "away_stats"):
        if d.get(key):
            try:
                d[key] = _norm_stats(json.loads(d[key]))
            except Exception:
                d[key] = None
    if with_h2h:
        try:
            d["h2h"] = json.loads(d["h2h"]) if d.get("h2h") else []
        except Exception:
            d["h2h"] = []
    return d

@router.get("/fixtures")
async def list_fixtures(
    date: Annotated[str | None, Query()] = None,
    leagues: Annotated[str | None, Query()] = None,
    limit: Annotated[int | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
    db: aiosqlite.Connection = Depends(get_db),
):
    if not leagues:
        return {"fixtures": [], "total": 0, "cached_at": None}
    target = date or str(date_type.today())
    ids = [int(x) for x in leagues.split(",") if x.strip()]
    if not ids:
        return {"fixtures": [], "total": 0, "cached_at": None}
    ph = ",".join("?" * len(ids))
    params: list = [target] + ids
    extra = ""
    if status:
        extra += " AND f.status=?"
        params.append(status)
    lim = f"LIMIT {int(limit)}" if limit else ""
    sql = f"""
        SELECT f.*,
               s.odds_home, s.odds_draw, s.odds_away, s.drop_pct, s.drop_market
        FROM fixtures f
        LEFT JOIN (
            SELECT fixture_id, odds_home, odds_draw, odds_away, drop_pct, drop_market
            FROM odds_snapshots
            WHERE (fixture_id, recorded_at) IN (
                SELECT fixture_id, MAX(recorded_at) FROM odds_snapshots GROUP BY fixture_id
            )
        ) s ON f.id = s.fixture_id
        WHERE date(f.kickoff_utc)=? AND f.competition_id IN ({ph}) {extra}
        ORDER BY f.kickoff_utc {lim}
    """
    async with db.execute(sql, params) as cur:
        rows = await cur.fetchall()
    return {"fixtures": [_parse(r) for r in rows], "total": len(rows), "cached_at": None}

@router.get("/competitions")
async def list_competitions(db: aiosqlite.Connection = Depends(get_db)):
    async with db.execute(
        "SELECT DISTINCT competition_id as id, competition_name as name FROM fixtures ORDER BY competition_name"
    ) as cur:
        rows = await cur.fetchall()
    return {"competitions": [dict(r) for r in rows]}

@router.get("/fixtures/{fixture_id}")
async def get_fixture(fixture_id: int, db: aiosqlite.Connection = Depends(get_db)):
    async with db.execute("SELECT * FROM fixtures WHERE id=?", (fixture_id,)) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(404, "Fixture not found")
    fixture = _parse(row, with_h2h=True)
    h2h = fixture.pop("h2h", [])
    stats = {"home": fixture.get("home_stats"), "away": fixture.get("away_stats")}
    async with db.execute(
        "SELECT * FROM odds_snapshots WHERE fixture_id=? ORDER BY recorded_at", (fixture_id,)
    ) as cur:
        odds_history = [dict(r) for r in await cur.fetchall()]
    return {"fixture": fixture, "odds_history": odds_history, "h2h": h2h, "stats": stats}

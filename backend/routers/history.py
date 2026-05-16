import json
from typing import Annotated
from fastapi import APIRouter, Depends, Query
import aiosqlite
from database import get_db
from routers.fixtures import _norm_status, _norm_stats

router = APIRouter()

@router.get("/history")
async def list_history(
    limit: Annotated[int, Query()] = 50,
    offset: Annotated[int, Query()] = 0,
    league: Annotated[int | None, Query()] = None,
    db: aiosqlite.Connection = Depends(get_db),
):
    params: list = []
    clauses = ["f.status='ft'"]
    if league:
        clauses.append("f.competition_id=?")
        params.append(league)
    where = "WHERE " + " AND ".join(clauses)
    async with db.execute(f"SELECT COUNT(*) FROM fixtures f {where}", params) as cur:
        total = (await cur.fetchone())[0]
    sql = f"""
        SELECT f.*, s.odds_home, s.odds_draw, s.odds_away
        FROM fixtures f
        LEFT JOIN (
            SELECT fixture_id, odds_home, odds_draw, odds_away FROM odds_snapshots
            WHERE (fixture_id, recorded_at) IN (
                SELECT fixture_id, MAX(recorded_at) FROM odds_snapshots GROUP BY fixture_id
            )
        ) s ON f.id=s.fixture_id
        {where}
        ORDER BY f.kickoff_utc DESC LIMIT ? OFFSET ?
    """
    async with db.execute(sql, params + [limit, offset]) as cur:
        rows = await cur.fetchall()
    items = []
    for row in rows:
        d = dict(row)
        d["status"] = _norm_status(d.get("status", "NS"))
        for k in ("home_stats", "away_stats"):
            if d.get(k):
                try:
                    d[k] = _norm_stats(json.loads(d[k]))
                except Exception:
                    d[k] = None
        if d.get("h2h"):
            try:
                d["h2h"] = json.loads(d["h2h"])
            except Exception:
                d["h2h"] = []
        items.append(d)
    return {"items": items, "total": total}

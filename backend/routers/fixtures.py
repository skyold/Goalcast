import json
from datetime import date as date_type
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query
import aiosqlite
from database import get_db
from services.ah import derive_main_ah_line

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

def _pct(numer, denom):
    if not numer or not denom:
        return None
    return round(numer * 100 / denom, 2)

def _build_form(row: dict | None) -> dict | None:
    if not row or row.get("form5_str") is None:
        return None
    return {
        "form5": row.get("form5_str") or "",
        "won": row.get("won"), "drawn": row.get("drawn"), "lost": row.get("lost"),
        "gf": row.get("goals_for"), "ga": row.get("goals_against"),
    }

def _build_prediction_summary(p: dict | None) -> dict | None:
    if not p or not p.get("simulations"):
        return None
    s = p["simulations"]
    return {
        "home_win_pct": _pct(p["home_win"], s),
        "draw_pct":     _pct(p["draw"], s),
        "away_win_pct": _pct(p["away_win"], s),
        "btts_pct":     _pct(p["btts"], s),
        "o25_pct":      _pct(p["o25_goals"], s),
    }

def _format_ah_outcome(side: str, line: float) -> str:
    if line == 0:
        return f"{side}_0"
    sign = "m" if (side == "home" and line < 0) or (side == "away" and line > 0) else "p"
    abs_line = abs(line)
    # Convert to the OddAlerts string format: 0.5->'05', 0.75->'075', 1->'1', 1.5->'15', 1.25->'125'
    if abs_line == int(abs_line):
        digits = f"{int(abs_line)}"
    else:
        # quarter line: 0.25, 0.75, 1.25, 1.75
        if (abs_line * 4) == int(abs_line * 4) and (abs_line * 2) != int(abs_line * 2):
            digits = f"{int(abs_line * 100):03d}"
        else:
            # half line: 0.5, 1.5, 2.5
            digits = f"{int(abs_line * 10):02d}"
    return f"{side}_{sign}{digits}"

def _bookmaker_1x2(rows: list[dict], bk: int) -> dict | None:
    pick = {r["outcome"]: r for r in rows if r["market_id"] == 6 and r["bookmaker_id"] == bk}
    if not pick:
        return None
    def _v(o):
        r = pick.get(o)
        return float(r["current"]) if r and r["current"] is not None else None
    home = _v("home"); draw = _v("draw"); away = _v("away")
    if home is None or away is None:
        return None
    at = pick.get("home", {}).get("current_at") if isinstance(pick.get("home"), dict) else None
    return {"home": home, "draw": draw, "away": away, "current_at": at}

def _build_odds_summary(rows: list[dict]) -> dict | None:
    if not rows:
        return None
    ft = {"pinnacle": _bookmaker_1x2(rows, 1), "bet365": _bookmaker_1x2(rows, 2)}
    ah = None
    pin = derive_main_ah_line(rows, bookmaker_id=1)
    b365 = derive_main_ah_line(rows, bookmaker_id=2)
    if pin:
        line, ph, pa = pin
        ah = {
            "line": line,
            "pinnacle": {
                "home_outcome": _format_ah_outcome("home", line),
                "home_odds": ph,
                "away_outcome": _format_ah_outcome("away", -line),
                "away_odds": pa,
            },
            "bet365": ({"home_odds": b365[1], "away_odds": b365[2]}
                        if b365 and b365[0] == line else None),
        }
    if not ft["pinnacle"] and not ft["bet365"] and ah is None:
        return None
    return {"ft_result": ft, "asian_handicap": ah}

@router.get("/fixtures")
async def list_fixtures(
    date: Annotated[str | None, Query()] = None,
    leagues: Annotated[str | None, Query()] = None,
    predictability: Annotated[str | None, Query()] = None,
    min_drop: Annotated[float | None, Query()] = None,
    has_ai: Annotated[bool, Query()] = False,
    limit: Annotated[int, Query()] = 200,
    status: Annotated[str | None, Query()] = None,
    db: aiosqlite.Connection = Depends(get_db),
):
    target = date or str(date_type.today())
    sql = (
        "SELECT f.*, "
        "  hf.form5_str AS h_form5, hf.won AS h_won, hf.drawn AS h_drawn, hf.lost AS h_lost,"
        "  hf.goals_for AS h_gf, hf.goals_against AS h_ga,"
        "  af.form5_str AS a_form5, af.won AS a_won, af.drawn AS a_drawn, af.lost AS a_lost,"
        "  af.goals_for AS a_gf, af.goals_against AS a_ga,"
        "  p.simulations, p.home_win, p.draw, p.away_win, p.btts, p.o25_goals,"
        "  ds.drop_pct AS d_drop_pct, ds.drop_market AS d_drop_market"
        " FROM fixtures f"
        " LEFT JOIN team_form hf ON hf.team_id=f.home_team_id AND hf.season_id=f.season_id"
        " LEFT JOIN team_form af ON af.team_id=f.away_team_id AND af.season_id=f.season_id"
        " LEFT JOIN predictions p ON p.fixture_id=f.id"
        " LEFT JOIN ("
        "   SELECT fixture_id, drop_pct, drop_market FROM odds_snapshots"
        "   WHERE (fixture_id, recorded_at) IN ("
        "     SELECT fixture_id, MAX(recorded_at) FROM odds_snapshots GROUP BY fixture_id)"
        " ) ds ON ds.fixture_id=f.id"
        " WHERE date(f.kickoff_utc)=?"
    )
    params: list = [target]
    if leagues:
        ids = [int(x) for x in leagues.split(",") if x.strip()]
        if ids:
            sql += f" AND f.competition_id IN ({','.join('?'*len(ids))})"
            params.extend(ids)
    if predictability:
        levels = [s.strip() for s in predictability.split(",") if s.strip()]
        if levels:
            sql += f" AND f.predictability IN ({','.join('?'*len(levels))})"
            params.extend(levels)
    if has_ai:
        sql += " AND p.simulations IS NOT NULL AND p.simulations > 0"
    if min_drop is not None:
        sql += " AND ds.drop_pct <= ?"
        params.append(-abs(min_drop))
    if status:
        sql += " AND f.status=?"
        params.append(status)
    sql += f" ORDER BY f.kickoff_utc LIMIT {int(limit)}"

    async with db.execute(sql, params) as cur:
        rows = await cur.fetchall()

    fixtures = []
    for row in rows:
        d = _parse(row)
        async with db.execute(
            "SELECT * FROM bookmaker_odds WHERE fixture_id=?", (row["id"],)
        ) as ocur:
            odds_rows = [dict(r) for r in await ocur.fetchall()]
        home_form = _build_form({"form5_str": row["h_form5"], "won": row["h_won"],
                                   "drawn": row["h_drawn"], "lost": row["h_lost"],
                                   "goals_for": row["h_gf"], "goals_against": row["h_ga"]})
        away_form = _build_form({"form5_str": row["a_form5"], "won": row["a_won"],
                                   "drawn": row["a_drawn"], "lost": row["a_lost"],
                                   "goals_for": row["a_gf"], "goals_against": row["a_ga"]})
        d.update({
            "predictability": row["predictability"],
            "home_form": home_form, "away_form": away_form,
            "prediction_summary": _build_prediction_summary({
                "simulations": row["simulations"], "home_win": row["home_win"],
                "draw": row["draw"], "away_win": row["away_win"],
                "btts": row["btts"], "o25_goals": row["o25_goals"],
            }),
            "odds": _build_odds_summary(odds_rows),
            "drop_flag": ({"market_key": row["d_drop_market"],
                            "drop_percentage": abs(row["d_drop_pct"]) if row["d_drop_pct"] else 0}
                           if row["d_drop_pct"] is not None else None),
        })
        fixtures.append(d)
    return {"fixtures": fixtures, "total": len(fixtures), "cached_at": None}

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

import json
from datetime import date as date_type
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query
import aiosqlite
from database import get_db
from services.ah import derive_main_ah_line
from services.auth import get_current_user_optional, get_user_competition_prefs

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
    # Rename internal column home_position/away_position → home_rank/away_rank per the API contract.
    if "home_position" in d:
        d["home_rank"] = d.pop("home_position")
    if "away_position" in d:
        d["away_rank"] = d.pop("away_position")
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
    user: dict | None = Depends(get_current_user_optional),
):
    # Phase 3: logged-in users have a competition whitelist. Empty prefs => empty
    # results (forces the user to set prefs); non-empty => intersect with the
    # already-requested `leagues` filter (so chip drill-down still works).
    user_prefs = await get_user_competition_prefs(user, db)
    if user_prefs is not None and not user_prefs:
        return {"fixtures": [], "total": 0, "cached_at": None}
    target = date or str(date_type.today())
    select_cols = (
        "SELECT f.*, "
        "  hf.form5_str AS h_form5, hf.won AS h_won, hf.drawn AS h_drawn, hf.lost AS h_lost,"
        "  hf.goals_for AS h_gf, hf.goals_against AS h_ga,"
        "  af.form5_str AS a_form5, af.won AS a_won, af.drawn AS a_drawn, af.lost AS a_lost,"
        "  af.goals_for AS a_gf, af.goals_against AS a_ga,"
        "  p.simulations, p.home_win, p.draw, p.away_win, p.btts, p.o25_goals,"
        "  ds.drop_pct AS d_drop_pct, ds.drop_market AS d_drop_market,"
        "  th.short_code AS home_abbr, ta.short_code AS away_abbr,"
        "  th.name_zh AS home_team_zh, ta.name_zh AS away_team_zh,"
        "  c.name_zh AS competition_name_zh"
    )
    from_clause = (
        " FROM fixtures f"
        " LEFT JOIN team_form hf ON hf.team_id=f.home_team_id AND hf.season_id=f.season_id"
        " LEFT JOIN team_form af ON af.team_id=f.away_team_id AND af.season_id=f.season_id"
        " LEFT JOIN predictions p ON p.fixture_id=f.id"
        " LEFT JOIN teams th ON th.id=f.home_team_id"
        " LEFT JOIN teams ta ON ta.id=f.away_team_id"
        " LEFT JOIN competitions c ON c.id=f.competition_id"
        " LEFT JOIN ("
        "   SELECT fixture_id, drop_pct, drop_market FROM odds_snapshots"
        "   WHERE (fixture_id, recorded_at) IN ("
        "     SELECT fixture_id, MAX(recorded_at) FROM odds_snapshots GROUP BY fixture_id)"
        " ) ds ON ds.fixture_id=f.id"
        " WHERE date(f.kickoff_utc)=?"
    )
    params: list = [target]
    where_extra = ""
    if leagues:
        ids = [int(x) for x in leagues.split(",") if x.strip()]
        # Intersect with prefs whitelist (when logged in). If intersection is
        # empty, short-circuit before running the query.
        if user_prefs is not None:
            ids = [i for i in ids if i in user_prefs]
            if not ids:
                return {"fixtures": [], "total": 0, "cached_at": None}
        if ids:
            where_extra += f" AND f.competition_id IN ({','.join('?'*len(ids))})"
            params.extend(ids)
    elif user_prefs is not None:
        # No `leagues` query param but user is logged in: default to their prefs.
        pref_ids = sorted(user_prefs)
        where_extra += f" AND f.competition_id IN ({','.join('?'*len(pref_ids))})"
        params.extend(pref_ids)
    if predictability:
        levels = [s.strip() for s in predictability.split(",") if s.strip()]
        if levels:
            where_extra += f" AND f.predictability IN ({','.join('?'*len(levels))})"
            params.extend(levels)
    if has_ai:
        where_extra += " AND p.simulations IS NOT NULL AND p.simulations > 0"
    if min_drop is not None:
        where_extra += " AND ds.drop_pct <= ?"
        params.append(-abs(min_drop))
    if status:
        where_extra += " AND f.status=?"
        params.append(status)

    base_query = select_cols + from_clause + where_extra
    paged_query = base_query + f" ORDER BY f.kickoff_utc LIMIT {int(limit)}"
    count_query = (
        "SELECT COUNT(*) FROM fixtures f"
        + from_clause.split("FROM fixtures f", 1)[1]
        + where_extra
    )

    async with db.execute(paged_query, params) as cur:
        rows = await cur.fetchall()

    # Batch-fetch bookmaker_odds for all returned fixtures in ONE query, then group in Python.
    # Replaces previous per-row subquery (N+1) with one IN-list query.
    fixture_ids = [row["id"] for row in rows]
    odds_by_fixture: dict[int, list[dict]] = {}
    if fixture_ids:
        ph = ",".join("?" * len(fixture_ids))
        async with db.execute(
            f"SELECT * FROM bookmaker_odds WHERE fixture_id IN ({ph})",
            fixture_ids,
        ) as ocur:
            for r in await ocur.fetchall():
                d = dict(r)
                odds_by_fixture.setdefault(d["fixture_id"], []).append(d)

    fixtures = []
    for row in rows:
        d = _parse(row)
        odds_rows = odds_by_fixture.get(row["id"], [])
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

    async with db.execute(count_query, params) as ccur:
        total_row = await ccur.fetchone()
    total = total_row[0] if total_row else len(fixtures)

    return {"fixtures": fixtures, "total": total, "cached_at": None}

@router.get("/fixtures/{fixture_id}/odds-timeseries")
async def odds_timeseries(
    fixture_id: int,
    window: Annotated[str, Query(pattern="^(24h|7d)$")] = "24h",
    bookmaker: Annotated[str | None, Query()] = "Pinnacle",
    market: Annotated[str | None, Query()] = "all",
    db: aiosqlite.Connection = Depends(get_db),
):
    """Phase 1 — drop_pct time series for a fixture.

    `odds_snapshots.odds_home/draw/away` columns exist but are 100% NULL in
    practice (the sync only writes drop_pct). So this endpoint returns a
    single-series line of drop_pct over time. Default narrows to Pinnacle (sharp)
    on the 1x2 market; pass ?bookmaker=all and ?market=all to widen.
    """
    from datetime import datetime, timedelta, timezone

    hours = 24 if window == "24h" else 168
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

    clauses = ["fixture_id=?", "recorded_at >= ?", "drop_pct IS NOT NULL"]
    params: list = [fixture_id, cutoff]
    if bookmaker and bookmaker != "all":
        clauses.append("bookmaker=?")
        params.append(bookmaker)
    if market and market != "all":
        clauses.append("market=?")
        params.append(market)

    where = " AND ".join(clauses)
    async with db.execute(
        f"SELECT recorded_at, drop_pct, bookmaker, market FROM odds_snapshots "
        f"WHERE {where} ORDER BY recorded_at",
        params,
    ) as cur:
        rows = [dict(r) for r in await cur.fetchall()]

    # Downsample to ≤ 50 points: bucket by even time slices and take the
    # min drop_pct per bucket (most extreme = most informative).
    MAX_POINTS = 50
    if len(rows) > MAX_POINTS:
        rows = _downsample_by_time(rows, MAX_POINTS)

    return {
        "fixture_id": fixture_id,
        "window": window,
        "bookmaker": bookmaker,
        "market": market,
        "points": rows,
    }


def _downsample_by_time(rows: list[dict], max_points: int) -> list[dict]:
    if len(rows) <= max_points:
        return rows
    from datetime import datetime

    t0 = datetime.fromisoformat(rows[0]["recorded_at"])
    t1 = datetime.fromisoformat(rows[-1]["recorded_at"])
    span = (t1 - t0).total_seconds() or 1.0
    bucket_size = span / max_points

    buckets: dict[int, list[dict]] = {}
    for r in rows:
        t = datetime.fromisoformat(r["recorded_at"])
        idx = min(int((t - t0).total_seconds() / bucket_size), max_points - 1)
        buckets.setdefault(idx, []).append(r)

    out: list[dict] = []
    for idx in sorted(buckets):
        bucket = buckets[idx]
        # Pick the row with the most extreme (smallest = most negative) drop_pct.
        pick = min(bucket, key=lambda r: r["drop_pct"])
        out.append(pick)
    return out


@router.get("/competitions")
async def list_competitions(db: aiosqlite.Connection = Depends(get_db)):
    # Pull every competition referenced by fixtures and join with the curated
    # `competitions` table so the response carries `name_zh` for top leagues.
    async with db.execute(
        """SELECT f.competition_id AS id,
                  f.competition_name AS name,
                  c.name_zh AS name_zh
           FROM fixtures f
           LEFT JOIN competitions c ON c.id = f.competition_id
           GROUP BY f.competition_id, f.competition_name, c.name_zh
           ORDER BY (c.name_zh IS NULL), COALESCE(c.name_zh, f.competition_name)"""
    ) as cur:
        rows = await cur.fetchall()
    return {"competitions": [dict(r) for r in rows]}

def _bookmaker_1x2_detail(rows: list[dict], bk: int) -> dict | None:
    pick = {r["outcome"]: r for r in rows if r["market_id"] == 6 and r["bookmaker_id"] == bk}
    if not pick:
        return None
    def _entry(o):
        r = pick.get(o)
        if not r:
            return None
        return {
            "current": float(r["current"]) if r["current"] is not None else None,
            "opening": float(r["opening"]) if r["opening"] is not None else None,
            "current_at": r["current_at"],
        }
    return {"home": _entry("home"), "draw": _entry("draw"), "away": _entry("away")}

def _all_ah_lines(rows: list[dict]) -> list[dict]:
    from services.ah import parse_ah_outcome_line
    by_bm: dict[int, dict[float, dict[str, dict]]] = {}
    for r in rows:
        if r["market_id"] != 51:
            continue
        parsed = parse_ah_outcome_line(r["outcome"])
        if not parsed:
            continue
        side, line = parsed
        home_line = line if side == "home" else -line
        b = by_bm.setdefault(r["bookmaker_id"], {}).setdefault(home_line, {})
        b[side] = {
            "current": float(r["current"]) if r["current"] is not None else None,
            "opening": float(r["opening"]) if r["opening"] is not None else None,
        }
    all_lines = sorted(set().union(*(b.keys() for b in by_bm.values())) if by_bm else [])
    out = []
    for ln in all_lines:
        item = {"line": ln}
        for bk_name, bk_id in (("pinnacle", 1), ("bet365", 2)):
            d = by_bm.get(bk_id, {}).get(ln, {})
            home, away = d.get("home", {}), d.get("away", {})
            if home or away:
                item[bk_name] = {
                    "home": home.get("current"), "away": away.get("current"),
                    "opening_home": home.get("opening"), "opening_away": away.get("opening"),
                }
            else:
                item[bk_name] = None
        out.append(item)
    return out

def _build_detail_odds(rows: list[dict]) -> dict | None:
    if not rows:
        return None
    ft = {"pinnacle": _bookmaker_1x2_detail(rows, 1), "bet365": _bookmaker_1x2_detail(rows, 2)}
    return {"ft_result": ft, "asian_handicap_lines": _all_ah_lines(rows)}

@router.get("/fixtures/{fixture_id}")
async def get_fixture(fixture_id: int, db: aiosqlite.Connection = Depends(get_db)):
    async with db.execute(
        """SELECT f.*,
                  th.name_zh AS home_team_zh,
                  ta.name_zh AS away_team_zh,
                  c.name_zh  AS competition_name_zh
           FROM fixtures f
           LEFT JOIN teams th ON th.id = f.home_team_id
           LEFT JOIN teams ta ON ta.id = f.away_team_id
           LEFT JOIN competitions c ON c.id = f.competition_id
           WHERE f.id=?""",
        (fixture_id,),
    ) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(404, "Fixture not found")
    fixture = _parse(row, with_h2h=False)
    fixture["predictability"] = row["predictability"]

    async with db.execute("SELECT * FROM predictions WHERE fixture_id=?", (fixture_id,)) as cur:
        p = await cur.fetchone()
    prediction = None
    if p and p["simulations"]:
        s = p["simulations"]
        prediction = {
            "simulations": s,
            "home_win_pct": _pct(p["home_win"], s),
            "draw_pct":     _pct(p["draw"], s),
            "away_win_pct": _pct(p["away_win"], s),
            "btts_pct":     _pct(p["btts"], s),
            "o25_pct":      _pct(p["o25_goals"], s),
            "o35_pct":      _pct(p["o35_goals"], s),
            "scorelines":   json.loads(p["scorelines"] or "{}"),
            "updated_at":   p["updated_at"],
        }

    async with db.execute("SELECT * FROM bookmaker_odds WHERE fixture_id=?", (fixture_id,)) as cur:
        odds_rows = [dict(r) for r in await cur.fetchall()]
    odds = _build_detail_odds(odds_rows)

    async with db.execute(
        """SELECT tf.* FROM fixtures f
           LEFT JOIN team_form tf ON tf.team_id=f.home_team_id AND tf.season_id=f.season_id
           WHERE f.id=?""", (fixture_id,)) as cur:
        hf_row = await cur.fetchone()
    async with db.execute(
        """SELECT tf.* FROM fixtures f
           LEFT JOIN team_form tf ON tf.team_id=f.away_team_id AND tf.season_id=f.season_id
           WHERE f.id=?""", (fixture_id,)) as cur:
        af_row = await cur.fetchone()
    home_form = _build_form(dict(hf_row) if hf_row else None)
    away_form = _build_form(dict(af_row) if af_row else None)

    home_team_obj = {"id": row["home_team_id"], "name": row["home_team"],
                       "stats": fixture.get("home_stats"), "form": home_form}
    away_team_obj = {"id": row["away_team_id"], "name": row["away_team"],
                       "stats": fixture.get("away_stats"), "form": away_form}

    async with db.execute(
        """SELECT market AS market_key, drop_market, drop_pct,
                  odds_home, odds_draw, odds_away, bookmaker, recorded_at
           FROM odds_snapshots
           WHERE fixture_id=?
           ORDER BY recorded_at DESC LIMIT 50""",
        (fixture_id,)) as cur:
        drops = [dict(r) for r in await cur.fetchall()]

    # 注意：键名用 *_obj 后缀以免与 fixture 内的字符串字段 home_team / away_team 冲突
    return {"fixture": fixture, "home_team_obj": home_team_obj, "away_team_obj": away_team_obj,
            "prediction": prediction, "odds": odds, "dropping_records": drops}

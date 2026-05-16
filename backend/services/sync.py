import json
from datetime import datetime, timezone
import aiosqlite
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database import _db_path
from services.oddalerts import oddalerts_client

scheduler = AsyncIOScheduler()

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _from_unix(ts: int | None) -> str:
    if not ts:
        return ""
    return datetime.fromtimestamp(ts, timezone.utc).isoformat()

async def _log(db: aiosqlite.Connection, sync_type: str, status: str,
               records: int = 0, error_msg: str | None = None, started_at: str = "") -> None:
    await db.execute(
        "INSERT INTO sync_log (sync_type,status,records,error_msg,started_at,finished_at) VALUES(?,?,?,?,?,?)",
        (sync_type, status, records, error_msg, started_at, _now()),
    )

async def sync_dropping_odds() -> None:
    started = _now()
    async with aiosqlite.connect(_db_path()) as db:
        try:
            items = await oddalerts_client.get_dropping_odds()
            count = 0
            for item in items:
                fid = item.get("fixture_id")
                if not fid:
                    continue
                raw_drop = item.get("drop_percentage")
                drop_pct = -float(raw_drop) if raw_drop else None
                await db.execute(
                    """INSERT INTO odds_snapshots
                       (fixture_id,market,bookmaker,odds_home,odds_draw,odds_away,drop_pct,drop_market,recorded_at)
                       VALUES(?,?,?,?,?,?,?,?,?)""",
                    (fid, item.get("market_key", "1x2"), item.get("bookmaker_name", "unknown"),
                     None, None, None,
                     drop_pct, item.get("market_key"), _now()),
                )
                count += 1
            await db.commit()
            await _log(db, "dropping", "ok", count, started_at=started)
            await db.commit()
        except Exception as exc:
            await _log(db, "dropping", "error", error_msg=str(exc), started_at=started)
            await db.commit()

async def sync_from_trends() -> None:
    """Populate fixtures table from trends data (primary fixture source).

    Trends returns 250 upcoming fixtures per type, each with embedded home/away stats.
    This replaces the empty /fixtures/id endpoint as the fixture discovery mechanism.
    """
    started = _now()
    async with aiosqlite.connect(_db_path()) as db:
        try:
            trend_cols = {
                "homeWin": "trend_home_win",
                "awayWin": "trend_away_win",
                "btts": "trend_btts",
            }
            now = _now()
            upserted = 0

            for trend_type, col in trend_cols.items():
                items = await oddalerts_client.get_trends(trend_type)
                for item in items:
                    fid = item.get("id")
                    if not fid:
                        continue
                    kickoff = _from_unix(item.get("unix"))
                    home_stats = json.dumps(item.get("stats", {}).get("home", {}))
                    away_stats = json.dumps(item.get("stats", {}).get("away", {}))

                    await db.execute(
                        """INSERT OR IGNORE INTO fixtures
                           (id,competition_id,competition_name,home_team,away_team,
                            kickoff_utc,status,home_stats,away_stats,h2h,fetched_at,updated_at)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (fid,
                         item.get("competition_id", 0),
                         item.get("competition_name", ""),
                         item.get("home_name", ""),
                         item.get("away_name", ""),
                         kickoff, "NS",
                         home_stats, away_stats, "[]",
                         now, now),
                    )
                    upserted += 1

                    await db.execute(
                        f"UPDATE fixtures SET {col}=1, updated_at=? WHERE id=?",
                        (now, fid),
                    )

            await db.commit()
            await _log(db, "fixture_trends", "ok", upserted, started_at=started)
            await db.commit()
        except Exception as exc:
            await _log(db, "fixture_trends", "error", error_msg=str(exc), started_at=started)
            await db.commit()

async def sync_fixtures_upcoming() -> None:
    started = _now()
    async with aiosqlite.connect(_db_path()) as db:
        try:
            page = 1
            upserted = 0
            while True:
                items = await oddalerts_client.get_upcoming_fixtures(page=page, per_page=250)
                if not items:
                    break
                now = _now()
                for it in items:
                    fid = it.get("id")
                    if not fid:
                        continue
                    kickoff = _from_unix(it.get("unix"))
                    await db.execute(
                        """INSERT INTO fixtures
                           (id,competition_id,competition_name,home_team,away_team,
                            home_team_id,away_team_id,season_id,kickoff_utc,status,
                            predictability,fetched_at,updated_at)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
                           ON CONFLICT(id) DO UPDATE SET
                             kickoff_utc=excluded.kickoff_utc,
                             status=excluded.status,
                             predictability=excluded.predictability,
                             home_team_id=excluded.home_team_id,
                             away_team_id=excluded.away_team_id,
                             season_id=excluded.season_id,
                             updated_at=excluded.updated_at""",
                        (fid,
                         it.get("competition_id", 0),
                         it.get("competition_name", ""),
                         it.get("home_name", ""),
                         it.get("away_name", ""),
                         it.get("home_id"), it.get("away_id"),
                         it.get("season_id"),
                         kickoff, it.get("status", "NS"),
                         it.get("competition_predictability"),
                         now, now),
                    )
                    upserted += 1
                page += 1
                if len(items) < 250:
                    break
            await db.commit()
            await _log(db, "fixtures_upcoming", "ok", upserted, started_at=started)
            await db.commit()
        except Exception as exc:
            await _log(db, "fixtures_upcoming", "error", error_msg=str(exc), started_at=started)
            await db.commit()


def _build_form5(raw: dict) -> str:
    """Prefer API-provided form string; fallback to empty."""
    s = raw.get("form_overall") or raw.get("form") or ""
    if isinstance(s, str) and s:
        return s[:5].upper()
    return ""

async def sync_team_form(season_ids: list[int] | None = None) -> None:
    started = _now()
    async with aiosqlite.connect(_db_path()) as db:
        try:
            if season_ids is None:
                cur = await db.execute(
                    """SELECT DISTINCT season_id FROM fixtures
                       WHERE kickoff_utc >= datetime('now') AND season_id IS NOT NULL"""
                )
                season_ids = [int(r[0]) for r in await cur.fetchall()]
            now = _now()
            count = 0
            for sid in season_ids:
                rows = await oddalerts_client.get_season_stats_last_x(sid, n=5)
                for r in rows:
                    tid = r.get("team_id")
                    if not tid:
                        continue
                    played = (r.get("played") or {}).get("total")
                    won = (r.get("won") or {}).get("total")
                    drawn = (r.get("drawn") or {}).get("total")
                    lost = (r.get("lost") or {}).get("total")
                    gf = (r.get("goals_for") or {}).get("total")
                    ga = (r.get("goals_against") or {}).get("total")
                    g_avg = (r.get("goals_total") or {}).get("total_avg")
                    await db.execute(
                        """INSERT INTO team_form
                           (team_id,season_id,form5_str,played,won,drawn,lost,
                            goals_for,goals_against,goals_avg,updated_at)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?)
                           ON CONFLICT(team_id, season_id) DO UPDATE SET
                             form5_str=excluded.form5_str, played=excluded.played,
                             won=excluded.won, drawn=excluded.drawn, lost=excluded.lost,
                             goals_for=excluded.goals_for, goals_against=excluded.goals_against,
                             goals_avg=excluded.goals_avg, updated_at=excluded.updated_at""",
                        (tid, sid, _build_form5(r), played, won, drawn, lost,
                         gf, ga, g_avg, now),
                    )
                    count += 1
            await db.commit()
            await _log(db, "team_form", "ok", count, started_at=started)
            await db.commit()
        except Exception as exc:
            await _log(db, "team_form", "error", error_msg=str(exc), started_at=started)
            await db.commit()


async def full_sync() -> None:
    await sync_from_trends()
    await sync_dropping_odds()

scheduler.add_job(sync_dropping_odds, "interval", minutes=5, id="dropping")
scheduler.add_job(sync_from_trends, "interval", hours=1, id="fixture_trends")

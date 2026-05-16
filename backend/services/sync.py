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

async def full_sync() -> None:
    await sync_from_trends()
    await sync_dropping_odds()

scheduler.add_job(sync_dropping_odds, "interval", minutes=5, id="dropping")
scheduler.add_job(sync_from_trends, "interval", hours=1, id="fixture_trends")

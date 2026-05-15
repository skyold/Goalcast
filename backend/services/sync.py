import json
from datetime import datetime, timezone
import aiosqlite
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database import _db_path
from services.oddalerts import oddalerts_client

scheduler = AsyncIOScheduler()

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

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
                await db.execute(
                    """INSERT INTO odds_snapshots
                       (fixture_id,market,bookmaker,odds_home,odds_draw,odds_away,drop_pct,drop_market,recorded_at)
                       VALUES(?,?,?,?,?,?,?,?,?)""",
                    (fid, item.get("market", "1x2"), item.get("bookmaker", "unknown"),
                     item.get("odds_home"), item.get("odds_draw"), item.get("odds_away"),
                     item.get("drop_pct"), item.get("drop_market"), _now()),
                )
                count += 1
            await db.commit()
            await _log(db, "dropping", "ok", count, started_at=started)
            await db.commit()
        except Exception as exc:
            await _log(db, "dropping", "error", error_msg=str(exc), started_at=started)
            await db.commit()

async def sync_trends() -> None:
    started = _now()
    async with aiosqlite.connect(_db_path()) as db:
        try:
            count = 0
            col_map = {"homeWin": "trend_home_win", "awayWin": "trend_away_win", "btts": "trend_btts"}
            for trend_type, col in col_map.items():
                for item in await oddalerts_client.get_trends(trend_type):
                    fid = item.get("fixture_id")
                    if fid:
                        await db.execute(f"UPDATE fixtures SET {col}=1,updated_at=? WHERE id=?", (_now(), fid))
                        count += 1
            await db.commit()
            await _log(db, "trends", "ok", count, started_at=started)
            await db.commit()
        except Exception as exc:
            await _log(db, "trends", "error", error_msg=str(exc), started_at=started)
            await db.commit()

async def sync_fixture_ids() -> None:
    started = _now()
    async with aiosqlite.connect(_db_path()) as db:
        try:
            ids = await oddalerts_client.get_fixture_ids()
            count = 0
            for fid in ids:
                async with db.execute("SELECT id FROM fixtures WHERE id=?", (fid,)) as cur:
                    if await cur.fetchone():
                        continue
                detail = await oddalerts_client.get_fixture_detail(fid)
                if not detail:
                    continue
                stats = await oddalerts_client.get_stats(fid)
                preds = detail.get("predictions", {})
                now = _now()
                await db.execute(
                    """INSERT OR IGNORE INTO fixtures
                       (id,competition_id,competition_name,home_team,away_team,home_team_id,away_team_id,
                        kickoff_utc,status,prob_home_win,prob_draw,prob_away_win,
                        home_stats,away_stats,h2h,fetched_at,updated_at)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (fid,
                     detail.get("competition_id", 0), detail.get("competition_name", ""),
                     detail.get("home_team", ""), detail.get("away_team", ""),
                     detail.get("home_team_id"), detail.get("away_team_id"),
                     detail.get("kickoff_utc", ""), detail.get("status", "pre"),
                     preds.get("prob_home_win"), preds.get("prob_draw"), preds.get("prob_away_win"),
                     json.dumps(stats.get("home", {})), json.dumps(stats.get("away", {})),
                     json.dumps(detail.get("h2h", [])), now, now),
                )
                count += 1
            await db.commit()
            await _log(db, "fixture_detail", "ok", count, started_at=started)
            await db.commit()
        except Exception as exc:
            await _log(db, "fixture_detail", "error", error_msg=str(exc), started_at=started)
            await db.commit()

async def full_sync() -> None:
    await sync_fixture_ids()
    await sync_dropping_odds()
    await sync_trends()

scheduler.add_job(sync_dropping_odds, "interval", minutes=5, id="dropping")
scheduler.add_job(sync_trends, "interval", minutes=5, id="trends")
scheduler.add_job(sync_fixture_ids, "interval", hours=1, id="fixture_ids")

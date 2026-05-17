import asyncio
import json
from datetime import datetime, timezone
import aiosqlite
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database import _db_path
from services.oddalerts import oddalerts_client

scheduler = AsyncIOScheduler()

# Concurrency cap for OddAlerts HTTP calls inside sync jobs.
# OddAlerts publishes no rate limit; 5 is a conservative starting value that
# yielded no 429s in local backfill testing. Raise if quota allows.
OA_CONCURRENCY = 5

async def _gather_throttled(coros: list, concurrency: int = OA_CONCURRENCY) -> list:
    """Run awaitables concurrently capped by a semaphore. Returns results in input order,
    with exceptions returned in place (callers MUST inspect for Exception instances)."""
    if not coros:
        return []
    sem = asyncio.Semaphore(concurrency)
    async def _bound(c):
        async with sem:
            return await c
    return await asyncio.gather(*[_bound(c) for c in coros], return_exceptions=True)

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
    new_fids: list[int] = []
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
                            predictability,home_position,away_position,fetched_at,updated_at)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                           ON CONFLICT(id) DO UPDATE SET
                             kickoff_utc=excluded.kickoff_utc,
                             status=excluded.status,
                             predictability=excluded.predictability,
                             home_team_id=excluded.home_team_id,
                             away_team_id=excluded.away_team_id,
                             season_id=excluded.season_id,
                             home_position=excluded.home_position,
                             away_position=excluded.away_position,
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
                         it.get("home_position"), it.get("away_position"),
                         now, now),
                    )
                    upserted += 1
                page += 1
                if len(items) < 250:
                    break
            await db.commit()
            await _log(db, "fixtures_upcoming", "ok", upserted, started_at=started)
            await db.commit()
            # chain: collect new fixture IDs that have no bookmaker_odds yet
            cur = await db.execute(
                """SELECT f.id FROM fixtures f
                   LEFT JOIN bookmaker_odds bo ON bo.fixture_id=f.id
                   WHERE f.kickoff_utc >= strftime('%Y-%m-%dT%H:%M:%S','now') AND bo.fixture_id IS NULL
                   LIMIT 200"""
            )
            new_fids = [int(r[0]) for r in await cur.fetchall()]
        except Exception as exc:
            await _log(db, "fixtures_upcoming", "error", error_msg=str(exc), started_at=started)
            await db.commit()
    # outside the `with` block — fresh connection used by sync_ah_odds_seed
    if new_fids:
        await sync_ah_odds_seed(fixture_ids=new_fids)


async def _derive_form5(db: aiosqlite.Connection, team_id: int) -> str:
    """Derive a 5-char W/D/L string from local fixtures (status='FT') involving team_id.

    Convention: most recent match at the END of the string (e.g. 'LWDWW' = oldest...newest).
    Returns empty string if there are no finished fixtures for this team yet.
    """
    cur = await db.execute(
        """SELECT home_team_id, winning_team, score_home, score_away
           FROM fixtures
           WHERE status='FT'
             AND (home_team_id = ? OR away_team_id = ?)
             AND score_home IS NOT NULL AND score_away IS NOT NULL
           ORDER BY kickoff_utc DESC
           LIMIT 5""",
        (team_id, team_id),
    )
    rows = await cur.fetchall()  # DESC: most recent first
    out: list[str] = []
    for r in rows:
        _h, win, sh, sa = r[0], r[1], r[2], r[3]
        if sh == sa:
            out.append("D")
        elif win == team_id:
            out.append("W")
        else:
            out.append("L")
    # reverse so the most-recent match is at the end (matches design-mock convention).
    return "".join(reversed(out))


async def sync_team_form(season_ids: list[int] | None = None) -> None:
    """Keep aggregated W/D/L counts from /stats/season AND derive the 5-char form5
    string locally from the fixtures table (which sync_historical_fixtures populates)."""
    started = _now()
    async with aiosqlite.connect(_db_path()) as db:
        try:
            if season_ids is None:
                cur = await db.execute(
                    """SELECT DISTINCT season_id FROM fixtures
                       WHERE kickoff_utc >= strftime('%Y-%m-%dT%H:%M:%S', 'now') AND season_id IS NOT NULL"""
                )
                season_ids = [int(r[0]) for r in await cur.fetchall()]
            now = _now()
            count = 0
            failed_seasons = 0
            results = await _gather_throttled(
                [oddalerts_client.get_season_stats_last_x(sid, n=5) for sid in season_ids]
            )
            for sid, rows in zip(season_ids, results):
                if isinstance(rows, Exception):
                    failed_seasons += 1
                    continue
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
                    form5 = await _derive_form5(db, int(tid))
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
                        (tid, sid, form5, played, won, drawn, lost,
                         gf, ga, g_avg, now),
                    )
                    count += 1
            await db.commit()
            await _log(db, "team_form", "ok", count, started_at=started)
            await db.commit()
        except Exception as exc:
            await _log(db, "team_form", "error", error_msg=str(exc), started_at=started)
            await db.commit()


async def sync_competitions() -> None:
    """Refresh competitions table from upstream. Preserves manually-curated name_zh."""
    started = _now()
    async with aiosqlite.connect(_db_path()) as db:
        try:
            page = 1
            upserted = 0
            now = _now()
            while True:
                items = await oddalerts_client.get_competitions(page=page, per_page=250)
                if not items:
                    break
                for it in items:
                    cid = it.get("id")
                    name = it.get("name")
                    if not cid or not name:
                        continue
                    await db.execute(
                        """INSERT INTO competitions (id, name_en, name_zh, country, last_synced_at)
                           VALUES(?,?,?,?,?)
                           ON CONFLICT(id) DO UPDATE SET
                             name_en=excluded.name_en,
                             country=COALESCE(excluded.country, competitions.country),
                             last_synced_at=excluded.last_synced_at""",
                        (cid, name, None, it.get("country"), now),
                    )
                    upserted += 1
                page += 1
                if len(items) < 250:
                    break
            await db.commit()
            await _log(db, "competitions", "ok", upserted, started_at=started)
            await db.commit()
        except Exception as exc:
            await _log(db, "competitions", "error", error_msg=str(exc), started_at=started)
            await db.commit()


async def sync_teams_meta(team_ids: list[int] | None = None, ttl_days: int = 7) -> None:
    """Fetch /teams/find/:ID for team_ids referenced by fixtures.
    Skips teams synced within ttl_days. Preserves curated name_zh."""
    started = _now()
    async with aiosqlite.connect(_db_path()) as db:
        try:
            if team_ids is None:
                cur = await db.execute(
                    f"""SELECT DISTINCT tid FROM (
                          SELECT home_team_id AS tid FROM fixtures WHERE home_team_id IS NOT NULL
                          UNION
                          SELECT away_team_id AS tid FROM fixtures WHERE away_team_id IS NOT NULL
                        )
                        WHERE tid NOT IN (
                          SELECT id FROM teams
                          WHERE last_synced_at IS NOT NULL
                            AND last_synced_at > datetime('now', '-{int(ttl_days)} days')
                        )"""
                )
                team_ids = [int(r[0]) for r in await cur.fetchall()]
            if not team_ids:
                await _log(db, "teams_meta", "ok", 0, started_at=started)
                await db.commit()
                return
            results = await _gather_throttled(
                [oddalerts_client.get_team_find(tid) for tid in team_ids]
            )
            now = _now()
            count = 0
            skipped = 0
            for tid, r in zip(team_ids, results):
                if isinstance(r, Exception) or r is None:
                    skipped += 1
                    continue
                await db.execute(
                    """INSERT INTO teams (id, name, name_zh, short_code, country, last_synced_at)
                       VALUES(?,?,?,?,?,?)
                       ON CONFLICT(id) DO UPDATE SET
                         name=excluded.name,
                         short_code=COALESCE(excluded.short_code, teams.short_code),
                         country=COALESCE(excluded.country, teams.country),
                         last_synced_at=excluded.last_synced_at""",
                    (tid, r.get("name", ""), None, r.get("short_code"),
                     r.get("country"), now),
                )
                count += 1
            await db.commit()
            await _log(db, "teams_meta", "ok", count, started_at=started)
            await db.commit()
        except Exception as exc:
            await _log(db, "teams_meta", "error", error_msg=str(exc), started_at=started)
            await db.commit()


async def sync_historical_fixtures(days: int = 60) -> None:
    """Fetch finished fixtures from the past `days` days via /fixtures/between.
    Used to populate form5 (W/D/L sequence) without extra per-team calls.

    Resilience: a single page that times out / 5xx is logged and skipped instead
    of killing the whole job. PAGE_CAP prevents runaway loops; consecutive failure
    threshold avoids hammering a degraded upstream.
    """
    import time as _time
    started = _now()
    now_ts = int(_time.time())
    from_ts = now_ts - days * 86400
    async with aiosqlite.connect(_db_path()) as db:
        try:
            page = 1
            upserted = 0
            failed_pages = 0
            consecutive_fails = 0
            now = _now()
            PAGE_CAP = 200
            while page <= PAGE_CAP:
                try:
                    items = await oddalerts_client.get_fixtures_between(
                        ts_from=from_ts, ts_to=now_ts, page=page, per_page=250
                    )
                    consecutive_fails = 0
                except Exception:
                    failed_pages += 1
                    consecutive_fails += 1
                    page += 1
                    if consecutive_fails >= 5:
                        break
                    continue
                if not items:
                    break
                for it in items:
                    fid = it.get("id")
                    status = (it.get("status") or "").upper()
                    if not fid or status != "FT":
                        continue
                    kickoff = _from_unix(it.get("unix"))
                    await db.execute(
                        """INSERT INTO fixtures
                           (id,competition_id,competition_name,home_team,away_team,
                            home_team_id,away_team_id,season_id,kickoff_utc,status,
                            score_home,score_away,winning_team,
                            home_position,away_position,
                            predictability,fetched_at,updated_at)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                           ON CONFLICT(id) DO UPDATE SET
                             status=excluded.status,
                             score_home=excluded.score_home,
                             score_away=excluded.score_away,
                             winning_team=excluded.winning_team,
                             home_position=COALESCE(excluded.home_position, fixtures.home_position),
                             away_position=COALESCE(excluded.away_position, fixtures.away_position),
                             updated_at=excluded.updated_at""",
                        (fid,
                         it.get("competition_id", 0),
                         it.get("competition_name", ""),
                         it.get("home_name", ""),
                         it.get("away_name", ""),
                         it.get("home_id"), it.get("away_id"),
                         it.get("season_id"),
                         kickoff, status,
                         it.get("home_goals"), it.get("away_goals"),
                         it.get("winning_team"),
                         it.get("home_position"), it.get("away_position"),
                         it.get("competition_predictability"),
                         now, now),
                    )
                    upserted += 1
                page += 1
                if len(items) < 250:
                    break
            await db.commit()
            await _log(db, "historical_fixtures", "ok", upserted, started_at=started)
            await db.commit()
        except Exception as exc:
            await _log(db, "historical_fixtures", "error", error_msg=str(exc), started_at=started)
            await db.commit()


TARGET_BOOKMAKERS = {1, 2}    # Pinnacle, Bet365
TARGET_MARKETS = {6, 51}      # ft_result, asian_handicap

async def sync_ah_odds_seed(fixture_ids: list[int] | None = None) -> None:
    started = _now()
    async with aiosqlite.connect(_db_path()) as db:
        try:
            if fixture_ids is None:
                cur = await db.execute(
                    """SELECT f.id FROM fixtures f
                       LEFT JOIN bookmaker_odds bo ON bo.fixture_id=f.id
                       WHERE f.kickoff_utc >= strftime('%Y-%m-%dT%H:%M:%S','now') AND bo.fixture_id IS NULL"""
                )
                fixture_ids = [int(r[0]) for r in await cur.fetchall()]
            now = _now()
            count = 0
            failed_fixtures = 0
            # Fan out per-fixture odds-history fetches concurrently.
            results = await _gather_throttled(
                [oddalerts_client.get_odds_history_by_path(fid) for fid in fixture_ids]
            )
            for fid, rows in zip(fixture_ids, results):
                if isinstance(rows, Exception):
                    failed_fixtures += 1
                    continue
                for r in rows:
                    bk = r.get("bookmaker_id"); mk = r.get("market_id")
                    if bk not in TARGET_BOOKMAKERS or mk not in TARGET_MARKETS:
                        continue
                    opening = float(r["opening"]) if r.get("opening") else None
                    closing = float(r["closing"]) if r.get("closing") else None
                    peak = float(r["peak"]) if r.get("peak") else None
                    await db.execute(
                        """INSERT INTO bookmaker_odds
                           (fixture_id,bookmaker_id,market_id,outcome,
                            opening,current,peak,opening_at,current_at)
                           VALUES(?,?,?,?,?,?,?,?,?)
                           ON CONFLICT(fixture_id,bookmaker_id,market_id,outcome) DO UPDATE SET
                             opening=COALESCE(bookmaker_odds.opening, excluded.opening),
                             current=excluded.current,
                             peak=MAX(IFNULL(bookmaker_odds.peak,0), IFNULL(excluded.peak,0)),
                             opening_at=COALESCE(bookmaker_odds.opening_at, excluded.opening_at),
                             current_at=excluded.current_at""",
                        (fid, bk, mk, r.get("outcome", ""),
                         opening, closing, peak, now, now),
                    )
                    count += 1
            await db.commit()
            await _log(db, "ah_odds_seed", "ok", count, started_at=started)
            await db.commit()
        except Exception as exc:
            await _log(db, "ah_odds_seed", "error", error_msg=str(exc), started_at=started)
            await db.commit()


async def sync_ah_odds_latest(max_pages: int = 20) -> None:
    started = _now()
    async with aiosqlite.connect(_db_path()) as db:
        try:
            now = _now()
            count = 0
            for page in range(1, max_pages + 1):
                items = await oddalerts_client.get_odds_latest(
                    bookmakers="1,2", markets="6,51", per_page=500, page=page
                )
                if not items:
                    break
                for r in items:
                    bk = r.get("bookmaker_id"); mk = r.get("market_id")
                    if bk not in TARGET_BOOKMAKERS or mk not in TARGET_MARKETS:
                        continue
                    fid = r.get("fixture_id"); odds = r.get("odds")
                    if not fid or odds is None:
                        continue
                    o = float(odds)
                    await db.execute(
                        """INSERT INTO bookmaker_odds
                           (fixture_id,bookmaker_id,market_id,outcome,
                            opening,current,peak,opening_at,current_at)
                           VALUES(?,?,?,?,?,?,?,?,?)
                           ON CONFLICT(fixture_id,bookmaker_id,market_id,outcome) DO UPDATE SET
                             current=excluded.current,
                             peak=MAX(IFNULL(bookmaker_odds.peak,0), excluded.current),
                             current_at=excluded.current_at""",
                        (fid, bk, mk, r.get("outcome", ""),
                         o, o, o, now, now),
                    )
                    count += 1
                if len(items) < 500:
                    break
            await db.commit()
            await _log(db, "ah_odds_latest", "ok", count, started_at=started)
            await db.commit()
        except Exception as exc:
            await _log(db, "ah_odds_latest", "error", error_msg=str(exc), started_at=started)
            await db.commit()


async def sync_predictions() -> None:
    """Per-fixture call to /predictions/generate/:ID. The /multiple endpoint returns 400
    for any batch containing a fixture without an active prediction model, killing the
    whole batch. Per-fixture is slower but resilient: each unsupported fixture is just
    skipped via the 4xx handler in get_predictions_single."""
    started = _now()
    async with aiosqlite.connect(_db_path()) as db:
        try:
            cur = await db.execute(
                """SELECT id FROM fixtures
                   WHERE kickoff_utc >= strftime('%Y-%m-%dT%H:%M:%S','now')
                     AND (predictability IS NULL OR predictability != 'poor')"""
            )
            fids = [int(r[0]) for r in await cur.fetchall()]
            now = _now()
            count = 0
            skipped = 0
            # Fan out per-fixture prediction fetches concurrently.
            results = await _gather_throttled(
                [oddalerts_client.get_predictions_single(fid) for fid in fids]
            )
            for fid, r in zip(fids, results):
                if isinstance(r, Exception):
                    skipped += 1
                    continue
                if r is None:
                    skipped += 1
                    continue
                await db.execute(
                    """INSERT INTO predictions
                       (fixture_id,simulations,home_win,draw,away_win,btts,
                        o15_goals,o25_goals,o35_goals,o45_goals,
                        scorelines,updated_at)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                       ON CONFLICT(fixture_id) DO UPDATE SET
                         simulations=excluded.simulations,
                         home_win=excluded.home_win, draw=excluded.draw,
                         away_win=excluded.away_win, btts=excluded.btts,
                         o15_goals=excluded.o15_goals, o25_goals=excluded.o25_goals,
                         o35_goals=excluded.o35_goals, o45_goals=excluded.o45_goals,
                         scorelines=excluded.scorelines, updated_at=excluded.updated_at""",
                    (fid, r.get("simulations", 0),
                     r.get("home_win"), r.get("draw"), r.get("away_win"),
                     r.get("btts"),
                     r.get("o15_goals"), r.get("o25_goals"),
                     r.get("o35_goals"), r.get("o45_goals"),
                     json.dumps(r.get("scorelines") or {}), now),
                )
                count += 1
            await db.commit()
            await _log(db, "predictions", "ok", count, started_at=started)
            await db.commit()
        except Exception as exc:
            await _log(db, "predictions", "error", error_msg=str(exc), started_at=started)
            await db.commit()


async def full_sync() -> None:
    await sync_from_trends()
    await sync_dropping_odds()

async def _alerts_scan_job():
    """Wrap services.alerts.scan_alerts with a fresh DB connection. Errors are
    swallowed so a transient SQLite hiccup doesn't take down the scheduler."""
    try:
        import aiosqlite
        from database import _db_path
        from services.alerts import scan_alerts
        async with aiosqlite.connect(_db_path()) as db:
            db.row_factory = aiosqlite.Row
            await scan_alerts(db)
    except Exception:
        pass

scheduler.add_job(sync_dropping_odds, "interval", minutes=5, id="dropping")
scheduler.add_job(_alerts_scan_job, "interval", minutes=5, id="alerts_scan")
scheduler.add_job(sync_from_trends, "interval", hours=1, id="fixture_trends")
scheduler.add_job(sync_fixtures_upcoming, "interval", hours=1, id="fixtures_upcoming")
scheduler.add_job(sync_ah_odds_latest, "interval", minutes=5, id="ah_odds_latest")
scheduler.add_job(sync_historical_fixtures, "interval", hours=24, id="historical_fixtures")
scheduler.add_job(sync_team_form, "interval", hours=6, id="team_form")
scheduler.add_job(sync_ah_odds_seed, "interval", hours=12, id="ah_odds_seed")
scheduler.add_job(sync_predictions, "interval", hours=6, id="predictions")
scheduler.add_job(sync_competitions, "interval", hours=24, id="competitions")
scheduler.add_job(sync_teams_meta, "interval", hours=24, id="teams_meta")

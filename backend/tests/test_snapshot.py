"""Snapshot pipeline tests (services/snapshot.py).

Validates waypoint capture semantics:
- Only fixtures within the scan window are touched.
- Waypoints captured in order as `hours_to_kickoff` crosses each threshold.
- (fixture, waypoint) is idempotent — a second run on the same state inserts 0.
- Fixtures without any predictions OR odds rows produce no snapshot.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
import aiosqlite


@pytest.fixture
async def db_path(tmp_path, monkeypatch):
    monkeypatch.setenv("GOALCAST_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("ODDALERTS_API_KEY", "ci-stub")
    import importlib, database
    importlib.reload(database)
    await database.init_db()
    return str(tmp_path / "test.db")


async def _seed_fixture(db_path: str, *, fixture_id: int, kickoff: datetime,
                         status: str = "NS", with_pred: bool = True, with_odds: bool = True):
    now_str = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """INSERT INTO fixtures (id, competition_id, competition_name, home_team, away_team,
               kickoff_utc, status, fetched_at, updated_at)
               VALUES (?, 1, 'L', 'A', 'B', ?, ?, ?, ?)""",
            (fixture_id, kickoff.isoformat(), status, now_str, now_str),
        )
        if with_pred:
            await db.execute(
                """INSERT INTO predictions (fixture_id, simulations, home_win, draw, away_win, btts,
                   o15_goals, o25_goals, o35_goals, o45_goals, scorelines, updated_at)
                   VALUES (?, 100, 60, 25, 15, 55, 70, 55, 30, 10, '{}', ?)""",
                (fixture_id, now_str),
            )
        if with_odds:
            for outcome, current in (("home", 1.90), ("draw", 3.40), ("away", 4.20)):
                await db.execute(
                    """INSERT INTO bookmaker_odds
                       (fixture_id, bookmaker_id, market_id, outcome, opening, current, peak, opening_at, current_at)
                       VALUES (?, 1, 6, ?, ?, ?, ?, ?, ?)""",
                    (fixture_id, outcome, current + 0.1, current, current + 0.1, now_str, now_str),
                )
        await db.commit()


@pytest.mark.asyncio
async def test_captures_at_48h_waypoint(db_path):
    from services.snapshot import run_snapshot
    now = datetime(2026, 5, 18, 12, 0, 0, tzinfo=timezone.utc)
    await _seed_fixture(db_path, fixture_id=10, kickoff=now + timedelta(hours=47.5))
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        inserted = await run_snapshot(db, now=now)
    assert inserted == 1

    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT waypoint FROM historical_predictions WHERE fixture_id=10") as cur:
            rows = await cur.fetchall()
    waypoints = [r["waypoint"] for r in rows]
    assert waypoints == ["48h"]


@pytest.mark.asyncio
async def test_progression_captures_each_waypoint_as_time_advances(db_path):
    """As we simulate time approaching kickoff, each waypoint fires once."""
    from services.snapshot import run_snapshot
    kickoff = datetime(2026, 5, 20, 12, 0, 0, tzinfo=timezone.utc)
    await _seed_fixture(db_path, fixture_id=20, kickoff=kickoff)

    time_points = [
        kickoff - timedelta(hours=47.5),  # 48h fires
        kickoff - timedelta(hours=23.5),  # 24h fires
        kickoff - timedelta(hours=5.5),   # 6h fires
        kickoff - timedelta(hours=0.5),   # 1h fires
        kickoff + timedelta(minutes=10),  # kickoff fires (hours_to negative)
    ]
    expected_total = [1, 2, 3, 4, 5]
    rows = []
    for now, expected_n in zip(time_points, expected_total):
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            await run_snapshot(db, now=now)
            async with db.execute("SELECT waypoint FROM historical_predictions WHERE fixture_id=20") as cur:
                rows = await cur.fetchall()
        assert len(rows) == expected_n, (
            f"at {now.isoformat()} expected {expected_n} rows, got {len(rows)}: {[r['waypoint'] for r in rows]}"
        )

    waypoints = {r["waypoint"] for r in rows}
    assert waypoints == {"48h", "24h", "6h", "1h", "kickoff"}


@pytest.mark.asyncio
async def test_idempotent_second_run_inserts_nothing(db_path):
    from services.snapshot import run_snapshot
    now = datetime(2026, 5, 18, 12, 0, 0, tzinfo=timezone.utc)
    await _seed_fixture(db_path, fixture_id=30, kickoff=now + timedelta(hours=20))
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        first = await run_snapshot(db, now=now)
        second = await run_snapshot(db, now=now)
    # hours_to=20 < 24 < 48 → 48h + 24h captured (2 waypoints).
    assert first == 2
    assert second == 0


@pytest.mark.asyncio
async def test_skips_when_no_predictions_or_odds(db_path):
    from services.snapshot import run_snapshot
    now = datetime(2026, 5, 18, 12, 0, 0, tzinfo=timezone.utc)
    await _seed_fixture(db_path, fixture_id=40, kickoff=now + timedelta(hours=20),
                          with_pred=False, with_odds=False)
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        inserted = await run_snapshot(db, now=now)
    assert inserted == 0


@pytest.mark.asyncio
async def test_captures_odds_only_when_no_prediction(db_path):
    from services.snapshot import run_snapshot
    now = datetime(2026, 5, 18, 12, 0, 0, tzinfo=timezone.utc)
    await _seed_fixture(db_path, fixture_id=50, kickoff=now + timedelta(hours=20),
                          with_pred=False, with_odds=True)
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        inserted = await run_snapshot(db, now=now)
        async with db.execute("SELECT COUNT(*) AS n FROM historical_predictions WHERE fixture_id=50") as cur:
            pred_n = (await cur.fetchone())["n"]
        async with db.execute("SELECT COUNT(*) AS n FROM historical_odds WHERE fixture_id=50") as cur:
            odds_n = (await cur.fetchone())["n"]
    assert pred_n == 0
    assert odds_n == 6  # 3 outcomes × 2 waypoints
    assert inserted == 2


@pytest.mark.asyncio
async def test_fixtures_outside_scan_window_ignored(db_path):
    from services.snapshot import run_snapshot
    now = datetime(2026, 5, 18, 12, 0, 0, tzinfo=timezone.utc)
    # Kickoff 100h away — outside the 60h forward window.
    await _seed_fixture(db_path, fixture_id=60, kickoff=now + timedelta(hours=100))
    # Kickoff 12h ago — outside the 6h backward window.
    await _seed_fixture(db_path, fixture_id=61, kickoff=now - timedelta(hours=12), status="FT")
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        inserted = await run_snapshot(db, now=now)
    assert inserted == 0


@pytest.mark.asyncio
async def test_kickoff_waypoint_fires_after_status_transition(db_path):
    """Once a fixture passes kickoff (hours_to < 0), the 'kickoff' waypoint
    should be captured even if status has flipped to LIVE/FT."""
    from services.snapshot import run_snapshot
    now = datetime(2026, 5, 18, 12, 0, 0, tzinfo=timezone.utc)
    await _seed_fixture(db_path, fixture_id=70, kickoff=now - timedelta(minutes=30), status="FT")
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        inserted = await run_snapshot(db, now=now)
        async with db.execute("SELECT waypoint FROM historical_predictions WHERE fixture_id=70 ORDER BY waypoint") as cur:
            wps = [r["waypoint"] for r in await cur.fetchall()]
    # All 5 waypoints already crossed → all 5 captured at once.
    assert sorted(wps) == sorted(["1h", "24h", "48h", "6h", "kickoff"])
    assert inserted == 5


@pytest.mark.asyncio
async def test_ht_pct_copied_to_historical_predictions(db_path):
    """HT pcts on predictions row → snapshot copies them to historical_predictions.

    Wires up the gs_ht_ev signal: without this copy, gs_ht_ev.compute()
    returns None because historical_predictions.home_win_ht_pct is NULL.
    """
    from services.snapshot import run_snapshot
    now = datetime(2026, 5, 18, 12, 0, 0, tzinfo=timezone.utc)
    await _seed_fixture(db_path, fixture_id=90, kickoff=now + timedelta(hours=20))
    # Backfill HT pcts onto the predictions row (mirrors sync_fixtures_upcoming
    # writing them, then sync_predictions filling in FT sim counts).
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """UPDATE predictions
                 SET home_win_ht_pct=42.0, draw_ht_pct=28.0, away_win_ht_pct=30.0
               WHERE fixture_id=90""",
        )
        await db.commit()

    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        await run_snapshot(db, now=now)
        async with db.execute(
            """SELECT waypoint, home_win_ht_pct, draw_ht_pct, away_win_ht_pct
               FROM historical_predictions WHERE fixture_id=90
               ORDER BY waypoint"""
        ) as cur:
            rows = [dict(r) for r in await cur.fetchall()]
    assert len(rows) >= 1
    for r in rows:
        assert r["home_win_ht_pct"] == 42.0
        assert r["draw_ht_pct"] == 28.0
        assert r["away_win_ht_pct"] == 30.0


@pytest.mark.asyncio
async def test_ht_pct_null_when_predictions_lack_it(db_path):
    """No HT pcts on predictions → historical_predictions rows have NULLs (no crash)."""
    from services.snapshot import run_snapshot
    now = datetime(2026, 5, 18, 12, 0, 0, tzinfo=timezone.utc)
    await _seed_fixture(db_path, fixture_id=91, kickoff=now + timedelta(hours=20))
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        await run_snapshot(db, now=now)
        async with db.execute(
            """SELECT home_win_ht_pct, draw_ht_pct, away_win_ht_pct
               FROM historical_predictions WHERE fixture_id=91"""
        ) as cur:
            rows = [dict(r) for r in await cur.fetchall()]
    assert rows
    for r in rows:
        assert r["home_win_ht_pct"] is None
        assert r["draw_ht_pct"] is None
        assert r["away_win_ht_pct"] is None


@pytest.mark.asyncio
async def test_signals_snapshot_written_alongside_historical(db_path):
    """After a snapshot run, signals_snapshot must have a GS-Mispricing row per
    captured (fixture, waypoint) where both predictions and Pinnacle 1X2 odds
    are present. Other registered signals (GS-LineMove, GS-SharpSquare) write
    their own rows when their preconditions hold — we assert only on the
    GS-Mispricing rows here, since this test seeds only Pinnacle odds and
    line-move on the first waypoint cannot be computed yet."""
    from services.snapshot import run_snapshot
    now = datetime(2026, 5, 18, 12, 0, 0, tzinfo=timezone.utc)
    await _seed_fixture(db_path, fixture_id=80, kickoff=now + timedelta(hours=20))
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        await run_snapshot(db, now=now)
        async with db.execute(
            """SELECT signal_type, signal_version, waypoint, scope, value_json, strength
               FROM signals_snapshot
               WHERE fixture_id=80 AND signal_type='GS-Mispricing'
               ORDER BY waypoint"""
        ) as cur:
            rows = [dict(r) for r in await cur.fetchall()]
    # 48h + 24h waypoints captured → two GS-Mispricing rows.
    assert len(rows) == 2
    assert {r["waypoint"] for r in rows} == {"48h", "24h"}
    import json
    for r in rows:
        assert r["signal_version"] == "v1.0"
        assert r["scope"] == "public"
        assert r["strength"] is not None and 0.0 <= r["strength"] <= 1.0
        v = json.loads(r["value_json"])
        assert v["selection"] in ("home", "draw", "away")
        assert isinstance(v["delta_pct"], (int, float))

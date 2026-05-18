"""NS → FT snapshot pipeline.

Captures `predictions` + `bookmaker_odds` into `historical_*` tables at five
waypoints relative to kickoff_utc:

    T-48h → T-24h → T-6h → T-1h → kickoff

The job is idempotent on PRIMARY KEY (fixture_id, waypoint). Each waypoint is
captured the FIRST time the scheduler observes hours_to_kickoff <= threshold
AND the row is still missing. Subsequent runs see the row exists and skip.

There is intentionally NO tolerance window at write time — `captured_at` is
stored alongside so downstream queries can filter "snapshots taken near their
target waypoint" if needed. Recording-when-we-saw-it is the source of truth.

Waypoint coverage rules:
- 48h captured once hours_to <= 48
- 24h captured once hours_to <= 24
- 6h, 1h similarly
- 'kickoff' captured once hours_to <= 0 (i.e., kickoff time has passed). The
  status will likely already be LIVE/FT by then; we still snapshot whatever
  predictions/odds row is currently present.

Designed to be called every ~15 minutes; finer cadence improves waypoint
freshness but isn't required for correctness.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import logging

import aiosqlite

from services.signals import REGISTERED as SIGNALS

log = logging.getLogger(__name__)

# (waypoint name, hours-from-kickoff threshold)
WAYPOINTS: list[tuple[str, float]] = [
    ("48h", 48.0),
    ("24h", 24.0),
    ("6h", 6.0),
    ("1h", 1.0),
    ("kickoff", 0.0),
]


async def run_snapshot(db: aiosqlite.Connection, *, now: Optional[datetime] = None) -> int:
    """One-shot snapshot run. Returns number of (fixture, waypoint) pairs written.

    A "write" means at least one row landed in either history table; if a
    fixture has neither prediction nor odds rows, the snapshot is skipped.
    """
    now = now or datetime.now(timezone.utc)
    # Scan window: 60h ahead covers the 48h waypoint with slack; 6h behind
    # catches LIVE/FT fixtures we may have missed at kickoff.
    win_start = (now - timedelta(hours=6)).isoformat()
    win_end = (now + timedelta(hours=60)).isoformat()

    async with db.execute(
        """SELECT id, kickoff_utc, status FROM fixtures
           WHERE kickoff_utc BETWEEN ? AND ?""",
        (win_start, win_end),
    ) as cur:
        fixtures = [dict(r) for r in await cur.fetchall()]

    if not fixtures:
        return 0

    # Cache already-captured (fixture, waypoint) pairs to avoid per-waypoint queries.
    fixture_ids = [f["id"] for f in fixtures]
    placeholders = ",".join("?" * len(fixture_ids))
    captured: set[tuple[int, str]] = set()
    async with db.execute(
        f"SELECT fixture_id, waypoint FROM historical_predictions WHERE fixture_id IN ({placeholders})",
        fixture_ids,
    ) as cur:
        for r in await cur.fetchall():
            captured.add((r["fixture_id"], r["waypoint"]))
    async with db.execute(
        f"SELECT DISTINCT fixture_id, waypoint FROM historical_odds WHERE fixture_id IN ({placeholders})",
        fixture_ids,
    ) as cur:
        for r in await cur.fetchall():
            captured.add((r["fixture_id"], r["waypoint"]))

    written_pairs = 0
    for fx in fixtures:
        kickoff_str = fx["kickoff_utc"]
        if not kickoff_str:
            continue
        try:
            kickoff = _parse_iso(kickoff_str)
        except ValueError:
            continue
        hours_to = (kickoff - now).total_seconds() / 3600.0

        for waypoint, threshold in WAYPOINTS:
            if (fx["id"], waypoint) in captured:
                continue
            if hours_to > threshold:
                continue  # not yet at this waypoint
            wrote = await _capture(db, fx["id"], waypoint, now)
            if wrote:
                written_pairs += 1
                captured.add((fx["id"], waypoint))

    if written_pairs:
        await db.commit()
    return written_pairs


async def _capture(db: aiosqlite.Connection, fixture_id: int, waypoint: str, now: datetime) -> bool:
    """Capture predictions + odds for one (fixture, waypoint). Returns whether
    anything was actually written (False if neither predictions nor odds exist)."""
    wrote = False

    async with db.execute(
        """SELECT simulations, home_win, draw, away_win, btts, o25_goals, scorelines,
                  home_win_ht_pct, draw_ht_pct, away_win_ht_pct
           FROM predictions WHERE fixture_id=?""",
        (fixture_id,),
    ) as cur:
        pred = await cur.fetchone()
    if pred and pred["simulations"]:
        sims = pred["simulations"]
        await db.execute(
            """INSERT INTO historical_predictions
                 (fixture_id, waypoint, simulations,
                  home_win_pct, draw_pct, away_win_pct,
                  btts_pct, o25_pct, scorelines, captured_at,
                  home_win_ht_pct, draw_ht_pct, away_win_ht_pct)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(fixture_id, waypoint) DO NOTHING""",
            (
                fixture_id, waypoint, sims,
                round(pred["home_win"] / sims * 100, 2),
                round(pred["draw"]     / sims * 100, 2),
                round(pred["away_win"] / sims * 100, 2),
                round(pred["btts"]      / sims * 100, 2) if pred["btts"] is not None else None,
                round(pred["o25_goals"] / sims * 100, 2) if pred["o25_goals"] is not None else None,
                pred["scorelines"],
                now.isoformat(),
                pred["home_win_ht_pct"],
                pred["draw_ht_pct"],
                pred["away_win_ht_pct"],
            ),
        )
        wrote = True

    async with db.execute(
        """SELECT bookmaker_id, market_id, outcome, current
           FROM bookmaker_odds WHERE fixture_id=? AND current IS NOT NULL""",
        (fixture_id,),
    ) as cur:
        odds_rows = [dict(r) for r in await cur.fetchall()]
    for o in odds_rows:
        await db.execute(
            """INSERT INTO historical_odds
                 (fixture_id, bookmaker_id, market_id, outcome, waypoint, odds, captured_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(fixture_id, bookmaker_id, market_id, outcome, waypoint) DO NOTHING""",
            (fixture_id, o["bookmaker_id"], o["market_id"], o["outcome"],
             waypoint, o["current"], now.isoformat()),
        )
        wrote = True

    # Compute and persist signals for this (fixture, waypoint). Signal failures
    # are isolated from the historical_* writes — a buggy signal must not block
    # the load-bearing snapshot.
    for signal in SIGNALS:
        try:
            result = await signal.compute(db, fixture_id, waypoint)
            if result is None:
                continue
            await db.execute(
                """INSERT INTO signals_snapshot
                     (fixture_id, signal_type, signal_version, waypoint,
                      scope, value_json, strength, captured_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(fixture_id, signal_type, waypoint) DO NOTHING""",
                (
                    fixture_id, signal.signal_type, signal.signal_version,
                    waypoint, signal.scope, result["value_json"],
                    result.get("strength"), now.isoformat(),
                ),
            )
        except Exception:
            log.exception(
                "signal %s failed for fixture=%s waypoint=%s",
                signal.signal_type, fixture_id, waypoint,
            )

    return wrote


def _parse_iso(ts: str) -> datetime:
    """Parse a UTC ISO 8601 timestamp robustly (handles trailing Z and offset-less inputs)."""
    s = ts.replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt

"""Paper-trading core workers — House Book auto-follow + FT settlement.

Two idempotent functions, both pure read-from / write-to SQLite (no network,
no scheduler-aware logic — composed by sync.py APScheduler hooks).

1. place_house_bets(db, book_type, threshold)
     For each GS-Mispricing row in signals_snapshot with delta_pct > threshold
     (positive edge only — model > market) on a fixture still status='NS',
     INSERT OR IGNORE into simulated_bets with user_id=0 sentinel. The UNIQUE
     constraint (book_type, fixture_id, selection, user_id) guarantees a
     single bet per (book, match, side) regardless of how often this runs.

2. settle_bets(db)
     For every pending bet (outcome IS NULL) whose fixture is status='FT' and
     has score_home/away, compute the actual 1X2 outcome, mark win/loss,
     write pnl_units, and snapshot closing_odds from
     historical_odds.waypoint='kickoff' for CLV.

See docs/PRD/paper-trading.prd.md.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import aiosqlite

DEFAULT_SIGNAL_TYPE = "GS-Mispricing"
HOUSE_USER_ID = 0
DEFAULT_STAKE = 1.0


def _actual_outcome(score_home: int, score_away: int) -> str:
    if score_home > score_away:
        return "home"
    if score_home < score_away:
        return "away"
    return "draw"


async def place_house_bets(
    db: aiosqlite.Connection,
    *,
    book_type: str,
    threshold: float,
    signal_type: str = DEFAULT_SIGNAL_TYPE,
) -> int:
    """Scan signals_snapshot for positive-edge GS-Mispricing rows whose fixture
    is still NS, place one virtual bet per fixture (idempotent on UNIQUE).
    Returns the number of newly-inserted rows."""
    sql = """
        SELECT s.fixture_id, s.signal_version, s.value_json, s.captured_at, s.waypoint
        FROM signals_snapshot s
        JOIN fixtures f ON f.id = s.fixture_id
        WHERE s.signal_type = ?
          AND f.status = 'NS'
          AND f.id NOT IN (
              SELECT fixture_id FROM simulated_bets
              WHERE book_type = ? AND user_id = ?
          )
    """
    async with db.execute(sql, (signal_type, book_type, HOUSE_USER_ID)) as cur:
        candidates = [dict(r) for r in await cur.fetchall()]

    inserted = 0
    for c in candidates:
        try:
            value = json.loads(c["value_json"])
        except (ValueError, TypeError):
            continue
        delta = value.get("delta_pct")
        selection = value.get("selection")
        if delta is None or selection not in ("home", "draw", "away"):
            continue
        if delta <= threshold:
            # Threshold is exclusive lower bound; negative deltas (market
            # over-estimates the selection) never qualify for House Book.
            continue

        async with db.execute(
            """SELECT odds FROM historical_odds
               WHERE fixture_id=? AND waypoint=? AND bookmaker_id=1
                 AND market_id=6 AND outcome=?""",
            (c["fixture_id"], c["waypoint"], selection),
        ) as cur:
            row = await cur.fetchone()
        if row is None or row["odds"] is None:
            continue
        entry_odds = row["odds"]

        result = await db.execute(
            """INSERT OR IGNORE INTO simulated_bets
                 (book_type, user_id, fixture_id, selection,
                  stake_units, entry_odds, entry_at, entry_waypoint,
                  signal_type, signal_version)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                book_type, HOUSE_USER_ID, c["fixture_id"], selection,
                DEFAULT_STAKE, entry_odds, c["captured_at"], c["waypoint"],
                signal_type, c["signal_version"],
            ),
        )
        if result.rowcount > 0:
            inserted += 1
    if inserted:
        await db.commit()
    return inserted


async def house_book_summary(
    db: aiosqlite.Connection,
    *,
    book_type: str,
    start_bankroll: float = 1000.0,
) -> dict:
    """Aggregated view of one House Book band. Pure read.

    Bankroll is computed deterministically: start + cumulative(pnl_units) over
    settled bets ordered by settled_at ASC. ROI = sum(pnl) / sum(stake) on
    settled bets only — pending bets carry no PnL signal yet.
    """
    async with db.execute(
        """SELECT COUNT(*) AS n FROM simulated_bets
           WHERE book_type=? AND user_id=? AND outcome IS NULL""",
        (book_type, HOUSE_USER_ID),
    ) as cur:
        pending = (await cur.fetchone())["n"]

    async with db.execute(
        """SELECT stake_units, pnl_units, outcome, settled_at
           FROM simulated_bets
           WHERE book_type=? AND user_id=? AND outcome IS NOT NULL
           ORDER BY settled_at ASC, id ASC""",
        (book_type, HOUSE_USER_ID),
    ) as cur:
        settled = [dict(r) for r in await cur.fetchall()]

    n = len(settled)
    if n == 0:
        return {
            "book_type": book_type,
            "bets_settled": 0,
            "bets_pending": pending,
            "bankroll": {"start": start_bankroll, "current": start_bankroll},
            "metrics": {"roi_pct": None, "win_rate": None},
            "timeseries": [],
        }

    total_stake = sum(b["stake_units"] for b in settled)
    total_pnl   = sum(b["pnl_units"]   for b in settled)
    wins        = sum(1 for b in settled if b["outcome"] == "win")

    running = start_bankroll
    timeseries = []
    for b in settled:
        running += b["pnl_units"]
        timeseries.append({"settled_at": b["settled_at"], "bankroll": round(running, 2)})

    return {
        "book_type": book_type,
        "bets_settled": n,
        "bets_pending": pending,
        "bankroll": {"start": start_bankroll, "current": round(running, 2)},
        "metrics": {
            "roi_pct":  round(total_pnl / total_stake * 100, 2) if total_stake else None,
            "win_rate": round(wins / n, 4),
        },
        "timeseries": timeseries,
    }


async def settle_bets(db: aiosqlite.Connection) -> int:
    """Settle every pending bet whose fixture has finalized. Idempotent: bets
    whose `outcome IS NOT NULL` are skipped on re-runs."""
    sql = """
        SELECT b.id, b.selection, b.stake_units, b.entry_odds, b.fixture_id, b.entry_waypoint,
               f.score_home, f.score_away
        FROM simulated_bets b
        JOIN fixtures f ON f.id = b.fixture_id
        WHERE b.outcome IS NULL
          AND f.status = 'FT'
          AND f.score_home IS NOT NULL
          AND f.score_away IS NOT NULL
    """
    async with db.execute(sql) as cur:
        pending = [dict(r) for r in await cur.fetchall()]

    settled_count = 0
    now_iso = datetime.now(timezone.utc).isoformat()
    for r in pending:
        actual = _actual_outcome(r["score_home"], r["score_away"])
        won = (r["selection"] == actual)
        pnl = r["stake_units"] * (r["entry_odds"] - 1) if won else -r["stake_units"]

        # closing_odds = Pinnacle 1X2 at kickoff waypoint for THIS selection.
        # Missing means we never captured kickoff snapshot — CLV stays NULL.
        async with db.execute(
            """SELECT odds FROM historical_odds
               WHERE fixture_id=? AND waypoint='kickoff'
                 AND bookmaker_id=1 AND market_id=6 AND outcome=?""",
            (r["fixture_id"], r["selection"]),
        ) as cur:
            row = await cur.fetchone()
        closing_odds = row["odds"] if row and row["odds"] is not None else None

        await db.execute(
            """UPDATE simulated_bets
                 SET outcome=?, pnl_units=?, closing_odds=?, settled_at=?
                 WHERE id=?""",
            ("win" if won else "loss", pnl, closing_odds, now_iso, r["id"]),
        )
        settled_count += 1
    if settled_count:
        await db.commit()
    return settled_count

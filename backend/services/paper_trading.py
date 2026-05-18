"""Paper-trading core workers — House Book auto-follow + FT settlement.

Three idempotent functions, all pure read-from / write-to SQLite (no network,
no scheduler-aware logic — composed by sync.py APScheduler hooks).

1. place_house_bets(db, book_type, threshold)  [legacy, paper-trading V1]
     For each GS-Mispricing row in signals_snapshot with delta_pct > threshold
     (positive edge only — model > market) on a fixture still status='NS',
     INSERT OR IGNORE into simulated_bets with user_id=0 sentinel. The UNIQUE
     constraint (book_type, fixture_id, selection, user_id) guarantees a
     single bet per (book, match, side) regardless of how often this runs.

2. place_bets_for_books(db)  [Phase 4a of signal-catalog PRD]
     Same idea but iterates rows from simulated_books. Each book carries
     signal_type / conditions_json / match_scope, so the worker applies the
     SAME conditions evaluator the backtest uses (forward ↔ backtest parity).

3. settle_bets(db)
     For every pending bet (outcome IS NULL) whose fixture is status='FT' and
     has score_home/away, compute the actual 1X2 outcome, mark win/loss,
     write pnl_units, and snapshot closing_odds from
     historical_odds.waypoint='kickoff' for CLV.

See docs/PRD/paper-trading.prd.md + docs/PRD/signal-catalog-and-subscriptions.prd.md.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import aiosqlite

from services.signals.conditions import eval_conditions

DEFAULT_SIGNAL_TYPE = "GS-Mispricing"
HOUSE_USER_ID = 0
DEFAULT_STAKE = 1.0

# Map of book.name → legacy book_type string. New bets on these specific Books
# preserve the legacy `book_type` value so the existing `/api/paper-trading/house`
# endpoint that filters by `book_type='house_5pct'` keeps working. Books not in
# this map use a synthetic `book_<id>` book_type.
_LEGACY_BAND_NAMES: dict[str, str] = {
    "House-GS-Mispricing-3pct": "house_3pct",
    "House-GS-Mispricing-5pct": "house_5pct",
    "House-GS-Mispricing-7pct": "house_7pct",
}


def _book_type_for(book: dict) -> str:
    """Return the (book_type) string to write into simulated_bets for this book,
    preserving legacy band names where applicable."""
    name = book["name"]
    if name in _LEGACY_BAND_NAMES:
        return _LEGACY_BAND_NAMES[name]
    return f"book_{book['id']}"


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


async def place_bets_for_books(db: aiosqlite.Connection) -> int:
    """Per-book auto-bet for every non-archived simulated_books row.

    For each book whose signal_type/version matches a non-NS signals_snapshot
    row, evaluate book.conditions_json + match_scope against the row, look up
    the Pinnacle 1X2 odds for the indicated selection, and INSERT OR IGNORE
    one bet into simulated_bets (book_id-keyed UNIQUE index dedupes).

    Returns total newly-inserted rows across all books. Idempotent — safe
    to schedule every minute.
    """
    async with db.execute(
        """SELECT id, user_id, name, signal_type, signal_version,
                  conditions_json, match_scope
           FROM simulated_books WHERE archived_at IS NULL"""
    ) as cur:
        books = [dict(r) for r in await cur.fetchall()]
    if not books:
        return 0

    # Pre-fetch signals_snapshot rows for all (signal_type, signal_version)
    # combos in one pass — avoid N book-scoped queries.
    sig_versions = {(b["signal_type"], b["signal_version"]) for b in books}
    placeholders = ",".join("(?,?)" for _ in sig_versions)
    flat: list = []
    for st, sv in sig_versions:
        flat.extend([st, sv])
    sig_sql = f"""
        SELECT s.fixture_id, s.signal_type, s.signal_version, s.waypoint,
               s.value_json, s.strength, s.captured_at, f.competition_id
        FROM signals_snapshot s
        JOIN fixtures f ON f.id = s.fixture_id
        WHERE f.status = 'NS'
          AND (s.signal_type, s.signal_version) IN (VALUES {placeholders})
    """
    async with db.execute(sig_sql, flat) as cur:
        rows = [dict(r) for r in await cur.fetchall()]
    # bucket by (signal_type, signal_version)
    by_sig: dict[tuple[str, str], list[dict]] = {}
    for r in rows:
        by_sig.setdefault((r["signal_type"], r["signal_version"]), []).append(r)

    total_inserted = 0
    for book in books:
        try:
            conditions = json.loads(book["conditions_json"]) if book["conditions_json"] else {}
        except (TypeError, ValueError):
            conditions = {}
        candidates = by_sig.get((book["signal_type"], book["signal_version"]), [])
        if not candidates:
            continue

        # Pre-resolve match_scope user prefs for this book if needed.
        allowed_competitions: set[int] | None = None
        if book["match_scope"] == "my_leagues" and book["user_id"] != HOUSE_USER_ID:
            async with db.execute(
                "SELECT competition_id FROM user_competition_prefs WHERE user_id=?",
                (book["user_id"],),
            ) as cur:
                allowed_competitions = {r["competition_id"] for r in await cur.fetchall()}
        # House Books are PRD-forced to match_scope='all' — invariant enforced
        # at INSERT time elsewhere; defensively allow all here if user_id=0.

        book_type = _book_type_for(book)
        for r in candidates:
            if allowed_competitions is not None and r["competition_id"] not in allowed_competitions:
                continue
            if not eval_conditions(conditions, r):
                continue
            try:
                value = json.loads(r["value_json"]) if r["value_json"] else {}
            except (TypeError, ValueError):
                continue
            selection = value.get("selection")
            if selection not in ("home", "draw", "away"):
                continue
            # Pinnacle 1X2 odds at this waypoint for the selected side.
            async with db.execute(
                """SELECT odds FROM historical_odds
                   WHERE fixture_id=? AND waypoint=? AND bookmaker_id=1
                     AND market_id=6 AND outcome=?""",
                (r["fixture_id"], r["waypoint"], selection),
            ) as cur:
                odds_row = await cur.fetchone()
            if odds_row is None or odds_row["odds"] is None:
                continue
            entry_odds = odds_row["odds"]
            res = await db.execute(
                """INSERT OR IGNORE INTO simulated_bets
                     (book_id, book_type, user_id, fixture_id, selection,
                      stake_units, entry_odds, entry_at, entry_waypoint,
                      signal_type, signal_version)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    book["id"], book_type, book["user_id"],
                    r["fixture_id"], selection,
                    DEFAULT_STAKE, entry_odds,
                    r["captured_at"], r["waypoint"],
                    r["signal_type"], r["signal_version"],
                ),
            )
            if res.rowcount and res.rowcount > 0:
                total_inserted += 1
    if total_inserted:
        await db.commit()
    return total_inserted


async def house_book_summary(
    db: aiosqlite.Connection,
    *,
    book_type: str,
    start_bankroll: float = 1000.0,
) -> dict:
    """Aggregated view of one House Book band. Pure read.

    Bankroll = start + cumulative pnl_units over all settled bets (void rows
    contribute 0). ROI and win_rate are computed only over **graded** bets
    (outcome in {'win','loss'}); voided bets are surfaced via `bets_voided`
    but excluded from both metrics' denominators (real-bookmaker convention:
    cancelled matches don't count in your record).
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
        settled_rows = [dict(r) for r in await cur.fetchall()]

    n_settled = len(settled_rows)
    n_voided  = sum(1 for b in settled_rows if b["outcome"] == "void")

    if n_settled == 0:
        return {
            "book_type": book_type,
            "bets_settled": 0,
            "bets_pending": pending,
            "bets_voided": 0,
            "bankroll": {"start": start_bankroll, "current": start_bankroll},
            "metrics": {"roi_pct": None, "win_rate": None},
            "timeseries": [],
        }

    graded = [b for b in settled_rows if b["outcome"] in ("win", "loss")]
    graded_stake = sum(b["stake_units"] for b in graded)
    graded_pnl   = sum(b["pnl_units"]   for b in graded)
    wins         = sum(1 for b in graded if b["outcome"] == "win")

    running = start_bankroll
    timeseries = []
    for b in settled_rows:
        running += b["pnl_units"]  # void contributes 0 → bankroll unchanged
        timeseries.append({"settled_at": b["settled_at"], "bankroll": round(running, 2)})

    return {
        "book_type": book_type,
        "bets_settled": n_settled,
        "bets_pending": pending,
        "bets_voided": n_voided,
        "bankroll": {"start": start_bankroll, "current": round(running, 2)},
        "metrics": {
            "roi_pct":  round(graded_pnl / graded_stake * 100, 2) if graded_stake else None,
            "win_rate": round(wins / len(graded), 4) if graded else None,
        },
        "timeseries": timeseries,
    }


# Fixture status values that mean "match will never produce a 1X2 result":
# postponed, cancelled, abandoned, awarded (forfeit), walkover. Real books
# refund stake on these → virtual ledger mirrors with outcome='void', pnl=0.
VOID_STATUSES = frozenset({"PST", "CAN", "ABD", "AWD", "WO"})
# Statuses that mean "match still in progress / not yet kicked off". The bet
# stays pending (outcome=NULL) — a previously-settled row that lands here is
# evidence the upstream feed un-finalized the fixture (postponed mid-match,
# admin reversal) and must be reset.
PENDING_STATUSES = frozenset({"NS", "TBD", "LIVE", "1H", "HT", "2H", "ET", "P"})


def _desired_outcome(
    fixture_status: str, score_home, score_away, selection: str, stake_units: float, entry_odds: float
) -> tuple[str | None, float | None]:
    """Resolve the (outcome, pnl_units) that the bet SHOULD have right now,
    given the fixture's current status/score. Returns (None, None) for pending."""
    if fixture_status == "FT" and score_home is not None and score_away is not None:
        actual = _actual_outcome(score_home, score_away)
        won = (selection == actual)
        pnl = stake_units * (entry_odds - 1) if won else -stake_units
        return ("win" if won else "loss", pnl)
    if fixture_status in VOID_STATUSES:
        return ("void", 0.0)
    # PENDING_STATUSES, unknown, or FT-but-no-score: treat as pending.
    return (None, None)


async def settle_bets(db: aiosqlite.Connection) -> int:
    """Re-evaluate every bet against its fixture's CURRENT state, updating
    only when the stored outcome/pnl drifted from what the fixture now says.

    Handles four classes of drift safely:
      • Pending → resolved (the normal settlement path)
      • Resolved → re-resolved (administrative score correction post-FT)
      • Resolved → pending (fixture reverted to NS / postponed mid-match)
      • Pending → void (fixture cancelled / postponed before completion)

    No-change runs touch nothing — settled_at is preserved verbatim. Only
    actual drifts bump settled_at (and the audit trail with it).
    """
    sql = """
        SELECT b.id, b.selection, b.stake_units, b.entry_odds, b.fixture_id,
               b.outcome, b.pnl_units,
               f.status, f.score_home, f.score_away
        FROM simulated_bets b
        JOIN fixtures f ON f.id = b.fixture_id
    """
    async with db.execute(sql) as cur:
        rows = [dict(r) for r in await cur.fetchall()]

    changed = 0
    now_iso = datetime.now(timezone.utc).isoformat()
    for r in rows:
        desired_outcome, desired_pnl = _desired_outcome(
            r["status"], r["score_home"], r["score_away"],
            r["selection"], r["stake_units"], r["entry_odds"],
        )

        # Compare against stored state with float tolerance to avoid spurious churn.
        same_outcome = (r["outcome"] == desired_outcome)
        same_pnl = (
            (r["pnl_units"] is None and desired_pnl is None)
            or (r["pnl_units"] is not None and desired_pnl is not None
                and abs(r["pnl_units"] - desired_pnl) < 1e-9)
        )
        if same_outcome and same_pnl:
            continue

        if desired_outcome is None:
            # Reset to pending — keep closing_odds for potential CLV when fixture re-finalizes.
            await db.execute(
                """UPDATE simulated_bets
                     SET outcome=NULL, pnl_units=NULL, settled_at=NULL
                     WHERE id=?""",
                (r["id"],),
            )
        else:
            # Capture closing_odds from historical_odds at kickoff waypoint
            # (only meaningful for win/loss; void keeps it but it's informational).
            async with db.execute(
                """SELECT odds FROM historical_odds
                   WHERE fixture_id=? AND waypoint='kickoff'
                     AND bookmaker_id=1 AND market_id=6 AND outcome=?""",
                (r["fixture_id"], r["selection"]),
            ) as cur:
                co_row = await cur.fetchone()
            closing_odds = co_row["odds"] if co_row and co_row["odds"] is not None else None

            await db.execute(
                """UPDATE simulated_bets
                     SET outcome=?, pnl_units=?, closing_odds=?, settled_at=?
                     WHERE id=?""",
                (desired_outcome, desired_pnl, closing_odds, now_iso, r["id"]),
            )
        changed += 1
    if changed:
        await db.commit()
    return changed

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

from services.ah import make_ah_outcome
from services.paper_trading_ah import settle_ah
from services.signals import REGISTERED
from services.signals.conditions import eval_conditions

DEFAULT_SIGNAL_TYPE = "GS-Mispricing"
HOUSE_USER_ID = 0
DEFAULT_STAKE = 1.0

# Phase B of paper-trading-realism PRD: settlement / placement dispatchers
# know how to handle these two markets. Any registered signal whose
# settle_market is not in this set is gated out of place_bets_for_books and
# settle_bets. Add to this set as new market settlement paths are wired up.
_PAPER_TRADING_1X2_MARKET: tuple[int, str] = (6, "1X2")
_PAPER_TRADING_FT_AH_MARKET: tuple[int, str] = (51, "FT_AH")
SUPPORTED_SETTLE_MARKETS: frozenset[tuple[int, str]] = frozenset({
    _PAPER_TRADING_1X2_MARKET,
    _PAPER_TRADING_FT_AH_MARKET,
})

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

    # Drop books whose signal is unregistered or settles on a market the
    # dispatcher below doesn't support (currently 1X2 + FT AH).
    settle_by_sig = {(s.signal_type, s.signal_version): s.settle_market for s in REGISTERED}
    books = [
        b for b in books
        if settle_by_sig.get((b["signal_type"], b["signal_version"])) in SUPPORTED_SETTLE_MARKETS
    ]
    if not books:
        return 0

    # Pre-fetch signals_snapshot rows for all (signal_type, signal_version)
    # combos in one pass — avoid N book-scoped queries.
    # The f-string `placeholders` interpolation only emits `?` markers (no user
    # data); the actual values go through the parameterized `flat` list.
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

    # Batch-fetch all Pinnacle 1X2 odds for the (fixture_id, waypoint) pairs
    # touched by any candidate row. Avoids N×M single-row SELECTs in the inner
    # loop (review finding M1). Keyed by (fixture_id, waypoint, outcome).
    odds_by_key: dict[tuple[int, str, str], float] = {}
    if rows:
        fw_pairs = {(r["fixture_id"], r["waypoint"]) for r in rows}
        odds_placeholders = ",".join("(?,?)" for _ in fw_pairs)
        odds_flat: list = []
        for fid, wp in fw_pairs:
            odds_flat.extend([fid, wp])
        odds_sql = f"""
            SELECT fixture_id, waypoint, outcome, odds
            FROM historical_odds
            WHERE bookmaker_id = 1 AND market_id = 6
              AND outcome IN ('home','draw','away')
              AND (fixture_id, waypoint) IN (VALUES {odds_placeholders})
        """
        async with db.execute(odds_sql, odds_flat) as cur:
            for r in await cur.fetchall():
                if r["odds"] is None:
                    continue
                odds_by_key[(r["fixture_id"], r["waypoint"], r["outcome"])] = float(r["odds"])

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
        book_sm = settle_by_sig[(book["signal_type"], book["signal_version"])]
        for r in candidates:
            if allowed_competitions is not None and r["competition_id"] not in allowed_competitions:
                continue
            if not eval_conditions(conditions, r):
                continue
            try:
                value = json.loads(r["value_json"]) if r["value_json"] else {}
            except (TypeError, ValueError):
                continue

            # Per-market dispatch — resolve (entry_odds, market_id, selection, ah_line).
            if book_sm == _PAPER_TRADING_1X2_MARKET:
                selection = value.get("selection")
                if selection not in ("home", "draw", "away"):
                    continue
                entry_odds = odds_by_key.get((r["fixture_id"], r["waypoint"], selection))
                if entry_odds is None:
                    continue
                bet_market_id, bet_selection, bet_ah_line = 6, selection, None
            elif book_sm == _PAPER_TRADING_FT_AH_MARKET:
                side = value.get("selection")
                if side not in ("home", "away"):
                    continue
                home_line = value.get("ah_line")
                if home_line is None:
                    continue
                # `ah_line` in value_json is from the home team's perspective;
                # flip the sign when betting the away side.
                line_from_side = float(home_line) if side == "home" else -float(home_line)
                try:
                    outcome_str = make_ah_outcome(side, line_from_side)
                except ValueError:
                    continue
                async with db.execute(
                    """SELECT odds FROM historical_odds
                       WHERE fixture_id=? AND waypoint=? AND bookmaker_id=1
                         AND market_id=51 AND outcome=?""",
                    (r["fixture_id"], r["waypoint"], outcome_str),
                ) as cur:
                    odds_row = await cur.fetchone()
                if not odds_row or odds_row["odds"] is None:
                    continue
                entry_odds = float(odds_row["odds"])
                bet_market_id, bet_selection, bet_ah_line = 51, side, line_from_side
            else:
                continue

            res = await db.execute(
                """INSERT OR IGNORE INTO simulated_bets
                     (book_id, book_type, user_id, fixture_id, market_id, ah_line, selection,
                      stake_units, entry_odds, entry_at, entry_waypoint,
                      signal_type, signal_version)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    book["id"], book_type, book["user_id"],
                    r["fixture_id"], bet_market_id, bet_ah_line, bet_selection,
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


async def book_summary(
    db: aiosqlite.Connection,
    *,
    book_id: int,
    starting_units: float = 100.0,
) -> dict:
    """Aggregated view of one Book (House or Personal) keyed by book_id.

    Same metrics as `house_book_summary` (ROI / win_rate / pending / voided /
    bankroll timeseries) but addresses the Book by its primary key instead
    of the legacy `book_type` string. Phase 4b of signal-catalog PRD.

    Defaults `starting_units=100.0` to align with `simulated_books.starting_units`
    default, so per-book ROI curves on the multi-curve chart use a consistent
    baseline — the **whole point** of "信号即账户 + 统一起始资金".
    """
    async with db.execute(
        """SELECT COUNT(*) AS n FROM simulated_bets
           WHERE book_id=? AND outcome IS NULL""",
        (book_id,),
    ) as cur:
        pending = (await cur.fetchone())["n"]

    async with db.execute(
        """SELECT stake_units, pnl_units, outcome, settled_at
           FROM simulated_bets
           WHERE book_id=? AND outcome IS NOT NULL
           ORDER BY settled_at ASC, id ASC""",
        (book_id,),
    ) as cur:
        settled_rows = [dict(r) for r in await cur.fetchall()]

    n_settled = len(settled_rows)
    # Both 'void' (fixture cancelled) and 'push' (AH adjusted score = 0) are
    # refunds — neither contributes to ROI denominator or win_rate.
    n_voided  = sum(1 for b in settled_rows if b["outcome"] in ("void", "push"))

    if n_settled == 0:
        return {
            "book_id":      book_id,
            "bets_settled": 0,
            "bets_pending": pending,
            "bets_voided":  0,
            "bankroll":     {"start": starting_units, "current": starting_units},
            "metrics":      {"roi_pct": None, "win_rate": None},
            "timeseries":   [],
        }

    # Graded outcomes include AH half_win / half_loss — they have real signed
    # pnl on a real (half-) stake, so excluding them would understate volume.
    graded = [b for b in settled_rows if b["outcome"] in ("win", "loss", "half_win", "half_loss")]
    graded_stake = sum(b["stake_units"] for b in graded)
    graded_pnl   = sum(b["pnl_units"]   for b in graded)
    # win_rate counts half_win at 0.5 — partial AH wins are partial victories.
    wins         = sum(1.0 if b["outcome"] == "win"
                       else 0.5 if b["outcome"] == "half_win"
                       else 0.0
                       for b in graded)

    running = starting_units
    timeseries = []
    for b in settled_rows:
        running += b["pnl_units"]  # void contributes 0 → bankroll unchanged
        timeseries.append({"settled_at": b["settled_at"], "bankroll": round(running, 2)})

    return {
        "book_id":      book_id,
        "bets_settled": n_settled,
        "bets_pending": pending,
        "bets_voided":  n_voided,
        "bankroll":     {"start": starting_units, "current": round(running, 2)},
        "metrics": {
            "roi_pct":  round(graded_pnl / graded_stake * 100, 2) if graded_stake else None,
            "win_rate": round(wins / len(graded), 4) if graded else None,
        },
        "timeseries": timeseries,
    }


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
    # Both 'void' and 'push' are refunds — see book_summary().
    n_voided  = sum(1 for b in settled_rows if b["outcome"] in ("void", "push"))

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

    graded = [b for b in settled_rows if b["outcome"] in ("win", "loss", "half_win", "half_loss")]
    graded_stake = sum(b["stake_units"] for b in graded)
    graded_pnl   = sum(b["pnl_units"]   for b in graded)
    wins         = sum(1.0 if b["outcome"] == "win"
                       else 0.5 if b["outcome"] == "half_win"
                       else 0.0
                       for b in graded)

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
    fixture_status: str,
    score_home, score_away,
    selection: str,
    stake_units: float,
    entry_odds: float,
    market_id: int | None,
    ah_line: float | None,
) -> tuple[str | None, float | None]:
    """Resolve the (outcome, pnl_units) that the bet SHOULD have right now,
    given the fixture's current status/score. Returns (None, None) for pending.

    Dispatches by ``market_id``:
      • 6  or NULL (legacy) → 1X2 settlement (win/loss only)
      • 51                  → Asian Handicap via services.paper_trading_ah.settle_ah
                              (outcomes may include push / half_win / half_loss)
    """
    if fixture_status in VOID_STATUSES:
        return ("void", 0.0)
    if fixture_status != "FT" or score_home is None or score_away is None:
        return (None, None)

    if market_id == 51:
        if ah_line is None or selection not in ("home", "away"):
            return ("void", 0.0)
        return settle_ah(
            float(ah_line), score_home, score_away, selection,
            stake_units, entry_odds,
        )
    # 1X2 (market_id == 6 or legacy NULL).
    actual = _actual_outcome(score_home, score_away)
    won = (selection == actual)
    pnl = stake_units * (entry_odds - 1) if won else -stake_units
    return ("win" if won else "loss", pnl)


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
               b.market_id, b.ah_line, b.outcome, b.pnl_units,
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
            r["market_id"], r["ah_line"],
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
            # Capture closing_odds from historical_odds at kickoff waypoint —
            # query market_id + outcome by the bet's own market binding so AH
            # bets use the AH closing line and 1X2 bets use the 1X2 line.
            co_market_id = r["market_id"] if r["market_id"] is not None else 6
            if co_market_id == 51 and r["ah_line"] is not None and r["selection"] in ("home", "away"):
                try:
                    co_outcome = make_ah_outcome(r["selection"], float(r["ah_line"]))
                except ValueError:
                    co_outcome = None
            else:
                co_outcome = r["selection"]
            closing_odds: float | None = None
            if co_outcome is not None:
                async with db.execute(
                    """SELECT odds FROM historical_odds
                       WHERE fixture_id=? AND waypoint='kickoff'
                         AND bookmaker_id=1 AND market_id=? AND outcome=?""",
                    (r["fixture_id"], co_market_id, co_outcome),
                ) as cur:
                    co_row = await cur.fetchone()
                if co_row and co_row["odds"] is not None:
                    closing_odds = co_row["odds"]

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

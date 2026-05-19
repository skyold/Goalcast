"""House Book bootstrap & legacy migration.

Phase 4a of the signal-catalog-and-subscriptions PRD. Two responsibilities:

1. **ensure_house_books(db)** — On every startup, make sure each REGISTERED
   signal has at least one House Book (user_id=0). Idempotent via the
   `UNIQUE(user_id, name)` constraint on simulated_books.

2. **migrate_legacy_book_types(db)** — Translate pre-Phase-4 `simulated_bets`
   rows (those with `book_type LIKE 'house_%pct'` and `book_id IS NULL`) onto
   the new per-signal Book model. Specifically:
     - For each legacy band (`house_3pct`/`house_5pct`/`house_7pct`), create a
       dedicated House Book whose conditions encode the band's delta_pct
       threshold, then UPDATE matching simulated_bets.book_id to point to it.
     - Run on startup so even existing prod DBs catch up without a separate
       migration script.

Both functions are designed to be idempotent and safe to re-run.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import aiosqlite

from services.signals import REGISTERED


# Default conditions for each signal's canonical House Book. PRD § Migration
# step 5 says the GS-Mispricing House Book inherits the legacy 5pct threshold
# to preserve behaviour; other signals get empty conditions (subscribe to all).
_DEFAULT_HOUSE_CONDITIONS: dict[str, dict] = {
    "GS-Mispricing": {
        "filters": [{"path": "value.delta_pct", "op": ">", "value": 5}],
    },
    # GS-LineMove, GS-SharpSquare, GS-KEN-HT-EV, ... → empty default → {}
}

# Legacy paper-trading V1 band → (delta_pct threshold, House Book name).
_LEGACY_BANDS: list[tuple[str, float]] = [
    ("house_3pct", 3.0),
    ("house_5pct", 5.0),
    ("house_7pct", 7.0),
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def ensure_house_books(db: aiosqlite.Connection) -> int:
    """Make sure every REGISTERED signal has a House Book row.

    Returns the number of new books inserted (0 on idempotent reruns).
    """
    inserted = 0
    now = _now()
    for sig in REGISTERED:
        name = f"House-{sig.signal_type}"
        conditions = _DEFAULT_HOUSE_CONDITIONS.get(sig.signal_type, {})
        cur = await db.execute(
            """INSERT INTO simulated_books
                 (user_id, name, signal_type, signal_version,
                  conditions_json, starting_units, match_scope, created_at)
               VALUES (0, ?, ?, ?, ?, 100.0, 'all', ?)
               ON CONFLICT(user_id, name) DO NOTHING""",
            (name, sig.signal_type, sig.signal_version,
             json.dumps(conditions, separators=(",", ":")), now),
        )
        if cur.rowcount and cur.rowcount > 0:
            inserted += 1
    await db.commit()
    return inserted


async def migrate_legacy_book_types(db: aiosqlite.Connection) -> int:
    """Backfill `simulated_bets.book_id` from legacy `book_type` bands.

    Returns the number of `simulated_bets` rows updated. Safe to re-run —
    the WHERE clause requires book_id IS NULL.
    """
    now = _now()
    rows_updated = 0
    for book_type, threshold in _LEGACY_BANDS:
        # Find or create the corresponding House Book.
        name = f"House-GS-Mispricing-{int(threshold)}pct"
        await db.execute(
            """INSERT INTO simulated_books
                 (user_id, name, signal_type, signal_version,
                  conditions_json, starting_units, match_scope, created_at)
               VALUES (0, ?, 'GS-Mispricing', 'v1.0', ?, 100.0, 'all', ?)
               ON CONFLICT(user_id, name) DO NOTHING""",
            (
                name,
                json.dumps(
                    {"filters": [{"path": "value.delta_pct", "op": ">", "value": threshold}]},
                    separators=(",", ":"),
                ),
                now,
            ),
        )
        # Resolve the book id we just ensured exists.
        async with db.execute(
            "SELECT id FROM simulated_books WHERE user_id=0 AND name=?", (name,),
        ) as cur:
            row = await cur.fetchone()
        if row is None:
            continue
        book_id = row["id"]
        # Backfill legacy rows. Only touch rows whose book_id is still NULL.
        cur = await db.execute(
            """UPDATE simulated_bets SET book_id=?
               WHERE book_type=? AND book_id IS NULL""",
            (book_id, book_type),
        )
        rows_updated += cur.rowcount or 0
    await db.commit()
    return rows_updated


async def bootstrap_books(db: aiosqlite.Connection) -> tuple[int, int]:
    """One-call helper for startup: ensure books + migrate legacy rows.

    Returns (new_books_count, rows_backfilled).
    """
    new_books = await ensure_house_books(db)
    rows = await migrate_legacy_book_types(db)
    return new_books, rows

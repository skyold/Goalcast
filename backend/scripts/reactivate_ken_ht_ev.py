"""Reactivate the KEN-HT-EV House Book and clear its stale wrong-market bets.

Phase B of paper-trading-realism PRD. After B0-B4 the AH settlement path is
wired up — but the existing House Book is still archived (from Phase A's
archive_misconfigured_books pass) and its pending bets carry FT 1X2
entry_odds (the wrong market). This script:

  1. UPDATE simulated_books SET archived_at = NULL
       WHERE signal_type = 'GS-KEN-HT-EV' AND archived_at IS NOT NULL
  2. DELETE FROM simulated_bets
       WHERE signal_type = 'GS-KEN-HT-EV'
         AND outcome IS NULL
         AND (market_id IS NULL OR market_id = 6)
     — only the legacy wrong-market pending rows; settled bets and correct
     market_id=51 AH bets are preserved.

After running, place_bets_for_books will repopulate the book with correct
market_id=51 AH bets on the next snapshot tick (assuming AH odds are
available in historical_odds for the relevant fixture/waypoint).

Idempotent: second run is a no-op once the book is unarchived and stale
1X2-tagged KEN-HT-EV pending bets are gone.

Usage:
    cd backend && .venv/bin/python -m scripts.reactivate_ken_ht_ev
"""
from __future__ import annotations

import asyncio

import aiosqlite

from database import _db_path

KEN_HT_EV_SIGNAL_TYPE = "GS-KEN-HT-EV"


async def reactivate_ken_ht_ev(db: aiosqlite.Connection) -> tuple[int, int]:
    """Unarchive KEN-HT-EV books and delete their stale market_id=6 pending
    bets. Returns ``(books_unarchived, bets_deleted)``."""
    res_books = await db.execute(
        """UPDATE simulated_books
              SET archived_at = NULL
            WHERE signal_type = ?
              AND archived_at IS NOT NULL""",
        (KEN_HT_EV_SIGNAL_TYPE,),
    )
    n_unarchived = res_books.rowcount or 0

    res_bets = await db.execute(
        """DELETE FROM simulated_bets
            WHERE signal_type = ?
              AND outcome IS NULL
              AND (market_id IS NULL OR market_id = 6)""",
        (KEN_HT_EV_SIGNAL_TYPE,),
    )
    n_deleted = res_bets.rowcount or 0

    if n_unarchived or n_deleted:
        await db.commit()
    return n_unarchived, n_deleted


async def _main() -> None:
    async with aiosqlite.connect(_db_path()) as db:
        db.row_factory = aiosqlite.Row
        n_books, n_bets = await reactivate_ken_ht_ev(db)
    print(
        f"reactivate_ken_ht_ev: unarchived {n_books} book(s), "
        f"deleted {n_bets} stale pending bet(s)"
    )


if __name__ == "__main__":
    asyncio.run(_main())

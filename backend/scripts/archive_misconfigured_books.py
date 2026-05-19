"""Archive simulated_books whose signal's settle_market is not 1X2.

Phase A of paper-trading-realism PRD. Background:

    place_bets_for_books was originally hard-wired to FT 1X2 odds lookup.
    GS-KEN-HT-EV — which trades HT Asian Handicap — was nonetheless being
    matched because its value_json carries 'home'/'away' selections, so the
    runner produced bets with wrong-market entry_odds and settled them with
    wrong-market FT 1X2 outcomes. Phase A adds a gate in place_bets_for_books
    so no NEW misconfigured bets land; this script handles the EXISTING
    Books — flips their archived_at so they stop showing up in the catalog
    and in multi-curve ROI comparisons.

The stale simulated_bets rows on those Books are intentionally NOT touched
(PRD invariant: 旧的 simulated_bets 行不会被改写). Phase B's AH settlement +
a follow-up backfill script can recompute them once the AH path is live.

Usage:
    cd backend && .venv/bin/python -m scripts.archive_misconfigured_books

Idempotent: re-running affects 0 rows once misconfigured Books are archived.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import aiosqlite

from database import _db_path
from services.paper_trading import SUPPORTED_SETTLE_MARKETS
from services.signals import REGISTERED


async def archive_misconfigured_books(db: aiosqlite.Connection) -> int:
    """Archive every non-archived simulated_books row bound to a signal whose
    settle_market is not handled by the current settlement dispatcher.
    Returns the number of newly-archived rows."""
    misconfigured = [
        (s.signal_type, s.signal_version)
        for s in REGISTERED
        if s.settle_market not in SUPPORTED_SETTLE_MARKETS
    ]
    if not misconfigured:
        return 0

    now_iso = datetime.now(timezone.utc).isoformat()
    total = 0
    for signal_type, signal_version in misconfigured:
        res = await db.execute(
            """UPDATE simulated_books
                  SET archived_at = ?
                WHERE archived_at IS NULL
                  AND signal_type = ?
                  AND signal_version = ?""",
            (now_iso, signal_type, signal_version),
        )
        total += res.rowcount or 0
    if total:
        await db.commit()
    return total


async def _main() -> None:
    async with aiosqlite.connect(_db_path()) as db:
        db.row_factory = aiosqlite.Row
        archived = await archive_misconfigured_books(db)
    print(f"archive_misconfigured_books: archived {archived} simulated_books row(s)")


if __name__ == "__main__":
    asyncio.run(_main())

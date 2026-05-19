"""Phase B (paper-trading-realism PRD) — scripts.reactivate_ken_ht_ev.

Verifies the reactivation script:
  • unarchives all KEN-HT-EV books
  • deletes only the **stale, pending, wrong-market** KEN-HT-EV bets
    (market_id IS NULL or =6, outcome IS NULL)
  • preserves: settled KEN-HT-EV bets, correct AH (market_id=51) bets,
    and bets from any other signal
  • is idempotent (second run is a no-op)
"""
from __future__ import annotations

import aiosqlite
import pytest


NOW = "2026-05-19T10:00:00"
KICKOFF_FUTURE = "2026-05-20T15:00:00"


async def _seed_fixture(db_path: str, fixture_id: int = 10, *, status: str = "NS",
                         score_home: int | None = None, score_away: int | None = None):
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """INSERT INTO fixtures (id, competition_id, competition_name,
               home_team, away_team, kickoff_utc, status, score_home, score_away,
               fetched_at, updated_at)
               VALUES (?, 100, 'L', 'A', 'B', ?, ?, ?, ?, ?, ?)""",
            (fixture_id, KICKOFF_FUTURE, status, score_home, score_away, NOW, NOW),
        )
        await db.commit()


async def _seed_book(
    db_path: str, *, name: str, signal_type: str, archived: bool = False,
) -> int:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """INSERT INTO simulated_books
                 (user_id, name, signal_type, signal_version,
                  conditions_json, starting_units, match_scope,
                  created_at, archived_at)
               VALUES (0, ?, ?, 'v1.0', '{}', 100.0, 'all', ?, ?)""",
            (name, signal_type, NOW, NOW if archived else None),
        )
        await db.commit()
        return cur.lastrowid


async def _seed_bet(
    db_path: str, *, book_id: int, fixture_id: int, signal_type: str,
    market_id: int | None, ah_line: float | None, selection: str,
    outcome: str | None = None, pnl_units: float | None = None,
):
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """INSERT INTO simulated_bets
                 (book_id, book_type, user_id, fixture_id, market_id, ah_line, selection,
                  stake_units, entry_odds, entry_at, entry_waypoint,
                  signal_type, signal_version, outcome, pnl_units, settled_at)
               VALUES (?, 'book_x', 0, ?, ?, ?, ?, 1.0, 2.0, ?, 'kickoff',
                       ?, 'v1.0', ?, ?, ?)""",
            (book_id, fixture_id, market_id, ah_line, selection,
             NOW, signal_type, outcome, pnl_units,
             NOW if outcome is not None else None),
        )
        await db.commit()


@pytest.mark.asyncio
async def test_reactivate_unarchives_ken_book_and_deletes_stale_pending_bets(tmp_path):
    db_path = str(tmp_path / "test.db")
    import database, importlib
    importlib.reload(database)
    await database.init_db()

    await _seed_fixture(db_path, fixture_id=10)
    ken_book = await _seed_book(
        db_path, name="House-GS-KEN-HT-EV", signal_type="GS-KEN-HT-EV", archived=True,
    )
    await _seed_bet(
        db_path, book_id=ken_book, fixture_id=10, signal_type="GS-KEN-HT-EV",
        market_id=6, ah_line=None, selection="home",
    )

    from scripts.reactivate_ken_ht_ev import reactivate_ken_ht_ev
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        n_books, n_bets = await reactivate_ken_ht_ev(db)
        async with db.execute(
            "SELECT archived_at FROM simulated_books WHERE id=?", (ken_book,),
        ) as cur:
            book = dict(await cur.fetchone())
        async with db.execute("SELECT COUNT(*) AS n FROM simulated_bets") as cur:
            bet_count = (await cur.fetchone())["n"]
    assert n_books == 1
    assert n_bets  == 1
    assert book["archived_at"] is None
    assert bet_count == 0


@pytest.mark.asyncio
async def test_reactivate_preserves_correct_ah_bets_and_settled_bets(tmp_path):
    db_path = str(tmp_path / "test.db")
    import database, importlib
    importlib.reload(database)
    await database.init_db()

    await _seed_fixture(db_path, fixture_id=10)
    await _seed_fixture(db_path, fixture_id=11, status="FT", score_home=1, score_away=0)
    ken_book = await _seed_book(
        db_path, name="House-GS-KEN-HT-EV", signal_type="GS-KEN-HT-EV", archived=True,
    )
    # Correct AH pending bet — KEEP.
    await _seed_bet(
        db_path, book_id=ken_book, fixture_id=10, signal_type="GS-KEN-HT-EV",
        market_id=51, ah_line=-0.5, selection="home",
    )
    # Settled KEN-HT-EV bet on a past fixture — KEEP (history preserved).
    await _seed_bet(
        db_path, book_id=ken_book, fixture_id=11, signal_type="GS-KEN-HT-EV",
        market_id=6, ah_line=None, selection="home",
        outcome="win", pnl_units=1.0,
    )

    from scripts.reactivate_ken_ht_ev import reactivate_ken_ht_ev
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        await reactivate_ken_ht_ev(db)
        async with db.execute(
            "SELECT fixture_id, market_id, outcome FROM simulated_bets ORDER BY fixture_id"
        ) as cur:
            bets = [dict(r) for r in await cur.fetchall()]
    assert len(bets) == 2
    ah_pending = next(b for b in bets if b["fixture_id"] == 10)
    assert ah_pending["market_id"] == 51 and ah_pending["outcome"] is None
    settled = next(b for b in bets if b["fixture_id"] == 11)
    assert settled["outcome"] == "win"


@pytest.mark.asyncio
async def test_reactivate_does_not_touch_other_signals(tmp_path):
    db_path = str(tmp_path / "test.db")
    import database, importlib
    importlib.reload(database)
    await database.init_db()

    await _seed_fixture(db_path, fixture_id=10)
    misp_book = await _seed_book(
        db_path, name="House-GS-Mispricing", signal_type="GS-Mispricing", archived=False,
    )
    await _seed_bet(
        db_path, book_id=misp_book, fixture_id=10, signal_type="GS-Mispricing",
        market_id=6, ah_line=None, selection="home",
    )

    from scripts.reactivate_ken_ht_ev import reactivate_ken_ht_ev
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        n_books, n_bets = await reactivate_ken_ht_ev(db)
        async with db.execute("SELECT COUNT(*) AS n FROM simulated_bets") as cur:
            bet_count = (await cur.fetchone())["n"]
    assert n_books == 0
    assert n_bets  == 0
    assert bet_count == 1  # Mispricing bet untouched


@pytest.mark.asyncio
async def test_reactivate_is_idempotent(tmp_path):
    db_path = str(tmp_path / "test.db")
    import database, importlib
    importlib.reload(database)
    await database.init_db()

    await _seed_fixture(db_path, fixture_id=10)
    ken_book = await _seed_book(
        db_path, name="House-GS-KEN-HT-EV", signal_type="GS-KEN-HT-EV", archived=True,
    )
    await _seed_bet(
        db_path, book_id=ken_book, fixture_id=10, signal_type="GS-KEN-HT-EV",
        market_id=6, ah_line=None, selection="home",
    )

    from scripts.reactivate_ken_ht_ev import reactivate_ken_ht_ev
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        first  = await reactivate_ken_ht_ev(db)
        second = await reactivate_ken_ht_ev(db)
    assert first  == (1, 1)
    assert second == (0, 0)

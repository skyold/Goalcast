"""Phase A (paper-trading-realism PRD) — settle_market gating + archive script.

Covers:
  • BaseSignal.settle_market default = (6, '1X2')
  • Each concrete signal carries the correct settle_market tuple
  • place_bets_for_books SKIPS a book whose signal.settle_market != (6, '1X2')
    while still inserting for a 1X2 signal (positive control)
  • scripts.archive_misconfigured_books archives non-1X2 books, leaves 1X2
    books and pre-existing simulated_bets rows untouched, and is idempotent.
"""
from __future__ import annotations

import json

import aiosqlite
import pytest


NOW = "2026-05-19T10:00:00"
KICKOFF_FUTURE = "2026-05-20T15:00:00"


# ---------- BaseSignal / REGISTERED metadata ----------

def test_base_signal_default_settle_market_is_1x2():
    from services.signals.base import BaseSignal
    assert BaseSignal.settle_market == (6, "1X2")


def test_registered_signals_carry_expected_settle_market():
    """3 公开 1X2 信号继承默认 (6,'1X2');KEN-HT-EV 覆盖为 (51,'AH_0_HT')."""
    from services.signals import REGISTERED
    by_type = {s.signal_type: s.settle_market for s in REGISTERED}
    assert by_type["GS-Mispricing"]  == (6, "1X2")
    assert by_type["GS-LineMove"]    == (6, "1X2")
    assert by_type["GS-SharpSquare"] == (6, "1X2")
    assert by_type["GS-KEN-HT-EV"]   == (51, "AH_0_HT")


# ---------- shared seeders ----------

async def _seed_fixture_and_odds(db_path: str, fixture_id: int = 10, selection: str = "home"):
    """One NS fixture + Pinnacle 1X2 historical_odds at waypoint='kickoff'."""
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """INSERT INTO fixtures (id, competition_id, competition_name,
               home_team, away_team, kickoff_utc, status, fetched_at, updated_at)
               VALUES (?, 100, 'L', 'A', 'B', ?, 'NS', ?, ?)""",
            (fixture_id, KICKOFF_FUTURE, NOW, NOW),
        )
        for outcome in ("home", "draw", "away"):
            await db.execute(
                """INSERT INTO historical_odds
                     (fixture_id, bookmaker_id, market_id, outcome, waypoint, odds, captured_at)
                   VALUES (?, 1, 6, ?, 'kickoff', ?, ?)""",
                (fixture_id, outcome, 2.10 if outcome == selection else 3.40, NOW),
            )
        await db.commit()


async def _seed_signal_row(
    db_path: str,
    *,
    fixture_id: int,
    signal_type: str,
    value_json: dict,
    signal_version: str = "v1.0",
    scope: str = "public",
    strength: float = 0.5,
):
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """INSERT INTO signals_snapshot
                 (fixture_id, signal_type, signal_version, waypoint,
                  scope, value_json, strength, captured_at)
               VALUES (?, ?, ?, 'kickoff', ?, ?, ?, ?)""",
            (fixture_id, signal_type, signal_version, scope,
             json.dumps(value_json), strength, NOW),
        )
        await db.commit()


async def _seed_book(
    db_path: str,
    *,
    name: str,
    signal_type: str,
    user_id: int = 0,
    signal_version: str = "v1.0",
    conditions: dict | None = None,
    match_scope: str = "all",
    archived: bool = False,
) -> int:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """INSERT INTO simulated_books
                 (user_id, name, signal_type, signal_version,
                  conditions_json, starting_units, match_scope,
                  created_at, archived_at)
               VALUES (?, ?, ?, ?, ?, 100.0, ?, ?, ?)""",
            (user_id, name, signal_type, signal_version,
             json.dumps(conditions or {}), match_scope, NOW,
             NOW if archived else None),
        )
        await db.commit()
        return cur.lastrowid


# ---------- place_bets_for_books gate ----------

@pytest.mark.asyncio
async def test_place_bets_skips_book_whose_signal_is_not_1x2(tmp_path):
    """Even with a valid signals_snapshot row + matching Pinnacle 1X2 odds,
    a Book bound to GS-KEN-HT-EV (settle_market != 1X2) must NOT produce any
    new simulated_bets row — that's Phase A's safety gate."""
    db_path = str(tmp_path / "test.db")
    import database, importlib
    importlib.reload(database)
    await database.init_db()

    await _seed_fixture_and_odds(db_path, fixture_id=10, selection="home")
    await _seed_signal_row(
        db_path, fixture_id=10, signal_type="GS-KEN-HT-EV",
        value_json={"selection": "home"},  # 'home' would otherwise pass the 1X2 gate
    )
    await _seed_book(db_path, name="House-GS-KEN-HT-EV", signal_type="GS-KEN-HT-EV")

    from services.paper_trading import place_bets_for_books
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        inserted = await place_bets_for_books(db)
        async with db.execute("SELECT COUNT(*) AS n FROM simulated_bets") as cur:
            n = (await cur.fetchone())["n"]
    assert inserted == 0
    assert n == 0


@pytest.mark.asyncio
async def test_place_bets_still_inserts_for_1x2_book(tmp_path):
    """Positive control: a 1X2 signal Book on the same fixture DOES insert,
    proving the gate above isn't accidentally blocking everything."""
    db_path = str(tmp_path / "test.db")
    import database, importlib
    importlib.reload(database)
    await database.init_db()

    await _seed_fixture_and_odds(db_path, fixture_id=10, selection="home")
    await _seed_signal_row(
        db_path, fixture_id=10, signal_type="GS-Mispricing",
        value_json={"selection": "home", "delta_pct": 7.0},
    )
    await _seed_book(db_path, name="House-GS-Mispricing", signal_type="GS-Mispricing")

    from services.paper_trading import place_bets_for_books
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        inserted = await place_bets_for_books(db)
        async with db.execute("SELECT COUNT(*) AS n FROM simulated_bets") as cur:
            n = (await cur.fetchone())["n"]
    assert inserted == 1
    assert n == 1


# ---------- archive_misconfigured_books script ----------

@pytest.mark.asyncio
async def test_archive_misconfigured_books_archives_non_1x2(tmp_path):
    db_path = str(tmp_path / "test.db")
    import database, importlib
    importlib.reload(database)
    await database.init_db()

    ken_id  = await _seed_book(db_path, name="House-GS-KEN-HT-EV", signal_type="GS-KEN-HT-EV")
    misp_id = await _seed_book(db_path, name="House-GS-Mispricing", signal_type="GS-Mispricing")

    from scripts.archive_misconfigured_books import archive_misconfigured_books
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        archived = await archive_misconfigured_books(db)
        async with db.execute(
            "SELECT id, archived_at FROM simulated_books ORDER BY id"
        ) as cur:
            rows = [dict(r) for r in await cur.fetchall()]
    assert archived == 1
    rows_by_id = {r["id"]: r for r in rows}
    assert rows_by_id[ken_id]["archived_at"] is not None
    assert rows_by_id[misp_id]["archived_at"] is None


@pytest.mark.asyncio
async def test_archive_misconfigured_books_is_idempotent(tmp_path):
    db_path = str(tmp_path / "test.db")
    import database, importlib
    importlib.reload(database)
    await database.init_db()

    await _seed_book(db_path, name="House-GS-KEN-HT-EV", signal_type="GS-KEN-HT-EV")

    from scripts.archive_misconfigured_books import archive_misconfigured_books
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        first  = await archive_misconfigured_books(db)
        second = await archive_misconfigured_books(db)
    assert first == 1
    assert second == 0


@pytest.mark.asyncio
async def test_archive_misconfigured_books_leaves_existing_bets_alone(tmp_path):
    """PRD invariant: 旧的 simulated_bets 行不会被改写 — 只动 simulated_books."""
    db_path = str(tmp_path / "test.db")
    import database, importlib
    importlib.reload(database)
    await database.init_db()

    ken_id = await _seed_book(db_path, name="House-GS-KEN-HT-EV", signal_type="GS-KEN-HT-EV")
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """INSERT INTO fixtures (id, competition_id, competition_name,
               home_team, away_team, kickoff_utc, status, score_home, score_away,
               fetched_at, updated_at)
               VALUES (10, 100, 'L', 'A', 'B', ?, 'FT', 1, 0, ?, ?)""",
            (KICKOFF_FUTURE, NOW, NOW),
        )
        await db.execute(
            """INSERT INTO simulated_bets
                 (book_id, book_type, user_id, fixture_id, selection,
                  stake_units, entry_odds, entry_at, entry_waypoint,
                  signal_type, signal_version, outcome, pnl_units, settled_at)
               VALUES (?, 'book_ken', 0, 10, 'home', 1.0, 2.10, ?, 'kickoff',
                       'GS-KEN-HT-EV', 'v1.0', 'win', 1.10, ?)""",
            (ken_id, NOW, NOW),
        )
        await db.commit()

    from scripts.archive_misconfigured_books import archive_misconfigured_books
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        await archive_misconfigured_books(db)
        async with db.execute(
            "SELECT outcome, pnl_units FROM simulated_bets WHERE book_id=?", (ken_id,),
        ) as cur:
            bet = dict(await cur.fetchone())
    assert bet["outcome"] == "win"
    assert bet["pnl_units"] == pytest.approx(1.10, abs=0.001)

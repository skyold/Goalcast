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
    assert by_type["GS-KEN-HT-EV"]   == (51, "FT_AH")


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


# ---------- place_bets_for_books dispatch (1X2 + FT_AH) ----------

@pytest.mark.asyncio
async def test_place_bets_skips_ah_book_when_ah_odds_missing(tmp_path):
    """Phase B: KEN-HT-EV is supported, but place_bets still skips a candidate
    when the historical_odds row for the constructed AH outcome is missing
    (e.g. signal fires before the AH odds are synced for that waypoint)."""
    db_path = str(tmp_path / "test.db")
    import database, importlib
    importlib.reload(database)
    await database.init_db()

    await _seed_fixture_and_odds(db_path, fixture_id=10, selection="home")
    await _seed_signal_row(
        db_path, fixture_id=10, signal_type="GS-KEN-HT-EV",
        value_json={"selection": "home", "ah_line": -0.5},
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
    """1X2 path still works; new market_id=6 + ah_line=NULL columns are populated."""
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
        async with db.execute(
            "SELECT market_id, ah_line, selection FROM simulated_bets"
        ) as cur:
            bet = dict(await cur.fetchone())
    assert inserted == 1
    assert bet["market_id"] == 6
    assert bet["ah_line"]   is None
    assert bet["selection"] == "home"


@pytest.mark.asyncio
async def test_ah_settle_bets_full_pipeline(tmp_path):
    """End-to-end: KEN-HT-EV book auto-places an AH bet, fixture goes FT,
    settle_bets dispatches to the AH path and writes the AH outcome/pnl/CLV.

    Scenario:  home-perspective ah_line=-0.5 (home -0.5), side='home',
               entry_odds=1.92, FT score 1-0.
       → bet's side-perspective line = -0.5
       → AH grading: home -0.5 + score 1-0 → 'win'
       → pnl = +1.0 * (1.92 - 1) = +0.92
    """
    db_path = str(tmp_path / "test.db")
    import database, importlib
    importlib.reload(database)
    await database.init_db()

    await _seed_fixture_and_odds(db_path, fixture_id=10, selection="home")
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """INSERT INTO historical_odds
                 (fixture_id, bookmaker_id, market_id, outcome, waypoint, odds, captured_at)
               VALUES (10, 1, 51, 'home_m05', 'kickoff', 1.92, ?)""",
            (NOW,),
        )
        await db.commit()
    await _seed_signal_row(
        db_path, fixture_id=10, signal_type="GS-KEN-HT-EV",
        value_json={"selection": "home", "ah_line": -0.5},
    )
    await _seed_book(db_path, name="House-GS-KEN-HT-EV", signal_type="GS-KEN-HT-EV")

    from services.paper_trading import place_bets_for_books, settle_bets
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        await place_bets_for_books(db)
        await db.execute(
            "UPDATE fixtures SET status='FT', score_home=1, score_away=0 WHERE id=10"
        )
        await db.commit()
        settled = await settle_bets(db)
        async with db.execute(
            "SELECT market_id, ah_line, selection, outcome, pnl_units, closing_odds "
            "FROM simulated_bets WHERE fixture_id=10"
        ) as cur:
            bet = dict(await cur.fetchone())
    assert settled == 1
    assert bet["market_id"]    == 51
    assert bet["ah_line"]      == pytest.approx(-0.5)
    assert bet["selection"]    == "home"
    assert bet["outcome"]      == "win"
    assert bet["pnl_units"]    == pytest.approx(1.0 * (1.92 - 1), abs=1e-9)
    assert bet["closing_odds"] == pytest.approx(1.92, abs=1e-9)


@pytest.mark.asyncio
async def test_ah_settle_bets_push_at_handicap_zero_draw(tmp_path):
    """AH line=0 home, FT score 0-0 → push, pnl=0, outcome='push'."""
    db_path = str(tmp_path / "test.db")
    import database, importlib
    importlib.reload(database)
    await database.init_db()

    await _seed_fixture_and_odds(db_path, fixture_id=10, selection="home")
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """INSERT INTO historical_odds
                 (fixture_id, bookmaker_id, market_id, outcome, waypoint, odds, captured_at)
               VALUES (10, 1, 51, 'home_0', 'kickoff', 1.95, ?)""",
            (NOW,),
        )
        await db.commit()
    await _seed_signal_row(
        db_path, fixture_id=10, signal_type="GS-KEN-HT-EV",
        value_json={"selection": "home", "ah_line": 0.0},
    )
    await _seed_book(db_path, name="House-GS-KEN-HT-EV", signal_type="GS-KEN-HT-EV")

    from services.paper_trading import place_bets_for_books, settle_bets
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        await place_bets_for_books(db)
        await db.execute(
            "UPDATE fixtures SET status='FT', score_home=0, score_away=0 WHERE id=10"
        )
        await db.commit()
        await settle_bets(db)
        async with db.execute(
            "SELECT outcome, pnl_units FROM simulated_bets WHERE fixture_id=10"
        ) as cur:
            bet = dict(await cur.fetchone())
    assert bet["outcome"]   == "push"
    assert bet["pnl_units"] == pytest.approx(0.0, abs=1e-9)


@pytest.mark.asyncio
async def test_place_bets_inserts_ah_bet_for_ken_ht_ev_book(tmp_path):
    """Phase B happy path: AH odds present → KEN-HT-EV bet lands with
    market_id=51, side-perspective ah_line, and the AH-market entry_odds.
    Signal output ah_line is from home perspective; for side='away' the
    bet's ah_line is flipped (away +0.5 ↔ home -0.5)."""
    db_path = str(tmp_path / "test.db")
    import database, importlib
    importlib.reload(database)
    await database.init_db()

    # Fixture (NS) + 1X2 odds (not used here, but _seed_fixture_and_odds is the
    # shared seeder) + AH odds for the away_p05 line at market_id=51.
    await _seed_fixture_and_odds(db_path, fixture_id=10, selection="home")
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """INSERT INTO historical_odds
                 (fixture_id, bookmaker_id, market_id, outcome, waypoint, odds, captured_at)
               VALUES (10, 1, 51, 'away_p05', 'kickoff', 1.92, ?)""",
            (NOW,),
        )
        await db.commit()
    # KEN-HT-EV signal: home-perspective ah_line=-0.5, signal picks 'away'
    # → bet's side-perspective line flips sign to +0.5 → outcome 'away_p05'.
    await _seed_signal_row(
        db_path, fixture_id=10, signal_type="GS-KEN-HT-EV",
        value_json={"selection": "away", "ah_line": -0.5},
    )
    await _seed_book(db_path, name="House-GS-KEN-HT-EV", signal_type="GS-KEN-HT-EV")

    from services.paper_trading import place_bets_for_books
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        inserted = await place_bets_for_books(db)
        async with db.execute(
            "SELECT market_id, ah_line, selection, entry_odds, signal_type FROM simulated_bets"
        ) as cur:
            bet = dict(await cur.fetchone())
    assert inserted == 1
    assert bet["market_id"]   == 51
    assert bet["ah_line"]     == pytest.approx(0.5)
    assert bet["selection"]   == "away"
    assert bet["entry_odds"]  == pytest.approx(1.92)
    assert bet["signal_type"] == "GS-KEN-HT-EV"


# ---------- archive_misconfigured_books script (Phase B: KEN-HT-EV is now supported) ----------

@pytest.mark.asyncio
async def test_archive_misconfigured_books_noop_when_all_signals_supported(tmp_path):
    """Phase B reality: all 4 REGISTERED signals' settle_markets are in
    SUPPORTED_SETTLE_MARKETS, so the archive script is a no-op against the
    current registry. KEN-HT-EV stays unarchived because it's now supported."""
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
    assert archived == 0
    rows_by_id = {r["id"]: r for r in rows}
    assert rows_by_id[ken_id]["archived_at"]  is None
    assert rows_by_id[misp_id]["archived_at"] is None


@pytest.mark.asyncio
async def test_archive_misconfigured_books_archives_unsupported_market(tmp_path, monkeypatch):
    """The script's MECHANISM still archives when a misconfigured signal exists,
    proved by monkeypatching SUPPORTED_SETTLE_MARKETS to exclude AH —
    KEN-HT-EV book should then be flagged and archived."""
    db_path = str(tmp_path / "test.db")
    import database, importlib
    importlib.reload(database)
    await database.init_db()

    ken_id = await _seed_book(db_path, name="House-GS-KEN-HT-EV", signal_type="GS-KEN-HT-EV")

    import scripts.archive_misconfigured_books as mod
    monkeypatch.setattr(mod, "SUPPORTED_SETTLE_MARKETS", frozenset({(6, "1X2")}))

    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        first  = await mod.archive_misconfigured_books(db)
        second = await mod.archive_misconfigured_books(db)
        async with db.execute(
            "SELECT archived_at FROM simulated_books WHERE id=?", (ken_id,),
        ) as cur:
            row = dict(await cur.fetchone())
    assert first  == 1
    assert second == 0  # idempotent
    assert row["archived_at"] is not None

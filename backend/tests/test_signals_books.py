"""Phase 4a tests — simulated_books schema, House Book bootstrap, legacy
migration, and per-book bet placement.

Pins three invariants:
1. bootstrap_books is idempotent: re-running yields no new rows / no
   double-migration.
2. Legacy `simulated_bets.book_type='house_5pct'` rows get backfilled with
   the corresponding new `book_id`.
3. place_bets_for_books produces bets keyed by book_id with proper
   dedupe — keystone for the PRD "House Book 行为平迁 ±5%" success metric.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import aiosqlite
import pytest


NOW = datetime.now(timezone.utc).isoformat()


@pytest.fixture
async def db_path(tmp_path, monkeypatch):
    monkeypatch.setenv("GOALCAST_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("GOALCAST_JWT_SECRET", "test-secret-not-prod")
    import importlib, database
    importlib.reload(database)
    await database.init_db()
    return str(tmp_path / "test.db")


# --- schema --------------------------------------------------------------

@pytest.mark.asyncio
async def test_simulated_books_table_exists(db_path):
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='simulated_books'"
        ) as cur:
            assert (await cur.fetchone()) is not None


@pytest.mark.asyncio
async def test_simulated_bets_has_book_id_column(db_path):
    async with aiosqlite.connect(db_path) as db:
        cur = await db.execute("PRAGMA table_info(simulated_bets)")
        cols = {r[1] for r in await cur.fetchall()}
    assert "book_id" in cols


@pytest.mark.asyncio
async def test_book_id_unique_index_exists(db_path):
    """Partial UNIQUE INDEX on (book_id, fixture_id, selection) WHERE book_id IS NOT NULL."""
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            "SELECT sql FROM sqlite_master WHERE type='index' AND name='idx_sb_book_fixsel'"
        ) as cur:
            row = await cur.fetchone()
    assert row is not None
    assert "book_id IS NOT NULL" in row[0]


# --- bootstrap_books -----------------------------------------------------

@pytest.mark.asyncio
async def test_bootstrap_creates_one_house_book_per_registered_signal(db_path):
    from services.signals.books import bootstrap_books
    from services.signals import REGISTERED
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        new_books, _ = await bootstrap_books(db)
        async with db.execute(
            """SELECT name, signal_type FROM simulated_books
               WHERE user_id=0 AND name LIKE 'House-GS-%'
               AND name NOT LIKE 'House-GS-Mispricing-%pct'"""
        ) as cur:
            rows = [dict(r) for r in await cur.fetchall()]
    by_signal = {r["signal_type"]: r["name"] for r in rows}
    for sig in REGISTERED:
        assert sig.signal_type in by_signal
        assert by_signal[sig.signal_type] == f"House-{sig.signal_type}"
    assert new_books >= len(REGISTERED)


@pytest.mark.asyncio
async def test_bootstrap_is_idempotent(db_path):
    from services.signals.books import bootstrap_books
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        await bootstrap_books(db)
        async with db.execute("SELECT COUNT(*) AS n FROM simulated_books") as cur:
            n1 = (await cur.fetchone())["n"]
        # Re-run.
        await bootstrap_books(db)
        async with db.execute("SELECT COUNT(*) AS n FROM simulated_books") as cur:
            n2 = (await cur.fetchone())["n"]
    assert n1 == n2


@pytest.mark.asyncio
async def test_house_gs_mispricing_default_conditions_inherit_5pct(db_path):
    from services.signals.books import bootstrap_books
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        await bootstrap_books(db)
        async with db.execute(
            "SELECT conditions_json FROM simulated_books WHERE name='House-GS-Mispricing'"
        ) as cur:
            row = await cur.fetchone()
    assert row is not None
    cond = json.loads(row["conditions_json"])
    # PRD § Migration step 5: default conditions encode the legacy 5pct band.
    assert cond == {"filters": [{"path": "value.delta_pct", "op": ">", "value": 5}]}


@pytest.mark.asyncio
async def test_house_books_use_all_match_scope(db_path):
    """Invariant: House Books (user_id=0) are PRD-forced to match_scope='all'."""
    from services.signals.books import bootstrap_books
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        await bootstrap_books(db)
        async with db.execute(
            "SELECT match_scope FROM simulated_books WHERE user_id=0"
        ) as cur:
            scopes = {r["match_scope"] for r in await cur.fetchall()}
    assert scopes == {"all"}


# --- migrate_legacy_book_types ------------------------------------------

@pytest.mark.asyncio
async def test_legacy_book_types_get_backfilled(db_path):
    """Pre-existing simulated_bets rows with book_type='house_5pct' (etc.) get
    their book_id pointed at the new House-GS-Mispricing-5pct row."""
    async with aiosqlite.connect(db_path) as db:
        # Seed legacy rows BEFORE running bootstrap.
        await db.execute(
            """INSERT INTO fixtures (id, competition_id, competition_name, home_team, away_team,
               kickoff_utc, status, fetched_at, updated_at)
               VALUES (200, 1, 'L', 'X', 'Y', ?, 'NS', ?, ?)""",
            (NOW, NOW, NOW),
        )
        await db.executemany(
            """INSERT INTO simulated_bets
                 (book_type, user_id, fixture_id, selection,
                  stake_units, entry_odds, entry_at, entry_waypoint,
                  signal_type, signal_version)
               VALUES (?, 0, ?, ?, 1.0, 2.10, ?, 'kickoff', 'GS-Mispricing', 'v1.0')""",
            [
                ("house_3pct", 200, "home", NOW),
                ("house_5pct", 200, "draw", NOW),
                ("house_7pct", 200, "away", NOW),
            ],
        )
        await db.commit()
    from services.signals.books import bootstrap_books
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        _, rows_updated = await bootstrap_books(db)
        async with db.execute(
            """SELECT book_type, book_id FROM simulated_bets
               WHERE fixture_id=200 ORDER BY book_type"""
        ) as cur:
            rows = [dict(r) for r in await cur.fetchall()]
    assert rows_updated == 3
    for r in rows:
        assert r["book_id"] is not None, f"book_type={r['book_type']} did not get backfilled"


@pytest.mark.asyncio
async def test_migrate_is_idempotent(db_path):
    """Re-running bootstrap with no new legacy rows yields 0 backfills."""
    from services.signals.books import bootstrap_books
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        await bootstrap_books(db)
        _, rows_updated_2 = await bootstrap_books(db)
    assert rows_updated_2 == 0


# --- place_bets_for_books ----------------------------------------------

@pytest.mark.asyncio
async def test_place_bets_for_books_dedupes_and_uses_book_id(db_path):
    """Seed a signal that satisfies House-GS-Mispricing's default conditions
    (delta_pct > 5). Run place_bets_for_books → INSERTs bets keyed by book_id.
    Re-run → 0 new (dedupe via UNIQUE partial index)."""
    from services.signals.books import bootstrap_books
    from services.paper_trading import place_bets_for_books
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        await bootstrap_books(db)
        await db.execute(
            """INSERT INTO fixtures (id, competition_id, competition_name,
               home_team, away_team, kickoff_utc, status, fetched_at, updated_at)
               VALUES (300, 1, 'L', 'A', 'B', ?, 'NS', ?, ?)""",
            (NOW, NOW, NOW),
        )
        for outcome, odds in (("home", 2.10), ("draw", 3.40), ("away", 3.80)):
            await db.execute(
                """INSERT INTO historical_odds
                   (fixture_id, bookmaker_id, market_id, outcome, waypoint, odds, captured_at)
                   VALUES (300, 1, 6, ?, 'kickoff', ?, ?)""",
                (outcome, odds, NOW),
            )
        await db.execute(
            """INSERT INTO signals_snapshot
                 (fixture_id, signal_type, signal_version, waypoint, scope,
                  value_json, strength, captured_at)
               VALUES (300, 'GS-Mispricing', 'v1.0', 'kickoff', 'public', ?, 0.8, ?)""",
            (json.dumps({"delta_pct": 8.0, "selection": "home"}), NOW),
        )
        await db.commit()

        n1 = await place_bets_for_books(db)
        n2 = await place_bets_for_books(db)
        async with db.execute(
            """SELECT book_id, book_type, selection FROM simulated_bets
               WHERE fixture_id=300"""
        ) as cur:
            bets = [dict(r) for r in await cur.fetchall()]

    # delta_pct=8 qualifies: House-GS-Mispricing (>5) + 3pct + 5pct + 7pct = 4 bets.
    assert n1 >= 1
    assert n2 == 0  # second run dedupes
    for b in bets:
        assert b["book_id"] is not None


@pytest.mark.asyncio
async def test_place_bets_skips_when_signal_below_threshold(db_path):
    """delta_pct=3 → House-GS-Mispricing default (>5) skips; 3pct band (>3)
    skips too (exclusive); only sub-3 bands (none) could qualify → 0 bets."""
    from services.signals.books import bootstrap_books
    from services.paper_trading import place_bets_for_books
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        await bootstrap_books(db)
        await db.execute(
            """INSERT INTO fixtures (id, competition_id, competition_name,
               home_team, away_team, kickoff_utc, status, fetched_at, updated_at)
               VALUES (301, 1, 'L', 'A', 'B', ?, 'NS', ?, ?)""",
            (NOW, NOW, NOW),
        )
        for outcome, odds in (("home", 2.10), ("draw", 3.40), ("away", 3.80)):
            await db.execute(
                """INSERT INTO historical_odds
                   (fixture_id, bookmaker_id, market_id, outcome, waypoint, odds, captured_at)
                   VALUES (301, 1, 6, ?, 'kickoff', ?, ?)""",
                (outcome, odds, NOW),
            )
        await db.execute(
            """INSERT INTO signals_snapshot
                 (fixture_id, signal_type, signal_version, waypoint, scope,
                  value_json, strength, captured_at)
               VALUES (301, 'GS-Mispricing', 'v1.0', 'kickoff', 'public', ?, 0.4, ?)""",
            (json.dumps({"delta_pct": 3.0, "selection": "home"}), NOW),
        )
        await db.commit()
        n = await place_bets_for_books(db)
        async with db.execute(
            "SELECT COUNT(*) AS n FROM simulated_bets WHERE fixture_id=301"
        ) as cur:
            count = (await cur.fetchone())["n"]
    assert n == 0
    assert count == 0


@pytest.mark.asyncio
async def test_place_bets_for_books_match_scope_my_leagues(db_path):
    """Personal Book with match_scope='my_leagues' only bets on fixtures whose
    competition_id is in the user's user_competition_prefs."""
    from services.signals.books import bootstrap_books
    from services.paper_trading import place_bets_for_books
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        await bootstrap_books(db)
        await db.execute("INSERT INTO users (id, email, password_hash) VALUES (5, 'u@x', 'h')")
        await db.execute("INSERT INTO user_competition_prefs (user_id, competition_id) VALUES (5, 100)")
        # User's Personal Book on GS-Mispricing, match_scope='my_leagues'.
        await db.execute(
            """INSERT INTO simulated_books
                 (user_id, name, signal_type, signal_version,
                  conditions_json, starting_units, match_scope, created_at)
               VALUES (5, 'mine-mispricing', 'GS-Mispricing', 'v1.0', '{}', 100.0, 'my_leagues', ?)""",
            (NOW,),
        )
        # Two fixtures: 400 in competition 100 (user's pref), 401 in competition 200 (not).
        for fid, cid in [(400, 100), (401, 200)]:
            await db.execute(
                """INSERT INTO fixtures (id, competition_id, competition_name,
                   home_team, away_team, kickoff_utc, status, fetched_at, updated_at)
                   VALUES (?, ?, 'L', 'A', 'B', ?, 'NS', ?, ?)""",
                (fid, cid, NOW, NOW, NOW),
            )
            for outcome, odds in (("home", 2.10), ("draw", 3.40), ("away", 3.80)):
                await db.execute(
                    """INSERT INTO historical_odds
                       (fixture_id, bookmaker_id, market_id, outcome, waypoint, odds, captured_at)
                       VALUES (?, 1, 6, ?, 'kickoff', ?, ?)""",
                    (fid, outcome, odds, NOW),
                )
            await db.execute(
                """INSERT INTO signals_snapshot
                     (fixture_id, signal_type, signal_version, waypoint, scope,
                      value_json, strength, captured_at)
                   VALUES (?, 'GS-Mispricing', 'v1.0', 'kickoff', 'public', ?, 0.8, ?)""",
                (fid, json.dumps({"delta_pct": 8.0, "selection": "home"}), NOW),
            )
        await db.commit()

        await place_bets_for_books(db)
        async with db.execute(
            "SELECT fixture_id FROM simulated_bets WHERE user_id=5"
        ) as cur:
            fids = {r["fixture_id"] for r in await cur.fetchall()}

    # Only fixture 400 (in user's preferred competition 100) gets a bet.
    assert 400 in fids
    assert 401 not in fids

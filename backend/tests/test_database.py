import pytest
import aiosqlite

@pytest.mark.asyncio
async def test_init_creates_all_tables(tmp_path, monkeypatch):
    monkeypatch.setenv("GOALCAST_DB_PATH", str(tmp_path / "test.db"))
    import importlib, database
    importlib.reload(database)

    await database.init_db()

    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        async with db.execute("SELECT name FROM sqlite_master WHERE type='table'") as cur:
            tables = {row[0] for row in await cur.fetchall()}

    assert "fixtures" in tables
    assert "odds_snapshots" in tables
    assert "sync_log" in tables

@pytest.mark.asyncio
async def test_new_tables_exist(tmp_path, monkeypatch):
    monkeypatch.setenv("GOALCAST_DB_PATH", str(tmp_path / "test.db"))
    import importlib, database
    importlib.reload(database)
    await database.init_db()
    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        cur = await db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        names = {row[0] for row in await cur.fetchall()}
    assert {"predictions", "team_form", "bookmaker_odds"}.issubset(names)

@pytest.mark.asyncio
async def test_fixtures_has_new_columns(tmp_path, monkeypatch):
    monkeypatch.setenv("GOALCAST_DB_PATH", str(tmp_path / "test.db"))
    import importlib, database
    importlib.reload(database)
    await database.init_db()
    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        cur = await db.execute("PRAGMA table_info(fixtures)")
        col_names = {row[1] for row in await cur.fetchall()}
    assert "predictability" in col_names
    assert "season_id" in col_names


# ---------- Phase B (paper-trading-realism) schema migrations ----------

@pytest.mark.asyncio
async def test_simulated_bets_has_market_id_and_ah_line(tmp_path, monkeypatch):
    """Phase B: simulated_bets gains market_id (which market the bet is on)
    and ah_line (signed AH handicap from side perspective; NULL for 1X2)."""
    monkeypatch.setenv("GOALCAST_DB_PATH", str(tmp_path / "test.db"))
    import importlib, database
    importlib.reload(database)
    await database.init_db()
    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        cur = await db.execute("PRAGMA table_info(simulated_bets)")
        cols = {row[1] for row in await cur.fetchall()}
    assert "market_id" in cols
    assert "ah_line"   in cols


@pytest.mark.asyncio
async def test_simulated_bets_has_market_aware_unique_index(tmp_path, monkeypatch):
    """The new UNIQUE index allows the same (book, fixture, selection) on different
    markets — defensive even though current per-book signal binding is 1:1 with market."""
    monkeypatch.setenv("GOALCAST_DB_PATH", str(tmp_path / "test.db"))
    import importlib, database
    importlib.reload(database)
    await database.init_db()
    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        cur = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='simulated_bets'"
        )
        idx_names = {row[0] for row in await cur.fetchall()}
    assert "idx_sb_book_market_fixsel" in idx_names


@pytest.mark.asyncio
async def test_simulated_bets_backfills_market_id_for_legacy_rows(tmp_path, monkeypatch):
    """Pre-migration rows (inserted before the market_id column existed) get
    backfilled to market_id=6 (FT 1X2) at init_db time. Simulates the
    real-world upgrade path on the running production DB."""
    monkeypatch.setenv("GOALCAST_DB_PATH", str(tmp_path / "test.db"))

    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        await db.execute("""
            CREATE TABLE simulated_bets (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                book_type       TEXT    NOT NULL,
                user_id         INTEGER NOT NULL DEFAULT 0,
                fixture_id      INTEGER NOT NULL,
                selection       TEXT    NOT NULL,
                stake_units     REAL    NOT NULL,
                entry_odds      REAL    NOT NULL,
                entry_at        TIMESTAMP NOT NULL,
                entry_waypoint  TEXT    NOT NULL,
                signal_type     TEXT,
                signal_version  TEXT,
                outcome         TEXT,
                pnl_units       REAL,
                settled_at      TIMESTAMP,
                closing_odds    REAL,
                UNIQUE (book_type, fixture_id, selection, user_id)
            )
        """)
        await db.execute(
            """INSERT INTO simulated_bets
                 (book_type, user_id, fixture_id, selection,
                  stake_units, entry_odds, entry_at, entry_waypoint,
                  signal_type, signal_version)
               VALUES ('legacy', 0, 1, 'home', 1.0, 2.0,
                       '2026-05-01T00:00:00', 'kickoff',
                       'GS-Mispricing', 'v1.0')"""
        )
        await db.commit()

    import importlib, database
    importlib.reload(database)
    await database.init_db()

    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT market_id, ah_line FROM simulated_bets") as cur:
            rows = [dict(r) for r in await cur.fetchall()]
    assert len(rows) == 1
    assert rows[0]["market_id"] == 6
    assert rows[0]["ah_line"]   is None

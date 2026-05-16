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

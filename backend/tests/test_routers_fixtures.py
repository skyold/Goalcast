import pytest
import aiosqlite
from httpx import AsyncClient, ASGITransport

@pytest.fixture
async def app_with_db(tmp_path, monkeypatch):
    monkeypatch.setenv("GOALCAST_DB_PATH", str(tmp_path / "test.db"))
    import importlib, database, main
    importlib.reload(database)
    await database.init_db()
    now = "2026-05-15T15:00:00"
    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        await db.execute(
            """INSERT INTO fixtures
               (id,competition_id,competition_name,home_team,away_team,
                kickoff_utc,status,fetched_at,updated_at)
               VALUES(1,101,'Premier League','Arsenal','Chelsea','2026-05-15T15:00:00','pre',?,?)""",
            (now, now),
        )
        await db.commit()
    importlib.reload(main)
    return main.app

@pytest.mark.asyncio
async def test_list_fixtures_requires_leagues(app_with_db):
    async with AsyncClient(transport=ASGITransport(app=app_with_db), base_url="http://test") as client:
        r = await client.get("/api/fixtures")
    assert r.status_code == 200
    assert r.json()["fixtures"] == []

@pytest.mark.asyncio
async def test_list_fixtures_returns_match(app_with_db):
    async with AsyncClient(transport=ASGITransport(app=app_with_db), base_url="http://test") as client:
        r = await client.get("/api/fixtures", params={"date": "2026-05-15", "leagues": "101"})
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert data["fixtures"][0]["home_team"] == "Arsenal"

@pytest.mark.asyncio
async def test_get_fixture_not_found(app_with_db):
    async with AsyncClient(transport=ASGITransport(app=app_with_db), base_url="http://test") as client:
        r = await client.get("/api/fixtures/999")
    assert r.status_code == 404

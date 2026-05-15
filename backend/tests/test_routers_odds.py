import pytest, aiosqlite
from httpx import AsyncClient, ASGITransport

@pytest.fixture
async def seeded_app(tmp_path, monkeypatch):
    monkeypatch.setenv("GOALCAST_DB_PATH", str(tmp_path / "test.db"))
    import importlib, database, main
    importlib.reload(database)
    await database.init_db()
    now = "2026-05-15T15:00:00"
    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        await db.execute(
            """INSERT INTO fixtures
               (id,competition_id,competition_name,home_team,away_team,
                kickoff_utc,status,prob_home_win,prob_draw,prob_away_win,fetched_at,updated_at)
               VALUES(1,101,'PL','Arsenal','Chelsea',?,?,0.55,0.25,0.20,?,?)""",
            (now, "pre", now, now),
        )
        await db.execute(
            """INSERT INTO odds_snapshots
               (fixture_id,market,bookmaker,odds_home,odds_draw,odds_away,drop_pct,drop_market,recorded_at)
               VALUES(1,'1x2','bet365',1.70,3.50,4.50,-15.0,'home',?)""",
            (now,),
        )
        await db.commit()
    importlib.reload(main)
    return main.app

@pytest.mark.asyncio
async def test_dropping_odds(seeded_app):
    async with AsyncClient(transport=ASGITransport(app=seeded_app), base_url="http://test") as c:
        r = await c.get("/api/dropping-odds", params={"min_drop": 10})
    assert r.status_code == 200
    assert len(r.json()["items"]) == 1
    assert r.json()["items"][0]["drop_pct"] == -15.0

@pytest.mark.asyncio
async def test_value_bets_empty_when_no_edge(seeded_app):
    async with AsyncClient(transport=ASGITransport(app=seeded_app), base_url="http://test") as c:
        r = await c.get("/api/value-bets", params={"min_edge": 5})
    assert r.status_code == 200
    assert r.json()["items"] == []

@pytest.mark.asyncio
async def test_history_empty_when_no_ft(seeded_app):
    async with AsyncClient(transport=ASGITransport(app=seeded_app), base_url="http://test") as c:
        r = await c.get("/api/history")
    assert r.status_code == 200
    assert r.json()["total"] == 0

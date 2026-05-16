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

@pytest.mark.asyncio
async def test_list_fixtures_returns_predictability_form_odds(tmp_path, monkeypatch):
    monkeypatch.setenv("GOALCAST_DB_PATH", str(tmp_path / "test.db"))
    import importlib, database, main
    importlib.reload(database)
    await database.init_db()
    now = "2026-05-15T15:00:00"
    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        await db.execute(
            """INSERT INTO fixtures
               (id,competition_id,competition_name,home_team,away_team,
                home_team_id,away_team_id,season_id,kickoff_utc,status,predictability,
                fetched_at,updated_at)
               VALUES(1,101,'Premier League','Arsenal','Chelsea',11,22,55,
                      '2026-05-15T15:00:00','pre','high',?,?)""",
            (now, now),
        )
        await db.execute(
            """INSERT INTO team_form
               (team_id,season_id,form5_str,played,won,drawn,lost,
                goals_for,goals_against,goals_avg,updated_at)
               VALUES(11,55,'WWLDW',5,3,1,1,8,4,2.4,?)""",
            (now,),
        )
        await db.execute(
            """INSERT INTO predictions
               (fixture_id,simulations,home_win,draw,away_win,btts,o25_goals,updated_at)
               VALUES(1,50000,28000,12000,10000,22000,22000,?)""",
            (now,),
        )
        await db.execute(
            """INSERT INTO bookmaker_odds
               (fixture_id,bookmaker_id,market_id,outcome,opening,current,peak,opening_at,current_at)
               VALUES(1,1,6,'home',2.05,1.95,2.10,?,?),
                     (1,1,6,'draw',3.40,3.40,3.40,?,?),
                     (1,1,6,'away',4.20,4.20,4.20,?,?),
                     (1,2,6,'home',2.00,1.91,2.00,?,?),
                     (1,2,6,'draw',3.50,3.50,3.50,?,?),
                     (1,2,6,'away',4.00,4.00,4.00,?,?),
                     (1,1,51,'home_m05',1.85,1.85,1.95,?,?),
                     (1,1,51,'away_p05',1.95,1.95,1.95,?,?)""",
            tuple([now] * 16),
        )
        await db.commit()
    importlib.reload(main)
    async with AsyncClient(transport=ASGITransport(app=main.app), base_url="http://test") as c:
        r = await c.get("/api/fixtures", params={"date": "2026-05-15", "leagues": "101"})
    assert r.status_code == 200
    f = r.json()["fixtures"][0]
    assert f["predictability"] == "high"
    assert f["home_form"]["form5"] == "WWLDW"
    assert f["prediction_summary"]["home_win_pct"] == pytest.approx(56.0, abs=0.1)
    assert f["odds"]["ft_result"]["pinnacle"]["home"] == 1.95
    assert f["odds"]["ft_result"]["bet365"]["home"] == 1.91
    assert f["odds"]["asian_handicap"]["line"] == -0.5
    assert f["odds"]["asian_handicap"]["pinnacle"]["home_odds"] == 1.85

@pytest.mark.asyncio
async def test_list_fixtures_exposes_rank_abbr_zh(tmp_path, monkeypatch):
    """Phase 1: /api/fixtures must surface home_rank/away_rank, home_abbr/away_abbr,
    home_team_zh/away_team_zh, and competition_name_zh when teams/competitions rows exist."""
    monkeypatch.setenv("GOALCAST_DB_PATH", str(tmp_path / "test.db"))
    import importlib, database, main
    importlib.reload(database); await database.init_db()
    now = "2026-05-15T15:00:00"
    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        await db.execute(
            """INSERT INTO fixtures
               (id,competition_id,competition_name,home_team,away_team,
                home_team_id,away_team_id,season_id,kickoff_utc,status,
                predictability,home_position,away_position,fetched_at,updated_at)
               VALUES(7,419,'La Liga','Atlético Madrid','Sevilla',11509,11575,762170,
                      '2026-05-15T15:00:00','pre','high',4,11,?,?)""",
            (now, now),
        )
        await db.execute(
            """INSERT INTO competitions (id, name_en, name_zh, country, last_synced_at)
               VALUES(419, 'La Liga', '西甲', 'Spain', ?)""",
            (now,),
        )
        await db.execute(
            """INSERT INTO teams (id, name, name_zh, short_code, country, last_synced_at)
               VALUES(11509, 'Atlético Madrid', '马德里竞技', 'ATM', 'Spain', ?),
                     (11575, 'Sevilla',         '塞维利亚',   'SEV', 'Spain', ?)""",
            (now, now),
        )
        await db.commit()
    importlib.reload(main)
    async with AsyncClient(transport=ASGITransport(app=main.app), base_url="http://test") as c:
        r = await c.get("/api/fixtures", params={"date": "2026-05-15", "leagues": "419"})
    assert r.status_code == 200
    f = r.json()["fixtures"][0]
    assert f["home_rank"] == 4
    assert f["away_rank"] == 11
    assert f["home_abbr"] == "ATM"
    assert f["away_abbr"] == "SEV"
    assert f["home_team_zh"] == "马德里竞技"
    assert f["away_team_zh"] == "塞维利亚"
    assert f["competition_name_zh"] == "西甲"


@pytest.mark.asyncio
async def test_get_fixture_detail_returns_prediction_and_ah_lines(tmp_path, monkeypatch):
    monkeypatch.setenv("GOALCAST_DB_PATH", str(tmp_path / "test.db"))
    import importlib, database, main, json
    importlib.reload(database); await database.init_db()
    now = "2026-05-15T15:00:00"
    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        await db.execute(
            """INSERT INTO fixtures(id,competition_id,competition_name,home_team,away_team,
                home_team_id,away_team_id,season_id,kickoff_utc,status,predictability,
                fetched_at,updated_at)
               VALUES(1,101,'PL','A','B',11,22,55,'2026-05-15T15:00:00','pre','medium',?,?)""",
            (now, now),
        )
        await db.execute(
            """INSERT INTO predictions(fixture_id,simulations,home_win,draw,away_win,btts,
                o15_goals,o25_goals,o35_goals,o45_goals,scorelines,updated_at)
               VALUES(1,50000,28000,12000,10000,22000,35000,22000,11000,5000,?,?)""",
            (json.dumps({"1-0": 13.44, "2-0": 11.87, "1-1": 11.5}), now),
        )
        await db.execute(
            """INSERT INTO bookmaker_odds
               (fixture_id,bookmaker_id,market_id,outcome,opening,current,peak,opening_at,current_at)
               VALUES(1,1,51,'home_m05',1.92,1.85,1.95,?,?),
                     (1,1,51,'away_p05',1.95,1.95,1.95,?,?),
                     (1,1,51,'home_m075',2.10,2.10,2.10,?,?),
                     (1,1,51,'away_p075',1.75,1.75,1.75,?,?)""",
            tuple([now] * 8),
        )
        await db.commit()
    importlib.reload(main)
    async with AsyncClient(transport=ASGITransport(app=main.app), base_url="http://test") as c:
        r = await c.get("/api/fixtures/1")
    j = r.json()
    assert j["prediction"]["home_win_pct"] == pytest.approx(56.0, abs=0.1)
    assert j["prediction"]["scorelines"]["1-0"] == 13.44
    ah_lines = j["odds"]["asian_handicap_lines"]
    lines = sorted([l["line"] for l in ah_lines])
    assert -0.75 in lines and -0.5 in lines

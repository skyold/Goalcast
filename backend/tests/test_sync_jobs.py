import json
import aiosqlite
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_sync_fixtures_upcoming_inserts(tmp_path, monkeypatch):
    monkeypatch.setenv("GOALCAST_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("ODDALERTS_API_KEY", "K")
    import importlib, config, database, services.oddalerts as oa, services.sync as sync
    for m in (config, database, oa, sync): importlib.reload(m)
    await database.init_db()

    fake = [
        {"id": 100, "home_name": "A", "away_name": "B", "home_id": 11, "away_id": 22,
         "competition_id": 1, "competition_name": "L1", "competition_predictability": "medium",
         "season_id": 5, "unix": 1779000000, "status": "NS"},
        {"id": 101, "home_name": "C", "away_name": "D", "home_id": 33, "away_id": 44,
         "competition_id": 1, "competition_name": "L1", "competition_predictability": "high",
         "season_id": 5, "unix": 1779001000, "status": "NS"},
    ]
    with patch.object(oa.oddalerts_client, "get_upcoming_fixtures",
                       new=AsyncMock(side_effect=[fake, []])):
        await sync.sync_fixtures_upcoming()

    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        cur = await db.execute(
            "SELECT id, home_team, predictability, home_team_id, season_id FROM fixtures ORDER BY id"
        )
        rows = await cur.fetchall()
    assert len(rows) == 2
    assert rows[0] == (100, "A", "medium", 11, 5)
    assert rows[1] == (101, "C", "high", 33, 5)

@pytest.mark.asyncio
async def test_sync_team_form_inserts(tmp_path, monkeypatch):
    monkeypatch.setenv("GOALCAST_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("ODDALERTS_API_KEY", "K")
    import importlib, config, database, services.oddalerts as oa, services.sync as sync
    for m in (config, database, oa, sync): importlib.reload(m)
    await database.init_db()
    now = "2026-05-16T00:00:00"
    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        await db.execute(
            """INSERT INTO fixtures
               (id,competition_id,competition_name,home_team,away_team,home_team_id,away_team_id,
                season_id,kickoff_utc,status,fetched_at,updated_at)
               VALUES(100,1,'L1','A','B',11,22,5,'2026-05-20T00:00:00','NS',?,?)""",
            (now, now),
        )
        await db.commit()

    fake_rows = [{
        "team_id": 11, "season_id": 5, "name": "A",
        "played": {"total": 5}, "won": {"total": 3}, "drawn": {"total": 1}, "lost": {"total": 1},
        "goals_for": {"total": 8}, "goals_against": {"total": 4},
        "goals_total": {"total_avg": 2.4},
        "form_overall": "WDWLW"
    }]
    with patch.object(oa.oddalerts_client, "get_season_stats_last_x",
                       new=AsyncMock(return_value=fake_rows)):
        await sync.sync_team_form(season_ids=[5])

    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        cur = await db.execute(
            "SELECT team_id, season_id, form5_str, played, won, goals_for FROM team_form"
        )
        rows = await cur.fetchall()
    assert rows[0] == (11, 5, "WDWLW", 5, 3, 8)

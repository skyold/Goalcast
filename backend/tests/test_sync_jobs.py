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

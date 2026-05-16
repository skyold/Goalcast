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
async def test_sync_team_form_derives_form5_from_local_history(tmp_path, monkeypatch):
    """Phase 1: form5 is no longer read from upstream `form_overall`; it's derived
    from local fixtures table (status='FT'). Seeds 5 finished matches and asserts
    the derived string plus persisted aggregates."""
    monkeypatch.setenv("GOALCAST_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("ODDALERTS_API_KEY", "K")
    import importlib, config, database, services.oddalerts as oa, services.sync as sync
    for m in (config, database, oa, sync): importlib.reload(m)
    await database.init_db()
    now = "2026-05-16T00:00:00"
    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        # upcoming fixture so sync_team_form can discover season_id=5
        await db.execute(
            """INSERT INTO fixtures
               (id,competition_id,competition_name,home_team,away_team,home_team_id,away_team_id,
                season_id,kickoff_utc,status,fetched_at,updated_at)
               VALUES(100,1,'L1','A','B',11,22,5,'2099-05-20T00:00:00','NS',?,?)""",
            (now, now),
        )
        # 5 finished matches for team 11. Oldest → newest, outcomes from team 11's
        # perspective: W, D, L, W, W. With 末尾=最近 convention the derived string
        # should be "WDLWW".
        history = [
            (201, "2025-04-01", 11, 22, 11,   2, 1),  # W home
            (202, "2025-04-08", 33, 11, None, 1, 1),  # D draw
            (203, "2025-04-15", 11, 44, 44,   0, 1),  # L home
            (204, "2025-04-22", 55, 11, 11,   0, 2),  # W away
            (205, "2025-04-29", 11, 66, 11,   3, 0),  # W home
        ]
        for fid, ko, h, a, win, sh, sa in history:
            await db.execute(
                """INSERT INTO fixtures
                   (id,competition_id,competition_name,home_team,away_team,
                    home_team_id,away_team_id,kickoff_utc,status,
                    score_home,score_away,winning_team,fetched_at,updated_at)
                   VALUES(?,1,'L1','H','A',?,?,?,?, ?,?,?,?,?)""",
                (fid, h, a, ko, "FT", sh, sa, win, now, now),
            )
        await db.commit()

    fake_rows = [{
        "team_id": 11, "season_id": 5, "name": "A",
        "played": {"total": 5}, "won": {"total": 3}, "drawn": {"total": 1}, "lost": {"total": 1},
        "goals_for": {"total": 8}, "goals_against": {"total": 4},
        "goals_total": {"total_avg": 2.4},
    }]
    with patch.object(oa.oddalerts_client, "get_season_stats_last_x",
                       new=AsyncMock(return_value=fake_rows)):
        await sync.sync_team_form(season_ids=[5])

    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        cur = await db.execute(
            "SELECT team_id, season_id, form5_str, played, won, goals_for FROM team_form"
        )
        rows = await cur.fetchall()
    assert rows[0] == (11, 5, "WDLWW", 5, 3, 8)


@pytest.mark.asyncio
async def test_sync_fixtures_upcoming_persists_positions(tmp_path, monkeypatch):
    """Phase 1: home_position/away_position must be written through from upstream."""
    monkeypatch.setenv("GOALCAST_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("ODDALERTS_API_KEY", "K")
    import importlib, config, database, services.oddalerts as oa, services.sync as sync
    for m in (config, database, oa, sync): importlib.reload(m)
    await database.init_db()

    fake = [
        {"id": 700, "home_name": "A", "away_name": "B", "home_id": 11, "away_id": 22,
         "competition_id": 1, "competition_name": "L1",
         "season_id": 5, "unix": 1779000000, "status": "NS",
         "home_position": 4, "away_position": 11},
    ]
    with patch.object(oa.oddalerts_client, "get_upcoming_fixtures",
                       new=AsyncMock(side_effect=[fake, []])):
        await sync.sync_fixtures_upcoming()

    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        cur = await db.execute("SELECT home_position, away_position FROM fixtures WHERE id=700")
        rows = await cur.fetchall()
    assert rows[0] == (4, 11)


@pytest.mark.asyncio
async def test_sync_historical_fixtures_persists_ft_only(tmp_path, monkeypatch):
    """Phase 1: only status=FT rows are persisted with score/winning_team."""
    monkeypatch.setenv("GOALCAST_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("ODDALERTS_API_KEY", "K")
    import importlib, config, database, services.oddalerts as oa, services.sync as sync
    for m in (config, database, oa, sync): importlib.reload(m)
    await database.init_db()

    items = [
        {"id": 801, "status": "FT", "home_name": "A", "away_name": "B",
         "home_id": 11, "away_id": 22, "competition_id": 1, "competition_name": "L1",
         "season_id": 5, "unix": 1778000000, "home_goals": 2, "away_goals": 1,
         "winning_team": 11, "home_position": 1, "away_position": 12},
        {"id": 802, "status": "NS",
         "home_name": "C", "away_name": "D",
         "competition_id": 1, "competition_name": "L1"},
    ]
    with patch.object(oa.oddalerts_client, "get_fixtures_between",
                       new=AsyncMock(side_effect=[items, []])):
        await sync.sync_historical_fixtures(days=30)

    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        cur = await db.execute(
            "SELECT id, status, score_home, score_away, winning_team FROM fixtures ORDER BY id"
        )
        rows = await cur.fetchall()
    assert rows == [(801, "FT", 2, 1, 11)]


@pytest.mark.asyncio
async def test_sync_competitions_preserves_name_zh(tmp_path, monkeypatch):
    """Phase 1: re-syncing competitions must NOT clobber curated name_zh."""
    monkeypatch.setenv("GOALCAST_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("ODDALERTS_API_KEY", "K")
    import importlib, config, database, services.oddalerts as oa, services.sync as sync
    for m in (config, database, oa, sync): importlib.reload(m)
    await database.init_db()
    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        await db.execute(
            """INSERT INTO competitions (id, name_en, name_zh, country, last_synced_at)
               VALUES(419, 'La Liga', '西甲', 'Spain', '2026-01-01T00:00:00')"""
        )
        await db.commit()

    upstream = [
        {"id": 419, "name": "La Liga", "country": "Spain"},
        {"id": 999, "name": "Unknown League", "country": "Nowhere"},
    ]
    with patch.object(oa.oddalerts_client, "get_competitions",
                       new=AsyncMock(side_effect=[upstream, []])):
        await sync.sync_competitions()

    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        cur = await db.execute("SELECT id, name_en, name_zh FROM competitions ORDER BY id")
        rows = await cur.fetchall()
    assert (419, "La Liga", "西甲") in rows
    assert (999, "Unknown League", None) in rows


@pytest.mark.asyncio
async def test_sync_teams_meta_writes_short_code(tmp_path, monkeypatch):
    """Phase 1: sync_teams_meta upserts teams from /teams/find/:ID and
    preserves curated name_zh on already-seeded rows."""
    monkeypatch.setenv("GOALCAST_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("ODDALERTS_API_KEY", "K")
    import importlib, config, database, services.oddalerts as oa, services.sync as sync
    for m in (config, database, oa, sync): importlib.reload(m)
    await database.init_db()

    now = "2026-05-16T00:00:00"
    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        await db.execute(
            """INSERT INTO fixtures
               (id,competition_id,competition_name,home_team,away_team,
                home_team_id,away_team_id,kickoff_utc,status,fetched_at,updated_at)
               VALUES(900,1,'L1','A','B',11,22,'2099-01-01T00:00:00','NS',?,?)""",
            (now, now),
        )
        await db.execute(
            """INSERT INTO teams (id, name, name_zh, last_synced_at)
               VALUES(11, 'OldName', '马德里竞技', NULL)"""
        )
        await db.commit()

    async def _fake_team(tid):
        return {"id": tid, "name": f"T{tid}", "short_code": f"S{tid}", "country": "X"}
    with patch.object(oa.oddalerts_client, "get_team_find",
                       new=AsyncMock(side_effect=_fake_team)):
        await sync.sync_teams_meta()

    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        cur = await db.execute(
            "SELECT id, name, name_zh, short_code, country FROM teams ORDER BY id"
        )
        rows = await cur.fetchall()
    by_id = {r[0]: r for r in rows}
    assert by_id[11] == (11, "T11", "马德里竞技", "S11", "X")  # zh preserved, code added
    assert by_id[22] == (22, "T22", None, "S22", "X")

@pytest.mark.asyncio
async def test_sync_ah_odds_seed_filters_bookmakers(tmp_path, monkeypatch):
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
                kickoff_utc,status,fetched_at,updated_at)
               VALUES(200,1,'L','A','B',11,22,'2026-05-20T00:00:00','NS',?,?)""",
            (now, now),
        )
        await db.commit()

    history = [
        {"fixture_id": 200, "market_id": 51, "outcome": "home_m05",
         "opening": "1.92", "closing": "1.85", "peak": "1.95",
         "bookmaker_id": 1, "bookmaker_name": "Pinnacle"},
        {"fixture_id": 200, "market_id": 6, "outcome": "home",
         "opening": "2.05", "closing": "1.95", "peak": "2.10",
         "bookmaker_id": 2, "bookmaker_name": "Bet365"},
        {"fixture_id": 200, "market_id": 6, "outcome": "home",
         "opening": "2.00", "closing": "1.92", "peak": "2.00",
         "bookmaker_id": 7, "bookmaker_name": "Betano"},
    ]
    with patch.object(oa.oddalerts_client, "get_odds_history_by_path",
                       new=AsyncMock(return_value=history)):
        await sync.sync_ah_odds_seed(fixture_ids=[200])

    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        cur = await db.execute(
            "SELECT bookmaker_id, market_id, outcome, opening, current FROM bookmaker_odds ORDER BY bookmaker_id"
        )
        rows = await cur.fetchall()
    assert len(rows) == 2   # Betano dropped
    assert (rows[0][0], rows[0][1], rows[0][2]) == (1, 51, "home_m05")
    assert rows[0][3] == 1.92 and rows[0][4] == 1.85

@pytest.mark.asyncio
async def test_sync_ah_odds_latest_preserves_opening(tmp_path, monkeypatch):
    monkeypatch.setenv("GOALCAST_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("ODDALERTS_API_KEY", "K")
    import importlib, config, database, services.oddalerts as oa, services.sync as sync
    for m in (config, database, oa, sync): importlib.reload(m)
    await database.init_db()
    now = "2026-05-16T00:00:00"
    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        await db.execute(
            """INSERT INTO fixtures
               (id,competition_id,competition_name,home_team,away_team,
                kickoff_utc,status,fetched_at,updated_at)
               VALUES(300,1,'L','A','B','2026-05-20T00:00:00','NS',?,?)""",
            (now, now),
        )
        await db.execute(
            """INSERT INTO bookmaker_odds
               (fixture_id,bookmaker_id,market_id,outcome,opening,current,peak,opening_at,current_at)
               VALUES(300,1,6,'home',2.10,2.10,2.10,?,?)""",
            (now, now),
        )
        await db.commit()

    latest = [{"fixture_id": 300, "market_id": 6, "outcome": "home", "odds": 1.95,
               "unix": 1779000000, "bookmaker_id": 1, "bookmaker_name": "Pinnacle"}]
    with patch.object(oa.oddalerts_client, "get_odds_latest",
                       new=AsyncMock(side_effect=[latest, []])):
        await sync.sync_ah_odds_latest()

    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        cur = await db.execute(
            "SELECT current, opening FROM bookmaker_odds WHERE fixture_id=300 AND bookmaker_id=1 AND market_id=6 AND outcome='home'"
        )
        rows = await cur.fetchall()
    assert rows[0] == (1.95, 2.10)   # current updated, opening preserved

@pytest.mark.asyncio
async def test_sync_predictions_filters_poor(tmp_path, monkeypatch):
    monkeypatch.setenv("GOALCAST_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("ODDALERTS_API_KEY", "K")
    import importlib, config, database, services.oddalerts as oa, services.sync as sync
    for m in (config, database, oa, sync): importlib.reload(m)
    await database.init_db()
    now = "2026-05-16T00:00:00"
    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        for fid, pred in [(401, "poor"), (402, "medium")]:
            await db.execute(
                """INSERT INTO fixtures
                   (id,competition_id,competition_name,home_team,away_team,
                    kickoff_utc,status,predictability,fetched_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (fid, 1, "L", "A", "B", "2026-05-20T00:00:00", "NS", pred, now, now),
            )
        await db.commit()

    # sync_predictions now uses per-fixture get_predictions_single; mock it accordingly.
    # 402 (medium) -> data; 401 (poor) is filtered out before the call.
    fake_402 = {"fixture_id": 402, "simulations": 50000,
                "home_win": 28000, "draw": 12000, "away_win": 10000,
                "btts": 22000, "o15_goals": 35000, "o25_goals": 22000,
                "o35_goals": 11000, "o45_goals": 5000,
                "scorelines": {"1-0": 13.44, "2-0": 11.87}}
    async def _fake_single(fid):
        return fake_402 if fid == 402 else None
    with patch.object(oa.oddalerts_client, "get_predictions_single",
                       new=AsyncMock(side_effect=_fake_single)):
        await sync.sync_predictions()

    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        cur = await db.execute("SELECT fixture_id, home_win, scorelines FROM predictions")
        rows = await cur.fetchall()
    assert len(rows) == 1   # poor was filtered out
    assert rows[0][0] == 402
    assert rows[0][1] == 28000
    assert json.loads(rows[0][2])["1-0"] == 13.44

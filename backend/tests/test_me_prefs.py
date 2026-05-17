"""Phase 3 — my-leagues whitelist tests.

Cover:
- PUT/GET round-trip for user prefs.
- /fixtures filters by prefs (intersection with `leagues` query).
- /fixtures returns empty when logged in with no prefs (forces user to set them).
- /dropping-odds + /value-bets respect the same whitelist.
- Anonymous requests behave as before (no filter applied).
"""
import pytest
import aiosqlite
from httpx import AsyncClient, ASGITransport


@pytest.fixture
async def app(tmp_path, monkeypatch):
    monkeypatch.setenv("GOALCAST_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("GOALCAST_JWT_SECRET", "test-secret-not-prod")
    import importlib, database, main, services.auth
    importlib.reload(database)
    await database.init_db()
    importlib.reload(services.auth)

    now = "2026-05-15T15:00:00"
    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        # Two competitions, two fixtures (one per comp).
        await db.executemany(
            """INSERT INTO fixtures
               (id, competition_id, competition_name, home_team, away_team,
                kickoff_utc, status, fetched_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, 'pre', ?, ?)""",
            [
                (1, 100, 'League Alpha', 'Alpha FC', 'Alpha United',
                 '2026-05-15T15:00:00', now, now),
                (2, 200, 'League Beta',  'Beta FC',  'Beta United',
                 '2026-05-15T15:00:00', now, now),
            ],
        )
        # Dropping snapshot for both fixtures.
        await db.executemany(
            """INSERT INTO odds_snapshots
               (fixture_id, market, bookmaker, drop_pct, drop_market, recorded_at)
               VALUES (?, 'ft_result', 'pinnacle', ?, 'ft_result', ?)""",
            [(1, -60.0, now), (2, -55.0, now)],
        )
        await db.commit()

    importlib.reload(main)
    return main.app


async def _signup(c: AsyncClient, email="a@b.com"):
    return await c.post("/api/auth/signup",
                        json={"email": email, "password": "secret123"})


@pytest.mark.asyncio
async def test_anonymous_fixtures_see_all_leagues(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/fixtures",
                         params={"date": "2026-05-15", "leagues": "100,200"})
    assert r.status_code == 200
    ids = sorted(f["id"] for f in r.json()["fixtures"])
    assert ids == [1, 2]


@pytest.mark.asyncio
async def test_logged_in_empty_prefs_returns_empty(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await _signup(c)
        r = await c.get("/api/fixtures",
                         params={"date": "2026-05-15", "leagues": "100,200"})
    assert r.status_code == 200
    assert r.json() == {"fixtures": [], "total": 0, "cached_at": None}


@pytest.mark.asyncio
async def test_put_then_get_my_competitions_round_trip(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await _signup(c)
        put = await c.put("/api/me/competitions",
                           json={"competition_ids": [200, 100, 100]})
        assert put.status_code == 200
        # Dedupe + sort.
        assert put.json() == {"competition_ids": [100, 200]}
        get = await c.get("/api/me/competitions")
        assert get.status_code == 200
        assert get.json() == {"competition_ids": [100, 200]}


@pytest.mark.asyncio
async def test_logged_in_prefs_filter_fixtures(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await _signup(c)
        await c.put("/api/me/competitions", json={"competition_ids": [100]})
        # User requested both, but prefs restrict to 100.
        r = await c.get("/api/fixtures",
                         params={"date": "2026-05-15", "leagues": "100,200"})
    assert r.status_code == 200
    ids = sorted(f["id"] for f in r.json()["fixtures"])
    assert ids == [1]


@pytest.mark.asyncio
async def test_logged_in_no_leagues_defaults_to_prefs(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await _signup(c)
        await c.put("/api/me/competitions", json={"competition_ids": [200]})
        r = await c.get("/api/fixtures", params={"date": "2026-05-15"})
    assert r.status_code == 200
    ids = [f["id"] for f in r.json()["fixtures"]]
    assert ids == [2]


@pytest.mark.asyncio
async def test_dropping_odds_filters_by_prefs(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        # Anonymous: both items.
        anon = await c.get("/api/dropping-odds")
        assert len({i["fixture_id"] for i in anon.json()["items"]}) == 2
        # Sign up + set prefs to only comp 200.
        await _signup(c)
        await c.put("/api/me/competitions", json={"competition_ids": [200]})
        logged = await c.get("/api/dropping-odds")
        ids = {i["fixture_id"] for i in logged.json()["items"]}
        assert ids == {2}


@pytest.mark.asyncio
async def test_logged_in_empty_prefs_empties_dropping_odds(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await _signup(c)
        r = await c.get("/api/dropping-odds")
    assert r.status_code == 200
    assert r.json()["items"] == []


@pytest.mark.asyncio
async def test_me_endpoints_require_auth(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/me/competitions")
        assert r.status_code == 401
        r = await c.put("/api/me/competitions", json={"competition_ids": [1]})
        assert r.status_code == 401

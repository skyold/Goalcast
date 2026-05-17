"""Phase 1 + 2 endpoint tests:
- /api/fixtures/:id/odds-timeseries  → drop_pct timeseries with downsampling
- /api/insights/mispricings          → de-vigged model vs market deltas
"""
from __future__ import annotations

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

    now = "2026-05-17T10:00:00"
    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        # Two fixtures on the same day, different comps.
        await db.executemany(
            """INSERT INTO fixtures
               (id, competition_id, competition_name, home_team, away_team,
                kickoff_utc, status, fetched_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, 'NS', ?, ?)""",
            [
                (10, 100, 'League Alpha', 'Alpha FC', 'Alpha United',
                 '2026-05-17T15:00:00', now, now),
                (20, 200, 'League Beta', 'Beta FC', 'Beta United',
                 '2026-05-17T15:00:00', now, now),
            ],
        )
        # Predictions: simulate 100 sims; home=70 means model says 70% home win.
        await db.executemany(
            """INSERT INTO predictions
               (fixture_id, simulations, home_win, draw, away_win, btts,
                o15_goals, o25_goals, o35_goals, o45_goals, scorelines, updated_at)
               VALUES (?, 100, ?, ?, ?, 50, 60, 50, 30, 10, '{}', ?)""",
            [
                (10, 70, 20, 10, now),   # model: 70/20/10
                (20, 33, 33, 34, now),   # model: balanced
            ],
        )
        # Bookmaker odds (Pinnacle = 1, market 1x2 = 6).
        # Fixture 10: market gives near 50/30/20 → big mispricing on home (model 70% vs market ~50%).
        # Fixture 20: market matches model 33/33/34 → small delta, below default 3% threshold.
        await db.executemany(
            """INSERT INTO bookmaker_odds
               (fixture_id, bookmaker_id, market_id, outcome, opening, current, peak, opening_at, current_at)
               VALUES (?, 1, 6, ?, ?, ?, ?, ?, ?)""",
            [
                (10, 'home', 1.9, 1.9, 1.9, now, now),
                (10, 'draw', 3.4, 3.4, 3.4, now, now),
                (10, 'away', 5.5, 5.5, 5.5, now, now),
                (20, 'home', 3.0, 3.0, 3.0, now, now),
                (20, 'draw', 3.0, 3.0, 3.0, now, now),
                (20, 'away', 3.0, 3.0, 3.0, now, now),
            ],
        )
        # odds_snapshots — drop_pct points for fixture 10, last hour.
        snaps = [
            (10, "ft_result", "Pinnacle", -10.0, "ft_result", "2026-05-17T09:30:00+00:00"),
            (10, "ft_result", "Pinnacle", -25.0, "ft_result", "2026-05-17T09:45:00+00:00"),
            (10, "ft_result", "Pinnacle", -42.0, "ft_result", "2026-05-17T09:55:00+00:00"),
            (10, "ft_result", "Bet365",   -8.0,  "ft_result", "2026-05-17T09:32:00+00:00"),
        ]
        await db.executemany(
            "INSERT INTO odds_snapshots (fixture_id, market, bookmaker, drop_pct, drop_market, recorded_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            snaps,
        )
        await db.commit()

    importlib.reload(main)
    return main.app


# ---------- timeseries ----------

@pytest.mark.asyncio
async def test_timeseries_filters_to_pinnacle_ft_result_by_default(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/fixtures/10/odds-timeseries", params={"window": "7d"})
    assert r.status_code == 200
    body = r.json()
    assert body["fixture_id"] == 10
    # 4 snaps total but only 3 are Pinnacle.
    assert len(body["points"]) == 3
    assert {p["bookmaker"] for p in body["points"]} == {"Pinnacle"}


@pytest.mark.asyncio
async def test_timeseries_all_bookmakers(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/fixtures/10/odds-timeseries", params={"window": "7d", "bookmaker": "all"})
    assert r.status_code == 200
    assert len(r.json()["points"]) == 4


@pytest.mark.asyncio
async def test_timeseries_empty_when_no_snapshots(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/fixtures/20/odds-timeseries", params={"window": "7d"})
    assert r.status_code == 200
    assert r.json()["points"] == []


@pytest.mark.asyncio
async def test_timeseries_downsamples_above_50_points(app, tmp_path):
    extra = [
        (10, "ft_result", "Pinnacle", -float(i) / 5, "ft_result",
         f"2026-05-17T11:{i // 60:02d}:{i % 60:02d}+00:00")
        for i in range(200)
    ]
    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        await db.executemany(
            "INSERT INTO odds_snapshots (fixture_id, market, bookmaker, drop_pct, drop_market, recorded_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            extra,
        )
        await db.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/fixtures/10/odds-timeseries", params={"window": "7d"})
    assert r.status_code == 200
    points = r.json()["points"]
    assert len(points) <= 50


# ---------- mispricings ----------

@pytest.mark.asyncio
async def test_mispricings_returns_high_delta_only(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/insights/mispricings",
                         params={"date": "2026-05-17", "min_abs_edge": 5})
    assert r.status_code == 200
    items = r.json()["items"]
    assert all(i["fixture_id"] == 10 for i in items)
    home_row = next(i for i in items if i["selection"] == "home")
    assert home_row["delta_pct"] > 10


@pytest.mark.asyncio
async def test_mispricings_includes_negative_delta(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/insights/mispricings",
                         params={"date": "2026-05-17", "min_abs_edge": 5})
    items = r.json()["items"]
    away_row = next((i for i in items if i["selection"] == "away"), None)
    assert away_row is not None
    assert away_row["delta_pct"] < -5


@pytest.mark.asyncio
async def test_mispricings_sorted_by_abs_delta_desc(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/insights/mispricings",
                         params={"date": "2026-05-17", "min_abs_edge": 1})
    items = r.json()["items"]
    deltas = [abs(i["delta_pct"]) for i in items]
    assert deltas == sorted(deltas, reverse=True)


@pytest.mark.asyncio
async def test_mispricings_prefs_filter(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post("/api/auth/signup", json={"email": "a@b.com", "password": "secret123"})
        await c.put("/api/me/competitions", json={"competition_ids": [200]})
        r = await c.get("/api/insights/mispricings",
                         params={"date": "2026-05-17", "min_abs_edge": 5})
    items = r.json()["items"]
    assert all(i["fixture_id"] != 10 for i in items)


@pytest.mark.asyncio
async def test_mispricings_empty_prefs_returns_empty(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post("/api/auth/signup", json={"email": "a@b.com", "password": "secret123"})
        r = await c.get("/api/insights/mispricings", params={"date": "2026-05-17"})
    assert r.json()["items"] == []

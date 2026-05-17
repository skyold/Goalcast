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


# ---------- league_stats ----------

@pytest.fixture
async def app_with_ft(tmp_path, monkeypatch):
    """Fixture set with finished games for the league_stats endpoint."""
    monkeypatch.setenv("GOALCAST_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("GOALCAST_JWT_SECRET", "test-secret-not-prod")
    monkeypatch.setenv("ODDALERTS_API_KEY", "ci-stub")
    import importlib, database, main, services.auth
    importlib.reload(database)
    await database.init_db()
    importlib.reload(services.auth)

    now = "2026-05-17T10:00:00"
    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        await db.execute(
            "INSERT INTO competitions (id, name_en, name_zh) VALUES (500, 'Premier League', '英超')"
        )
        # Result mix: 2 home / 2 draw / 1 away. Goals 3+2+5+4+3=17 → avg 3.4.
        # Predictability: 2 high, 1 good, 1 medium, 1 poor → upset 20% / top_pred 60%.
        fts = [
            (1001, 500, 'A', 'B', 2, 1, 'high'),
            (1002, 500, 'C', 'D', 1, 1, 'good'),
            (1003, 500, 'E', 'F', 3, 2, 'medium'),
            (1004, 500, 'G', 'H', 2, 2, 'poor'),
            (1005, 500, 'I', 'J', 1, 2, 'high'),
        ]
        for f in fts:
            await db.execute(
                """INSERT INTO fixtures (id, competition_id, competition_name, home_team, away_team,
                   score_home, score_away, predictability, kickoff_utc, status, fetched_at, updated_at)
                   VALUES (?, ?, 'Premier League', ?, ?, ?, ?, ?, ?, 'FT', ?, ?)""",
                (f[0], f[1], f[2], f[3], f[4], f[5], f[6], now, now, now),
            )
        # 4 predictions: 1001 picks home (correct), 1002 picks home (actual draw, miss),
        # 1003 picks home (correct), 1005 picks away (correct). Hit rate 3/4 = 75%.
        preds = [
            (1001, 100, 70, 20, 10),
            (1002, 100, 60, 20, 20),
            (1003, 100, 55, 25, 20),
            (1005, 100, 20, 30, 50),
        ]
        for p in preds:
            await db.execute(
                """INSERT INTO predictions
                   (fixture_id, simulations, home_win, draw, away_win, btts,
                    o15_goals, o25_goals, o35_goals, o45_goals, scorelines, updated_at)
                   VALUES (?, ?, ?, ?, ?, 50, 60, 50, 30, 10, '{}', ?)""",
                (p[0], p[1], p[2], p[3], p[4], now),
            )
        await db.commit()

    importlib.reload(main)
    return main.app


@pytest.mark.asyncio
async def test_league_stats_aggregates(app_with_ft):
    async with AsyncClient(transport=ASGITransport(app=app_with_ft), base_url="http://test") as c:
        r = await c.get("/api/insights/leagues/500")
    assert r.status_code == 200
    d = r.json()
    assert d["matches_played"] == 5
    assert d["competition_name_zh"] == "英超"
    assert d["avg_goals"] == pytest.approx(3.4)
    assert d["home_win_pct"] == pytest.approx(40.0)
    assert d["draw_pct"]     == pytest.approx(40.0)
    assert d["away_win_pct"] == pytest.approx(20.0)
    # 4 predictions, 3 hits → hit_rate 75%, upset 25%
    assert d["model_hit_rate_pct"] == pytest.approx(75.0)
    assert d["upset_pct"] == pytest.approx(25.0)
    assert d["predicted_count"] == 4


@pytest.mark.asyncio
async def test_league_stats_empty_returns_zeros(app_with_ft):
    async with AsyncClient(transport=ASGITransport(app=app_with_ft), base_url="http://test") as c:
        r = await c.get("/api/insights/leagues/9999")
    assert r.status_code == 200
    body = r.json()
    assert body["matches_played"] == 0
    assert body["model_hit_rate_pct"] is None
    assert body["upset_pct"] is None
    assert body["predicted_count"] == 0


# ---------- h2h ----------

@pytest.fixture
async def app_with_h2h(tmp_path, monkeypatch):
    """Anchor fixture + 3 prior FT matchups between team_id 11 and 22."""
    monkeypatch.setenv("GOALCAST_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("GOALCAST_JWT_SECRET", "test-secret-not-prod")
    monkeypatch.setenv("ODDALERTS_API_KEY", "ci-stub")
    import importlib, database, main, services.auth
    importlib.reload(database)
    await database.init_db()
    importlib.reload(services.auth)
    now = "2026-05-17T10:00:00"
    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        await db.execute(
            """INSERT INTO fixtures (id, competition_id, competition_name, home_team, away_team,
               home_team_id, away_team_id, kickoff_utc, status, fetched_at, updated_at)
               VALUES (900, 1, 'L', 'TeamA', 'TeamB', 11, 22, ?, 'NS', ?, ?)""",
            (now, now, now),
        )
        prior = [
            (901, 1, 11, 'TeamA', 22, 'TeamB', '2025-12-01T15:00:00', 2, 1),
            (902, 1, 22, 'TeamB', 11, 'TeamA', '2025-09-15T15:00:00', 0, 3),
            (903, 2, 11, 'TeamA', 22, 'TeamB', '2024-08-20T15:00:00', 1, 1),
        ]
        for p in prior:
            await db.execute(
                """INSERT INTO fixtures (id, competition_id, competition_name, home_team_id, home_team,
                   away_team_id, away_team, kickoff_utc, score_home, score_away,
                   status, fetched_at, updated_at)
                   VALUES (?, ?, 'L', ?, ?, ?, ?, ?, ?, ?, 'FT', ?, ?)""",
                (p[0], p[1], p[2], p[3], p[4], p[5], p[6], p[7], p[8], now, now),
            )
        # Unrelated fixture: same team 11 but different opponent — must NOT appear.
        await db.execute(
            """INSERT INTO fixtures (id, competition_id, competition_name, home_team_id, home_team,
               away_team_id, away_team, kickoff_utc, score_home, score_away,
               status, fetched_at, updated_at)
               VALUES (999, 1, 'L', 11, 'TeamA', 33, 'TeamC', ?, 1, 0, 'FT', ?, ?)""",
            ('2025-07-01T15:00:00', now, now),
        )
        await db.commit()
    importlib.reload(main)
    return main.app


@pytest.mark.asyncio
async def test_h2h_returns_prior_meetings(app_with_h2h):
    async with AsyncClient(transport=ASGITransport(app=app_with_h2h), base_url="http://test") as c:
        r = await c.get("/api/fixtures/900/h2h")
    assert r.status_code == 200
    d = r.json()
    assert d["count"] == 3
    ids = [i["id"] for i in d["items"]]
    assert ids == [901, 902, 903]
    assert 999 not in ids


@pytest.mark.asyncio
async def test_h2h_anchor_missing_team_returns_empty(app_with_h2h, tmp_path):
    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        await db.execute(
            """INSERT INTO fixtures (id, competition_id, competition_name, home_team, away_team,
               kickoff_utc, status, fetched_at, updated_at)
               VALUES (888, 1, 'L', 'X', 'Y', ?, 'NS', ?, ?)""",
            ("2026-05-17T10:00:00", "2026-05-17T10:00:00", "2026-05-17T10:00:00"),
        )
        await db.commit()
    async with AsyncClient(transport=ASGITransport(app=app_with_h2h), base_url="http://test") as c:
        r = await c.get("/api/fixtures/888/h2h")
    assert r.status_code == 200
    assert r.json()["count"] == 0


@pytest.mark.asyncio
async def test_h2h_respects_limit(app_with_h2h):
    async with AsyncClient(transport=ASGITransport(app=app_with_h2h), base_url="http://test") as c:
        r = await c.get("/api/fixtures/900/h2h", params={"limit": 2})
    assert r.json()["count"] == 2

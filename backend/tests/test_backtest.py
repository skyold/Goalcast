"""Backtest center — model accuracy on FT × kickoff_snap pairs.

Worked example (3 fixtures, model 60/30/10 each, mixed actuals):
  F1 home → hit;  Brier = (0.6-1)² + 0.3² + 0.1² = 0.26
  F2 draw → miss; Brier = 0.6² + (0.3-1)² + 0.1² = 0.86
  F3 home → hit;  Brier = 0.26
  hit_rate    = 2/3 ≈ 0.667
  mean Brier  = 1.38/3 = 0.46
"""
from __future__ import annotations

import aiosqlite
import pytest


@pytest.fixture
async def app(tmp_path, monkeypatch):
    monkeypatch.setenv("GOALCAST_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("GOALCAST_JWT_SECRET", "test-secret-not-prod")
    monkeypatch.setenv("ODDALERTS_API_KEY", "ci-stub")
    import importlib, database, main, services.auth
    importlib.reload(database)
    await database.init_db()
    importlib.reload(services.auth)

    now = "2026-05-18T10:00:00"
    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        await db.execute(
            "INSERT INTO competitions (id, name_en, name_zh) VALUES (500, 'EPL', '英超')"
        )
        await db.execute(
            "INSERT INTO competitions (id, name_en, name_zh) VALUES (600, 'La Liga', '西甲')"
        )

        fts = [
            (1, 500, 2, 0),  # home actual → hit
            (2, 500, 1, 1),  # draw actual → miss
            (3, 500, 3, 1),  # home actual → hit
            (4, 600, 0, 2),  # away actual → miss
        ]
        for fid, comp, sh, sa in fts:
            await db.execute(
                """INSERT INTO fixtures (id, competition_id, competition_name,
                   home_team, away_team, score_home, score_away,
                   kickoff_utc, status, fetched_at, updated_at)
                   VALUES (?, ?, 'L', 'A', 'B', ?, ?, '2026-05-17T15:00:00', 'FT', ?, ?)""",
                (fid, comp, sh, sa, now, now),
            )
        for fid in (1, 2, 3, 4):
            await db.execute(
                """INSERT INTO historical_predictions
                     (fixture_id, waypoint, simulations,
                      home_win_pct, draw_pct, away_win_pct,
                      btts_pct, o25_pct, scorelines, captured_at)
                   VALUES (?, 'kickoff', 100, 60.0, 30.0, 10.0, 50.0, 50.0, '{}', ?)""",
                (fid, now),
            )
        await db.commit()

    importlib.reload(main)
    return main.app


# ---------- /api/backtest/summary ----------

@pytest.mark.asyncio
async def test_summary_hit_rate_and_brier_known_inputs(app):
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/backtest/summary", params={"min_samples": 1})
    assert r.status_code == 200
    d = r.json()
    assert d["model_id"] == "oddalerts_default"
    assert d["scope"]["waypoint"] == "kickoff"
    assert d["samples"] == 4  # 3 EPL + 1 La Liga
    assert d["enough"] is True
    # 2 EPL hits (F1, F3) + 0 La Liga hits = 2 / 4 = 0.5
    assert d["metrics"]["top1_hit_rate"] == pytest.approx(0.5, abs=0.001)
    # Brier across 4: (0.26+0.86+0.26+1.26)/4 = 0.66
    # F4 actual=away → (0.6-0)² + 0.3² + (0.1-1)² = 0.36+0.09+0.81 = 1.26
    assert d["metrics"]["brier"] == pytest.approx(0.66, abs=0.005)


@pytest.mark.asyncio
async def test_summary_competition_filter(app):
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(
            "/api/backtest/summary",
            params={"competition_id": 500, "min_samples": 1},
        )
    d = r.json()
    assert d["samples"] == 3
    assert d["metrics"]["top1_hit_rate"] == pytest.approx(2 / 3, abs=0.001)
    assert d["metrics"]["brier"] == pytest.approx(0.46, abs=0.005)


@pytest.mark.asyncio
async def test_summary_enough_false_when_below_threshold(app):
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/backtest/summary", params={"min_samples": 10})
    d = r.json()
    assert d["samples"] == 4
    assert d["enough"] is False
    assert d["min_samples"] == 10
    assert "metrics" in d


@pytest.mark.asyncio
async def test_summary_empty_when_no_pairs(tmp_path, monkeypatch):
    """No FT+kickoff_snap pairs (fresh DB) → samples=0, enough=false."""
    monkeypatch.setenv("GOALCAST_DB_PATH", str(tmp_path / "empty.db"))
    monkeypatch.setenv("GOALCAST_JWT_SECRET", "test-secret-not-prod")
    monkeypatch.setenv("ODDALERTS_API_KEY", "ci-stub")
    import importlib, database, main, services.auth
    importlib.reload(database)
    await database.init_db()
    importlib.reload(services.auth)
    importlib.reload(main)
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(transport=ASGITransport(app=main.app), base_url="http://test") as c:
        r = await c.get("/api/backtest/summary")
    d = r.json()
    assert d["samples"] == 0
    assert d["enough"] is False


# ---------- /api/backtest/by-league ----------

@pytest.mark.asyncio
async def test_by_league_returns_one_row_per_competition(app):
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/backtest/by-league", params={"min_samples": 1})
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 2
    by_comp = {it["competition_id"]: it for it in items}
    assert by_comp[500]["samples"] == 3
    assert by_comp[500]["top1_hit_rate"] == pytest.approx(2 / 3, abs=0.001)
    assert by_comp[600]["samples"] == 1
    assert by_comp[600]["top1_hit_rate"] == pytest.approx(0.0, abs=0.001)


@pytest.mark.asyncio
async def test_by_league_marks_under_threshold_as_not_enough(app):
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/backtest/by-league", params={"min_samples": 2})
    items = r.json()["items"]
    by_comp = {it["competition_id"]: it for it in items}
    assert by_comp[500]["enough"] is True   # 3 >= 2
    assert by_comp[600]["enough"] is False  # 1 < 2

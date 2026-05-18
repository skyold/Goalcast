"""Unified /api/signals/* router — list-by-type and cross-signal active feed."""
from __future__ import annotations

import json
import aiosqlite
import pytest

NOW = "2026-05-18T10:00:00"


@pytest.fixture
async def app(tmp_path, monkeypatch):
    monkeypatch.setenv("GOALCAST_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("GOALCAST_JWT_SECRET", "test-secret-not-prod")
    monkeypatch.setenv("ODDALERTS_API_KEY", "ci-stub")
    import importlib, database, main, services.auth
    importlib.reload(database)
    await database.init_db()
    importlib.reload(services.auth)

    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        await db.execute(
            "INSERT INTO competitions (id, name_en, name_zh) VALUES (500, 'EPL', '英超')"
        )
        for fid in (10, 11, 12):
            await db.execute(
                """INSERT INTO fixtures (id, competition_id, competition_name,
                   home_team, away_team, kickoff_utc, status, fetched_at, updated_at)
                   VALUES (?, 500, 'EPL', 'A', 'B', '2026-05-19T15:00:00', 'NS', ?, ?)""",
                (fid, NOW, NOW),
            )
        # One FT fixture to verify only_upcoming filter.
        await db.execute(
            """INSERT INTO fixtures (id, competition_id, competition_name,
               home_team, away_team, score_home, score_away,
               kickoff_utc, status, fetched_at, updated_at)
               VALUES (99, 500, 'EPL', 'X', 'Y', 2, 0, '2026-05-10T15:00:00', 'FT', ?, ?)""",
            (NOW, NOW),
        )

        seeds = [
            (10, "GS-Mispricing",  "v1.0", "public", json.dumps({"delta_pct": 8.0, "selection": "home"}), 0.80),
            (10, "GS-LineMove",    "v1.0", "member", json.dumps({"selection": "home", "move_pct": -12.0, "open_odds": 2.5, "current_odds": 2.2}), 0.60),
            (11, "GS-Mispricing",  "v1.0", "public", json.dumps({"delta_pct": 5.0, "selection": "away"}), 0.50),
            (12, "GS-SharpSquare", "v1.0", "member", json.dumps({"selection": "draw", "delta_pct": 7.0, "pinnacle_pct": 28.0, "bet365_pct": 21.0}), 0.70),
            (99, "GS-Mispricing",  "v1.0", "public", json.dumps({"delta_pct": 9.0, "selection": "home"}), 0.90),
        ]
        for fid, st, sv, sc, vj, strength in seeds:
            await db.execute(
                """INSERT INTO signals_snapshot
                     (fixture_id, signal_type, signal_version, waypoint,
                      scope, value_json, strength, captured_at)
                   VALUES (?, ?, ?, 'kickoff', ?, ?, ?, ?)""",
                (fid, st, sv, sc, vj, strength, NOW),
            )
        await db.commit()

    importlib.reload(main)
    return main.app


@pytest.mark.asyncio
async def test_get_by_type_returns_only_that_signal_with_meta(app):
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/signals/GS-Mispricing", params={"only_upcoming": "true"})
    assert r.status_code == 200
    d = r.json()
    assert d["signal_type"] == "GS-Mispricing"
    assert all(it["signal_type"] == "GS-Mispricing" for it in d["items"])
    # 2 NS fixtures (10 + 11); FT fixture 99 excluded by only_upcoming.
    assert d["count"] == 2
    assert d["items"][0]["fixture_id"] == 10  # strength desc → 0.80 first
    assert d["items"][0]["competition_name_zh"] == "英超"
    assert d["items"][0]["value"]["selection"] == "home"


@pytest.mark.asyncio
async def test_get_by_type_min_strength_filter(app):
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/signals/GS-Mispricing", params={"min_strength": 0.6})
    assert r.json()["count"] == 1  # only fixture 10 (0.80) qualifies


@pytest.mark.asyncio
async def test_get_by_type_rejects_non_gs_prefix(app):
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/signals/Foo-Bar")
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_active_ranks_across_signal_types(app):
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/signals/active", params={"min_strength": 0.0})
    d = r.json()
    types = [it["signal_type"] for it in d["items"]]
    assert "GS-Mispricing" in types
    assert "GS-LineMove" in types
    assert "GS-SharpSquare" in types
    # FT fixture 99 excluded by only_upcoming default.
    assert all(it["fixture_id"] != 99 for it in d["items"])
    strengths = [it["strength"] for it in d["items"]]
    assert strengths == sorted(strengths, reverse=True)


@pytest.mark.asyncio
async def test_active_only_upcoming_can_be_disabled(app):
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/signals/active",
                         params={"only_upcoming": "false", "min_strength": 0.0})
    fids = {it["fixture_id"] for it in r.json()["items"]}
    assert 99 in fids

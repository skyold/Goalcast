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


# --- Phase 1 of signal-catalog-and-subscriptions PRD --------------------------

@pytest.mark.asyncio
async def test_catalog_lists_every_registered_signal_with_metadata(app):
    """Catalog returns one row per REGISTERED signal with full ClassVar metadata."""
    from httpx import AsyncClient, ASGITransport
    from services.signals import REGISTERED
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/signals/catalog", params={"locale": "zh"})
    assert r.status_code == 200
    d = r.json()
    assert d["locale"] == "zh"
    types_returned = {it["signal_type"] for it in d["items"]}
    types_registered = {s.signal_type for s in REGISTERED}
    assert types_returned == types_registered
    for it in d["items"]:
        # ClassVar contract pass-through
        assert it["description"]
        assert it["output_schema"]
        assert it["strength_formula"]
        assert it["failure_modes"]
        # signal-version + scope present
        assert it["signal_version"]
        assert it["scope"] in ("public", "member")
        # forward-compat null until Phase 4
        assert it["house_book"] is None


@pytest.mark.asyncio
async def test_catalog_includes_methodology_after_seed(app):
    """After seed_methodology(), each item has methodology_md + updated_at populated."""
    from httpx import AsyncClient, ASGITransport
    from scripts.seed_methodology import seed_methodology
    await seed_methodology()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r_zh = await c.get("/api/signals/catalog", params={"locale": "zh"})
        r_en = await c.get("/api/signals/catalog", params={"locale": "en"})
    for d in (r_zh.json(), r_en.json()):
        for it in d["items"]:
            assert it["methodology_md"] is not None, f"{it['signal_type']}: no methodology"
            assert it["methodology_updated_at"] is not None
    # Body is locale-specific — zh body must differ from en body.
    z = {it["signal_type"]: it["methodology_md"] for it in r_zh.json()["items"]}
    e = {it["signal_type"]: it["methodology_md"] for it in r_en.json()["items"]}
    for st in z:
        assert z[st] != e[st], f"{st}: zh body == en body (locale routing broken)"


@pytest.mark.asyncio
async def test_catalog_methodology_null_when_not_seeded(app):
    """Without running seed, methodology fields are None but item still appears."""
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/signals/catalog")
    for it in r.json()["items"]:
        assert it["methodology_md"] is None
        assert it["methodology_updated_at"] is None
        # Metadata from ClassVars must still be present.
        assert it["description"]


@pytest.mark.asyncio
async def test_catalog_includes_7d_stats_from_signals_snapshot(app):
    """stats_7d reflects actual signals_snapshot rows (the app fixture seeded
    5 rows across 3 signal types)."""
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/signals/catalog")
    by_type = {it["signal_type"]: it for it in r.json()["items"]}

    misp = by_type["GS-Mispricing"]["stats_7d"]
    assert misp is not None
    # 3 GS-Mispricing rows seeded: strengths 0.80, 0.50, 0.90.
    assert misp["triggered"] == 3
    assert misp["max_strength"] == pytest.approx(0.90)
    assert misp["avg_strength"] == pytest.approx((0.80 + 0.50 + 0.90) / 3, abs=0.001)

    # GS-KEN-HT-EV is registered but has no signals_snapshot rows → stats_7d is None.
    ht_ev = by_type["GS-KEN-HT-EV"]
    assert ht_ev["stats_7d"] is None


@pytest.mark.asyncio
async def test_catalog_default_locale_is_zh(app):
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/signals/catalog")
    assert r.json()["locale"] == "zh"


@pytest.mark.asyncio
async def test_catalog_rejects_invalid_locale(app):
    """FastAPI Literal[zh|en] enforces this — anything else 422."""
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/signals/catalog", params={"locale": "fr"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_catalog_does_not_shadow_signal_type_route(app):
    """Critical: /signals/catalog must NOT be matched by /signals/{signal_type}.
    If route order was wrong, GET /signals/catalog would hit get_by_type with
    signal_type='catalog' and return a 400 (must start with GS-)."""
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/signals/catalog")
    assert r.status_code == 200
    # And the shape is the catalog shape, not the by_type shape:
    body = r.json()
    assert "items" in body and "locale" in body
    assert "signal_type" not in body  # by_type returns top-level signal_type


# --- Phase 3 backtest endpoint ------------------------------------------------

@pytest.mark.asyncio
async def test_backtest_default_window_returns_result_shape(app):
    """POST returns BacktestResult shape even when nothing settles.

    The app fixture seeds 1 FT fixture (id=99) with a GS-Mispricing snapshot
    but no historical_odds → considered=1, settled=0 (no Pinnacle odds to
    settle against). End-to-end arithmetic is covered in test_signals_backtest.py;
    here we just verify the endpoint plumbing returns the expected shape.
    """
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/signals/GS-Mispricing/backtest", json={})
    assert r.status_code == 200
    d = r.json()
    assert d["signal_type"] == "GS-Mispricing"
    assert d["window"] == "30d"
    assert d["match_scope"] == "all"
    assert d["considered_count"] == 1
    assert d["settled_count"] == 0
    assert d["roi_pct"] is None
    assert d["equity_curve"] == []


@pytest.mark.asyncio
async def test_backtest_rejects_non_gs_prefix(app):
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/signals/Foo-Bar/backtest", json={})
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_backtest_rejects_invalid_window(app):
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/signals/GS-Mispricing/backtest", json={"window": "60d"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_backtest_rejects_invalid_match_scope(app):
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/signals/GS-Mispricing/backtest", json={"match_scope": "country"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_backtest_my_leagues_without_login_401(app):
    """match_scope='my_leagues' requires login — anon → 401, not silent fall-through."""
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/signals/GS-Mispricing/backtest", json={"match_scope": "my_leagues"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_backtest_passes_conditions_to_evaluator(app):
    """Endpoint forwards conditions intact (smoke test for plumbing —
    settlement arithmetic already covered in test_signals_backtest.py)."""
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            "/api/signals/GS-Mispricing/backtest",
            json={"conditions": {"strength_min": 0.5}, "window": "7d"},
        )
    assert r.status_code == 200
    assert r.json()["window"] == "7d"

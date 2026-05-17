"""Phase 3 Sharp/Square divergence alerts — unit + integration tests."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
import aiosqlite
from httpx import AsyncClient, ASGITransport


@pytest.fixture
async def app(tmp_path, monkeypatch):
    monkeypatch.setenv("GOALCAST_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("GOALCAST_JWT_SECRET", "test-secret-not-prod")
    monkeypatch.setenv("ODDALERTS_API_KEY", "ci-stub")
    import importlib, database, main, services.auth, services.alerts
    importlib.reload(database)
    await database.init_db()
    importlib.reload(services.auth)
    importlib.reload(services.alerts)

    now = datetime.now(timezone.utc)
    # Fixture A (comp 100): wide divergence between Pinnacle and Bet365 (~14% delta).
    # Fixture B (comp 200): tight markets (<1% delta) — must NOT alert at 5% threshold.
    kickoff_a = (now + timedelta(hours=3)).isoformat()
    kickoff_b = (now + timedelta(hours=4)).isoformat()
    fetched = now.isoformat()
    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        await db.executemany(
            """INSERT INTO fixtures
               (id, competition_id, competition_name, home_team, away_team,
                kickoff_utc, status, fetched_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, 'NS', ?, ?)""",
            [
                (100, 100, 'League A', 'A1', 'A2', kickoff_a, fetched, fetched),
                (200, 200, 'League B', 'B1', 'B2', kickoff_b, fetched, fetched),
            ],
        )
        await db.executemany(
            """INSERT INTO bookmaker_odds
               (fixture_id, bookmaker_id, market_id, outcome, opening, current, peak, opening_at, current_at)
               VALUES (?, ?, 6, ?, ?, ?, ?, ?, ?)""",
            [
                # Fixture A — Pinnacle (sharp)
                (100, 1, 'home', 1.80, 1.80, 1.80, fetched, fetched),
                (100, 1, 'draw', 3.50, 3.50, 3.50, fetched, fetched),
                (100, 1, 'away', 5.00, 5.00, 5.00, fetched, fetched),
                # Fixture A — Bet365 (square, diverged)
                (100, 2, 'home', 2.40, 2.40, 2.40, fetched, fetched),
                (100, 2, 'draw', 3.20, 3.20, 3.20, fetched, fetched),
                (100, 2, 'away', 3.20, 3.20, 3.20, fetched, fetched),
                # Fixture B — both tight
                (200, 1, 'home', 2.00, 2.00, 2.00, fetched, fetched),
                (200, 1, 'draw', 3.40, 3.40, 3.40, fetched, fetched),
                (200, 1, 'away', 4.00, 4.00, 4.00, fetched, fetched),
                (200, 2, 'home', 2.02, 2.02, 2.02, fetched, fetched),
                (200, 2, 'draw', 3.40, 3.40, 3.40, fetched, fetched),
                (200, 2, 'away', 3.95, 3.95, 3.95, fetched, fetched),
            ],
        )
        await db.commit()

    importlib.reload(main)
    return main.app


# ---------- unit: compute_divergence ----------

def test_compute_divergence_basic():
    from services.alerts import compute_divergence
    div = compute_divergence(
        {"home": 1.80, "draw": 3.50, "away": 5.00},
        {"home": 2.40, "draw": 3.20, "away": 3.20},
    )
    assert "max_outcome" in div
    assert abs(div["max_delta_pct"]) > 10
    assert sum(div["pinnacle_implied"].values()) == pytest.approx(1.0, abs=1e-9)
    assert sum(div["bet365_implied"].values()) == pytest.approx(1.0, abs=1e-9)


def test_compute_divergence_rejects_invalid_odds():
    from services.alerts import compute_divergence
    with pytest.raises(ValueError):
        compute_divergence(
            {"home": 1.80, "draw": 3.50, "away": 5.00},
            {"home": 0, "draw": 3.20, "away": 3.20},
        )


# ---------- integration ----------

@pytest.mark.asyncio
async def test_scan_writes_alert_for_user_with_pref(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post("/api/auth/signup", json={"email": "u@x.com", "password": "secret123"})
        await c.put("/api/me/competitions", json={"competition_ids": [100, 200]})
        r = await c.post("/api/me/alerts/scan")
    assert r.status_code == 200
    assert r.json()["inserted"] == 1


@pytest.mark.asyncio
async def test_alerts_listed_with_payload(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post("/api/auth/signup", json={"email": "u@x.com", "password": "secret123"})
        await c.put("/api/me/competitions", json={"competition_ids": [100]})
        await c.post("/api/me/alerts/scan")
        r = await c.get("/api/me/alerts")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 1
    a = body["items"][0]
    assert a["alert_type"] == "sharp_square_divergence"
    assert "max_delta_pct" in a["payload"]
    assert "pinnacle_odds" in a["payload"] and "bet365_odds" in a["payload"]


@pytest.mark.asyncio
async def test_30min_dedupe(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post("/api/auth/signup", json={"email": "u@x.com", "password": "secret123"})
        await c.put("/api/me/competitions", json={"competition_ids": [100]})
        r1 = await c.post("/api/me/alerts/scan")
        r2 = await c.post("/api/me/alerts/scan")
    assert r1.json()["inserted"] == 1
    assert r2.json()["inserted"] == 0


@pytest.mark.asyncio
async def test_threshold_gating(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post("/api/auth/signup", json={"email": "u@x.com", "password": "secret123"})
        await c.put("/api/me/competitions", json={"competition_ids": [100, 200]})
        await c.put("/api/me/alert-settings", json={"divergence_threshold": 25.0, "enabled": True})
        r = await c.post("/api/me/alerts/scan")
    assert r.json()["inserted"] == 0


@pytest.mark.asyncio
async def test_disabled_user_no_alerts(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post("/api/auth/signup", json={"email": "u@x.com", "password": "secret123"})
        await c.put("/api/me/competitions", json={"competition_ids": [100]})
        await c.put("/api/me/alert-settings", json={"divergence_threshold": 5.0, "enabled": False})
        r = await c.post("/api/me/alerts/scan")
    assert r.json()["inserted"] == 0


@pytest.mark.asyncio
async def test_prefs_filter(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post("/api/auth/signup", json={"email": "u@x.com", "password": "secret123"})
        await c.put("/api/me/competitions", json={"competition_ids": [200]})
        r = await c.post("/api/me/alerts/scan")
    assert r.json()["inserted"] == 0


@pytest.mark.asyncio
async def test_dismiss_removes_from_list(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post("/api/auth/signup", json={"email": "u@x.com", "password": "secret123"})
        await c.put("/api/me/competitions", json={"competition_ids": [100]})
        await c.post("/api/me/alerts/scan")
        listing = await c.get("/api/me/alerts")
        aid = listing.json()["items"][0]["id"]
        r = await c.post(f"/api/me/alerts/{aid}/dismiss")
        assert r.status_code == 204
        again = await c.get("/api/me/alerts")
    assert again.json()["count"] == 0


@pytest.mark.asyncio
async def test_endpoints_require_auth(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        assert (await c.get("/api/me/alerts")).status_code == 401
        assert (await c.post("/api/me/alerts/scan")).status_code == 401
        assert (await c.get("/api/me/alert-settings")).status_code == 401
        assert (await c.put("/api/me/alert-settings", json={"divergence_threshold": 5.0, "enabled": True})).status_code == 401


@pytest.mark.asyncio
async def test_alert_settings_default_and_update_roundtrip(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post("/api/auth/signup", json={"email": "u@x.com", "password": "secret123"})
        d = await c.get("/api/me/alert-settings")
        assert d.status_code == 200
        assert d.json()["divergence_threshold"] == 5.0
        assert d.json()["enabled"] is True
        await c.put("/api/me/alert-settings", json={"divergence_threshold": 8.5, "enabled": False})
        r = await c.get("/api/me/alert-settings")
    assert r.json() == {"divergence_threshold": 8.5, "enabled": False}

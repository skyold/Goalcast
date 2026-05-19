"""Tests for GET /api/paper-trading/books (Phase 4b)."""
from __future__ import annotations

import json
from datetime import datetime, timezone

import aiosqlite
import pytest


NOW = datetime.now(timezone.utc).isoformat()


@pytest.fixture
async def app(tmp_path, monkeypatch):
    monkeypatch.setenv("GOALCAST_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("GOALCAST_JWT_SECRET", "test-secret-not-prod")
    monkeypatch.setenv("ODDALERTS_API_KEY", "ci-stub")
    import importlib, database, main, services.auth
    importlib.reload(database)
    await database.init_db()
    importlib.reload(services.auth)

    # Seed: 1 House Book (manual, simulating bootstrap_books result) + 1 archived House Book.
    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        await db.execute(
            """INSERT INTO simulated_books
                 (user_id, name, signal_type, signal_version,
                  conditions_json, starting_units, match_scope, created_at)
               VALUES (0, 'House-GS-Mispricing', 'GS-Mispricing', 'v1.0',
                       ?, 100.0, 'all', ?)""",
            (json.dumps({"filters": [{"path": "value.delta_pct", "op": ">", "value": 5}]}), NOW),
        )
        await db.execute(
            """INSERT INTO simulated_books
                 (user_id, name, signal_type, signal_version,
                  conditions_json, starting_units, match_scope, created_at, archived_at)
               VALUES (0, 'House-Archived', 'GS-Mispricing', 'v1.0',
                       '{}', 100.0, 'all', ?, ?)""",
            (NOW, NOW),
        )
        # User 1 + their Personal Book.
        await db.execute("INSERT INTO users (id, email, password_hash) VALUES (1, 'u@x', 'h')")
        await db.execute(
            """INSERT INTO simulated_books
                 (user_id, name, signal_type, signal_version,
                  conditions_json, starting_units, match_scope, created_at)
               VALUES (1, 'mine-aggressive', 'GS-Mispricing', 'v1.0',
                       ?, 50.0, 'my_leagues', ?)""",
            (json.dumps({"filters": [{"path": "value.delta_pct", "op": ">", "value": 8}]}), NOW),
        )
        # Add a fixture for settled bet, then a settled bet on House-GS-Mispricing (book_id=1).
        await db.execute(
            """INSERT INTO fixtures (id, competition_id, competition_name,
               home_team, away_team, kickoff_utc, status, score_home, score_away,
               fetched_at, updated_at)
               VALUES (10, 1, 'L', 'A', 'B', ?, 'FT', 2, 0, ?, ?)""",
            (NOW, NOW, NOW),
        )
        await db.execute(
            """INSERT INTO simulated_bets
                 (book_id, book_type, user_id, fixture_id, selection,
                  stake_units, entry_odds, entry_at, entry_waypoint,
                  signal_type, signal_version, outcome, pnl_units, settled_at)
               VALUES (1, 'house_5pct', 0, 10, 'home',
                       1.0, 2.10, ?, 'kickoff',
                       'GS-Mispricing', 'v1.0', 'win', 1.10, ?)""",
            (NOW, NOW),
        )
        await db.commit()

    importlib.reload(main)
    return main.app


@pytest.mark.asyncio
async def test_anon_sees_only_house_books(app):
    """Anonymous request → only user_id=0 Books, archived excluded by default."""
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/paper-trading/books")
    assert r.status_code == 200
    d = r.json()
    user_ids = {it["user_id"] for it in d["items"]}
    assert user_ids == {0}
    names = {it["name"] for it in d["items"]}
    assert "House-Archived" not in names  # archived hidden by default


@pytest.mark.asyncio
async def test_include_archived_query(app):
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/paper-trading/books", params={"include_archived": "true"})
    names = {it["name"] for it in r.json()["items"]}
    assert "House-Archived" in names


@pytest.mark.asyncio
async def test_book_summary_attached(app):
    """House-GS-Mispricing has 1 settled win → summary.metrics.roi_pct = 110.0."""
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/paper-trading/books")
    item = next(it for it in r.json()["items"] if it["name"] == "House-GS-Mispricing")
    s = item["summary"]
    assert s["bets_settled"] == 1
    assert s["bankroll"]["start"] == 100.0
    assert s["bankroll"]["current"] == 101.10
    # Single graded win at +1.10 over 1.0 stake → ROI = 110%.
    assert s["metrics"]["roi_pct"] == pytest.approx(110.0)
    assert s["metrics"]["win_rate"] == pytest.approx(1.0)
    assert item["scope"] == "house"


@pytest.mark.asyncio
async def test_conditions_returned_as_object_not_string(app):
    """conditions_json is parsed at the API boundary; frontend receives an
    object, not a string."""
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/paper-trading/books")
    item = next(it for it in r.json()["items"] if it["name"] == "House-GS-Mispricing")
    assert isinstance(item["conditions"], dict)
    assert item["conditions"]["filters"][0]["op"] == ">"


@pytest.mark.asyncio
async def test_authenticated_user_sees_their_personal_books(app):
    """Login as user 1 → House Books + 'mine-aggressive' (user_id=1) visible."""
    from httpx import AsyncClient, ASGITransport
    from services.auth import create_token
    token = create_token(user_id=1)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test",
        cookies={"gc_token": token},
    ) as c:
        r = await c.get("/api/paper-trading/books")
    names = {it["name"] for it in r.json()["items"]}
    assert "House-GS-Mispricing" in names
    assert "mine-aggressive" in names


@pytest.mark.asyncio
async def test_other_users_personal_books_hidden(app, tmp_path):
    """Login as user 2 → must NOT see user 1's Personal Book."""
    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        await db.execute("INSERT INTO users (id, email, password_hash) VALUES (2, 'v@x', 'h')")
        await db.commit()
    from httpx import AsyncClient, ASGITransport
    from services.auth import create_token
    token = create_token(user_id=2)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test",
        cookies={"gc_token": token},
    ) as c:
        r = await c.get("/api/paper-trading/books")
    names = {it["name"] for it in r.json()["items"]}
    assert "mine-aggressive" not in names

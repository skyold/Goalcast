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


# --- Phase 4c CRUD endpoints --------------------------------------------------

def _user1_client(app):
    """Helper: return an AsyncClient authed as user 1."""
    from httpx import AsyncClient, ASGITransport
    from services.auth import create_token
    return AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test",
        cookies={"gc_token": create_token(user_id=1)},
    )


@pytest.mark.asyncio
async def test_create_book_requires_auth(app):
    """POST without cookie → 401."""
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/paper-trading/books", json={
            "name": "x", "signal_type": "GS-Mispricing", "signal_version": "v1.0",
        })
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_create_book_explicit_binding(app):
    """Bare construction with signal_type + signal_version → new Personal Book."""
    async with _user1_client(app) as c:
        r = await c.post("/api/paper-trading/books", json={
            "name": "my-experiment",
            "signal_type": "GS-LineMove",
            "signal_version": "v1.0",
            "starting_units": 50.0,
        })
    assert r.status_code == 201
    b = r.json()
    assert b["name"] == "my-experiment"
    assert b["scope"] == "personal"
    assert b["user_id"] == 1
    assert b["signal_type"] == "GS-LineMove"
    assert b["starting_units"] == 50.0
    assert b["match_scope"] == "my_leagues"  # default for Personal
    assert b["archived_at"] is None


@pytest.mark.asyncio
async def test_create_book_fork_inherits_signal_and_conditions(app):
    """fork_from a House Book copies signal_type/version/conditions/starting_units."""
    async with _user1_client(app) as c:
        # First list books to find House-GS-Mispricing id.
        r0 = await c.get("/api/paper-trading/books")
        house = next(it for it in r0.json()["items"] if it["name"] == "House-GS-Mispricing")
        r = await c.post("/api/paper-trading/books", json={
            "name": "fork-of-mispricing",
            "fork_from": house["id"],
        })
    assert r.status_code == 201
    b = r.json()
    assert b["signal_type"] == house["signal_type"]
    assert b["signal_version"] == house["signal_version"]
    assert b["conditions"] == house["conditions"]
    assert b["starting_units"] == house["starting_units"]


@pytest.mark.asyncio
async def test_create_book_fork_with_overrides(app):
    """fork_from + explicit conditions/starting_units → override the inherited values."""
    async with _user1_client(app) as c:
        r0 = await c.get("/api/paper-trading/books")
        house = next(it for it in r0.json()["items"] if it["name"] == "House-GS-Mispricing")
        r = await c.post("/api/paper-trading/books", json={
            "name": "fork-aggressive",
            "fork_from": house["id"],
            "conditions": {"filters": [{"path": "value.delta_pct", "op": ">", "value": 10}]},
            "starting_units": 200.0,
            "match_scope": "all",
        })
    b = r.json()
    assert b["conditions"]["filters"][0]["value"] == 10  # overridden
    assert b["starting_units"] == 200.0
    assert b["match_scope"] == "all"


@pytest.mark.asyncio
async def test_create_book_rejects_missing_signal_binding(app):
    """Neither fork_from nor signal_type → 422."""
    async with _user1_client(app) as c:
        r = await c.post("/api/paper-trading/books", json={"name": "naked"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_book_rejects_duplicate_name(app):
    """UNIQUE(user_id, name) → 409 on collision."""
    async with _user1_client(app) as c:
        r = await c.post("/api/paper-trading/books", json={
            "name": "mine-aggressive",  # pre-seeded for user 1
            "signal_type": "GS-Mispricing", "signal_version": "v1.0",
        })
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_create_book_rejects_bad_match_scope(app):
    async with _user1_client(app) as c:
        r = await c.post("/api/paper-trading/books", json={
            "name": "weird-scope",
            "signal_type": "GS-Mispricing", "signal_version": "v1.0",
            "match_scope": "europe-only",
        })
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_patch_book_updates_conditions(app):
    """PATCH the user's Personal Book — conditions field can be changed."""
    async with _user1_client(app) as c:
        r0 = await c.get("/api/paper-trading/books")
        mine = next(it for it in r0.json()["items"] if it["name"] == "mine-aggressive")
        r = await c.patch(f"/api/paper-trading/books/{mine['id']}", json={
            "conditions": {"strength_min": 0.7},
        })
    assert r.status_code == 200
    assert r.json()["conditions"] == {"strength_min": 0.7}


@pytest.mark.asyncio
async def test_patch_book_house_book_forbidden(app):
    """House Books cannot be PATCHed by any user (404 — invisible as personal)."""
    async with _user1_client(app) as c:
        r0 = await c.get("/api/paper-trading/books")
        house = next(it for it in r0.json()["items"] if it["name"] == "House-GS-Mispricing")
        r = await c.patch(f"/api/paper-trading/books/{house['id']}", json={
            "conditions": {"strength_min": 0.99},
        })
    # user_id=0 != current_user.id=1 → 404 (don't leak existence)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_patch_book_other_user_forbidden(app, tmp_path):
    """User 2 cannot PATCH user 1's Personal Book."""
    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        await db.execute("INSERT INTO users (id, email, password_hash) VALUES (2, 'v@x', 'h')")
        await db.commit()
    from httpx import AsyncClient, ASGITransport
    from services.auth import create_token
    async with _user1_client(app) as c:
        r0 = await c.get("/api/paper-trading/books")
        mine = next(it for it in r0.json()["items"] if it["name"] == "mine-aggressive")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test",
        cookies={"gc_token": create_token(user_id=2)},
    ) as c:
        r = await c.patch(f"/api/paper-trading/books/{mine['id']}", json={"name": "stolen"})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_patch_empty_body_is_noop(app):
    async with _user1_client(app) as c:
        r0 = await c.get("/api/paper-trading/books")
        mine = next(it for it in r0.json()["items"] if it["name"] == "mine-aggressive")
        r = await c.patch(f"/api/paper-trading/books/{mine['id']}", json={})
    assert r.status_code == 200
    assert r.json()["name"] == "mine-aggressive"


@pytest.mark.asyncio
async def test_delete_archives_book(app):
    """DELETE sets archived_at; default GET /books no longer surfaces it."""
    async with _user1_client(app) as c:
        r0 = await c.get("/api/paper-trading/books")
        mine = next(it for it in r0.json()["items"] if it["name"] == "mine-aggressive")
        r = await c.delete(f"/api/paper-trading/books/{mine['id']}")
        assert r.status_code == 200
        assert r.json()["archived_at"] is not None
        r2 = await c.get("/api/paper-trading/books")
        names = {it["name"] for it in r2.json()["items"]}
        assert "mine-aggressive" not in names
        r3 = await c.get("/api/paper-trading/books", params={"include_archived": "true"})
        names2 = {it["name"] for it in r3.json()["items"]}
        assert "mine-aggressive" in names2


@pytest.mark.asyncio
async def test_delete_house_book_forbidden(app):
    async with _user1_client(app) as c:
        r0 = await c.get("/api/paper-trading/books")
        house = next(it for it in r0.json()["items"] if it["name"] == "House-GS-Mispricing")
        r = await c.delete(f"/api/paper-trading/books/{house['id']}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_is_idempotent(app):
    """Second DELETE on already-archived book → 200, archived_at preserved."""
    async with _user1_client(app) as c:
        r0 = await c.get("/api/paper-trading/books")
        mine = next(it for it in r0.json()["items"] if it["name"] == "mine-aggressive")
        r1 = await c.delete(f"/api/paper-trading/books/{mine['id']}")
        first_archived_at = r1.json()["archived_at"]
        r2 = await c.delete(f"/api/paper-trading/books/{mine['id']}")
    assert r2.status_code == 200
    assert r2.json()["archived_at"] == first_archived_at

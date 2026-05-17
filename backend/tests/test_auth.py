"""Auth flow tests: signup, login, /me, logout, error cases."""
import pytest
from httpx import AsyncClient, ASGITransport


@pytest.fixture
async def app(tmp_path, monkeypatch):
    monkeypatch.setenv("GOALCAST_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("GOALCAST_JWT_SECRET", "test-secret-not-prod")
    import importlib, database, main
    importlib.reload(database)
    await database.init_db()
    # services.auth caches JWT_SECRET at module import — reload so env var takes effect.
    import services.auth
    importlib.reload(services.auth)
    importlib.reload(main)
    return main.app


@pytest.mark.asyncio
async def test_signup_sets_cookie_and_returns_user(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/auth/signup", json={"email": "a@b.com", "password": "secret123"})
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "a@b.com"
    assert isinstance(body["id"], int)
    assert "gc_token" in r.cookies


@pytest.mark.asyncio
async def test_signup_duplicate_email_409(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post("/api/auth/signup", json={"email": "a@b.com", "password": "secret123"})
        r = await c.post("/api/auth/signup", json={"email": "a@b.com", "password": "different1"})
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_signup_weak_password_rejected(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/auth/signup", json={"email": "a@b.com", "password": "short"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_login_wrong_password_401(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post("/api/auth/signup", json={"email": "a@b.com", "password": "secret123"})
        r = await c.post("/api/auth/login", json={"email": "a@b.com", "password": "WRONGPWD!"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email_401(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/auth/login", json={"email": "ghost@nope.com", "password": "secret123"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_me_with_cookie_returns_user(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        signup = await c.post("/api/auth/signup", json={"email": "a@b.com", "password": "secret123"})
        # AsyncClient persists cookies across requests in the same client.
        r = await c.get("/api/auth/me")
    assert r.status_code == 200
    assert r.json()["email"] == "a@b.com"
    assert r.json()["id"] == signup.json()["id"]


@pytest.mark.asyncio
async def test_me_without_cookie_401(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/auth/me")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_logout_clears_cookie(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post("/api/auth/signup", json={"email": "a@b.com", "password": "secret123"})
        await c.post("/api/auth/logout")
        r = await c.get("/api/auth/me")
    assert r.status_code == 401

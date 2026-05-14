import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path, monkeypatch):
    """Point the browse router's cache at a temp DB for each test."""
    from utils.cache import Cache
    import server.routes.browse as browse_mod

    monkeypatch.setattr(browse_mod, "_cache", Cache(tmp_path / "cache.db"))
    yield


@pytest.fixture
def client():
    from server.server import app
    return TestClient(app)


def test_competitions_endpoint_returns_list(client):
    fake = {"data": [{"id": 8, "name": "Premier League", "country": "England"}]}
    with patch("provider.oddalerts.client.OddAlertsProvider.get_competitions",
               AsyncMock(return_value=fake)):
        r = client.get("/api/competitions")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    assert body[0]["name"] == "Premier League"


def test_competitions_cached_on_second_call(client):
    fake = {"data": [{"id": 8, "name": "PL", "country": "ENG"}]}
    with patch("provider.oddalerts.client.OddAlertsProvider.get_competitions",
               AsyncMock(return_value=fake)) as mock:
        client.get("/api/competitions")
        client.get("/api/competitions")
        assert mock.await_count == 1


def test_fixtures_endpoint_filters_by_date(client):
    fake = {"data": [
        {"id": 1, "fixture_name": "A vs B", "starting_at": "2026-05-14T20:00:00Z",
         "league": {"id": 8, "name": "PL"}, "drop_percentage": -8.0,
         "closing": 1.72, "opening": 1.87},
        {"id": 2, "fixture_name": "C vs D", "starting_at": "2026-05-15T20:00:00Z",
         "league": {"id": 8, "name": "PL"}},
    ]}
    with patch("provider.oddalerts.client.OddAlertsProvider.get_dropping_odds",
               AsyncMock(return_value=fake)):
        r = client.get("/api/fixtures?date=2026-05-14")
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    assert items[0]["fixture_id"] == 1

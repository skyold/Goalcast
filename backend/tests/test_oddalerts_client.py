import pytest
from pytest_httpx import HTTPXMock

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("ODDALERTS_API_KEY", "TESTKEY")
    import importlib, config, services.oddalerts as oa
    importlib.reload(config); importlib.reload(oa)
    return oa.OddAlertClient()

@pytest.mark.asyncio
async def test_get_upcoming_fixtures(client, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://data.oddalerts.com/api/fixtures/upcoming?api_token=TESTKEY&page=1&per_page=250",
        json={"info": {"total": 2}, "data": [{"id": 1, "home_name": "A"}, {"id": 2, "home_name": "B"}]})
    items = await client.get_upcoming_fixtures(page=1, per_page=250)
    assert len(items) == 2 and items[0]["id"] == 1
    await client.aclose()

@pytest.mark.asyncio
async def test_get_season_stats_last_x(client, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://data.oddalerts.com/api/stats/season/999?api_token=TESTKEY&last_x=5_overall",
        json={"info": {"total": 1}, "data": [{"team_id": 11, "played": {"total": 5}, "won": {"total": 3}}]})
    rows = await client.get_season_stats_last_x(999, n=5)
    assert rows[0]["team_id"] == 11
    await client.aclose()

@pytest.mark.asyncio
async def test_get_odds_history_by_path(client, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://data.oddalerts.com/api/odds/history/77?api_token=TESTKEY",
        json={"info": {"count": 1}, "data": [{"fixture_id": 77, "market_id": 51, "outcome": "home_m05",
                                                "opening": "1.90", "closing": "1.85", "peak": "1.95",
                                                "bookmaker_id": 1, "bookmaker_name": "Pinnacle"}]})
    rows = await client.get_odds_history_by_path(77)
    assert rows[0]["outcome"] == "home_m05"
    await client.aclose()

@pytest.mark.asyncio
async def test_get_odds_history_handles_false_body(client, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://data.oddalerts.com/api/odds/history/77?api_token=TESTKEY",
        json=False)
    rows = await client.get_odds_history_by_path(77)
    assert rows == []
    await client.aclose()

@pytest.mark.asyncio
async def test_get_odds_latest(client, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://data.oddalerts.com/api/odds/latest?api_token=TESTKEY&bookmakers=1%2C2&markets=6%2C51&per_page=500&page=1",
        json={"info": {"page": 1}, "data": [{"fixture_id": 77, "market_id": 6, "outcome": "home",
                                              "odds": 1.95, "unix": 1779000000, "bookmaker_id": 1,
                                              "bookmaker_name": "Pinnacle"}]})
    rows = await client.get_odds_latest(bookmakers="1,2", markets="6,51", per_page=500, page=1)
    assert rows[0]["fixture_id"] == 77
    await client.aclose()

@pytest.mark.asyncio
async def test_get_predictions_multiple(client, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://data.oddalerts.com/api/predictions/generate/multiple?api_token=TESTKEY&ids=1%2C2",
        json={"info": {"results": 2}, "data": [{"fixture_id": 1, "simulations": 50000, "home_win": 28000},
                                                 {"fixture_id": 2, "simulations": 50000, "home_win": 18000}]})
    rows = await client.get_predictions_multiple([1, 2])
    assert len(rows) == 2
    await client.aclose()

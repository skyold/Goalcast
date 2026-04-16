import pytest

from mcp_server.tools import footystats as footystats_tools


class FakeMCP:
    def __init__(self):
        self.tools = {}

    def tool(self, **kwargs):
        def decorator(func):
            self.tools[func.__name__] = func
            return func

        return decorator


class FakeFootyStatsProvider:
    def __init__(self):
        self.calls = []

    def get_todays_matches(self, date, timezone=None):
        self.calls.append((date, timezone))
        return {
            "data": [
                {
                    "home_name": "Arsenal",
                    "away_name": "Chelsea",
                    "competition_name": "Premier League",
                    "date_unix": 1776270000,
                    "id": 1001,
                    "homeID": 1,
                    "awayID": 2,
                    "competition_id": 2001,
                }
            ]
        }


def test_register_goalcast_footystats_tools_registers_expected_names():
    fake_mcp = FakeMCP()
    footystats_tools.register_goalcast_footystats_tools(fake_mcp)

    assert set(fake_mcp.tools) == {
        "goalcast_footystats_resolve_match",
        "goalcast_footystats_get_todays_matches",
    }


@pytest.mark.asyncio
async def test_goalcast_footystats_get_todays_matches_normalizes_fixtures(monkeypatch):
    fake_mcp = FakeMCP()
    provider = FakeFootyStatsProvider()

    async def fake_handle_api_call(provider_name, coro):
        assert provider_name == "FootyStats"
        return coro

    monkeypatch.setattr(footystats_tools, "get_footystats", lambda: provider)
    monkeypatch.setattr(footystats_tools, "handle_api_call", fake_handle_api_call)

    footystats_tools.register_goalcast_footystats_tools(fake_mcp)

    result = await fake_mcp.tools["goalcast_footystats_get_todays_matches"](
        date="2026-04-15",
        league_filter="Premier League",
    )

    assert result[0]["home_team"] == "Arsenal"
    assert result[0]["season_id"] == "2001"
    assert provider.calls == [("2026-04-15", None)]


@pytest.mark.asyncio
async def test_goalcast_footystats_resolve_match_builds_context(monkeypatch):
    fake_mcp = FakeMCP()

    class FakeContext:
        def to_dict(self):
            return {"match_id": "1001", "overall_quality": 0.8}

    class FakeFusion:
        def __init__(self, footystats, understat):
            self.footystats = footystats
            self.understat = understat

        async def build(self, **kwargs):
            assert kwargs["match_id"] == "1001"
            assert kwargs["league"] == "Premier League"
            return FakeContext()

    monkeypatch.setattr(footystats_tools, "DataFusion", FakeFusion)
    monkeypatch.setattr(footystats_tools, "get_footystats", lambda: object())
    monkeypatch.setattr(footystats_tools, "get_understat", lambda: object())

    footystats_tools.register_goalcast_footystats_tools(fake_mcp)

    result = await fake_mcp.tools["goalcast_footystats_resolve_match"](
        match_id="1001",
        home_team="Arsenal",
        home_team_id="1",
        away_team="Chelsea",
        away_team_id="2",
        season_id="2001",
        league="Premier League",
        match_date="2026-04-15",
    )

    assert result == {"match_id": "1001", "overall_quality": 0.8}

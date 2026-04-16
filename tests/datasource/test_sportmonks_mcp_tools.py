import pytest

from mcp_server.tools.sportmonks import register_goalcast_sportmonks_tools

class FakeMCP:
    def __init__(self):
        self.tools = {}
        self.tool_meta = {}

    def tool(self, **kwargs):
        def decorator(func):
            self.tools[func.__name__] = func
            self.tool_meta[func.__name__] = kwargs
            return func

        return decorator

class FakeService:
    def __init__(self):
        self.calls = []

    async def get_matches(self, date=None, leagues=None):
        self.calls.append(("get_matches", date, leagues))
        return [
            {
                "id": 19374628,
                "league": {"name": "Premier League"},
                "participants": [
                    {"name": "Arsenal", "meta": {"location": "home"}},
                    {"name": "Chelsea", "meta": {"location": "away"}}
                ]
            }
        ]

    async def get_match_for_analysis(self, fixture_id, match_date=None):
        self.calls.append(("get_match_for_analysis", fixture_id, match_date))
        return {
            "fixture": {"id": fixture_id},
            "odds": {"home_win": 1.5},
            "predictions": {"home": 0.6},
            "h2h": [{"home": "Arsenal"}],
            "standings": [{"team_id": 1}]
        }


@pytest.mark.asyncio
async def test_goalcast_sportmonks_get_matches():
    mcp = FakeMCP()
    service = FakeService()
    register_goalcast_sportmonks_tools(mcp, lambda: service)

    tool_func = mcp.tools["goalcast_sportmonks_get_matches"]
    result = await tool_func(date="2026-04-15", leagues=["Premier League"])

    assert result["ok"] is True
    assert result["count"] == 1
    assert result["data"][0]["id"] == 19374628
    assert ("get_matches", "2026-04-15", ["Premier League"]) in service.calls


@pytest.mark.asyncio
async def test_goalcast_sportmonks_get_match():
    mcp = FakeMCP()
    service = FakeService()
    register_goalcast_sportmonks_tools(mcp, lambda: service)

    tool_func = mcp.tools["goalcast_sportmonks_get_match"]
    result = await tool_func(fixture_id=19374628)

    assert result["ok"] is True
    assert result["data"]["fixture"]["id"] == 19374628
    assert result["data"]["odds"]["home_win"] == 1.5
    assert ("get_match_for_analysis", 19374628, None) in service.calls

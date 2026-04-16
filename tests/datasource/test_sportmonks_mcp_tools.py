import pytest

from datasource.sportmonks.models import (
    SportmonksFixtureSummary,
    SportmonksMatchSnapshot,
)
from mcp_server.tools.sportmonks import (
    register_goalcast_sportmonks_tools,
)


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
            SportmonksFixtureSummary(
                fixture_id=19374628,
                match_date=date or "2026-04-15",
                kickoff_time="2026-04-15T19:00:00Z",
                league_id=8,
                league_name="Premier League",
                season_id=23614,
                home_team_id=1,
                home_team_name="Arsenal",
                away_team_id=2,
                away_team_name="Chelsea",
                cache_status="fresh",
                last_updated_at="2026-04-15T10:00:00Z",
            )
        ]

    async def get_match_for_analysis(self, fixture_id, match_date=None):
        self.calls.append(("get_match_for_analysis", fixture_id, match_date))
        return SportmonksMatchSnapshot(
            fixture_id=fixture_id,
            match_date=match_date or "2026-04-15",
            kickoff_time="2026-04-15T19:00:00Z",
            league="Premier League",
            season_id=23614,
            home_team="Arsenal",
            away_team="Chelsea",
            home_team_id=1,
            away_team_id=2,
            xg={"home_xg_for": 1.8, "away_xg_for": 1.1},
            standings={"data": [{"position": 1}]},
            odds={"home_win": 1.91, "draw": 3.45, "away_win": 4.10},
            asian_handicap={"home": -0.5, "away": 0.5},
            odds_movement={"home_open": 1.95, "home_current": 1.91},
            lineups={"home_formation": "4-3-3", "away_formation": "4-4-2"},
            h2h=[{"date": "2026-01-01", "score": "2-1"}],
            predictions={"home": 0.52, "draw": 0.25, "away": 0.23},
            available_layers=("xg", "odds"),
            missing_layers=(),
            cache_status="fresh",
            overall_quality=0.92,
            warmed_at="2026-04-15T10:00:00Z",
            updated_at="2026-04-15T10:15:00Z",
            expires_at="2026-04-15T12:15:00Z",
            source_versions={"sportmonks": "v3"},
        )

def test_register_goalcast_sportmonks_tools_registers_all_expected_names():
    fake_mcp = FakeMCP()
    register_goalcast_sportmonks_tools(fake_mcp, service_factory=FakeService)

    assert set(fake_mcp.tools) == {
        "goalcast_sportmonks_get_matches",
        "goalcast_sportmonks_get_match",
    }
    assert "goalcast_sportmonks_prefetch" not in fake_mcp.tools
    assert "goalcast_sportmonks_refresh_match" not in fake_mcp.tools
    assert "goalcast_sportmonks_get_cache_status" not in fake_mcp.tools


def test_register_goalcast_sportmonks_tools_sets_explicit_mcp_descriptions():
    fake_mcp = FakeMCP()
    register_goalcast_sportmonks_tools(fake_mcp, service_factory=FakeService)

    assert "比赛列表" in fake_mcp.tool_meta["goalcast_sportmonks_get_matches"]["description"]
    assert "单场" in fake_mcp.tool_meta["goalcast_sportmonks_get_match"]["description"]
    assert "缓存" not in fake_mcp.tool_meta["goalcast_sportmonks_get_matches"]["description"]


@pytest.mark.asyncio
async def test_goalcast_sportmonks_get_matches_calls_service_and_serializes():
    fake_mcp = FakeMCP()
    service = FakeService()
    register_goalcast_sportmonks_tools(fake_mcp, service_factory=lambda: service)

    result = await fake_mcp.tools["goalcast_sportmonks_get_matches"](
        date="2026-04-15",
        leagues=["Premier League"],
    )

    assert result["ok"] is True
    assert result["count"] == 1
    assert result["data"][0]["fixture_id"] == 19374628
    assert service.calls == [("get_matches", "2026-04-15", ["Premier League"])]


@pytest.mark.asyncio
async def test_goalcast_sportmonks_get_match_uses_minimal_input_contract():
    fake_mcp = FakeMCP()
    service = FakeService()
    register_goalcast_sportmonks_tools(fake_mcp, service_factory=lambda: service)

    result = await fake_mcp.tools["goalcast_sportmonks_get_match"](
        fixture_id=19374628,
        match_date="2026-04-15",
    )

    assert result["ok"] is True
    assert result["data"]["fixture_id"] == 19374628
    assert result["data"]["league"] == "Premier League"
    assert service.calls == [("get_match_for_analysis", 19374628, "2026-04-15")]


def test_goalcast_sportmonks_get_match_signature_no_manual_context_fields():
    fake_mcp = FakeMCP()
    register_goalcast_sportmonks_tools(fake_mcp, service_factory=FakeService)

    params = fake_mcp.tools["goalcast_sportmonks_get_match"].__annotations__
    assert "home_team" not in params
    assert "away_team" not in params
    assert "season_id" not in params
    assert "league" not in params
    assert "match_date" in params

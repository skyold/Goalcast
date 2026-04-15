import pytest

from data_strategy.sportmonks.models import (
    SportmonksFixtureSummary,
    SportmonksMatchSnapshot,
    SportmonksWarmupResult,
)
from mcp_server.tools.goalcast_sportmonks import (
    legacy_goalcast_sm_fetch,
    legacy_goalcast_sm_get_fixtures,
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

    async def get_todays_matches(self, leagues=None, warm_if_missing=True):
        self.calls.append(("get_todays_matches", leagues, warm_if_missing))
        return [
            SportmonksFixtureSummary(
                fixture_id=19374628,
                match_date="2026-04-15",
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

    async def prefetch_today(self, leagues=None, refresh_stale=False):
        self.calls.append(("prefetch_today", leagues, refresh_stale))
        return SportmonksWarmupResult(
            date="2026-04-15",
            leagues=leagues or [],
            fixtures_found=1,
            fixtures_warmed=1,
            fixtures_partial=0,
            fixtures_failed=0,
            output_path="data/cache/sportmonks/2026-04-15",
            results=[{"fixture_id": 19374628, "cache_status": "fresh"}],
        )

    async def get_match(self, fixture_id, date=None, refresh_if_stale=True):
        self.calls.append(("get_match", fixture_id, date, refresh_if_stale))
        return SportmonksMatchSnapshot(
            fixture_id=fixture_id,
            match_date="2026-04-15",
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

    async def get_fixtures(self, date, leagues=None, warm_if_missing=True):
        self.calls.append(("get_fixtures", date, leagues, warm_if_missing))
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

    async def prefetch(self, date, leagues=None, refresh_stale=False):
        self.calls.append(("prefetch", date, leagues, refresh_stale))
        return {"date": date}

    async def refresh_match(self, fixture_id, date=None, layers=None):
        self.calls.append(("refresh_match", fixture_id, date, layers))
        return {"fixture_id": fixture_id}

    async def get_cache_status(self, date=None, fixture_id=None):
        self.calls.append(("get_cache_status", date, fixture_id))
        return {"date": date, "fixture_id": fixture_id}


def test_register_goalcast_sportmonks_tools_registers_all_expected_names():
    fake_mcp = FakeMCP()
    register_goalcast_sportmonks_tools(fake_mcp, service_factory=FakeService)

    assert set(fake_mcp.tools) == {
        "goalcast_sportmonks_get_todays_matches",
        "goalcast_sportmonks_prefetch_today",
        "goalcast_sportmonks_get_fixtures",
        "goalcast_sportmonks_prefetch",
        "goalcast_sportmonks_get_match",
        "goalcast_sportmonks_refresh_match",
        "goalcast_sportmonks_get_cache_status",
    }


def test_register_goalcast_sportmonks_tools_exposes_tool_docstrings():
    fake_mcp = FakeMCP()
    register_goalcast_sportmonks_tools(fake_mcp, service_factory=FakeService)

    assert "今日" in (fake_mcp.tools["goalcast_sportmonks_get_todays_matches"].__doc__ or "")
    assert "预热" in (fake_mcp.tools["goalcast_sportmonks_prefetch_today"].__doc__ or "")
    assert "单场" in (fake_mcp.tools["goalcast_sportmonks_get_match"].__doc__ or "")


def test_register_goalcast_sportmonks_tools_sets_explicit_mcp_descriptions():
    fake_mcp = FakeMCP()
    register_goalcast_sportmonks_tools(fake_mcp, service_factory=FakeService)

    assert "今日比赛列表" in fake_mcp.tool_meta["goalcast_sportmonks_get_todays_matches"]["description"]
    assert "预热今日比赛缓存" in fake_mcp.tool_meta["goalcast_sportmonks_prefetch_today"]["description"]
    assert "单场比赛快照" in fake_mcp.tool_meta["goalcast_sportmonks_get_match"]["description"]


@pytest.mark.asyncio
async def test_goalcast_sportmonks_get_todays_matches_calls_service_and_serializes():
    fake_mcp = FakeMCP()
    service = FakeService()
    register_goalcast_sportmonks_tools(fake_mcp, service_factory=lambda: service)

    result = await fake_mcp.tools["goalcast_sportmonks_get_todays_matches"](
        leagues=["Premier League"],
        warm_if_missing=False,
    )

    assert result["ok"] is True
    assert result["count"] == 1
    assert result["fixtures"][0]["fixture_id"] == 19374628
    assert service.calls == [("get_todays_matches", ["Premier League"], False)]


@pytest.mark.asyncio
async def test_goalcast_sportmonks_prefetch_today_calls_service():
    fake_mcp = FakeMCP()
    service = FakeService()
    register_goalcast_sportmonks_tools(fake_mcp, service_factory=lambda: service)

    result = await fake_mcp.tools["goalcast_sportmonks_prefetch_today"](
        leagues=["Premier League"],
        refresh_stale=True,
    )

    assert result["ok"] is True
    assert result["data"]["fixtures_warmed"] == 1
    assert service.calls == [("prefetch_today", ["Premier League"], True)]


@pytest.mark.asyncio
async def test_goalcast_sportmonks_get_match_calls_service_and_serializes_snapshot():
    fake_mcp = FakeMCP()
    service = FakeService()
    register_goalcast_sportmonks_tools(fake_mcp, service_factory=lambda: service)

    result = await fake_mcp.tools["goalcast_sportmonks_get_match"](
        fixture_id=19374628,
        date="2026-04-15",
        refresh_if_stale=False,
    )

    assert result["ok"] is True
    assert result["cache_status"] == "fresh"
    assert result["data"]["home_team"] == "Arsenal"
    assert service.calls == [("get_match", 19374628, "2026-04-15", False)]


@pytest.mark.asyncio
async def test_legacy_goalcast_sm_get_fixtures_preserves_old_shape():
    service = FakeService()

    result = await legacy_goalcast_sm_get_fixtures(
        service,
        leagues=["Premier League"],
        date="2026-04-15",
    )

    assert result["date"] == "2026-04-15"
    assert result["count"] == 1
    assert result["fixtures"][0]["fixture_id"] == 19374628
    assert result["fixtures"][0]["home_team"] == "Arsenal"
    assert result["fixtures"][0]["season_id"] == 23614


@pytest.mark.asyncio
async def test_legacy_goalcast_sm_fetch_adapts_snapshot_to_legacy_match_data_shape():
    service = FakeService()

    result = await legacy_goalcast_sm_fetch(
        service,
        fixture_id=19374628,
        home_team="Arsenal",
        home_team_id=1,
        away_team="Chelsea",
        away_team_id=2,
        season_id=23614,
        league="Premier League",
        match_date="2026-04-15",
        season="2025",
    )

    assert result["fixture_id"] == 19374628
    assert result["xg"]["home_xg_for"] == 1.8
    assert result["odds"]["home_win"] == 1.91
    assert result["asian_handicap"]["ah_line"] == -0.5
    assert result["overall_quality"] == 0.92

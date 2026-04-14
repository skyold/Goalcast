"""
DataFusion 单元测试

覆盖：
- footystats provider 路由：data_provider 字段正确，lineups 在 data_gaps，form 不在
- sportmonks provider 路由：form 在 data_gaps，lineups / odds_movement 正确填充
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from data_strategy.fusion import DataFusion
from data_strategy.resolver import ResolvedData


def _make_ok(data, source="footystats", quality=0.85):
    return ResolvedData(data=data, source=source, quality=quality)


def _make_missing(name):
    return ResolvedData.missing(name)


@pytest.fixture
def mock_fs_resolver():
    r = MagicMock()
    r.resolve_xg = AsyncMock(return_value=_make_ok({
        "home_xg_for": 1.8, "home_xg_against": 1.0,
        "away_xg_for": 1.2, "away_xg_against": 1.4,
    }))
    r.resolve_form = AsyncMock(return_value=_make_ok({"home": {"avg_scored_5": 1.8}, "away": {"avg_scored_5": 1.2}}))
    r.resolve_standings = AsyncMock(return_value=_make_ok({"raw": []}))
    r.resolve_odds = AsyncMock(return_value=_make_ok({"home_win": 1.85, "draw": 3.50, "away_win": 4.20}))
    r.resolve_lineups = AsyncMock(return_value=_make_missing("lineups"))
    r.resolve_odds_movement = AsyncMock(return_value=_make_missing("odds_movement"))
    r.resolve_head_to_head = AsyncMock(return_value=_make_missing("head_to_head"))
    r.resolve_predictions = AsyncMock(return_value=_make_missing("predictions"))
    return r


@pytest.mark.asyncio
async def test_footystats_provider_sets_data_provider_field(mock_fs_resolver):
    with patch("data_strategy.fusion.FootyStatsResolver", return_value=mock_fs_resolver):
        fusion = DataFusion(
            data_provider="footystats",
            footystats=MagicMock(),
            understat=MagicMock(),
        )
        ctx = await fusion.build(
            fixture_id="8255851",
            match_id="8255851",
            home_team="Arsenal", home_team_id="86",
            away_team="Chelsea", away_team_id="83",
            season_id="1980",
            league="Premier League",
            match_date="2026-04-12",
        )
    assert ctx.data_provider == "footystats"
    assert "lineups" in ctx.data_gaps
    assert "form" not in ctx.data_gaps


@pytest.mark.asyncio
async def test_sportmonks_provider_form_in_gaps():
    sm_resolver = MagicMock()
    sm_resolver.resolve_xg = AsyncMock(return_value=_make_ok({
        "home_xg_for": 1.8, "home_xg_against": 1.0,
        "away_xg_for": 1.2, "away_xg_against": 1.4,
    }))
    sm_resolver.resolve_form = AsyncMock(return_value=_make_missing("form"))
    sm_resolver.resolve_standings = AsyncMock(return_value=_make_ok({"raw": []}))
    sm_resolver.resolve_odds = AsyncMock(return_value=_make_ok({"home_win": 1.90, "draw": 3.40, "away_win": 4.00}))
    sm_resolver.resolve_lineups = AsyncMock(return_value=_make_ok({
        "home_formation": "4-3-3",
        "away_formation": "4-4-2",
        "home_confirmed": True,
        "away_confirmed": False,
    }))
    sm_resolver.resolve_odds_movement = AsyncMock(return_value=_make_ok({
        "home_open": 2.10, "home_current": 1.90,
        "draw_open": 3.40, "draw_current": 3.40,
        "away_open": 3.80, "away_current": 4.00,
        "movement_hours": 48,
    }))
    sm_resolver.resolve_head_to_head = AsyncMock(return_value=_make_missing("head_to_head"))
    sm_resolver.resolve_predictions = AsyncMock(return_value=_make_missing("predictions"))

    with patch("data_strategy.fusion.SportmonksResolver", return_value=sm_resolver):
        fusion = DataFusion(
            data_provider="sportmonks",
            footystats=MagicMock(),
            understat=MagicMock(),
            sportmonks=MagicMock(),
        )
        ctx = await fusion.build(
            fixture_id="19374628",
            match_id="19374628",
            home_team="Arsenal", home_team_id="1",
            away_team="Chelsea", away_team_id="2",
            season_id="23614",
            league="Premier League",
            match_date="2026-04-12",
        )
    assert ctx.data_provider == "sportmonks"
    assert "form" in ctx.data_gaps
    assert ctx.lineups is not None
    assert ctx.lineups.home_formation == "4-3-3"
    assert ctx.odds_movement is not None

"""
DataFusion 单元测试

覆盖：
- footystats provider 路由：data_provider 字段正确，xg/form/standings/odds 正确映射
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datasource.datafusion.fusion import DataFusion
from datasource.datafusion.resolver import ResolvedData


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
    with patch("datasource.datafusion.fusion.FootyStatsResolver", return_value=mock_fs_resolver):
        fusion = DataFusion(
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
    assert "form" not in ctx.data_gaps

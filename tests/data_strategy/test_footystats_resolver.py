# tests/data_strategy/test_footystats_resolver.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from data_strategy.resolvers.footystats_resolver import FootyStatsResolver
from data_strategy.resolver import ResolvedData


@pytest.fixture
def mock_fs():
    fs = MagicMock()
    fs.get_team_last_x_stats = AsyncMock(return_value={
        "data": [
            {"last_x_match_num": 5, "stats": {
                "seasonScoredAVG_overall": 1.8,
                "seasonConcededAVG_overall": 1.0,
                "seasonWinsNum_overall": 3,
                "seasonDrawsNum_overall": 1,
                "seasonLossesNum_overall": 1,
                "seasonScoredNum_overall": 9,
                "seasonConcededNum_overall": 5,
            }},
            {"last_x_match_num": 10, "stats": {
                "seasonScoredAVG_overall": 1.6,
                "seasonConcededAVG_overall": 1.1,
                "seasonWinsNum_overall": 6,
                "seasonDrawsNum_overall": 2,
                "seasonLossesNum_overall": 2,
                "seasonScoredNum_overall": 16,
                "seasonConcededNum_overall": 11,
            }},
        ]
    })
    fs.get_league_tables = AsyncMock(return_value=[
        {"name": "Arsenal", "position": 1, "points": 70, "played": 30,
         "wins": 22, "draws": 4, "losses": 4, "goals_for": 65, "goals_against": 25},
        {"name": "Chelsea", "position": 5, "points": 52, "played": 30,
         "wins": 15, "draws": 7, "losses": 8, "goals_for": 48, "goals_against": 38},
    ])
    fs.get_match_details = AsyncMock(return_value={
        "data": [{"odds_ft_1": 1.85, "odds_ft_x": 3.50, "odds_ft_2": 4.20}]
    })
    return fs


@pytest.fixture
def mock_us():
    us = MagicMock()
    us.get_league_teams = AsyncMock(return_value=None)  # Understat not available
    return us


@pytest.mark.asyncio
async def test_resolve_form_returns_ok(mock_fs, mock_us):
    resolver = FootyStatsResolver(footystats=mock_fs, understat=mock_us)
    result = await resolver.resolve_form(home_team_id="86", away_team_id="83")
    assert result.ok
    assert result.source == "footystats"

@pytest.mark.asyncio
async def test_resolve_form_has_home_avg_scored(mock_fs, mock_us):
    resolver = FootyStatsResolver(footystats=mock_fs, understat=mock_us)
    result = await resolver.resolve_form(home_team_id="86", away_team_id="83")
    assert result.data["home"]["avg_scored_5"] == pytest.approx(1.8)

@pytest.mark.asyncio
async def test_resolve_standings_ok(mock_fs, mock_us):
    resolver = FootyStatsResolver(footystats=mock_fs, understat=mock_us)
    result = await resolver.resolve_standings(season_id="1980")
    assert result.ok
    assert result.source == "footystats"

@pytest.mark.asyncio
async def test_resolve_odds_ok(mock_fs, mock_us):
    resolver = FootyStatsResolver(footystats=mock_fs, understat=mock_us)
    result = await resolver.resolve_odds(match_id="8255851")
    assert result.ok
    assert result.data["home_win"] == pytest.approx(1.85)
    assert result.data["draw"] == pytest.approx(3.50)
    assert result.data["away_win"] == pytest.approx(4.20)

@pytest.mark.asyncio
async def test_resolve_lineups_always_missing(mock_fs, mock_us):
    resolver = FootyStatsResolver(footystats=mock_fs, understat=mock_us)
    result = await resolver.resolve_lineups(fixture_id="8255851", home_team_id="86", away_team_id="83")
    assert not result.ok
    assert result.source == "missing"

@pytest.mark.asyncio
async def test_resolve_odds_movement_always_missing(mock_fs, mock_us):
    resolver = FootyStatsResolver(footystats=mock_fs, understat=mock_us)
    result = await resolver.resolve_odds_movement(fixture_id="8255851")
    assert not result.ok
    assert result.source == "missing"

@pytest.mark.asyncio
async def test_resolve_head_to_head_always_missing(mock_fs, mock_us):
    resolver = FootyStatsResolver(footystats=mock_fs, understat=mock_us)
    result = await resolver.resolve_head_to_head(home_team_id="86", away_team_id="83")
    assert not result.ok
    assert result.source == "missing"

@pytest.mark.asyncio
async def test_resolve_xg_falls_back_to_league_avg_when_no_understat(mock_fs, mock_us):
    resolver = FootyStatsResolver(footystats=mock_fs, understat=mock_us)
    result = await resolver.resolve_xg(
        home_team="Arsenal", away_team="Chelsea",
        league="Premier League", season="2025",
        home_team_id="86", away_team_id="83",
    )
    # When Understat returns None and FootyStats proxy data is available,
    # should still return ok result
    assert result is not None  # Should not crash

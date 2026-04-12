# tests/data_strategy/test_sportmonks_resolver.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from data_strategy.resolvers.sportmonks_resolver import SportmonksResolver
from data_strategy.resolver import ResolvedData


@pytest.fixture
def mock_sm():
    sm = MagicMock()
    sm.get_standings_by_season = AsyncMock(return_value={
        "data": [
            {"name": "Arsenal", "position": 1, "points": 70, "played": 30,
             "wins": 22, "draws": 4, "losses": 4, "goals_for": 65, "goals_against": 25},
        ]
    })
    sm.get_prematch_odds = AsyncMock(return_value={
        "data": [{"odds": {"home": 1.90, "draw": 3.40, "away": 4.00}}]
    })
    sm.get_odds_movement = AsyncMock(return_value={
        "data": [
            {"type": {"name": "Home"}, "value": 2.10},
            {"type": {"name": "Draw"}, "value": 3.40},
            {"type": {"name": "Away"}, "value": 3.80},
        ]
    })
    sm.get_fixture_by_id = AsyncMock(return_value={
        "data": {
            "lineups": [
                {"team_id": 1, "formation": "4-3-3", "confirmed": True},
                {"team_id": 2, "formation": "4-4-2", "confirmed": False},
            ]
        }
    })
    sm.get_head_to_head = AsyncMock(return_value={
        "data": [
            {"starting_at": "2025-10-20 15:00:00",
             "participants": [
                 {"id": 1, "name": "Arsenal", "meta": {"location": "home"}},
                 {"id": 2, "name": "Chelsea", "meta": {"location": "away"}},
             ],
             "scores": [
                 {"score": {"participant": "home", "goals": 2}},
                 {"score": {"participant": "away", "goals": 1}},
             ]},
        ]
    })
    return sm


@pytest.fixture
def mock_us():
    us = MagicMock()
    us.get_league_teams = AsyncMock(return_value=None)
    return us


@pytest.mark.asyncio
async def test_resolve_form_always_missing(mock_sm, mock_us):
    resolver = SportmonksResolver(sportmonks=mock_sm, understat=mock_us)
    result = await resolver.resolve_form(home_team_id="1", away_team_id="2")
    assert not result.ok
    assert result.source == "missing"

@pytest.mark.asyncio
async def test_resolve_standings_ok(mock_sm, mock_us):
    resolver = SportmonksResolver(sportmonks=mock_sm, understat=mock_us)
    result = await resolver.resolve_standings(season_id="23614")
    assert result.ok
    assert result.source == "sportmonks"

@pytest.mark.asyncio
async def test_resolve_odds_ok(mock_sm, mock_us):
    resolver = SportmonksResolver(sportmonks=mock_sm, understat=mock_us)
    result = await resolver.resolve_odds(match_id="19374628")
    assert result.ok
    assert result.data["home_win"] == pytest.approx(1.90)

@pytest.mark.asyncio
async def test_resolve_lineups_ok(mock_sm, mock_us):
    resolver = SportmonksResolver(sportmonks=mock_sm, understat=mock_us)
    result = await resolver.resolve_lineups(
        fixture_id="19374628", home_team_id="1", away_team_id="2"
    )
    assert result.ok
    assert result.data["home_formation"] == "4-3-3"
    assert result.data["away_formation"] == "4-4-2"
    assert result.data["home_confirmed"] is True
    assert result.data["away_confirmed"] is False

@pytest.mark.asyncio
async def test_resolve_odds_movement_ok(mock_sm, mock_us):
    resolver = SportmonksResolver(sportmonks=mock_sm, understat=mock_us)
    result = await resolver.resolve_odds_movement(fixture_id="19374628")
    assert result.ok
    assert "home_open" in result.data
    assert "home_current" in result.data

@pytest.mark.asyncio
async def test_resolve_head_to_head_ok(mock_sm, mock_us):
    resolver = SportmonksResolver(sportmonks=mock_sm, understat=mock_us)
    result = await resolver.resolve_head_to_head(home_team_id="1", away_team_id="2")
    assert result.ok
    assert "entries" in result.data
    assert len(result.data["entries"]) >= 1
    entry = result.data["entries"][0]
    assert entry["home_team"] == "Arsenal"
    assert entry["home_goals"] == 2
    assert entry["away_goals"] == 1

@pytest.mark.asyncio
async def test_resolve_xg_falls_back_to_league_avg(mock_sm, mock_us):
    resolver = SportmonksResolver(sportmonks=mock_sm, understat=mock_us)
    result = await resolver.resolve_xg(
        home_team="Arsenal", away_team="Chelsea",
        league="Premier League", season="2025",
        home_team_id="1", away_team_id="2",
    )
    # With no Understat data, should return league_avg fallback
    assert result is not None
    assert result.source in ("understat_direct", "footystats_proxy", "league_avg")

@pytest.mark.asyncio
async def test_resolve_lineups_missing_when_no_data(mock_sm, mock_us):
    mock_sm.get_fixture_by_id = AsyncMock(return_value={"data": {}})
    resolver = SportmonksResolver(sportmonks=mock_sm, understat=mock_us)
    result = await resolver.resolve_lineups(
        fixture_id="99999", home_team_id="1", away_team_id="2"
    )
    assert not result.ok
    assert result.source == "missing"

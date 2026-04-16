import pytest
from unittest.mock import AsyncMock, MagicMock
from datasource.sportmonks.service import SportmonksDataService, SimpleCache

@pytest.fixture
def mock_provider():
    provider = AsyncMock()
    
    # Mock get_fixtures_by_date
    provider.get_fixtures_by_date.return_value = {
        "data": [
            {"id": 1, "league": {"name": "Premier League"}},
            {"id": 2, "league": {"name": "La Liga"}},
        ]
    }
    
    # Mock get_fixture_by_id
    provider.get_fixture_by_id.return_value = {
        "data": {"id": 1, "season_id": 100, "participants": [{"id": 10, "meta": {"location": "home"}}, {"id": 20, "meta": {"location": "away"}}]}
    }
    
    # Mock get_probabilities_by_fixture
    provider.get_probabilities_by_fixture.return_value = {"data": {"home_win": 0.5}}
    
    # Mock get_prematch_odds_by_fixture
    provider.get_prematch_odds_by_fixture.return_value = {"data": {"home": 1.5}}
    
    # Mock get_head_to_head
    provider.get_head_to_head.return_value = {"data": [{"fixture_id": 99}]}
    
    # Mock get_standings_by_season
    provider.get_standings_by_season.return_value = {"data": [{"team_id": 10}]}
    
    return provider

@pytest.fixture
def mock_cache():
    cache = MagicMock(spec=SimpleCache)
    # Default to not finding anything in cache
    cache.read_json.return_value = None
    cache.is_expired.return_value = True
    return cache

@pytest.mark.asyncio
async def test_get_matches_no_leagues(mock_provider, mock_cache):
    service = SportmonksDataService(provider=mock_provider, cache=mock_cache)
    matches = await service.get_matches(date="2026-04-15")
    
    assert len(matches) == 2
    assert matches[0]["id"] == 1
    mock_provider.get_fixtures_by_date.assert_called_once_with("2026-04-15", include="participants;league;scores;season;venue")
    mock_cache.write_json.assert_called_once()

@pytest.mark.asyncio
async def test_get_matches_with_leagues(mock_provider, mock_cache):
    service = SportmonksDataService(provider=mock_provider, cache=mock_cache)
    matches = await service.get_matches(date="2026-04-15", leagues=["premier league"])
    
    assert len(matches) == 1
    assert matches[0]["id"] == 1

@pytest.mark.asyncio
async def test_get_match_for_analysis_cache_miss(mock_provider, mock_cache):
    service = SportmonksDataService(provider=mock_provider, cache=mock_cache)
    
    match_data = await service.get_match_for_analysis(fixture_id=1)
    
    assert match_data["fixture"]["id"] == 1
    assert match_data["predictions"]["home_win"] == 0.5
    assert match_data["odds"]["home"] == 1.5
    assert match_data["h2h"][0]["fixture_id"] == 99
    assert match_data["standings"][0]["team_id"] == 10
    
    # Ensure provider was called
    mock_provider.get_fixture_by_id.assert_called_once()
    mock_provider.get_probabilities_by_fixture.assert_called_once()
    mock_provider.get_head_to_head.assert_called_once_with(10, 20)
    mock_provider.get_standings_by_season.assert_called_once_with(100)
    mock_cache.write_json.assert_called_once()

@pytest.mark.asyncio
async def test_get_match_for_analysis_cache_hit(mock_provider, mock_cache):
    # Setup cache to return data
    cached_data = {"fixture": {"id": 1, "cached": True}}
    mock_cache.read_json.return_value = cached_data
    mock_cache.is_expired.return_value = False
    
    service = SportmonksDataService(provider=mock_provider, cache=mock_cache)
    match_data = await service.get_match_for_analysis(fixture_id=1)
    
    assert match_data["fixture"]["cached"] is True
    # Ensure provider was NOT called
    mock_provider.get_fixture_by_id.assert_not_called()

# tests/data_strategy/test_sportmonks_resolver.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from data_strategy.resolvers import sportmonks_resolver as resolver_module
from data_strategy.resolvers.sportmonks_resolver import SportmonksResolver
from data_strategy.resolver import ResolvedData


@pytest.fixture(autouse=True)
def disable_resolver_cache(monkeypatch):
    monkeypatch.setattr(resolver_module, "cache_get", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(resolver_module, "cache_set", lambda *_args, **_kwargs: None)


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


def test_extract_sportmonks_odds_local_supports_flat_v3_market_rows():
    raw = {
        "data": [
            {"market_description": "3Way Result", "label": "1", "value": "2.45"},
            {"market_description": "3Way Result", "label": "X", "value": "3.20"},
            {"market_description": "3Way Result", "label": "2", "value": "2.90"},
        ]
    }

    assert resolver_module._extract_sportmonks_odds_local(raw) == {
        "home_win": 2.45,
        "draw": 3.20,
        "away_win": 2.90,
    }


def test_extract_sportmonks_odds_local_prefers_fulltime_result_over_other_result_markets():
    raw = {
        "data": [
            {"market_description": "Fulltime Result", "label": "Home", "value": "4.80"},
            {"market_description": "Fulltime Result", "label": "Draw", "value": "3.90"},
            {"market_description": "Fulltime Result", "label": "Away", "value": "1.66"},
            {"market_description": "Handicap Result", "label": "Home", "value": "1.42"},
            {"market_description": "Handicap Result", "label": "Draw", "value": "5.00"},
            {"market_description": "Handicap Result", "label": "Away", "value": "5.25"},
        ]
    }

    assert resolver_module._extract_sportmonks_odds_local(raw) == {
        "home_win": 4.80,
        "draw": 3.90,
        "away_win": 1.66,
    }


def test_extract_sportmonks_asian_handicap_local_reads_handicap_field():
    raw = {
        "data": [
            {
                "market_description": "Asian Handicap",
                "label": "Home",
                "value": "1.76",
                "handicap": "+1",
                "original_label": "+1",
            },
            {
                "market_description": "Asian Handicap",
                "label": "Away",
                "value": "2.40",
                "handicap": "+1",
                "original_label": "+1",
            },
        ]
    }

    assert resolver_module._extract_sportmonks_asian_handicap_local(raw) == {
        "ah_line": 1.0,
        "ah_home_odds": 1.76,
        "ah_away_odds": 2.40,
    }


@pytest.mark.asyncio
async def test_resolve_odds_falls_back_to_by_fixture_method_when_legacy_name_missing(mock_us):
    class ProviderWithOnlyByFixture:
        def __init__(self):
            self.get_prematch_odds_by_fixture = AsyncMock(
                return_value={"data": [{"odds": {"home": 1.88, "draw": 3.55, "away": 4.20}}]}
            )

    mock_sm = ProviderWithOnlyByFixture()
    resolver = SportmonksResolver(sportmonks=mock_sm, understat=mock_us)

    result = await resolver.resolve_odds(match_id="29374628")

    assert result.ok
    assert result.data["home_win"] == pytest.approx(1.88)
    mock_sm.get_prematch_odds_by_fixture.assert_awaited_once_with(29374628)

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
        league="Premier League", season="fallback-2025",
        home_team_id="1", away_team_id="2",
    )
    # With no Understat data, should return league_avg fallback
    assert result is not None
    assert result.source in ("understat_direct", "footystats_proxy", "league_avg")


@pytest.mark.asyncio
async def test_resolve_xg_reads_nested_data_value_from_sportmonks_response(mock_sm, mock_us):
    mock_sm.get_expected_goals_by_team = AsyncMock(
        side_effect=[
            {
                "data": [
                    {"participant_id": 1, "type_id": 5304, "data": {"value": 1.42}},
                    {"participant_id": 1, "type_id": 9687, "data": {"value": 1.18}},
                    {"participant_id": 999, "type_id": 9684, "data": {"value": -9.99}},
                ]
            },
            {
                "data": [
                    {"participant_id": 2, "type_id": 5304, "data": {"value": 0.91}},
                    {"participant_id": 2, "type_id": 9687, "data": {"value": 1.07}},
                    {"participant_id": 888, "type_id": 9686, "data": {"value": -8.88}},
                ]
            },
        ]
    )
    resolver = SportmonksResolver(sportmonks=mock_sm, understat=mock_us)

    result = await resolver.resolve_xg(
        home_team="Arsenal", away_team="Chelsea",
        league="Premier League", season="nested-2025",
        home_team_id="1", away_team_id="2",
    )

    assert result.ok
    assert result.source == "sportmonks_direct"
    assert result.data["home_xg_for"] == pytest.approx(1.42)
    assert result.data["home_xg_against"] == pytest.approx(1.18)
    assert result.data["away_xg_for"] == pytest.approx(0.91)
    assert result.data["away_xg_against"] == pytest.approx(1.07)


def test_extract_team_xg_avg_filters_requested_participant_and_expected_types():
    raw = {
        "data": [
            {"participant_id": 2714, "type_id": 5304, "data": {"value": 1.60}},
            {"participant_id": 2714, "type_id": 9687, "data": {"value": 1.10}},
            {"participant_id": 2714, "type_id": 9684, "data": {"value": 0.50}},
            {"participant_id": 85, "type_id": 5304, "data": {"value": 9.99}},
            {"participant_id": 85, "type_id": 9687, "data": {"value": 9.99}},
        ]
    }

    assert resolver_module._extract_team_xg_avg(raw, participant_id=2714) == {
        "xg_for": 1.60,
        "xg_against": 1.10,
    }


@pytest.mark.asyncio
async def test_resolve_xg_ignores_unrelated_participants_and_falls_back_when_no_match(mock_sm, mock_us):
    mock_sm.get_expected_goals_by_team = AsyncMock(
        side_effect=[
            {
                "data": [
                    {"participant_id": 85, "type_id": 5304, "data": {"value": 0.30}},
                    {"participant_id": 2356, "type_id": 9687, "data": {"value": 0.73}},
                ]
            },
            {
                "data": [
                    {"participant_id": 85, "type_id": 5304, "data": {"value": 0.30}},
                    {"participant_id": 2356, "type_id": 9687, "data": {"value": 0.73}},
                ]
            },
        ]
    )
    resolver = SportmonksResolver(sportmonks=mock_sm, understat=mock_us)

    result = await resolver.resolve_xg(
        home_team="Sassuolo", away_team="Como",
        league="Serie A", season="no-match-2025",
        home_team_id="2714", away_team_id="268",
    )

    assert result.source == "league_avg"

@pytest.mark.asyncio
async def test_resolve_lineups_missing_when_no_data(mock_sm, mock_us):
    mock_sm.get_fixture_by_id = AsyncMock(return_value={"data": {}})
    resolver = SportmonksResolver(sportmonks=mock_sm, understat=mock_us)
    result = await resolver.resolve_lineups(
        fixture_id="99999", home_team_id="1", away_team_id="2"
    )
    assert not result.ok
    assert result.source == "missing"

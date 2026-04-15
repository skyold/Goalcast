import pytest

from datasource.sportmonks.collector import SportmonksCollector


class FakeOddsProvider:
    def __init__(self):
        self.fixture_include = None

    async def get_fixture_by_id(self, fixture_id, include=None):
        self.fixture_include = include
        return {"data": {"lineups": []}}

    async def get_standings_by_season(self, season_id):
        return {"data": []}

    async def get_prematch_odds_by_fixture(self, fixture_id):
        return {
            "data": [
                {"market_description": "3Way Result", "label": "1", "value": "2.45"},
                {"market_description": "3Way Result", "label": "X", "value": "3.20"},
                {"market_description": "3Way Result", "label": "2", "value": "2.90"},
                {"market_description": "Asian Handicap", "label": "Home -0.5", "value": "1.91"},
                {"market_description": "Asian Handicap", "label": "Away -0.5", "value": "1.97"},
            ]
        }

    async def get_predictions_by_fixture(self, fixture_id):
        return {"data": []}

    async def get_expected_goals_by_team(self, team_id):
        return {"data": []}

    async def get_head_to_head(self, home_id, away_id):
        return {"data": []}


@pytest.mark.asyncio
async def test_collect_match_layers_extracts_v3_odds_and_asian_handicap():
    collector = SportmonksCollector(FakeOddsProvider())
    fixture = {
        "id": 19425209,
        "season_id": 25533,
        "participants": [
            {"id": 2714, "name": "Sassuolo", "meta": {"location": "home"}},
            {"id": 268, "name": "Como", "meta": {"location": "away"}},
        ],
    }

    layers = await collector.collect_match_layers(fixture)

    assert layers["odds"] == {
        "home_win": 2.45,
        "draw": 3.20,
        "away_win": 2.90,
    }
    assert layers["asian_handicap"] == {
        "ah_line": -0.5,
        "ah_home_odds": 1.91,
        "ah_away_odds": 1.97,
    }


class FakeXgProvider(FakeOddsProvider):
    async def get_fixture_by_id(self, fixture_id, include=None):
        self.fixture_include = include
        return {
            "data": {
                "expected": [
                    {"fixture_id": fixture_id, "participant_id": 2714, "type_id": 5304, "location": "home", "data": {"value": 1.44}},
                    {"fixture_id": fixture_id, "participant_id": 2714, "type_id": 9687, "location": "home", "data": {"value": 1.12}},
                    {"fixture_id": fixture_id, "participant_id": 2714, "type_id": 9684, "location": "home", "data": {"value": 0.32}},
                    {"fixture_id": fixture_id, "participant_id": 268, "type_id": 5304, "location": "away", "data": {"value": 0.88}},
                    {"fixture_id": fixture_id, "participant_id": 268, "type_id": 9687, "location": "away", "data": {"value": 1.35}},
                ],
                "lineups": [
                    {
                        "team_id": 2714,
                        "player_id": 100,
                        "player_name": "Sassuolo Player",
                        "expected": [
                            {"type_id": 5304, "data": {"value": 0.61}},
                            {"type_id": 5305, "data": {"value": 0.75}},
                        ],
                    },
                    {
                        "team_id": 268,
                        "player_id": 200,
                        "player_name": "Como Player",
                        "expected": [
                            {"type_id": 5304, "data": {"value": 0.33}},
                        ],
                    },
                ],
            }
        }

    async def get_expected_goals_by_team(self, team_id):
        return {
            "data": [
                {"fixture_id": 19000001, "participant_id": team_id, "type_id": 5304, "data": {"value": 1.90}},
                {"fixture_id": 19000001, "participant_id": team_id, "type_id": 9687, "data": {"value": 1.05}},
                {"fixture_id": 19000002, "participant_id": team_id, "type_id": 9684, "data": {"value": 0.85}},
            ]
        }


@pytest.mark.asyncio
async def test_collect_match_layers_preserves_extended_xg_sources_and_details():
    provider = FakeXgProvider()
    collector = SportmonksCollector(provider)
    fixture = {
        "id": 19425209,
        "season_id": 25533,
        "participants": [
            {"id": 2714, "name": "Sassuolo", "meta": {"location": "home"}},
            {"id": 268, "name": "Como", "meta": {"location": "away"}},
        ],
    }

    layers = await collector.collect_match_layers(fixture)

    assert provider.fixture_include == "lineups;xGFixture;lineups.xGLineup"
    assert layers["xg"]["home_xg_for"] == pytest.approx(1.44)
    assert layers["xg"]["home_xg_against"] == pytest.approx(1.12)
    assert layers["xg"]["away_xg_for"] == pytest.approx(0.88)
    assert layers["xg"]["away_xg_against"] == pytest.approx(1.35)
    assert layers["xg"]["summary_source"] == "fixture_expected"
    assert layers["xg"]["available_type_ids"] == [5304, 9684, 9687]
    assert layers["xg"]["fixture_expected"]["home"]["metrics"]["5304"] == pytest.approx(1.44)
    assert layers["xg"]["fixture_expected"]["home"]["metrics"]["9684"] == pytest.approx(0.32)
    assert layers["xg"]["lineup_expected"]["home"][0]["player_name"] == "Sassuolo Player"
    assert layers["xg"]["lineup_expected"]["home"][0]["expected"][0]["type_id"] == 5304
    assert layers["xg"]["team_expected_history"]["away"]["metrics"]["5304"] == pytest.approx(1.90)

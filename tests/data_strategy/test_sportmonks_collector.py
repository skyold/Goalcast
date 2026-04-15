import pytest

from data_strategy.sportmonks.collector import SportmonksCollector


class FakeOddsProvider:
    async def get_fixture_by_id(self, fixture_id, include=None):
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

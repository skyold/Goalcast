# Referees (+Stats) in The League

# League Referees

## Get Array of Referees
`GET` `https://api.football-data-api.com/league-referees?key=YOURKEY&season_id=*` This endpoint provides an array of referees that have refereed in the particular league/season ID
#### Query Parameters

| max_time | integer | UNIX timestamp. Set this number if you would like the API to return the stats of the league and the teams up to a certain time. For example, if I enter &max_time=1537984169, then the API will respond with stats as of Sept 26, 2018. |
| --- | --- | --- |
| max_time | integer | UNIX timestamp. Set this number if you would like the API to return the stats of the league and the teams up to a certain time. For example, if I enter &max_time=1537984169, then the API will respond with stats as of Sept 26, 2018. |
| key* | string | Your API Key |
| season_id* | integer | ID of the league season that you would like to retrieve. |

```json
{
    "success": true,
    "pager": {
        "current_page": 1,
        "max_page": 1,
        "results_per_page": 200,
        "total_results": 21
    },
    "data": [
        {
            "id": 393,
            "competition_id": 2012,
            "full_name": "Michael Oliver",
            "first_name": "Michael",
            "last_name": "Oliver",
            "known_as": "Michael Oliver",
            "shorthand": "michael-oliver",
            "age": 35,
            "league": "Premier League",
            "league_type": "Domestic League",
            "url": "https://footystats.org/referees/england-r-michael-oliver",
            "season": "2019/2020",
            "continent": "eu",
            "starting_year": 2019,
            "ending_year": 2020,
            "birthday": 477705600,
            "nationality": "England",
            "appearances_overall": 32,
            "wins_home": 11,
            "wins_away": 13,
            "draws_overall": 8,
            "wins_per_home": 34,
            "wins_per_away": 41,
            "draws_per": 25,
            "btts_overall": 63,
            "btts_percentage": 63,
            "goals_overall": 96,
            "goals_home": 46,
            "goals_away": 50,
            "goals_per_match_overall": 3,
            "goals_per_match_home": 1.44,
            "goals_per_match_away": 1.56,
            "penalties_given_overall": 5,
            "penalties_given_home": 2,
            "penalties_given_away": 3,
            "penalties_given_per_match_overall": 0.16,
            "penalties_given_per_match_home": 0.06,
            "penalties_given_per_match_away": 0.09,
            "penalties_given_percentage_overall": 16,
            "penalties_given_percentage_home": 6,
            "penalties_given_percentage_away": 9,
            "cards_overall": 105,
            "cards_home": 54,
            "cards_away": 51,
            "cards_per_match_overall": 3.28,
            "cards_per_match_home": 1.69,
            "cards_per_match_away": 1.59,
            "over05_cards_overall": 31,
            "over15_cards_overall": 27,
            "over25_cards_overall": 17,
            "over35_cards_overall": 11,
            "over45_cards_overall": 10,
            "over55_cards_overall": 5,
            "over65_cards_overall": 2,
            "over05_cards_per_match_overall": 0.97,
            "over15_cards_per_match_overall": 0.84,
            "over25_cards_per_match_overall": 0.53,
            "over35_cards_per_match_overall": 0.34,
            "over45_cards_per_match_overall": 0.31,
            "over55_cards_per_match_overall": 0.16,
            "over65_cards_per_match_overall": 0.06,
            "over05_cards_percentage_overall": 97,
            "over15_cards_percentage_overall": 84,
            "over25_cards_percentage_overall": 53,
            "over35_cards_percentage_overall": 34,
            "over45_cards_percentage_overall": 31,
            "over55_cards_percentage_overall": 16,
            "over65_cards_percentage_overall": 6,
            "yellow_cards_overall": 105,
            "red_cards_overall": 0,
            "min_per_goal_overall": 30,
            "min_per_card_overall": 27
        }
    ]
}
```

### Queries and Parameters

| id | ID of the Referee. |
| --- | --- |
| id | ID of the Referee. |
| competition_id | Competition ID. |
| full_name / first_name / last_name | Full name, First name and Last name of the Referee. |
| known_as | Name of the referee as he is . |
| shorthand | Code friendly name. |
| age | Age of the referee. |
| league | Name of the league. |
| league_type | Type of the league. |
| url | FootyStats url of the referee. |
| season | Season year of the league. |
| continent | Continent of the league. |
| starting_year / ending_year | Starting / Ending years of the season. |
| birthday | UNIX birthday of the referee. |
| nationality | Nationality of the referee. |
| appearances_overall | Number of matches participated in the season. |
| wins_home / wins_away / draws_overall | Number of matches refereed ended with Home win, Away win or draw. |
| wins_per_home / wins_per_away / draws_per | Percentage value of matches ending in Home win, Away win or draw.May not always end up accounting to exactly 100% because some numbers are rounded. |
| btts_overall | BTTS overall. |
| btts_percentage | Percentage of BTTS. |
| goals_overall | Number of goals total. |
| goals_home / goals_away | Number of goals Home and Away. |
| goals_per_match_overall / goals_per_match_home / goals_per_match_away | Average goal per match Overall, Home or Away. |
| penalties_given_overall / penalties_given_home / penalties_given_away | Penalties given Overall, Home or Away. |
| penalties_given_per_match_overall / penalties_given_per_match_home / penalties_given_per_match_away | Penalties given per match Overall, Home or Away. |
| penalties_given_percentage_overall / penalties_given_percentage_home / penalties_given_percentage_away | Penalties given percentage Overall, Home or Away. |
| cards_overall, cards_home, cards_away | Cards distributed Overall, Home or Away. |
| cards_per_match_overall / cards_per_match_home / cards_per_match_away | Average cards distributed per match Overall, Home or Away. |
| over05_cards_overall (0.5 - 6.5) | Number of Over 0.5 to Over 6.5 cards distributed. |
| over05_cards_per_match_overall (0.5 - 6.5) | Average number of Over 0.5 to Over 6.5 cards distributed. |
| over05_cards_percentage_overall (0.5 - 6.5) | Percentage of Over 0.5 to Over 6.5 cards distributed. |
| yellow_cards_overall / red_cards_overall | Number of yellow cards and red cards distributed. |
| min_per_goal_overall | Average time between goals accorded. |
| min_per_card_overall | Average time between cards given. |

[PreviousLeague Players](https://footystats.org/api/documentations/league-players) [NextTeam](https://footystats.org/api/documentations/team)
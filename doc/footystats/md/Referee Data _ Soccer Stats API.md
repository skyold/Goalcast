# Referee Data

# Referee - Individual

## Get Referee

`GET`

Returns an array of stats of the referee for all competitions and seasons they participated in.

#### Query Parameters

| key* | string | Your API Key |
| --- | --- | --- |
| key* | string | Your API Key |
| referee_id* | integer | ID of the referee that you would like to retrieve. |

```json
{
 "success": true,
 "pager": {
 "current_page": 1,
 "max_page": 1,
 "results_per_page": 50,
 "total_results": 33
 },
 "data": [
 {
 "id": 393,
 "competition_id": 4796,
 "full_name": "Michael Oliver",
 "first_name": "Michael",
 "last_name": "Oliver",
 "known_as": "Michael Oliver",
 "shorthand": "michael-oliver",
 "age": 35,
 "league": "UEFA Nations League",
 "league_type": "International",
 "url": "https://footystats.org/referees/england-r-michael-oliver",
 "season": "2020/2021",
 "continent": "",
 "starting_year": 2020,
 "ending_year": 2021,
 "birthday": 477705600,
 "nationality": "England",
 "appearances_overall": 2,
 "wins_home": 0,
 "wins_away": 0,
 "draws_overall": 2,
 "wins_per_home": 0,
 "wins_per_away": 0,
 "draws_per": 100,
 "btts_overall": 50,
 "btts_percentage": 50,
 "goals_overall": 2,
 "goals_home": 1,
 "goals_away": 1,
 "goals_per_match_overall": 1,
 "goals_per_match_home": 0.5,
 "goals_per_match_away": 0.5,
 "penalties_given_overall": 0,
 "penalties_given_home": 0,
 "penalties_given_away": 0,
 "penalties_given_per_match_overall": 0,
 "penalties_given_per_match_home": 0,
 "penalties_given_per_match_away": 0,
 "penalties_given_percentage_overall": 0,
 "penalties_given_percentage_home": 0,
 "penalties_given_percentage_away": 0
 }
 ]
}
```

### Queries and Parameters

> ℹ️ This part is still Work in progress, and will beupdated at a later date.

| id | ID of the Referee. |
| --- | --- |
| id | ID of the Referee. |
| full_name | Full name of the referee. |

[PreviousPlayer - Individual](https://footystats.org/api/documentations/player-individual) [NextBTTS Stats](https://footystats.org/api/documentations/btts-stats)
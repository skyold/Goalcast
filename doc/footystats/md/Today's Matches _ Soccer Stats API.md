# Today's Matches

# Today's Matches (Matches by day)
Get a list of matches by date

## Get a list of today's matches with or without stats

`GET`

`https://api.football-data-api.com/todays-matches?key=example`

You must choose the leagues in your settings for the matches to show up here.Returns a maximum of 200 matches per page. Pagination is enabled by default. Add &page=2 to begin paginating.

#### Query Parameters

| timezone | string | Timezone. ie&timezone=Europe/London.Uses TZ timezone name : https://en.wikipedia.org/wiki/List_of_tz_database_time_zones. Defaults to Etc/UTC if not specified. |
| --- | --- | --- |
| timezone | string | Timezone. ie&timezone=Europe/London.Uses TZ timezone name : https://en.wikipedia.org/wiki/List_of_tz_database_time_zones. Defaults to Etc/UTC if not specified. |
| date | string | Date format = YYYY-MM-DD. ie&date=2020-07-30. If not entered, defaults to current day in UTC timezone. |
| key* | string | Your API key. |

```json
{
 "success": true,
 "pager": {
 "current_page": 1,
 "max_page": 1,
 "results_per_page": 200,
 "total_results": 2
 },
 "data": [
 {
 "id": 579362,
 "homeID": 155,
 "awayID": 93,
 "season": "2019/2020",
 "status": "incomplete",
 "roundID": 50055,
 "game_week": 37,
 "revised_game_week": -1,
 "homeGoals": "[]",
 "awayGoals": "[]",
 "homeGoalCount": 0,
 "awayGoalCount": 0,
 "totalGoalCount": 0,
 "team_a_corners": -1,
 "team_b_corners": -1,
 "totalCornerCount": 0,
 "team_a_offsides": 0,
 "team_b_offsides": 0,
 "team_a_yellow_cards": 0,
 "team_b_yellow_cards": 0,
 "team_a_red_cards": 0,
 "team_b_red_cards": 0,
 "team_a_shotsOnTarget": -1,
 "team_b_shotsOnTarget": -1,
 "team_a_shotsOffTarget": -1,
 "team_b_shotsOffTarget": -1,
 "team_a_shots": -2,
 "team_b_shots": -2,
 "team_a_fouls": -1,
 "team_b_fouls": -1,
 "team_a_possession": -1,
 "team_b_possession": -1,
 "refereeID": -1,
 "coach_a_ID": -1,
 "coach_b_ID": -1,
 "stadium_name": "",
 "stadium_location": "",
 "team_a_cards_num": 0,
 "team_b_cards_num": 0,
 "odds_ft_1": 8.75,
 "odds_ft_x": 5.8,
 "odds_ft_2": 1.33
 }
 ]
}
```

| id | ID of the Match. |
| --- | --- |
| id | ID of the Match. |
| homeID | Home team id. |
| awayID | Away team id. |
| season | Season year of the league. |
| status | Status of the league. |
| roundID | Round ID. |
| game_week | Game week number. |
| revised_game_week | Revised game week -1 is default and means no revision. |
| homeGoals | Goal timings for Home team. |
| awayGoals | Goal timings for Home team. |
| homeGoalCount | How many goals scored by Home team. |
| awayGoalCount | How many goals scored by Away team. |
| totalGoalCount | How many goals scored in the match. |
| team_a_corners | Corners for Home team, -1 is default. |
| team_b_corners | Corners for Away team, -1 is default. |
| totalCornerCount | How many corners in the match. |
| team_a_offsides | Offsides for Home team. |
| team_b_offsides | Offsides for Away team. |
| team_a_yellow_cards | Yellow cards booked by Home team. |
| team_b_yellow_cards | Yellow cards booked by Away team. |
| team_a_red_cards | Red cards booked by Home team. |
| team_b_red_cards | Red cards booked by Away team. |
| team_a_shotsOnTarget | Shots on target for Home team, -1 is default. |
| team_b_shotsOnTarget | Shots on target for Away team, -1 is default. |
| team_a_shotsOffTarget | Shots off target for Home team, -1 is default. |
| team_b_shotsOffTarget | Shots off target for Away team, -1 is default. |
| team_a_shots | Total shots for Home team, -2 is default. |
| team_b_shots | Total shots for Away team, -2 is default. |
| team_a_fouls | Fouls for Home team, -1 is default. |
| team_b_fouls | Fouls for Away team, -1 is default. |
| team_a_possession | Possession for Home team, -1 is default. |
| team_b_possession | Possession for Away team, -1 is default. |
| refereeID | ID of the referee. |
| coach_a_ID | ID of the coach for Home team. |
| coach_b_ID | ID of the coach for Away team. |
| stadium_name | Name of the stadium. |
| stadium_location | Location of the stadium. |
| team_a_cards_num | Total cards booked by Home team. |
| team_b_cards_num | Total cards booked by Away team. |
| odds_ft_1 | Odds for Home team win at fulltime. |
| odds_ft_X | Odds for draw at fulltime. |
| odds_ft_2 | Odds for Away team win at fulltime. |

[PreviousCountry List](https://footystats.org/api/documentations/country-list) [NextLeague Stats](https://footystats.org/api/documentations/league-season-stats-teams)
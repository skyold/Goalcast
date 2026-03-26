# Match Schedule & Stats

# League Matches

## Get Matches
`GET` `https://api.football-data-api.com/league-matches?key=YOURKEY&season_id=1` Sample Response (Access the URL below)
[https://api.football-data-api.com/league-matches?key=example&season_id=2012](https://api.football-data-api.com/league-matches?key=example&season_id=2012) This endpoint responds with the full match schedule of the selected league id. Response will be a JSON Array containing each match details. Defaults to 300 matches per page. You can set &max_per_page=X (ie &max_per_page=500) to raise the amount of matches returned per page.
#### Query Parameters

| page | integer | ie "&page=2". Pagination. Each page by default shows up to 500 matches. If you want to see the next 500 matches, add &page=2 or &page=3, etc to paginate. |
| --- | --- | --- |
| page | integer | ie "&page=2". Pagination. Each page by default shows up to 500 matches. If you want to see the next 500 matches, add &page=2 or &page=3, etc to paginate. |
| max_per_page | integer | ie "&max_per_page=500". This raises the number of matches returned per page. Max 1000. |
| max_time | integer | UNIX timestamp. Set this number if you would like the API to return the stats of the league and the teams up to a certain time. For example, if I enter &max_time=1537984169, then the API will respond with stats as of Sept 26, 2018. |
| key* | string | Your API Key |
| season_id* | integer | ID of the league season that you would like to retrieve. |

```json
{
    "success": true,
    "data": [
        {
            "id": 49347,
            "homeID": 1002,
            "awayID": 1003,
            "season": "2017",
            "status": "complete",
            "roundID": "245",
            "game_week": "1",
            "revised_game_week": null,
            "homeGoals": [
                "13",
                "85",
                "90+2"
            ],
            "awayGoals": [
                "63",
                "64"
            ],
            "homeGoalCount": 3,
            "awayGoalCount": 2,
            "totalGoalCount": 5,
            "team_a_corners": 3,
            "team_b_corners": 5,
            "team_a_offsides": 3,
            "team_b_offsides": 1,
            "team_a_cards": [
                69,
                31,
                18
            ],
            "team_b_cards": [
                56,
                25
            ],
            "team_a_yellow_cards": 3,
            "team_b_yellow_cards": 2,
            "team_a_red_cards": 0,
            "team_b_red_cards": 0,
            "team_a_shotsOnTarget": 9,
            "team_b_shotsOnTarget": 10,
            "team_a_shotsOffTarget": 8,
            "team_b_shotsOffTarget": 5,
            "team_a_shots": 17,
            "team_b_shots": 15,
            "team_a_fouls": 18,
            "team_b_fouls": 15,
            "team_a_possession": 34,
            "team_b_possession": 66,
            "refereeID": 3193,
            "coach_a_ID": 1155,
            "coach_b_ID": 2322,
            "stadiumID": "0c0f0ce895c01f821348565e24606ab5",
            "stadium_name": "Nissan Stadium (Yokohama)",
            "stadium_location": "3302-5 Kozukue, Kohoku-ku, Yokohama",
            "team_a_cards_num": 3,
            "team_b_cards_num": 2,
            "odds_ft_1": 3.63,
            "odds_ft_x": 3.52,
            "odds_ft_2": 2.15,
            "odds_ft_over05": 0,
            "odds_ft_over15": 0,
            "odds_ft_over25": 0,
            "odds_ft_over35": 0,
            "odds_ft_over45": 0,
            "odds_ft_under05": 0,
            "odds_ft_under15": 0,
            "odds_ft_under25": 0,
            "odds_ft_under35": 0,
            "odds_ft_under45": 0,
            "odds_btts_yes": 0,
            "odds_btts_no": 0,
            "id_bet365": "",
            "odds_team_a_cs_yes": 0,
            "odds_team_a_cs_no": 0,
            "odds_team_b_cs_yes": 0,
            "odds_team_b_cs_no": 0,
            "id_ft_1": "",
            "id_ft_x": "",
            "id_ft_2": "",
            "id_ft_over05": "",
            "id_ft_over15": "",
            "id_ft_over25": "",
            "id_ft_over35": "",
            "id_ft_over45": "",
            "id_btts_yes": "",
            "id_btts_no": "",
            "id_team_a_cs_yes": "",
            "id_team_b_cs_yes": "",
            "id_team_a_cs_no": "",
            "id_team_b_cs_no": "",
            "events": [],
            "overallGoalCount": 5,
            "half_time": {
                "team_a": 1,
                "team_b": 0
            },
            "ht_goals_team_a": 1,
            "ht_goals_team_b": 0,
            "HTGoalCount": 1,
            "btts": true,
            "over05": true,
            "over15": true,
            "over25": true,
            "over35": true,
            "over45": true,
            "over55": false,
            "over65Corners": true,
            "over75Corners": true,
            "over85Corners": false,
            "over95Corners": false,
            "over105Corners": false,
            "over115Corners": false,
            "over125Corners": false,
            "over135Corners": false,
            "over145Corners": false,
            "date": null,
            "date_unix": 1487993400,
            "winningTeam": 1002,
            "no_home_away": 0,
            "home_team_goal_timings": "13,85,90'2",
            "away_team_goal_timings": "63,64"
        }
    ]
}
```

### Queries and Parameters

> ℹ️ You can test this API call by using the key "example" and loading the matches from the English Premier League 2018/2019 season (ID: 1625).

| id | ID of the match. |
| --- | --- |
| id | ID of the match. |
| homeID | ID of the home team. |
| awayID | ID of the away team. |
| season | Season of the league. |
| status | Status of the match ('complete', 'suspended', 'canceled', 'incomplete'). |
| roundID | Round ID of the match within the season. |
| game_week | Game week of the match within the season. |
| homeGoals | Goal timings for home team goals. Array |
| awayGoals | Goal timings for away team goals. Array |
| homeGoalCount | Number of home team goals. |
| awayGoalCount | Number of away team goals. |
| totalGoalCount | Number of total match goals. |
| team_a_corners | Number of Home Team Corners. |
| team_b_corners | Number of Away Team Corners. |
| team_a_offsides | Number of Offsides - Home Team. |
| team_b_offsides | Number of Offsides - Away Team. |
| team_a_yellow_cards | Number of yellow cards - Home Team. |
| team_b_yellow_cards | Number of yellow cards - Away Team. |
| team_a_red_cards | Number of Red Cards - Home Team. |
| team_b_red_cards | Number of Red Cards - Away Team. |
| team_a_shotsOnTarget | Number of Shots On Target - Home Team. |
| team_b_shotsOnTarget | Number of Shots On Target - Away Team. |
| team_a_shotsOffTarget | Number of Shots Off Target - Home Team. |
| team_b_shotsOffTarget | Number of Shots Off Target - Away Team. |
| team_a_shots | Number of Shots - Home Team. |
| team_b_shots | Number of Shots - Away Team. |
| team_a_fouls | Number of Fouls - Home Team. |
| team_b_fouls | Number of Fouls - Away Team. |
| team_a_possession | Possession of the Home Team. |
| team_b_possession | Possession of the Away Team. |
| refereeID | ID of the referee for this match. |
| coach_a_ID | ID of the coach for home team. |
| coach_b_ID | ID of the coach for away team. |
| stadium_name | Name of the stadium. |
| stadium_location | Location of the stadium. |
| team_a_cards_num | Number of cards for home team. |
| team_b_cards_num | Number of cards for away team. |
| odds_ft_1 | Odds for Home Team Win at FT. |
| odds_ft_x | Odds for Draw at FT. |
| odds_ft_2 | Odds for Away Team Win at FT. |
| odds_ft_over05 - odds_ft_over45 | Odds for Over 0.5 - 4.5 match goals. |
| odds_ft_under05 - odds_ft_under45 | Odds for Under 0.5 - 4.5 match goals. |
| odds_btts_yes / no | Odds for BTTS Yes / No. |
| odds_team_a_cs_yes / a_cs_no / b_cs_yes / b_cs_no | Odds for Clean Sheet Yes / No for Home and Away team. |
| overallGoalCount | Total number of goals in the match. |
| ht_goals_team_a | Number of home team goals by HT. |
| ht_goals_team_b | Number of away team goals by HT. |
| HTGoalCount | Total number of goals by HT. |
| date_unix | UNIX timestamp of the match kick off. |
| winningTeam | ID of the team that won. -1 if draw. |
| no_home_away | set to 1 if there is no home or away distinction for this match. |
| btts_potential | Pre-Match Stat for BTTS for both teams. Average between both teams. |
| o15_potential - o45_potential | Pre-Match Stat for Over 1.5 - 4.5 for both teams. Average between both teams. |
| o05HT_potential - o15HT_potential | Pre-Match Stat for Over 0.5 - 1.5 for both teams by HT. Average between both teams. |
| corners_potential | Pre-Match average corners for both teams. |
| offsides_potential | Pre-Match average offsides for both teams. |
| cards_potential | re-Match average cards for both teams. |
| avg_potential | Pre-Match average total goals per match for both teams. |
| corners_o85_potential - corners_o105_potential | Pre-Match Over X Corners for both teams. |
| u15_potential - u45_potential | Pre-Match Stat for Under 1.5 - 4.5 for both teams. Average between both teams |
| home_ppg | Points per game for home team. Current |
| away_ppg | Points per game for away team. Current |
| pre_match_home_ppg | Pre-Match Points Per Game for Home Team. |
| pre_match_away_ppg | Pre-Match Points Per Game for Away Team. |
| competition_id | Season ID of the league. |
| over05 - over55 | Set to true if the match ended with Over X goals. |
| btts | Set to true if match ended with BTTS. |

[PreviousLeague Stats](https://footystats.org/api/documentations/league-season-stats-teams) [NextLeague Teams](https://footystats.org/api/documentations/league-teams)
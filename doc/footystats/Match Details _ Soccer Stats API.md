# Match Details

# Match Details (Stats, H2H, Odds Comparison)
Provides Stats and Trends for a single match. This endpoint includes general stats, H2H data, as well as Odds comparison for a certain match.

## Get Match
`GET` `https://api.football-data-api.com/match?key=YOURKEY&match_id=1` Sample Response (Access the URL below)
[https://api.football-data-api.com/match?key=example&match_id=579101](https://api.football-data-api.com/match?key=example&match_id=579101) This endpoint provides details on a single match, including stats full odds, and trends. The difference between this and the League Match endpoint is that the Match Details endpoint provides Trends and Lineups of the teams as extra data. Head to Head stats are also provided by default on this endpoint.
#### Query Parameters

| key* | string | Your API Key |
| --- | --- | --- |
| key* | string | Your API Key |
| match_id* | integer | ID of the match. Please get the ID of the match from League Matches endpoint. |

```json
{
    "success": true,
    "pager": {
        "current_page": 1,
        "max_page": 1,
        "results_per_page": 1,
        "total_results": 1
    },
    "data": {
        "id": 579101,
        "homeID": 251,
        "awayID": 145,
        "season": "2019/2020",
        "status": "complete",
        "roundID": 50055,
        "game_week": 11,
        "revised_game_week": -1,
        "homeGoals": [
            "17",
            "43",
            "44"
        ],
        "awayGoals": [],
        "homeGoalCount": 3,
        "awayGoalCount": 0,
        "totalGoalCount": 3,
        "team_a_corners": 7,
        "team_b_corners": 6,
        "totalCornerCount": 13,
        "team_a_offsides": 1,
        "team_b_offsides": 0,
        "team_a_yellow_cards": 1,
        "team_b_yellow_cards": 2,
        "team_a_red_cards": 0,
        "team_b_red_cards": 0,
        "team_a_shotsOnTarget": 7,
        "team_b_shotsOnTarget": 0,
        "team_a_shotsOffTarget": 7,
        "team_b_shotsOffTarget": 6,
        "team_a_shots": 14,
        "team_b_shots": 6,
        "team_a_fouls": 8,
        "team_b_fouls": 12,
        "team_a_possession": 45,
        "team_b_possession": 55,
        "refereeID": 715,
        "coach_a_ID": 497,
        "coach_b_ID": 197,
        "stadium_name": "Bramall Lane (Sheffield)",
        "stadium_location": "",
        "team_a_cards_num": 1,
        "team_b_cards_num": 2,
        "odds_ft_1": 2.4,
        "odds_ft_x": 3.15,
        "odds_ft_2": 3.35,
        "odds_ft_over05": 1.09,
        "odds_ft_over15": 1.48,
        "odds_ft_over25": 2.45,
        "odds_ft_over35": 4.8,
        "odds_ft_over45": 10,
        "odds_ft_under05": 7.5,
        "odds_ft_under15": 2.65,
        "odds_ft_under25": 1.56,
        "odds_ft_under35": 1.18,
        "odds_ft_under45": 1.05,
        "odds_btts_yes": 2,
        "odds_btts_no": 1.69,
        "odds_team_a_cs_yes": 2.5,
        "odds_team_a_cs_no": 1.5,
        "odds_team_b_cs_yes": 3.25,
        "odds_team_b_cs_no": 1.33,
        "odds_doublechance_1x": 1.33,
        "odds_doublechance_12": 1.36,
        "odds_doublechance_x2": 1.57,
        "odds_1st_half_result_1": 3.1,
        "odds_1st_half_result_x": 1.95,
        "odds_1st_half_result_2": 4,
        "odds_2nd_half_result_1": 2.6,
        "odds_2nd_half_result_x": 2.25,
        "odds_2nd_half_result_2": 3.5,
        "odds_dnb_1": 0,
        "odds_dnb_2": 0,
        "odds_corners_over_75": 1.11,
        "odds_corners_over_85": 1.23,
        "odds_corners_over_95": 1.4,
        "odds_corners_over_105": 1.66,
        "odds_corners_over_115": 2,
        "odds_corners_under_75": 5.9,
        "odds_corners_under_85": 3.92,
        "odds_corners_under_95": 2.81,
        "odds_corners_under_105": 2.14,
        "odds_corners_under_115": 1.72,
        "odds_corners_1": 1.4,
        "odds_corners_x": 8.5,
        "odds_corners_2": 3.5,
        "odds_team_to_score_first_1": 1.8,
        "odds_team_to_score_first_x": 7.5,
        "odds_team_to_score_first_2": 2.35,
        "odds_win_to_nil_1": 3.5,
        "odds_win_to_nil_2": 5,
        "odds_1st_half_over05": 1.52,
        "odds_1st_half_over15": 3.6,
        "odds_1st_half_over25": 9.25,
        "odds_1st_half_over35": 21.25,
        "odds_1st_half_under05": 2.39,
        "odds_1st_half_under15": 1.27,
        "odds_1st_half_under25": 1.03,
        "odds_1st_half_under35": 1.01,
        "odds_2nd_half_over05": 1.38,
        "odds_2nd_half_over15": 2.25,
        "odds_2nd_half_over25": 6.2,
        "odds_2nd_half_over35": 13,
        "odds_2nd_half_under05": 3.04,
        "odds_2nd_half_under15": 1.57,
        "odds_2nd_half_under25": 1.12,
        "odds_2nd_half_under35": 1.02,
        "odds_btts_1st_half_yes": 0,
        "odds_btts_1st_half_no": 0,
        "odds_btts_2nd_half_yes": 0,
        "odds_btts_2nd_half_no": 0,
        "overallGoalCount": 3,
        "ht_goals_team_a": 3,
        "ht_goals_team_b": 0,
        "goals_2hg_team_a": 0,
        "goals_2hg_team_b": 0,
        "GoalCount_2hg": 0,
        "HTGoalCount": 3,
        "date_unix": 1572706800,
        "winningTeam": 251,
        "no_home_away": 0,
        "btts_potential": 60,
        "btts_fhg_potential": 20,
        "btts_2hg_potential": 30,
        "goalTimingDisabled": 0,
        "attendance": 31131,
        "corner_timings_recorded": 1,
        "card_timings_recorded": 1,
        "team_a_fh_corners": 2,
        "team_b_fh_corners": 3,
        "team_a_2h_corners": 5,
        "team_b_2h_corners": 3,
        "corner_fh_count": 5,
        "corner_2h_count": 8,
        "team_a_fh_cards": 0,
        "team_b_fh_cards": 1,
        "team_a_2h_cards": 1,
        "team_b_2h_cards": 1,
        "total_fh_cards": 1,
        "total_2h_cards": 2,
        "attacks_recorded": 1,
        "team_a_dangerous_attacks": 47,
        "team_b_dangerous_attacks": 53,
        "team_a_attacks": 101,
        "team_b_attacks": 101,
        "team_a_xg": 1.72,
        "team_b_xg": 0.77,
        "total_xg": 2.49,
        "team_a_penalties_won": 0,
        "team_b_penalties_won": 0,
        "team_a_penalty_goals": 0,
        "team_b_penalty_goals": 0,
        "team_a_penalty_missed": 0,
        "team_b_penalty_missed": 0,
        "pens_recorded": 1,
        "goal_timings_recorded": 1,
        "team_a_0_10_min_goals": 0,
        "team_b_0_10_min_goals": 0,
        "team_a_corners_0_10_min": 2,
        "team_b_corners_0_10_min": 1,
        "team_a_cards_0_10_min": 0,
        "team_b_cards_0_10_min": 0,
        "throwins_recorded": 1,
        "team_a_throwins": 1,
        "team_b_throwins": 0,
        "freekicks_recorded": -1,
        "team_a_freekicks": -1,
        "team_b_freekicks": -1,
        "goalkicks_recorded": -1,
        "team_a_goalkicks": -1,
        "team_b_goalkicks": -1,
        "o45_potential": 0,
        "o35_potential": 10,
        "o25_potential": 40,
        "o15_potential": 60,
        "o05_potential": 100,
        "o15HT_potential": 20,
        "o05HT_potential": 60,
        "o05_2H_potential": 90,
        "o15_2H_potential": 30,
        "corners_potential": 12.6,
        "offsides_potential": 2.4,
        "cards_potential": 4.8,
        "avg_potential": 2.1,
        "home_url": "/clubs/sheffield-united-fc-251",
        "home_image": "teams/england-sheffield-united-fc.png",
        "home_name": "Sheffield United",
        "away_url": "/clubs/burnley-fc-145",
        "away_image": "teams/england-burnley-fc.png",
        "away_name": "Burnley",
        "home_ppg": 1.74,
        "away_ppg": 1.37,
        "pre_match_home_ppg": 1.2,
        "pre_match_away_ppg": 0.6,
        "pre_match_teamA_overall_ppg": 1.3,
        "pre_match_teamB_overall_ppg": 1.2,
        "u45_potential": 100,
        "u35_potential": 90,
        "u25_potential": 60,
        "u15_potential": 40,
        "u05_potential": 0,
        "corners_o85_potential": 90,
        "corners_o95_potential": 80,
        "corners_o105_potential": 70,
        "team_a_xg_prematch": 1.42,
        "team_b_xg_prematch": 1.35,
        "total_xg_prematch": 2.77,
        "match_url": "/england/burnley-fc-vs-sheffield-united-fc-h2h-stats#579101",
        "competition_id": 2012,
        "matches_completed_minimum": 38,
        "lineups": {
            "team_a": [
                {
                    "player_id": 10127,
                    "shirt_number": 1,
                    "player_events": []
                },
                {
                    "player_id": 8515,
                    "shirt_number": 6,
                    "player_events": [
                        {
                            "event_type": "Yellow",
                            "event_time": "89"
                        }
                    ]
                },
                {
                    "player_id": 8697,
                    "shirt_number": 4,
                    "player_events": [
                        {
                            "event_type": "Goal",
                            "event_time": "44"
                        }
                    ]
                },
                {
                    "player_id": 8298,
                    "shirt_number": 7,
                    "player_events": [
                        {
                            "event_type": "Goal",
                            "event_time": "17"
                        },
                        {
                            "event_type": "Goal",
                            "event_time": "43"
                        }
                    ]
                },
                {
                    "player_id": 3964,
                    "shirt_number": 5,
                    "player_events": [
                        {
                            "event_type": "Yellow",
                            "event_time": "34"
                        }
                    ]
                },
                {
                    "player_id": 4305,
                    "shirt_number": 10,
                    "player_events": [
                        {
                            "event_type": "Yellow",
                            "event_time": "68"
                        }
                    ]
                },
                {
                    "player_id": 171045,
                    "shirt_number": 11,
                    "player_events": []
                }
            ]
        },
        "bench": {
            "team_a": [
                {
                    "player_in_id": 8329,
                    "player_in_shirt_number": 10,
                    "player_out_id": 4281,
                    "player_out_time": " 65'",
                    "player_in_events": []
                },
                {
                    "player_in_id": 4225,
                    "player_in_shirt_number": 9,
                    "player_out_id": 7325,
                    "player_out_time": " 75'",
                    "player_in_events": []
                }
            ],
            "team_b": [
                {
                    "player_in_id": 7445,
                    "player_in_shirt_number": 3,
                    "player_out_id": 4040,
                    "player_out_time": " 46'",
                    "player_in_events": []
                },
                {
                    "player_in_id": 4367,
                    "player_in_shirt_number": 12,
                    "player_out_id": 171045,
                    "player_out_time": " 59'",
                    "player_in_events": []
                }
            ]
        },
        "team_a_goal_details": [
            {
                "player_id": 8298,
                "time": "17",
                "extra": null,
                "assist_player_id": 4281
            },
            {
                "player_id": 8298,
                "time": "43",
                "extra": null,
                "assist_player_id": 4281
            },
            {
                "player_id": 8697,
                "time": "44",
                "extra": null,
                "assist_player_id": 4281
            }
        ],
        "team_b_goal_details": [],
        "trends": {
            "home": [
                [
                    "chart",
                    "Coming into this game, Sheffield United has picked up 8 points from the last 5 games, both home and away. That's 1.6 points per game on average. BTTS has landed in just 1 of those games. Sheffield United has scored 4 times in the last 5 fixtures."
                ],
                [
                    "bad",
                    "Just 1 of the last 5 games for Sheffield United has ended with both teams scoring. They have won 2 of those 5 games. Overall, BTTS has landed in 4/10 games for Sheffield United this season."
                ]
            ],
            "away": [
                [
                    "chart",
                    "Coming into this game, Burnley has picked up 7 points from the last 5 games, both home and away. That's 1.4 points per game on average. BTTS has landed in an intriguing 3 of those games. Burnley has scored 8 times in the last 5 fixtures."
                ],
                [
                    "great",
                    "It's likely that Burnley will score today, as they have netted in the last 6 games coming into this one and have scored 8 goals in the last five games."
                ]
            ]
        },
        "homeGoals_timings": [
            "17",
            "43",
            "44"
        ],
        "awayGoals_timings": [],
        "team_a_card_details": [
            {
                "player_id": 8515,
                "card_type": "Yellow",
                "time": "89"
            }
        ],
        "team_b_card_details": [
            {
                "player_id": 3964,
                "card_type": "Yellow",
                "time": "34"
            },
            {
                "player_id": 4305,
                "card_type": "Yellow",
                "time": "68"
            }
        ],
        "h2h": {
            "team_a_id": 251,
            "team_b_id": 145,
            "previous_matches_results": {
                "team_a_win_home": 0,
                "team_a_win_away": 0,
                "team_b_win_home": 3,
                "team_b_win_away": 1,
                "draw": 1,
                "team_a_wins": 0,
                "team_b_wins": 4,
                "totalMatches": 5,
                "team_a_win_percent": 0,
                "team_b_win_percent": 80
            },
            "betting_stats": {
                "over05": 5,
                "over15": 3,
                "over25": 3,
                "over35": 3,
                "over45": 3,
                "over55": 2,
                "btts": 3,
                "clubACS": 0,
                "clubBCS": 2,
                "over05Percentage": 100,
                "over15Percentage": 60,
                "over25Percentage": 60,
                "over35Percentage": 60,
                "over45Percentage": 60,
                "over55Percentage": 40,
                "bttsPercentage": 60,
                "clubACSPercentage": 0,
                "clubBCSPercentage": 40,
                "avg_goals": 3.8,
                "total_goals": 19
            },
            "previous_matches_ids": [
                {
                    "id": 759075,
                    "date_unix": 1293894000,
                    "team_a_id": 145,
                    "team_b_id": 251,
                    "team_a_goals": 4,
                    "team_b_goals": 2
                },
                {
                    "id": 3224310,
                    "date_unix": 1228575600,
                    "team_a_id": 251,
                    "team_b_id": 145,
                    "team_a_goals": 2,
                    "team_b_goals": 3
                }
            ]
        },
        "tv_stations": null,
        "weather": {
            "coordinates": {
                "lat": 53.38,
                "lon": -1.47
            },
            "temperature": {
                "temp": 46.04,
                "unit": "fahrenheit"
            },
            "humidity": "93%",
            "wind": {
                "degree": 250,
                "speed": "11.41 m/s"
            },
            "type": "shower rain",
            "temperature_celcius": {
                "temp": 7.8,
                "unit": "celcius"
            },
            "clouds": "40%",
            "code": "rain",
            "pressure": 974
        },
        "odds_comparison": {
            "FT Result": {
                "1": {
                    "BetFred": "2.38",
                    "10Bet": "2.28",
                    "BetVictor": "2.38",
                    "TitanBet": "2.30",
                    "Planetwin365": "2.26"
                }
            }
        }
    }
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
| status | Status of the match('complete', 'suspended', 'canceled', 'incomplete'). |
| roundID | Round ID of the match within the season. |
| game_week | Game week of the match within the season. |
| homeGoals | Goal timings for home team goals. Array. |
| awayGoals | Goal timings for away team goals. Array. |
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
| cards_potential | Pre-Match average cards for both teams. |
| avg_potential | Pre-Match average total goals per match for both teams. |
| corners_o85_potential - corners_o105_potential | Pre-Match Over X Corners for both teams. |
| u15_potential - u45_potential | Pre-Match Stat for Under 1.5 - 4.5 for both teams. Average between both teams. |
| home_ppg | Points per game for home team. Current. |
| away_ppg | Points per game for away team. Current. |
| pre_match_home_ppg | Pre-Match Points Per Game for Home Team. |
| pre_match_away_ppg | Pre-Match Points Per Game for Away Team. |
| competition_id | Season ID of the league. |
| over05 - over55 | Set to true if the match ended with Over X goals. |
| btts | Set to true if match ended with BTTS. |
| lineups | Players and their IDs that have participated in this match as the starting 11. Cards and Goal timings are also included. |
| bench | Players that have started on the bench. Includes time of substitution if substituted. Cards and Goal timings are also included. |
| trends | Textual representation of statistical trends for team_a (Home) and team_b (Away). |
| team_a_card_details / team_b_card_details | Yellow/Red Card details - Player ID, Card type, and timing of booking. |
| h2h | Head to Head stats, including over X, wins, win percentages, previous match scores, and previous match ids. |
| odds_comparison | Full line of odds. |

[PreviousLeague Matches](https://footystats.org/api/documentations/match-schedule-and-stats) [NextLeague Players](https://footystats.org/api/documentations/league-players)
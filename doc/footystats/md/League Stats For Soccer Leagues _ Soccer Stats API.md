# League Stats For Soccer Leagues

# League Stats

## Get Season Stats and Teams

`GET`

`https://api.football-data-api.com/league-season?key=example&season_id=2012`

This endpoint responds with the League season's stats, and an array of Teams that have participated in the season. The teams contain all stats relevant to them.

#### Query Parameters

| max_time | integer | UNIX Timestamp. Set this number if you would like the API to return the stats of the league and the teams up to a certain time. For example, if I enter &max_time=1537984169, then the API will respond with stats as of September 26th, 2018. |
| --- | --- | --- |
| max_time | integer | UNIX Timestamp. Set this number if you would like the API to return the stats of the league and the teams up to a certain time. For example, if I enter &max_time=1537984169, then the API will respond with stats as of September 26th, 2018. |
| key* | string | Your API Key |
| season_id* | integer | ID of the league season that you would like to retrieve. |

```json
{
 "success": true,
 "data": [
 {
 "id": "161",
 "division": "1",
 "name": "Premier League",
 "shortHand": "premier-league",
 "country": "England",
 "type": "Domestic League",
 "iso": "gb-eng",
 "continent": "eu",
 "image": "competitions/england-premier-league.png",
 "image_thumb": "competitions/england-premier-league_thumb.png",
 "url": "/england/premier-league/2017-2018/overview",
 "parent_url": "/england/premier-league",
 "countryURL": "/england",
 "tie_break": "goal-difference",
 "domestic_scale": "1",
 "international_scale": "2",
 "clubs": "[...Array...]",
 "clubNum": 20,
 "year": "20172018",
 "season": "2017/2018",
 "starting_year": "2017",
 "ending_year": "2018",
 "no_home_away": false,
 "seasonClean": "2017/18"
 }
 ]
}
```

### Queries and Parameters

| id | ID of the season |
| --- | --- |
| id | ID of the season |
| name | Name of the league |
| english_name | Name of the league with diacritics and accents removed |
| country | Name of the country |
| domestic_scale | How important this league is within their own country. Often used to rank leagues in a feed. |
| international_scale | How important this country's leagues are globally. Often used to rank leagues in a feed. |
| status | Status of the season |
| format | Format of the league |
| division | Division of the League |
| no_home_away | Set to 1 if this league has no home or away distinction |
| starting_year | YStarting year of the season. ie 17-18 season starting year is 2017. |
| ending_year | Ending year of the season. ie 17-18 season ending year is 2018. |
| women | Set to 1 or true if this league is a women's football league |
| continent | Continent of which the league is in |
| image | URL of the League image. |
| clubNum | Number of clubs in the league |
| season | Full description of the season |
| goalTimingDisabled | Set to 1 if the goal timings are not available for all of this league |
| totalMatches | Total # of matches in this league season |
| matchesCompleted | Number of matches completed this season |
| canceledMatchesNum | Number of canceled matches this season |
| game_week | Current game week of the league |
| total_game_week | Total number of game weeks |
| round | ID of the current season round. This corresponds to the round of the tables |
| progress | Progress of the season in % |
| total_goals | Total number of goals in this season |
| home_teams_goals | Number of goals scored by the home team |
| home_teams_conceded | Number of goals conceded by the home team |
| away_teams_goals | Number of goals scored by the away team |
| away_teams_conceded | Number of goals conceded by the away team |
| seasonAVG_overall | Average number of total goals per match |
| seasonAVG_home | Average number of goals scored by home teams per match |
| seasonAVG_away | Average number of goals scored by away teams per match |
| btts_matches | Number of matches that ended in BTTS |
| seasonBTTSPercentage | % of matches that ended in BTTS |
| seasonCSPercentage | % of matches that ended with a Clean sheet for either team |
| home_teams_clean_sheets | Number of clean sheets kept by the home team |
| away_teams_clean_sheets | Number of clean sheets kept by the away team |
| home_teams_failed_to_score | Number of failed to score by the home team |
| away_teams_failed_to_score | Number of failed to score by the away team |
| riskNum | FootyStats Prediction Risk |
| homeAttackAdvantagePercentage | Home advantage in terms of Attacking. How much more the percentage of goals the home teams score as opposed to away teams. |
| homeDefenceAdvantagePercentage | Home advantage in terms of Defence. How much less the percentage of goals the home teams concede as opposed to away teams. |
| homeOverallAdvantage | Overall advantage between Attacking and Defensive advantage |
| cornersAVG_overall | Average corners per match in the league |
| cornersAVG_home | Average corners per match of the home team |
| cornersAVG_away | Average corners per match of the away team |
| cornersTotal_overall | Total number of corners that happened in this season |
| cornersTotal_home | Total number of corners that the home teams earned |
| cornersTotal_away | otal number of corners that the away teams earned |
| cardsAVG_overall | Average cards per match in this season |
| cardsAVG_home | verage cards conceded per match for the home team |
| cardsAVG_away | Average cards conceded per match for the way team |
| cardsTotal_overall | Total number of cards that was dealt in this season |
| cardsTotal_home | Total number of cards that was dealt to the home team this season |
| cardsTotal_away | Total number of cards that was dealt to the away team this season |
| foulsTotal_overall | Number of fouls that happened this season |
| foulsTotal_home | Number of fouls the home team had conceded this season |
| foulsTotal_away | Number of fouls the away team had conceded this season |
| foulsAVG_overall | Average number of fouls per match |
| foulsAVG_home | Average number of fouls per match for the home team |
| foulsAVG_away | Average number fouls per match for the away team |
| shotsTotal_overall | Total number of shots this season |
| shotsTotal_home | Total number of shots by the home team this season |
| shotsTotal_away | Total number of shots by the away team this season |
| shotsAVG_overall | Average shots per match this season |
| shotsAVG_home | Average shots per match by the home team this season |
| shotsAVG_away | Average shots per match by the away team this season |
| offsidesTotal_overall | Total number of Offsides this season |
| offsidesTotal_home | Total number of Offsides by the home team this season |
| offsidesTotal_away | Total number of Offsides by the away team this season |
| offsidesAVG_overall | Average number of offsides per match |
| offsidesAVG_home | Average number of offsides per match for the home team |
| offsidesAVG_away | Average number of offsides per match for the away team |
| offsidesOver05_overall - offsidesOver65_overall | Number of matches ending with Over 0.5 - 6.5 offsides this season |
| over05OffsidesPercentage_overall - over65OffsidesPercentage_overall | Percentage of Over 0.5 - 6.5 offside matches this season |
| seasonOver05Percentage_overall - seasonOver55Percentage_overall | Percentage of Over 0.5 - 5.5 match goals that happened this season |
| seasonUnder05Percentage_overall - seasonUnder55Percentage_overall | Percentage of Under 0.5 - 5.5 match goals that happened this season |
| cornersRecorded_matches | Number of matches with corners recorded |
| cardsRecorded_matches | Number of matches with cards recorded |
| offsidesRecorded_matches | Number of matches with offsides recorded |
| over65Corners_overall - over145Corners_overall | Number of matches that ended with over 6.5 - 14.5 corners |
| over65CornersPercentage_overall - over145CornersPercentage_overall | Percentage of matches that ended with Over 6.5 - 14.5 corners |
| over05Cards_overall - over75Cards_overall | Number of matches that ended with over 0.5 - 7.5 cards |
| over05CardsPercentage_overall - over75CardsPercentage_overall | Percentage of matches that ended with over 0.5 - 7.5 cards |
| homeWins | Number of home team wins |
| draws | Number of draws |
| awayWins | Number of away team wins |
| homeWinPercentage | Home team win % |
| drawPercentage | Draw % |
| awayWinPercentage | Away team win % |
| shotsRecorded_matches | Number of matches with shots recorded |
| foulsRecorded_matches | Number of matches with fouls recorded |
| failed_to_score_total | Number of times teams faileds to score |
| clean_sheets_total | Number of timess team kept a clean sheet |
| round_format | Format of the current round of the season. 0 = League, 1 = Group Stage, 2 = Knock outs |
| goals_min_0_to_10 - goals_min_76_to_90 | Number of goals within the given period |
| player_count | Number of players that have participated in this league |
| over05_fhg_num - over35_fhg_num | Number of matches with Over 0.5 - 3.5 first half goals during this season |
| over05_fhg_percentage - over35_fhg_percentage | Percentage of matches with Over 0.5 - 3.5 first half goals |
| over05_2hg_num - over35_2hg_num | Number of matches with Over 0.5 - 3.5 2nd half goals during this season |
| over05_2hg_percentage - over35_2hg_percentage | Percentage of matches with Over 0.5 - 3.5 2nd half goals |
| goalTimingsRecorded_num | Number of matches where goal timings have been recorded |
| iso | Country ISO of the league |
| seasonGoals_home | Goal timings for all goals scored by the home team. Array |
| seasonConceded_home | Goal timings for all goals conceded by the home team. Array |
| seasonGoals_away | Goal timings for all goals scored by the away team. |
| seasonConceded_away | Goal timings for all goals conceded by the away team |
| footystats_url | URL of the league on footystats |

[PreviousToday's Matches (Matches by day)](https://footystats.org/api/documentations/todays-matches-matches-by-day) [NextLeague Matches](https://footystats.org/api/documentations/match-schedule-and-stats)
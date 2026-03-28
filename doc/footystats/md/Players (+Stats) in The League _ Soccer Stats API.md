# Players (+Stats) in The League

# League Players
Stats for all players that participated in a season of a league.

## Get Array of Players

`GET`

`https://api.football-data-api.com/league-players?key=example&season_id=2012&include=stats`

This endpoint provides an array of players that have played in the particular league/season ID. Each player object has attributes described in https://footystats.org/api/documentations/player-individual

#### Query Parameters

| page | integer | Pagination. Each page has 200 players max. If there is more players returned, then they are in page=2 and beyond. |
| --- | --- | --- |
| page | integer | Pagination. Each page has 200 players max. If there is more players returned, then they are in page=2 and beyond. |
| max_time | integer | UNIX timestamp. Set this number if you would like the API to return the stats of the league and the teams up to a certain time. For example, if I enter &max_time=1537984169, then the API will respond with stats as of Sept 26, 2018. |
| key* | string | Your API Key |
| season_id* | integer | ID of the league season that you would like to retrieve. |

```json
{
 "success": true,
 "data": [
 {
 "id": 2984,
 "competition_id": 161,
 "full_name": "Petr Čech",
 "first_name": "Petr",
 "last_name": "Čech",
 "known_as": "Petr Čech",
 "shorthand": "petr-cech",
 "age": 36,
 "league": "Premier League",
 "league_type": "Domestic League",
 "season": "2017/2018",
 "starting_year": "2017",
 "ending_year": "2018",
 "url": "/players/czech-republic/petr-cech",
 "club_team_id": 59,
 "club_team_2_id": -1,
 "national_team_id": -1,
 "position": "Goalkeeper",
 "minutes_played_overall": 3040,
 "minutes_played_home": 1510,
 "minutes_played_away": 1530,
 "birthday": 390726000,
 "nationality": "Czech Republic",
 "continent": "eu",
 "appearances_overall": 34,
 "appearances_home": 17,
 "appearances_away": 17,
 "goals_overall": 0
 }
 ]
}
```

### Queries and Parameters

> ℹ️ You can test this API call by using the key "example" and loading the matches from the English Premier League 2018/2019 season (ID: 1625).

| id | ID of the Player. |
| --- | --- |
| id | ID of the Player. |
| competition_id | ID of the Season. |
| full_name | Player's full name. |
| first_name | Player's first name. |
| last_name | Player's last name. |
| known_as | What the player is known as. |
| shorthand | String with spaces replaced by - , and diacritics removed. |
| age | Player's current age. |
| league | In which league is the player currently playing in. |
| league_type | Player league's scale. |
| season | What season the latest for this league. |
| starting_year | In what year did the season start, for example if the season is 2022/2023, the starting_year will be 2022. |
| ending_year | In what year did the season end, for example if the season is 2022/2023, the ending_year will be 2023. |
| url | Player's current url on FootyStats you will need to add https://footystats.org before it to access the player page. |
| club_team_id | The club id of the team the player is evolving in. |
| club_team_2_id | The club id of the team the player has been lent to, -1 is the base value and means that the player is not on a loan. |
| national_team_id | The the national team id the player is playing for, -1 is the base value and means that the player is not in the national team. |
| position | Potition the player is currently evolving in. |
| minutes_played_overall | Shows how many minutes the player has played for the team this season. |
| minutes_played_home | Shows how many minutes the player has played when at home for the team this season. |
| minutes_played_away | Shows how many minutes the player has played when away for the team this season. |
| birthday | UNIX timestamp of the player's birth. |
| nationality | Player's nationality. |
| continent | What continent is the player from. |
| appearances_overall | How many matches has the player appeared in this season. |
| appearances_home | How many matches has the player appeared in for home games this season. |
| appearances_away | How many matches has the player appeared in for away games this season.. |
| goals_overall | How many goals the player scored this season. |

[PreviousLeague Teams](https://footystats.org/api/documentations/league-team) [NextLeague Referees](https://footystats.org/api/documentations/league-referees)
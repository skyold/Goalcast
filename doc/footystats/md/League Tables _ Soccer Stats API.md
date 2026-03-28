# League Tables

# League Table

## Get All Tables for a League Season

`GET`

`https://api.football-data-api.com/league-tables?key=example&season_id=2012`

Returns the data of each team as a JSON array.Add &include=stats to the request to get the stats of each team !

#### Query Parameters

| max_time | integer | UNIX Timestamp. Set this number if you would like the API to return the stats of the league and the teams up to a certain time. For example, if I enter &max_time=1537984169, then the API will respond with stats as of September 26th, 2019. |
| --- | --- | --- |
| max_time | integer | UNIX Timestamp. Set this number if you would like the API to return the stats of the league and the teams up to a certain time. For example, if I enter &max_time=1537984169, then the API will respond with stats as of September 26th, 2019. |
| key* | string | Your API Key |
| season_id* | integer | ID of the league season that you would like to retrieve. |

```json
{
 "success": true,
 "data": {
 "all_matches_table_overall": [],
 "all_matches_table_home": [],
 "all_matches_table_away": [],
 "specific_tables": [
 {
 "round": "1st Qualifying Round",
 "table": null,
 "groups": null
 },
 {
 "round": "Group Stage",
 "table": null,
 "groups": [
 {
 "name": "Group A",
 "table": [
 {
 "id": "76",
 "seasonGoals_home": 5,
 "seasonGoals_away": 5,
 "seasonConceded_away": 2,
 "seasonConceded_home": 4,
 "seasonGoals": 10,
 "points": 11,
 "seasonConceded": 6,
 "seasonGoalDifference": 4,
 "seasonWins_home": 1,
 "seasonWins_away": 2,
 "seasonWins_overall": 3,
 "seasonDraws_home": 1,
 "seasonDraws_away": 1,
 "seasonDraws_overall": 2,
 "seasonLosses_away": 0,
 "seasonLosses_overall": 1,
 "seasonLosses_home": 1,
 "matchesPlayed": 6,
 "name": "Villarreal CF",
 "country": null,
 "cleanName": "Villarreal",
 "shortHand": "villarreal-cf",
 "url": "/clubs/spain/villarreal-cf",
 "seasonURL_overall": "/clubs/spain/villarreal-cf",
 "seasonURL_home": "/clubs/spain/villarreal-cf",
 "seasonURL_away": "/clubs/spain/villarreal-cf",
 "position": 1,
 "zone": [],
 "corrections": 0,
 "wdl_record": "wddwwl"
 }
 ]
 }
 ]
 }
 ]
 }
}
```

### Queries and Parameters

> ℹ️ You can test this API call by using the key "example" and loading the league tables from the English Premier League 2018/2019 season (ID: 1625).

| league_table | If the league only has a single round with no play-off matches (ie Premier League), the League Table is stored here.Returns NULL if the league is a Cup format. |
| --- | --- |
| league_table | If the league only has a single round with no play-off matches (ie Premier League), the League Table is stored here.Returns NULL if the league is a Cup format. |
| all_matches_table_overall | Full table across all matches played during the season. For example, if this is a cup competition, then we will generate a table with all teams across all the matches that they've played. This is not necessarily the league table. |
| all_matches_table_home / all_matches_table_away | Full table only taking into account either Home matches or Away matches. |
| specific_tables | Array. Contains tables for each round of a season. Many leagues in the world have multiple rounds with league tables during 1 season.ie Uruguay Primera Division:Apertura - Table.Intermediate Round - Group Tables.Clausura - Table.Final Play-Offs - NULL (no table).ie Championship :Regular Season - Table.Play-Offs - NULL (no table).ie UEFA Champions League.Qualification Matches - NULL (no table).Group Round - Table for each group.8th Finals - NULL (no table).Quarter Finals - NULL (no table). |

[PreviousMatch Details (Stats, H2H, Odds Comparison)](https://footystats.org/api/documentations/match-details) [NextPlayer - individual](https://footystats.org/api/documentations/player-individual)
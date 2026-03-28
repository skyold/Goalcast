# BTTS Data & List

# BTTS Stats
Get Top Teams, Fixtures, and Leagues for BTTS.

## Get Top Teams, Fixtures, and Leagues for BTTS

`GET`

Returns the data of the best BTTS Leagues, Teams, and Fixtures.

#### Query Parameters

| key* | string | Your API Key |
| --- | --- | --- |
| key* | string | Your API Key |

```json
{
 "data": {
 "top_teams": {
 "title": "BTTS Teams",
 "list_type": "teams",
 "data": []
 },
 "top_fixtures": {
 "title": "BTTS Fixtures",
 "list_type": "fixtures",
 "data": []
 },
 "top_leagues": {
 "title": "BTTS Leagues",
 "list_type": "leagues",
 "data": []
 }
 }
}
```

### Queries and Parameters

| top_teams | Showcases the best BTTS teams. |
| --- | --- |
| top_teams | Showcases the best BTTS teams. |
| top_fixtures | Showcases the best BTTS fixtures. |
| top_leagues | Showcases the best BTTS leagues. |
| title | Name. |
| list_type | Either teams, leagues or fixtures. |
| data | Data related to the best BTTS stats. |

[PreviousReferee - Individual](https://footystats.org/api/documentations/referee-individual) [NextOver 2.5 stats](https://footystats.org/api/documentations/over-2.5-stats)
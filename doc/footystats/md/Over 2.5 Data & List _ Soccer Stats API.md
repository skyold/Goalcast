# Over 2.5 Data & List

# Over 2.5 Stats
Get Top Teams, Fixtures, and Leagues for Over 2.5 Goals.

## Get Over 2.5 Stats

`GET`

This endpoint allows you to get Over 2.5 data.

#### Query Parameters

| key* | string | Your API Key |
| --- | --- | --- |
| key* | string | Your API Key |

```json
{
 "success": true,
 "pager": {
 "current_page": 1,
 "max_page": 1,
 "results_per_page": 50,
 "total_results": 3
 },
 "metadata": {
 "request_limit": null,
 "request_remaining": null,
 "request_reset_message": "Request limit is refreshed every hour."
 },
 "data": {
 "top_teams": {
 "title": "Over 2.5 Teams",
 "list_type": "teams",
 "data": []
 },
 "top_fixtures": {
 "title": "Over 2.5 Fixtures",
 "list_type": "fixtures",
 "data": []
 },
 "top_leagues": {
 "title": "Over 2.5 Leagues",
 "list_type": "leagues",
 "data": []
 }
 },
 "message": ""
}
```

### Queries and Parameters
[PreviousBTTS Stats](https://footystats.org/api/documentations/btts-stats)
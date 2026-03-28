# Soccer League List

# League List

## Get Leagues

`GET`

`https://api.football-data-api.com/league-list?key=example`

Returns a JSON array of all leagues available in the API Database. Each season of a competition gives a unique ID.

#### Query Parameters

| chosen_leagues_only | string | If set to "true", the list will only return leagues that have been chosen by the user. ie ?key=xxxx&chosen_leagues_only=true |
| --- | --- | --- |
| chosen_leagues_only | string | If set to "true", the list will only return leagues that have been chosen by the user. ie ?key=xxxx&chosen_leagues_only=true |
| key* | string | Your API Key |
| country | integer | ISO number of the country. Will filter the response to leagues from the selected country. Remove any leading 0s. If there are no data returned, it means there are no leagues we support in that country/nation. |

```json
{
 "success": true,
 "data": [
 {
 "name": "USA MLS",
 "season": [
 {
 "id": 1,
 "year": 2016
 },
 {
 "id": 16,
 "year": 2015
 },
 {
 "id": 1076,
 "year": 2018
 }
 ]
 }
 ]
}
```

### Queries and Parameters

| name | Name of the league |
| --- | --- |
| name | Name of the league |
| league_name | Name of the league without country |
| country | Country name |
| season > id | ID of the season |
| season > year | Year of the season |

[PreviousMake the first API Call](https://footystats.org/api/documentations/make-the-first-api-call) [NextCountry list](https://footystats.org/api/documentations/country-list)
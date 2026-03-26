# Country List

# Country List

## Get Countries
`GET` `https://api.football-data-api.com/country-list?key=YOURKEY` Sample Response (Access the URL below)
[https://api.football-data-api.com/country-list?key=example](https://api.football-data-api.com/country-list?key=example) Returns a JSON array of Countries and its ISO numbers. Often called to get the ISO number for filtering the results of other endpoints.
#### Query Parameters

| key* | string | Your API Key |
| --- | --- | --- |
| key* | string | Your API Key |

```json
{
    "success": true,
    "data": [
        {
            "id": 4,
            "name": "Afghanistan"
        },
        {
            "id": 901,
            "name": "Africa"
        },
        {
            "id": 248,
            "name": "Åland Islands"
        },
        {
            "id": 8,
            "name": "Albania"
        }
    ]
}
```

### Queries and Parameters

| id | ID of the country |
| --- | --- |
| id | ID of the country |
| name | Name of the country |
| country | Country name |
| season > id | ID of the season |
| season > year | Year of the season |

[PreviousLeague List](https://footystats.org/api/documentations/league-list) [NextToday's Matches (Matches by day)](https://footystats.org/api/documentations/todays-matches-matches-by-day)
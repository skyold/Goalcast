import httpx
from config import settings

BASE_URL = "https://data.oddalerts.com/api"

class OddAlertClient:
    def __init__(self):
        self._client = httpx.AsyncClient(
            base_url=BASE_URL,
            params={"api_token": settings.oddalerts_api_key},
            timeout=10.0,
            follow_redirects=True,
        )

    async def get_fixture_ids(self) -> list[int]:
        r = await self._client.get("/fixtures/id")
        r.raise_for_status()
        data = r.json()
        return [item["id"] for item in (data if isinstance(data, list) else data.get("data", []))]

    async def get_fixture_detail(self, fixture_id: int) -> dict:
        r = await self._client.get(f"/fixtures/{fixture_id}")
        r.raise_for_status()
        raw = r.json()
        items = raw.get("data", []) if isinstance(raw, dict) else raw
        return items[0] if items else {}

    async def get_stats(self, fixture_id: int) -> dict:
        r = await self._client.get("/stats", params={"fixture_id": fixture_id, "type": "fixture"})
        r.raise_for_status()
        raw = r.json()
        return raw.get("data", raw) if isinstance(raw, dict) else {}

    async def get_dropping_odds(self) -> list[dict]:
        r = await self._client.get("/odds/dropping")
        r.raise_for_status()
        raw = r.json()
        return raw if isinstance(raw, list) else raw.get("data", [])

    async def get_trends(self, trend_type: str) -> list[dict]:
        r = await self._client.get(f"/trends/{trend_type}")
        r.raise_for_status()
        raw = r.json()
        return raw if isinstance(raw, list) else raw.get("data", [])

    async def get_odds_history(self, fixture_id: int) -> list[dict]:
        r = await self._client.get("/odds/history", params={"fixture_id": fixture_id})
        r.raise_for_status()
        raw = r.json()
        return raw if isinstance(raw, list) else raw.get("data", [])

    async def get_upcoming_fixtures(self, page: int = 1, per_page: int = 250) -> list[dict]:
        r = await self._client.get("/fixtures/upcoming", params={"page": page, "per_page": per_page})
        r.raise_for_status()
        raw = r.json()
        return raw.get("data", []) if isinstance(raw, dict) else []

    async def get_season_stats_last_x(self, season_id: int, n: int = 5, location: str = "overall") -> list[dict]:
        r = await self._client.get(f"/stats/season/{season_id}", params={"last_x": f"{n}_{location}"})
        r.raise_for_status()
        raw = r.json()
        return raw.get("data", []) if isinstance(raw, dict) else []

    async def get_odds_history_by_path(self, fixture_id: int) -> list[dict]:
        r = await self._client.get(f"/odds/history/{fixture_id}")
        r.raise_for_status()
        raw = r.json()
        if isinstance(raw, bool):
            return []
        return raw.get("data", []) if isinstance(raw, dict) else []

    async def get_odds_latest(self, bookmakers: str = "1,2", markets: str = "6,51",
                              per_page: int = 500, page: int = 1) -> list[dict]:
        r = await self._client.get("/odds/latest", params={"bookmakers": bookmakers,
                                                             "markets": markets,
                                                             "per_page": per_page,
                                                             "page": page})
        r.raise_for_status()
        raw = r.json()
        return raw.get("data", []) if isinstance(raw, dict) else []

    async def get_predictions_multiple(self, fixture_ids: list[int]) -> list[dict]:
        ids = ",".join(str(i) for i in fixture_ids)
        r = await self._client.get("/predictions/generate/multiple", params={"ids": ids})
        r.raise_for_status()
        raw = r.json()
        return raw.get("data", []) if isinstance(raw, dict) else []

    async def aclose(self) -> None:
        await self._client.aclose()

oddalerts_client = OddAlertClient()

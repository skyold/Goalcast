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
        r = await self._client.get(f"/fixtures/{fixture_id}", params={"include": "h2h,correctScores"})
        r.raise_for_status()
        raw = r.json()
        return raw.get("data", raw) if isinstance(raw, dict) else raw

    async def get_stats(self, fixture_id: int) -> dict:
        r = await self._client.get("/stats", params={"fixture_id": fixture_id})
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

    async def aclose(self) -> None:
        await self._client.aclose()

oddalerts_client = OddAlertClient()

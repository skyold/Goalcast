from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from goalcast.provider.base import BaseProvider
from goalcast.utils.logger import logger
from goalcast.config.settings import settings


COMPETITION_IDS = {
    "Premier League": "PL",
    "La Liga": "PD",
    "Serie A": "SA",
    "Bundesliga": "BL1",
    "Ligue 1": "FL1",
    "Champions League": "CL",
    "Europa League": "EL",
}


class FootballDataProvider(BaseProvider):
    BASE_URL = "https://api.football-data.org/v4"
    DEFAULT_TIMEOUT = 10.0

    def __init__(self, api_key: str = "", timeout: float = None):
        super().__init__(api_key or getattr(settings, 'FOOTBALL_DATA_API_KEY', ''), timeout)
        if not self.api_key:
            logger.warning("Football-Data API key not configured")

    @property
    def name(self) -> str:
        return "football_data"

    async def is_available(self) -> bool:
        return bool(self.api_key)

    async def _request_raw(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        headers = {}
        if self.api_key:
            headers["X-Auth-Token"] = self.api_key

        return await self._request(endpoint, params, headers)

    async def get_matches(
        self,
        competition: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        comp_id = COMPETITION_IDS.get(competition, competition)
        logger.debug(f"Provider {self.name}: get_matches({comp_id})")
        
        params = {}
        if date_from:
            params["dateFrom"] = date_from
        if date_to:
            params["dateTo"] = date_to
        
        return await self._request_raw(f"/competitions/{comp_id}/matches", params)

    async def get_standings(self, competition: str) -> Optional[Dict[str, Any]]:
        comp_id = COMPETITION_IDS.get(competition, competition)
        logger.debug(f"Provider {self.name}: get_standings({comp_id})")
        return await self._request_raw(f"/competitions/{comp_id}/standings")

    async def get_team(self, team_id: int) -> Optional[Dict[str, Any]]:
        logger.debug(f"Provider {self.name}: get_team({team_id})")
        return await self._request_raw(f"/teams/{team_id}")

    async def get_upcoming_matches(
        self,
        competition: str,
        days: int = 7
    ) -> Optional[Dict[str, Any]]:
        today = datetime.now()
        date_from = today.strftime("%Y-%m-%d")
        date_to = (today + timedelta(days=days)).strftime("%Y-%m-%d")
        return await self.get_matches(competition, date_from, date_to)

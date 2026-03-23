from typing import Dict, Any, Optional, List
from provider.base import BaseProvider
from utils.logger import logger
from config.settings import settings


class FootyStatsProvider(BaseProvider):
    BASE_URL = "https://api.football-data-api.com"
    DEFAULT_TIMEOUT = 30.0

    def __init__(self, api_key: str = "", timeout: float = None):
        super().__init__(api_key or settings.FOOTYSTATS_API_KEY, timeout)
        if not self.api_key:
            logger.warning("FootyStats API key not configured")

    @property
    def name(self) -> str:
        return "footystats"

    async def is_available(self) -> bool:
        return bool(self.api_key)

    async def _request_raw(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        if not self.api_key:
            logger.error("FootyStats API key is not set")
            return None

        url = f"{self.BASE_URL}{endpoint}"
        if params:
            params = dict(params)
            params["key"] = self.api_key
        else:
            params = {"key": self.api_key}

        return await self._request(endpoint, params)

    async def get_team(self, team_id: str) -> Optional[Dict[str, Any]]:
        logger.debug(f"Provider {self.name}: get_team({team_id})")
        return await self._request_raw("/team", {"team_id": team_id})

    async def get_match(self, match_id: str) -> Optional[Dict[str, Any]]:
        logger.debug(f"Provider {self.name}: get_match({match_id})")
        return await self._request_raw("/match", {"match_id": match_id})

    async def get_league_matches(
        self,
        league_id: str,
        date: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        logger.debug(f"Provider {self.name}: get_league_matches({league_id}, {date})")
        params = {"league_id": league_id}
        if date:
            params["date"] = date
        return await self._request_raw("/league-matches", params)

    async def get_league_table(
        self,
        league_id: str,
        season_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        logger.debug(f"Provider {self.name}: get_league_table({league_id})")
        params = {"league_id": league_id}
        if season_id:
            params["season_id"] = season_id
        return await self._request_raw("/league-tables", params)

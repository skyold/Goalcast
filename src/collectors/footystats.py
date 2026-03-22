import httpx
import asyncio
from typing import Optional, Dict, Any, List
from urllib.parse import urlencode

from src.utils.logger import logger
from src.utils.cache import cache_get, cache_set
from src.utils.rate_limiter import async_acquire
from config.settings import settings


class FootyStatsClient:
    BASE_URL = "https://api.footystats.org"

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or settings.FOOTYSTATS_API_KEY
        if not self.api_key:
            logger.warning("FootyStats API key not configured")

    async def _request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        cache_ttl: float = 1.0,
    ) -> Optional[Dict[str, Any]]:
        if not self.api_key:
            logger.error("FootyStats API key is not set")
            return None

        cache_key = f"{endpoint}:{str(params)}"
        cached = cache_get("footystats", cache_key)
        if cached is not None:
            logger.debug(f"Cache hit for {endpoint}")
            return cached

        await async_acquire("footystats", 1800.0 / 3600.0)

        url = f"{self.BASE_URL}{endpoint}"
        if params:
            params["key"] = self.api_key
        else:
            params = {"key": self.api_key}

        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(url, params=params)

                    if response.status_code == 429:
                        wait_time = 2 ** attempt * 10
                        logger.warning(f"Rate limited, waiting {wait_time}s")
                        await asyncio.sleep(wait_time)
                        continue

                    if response.status_code >= 500:
                        wait_time = 2**attempt
                        logger.warning(f"Server error {response.status_code}, retrying in {wait_time}s")
                        await asyncio.sleep(wait_time)
                        continue

                    if response.status_code == 200:
                        data = response.json()
                        if data.get("error"):
                            logger.error(f"FootyStats API error: {data.get('message')}")
                            return None
                        cache_set("footystats", cache_key, data, cache_ttl)
                        return data

                    return None

            except httpx.TimeoutException:
                logger.warning(f"Timeout on attempt {attempt + 1}")
                if attempt == 2:
                    return None
                await asyncio.sleep(2**attempt)

            except httpx.HTTPError as e:
                logger.error(f"HTTP error: {e}")
                if attempt == 2:
                    return None
                await asyncio.sleep(2**attempt)

        return None

    async def get_team(self, team_id: str) -> Optional[Dict[str, Any]]:
        logger.info(f"Fetching team data for team_id={team_id}")
        data = await self._request(f"/team", {"team_id": team_id}, cache_ttl=24.0)
        if not data:
            return None

        return self._parse_team_data(data)

    async def get_league_matches(
        self, season_id: str, date: Optional[str] = None
    ) -> Optional[List[Dict[str, Any]]]:
        logger.info(f"Fetching league matches for season_id={season_id}, date={date}")
        params = {"season_id": season_id}
        if date:
            params["date"] = date

        data = await self._request("/league-matches", params, cache_ttl=1.0)
        if not data:
            return None

        return self._parse_league_matches(data)

    async def get_match(self, match_id: str) -> Optional[Dict[str, Any]]:
        logger.info(f"Fetching match data for match_id={match_id}")
        data = await self._request(f"/match", {"match_id": match_id}, cache_ttl=0.5)
        if not data:
            return None

        return self._parse_match_data(data)

    async def get_league_table(
        self, season_id: str, max_time: Optional[str] = None
    ) -> Optional[List[Dict[str, Any]]]:
        logger.info(f"Fetching league table for season_id={season_id}")
        params = {"season_id": season_id}
        if max_time:
            params["max_time"] = max_time

        data = await self._request("/league-tables", params, cache_ttl=12.0)
        if not data:
            return None

        return self._parse_league_table(data)

    def _parse_team_data(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            record = data.get("data", {})
            if not record:
                return None

            return {
                "team_id": record.get("team_id"),
                "team_name": record.get("team_name"),
                "season_xg_home": record.get("seasonXG_home"),
                "season_xg_away": record.get("seasonXG_away"),
                "season_xga_home": record.get("seasonXGAgainst_home"),
                "season_xga_away": record.get("seasonXGAgainst_away"),
                "ppg_overall": record.get("ppg_overall"),
                "season_possession_home": record.get("seasonPossession_home"),
                "season_possession_away": record.get("seasonPossession_away"),
                "season_attacks_home": record.get("seasonAttacks_home"),
                "season_attacks_away": record.get("seasonAttacks_away"),
                "recent_form": record.get("recent_form", []),
                "league_position": record.get("league_position"),
            }
        except Exception as e:
            logger.error(f"Error parsing team data: {e}")
            return None

    def _parse_league_matches(self, data: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        try:
            records = data.get("data", [])
            matches = []
            for record in records:
                matches.append({
                    "match_id": record.get("match_id"),
                    "home_id": record.get("homeID"),
                    "away_id": record.get("awayID"),
                    "home_name": record.get("homeName"),
                    "away_name": record.get("awayName"),
                    "status": record.get("status"),
                    "start_date": record.get("start_date"),
                    "odds_home": record.get("odds_home"),
                    "odds_draw": record.get("odds_draw"),
                    "odds_away": record.get("odds_away"),
                    "home_score": record.get("home_score"),
                    "away_score": record.get("away_score"),
                })
            return matches
        except Exception as e:
            logger.error(f"Error parsing league matches: {e}")
            return None

    def _parse_match_data(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            record = data.get("data", {})
            if not record:
                return None

            return {
                "match_id": record.get("match_id"),
                "home_id": record.get("homeID"),
                "away_id": record.get("awayID"),
                "home_name": record.get("homeName"),
                "away_name": record.get("awayName"),
                "competition": record.get("competition"),
                "league_id": record.get("league_id"),
                "season_id": record.get("season_id"),
                "start_date": record.get("start_date"),
                "start_time": record.get("start_time"),
                "status": record.get("status"),
                "home_score": record.get("home_score"),
                "away_score": record.get("away_score"),
                "h2h": record.get("h2h", []),
                "odds_home": record.get("odds_home"),
                "odds_draw": record.get("odds_draw"),
                "odds_away": record.get("odds_away"),
                "btts_potential": record.get("btts_potential"),
                "over_25_potential": record.get("over_25_potential"),
                "home_league_position": record.get("home_league_position"),
                "away_league_position": record.get("away_league_position"),
                "home_ppg": record.get("home_ppg"),
                "away_ppg": record.get("away_ppg"),
            }
        except Exception as e:
            logger.error(f"Error parsing match data: {e}")
            return None

    def _parse_league_table(self, data: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        try:
            records = data.get("data", [])
            table = []
            for record in records:
                table.append({
                    "position": record.get("position"),
                    "team_id": record.get("team_id"),
                    "team_name": record.get("team_name"),
                    "played": record.get("played"),
                    "won": record.get("won"),
                    "drawn": record.get("drawn"),
                    "lost": record.get("lost"),
                    "goals_for": record.get("goals_for"),
                    "goals_against": record.get("goals_against"),
                    "points": record.get("points"),
                    "ppg": record.get("ppg"),
                    "zone": record.get("zone"),
                })
            return table
        except Exception as e:
            logger.error(f"Error parsing league table: {e}")
            return None

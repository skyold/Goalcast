import httpx
import csv
import asyncio
import json
from typing import Optional, Dict, Any
from io import StringIO
from pathlib import Path

from src.utils.logger import logger
from src.utils.cache import cache_get, cache_set
from src.utils.rate_limiter import configure_sync_limit, async_acquire
from config.settings import settings, BASE_DIR


TEAM_NAME_MAP_PATH = BASE_DIR / "config" / "team_name_map.json"


def _load_team_name_map() -> Dict[str, Dict[str, str]]:
    if TEAM_NAME_MAP_PATH.exists():
        try:
            with open(TEAM_NAME_MAP_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


_TEAM_NAME_MAP_DATA = _load_team_name_map()


class ClubEloClient:
    BASE_URL = "http://api.clubelo.com"

    def __init__(self):
        configure_sync_limit("clubelo", 0.5)
        self._name_map = self._build_name_map()

    def _build_name_map(self) -> Dict[str, str]:
        result = {}
        for league, teams in _TEAM_NAME_MAP_DATA.items():
            for team_name, elo_name in teams.items():
                result[team_name] = elo_name
        return result

    def _map_team_name(self, team_name: str) -> str:
        if team_name in self._name_map:
            return self._name_map[team_name]
        return team_name.replace(" ", "-")

    async def get_elo(self, team_name: str, date: Optional[str] = None) -> Optional[float]:
        mapped_name = self._map_team_name(team_name)
        cache_key = f"{mapped_name}:{date or 'current'}"
        cached = cache_get("clubelo", cache_key)
        if cached is not None:
            logger.debug(f"Cache hit for ClubElo {team_name}")
            return cached.get("elo")

        await async_acquire("clubelo")

        url = f"{self.BASE_URL}/{mapped_name}"
        if date:
            url = f"{url}/{date}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)

                if response.status_code == 404:
                    logger.warning(f"Team not found in ClubElo: {team_name}")
                    return None

                if response.status_code != 200:
                    logger.error(f"ClubElo API error: {response.status_code}")
                    return None

                csv_text = response.text
                reader = csv.DictReader(StringIO(csv_text))
                rows = list(reader)

                if not rows:
                    return None

                latest_elo = float(rows[-1].get("Elo", 0))
                cache_set("clubelo", cache_key, {"elo": latest_elo}, 48.0)
                return latest_elo

        except Exception as e:
            logger.error(f"Error fetching ClubElo for {team_name}: {e}")
            return None

    def get_elo_sync(self, team_name: str, date: Optional[str] = None) -> Optional[float]:
        mapped_name = self._map_team_name(team_name)
        cache_key = f"{mapped_name}:{date or 'current'}"
        cached = cache_get("clubelo", cache_key)
        if cached is not None:
            return cached.get("elo")

        url = f"{self.BASE_URL}/{mapped_name}"
        if date:
            url = f"{url}/{date}"

        try:
            response = httpx.get(url, timeout=30.0)
            if response.status_code == 404:
                return None
            if response.status_code != 200:
                return None

            csv_text = response.text
            reader = csv.DictReader(StringIO(csv_text))
            rows = list(reader)

            if not rows:
                return None

            latest_elo = float(rows[-1].get("Elo", 0))
            cache_set("clubelo", cache_key, {"elo": latest_elo}, 48.0)
            return latest_elo

        except Exception as e:
            logger.error(f"Error fetching ClubElo for {team_name}: {e}")
            return None

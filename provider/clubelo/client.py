from typing import Dict, Any, Optional
import csv
from io import StringIO
from pathlib import Path
import json
from goalcast.provider.base import BaseProvider
from goalcast.utils.logger import logger
from goalcast.config.settings import BASE_DIR


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


class ClubEloProvider(BaseProvider):
    BASE_URL = "http://api.clubelo.com"
    DEFAULT_TIMEOUT = 30.0

    def __init__(self, timeout: float = None):
        super().__init__("", timeout)
        self._name_map = self._build_name_map()

    @property
    def name(self) -> str:
        return "clubelo"

    async def is_available(self) -> bool:
        return True

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

    async def get_elo(
        self,
        team_name: str,
        date: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        logger.debug(f"Provider {self.name}: get_elo({team_name}, {date})")
        
        mapped_name = self._map_team_name(team_name)
        endpoint = f"/{mapped_name}"
        if date:
            endpoint = f"{endpoint}/{date}"

        raw_data = await self._request(endpoint)
        if raw_data is None:
            return None
        
        if isinstance(raw_data, str):
            try:
                reader = csv.DictReader(StringIO(raw_data))
                rows = list(reader)
                if rows:
                    return {
                        "team": team_name,
                        "elo": float(rows[-1].get("Elo", 0)),
                        "date": rows[-1].get("Date"),
                        "rank": rows[-1].get("Rank"),
                        "country": rows[-1].get("Country"),
                        "level": rows[-1].get("Level"),
                    }
            except Exception as e:
                logger.error(f"Error parsing ClubElo CSV: {e}")
        
        return None

from typing import Dict, Any, Optional, List
from pathlib import Path
from goalcast.provider.base import BaseProvider
from goalcast.utils.logger import logger
from goalcast.config.settings import BASE_DIR

try:
    from understat import Understat
    import aiohttp
    UNDERSTAT_AVAILABLE = True
except ImportError:
    UNDERSTAT_AVAILABLE = False
    logger.warning("understat package not installed. Run: pip install understat")


UNDERSTAT_LEAGUES_PATH = BASE_DIR / "config" / "understat_leagues.json"


def _load_league_map() -> Dict[str, str]:
    if UNDERSTAT_LEAGUES_PATH.exists():
        try:
            import json
            with open(UNDERSTAT_LEAGUES_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "Premier League": "EPL",
        "La Liga": "La_liga",
        "Serie A": "Serie_A",
        "Bundesliga": "Bundesliga",
        "Ligue 1": "Ligue_1",
    }


_LEAGUE_MAP = _load_league_map()


class UnderstatProvider(BaseProvider):
    BASE_URL = ""
    DEFAULT_TIMEOUT = 30.0

    def __init__(self, timeout: float = None):
        super().__init__("", timeout)
        self._league_map = _LEAGUE_MAP
        self._session = None
        self._understat = None

    @property
    def name(self) -> str:
        return "understat"

    async def is_available(self) -> bool:
        return UNDERSTAT_AVAILABLE

    async def _get_client(self):
        if not UNDERSTAT_AVAILABLE:
            return None
        
        if self._session is None or self._session.closed:
            import aiohttp
            self._session = aiohttp.ClientSession()
            self._understat = Understat(self._session)
        
        return self._understat

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
            self._understat = None

    def _map_league(self, competition: str) -> str:
        return self._league_map.get(competition, competition)

    async def get_team_stats(
        self,
        team_name: str,
        league: str,
        season: str = "2024"
    ) -> Optional[Dict[str, Any]]:
        logger.debug(f"Provider {self.name}: get_team_stats({team_name}, {league})")
        
        if not UNDERSTAT_AVAILABLE:
            return None
        
        try:
            understat = await self._get_client()
            if understat is None:
                return None
            
            league_key = self._map_league(league)
            teams = await understat.get_teams(league_key, season)
            
            for team in teams:
                if team.get("title", "").lower() == team_name.lower():
                    return team
            
            logger.warning(f"Team not found in Understat: {team_name}")
            return None

        except Exception as e:
            logger.error(f"Error fetching Understat team stats: {e}")
            return None

    async def get_team_matches(
        self,
        team_name: str,
        league: str,
        season: str = "2024"
    ) -> Optional[List[Dict[str, Any]]]:
        logger.debug(f"Provider {self.name}: get_team_matches({team_name}, {league})")
        
        if not UNDERSTAT_AVAILABLE:
            return None
        
        try:
            understat = await self._get_client()
            if understat is None:
                return None
            
            league_key = self._map_league(league)
            matches = await understat.get_team_results(league_key, season, team_name)
            return matches

        except Exception as e:
            logger.error(f"Error fetching Understat matches: {e}")
            return None

    async def get_league_matches(
        self,
        league: str,
        season: str = "2024"
    ) -> Optional[List[Dict[str, Any]]]:
        logger.debug(f"Provider {self.name}: get_league_matches({league})")
        
        if not UNDERSTAT_AVAILABLE:
            return None
        
        try:
            understat = await self._get_client()
            if understat is None:
                return None
            
            league_key = self._map_league(league)
            matches = await understat.get_league_results(league_key, season)
            return matches

        except Exception as e:
            logger.error(f"Error fetching Understat league matches: {e}")
            return None

    async def get_player_stats(
        self,
        player_name: str,
        league: str = "EPL",
        season: str = "2024"
    ) -> Optional[Dict[str, Any]]:
        logger.debug(f"Provider {self.name}: get_player_stats({player_name})")
        
        if not UNDERSTAT_AVAILABLE:
            return None
        
        try:
            understat = await self._get_client()
            if understat is None:
                return None
            
            players = await understat.get_league_players(league, season)
            
            for player in players:
                if player.get("player_name", "").lower() == player_name.lower():
                    return player
            
            return None

        except Exception as e:
            logger.error(f"Error fetching Understat player stats: {e}")
            return None

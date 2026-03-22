import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path

from src.utils.logger import logger
from src.utils.cache import cache_get, cache_set
from src.utils.rate_limiter import async_acquire
from config.settings import BASE_DIR

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


class UnderstatClient:
    def __init__(self):
        self._league_map = _LEAGUE_MAP
        self._session = None
        self._understat = None

    async def _get_client(self):
        if not UNDERSTAT_AVAILABLE:
            raise RuntimeError("understat package not installed")
        
        if self._session is None or self._session.closed:
            import aiohttp
            self._session = aiohttp.ClientSession()
            self._understat = Understat(self._session)
        
        return self._understat

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    def _map_league(self, competition: str) -> str:
        return self._league_map.get(competition, competition)

    async def get_team_stats(
        self, 
        team_name: str, 
        league: str, 
        season: str = "2024"
    ) -> Optional[Dict[str, Any]]:
        cache_key = f"team_stats:{league}:{team_name}:{season}"
        cached = cache_get("understat", cache_key)
        if cached is not None:
            logger.debug(f"Cache hit for Understat team stats: {team_name}")
            return cached

        await async_acquire("understat", 60.0 / 60.0)

        try:
            understat = await self._get_client()
            league_key = self._map_league(league)

            teams = await understat.get_teams(league_key, season)
            
            for team in teams:
                if team.get("title", "").lower() == team_name.lower():
                    result = self._parse_team_stats(team)
                    cache_set("understat", cache_key, result, 168.0)
                    return result

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
        cache_key = f"team_matches:{league}:{team_name}:{season}"
        cached = cache_get("understat", cache_key)
        if cached is not None:
            logger.debug(f"Cache hit for Understat matches: {team_name}")
            return cached

        await async_acquire("understat", 60.0 / 60.0)

        try:
            understat = await self._get_client()
            league_key = self._map_league(league)

            matches = await understat.get_team_results(league_key, season, team_name)
            
            result = [self._parse_match(m) for m in matches]
            cache_set("understat", cache_key, result, 6.0)
            return result

        except Exception as e:
            logger.error(f"Error fetching Understat matches: {e}")
            return None

    async def get_league_matches(
        self,
        league: str,
        season: str = "2024"
    ) -> Optional[List[Dict[str, Any]]]:
        cache_key = f"league_matches:{league}:{season}"
        cached = cache_get("understat", cache_key)
        if cached is not None:
            logger.debug(f"Cache hit for Understat league matches: {league}")
            return cached

        await async_acquire("understat", 60.0 / 60.0)

        try:
            understat = await self._get_client()
            league_key = self._map_league(league)

            matches = await understat.get_league_results(league_key, season)
            
            result = [self._parse_match(m) for m in matches]
            cache_set("understat", cache_key, result, 6.0)
            return result

        except Exception as e:
            logger.error(f"Error fetching Understat league matches: {e}")
            return None

    async def get_player_stats(
        self,
        player_name: str,
        league: str = "EPL",
        season: str = "2024"
    ) -> Optional[Dict[str, Any]]:
        cache_key = f"player:{league}:{player_name}:{season}"
        cached = cache_get("understat", cache_key)
        if cached is not None:
            return cached

        await async_acquire("understat", 60.0 / 60.0)

        try:
            understat = await self._get_client()

            players = await understat.get_league_players(league, season)
            
            for player in players:
                if player.get("player_name", "").lower() == player_name.lower():
                    result = self._parse_player_stats(player)
                    cache_set("understat", cache_key, result, 24.0)
                    return result

            return None

        except Exception as e:
            logger.error(f"Error fetching Understat player stats: {e}")
            return None

    def _parse_team_stats(self, team: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "team_name": team.get("title"),
            "team_id": team.get("id"),
            "games": team.get("games", 0),
            "wins": team.get("wins", 0),
            "draws": team.get("draws", 0),
            "losses": team.get("loses", 0),
            "goals_scored": team.get("scored", 0),
            "goals_conceded": team.get("missed", 0),
            "xg": float(team.get("xG", 0) or 0),
            "xga": float(team.get("xGA", 0) or 0),
            "npxg": float(team.get("npxG", 0) or 0),
            "npxga": float(team.get("npxGA", 0) or 0),
            "ppda_att": float(team.get("ppda", {}).get("att", 0) or 0) if isinstance(team.get("ppda"), dict) else 0,
            "ppda_def": float(team.get("ppda", {}).get("def", 0) or 0) if isinstance(team.get("ppda"), dict) else 0,
            "deep_passes": team.get("deep", 0),
            "deep_passes_allowed": team.get("deep_allowed", 0),
            "points": team.get("pts", 0),
            "position": team.get("position", 0),
        }

    def _parse_match(self, match: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "match_id": match.get("id"),
            "home_team": match.get("h", {}).get("title") if isinstance(match.get("h"), dict) else match.get("h"),
            "away_team": match.get("a", {}).get("title") if isinstance(match.get("a"), dict) else match.get("a"),
            "home_goals": match.get("goals", {}).get("h", 0) if isinstance(match.get("goals"), dict) else 0,
            "away_goals": match.get("goals", {}).get("a", 0) if isinstance(match.get("goals"), dict) else 0,
            "home_xg": float(match.get("xG", {}).get("h", 0) or 0) if isinstance(match.get("xG"), dict) else 0,
            "away_xg": float(match.get("xG", {}).get("a", 0) or 0) if isinstance(match.get("xG"), dict) else 0,
            "datetime": match.get("datetime"),
            "result": match.get("result"),
        }

    def _parse_player_stats(self, player: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "player_name": player.get("player_name"),
            "player_id": player.get("id"),
            "team_name": player.get("team_title"),
            "position": player.get("position"),
            "games": player.get("games", 0),
            "minutes": player.get("time", 0),
            "goals": player.get("goals", 0),
            "assists": player.get("assists", 0),
            "xg": float(player.get("xG", 0) or 0),
            "xa": float(player.get("xA", 0) or 0),
            "npxg": float(player.get("npxG", 0) or 0),
            "npxg_xa": float(player.get("npxG+xA", 0) or 0),
            "shots": player.get("shots", 0),
            "key_passes": player.get("key_passes", 0),
            "yellow_cards": player.get("yellow_cards", 0),
            "red_cards": player.get("red_cards", 0),
        }


def compute_recent_form(
    matches: List[Dict[str, Any]], 
    team_name: str, 
    n: int = 5
) -> Dict[str, Any]:
    if not matches:
        return {
            "form": [],
            "xg_sum": 0.0,
            "xga_sum": 0.0,
            "xg_avg": 0.0,
            "xga_avg": 0.0,
            "goals_scored": 0,
            "goals_conceded": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "points": 0,
        }

    recent = matches[-n:] if len(matches) >= n else matches
    
    form = []
    xg_sum = 0.0
    xga_sum = 0.0
    goals_scored = 0
    goals_conceded = 0
    wins = 0
    draws = 0
    losses = 0

    for match in recent:
        is_home = match.get("home_team", "").lower() == team_name.lower()
        
        if is_home:
            team_goals = match.get("home_goals", 0)
            team_xg = match.get("home_xg", 0)
            opp_goals = match.get("away_goals", 0)
            opp_xg = match.get("away_xg", 0)
        else:
            team_goals = match.get("away_goals", 0)
            team_xg = match.get("away_xg", 0)
            opp_goals = match.get("home_goals", 0)
            opp_xg = match.get("home_xg", 0)

        xg_sum += float(team_xg)
        xga_sum += float(opp_xg)
        goals_scored += int(team_goals)
        goals_conceded += int(opp_goals)

        if team_goals > opp_goals:
            form.append("W")
            wins += 1
        elif team_goals < opp_goals:
            form.append("L")
            losses += 1
        else:
            form.append("D")
            draws += 1

    games = len(recent)
    points = wins * 3 + draws

    return {
        "form": form,
        "xg_sum": round(xg_sum, 2),
        "xga_sum": round(xga_sum, 2),
        "xg_avg": round(xg_sum / games, 3) if games > 0 else 0.0,
        "xga_avg": round(xga_sum / games, 3) if games > 0 else 0.0,
        "goals_scored": goals_scored,
        "goals_conceded": goals_conceded,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "points": points,
        "ppg": round(points / games, 2) if games > 0 else 0.0,
    }


def compute_ppda_season(
    team_stats: Dict[str, Any]
) -> Dict[str, float]:
    ppda_att = team_stats.get("ppda_att", 0)
    ppda_def = team_stats.get("ppda_def", 0)
    
    ppda = 0.0
    if ppda_att > 0 and ppda_def > 0:
        ppda = round(ppda_def / ppda_att, 2)
    
    return {
        "ppda": ppda,
        "ppda_att": ppda_att,
        "ppda_def": ppda_def,
    }

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from provider.base import BaseProvider
from utils.logger import logger


ESPN_API = "https://site.api.espn.com/apis/site/v2/sports/soccer"


class ESPNProvider(BaseProvider):
    BASE_URL = ESPN_API
    DEFAULT_TIMEOUT = 30.0

    LEAGUE_MAPPING = {
        "Premier League": "eng.1",
        "La Liga": "esp.1",
        "Serie A": "ita.1",
        "Bundesliga": "ger.1",
        "Ligue 1": "fra.1",
        "Champions League": "eng.1",
        "Europa League": "eng.1",
    }

    def __init__(self, timeout: float = None):
        super().__init__("", timeout)
        self._cache_ttl = 3600.0

    @property
    def name(self) -> str:
        return "espn"

    async def is_available(self) -> bool:
        return True

    def _get_league_key(self, league: str) -> str:
        return self.LEAGUE_MAPPING.get(league, league.lower().replace(" ", ""))

    async def get_schedule(
        self,
        league: str,
        season: Optional[str] = None
    ) -> Optional[List[Dict[str, Any]]]:
        logger.debug(f"Provider {self.name}: get_schedule({league}, {season})")

        if season is None:
            season = self._get_current_season()

        league_key = self._get_league_key(league)

        try:
            url = f"{self.BASE_URL}/{league_key}/scoreboard"
            params = {"dates": self._get_season_date_range(season)}

            response = await self._request(url, params)
            if not response:
                return None

            events = response.get("events", [])
            schedule = []

            for event in events:
                try:
                    competition = event.get("competitions", [{}])[0]
                    competitors = competition.get("competitors", [])

                    if len(competitors) < 2:
                        continue

                    home = competitors[0].get("team", {})
                    away = competitors[1].get("team", {})

                    schedule.append({
                        "match_id": event.get("id"),
                        "date": event.get("date"),
                        "home_team": home.get("name"),
                        "away_team": away.get("name"),
                        "home_team_id": home.get("id"),
                        "away_team_id": away.get("id"),
                        "status": event.get("status", {}).get("type", {}).get("name"),
                        "league": league,
                        "season": season,
                    })
                except Exception as e:
                    logger.warning(f"Error parsing event: {e}")
                    continue

            return schedule

        except Exception as e:
            logger.error(f"Error fetching ESPN schedule: {e}")
            return None

    async def get_match(self, match_id: str) -> Optional[Dict[str, Any]]:
        logger.debug(f"Provider {self.name}: get_match({match_id})")

        try:
            url = f"{self.BASE_URL}/summary"
            params = {"event": match_id}

            response = await self._request(url, params)
            if not response:
                return None

            event = response.get("event", {})
            competition = event.get("competitions", [{}])[0]
            competitors = competition.get("competitors", [])

            if len(competitors) < 2:
                return None

            home = competitors[0].get("team", {})
            away = competitors[1].get("team", {})

            home_score = competitors[0].get("score", {}).get("value")
            away_score = competitors[1].get("score", {}).get("value")

            result = {
                "match_id": event.get("id"),
                "date": event.get("date"),
                "home_team": home.get("name"),
                "away_team": away.get("name"),
                "home_team_id": home.get("id"),
                "away_team_id": away.get("id"),
                "home_score": home_score,
                "away_score": away_score,
                "status": event.get("status", {}).get("type", {}).get("name"),
                "venue": response.get("gameInfo", {}).get("venue", {}).get("fullName"),
                "attendance": response.get("gameInfo", {}).get("attendance"),
            }

            return result

        except Exception as e:
            logger.error(f"Error fetching ESPN match {match_id}: {e}")
            return None

    async def get_match_stats(self, match_id: str) -> Optional[Dict[str, Any]]:
        logger.debug(f"Provider {self.name}: get_match_stats({match_id})")

        match_data = await self.get_match(match_id)
        if not match_data:
            return None

        try:
            url = f"{self.BASE_URL}/summary"
            params = {"event": match_id}

            response = await self._request(url, params)
            if not response:
                return match_data

            boxscore = response.get("boxscore", {})
            teams = boxscore.get("teams", [])

            stats = {}
            for team_data in teams:
                team_name = team_data.get("team", {}).get("name")
                team_stats = team_data.get("statistics", [])

                stats[team_name] = {}
                for stat in team_stats:
                    stats[team_name][stat.get("name")] = stat.get("value")

            match_data["stats"] = stats
            return match_data

        except Exception as e:
            logger.warning(f"Error fetching match stats: {e}")
            return match_data

    async def get_team_matches(
        self,
        team_name: str,
        league: Optional[str] = None,
        season: Optional[str] = None
    ) -> Optional[List[Dict[str, Any]]]:
        logger.debug(f"Provider {self.name}: get_team_matches({team_name}, {league}, {season})")

        if league:
            schedule = await self.get_schedule(league, season)
            if not schedule:
                return None

            team_matches = [
                m for m in schedule
                if team_name.lower() in m.get("home_team", "").lower()
                or team_name.lower() in m.get("away_team", "").lower()
            ]
            return team_matches

        all_matches = []
        for league_name in self.LEAGUE_MAPPING.keys():
            schedule = await self.get_schedule(league_name, season)
            if schedule:
                team_matches = [
                    m for m in schedule
                    if team_name.lower() in m.get("home_team", "").lower()
                    or team_name.lower() in m.get("away_team", "").lower()
                ]
                all_matches.extend(team_matches)

        return all_matches if all_matches else None

    async def get_league_standings(
        self,
        league: str,
        season: Optional[str] = None
    ) -> Optional[List[Dict[str, Any]]]:
        logger.debug(f"Provider {self.name}: get_league_standings({league})")

        league_key = self._get_league_key(league)

        try:
            url = f"{self.BASE_URL}/{league_key}/standings"
            params = {}
            if season:
                params["season"] = season

            response = await self._request(url, params)
            if not response:
                return None

            standings = []
            for group in response.get("standings", []):
                for entry in group.get("teams", []):
                    standings.append({
                        "rank": entry.get("rank"),
                        "team_id": entry.get("team", {}).get("id"),
                        "team_name": entry.get("team", {}).get("name"),
                        "games_played": entry.get("gamesPlayed"),
                        "wins": entry.get("wins"),
                        "ties": entry.get("ties"),
                        "losses": entry.get("losses"),
                        "points": entry.get("points"),
                        "goals_for": entry.get("goalsFor"),
                        "goals_against": entry.get("goalsAgainst"),
                    })

            return standings

        except Exception as e:
            logger.error(f"Error fetching standings: {e}")
            return None

    def _get_current_season(self) -> str:
        now = datetime.now(tz=timezone.utc)
        year = now.year
        if now.month >= 7:
            return f"{year}"
        else:
            return f"{year - 1}"

    def _get_season_date_range(self, season: str) -> str:
        start_year = int(season[:4]) if len(season) == 4 else int(season)
        start_date = f"{start_year}0701"
        end_year = start_year + 1
        end_date = f"{end_year}0630"
        return f"{start_date}-{end_date}"

    def __repr__(self) -> str:
        return f"<ESPNProvider>"

from typing import Optional, List, Dict, Any
from datasource.base import DataSource, DataCapability
from datasource.types import DataSourceType, Team
from provider.base import BaseProvider
from utils.logger import logger


class TeamDataSource(DataSource[Team]):
    def __init__(self, providers: List[BaseProvider] = None):
        super().__init__(providers)
        self._cache_ttl = 3600.0

    @property
    def data_type(self) -> DataSourceType:
        return DataSourceType.TEAM

    def capabilities(self) -> DataCapability:
        return DataCapability(
            type=DataSourceType.TEAM,
            name="球队数据",
            description="球队统计、xG/xGA、近期状态等",
            providers=[p.name for p in self._providers],
            params={
                "team_id": "球队 ID",
                "team_name": "球队名称",
                "league": "联赛名称",
                "season": "赛季",
            },
            update_freq=3600.0,
            historical=True,
            realtime=False,
        )

    async def fetch(self, **params) -> Optional[Team]:
        team_id = params.get("team_id")
        team_name = params.get("team_name")
        
        if not team_id and not team_name:
            logger.error("team_id or team_name is required")
            return None

        cache_key = self._cache_key(**params)
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        team = None
        
        if team_id:
            raw_data = await self._try_providers("get_team", team_id=team_id)
            if raw_data:
                team = self.parse(raw_data)
        
        if team is None and team_name:
            for provider in self._providers:
                try:
                    if hasattr(provider, "get_team_stats"):
                        raw_data = await provider.get_team_stats(
                            team_name=team_name,
                            league=params.get("league", "Premier League"),
                            season=params.get("season", "2024")
                        )
                        if raw_data:
                            team = self.parse_understat(raw_data)
                            break
                except Exception as e:
                    logger.warning(f"Provider {provider.name} failed: {e}")
                    continue

        if team:
            await self._enrich_team_data(team, params)
            self._set_cache(cache_key, team)
        
        return team

    async def _enrich_team_data(self, team: Team, params: Dict[str, Any]) -> None:
        for provider in self._providers:
            if provider.name == "clubelo":
                try:
                    elo_data = await provider.get_elo(team.name)
                    if elo_data and elo_data.get("elo"):
                        team.elo = elo_data.get("elo")
                        break
                except Exception:
                    pass

    def parse(self, raw_data: Dict[str, Any]) -> Optional[Team]:
        if not raw_data:
            return None

        data = raw_data.get("data", raw_data)
        
        try:
            return Team(
                team_id=str(data.get("team_id") or data.get("id", "")),
                name=data.get("team_name") or data.get("name") or data.get("teamName", ""),
                short_name=data.get("short_name") or data.get("shortName") or data.get("tla"),
                
                xg_home=data.get("season_xg_home") or data.get("seasonXG_home"),
                xg_away=data.get("season_xg_away") or data.get("seasonXG_away"),
                xga_home=data.get("season_xga_home") or data.get("seasonXGAgainst_home"),
                xga_away=data.get("season_xga_away") or data.get("seasonXGAgainst_away"),
                
                ppg=data.get("ppg_overall") or data.get("ppg"),
                position=data.get("league_position") or data.get("position"),
                played=data.get("played") or data.get("games"),
                won=data.get("won") or data.get("wins"),
                drawn=data.get("drawn") or data.get("draws"),
                lost=data.get("lost") or data.get("losses"),
                goals_for=data.get("goals_for") or data.get("goals_scored") or data.get("scored"),
                goals_against=data.get("goals_against") or data.get("goals_conceded") or data.get("missed"),
                
                possession=data.get("season_possession_home") or data.get("possession"),
                
                recent_form=data.get("recent_form", []),
                
                country=data.get("country"),
                venue=data.get("venue"),
            )
        except Exception as e:
            logger.error(f"Error parsing team data: {e}")
            return None

    def parse_understat(self, raw_data: Dict[str, Any]) -> Optional[Team]:
        if not raw_data:
            return None

        try:
            ppda_data = raw_data.get("ppda", {})
            ppda_att = ppda_data.get("att", 0) if isinstance(ppda_data, dict) else 0
            ppda_def = ppda_data.get("def", 0) if isinstance(ppda_data, dict) else 0
            ppda = ppda_def / ppda_att if ppda_att > 0 else 0

            return Team(
                team_id=str(raw_data.get("id", "")),
                name=raw_data.get("title", ""),
                
                xg_home=float(raw_data.get("xG", 0) or 0) / 2,
                xg_away=float(raw_data.get("xG", 0) or 0) / 2,
                xga_home=float(raw_data.get("xGA", 0) or 0) / 2,
                xga_away=float(raw_data.get("xGA", 0) or 0) / 2,
                
                played=raw_data.get("games", 0),
                won=raw_data.get("wins", 0),
                drawn=raw_data.get("draws", 0),
                lost=raw_data.get("loses", 0),
                goals_for=raw_data.get("scored", 0),
                goals_against=raw_data.get("missed", 0),
                points=raw_data.get("pts", 0),
                position=raw_data.get("position", 0),
                
                ppda=round(ppda, 2),
            )
        except Exception as e:
            logger.error(f"Error parsing understat data: {e}")
            return None

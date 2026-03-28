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
                "season_id": "赛季 ID",
            },
            update_freq=3600.0,
            historical=True,
            realtime=False,
        )

    async def fetch(self, **params) -> Optional[Team]:
        team_id = params.get("team_id")
        
        if not team_id:
            logger.error("team_id is required")
            return None

        cache_key = self._cache_key(**params)
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        raw_data = await self._try_providers("get_team", team_id=team_id)
        if raw_data is None:
            return None

        team = self.parse(raw_data)
        if team:
            self._set_cache(cache_key, team)
        
        return team

    async def fetch_by_season(self, season_id: int) -> List[Team]:
        cache_key = self._cache_key(action="season", season_id=season_id)
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        teams = []
        for provider in self._providers:
            try:
                if not await provider.is_available():
                    continue

                if hasattr(provider, "get_league_teams"):
                    raw_data = await provider.get_league_teams(season_id)
                    if raw_data:
                        teams = self.parse_list(raw_data)
                        if teams:
                            break
            except Exception as e:
                logger.warning(f"Provider {provider.name} failed: {e}")
                continue

        self._set_cache(cache_key, teams)
        return teams

    def parse(self, raw_data: Dict[str, Any]) -> Optional[Team]:
        if not raw_data:
            return None

        data = raw_data.get("data", raw_data)
        if isinstance(data, list) and len(data) > 0:
            data = data[0]

        if not data:
            return None

        try:
            stats = data.get("stats", {})
            
            return Team(
                team_id=str(data.get("team_id") or data.get("id", "")),
                name=data.get("team_name") or data.get("name", ""),
                
                xg_home=stats.get("xg_for_avg_home"),
                xg_away=stats.get("xg_for_avg_away"),
                xga_home=stats.get("xg_against_avg_home"),
                xga_away=stats.get("xg_against_avg_away"),
                
                shots=stats.get("shotsTotal_overall"),
                shots_on_target=stats.get("shotsOnTargetTotal_overall"),
                
                ppg=stats.get("ppg_overall"),
                position=data.get("table_position") or data.get("league_position"),
                played=stats.get("seasonMatchesPlayed_overall") or data.get("played"),
                won=stats.get("seasonWinsNum_overall") or data.get("won"),
                drawn=stats.get("seasonDrawsNum_overall") or data.get("drawn"),
                lost=stats.get("seasonLossesNum_overall") or data.get("lost"),
                goals_for=stats.get("seasonGoals_overall") or data.get("goalsFor"),
                goals_against=stats.get("seasonConceded_overall") or data.get("goalsAgainst"),
                goal_difference=stats.get("seasonGoalDifference_overall") or data.get("goalDifference"),
                points=data.get("points"),
                
                recent_xg=stats.get("xg_for_avg_overall"),
                recent_xga=stats.get("xg_against_avg_overall"),
                
                possession=stats.get("possession_overall"),
                dangerous_attacks=stats.get("dangerous_attacks_avg_overall"),
                
                country=data.get("country"),
                founded=data.get("founded"),
                venue=data.get("stadium_name") or raw_data.get("stadium_name"),
            )
        except Exception as e:
            logger.error(f"Error parsing team data: {e}")
            return None

    def parse_list(self, raw_data: Dict[str, Any]) -> List[Team]:
        teams = []
        
        data_list = raw_data.get("data", [])
        if not isinstance(data_list, list):
            data_list = [data_list] if data_list else []

        for item in data_list:
            team = self.parse(item)
            if team:
                teams.append(team)

        return teams

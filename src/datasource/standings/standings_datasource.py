from typing import Optional, List, Dict, Any
from datasource.base import DataSource, DataCapability
from datasource.types import DataSourceType, StandingsEntry
from provider.base import BaseProvider
from utils.logger import logger


class StandingsDataSource(DataSource[List[StandingsEntry]]):
    def __init__(self, providers: List[BaseProvider] = None):
        super().__init__(providers)
        self._cache_ttl = 3600.0

    @property
    def data_type(self) -> DataSourceType:
        return DataSourceType.STANDINGS

    def capabilities(self) -> DataCapability:
        return DataCapability(
            type=DataSourceType.STANDINGS,
            name="积分榜数据",
            description="联赛积分榜、排名、积分等",
            providers=[p.name for p in self._providers],
            params={
                "competition": "联赛名称",
                "season": "赛季",
            },
            update_freq=3600.0,
            historical=True,
            realtime=False,
        )

    async def fetch(self, **params) -> Optional[List[StandingsEntry]]:
        competition = params.get("competition")
        if not competition:
            logger.error("competition is required")
            return None

        cache_key = self._cache_key(**params)
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        standings = []
        
        for provider in self._providers:
            try:
                if not await provider.is_available():
                    continue

                if hasattr(provider, "get_league_table"):
                    raw_data = await provider.get_league_table(
                        league_id=params.get("league_id", competition)
                    )
                elif hasattr(provider, "get_standings"):
                    raw_data = await provider.get_standings(competition)
                else:
                    continue

                if raw_data:
                    standings = self.parse(raw_data)
                    if standings:
                        break

            except Exception as e:
                logger.warning(f"Provider {provider.name} failed: {e}")
                continue

        if standings:
            self._set_cache(cache_key, standings)
        
        return standings

    def parse(self, raw_data: Dict[str, Any]) -> List[StandingsEntry]:
        standings = []
        
        data_list = raw_data.get("data", raw_data.get("standings", []))
        
        if isinstance(data_list, list) and data_list:
            first_item = data_list[0]
            if isinstance(first_item, dict) and "table" in first_item:
                data_list = first_item.get("table", [])
        
        for item in data_list:
            try:
                entry = StandingsEntry(
                    position=item.get("position", 0),
                    team_id=str(item.get("team_id") or item.get("team", {}).get("id", "")),
                    team_name=item.get("team_name") or item.get("team", {}).get("name", ""),
                    played=item.get("played") or item.get("playedGames", 0),
                    won=item.get("won", 0),
                    drawn=item.get("drawn") or item.get("draw", 0),
                    lost=item.get("lost", 0),
                    goals_for=item.get("goals_for") or item.get("goalsFor", 0),
                    goals_against=item.get("goals_against") or item.get("goalsAgainst", 0),
                    goal_difference=item.get("goal_difference") or item.get("goalDifference", 0),
                    points=item.get("points", 0),
                    ppg=item.get("ppg"),
                    form=item.get("form", []),
                )
                standings.append(entry)
            except Exception as e:
                logger.warning(f"Error parsing standings entry: {e}")
                continue

        return standings

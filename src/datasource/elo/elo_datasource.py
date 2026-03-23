from typing import Optional, List, Dict, Any
from datasource.base import DataSource, DataCapability
from datasource.types import DataSourceType, Elo
from provider.base import BaseProvider
from utils.logger import logger


class EloDataSource(DataSource[Elo]):
    def __init__(self, providers: List[BaseProvider] = None):
        super().__init__(providers)
        self._cache_ttl = 86400.0

    @property
    def data_type(self) -> DataSourceType:
        return DataSourceType.ELO

    def capabilities(self) -> DataCapability:
        return DataCapability(
            type=DataSourceType.ELO,
            name="Elo 评分数据",
            description="球队 Elo 评分、排名等",
            providers=[p.name for p in self._providers],
            params={
                "team_name": "球队名称",
                "date": "日期 (YYYY-MM-DD)",
            },
            update_freq=86400.0,
            historical=True,
            realtime=False,
        )

    async def fetch(self, **params) -> Optional[Elo]:
        team_name = params.get("team_name")
        if not team_name:
            logger.error("team_name is required")
            return None

        cache_key = self._cache_key(**params)
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        raw_data = await self._try_providers(
            "get_elo",
            team_name=team_name,
            date=params.get("date")
        )
        
        if raw_data is None:
            return None

        elo = self.parse(raw_data)
        if elo:
            self._set_cache(cache_key, elo)
        
        return elo

    def parse(self, raw_data: Dict[str, Any]) -> Optional[Elo]:
        if not raw_data:
            return None

        try:
            date_str = raw_data.get("date")
            date = None
            if date_str:
                try:
                    date = datetime.strptime(date_str, "%Y-%m-%d")
                except ValueError:
                    pass

            return Elo(
                team_name=raw_data.get("team", ""),
                elo=float(raw_data.get("elo", 0)),
                date=date,
                rank=raw_data.get("rank"),
                country=raw_data.get("country"),
                level=raw_data.get("level"),
            )
        except Exception as e:
            logger.error(f"Error parsing Elo data: {e}")
            return None

    async def get_elo_value(self, team_name: str) -> Optional[float]:
        elo = await self.fetch(team_name=team_name)
        return elo.elo if elo else None

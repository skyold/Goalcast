from typing import Optional, List, Dict, Any
from datetime import datetime
from datasource.base import DataSource, DataCapability
from datasource.types import DataSourceType, Odds
from provider.base import BaseProvider
from utils.logger import logger


class OddsDataSource(DataSource[Odds]):
    def __init__(self, providers: List[BaseProvider] = None):
        super().__init__(providers)
        self._cache_ttl = 60.0

    @property
    def data_type(self) -> DataSourceType:
        return DataSourceType.ODDS

    def capabilities(self) -> DataCapability:
        return DataCapability(
            type=DataSourceType.ODDS,
            name="赔率数据",
            description="比赛赔率、隐含概率等",
            providers=[p.name for p in self._providers],
            params={
                "competition": "联赛名称",
                "match_id": "比赛 ID",
                "regions": "地区 (eu, uk, us)",
                "markets": "市场类型 (h2h, totals)",
            },
            update_freq=60.0,
            historical=False,
            realtime=True,
        )

    async def fetch(self, **params) -> Optional[Odds]:
        competition = params.get("competition", "Premier League")
        
        cache_key = self._cache_key(**params)
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        raw_data = await self._try_providers(
            "get_odds",
            sport=competition,
            match_id=params.get("match_id"),
            regions=params.get("regions", "eu"),
            markets=params.get("markets", "h2h"),
        )
        
        if raw_data is None:
            return None

        odds = self.parse(raw_data)
        if odds:
            self._set_cache(cache_key, odds)
        
        return odds

    async def fetch_for_match(
        self,
        home_team: str,
        away_team: str,
        competition: str = "Premier League"
    ) -> Optional[Odds]:
        all_odds = await self.fetch(competition=competition)
        
        if all_odds and isinstance(all_odds, list):
            for odds_entry in all_odds:
                if isinstance(odds_entry, dict):
                    home = odds_entry.get("home_team", "").lower()
                    away = odds_entry.get("away_team", "").lower()
                    if home_team.lower() in home or away_team.lower() in away:
                        return self._parse_odds_entry(odds_entry)
        
        return None

    def parse(self, raw_data: Dict[str, Any]) -> Optional[Odds]:
        if not raw_data:
            return None

        data = raw_data.get("data", raw_data)
        
        if isinstance(data, list) and data:
            return self._parse_odds_entry(data[0])
        
        return self._parse_odds_entry(data)

    def _parse_odds_entry(self, data: Dict[str, Any]) -> Optional[Odds]:
        if not data:
            return None

        try:
            bookmakers = data.get("bookmakers", [])
            if not bookmakers:
                return None
            
            first_bookmaker = bookmakers[0]
            markets = first_bookmaker.get("markets", [])
            if not markets:
                return None
            
            h2h_market = markets[0]
            outcomes = h2h_market.get("outcomes", [])
            
            home_odds = None
            draw_odds = None
            away_odds = None
            
            for outcome in outcomes:
                name = outcome.get("name", "").lower()
                price = outcome.get("price", 0)
                
                if name in ["home", "1"]:
                    home_odds = price
                elif name in ["draw", "x", "tie"]:
                    draw_odds = price
                elif name in ["away", "2"]:
                    away_odds = price
            
            if home_odds and draw_odds and away_odds:
                odds = Odds(
                    home=home_odds,
                    draw=draw_odds,
                    away=away_odds,
                    bookmaker=first_bookmaker.get("key", ""),
                    timestamp=datetime.now(),
                )
                odds.calculate_implied_probabilities()
                return odds
            
            return None

        except Exception as e:
            logger.error(f"Error parsing odds data: {e}")
            return None

    def calculate_implied_probability(self, odds: float) -> float:
        if odds <= 0:
            return 0.0
        return 1.0 / odds

    def remove_vig(self, home_odds: float, draw_odds: float, away_odds: float) -> Dict[str, float]:
        total_implied = (
            self.calculate_implied_probability(home_odds)
            + self.calculate_implied_probability(draw_odds)
            + self.calculate_implied_probability(away_odds)
        )

        if total_implied <= 0:
            return {
                "home_prob": 1.0 / 3.0,
                "draw_prob": 1.0 / 3.0,
                "away_prob": 1.0 / 3.0,
            }

        return {
            "home_prob": self.calculate_implied_probability(home_odds) / total_implied,
            "draw_prob": self.calculate_implied_probability(draw_odds) / total_implied,
            "away_prob": self.calculate_implied_probability(away_odds) / total_implied,
        }

from typing import Dict, Any, Optional
import json
from pathlib import Path
from goalcast.provider.base import BaseProvider
from goalcast.utils.logger import logger
from goalcast.config.settings import settings, BASE_DIR


SPORT_KEYS_PATH = BASE_DIR / "config" / "odds_sport_keys.json"


def _load_sport_keys() -> Dict[str, str]:
    if SPORT_KEYS_PATH.exists():
        try:
            with open(SPORT_KEYS_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


_SPORT_KEYS_DATA = _load_sport_keys()


class OddsProvider(BaseProvider):
    BASE_URL = "https://api.the-odds-api.com"
    DEFAULT_TIMEOUT = 30.0

    def __init__(self, api_key: str = "", timeout: float = None):
        super().__init__(api_key or settings.ODDS_API_KEY, timeout)
        self._sport_keys = _SPORT_KEYS_DATA
        self.requests_remaining = None
        if not self.api_key:
            logger.warning("The Odds API key not configured")

    @property
    def name(self) -> str:
        return "odds_api"

    async def is_available(self) -> bool:
        return bool(self.api_key)

    def _get_sport_key(self, competition: str) -> str:
        return self._sport_keys.get(competition, "soccer_epl")

    async def get_odds(
        self,
        sport: str,
        match_id: Optional[str] = None,
        regions: str = "eu",
        markets: str = "h2h",
    ) -> Optional[Dict[str, Any]]:
        logger.debug(f"Provider {self.name}: get_odds({sport})")
        
        if not self.api_key:
            logger.error("The Odds API key is not set")
            return None

        sport_key = self._get_sport_key(sport)
        
        params = {
            "apiKey": self.api_key,
            "regions": regions,
            "markets": markets,
        }

        raw_data = await self._request(f"/v4/sports/{sport_key}/odds", params)
        
        if raw_data is not None:
            self.requests_remaining = self._client._headers.get("x-requests-remaining") if self._client else None
            self._check_usage()
        
        return raw_data

    def _check_usage(self):
        if self.requests_remaining is not None:
            try:
                remaining = int(self.requests_remaining)
                if remaining < 100:
                    logger.warning(f"Odds API usage low: {remaining} requests remaining")
            except ValueError:
                pass

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

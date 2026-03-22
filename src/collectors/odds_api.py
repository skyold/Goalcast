import httpx
import asyncio
import json
from typing import Optional, Dict, Any
from pathlib import Path

from src.utils.logger import logger
from src.utils.cache import cache_get, cache_set
from src.utils.rate_limiter import async_acquire
from config.settings import settings, BASE_DIR


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


class OddsAPIClient:
    BASE_URL = "https://api.the-odds-api.com"

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or settings.ODDS_API_KEY
        self.requests_remaining = None
        self._sport_keys = _SPORT_KEYS_DATA
        if not self.api_key:
            logger.warning("The Odds API key not configured")

    def _get_sport_key(self, competition: str) -> str:
        return self._sport_keys.get(competition, "soccer_epl")

    async def get_odds(
        self,
        sport: str,
        match_id: Optional[str] = None,
        regions: str = "eu",
        markets: str = "h2h",
    ) -> Optional[Dict[str, Any]]:
        if not self.api_key:
            logger.error("The Odds API key is not set")
            return None

        sport_key = self._get_sport_key(sport)
        cache_key = f"{sport_key}:{match_id or 'all'}:{regions}:{markets}"
        cached = cache_get("odds_api", cache_key)
        if cached is not None:
            logger.debug(f"Cache hit for odds {sport_key}")
            self.requests_remaining = cached.get("requests_remaining")
            return cached.get("data")

        await async_acquire("odds_api", 500.0 / 30.0 / 24.0)

        params = {
            "apiKey": self.api_key,
            "regions": regions,
            "markets": markets,
        }

        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(
                        f"{self.BASE_URL}/v4/sports/{sport_key}/odds",
                        params=params,
                    )

                    if response.status_code == 429:
                        wait_time = 2**attempt * 30
                        logger.warning(f"Odds API rate limited, waiting {wait_time}s")
                        await asyncio.sleep(wait_time)
                        continue

                    if response.status_code >= 500:
                        wait_time = 2**attempt
                        logger.warning(f"Odds API server error {response.status_code}")
                        await asyncio.sleep(wait_time)
                        continue

                    if response.status_code == 200:
                        self.requests_remaining = response.headers.get("x-requests-remaining")
                        data = response.json()

                        self._check_usage()

                        result = {
                            "data": data,
                            "requests_remaining": self.requests_remaining,
                        }
                        cache_set("odds_api", cache_key, result, 0.5)
                        return result

                    return None

            except httpx.HTTPError as e:
                logger.error(f"Odds API HTTP error: {e}")
                if attempt == 2:
                    return None
                await asyncio.sleep(2**attempt)

        return None

    def _check_usage(self):
        if self.requests_remaining is not None:
            try:
                remaining = int(self.requests_remaining)
                if remaining < 100:
                    logger.warning(
                        f"Odds API usage low: {remaining} requests remaining"
                    )
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

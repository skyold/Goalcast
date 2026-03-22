import httpx
import asyncio
import json
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from src.utils.logger import logger
from src.utils.cache import cache_get, cache_set
from src.utils.rate_limiter import async_acquire
from config.settings import settings, BASE_DIR


STADIUMS_PATH = BASE_DIR / "config" / "stadiums.json"


def _load_stadiums() -> Dict[str, Dict[str, Dict[str, float]]]:
    if STADIUMS_PATH.exists():
        try:
            with open(STADIUMS_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


_STADIUMS_DATA = _load_stadiums()


class WeatherClient:
    BASE_URL = "https://api.openweathermap.org/data/2.5"

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or settings.OPENWEATHER_API_KEY
        self._stadiums = self._build_stadium_map()
        if not self.api_key:
            logger.warning("OpenWeatherMap API key not configured")

    def _build_stadium_map(self) -> Dict[str, Dict[str, float]]:
        result = {}
        for league, teams in _STADIUMS_DATA.items():
            for team_name, coords in teams.items():
                result[team_name] = {
                    "lat": coords.get("lat", 0),
                    "lon": coords.get("lon", 0),
                }
        return result

    async def get_match_weather(
        self, lat: float, lon: float, match_datetime: datetime
    ) -> Optional[Dict[str, Any]]:
        if not self.api_key:
            return self._default_weather()

        cache_key = f"{lat:.4f}:{lon:.4f}:{match_datetime.strftime('%Y%m%d%H')}"
        cached = cache_get("weather", cache_key)
        if cached is not None:
            logger.debug(f"Cache hit for weather ({lat}, {lon})")
            return cached

        await async_acquire("openweather", 60.0 / 60.0)

        params = {
            "lat": lat,
            "lon": lon,
            "appid": self.api_key,
            "units": "metric",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/weather", params=params
                )

                if response.status_code == 401:
                    logger.error("Invalid OpenWeatherMap API key")
                    return self._default_weather()

                if response.status_code != 200:
                    logger.error(f"Weather API error: {response.status_code}")
                    return self._default_weather()

                data = response.json()
                weather = self._parse_weather_data(data)
                cache_set("weather", cache_key, weather, 3.0)
                return weather

        except httpx.HTTPError as e:
            logger.error(f"Weather API HTTP error: {e}")
            return self._default_weather()

    def _parse_weather_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        wind_speed = data.get("wind", {}).get("speed", 0)
        rain_1h = data.get("rain", {}).get("1h", 0)
        weather_main = data.get("weather", [{}])[0].get("main", "Clear")

        xg_adjustment = 0.0
        if wind_speed > 8:
            xg_adjustment -= 0.10
        if rain_1h > 5:
            xg_adjustment -= 0.10
        if weather_main in ["Snow", "Fog", "Mist"]:
            xg_adjustment -= 0.10

        return {
            "wind_speed": wind_speed,
            "rain_1h": rain_1h,
            "condition": weather_main,
            "xg_adjustment": xg_adjustment,
        }

    def _default_weather(self) -> Dict[str, Any]:
        return {
            "wind_speed": 0,
            "rain_1h": 0,
            "condition": "Unknown",
            "xg_adjustment": 0.0,
        }

    def get_stadium_coordinates(self, team_name: str) -> Optional[Dict[str, float]]:
        return self._stadiums.get(team_name)

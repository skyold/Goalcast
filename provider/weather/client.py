from typing import Dict, Any, Optional
import json
from pathlib import Path
from datetime import datetime
from goalcast.provider.base import BaseProvider
from goalcast.utils.logger import logger
from goalcast.config.settings import settings, BASE_DIR




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


class WeatherProvider(BaseProvider):
    BASE_URL = "https://api.openweathermap.org/data/2.5"
    DEFAULT_TIMEOUT = 30.0

    def __init__(self, api_key: str = "", timeout: float = None):
        super().__init__(api_key or settings.OPENWEATHER_API_KEY, timeout)
        self._stadiums = self._build_stadium_map()
        if not self.api_key:
            logger.warning("OpenWeatherMap API key not configured")

    @property
    def name(self) -> str:
        return "weather"

    async def is_available(self) -> bool:
        return bool(self.api_key)

    def _build_stadium_map(self) -> Dict[str, Dict[str, float]]:
        result = {}
        for league, teams in _STADIUMS_DATA.items():
            for team_name, coords in teams.items():
                result[team_name] = {
                    "lat": coords.get("lat", 0),
                    "lon": coords.get("lon", 0),
                }
        return result

    async def get_weather(
        self,
        lat: float,
        lon: float
    ) -> Optional[Dict[str, Any]]:
        logger.debug(f"Provider {self.name}: get_weather({lat}, {lon})")
        
        if not self.api_key:
            return self._default_weather()

        params = {
            "lat": lat,
            "lon": lon,
            "appid": self.api_key,
            "units": "metric",
        }

        raw_data = await self._request("/weather", params)
        
        if raw_data is None:
            return self._default_weather()
        
        return raw_data

    def _default_weather(self) -> Dict[str, Any]:
        return {
            "wind": {"speed": 0},
            "rain": {},
            "weather": [{"main": "Unknown"}],
            "main": {"temp": 15, "humidity": 50},
        }

    def get_stadium_coordinates(self, team_name: str) -> Optional[Dict[str, float]]:
        return self._stadiums.get(team_name)

    def parse_weather_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        wind_speed = data.get("wind", {}).get("speed", 0)
        rain_1h = data.get("rain", {}).get("1h", 0)
        weather_main = data.get("weather", [{}])[0].get("main", "Clear")
        temp = data.get("main", {}).get("temp")
        humidity = data.get("main", {}).get("humidity")

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
            "temperature": temp,
            "humidity": humidity,
            "xg_adjustment": xg_adjustment,
        }

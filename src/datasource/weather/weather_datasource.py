from typing import Optional, List, Dict, Any
from datetime import datetime
from datasource.base import DataSource, DataCapability
from datasource.types import DataSourceType, Weather
from provider.base import BaseProvider
from utils.logger import logger


class WeatherDataSource(DataSource[Weather]):
    def __init__(self, providers: List[BaseProvider] = None):
        super().__init__(providers)
        self._cache_ttl = 10800.0

    @property
    def data_type(self) -> DataSourceType:
        return DataSourceType.WEATHER

    def capabilities(self) -> DataCapability:
        return DataCapability(
            type=DataSourceType.WEATHER,
            name="天气数据",
            description="比赛场地天气、风速、降水等",
            providers=[p.name for p in self._providers],
            params={
                "lat": "纬度",
                "lon": "经度",
                "team_name": "球队名称（获取球场坐标）",
            },
            update_freq=10800.0,
            historical=False,
            realtime=True,
        )

    async def fetch(self, **params) -> Optional[Weather]:
        lat = params.get("lat")
        lon = params.get("lon")
        team_name = params.get("team_name")

        if lat is None or lon is None:
            if team_name:
                coords = await self._get_stadium_coordinates(team_name)
                if coords:
                    lat = coords.get("lat")
                    lon = coords.get("lon")
            
            if lat is None or lon is None:
                logger.error("lat/lon or team_name is required")
                return None

        cache_key = self._cache_key(lat=lat, lon=lon)
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        raw_data = await self._try_providers("get_weather", lat=lat, lon=lon)
        
        if raw_data is None:
            return self._default_weather()

        weather = self.parse(raw_data)
        if weather:
            self._set_cache(cache_key, weather)
        
        return weather

    async def _get_stadium_coordinates(self, team_name: str) -> Optional[Dict[str, float]]:
        for provider in self._providers:
            if hasattr(provider, "get_stadium_coordinates"):
                coords = provider.get_stadium_coordinates(team_name)
                if coords:
                    return coords
        return None

    def parse(self, raw_data: Dict[str, Any]) -> Optional[Weather]:
        if not raw_data:
            return self._default_weather()

        try:
            wind = raw_data.get("wind", {})
            rain = raw_data.get("rain", {})
            weather_list = raw_data.get("weather", [{}])
            main = raw_data.get("main", {})

            wind_speed = wind.get("speed", 0)
            rain_1h = rain.get("1h", 0)
            condition = weather_list[0].get("main", "Unknown") if weather_list else "Unknown"
            temperature = main.get("temp")
            humidity = main.get("humidity")

            weather = Weather(
                condition=condition,
                wind_speed=float(wind_speed),
                rain_1h=float(rain_1h),
                temperature=float(temperature) if temperature is not None else None,
                humidity=int(humidity) if humidity is not None else None,
            )
            weather.calculate_xg_adjustment()
            
            return weather

        except Exception as e:
            logger.error(f"Error parsing weather data: {e}")
            return self._default_weather()

    def _default_weather(self) -> Weather:
        return Weather(
            condition="Unknown",
            wind_speed=0.0,
            rain_1h=0.0,
            temperature=None,
            humidity=None,
            xg_adjustment=0.0,
        )

    async def get_xg_adjustment(self, team_name: str) -> float:
        weather = await self.fetch(team_name=team_name)
        return weather.xg_adjustment if weather else 0.0

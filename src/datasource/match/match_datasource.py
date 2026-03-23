from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from datasource.base import DataSource, DataCapability
from datasource.types import DataSourceType, Match, MatchType, MatchStatus
from provider.base import BaseProvider
from utils.logger import logger


class MatchDataSource(DataSource[Match]):
    def __init__(self, providers: List[BaseProvider] = None):
        super().__init__(providers)
        self._cache_ttl = 30.0

    @property
    def data_type(self) -> DataSourceType:
        return DataSourceType.MATCH

    def capabilities(self) -> DataCapability:
        return DataCapability(
            type=DataSourceType.MATCH,
            name="比赛数据",
            description="比赛信息、比分、状态、赔率等",
            providers=[p.name for p in self._providers],
            params={
                "match_id": "比赛 ID",
                "competition": "联赛名称",
                "date_from": "开始日期 (YYYY-MM-DD)",
                "date_to": "结束日期 (YYYY-MM-DD)",
                "days": "未来天数",
            },
            update_freq=10.0,
            historical=True,
            realtime=True,
        )

    async def fetch(self, **params) -> Optional[Match]:
        match_id = params.get("match_id")
        if not match_id:
            logger.error("match_id is required")
            return None

        cache_key = self._cache_key(**params)
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        raw_data = await self._try_providers("get_match", match_id=match_id)
        if raw_data is None:
            return None

        match = self.parse(raw_data)
        if match:
            self._set_cache(cache_key, match)
        
        return match

    async def fetch_upcoming(
        self,
        competition: str,
        days: int = 7
    ) -> List[Match]:
        cache_key = self._cache_key(action="upcoming", competition=competition, days=days)
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        today = datetime.now()
        date_from = today.strftime("%Y-%m-%d")
        date_to = (today + timedelta(days=days)).strftime("%Y-%m-%d")

        matches = []
        
        for provider in self._providers:
            try:
                if not await provider.is_available():
                    continue

                if hasattr(provider, "get_matches"):
                    raw_data = await provider.get_matches(competition, date_from, date_to)
                elif hasattr(provider, "get_league_matches"):
                    raw_data = await provider.get_league_matches(competition)
                else:
                    continue

                if raw_data:
                    parsed = self.parse_list(raw_data, competition)
                    matches.extend(parsed)
                    break

            except Exception as e:
                logger.warning(f"Provider {provider.name} failed: {e}")
                continue

        unique_matches = {m.match_id: m for m in matches}
        result = list(unique_matches.values())
        result.sort(key=lambda m: m.kickoff_time or datetime.max)
        
        self._set_cache(cache_key, result)
        return result

    def parse(self, raw_data: Dict[str, Any]) -> Optional[Match]:
        if not raw_data:
            return None

        data = raw_data.get("data", raw_data)
        
        try:
            kickoff_time = None
            if data.get("start_date"):
                date_str = data.get("start_date")
                time_str = data.get("start_time", "")
                if time_str:
                    kickoff_time = datetime.fromisoformat(f"{date_str}T{time_str}")
                else:
                    kickoff_time = datetime.fromisoformat(date_str)
            elif data.get("utcDate"):
                kickoff_time = datetime.fromisoformat(data["utcDate"].replace("Z", "+00:00"))

            status_str = str(data.get("status", "SCHEDULED")).upper()
            try:
                status = MatchStatus[status_str]
            except KeyError:
                status = MatchStatus.SCHEDULED

            return Match(
                match_id=str(data.get("match_id") or data.get("id") or data.get("matchId", "")),
                home_team=data.get("home_name") or data.get("homeName") or data.get("homeTeam", {}).get("name", ""),
                away_team=data.get("away_name") or data.get("awayName") or data.get("awayTeam", {}).get("name", ""),
                home_team_id=str(data.get("home_id") or data.get("homeID") or data.get("homeTeam", {}).get("id", "")),
                away_team_id=str(data.get("away_id") or data.get("awayID") or data.get("awayTeam", {}).get("id", "")),
                competition=data.get("competition") or data.get("competition", {}).get("name", ""),
                status=status,
                kickoff_time=kickoff_time,
                home_score=data.get("home_score"),
                away_score=data.get("away_score"),
                odds_home=data.get("odds_home"),
                odds_draw=data.get("odds_draw"),
                odds_away=data.get("odds_away"),
            )
        except Exception as e:
            logger.error(f"Error parsing match data: {e}")
            return None

    def parse_list(self, raw_data: Dict[str, Any], competition: str = "") -> List[Match]:
        matches = []
        
        data_list = raw_data.get("data", raw_data.get("matches", []))
        if not isinstance(data_list, list):
            data_list = [data_list] if data_list else []

        for item in data_list:
            match = self.parse(item)
            if match:
                if not match.competition:
                    match.competition = competition
                matches.append(match)

        return matches

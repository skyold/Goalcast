from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from datasource.base import DataSource, DataCapability
from datasource.types import DataSourceType, Match, MatchType, MatchStatus, Odds
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

        raw_data = await self._try_providers("get_match_details", match_id=match_id)
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
        errors = []
        
        for provider in self._providers:
            try:
                if not await provider.is_available():
                    logger.debug(f"Provider {provider.name} not available, skipping")
                    continue

                raw_data = None
                method_used = None
                
                if hasattr(provider, "get_todays_matches"):
                    raw_data = await provider.get_todays_matches(date=date_from)
                    method_used = "get_todays_matches"
                elif hasattr(provider, "get_league_matches"):
                    raw_data = await provider.get_league_matches(competition)
                    method_used = "get_league_matches"
                else:
                    logger.debug(f"Provider {provider.name} has no suitable method")
                    continue

                if raw_data:
                    parsed = self.parse_list(raw_data, competition)
                    if parsed:
                        matches.extend(parsed)
                        logger.info(f"Provider {provider.name} ({method_used}) returned {len(parsed)} matches for {competition}")
                        break
                    else:
                        logger.debug(f"Provider {provider.name} returned empty data")
                        
                if method_used == "get_todays_matches" and len(matches) == 0:
                    logger.info(f"Provider {provider.name} returned empty matches, trying extended date range...")
                    extended_from = (today - timedelta(days=7)).strftime("%Y-%m-%d")
                    extended_to = (today + timedelta(days=days + 7)).strftime("%Y-%m-%d")
                    raw_data = await provider.get_todays_matches(date=extended_from)
                    if raw_data:
                        parsed = self.parse_list(raw_data, competition)
                        if parsed:
                            matches.extend(parsed)
                            logger.info(f"Provider {provider.name} (extended range) returned {len(parsed)} matches for {competition}")
                            break
                else:
                    logger.debug(f"Provider {provider.name} returned None")
                    errors.append(f"{provider.name}: no data")

            except Exception as e:
                errors.append(f"{provider.name}: {e}")
                logger.warning(f"Provider {provider.name} failed for {competition}: {e}")
                continue

        if not matches:
            if errors:
                logger.warning(f"All providers failed for {competition}: {'; '.join(errors)}")
            else:
                logger.info(f"No matches found for {competition} in next {days} days")

        unique_matches = {m.match_id: m for m in matches}
        result = list(unique_matches.values())
        result.sort(key=lambda m: m.kickoff_time or datetime.max)
        
        self._set_cache(cache_key, result)
        return result

    def parse(self, raw_data: Dict[str, Any]) -> Optional[Match]:
        if not raw_data:
            return None

        data = raw_data.get("data", raw_data)
        if isinstance(data, list) and len(data) > 0:
            data = data[0]
        
        if not data:
            return None

        try:
            kickoff_time = None
            if data.get("date_unix"):
                kickoff_time = datetime.fromtimestamp(data["date_unix"])
            
            status_str = str(data.get("status", "SCHEDULED")).upper()
            if status_str in ["COMPLETE", "FINISHED"]:
                status_str = "FINISHED"
            elif status_str in ["INCOMPLETE", "IN_PLAY", "LIVE"]:
                status_str = "LIVE"
            try:
                status = MatchStatus[status_str]
            except KeyError:
                status = MatchStatus.SCHEDULED

            return Match(
                match_id=str(data.get("id", "")),
                home_team=data.get("home_name", ""),
                away_team=data.get("away_name", ""),
                home_team_id=str(data.get("homeID", "")) if data.get("homeID") else None,
                away_team_id=str(data.get("awayID", "")) if data.get("awayID") else None,
                competition=data.get("league_name", ""),
                status=status,
                kickoff_time=kickoff_time,
                home_score=data.get("homeGoalCount"),
                away_score=data.get("awayGoalCount"),
                venue=data.get("stadium_name"),
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


from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, date
from goalcast.datasource.base import DataSource, DataCapability
from goalcast.datasource.types import DataSourceType, Match, MatchType, MatchStatus, Odds, MatchStats
from goalcast.provider.base import BaseProvider
from goalcast.utils.logger import logger


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

            home_stats = MatchStats(
                possession=data.get("team_a_possession") if data.get("team_a_possession", -1) >= 0 else None,
                shots=data.get("team_a_shots") if data.get("team_a_shots", -1) >= 0 else None,
                shots_on_target=data.get("team_a_shotsOnTarget") if data.get("team_a_shotsOnTarget", -1) >= 0 else None,
                corners=data.get("team_a_corners") if data.get("team_a_corners", -1) >= 0 else None,
                fouls=data.get("team_a_fouls") if data.get("team_a_fouls", -1) >= 0 else None,
                yellow_cards=data.get("team_a_yellow_cards") if data.get("team_a_yellow_cards", -1) >= 0 else None,
                red_cards=data.get("team_a_red_cards") if data.get("team_a_red_cards", -1) >= 0 else None,
                xg=data.get("team_a_xg") if data.get("team_a_xg", -1) >= 0 else None,
            )

            away_stats = MatchStats(
                possession=data.get("team_b_possession") if data.get("team_b_possession", -1) >= 0 else None,
                shots=data.get("team_b_shots") if data.get("team_b_shots", -1) >= 0 else None,
                shots_on_target=data.get("team_b_shotsOnTarget") if data.get("team_b_shotsOnTarget", -1) >= 0 else None,
                corners=data.get("team_b_corners") if data.get("team_b_corners", -1) >= 0 else None,
                fouls=data.get("team_b_fouls") if data.get("team_b_fouls", -1) >= 0 else None,
                yellow_cards=data.get("team_b_yellow_cards") if data.get("team_b_yellow_cards", -1) >= 0 else None,
                red_cards=data.get("team_b_red_cards") if data.get("team_b_red_cards", -1) >= 0 else None,
                xg=data.get("team_b_xg") if data.get("team_b_xg", -1) >= 0 else None,
            )

            return Match(
                match_id=str(data.get("id", "")),
                home_team=data.get("home_name", ""),
                away_team=data.get("away_name", ""),
                home_team_id=str(data.get("homeID", "")) if data.get("homeID") else None,
                away_team_id=str(data.get("awayID", "")) if data.get("awayID") else None,
                competition=data.get("league_name") or f"League_{data.get('competition_id', 'Unknown')}",
                competition_id=data.get("competition_id"),
                season=data.get("season"),
                game_week=data.get("game_week"),
                status=status,
                kickoff_time=kickoff_time,
                home_score=data.get("homeGoalCount"),
                away_score=data.get("awayGoalCount"),
                venue=data.get("stadium_name"),
                home_stats=home_stats,
                away_stats=away_stats,
                home_xg_prematch=data.get("team_a_xg_prematch"),
                away_xg_prematch=data.get("team_b_xg_prematch"),
                total_xg_prematch=data.get("total_xg_prematch"),
                home_odds=data.get("odds_ft_1"),
                draw_odds=data.get("odds_ft_x"),
                away_odds=data.get("odds_ft_2"),
                over_25_odds=data.get("odds_ft_over25"),
                under_25_odds=data.get("odds_ft_under25"),
                btts_yes_odds=data.get("odds_btts_yes"),
                btts_no_odds=data.get("odds_btts_no"),
                btts_potential=data.get("btts_potential"),
                o25_potential=data.get("o25_potential"),
                o35_potential=data.get("o35_potential"),
                u25_potential=data.get("u25_potential"),
                corners_potential=data.get("corners_potential"),
                avg_potential=data.get("avg_potential"),
                home_ppg=data.get("home_ppg"),
                away_ppg=data.get("away_ppg"),
                pre_match_home_ppg=data.get("pre_match_home_ppg"),
                pre_match_away_ppg=data.get("pre_match_away_ppg"),
                raw_data=data,
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

    async def fetch_for_date(
        self,
        target_date: date,
        competition: str = ""
    ) -> List[Match]:
        """
        获取指定日期的所有比赛

        Args:
            target_date: 目标日期
            competition: 联赛名称（可选，用于过滤）

        Returns:
            比赛列表
        """
        date_str = target_date.strftime("%Y-%m-%d")
        cache_key = self._cache_key(action="date", date=date_str, competition=competition)
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        raw_data = await self._try_providers("get_todays_matches", date=date_str)
        if raw_data is None:
            return []

        matches = self.parse_list(raw_data, competition)
        
        self._set_cache(cache_key, matches)
        return matches

    async def fetch_in_date_range(
        self,
        start_date: date,
        end_date: date,
        competition: str = ""
    ) -> List[Dict[str, Any]]:
        """
        获取指定日期范围内所有比赛

        Args:
            start_date: 开始日期（包含）
            end_date: 结束日期（包含）
            competition: 联赛名称（可选，用于过滤）

        Returns:
            包含每日比赛数据的列表，格式：[{"date": "2026-03-26", "matches": [...]}]
        """
        all_matches = []
        current_date = start_date

        while current_date <= end_date:
            matches = await self.fetch_for_date(current_date, competition)
            if matches:
                all_matches.append({
                    "date": current_date.strftime("%Y-%m-%d"),
                    "matches": matches
                })
            current_date += timedelta(days=1)

        return all_matches

    async def fetch_next_n_days(
        self,
        days: int = 7,
        competition: str = ""
    ) -> List[Dict[str, Any]]:
        """
        获取未来N天内的所有比赛

        Args:
            days: 天数，默认7天
            competition: 联赛名称（可选，用于过滤）

        Returns:
            包含每日比赛数据的列表
        """
        today = date.today()
        end_date = today + timedelta(days=days - 1)
        return await self.fetch_in_date_range(today, end_date, competition)

    async def fetch_nearest_match_day(
        self,
        max_lookahead_days: int = 30,
        competition: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        获取最近有比赛的一天的所有比赛
        从今天开始向前查找，找到第一个有比赛的日期

        Args:
            max_lookahead_days: 最大向前查找天数，默认30天
            competition: 联赛名称（可选，用于过滤）

        Returns:
            包含日期和比赛列表的字典，如果没有找到则返回 None
            格式：{"date": "2026-03-26", "matches": [...]}
        """
        today = date.today()

        for day_offset in range(max_lookahead_days + 1):
            target_date = today + timedelta(days=day_offset)
            matches = await self.fetch_for_date(target_date, competition)

            if matches:
                return {
                    "date": target_date.strftime("%Y-%m-%d"),
                    "matches": matches
                }

        return None

    async def fetch_upcoming_summary(
        self,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        获取未来N天比赛的汇总信息

        Args:
            days: 天数

        Returns:
            汇总信息字典，包含：
            - period: 时间段描述
            - start_date: 开始日期
            - end_date: 结束日期
            - days_with_matches: 有比赛的天数
            - total_matches: 总比赛数
            - unique_leagues: 涉及联赛数
            - leagues: 联赛列表
            - daily_data: 每日详细数据
        """
        matches_data = await self.fetch_next_n_days(days)

        total_matches = sum(len(day_data["matches"]) for day_data in matches_data)

        leagues_set = set()
        for day_data in matches_data:
            for match in day_data["matches"]:
                if match.competition:
                    leagues_set.add(match.competition)

        return {
            "period": f"next {days} days",
            "start_date": date.today().strftime("%Y-%m-%d"),
            "end_date": (date.today() + timedelta(days=days - 1)).strftime("%Y-%m-%d"),
            "days_with_matches": len(matches_data),
            "total_matches": total_matches,
            "unique_leagues": len(leagues_set),
            "leagues": sorted(list(leagues_set)),
            "daily_data": matches_data
        }
    
    async def fetch_team_matches(
        self,
        team_name: str,
        start_date: date,
        end_date: date
    ) -> List[Match]:
        """
        获取指定球队在日期范围内的所有比赛
        
        Args:
            team_name: 球队名称（支持模糊匹配）
            start_date: 开始日期（包含）
            end_date: 结束日期（包含）
        
        Returns:
            比赛列表
        """
        logger.debug(f"Fetching matches for team '{team_name}' from {start_date} to {end_date}")
        
        # 1. 获取日期范围内的所有比赛
        date_range_data = await self.fetch_in_date_range(start_date, end_date)
        
        # 2. 过滤包含指定球队的比赛
        all_matches = []
        for day_data in date_range_data:
            for match in day_data["matches"]:
                if self._matches_team(match, team_name):
                    all_matches.append(match)
        
        # 3. 按开球时间排序
        all_matches.sort(key=lambda m: m.kickoff_time or datetime.max)
        
        logger.info(f"Found {len(all_matches)} matches for team '{team_name}'")
        return all_matches
    
    def _matches_team(self, match: Match, team_name: str) -> bool:
        """
        判断比赛是否包含指定球队（模糊匹配）
        
        Args:
            match: 比赛对象
            team_name: 球队名称
            
        Returns:
            True 如果比赛包含该球队，否则 False
        """
        team_name_lower = team_name.lower()
        
        # 检查主队或客队名称是否包含关键词
        return (
            team_name_lower in match.home_team.lower() or
            team_name_lower in match.away_team.lower()
        )


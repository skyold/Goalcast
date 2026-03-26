"""
FootyStats API Provider

实现 FootyStats API 的所有 16 个端点：
1. 联赛列表 (League List)
2. 国家列表 (Country List)
3. 每日比赛 (Today's Matches)
4. 联赛统计 (League Stats)
5. 联赛比赛 (League Matches)
6. 联赛球队 (League Teams)
7. 联赛球员 (League Players)
8. 联赛裁判 (League Referees)
9. 联赛积分榜 (League Tables)
10. 比赛详情 (Match Details)
11. 球队详情 (Team)
12. 球队近况统计 (Last 5/6/10 Team Stats)
13. 球员详情 (Player - Individual)
14. 裁判详情 (Referee - Individual)
15. BTTS 统计 (BTTS Stats)
16. Over 2.5 统计 (Over 2.5 Stats)
"""

from typing import Dict, Any, Optional, List, Union
from provider.base import BaseProvider
from utils.logger import logger
from config.settings import settings
import json


class FootyStatsProvider(BaseProvider):
    """FootyStats API 提供者"""
    
    BASE_URL = "https://api.football-data-api.com"
    DEFAULT_TIMEOUT = 30.0

    def __init__(self, api_key: str = "", timeout: float = None, debug: bool = False):
        """
        初始化 FootyStats Provider
        
        Args:
            api_key: API 密钥，如果不传则使用配置文件中的
            timeout: 请求超时时间（秒）
            debug: 是否打印调试信息
        """
        super().__init__(api_key or settings.FOOTYSTATS_API_KEY, timeout)
        self.debug = debug
        if not self.api_key:
            logger.warning("FootyStats API key not configured")

    @property
    def name(self) -> str:
        """返回提供者名称"""
        return "footystats"

    async def is_available(self) -> bool:
        """检查 API 是否可用"""
        return bool(self.api_key)

    async def _request_raw(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        发送原始请求到 FootyStats API
        
        Args:
            endpoint: API 端点路径
            params: 查询参数（不包含 key）
            
        Returns:
            API 响应数据，失败时返回 None
        """
        if not self.api_key:
            logger.error("FootyStats API key is not set")
            return None

        url = f"{self.BASE_URL}{endpoint}"
        if params:
            params = dict(params)
            params["key"] = self.api_key
        else:
            params = {"key": self.api_key}

        if self.debug:
            print(f"\n[DEBUG] API Request:")
            print(f"  URL: {url}")
            print(f"  Params: {json.dumps(params, indent=2, ensure_ascii=False)}")

        result = await self._request(endpoint, params)

        if self.debug:
            print(f"\n[DEBUG] API Response:")
            if result:
                print(f"  Success: {result.get('success')}")
                if result.get("success"):
                    data = result.get("data", [])
                    if isinstance(data, list):
                        print(f"  Data count: {len(data)}")
                        if data:
                            print(f"  First item (full):")
                            print(json.dumps(data[0], indent=2, ensure_ascii=False))
                    else:
                        print(f"  Data (full):")
                        print(json.dumps(data, indent=2, ensure_ascii=False))
                else:
                    print(f"  Error: {result.get('error', 'Unknown error')}")
                print(f"\n  Full response (first 2000 chars):")
                print(json.dumps(result, indent=2, ensure_ascii=False)[:2000])
            else:
                print(f"  Response: None")

        return result

    # ==================== 基础端点 ====================

    async def get_league_list(
        self,
        chosen_leagues_only: bool = False,
        country: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取联赛列表
        
        Args:
            chosen_leagues_only: 是否只返回用户选择的联赛
            country: 国家 ISO 编号，用于筛选特定国家的联赛
            
        Returns:
            联赛列表数据
        """
        logger.debug(f"Provider {self.name}: get_league_list(chosen_leagues_only={chosen_leagues_only}, country={country})")
        params = {}
        if chosen_leagues_only:
            params["chosen_leagues_only"] = "true"
        if country:
            params["country"] = country
        return await self._request_raw("/league-list", params)

    async def get_country_list(self) -> Optional[Dict[str, Any]]:
        """
        获取国家列表及其 ISO 编号
        
        Returns:
            国家列表数据
        """
        logger.debug(f"Provider {self.name}: get_country_list()")
        return await self._request_raw("/country-list", {})

    async def get_todays_matches(
        self,
        date: Optional[str] = None,
        timezone: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取每日比赛列表
        
        Args:
            date: 日期，格式 YYYY-MM-DD，默认当前日期
            timezone: 时区，例如 Europe/London，默认 Etc/UTC
            
        Returns:
            比赛列表数据
        """
        logger.debug(f"Provider {self.name}: get_todays_matches(date={date}, timezone={timezone})")
        params = {}
        if date:
            params["date"] = date
        if timezone:
            params["timezone"] = timezone
        return await self._request_raw("/todays-matches", params)

    # ==================== 联赛数据端点 ====================

    async def get_league_stats(
        self,
        season_id: int,
        max_time: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取联赛赛季统计数据和参与的球队信息
        
        Args:
            season_id: 联赛赛季 ID
            max_time: UNIX 时间戳，返回指定时间之前的统计数据
            
        Returns:
            联赛统计数据
        """
        logger.debug(f"Provider {self.name}: get_league_stats(season_id={season_id}, max_time={max_time})")
        params = {"season_id": season_id}
        if max_time:
            params["max_time"] = max_time
        return await self._request_raw("/league-season", params)

    async def get_league_matches(
        self,
        season_id: int,
        page: int = 1,
        max_per_page: int = 500,
        max_time: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取联赛的完整比赛赛程
        
        Args:
            season_id: 联赛赛季 ID
            page: 分页页码，默认 1
            max_per_page: 每页比赛数量，默认 500，最大 1000
            max_time: UNIX 时间戳
            
        Returns:
            比赛列表数据
        """
        logger.debug(f"Provider {self.name}: get_league_matches(season_id={season_id}, page={page})")
        params = {
            "season_id": season_id,
            "page": page,
            "max_per_page": min(max_per_page, 1000)
        }
        if max_time:
            params["max_time"] = max_time
        return await self._request_raw("/league-matches", params)

    async def get_league_teams(
        self,
        season_id: int,
        max_time: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取联赛中所有球队的详细统计数据
        
        Args:
            season_id: 联赛赛季 ID
            max_time: UNIX 时间戳
            
        Returns:
            球队列表数据
        """
        logger.debug(f"Provider {self.name}: get_league_teams(season_id={season_id})")
        params = {"season_id": season_id}
        if max_time:
            params["max_time"] = max_time
        return await self._request_raw("/league-teams", params)

    async def get_league_players(
        self,
        season_id: int,
        page: int = 1,
        include_stats: bool = False,
        max_time: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取参与联赛赛季的所有球员及其统计数据
        
        Args:
            season_id: 联赛赛季 ID
            page: 分页页码，默认 1
            include_stats: 是否包含详细统计数据
            max_time: UNIX 时间戳
            
        Returns:
            球员列表数据
        """
        logger.debug(f"Provider {self.name}: get_league_players(season_id={season_id}, page={page})")
        params: Dict[str, Any] = {
            "season_id": season_id,
            "page": page
        }
        if include_stats:
            params["include"] = "stats"
        if max_time:
            params["max_time"] = max_time
        return await self._request_raw("/league-players", params)

    async def get_league_referees(
        self,
        season_id: int,
        max_time: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取参与联赛赛季的所有裁判及其统计数据
        
        Args:
            season_id: 联赛赛季 ID
            max_time: UNIX 时间戳
            
        Returns:
            裁判列表数据
        """
        logger.debug(f"Provider {self.name}: get_league_referees(season_id={season_id})")
        params = {"season_id": season_id}
        if max_time:
            params["max_time"] = max_time
        return await self._request_raw("/league-referees", params)

    async def get_league_tables(
        self,
        season_id: int,
        max_time: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取联赛赛季的积分榜数据
        
        Args:
            season_id: 联赛赛季 ID
            max_time: UNIX 时间戳
            
        Returns:
            积分榜数据
        """
        logger.debug(f"Provider {self.name}: get_league_tables(season_id={season_id})")
        params = {"season_id": season_id}
        if max_time:
            params["max_time"] = max_time
        return await self._request_raw("/league-tables", params)

    # ==================== 详细数据端点 ====================

    async def get_match_details(
        self,
        match_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        获取单场比赛的详细统计数据、交锋记录和赔率比较
        
        Args:
            match_id: 比赛 ID
            
        Returns:
            比赛详情数据
        """
        logger.debug(f"Provider {self.name}: get_match_details(match_id={match_id})")
        return await self._request_raw("/match", {"match_id": match_id})

    async def get_team(
        self,
        team_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        获取单个球队的详细统计数据
        
        Args:
            team_id: 球队 ID
            
        Returns:
            球队详情数据
        """
        logger.debug(f"Provider {self.name}: get_team(team_id={team_id})")
        return await self._request_raw("/team", {"team_id": team_id})

    async def get_team_last_x_stats(
        self,
        team_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        获取球队最近 5/6/10 场比赛的详细统计数据
        
        Args:
            team_id: 球队 ID
            
        Returns:
            球队近况统计数据（包含最近 5 场、6 场、10 场）
        """
        logger.debug(f"Provider {self.name}: get_team_last_x_stats(team_id={team_id})")
        return await self._request_raw("/lastx", {"team_id": team_id})

    async def get_player_stats(
        self,
        player_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        获取单个球员的详细统计数据
        
        Args:
            player_id: 球员 ID
            
        Returns:
            球员详情数据
        """
        logger.debug(f"Provider {self.name}: get_player_stats(player_id={player_id})")
        return await self._request_raw("/player-stats", {"player_id": player_id})

    async def get_referee_stats(
        self,
        referee_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        获取单个裁判的详细统计数据
        
        Args:
            referee_id: 裁判 ID
            
        Returns:
            裁判详情数据
        """
        logger.debug(f"Provider {self.name}: get_referee_stats(referee_id={referee_id})")
        return await self._request_raw("/referee", {"referee_id": referee_id})

    # ==================== 统计数据端点 ====================

    async def get_btts_stats(self) -> Optional[Dict[str, Any]]:
        """
        获取双方进球（BTTS）相关的顶级球队、赛程和联赛数据
        
        Returns:
            BTTS 统计数据
        """
        logger.debug(f"Provider {self.name}: get_btts_stats()")
        return await self._request_raw("/stats-data-btts", {})

    async def get_over_2_5_stats(self) -> Optional[Dict[str, Any]]:
        """
        获取大球（Over 2.5）相关的顶级球队、赛程和联赛数据
        
        Returns:
            Over 2.5 统计数据
        """
        logger.debug(f"Provider {self.name}: get_over_2_5_stats()")
        return await self._request_raw("/stats-data-over25", {})

    # ==================== 辅助方法 ====================

    async def get_standings(
        self,
        competition: str,
        season_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取联赛积分榜（兼容性方法）
        
        Args:
            competition: 联赛名称或 ID
            season_id: 赛季 ID
            
        Returns:
            积分榜数据
        """
        logger.debug(f"Provider {self.name}: get_standings(competition={competition})")
        # 如果是联赛名称，尝试转换为 ID
        # 注意：实际使用时需要根据联赛名称查询对应的 season_id
        if season_id:
            return await self.get_league_tables(season_id)
        else:
            logger.warning("season_id is required for get_standings")
            return None

    async def get_matches(
        self,
        competition: str,
        season_id: int,
        page: int = 1
    ) -> Optional[Dict[str, Any]]:
        """
        获取联赛比赛（兼容性方法）
        
        Args:
            competition: 联赛名称或 ID
            season_id: 赛季 ID
            page: 分页页码
            
        Returns:
            比赛列表数据
        """
        logger.debug(f"Provider {self.name}: get_matches(competition={competition}, season_id={season_id})")
        return await self.get_league_matches(season_id, page)

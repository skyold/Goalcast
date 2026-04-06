"""
Sportmonks API v3 Football Provider

实现 Sportmonks API v3 的核心端点，支持丰富的数据包含 (Includes) 和过滤功能。
"""

from typing import Dict, Any, Optional, List
from provider.base import BaseProvider
from utils.logger import logger
from config.settings import settings
import json


class SportmonksProvider(BaseProvider):
    """Sportmonks API v3 提供者 - 完整实现"""
    
    BASE_URL = "https://api.sportmonks.com/v3/football"
    DEFAULT_TIMEOUT = 30.0

    def __init__(self, api_key: str = "", timeout: float = DEFAULT_TIMEOUT, debug: bool = False):
        """
        初始化 Sportmonks Provider
        
        Args:
            api_key: API 密钥，如果不传则使用配置文件中的 SPORTMONKS_API_KEY
            timeout: 请求超时时间（秒）
            debug: 是否打印调试信息
        """
        super().__init__(api_key or settings.SPORTMONKS_API_KEY, timeout)
        self.debug = debug
        if not self.api_key:
            logger.warning("Sportmonks API key not configured")

    @property
    def name(self) -> str:
        """返回提供者名称"""
        return "sportmonks"

    async def is_available(self) -> bool:
        """检查 API 是否可用"""
        return bool(self.api_key)

    async def _request_raw(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        发送原始请求到 Sportmonks API v3
        """
        if not self.api_key:
            logger.error("Sportmonks API key is not set")
            return None

        all_params = {"api_token": self.api_key}
        if params:
            all_params.update(params)

        if self.debug:
            print(f"\n[DEBUG] Sportmonks Request: {endpoint}")
            debug_params = dict(all_params)
            debug_params["api_token"] = "********"
            print(f"  Params: {json.dumps(debug_params, indent=2, ensure_ascii=False)}")

        result = await self._request(endpoint, all_params)

        if self.debug and result:
            print(f"[DEBUG] Sportmonks Response: Success")
        
        return result

    # ==================== 1. Livescores (实时数据) ====================

    async def get_livescores(self, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取当前正在进行的所有比赛实时数据"""
        params = {}
        if include:
            params["include"] = include
        return await self._request_raw("/livescores", params)

    async def get_livescores_inplay(self, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取当前正在进行的比赛实时数据 (优化版)"""
        params = {}
        if include:
            params["include"] = include
        return await self._request_raw("/livescores/inplay", params)

    async def get_livescores_latest(self, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取最近更新的实时比赛数据"""
        params = {}
        if include:
            params["include"] = include
        return await self._request_raw("/livescores/latest", params)

    # ==================== 2. Fixtures (赛程与比赛) ====================

    async def get_fixtures_by_date(self, date: str, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定日期的比赛 (YYYY-MM-DD)"""
        return await self._request_raw(f"/fixtures/date/{date}", {"include": include} if include else None)

    async def get_fixtures_between(self, start_date: str, end_date: str, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取日期范围内的比赛 (YYYY-MM-DD)"""
        return await self._request_raw(f"/fixtures/between/{start_date}/{end_date}", {"include": include} if include else None)

    async def get_fixture_by_id(self, fixture_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取单场比赛详情"""
        return await self._request_raw(f"/fixtures/{fixture_id}", {"include": include} if include else None)

    async def get_fixtures_by_ids(self, fixture_ids: List[int], include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """批量获取比赛详情"""
        ids_str = ",".join(map(str, fixture_ids))
        return await self._request_raw(f"/fixtures/multi/{ids_str}", {"include": include} if include else None)

    async def get_head_to_head(self, team1_id: int, team2_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """交锋记录 (H2H)"""
        return await self._request_raw(f"/fixtures/head-to-head/{team1_id}/{team2_id}", {"include": include} if include else None)

    async def get_fixtures_by_team(self, team_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定球队的所有比赛"""
        return await self._request_raw(f"/fixtures/teams/{team_id}", {"include": include} if include else None)

    async def get_fixtures_by_season(self, season_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定赛季的所有比赛"""
        return await self._request_raw(f"/fixtures/seasons/{season_id}", {"include": include} if include else None)

    # ==================== 3. Leagues & Seasons (联赛与赛季) ====================

    async def get_leagues(self, page: int = 1, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        params = {"page": page}
        if include: params["include"] = include
        return await self._request_raw("/leagues", params)

    async def get_league_by_id(self, league_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        return await self._request_raw(f"/leagues/{league_id}", {"include": include} if include else None)

    async def get_seasons(self, page: int = 1, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        params = {"page": page}
        if include: params["include"] = include
        return await self._request_raw("/seasons", params)

    async def get_season_by_id(self, season_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        return await self._request_raw(f"/seasons/{season_id}", {"include": include} if include else None)

    # ==================== 4. Standings (积分榜) ====================

    async def get_standings_by_season(self, season_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        return await self._request_raw(f"/standings/seasons/{season_id}", {"include": include} if include else None)

    async def get_standings_live_by_league(self, league_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取实时积分榜 (基于当前进行中的比赛)"""
        return await self._request_raw(f"/standings/live/leagues/{league_id}", {"include": include} if include else None)

    # ==================== 5. Teams & Players (球队与球员) ====================

    async def get_teams(self, page: int = 1, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        params = {"page": page}
        if include: params["include"] = include
        return await self._request_raw("/teams", params)

    async def get_team_by_id(self, team_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        return await self._request_raw(f"/teams/{team_id}", {"include": include} if include else None)

    async def get_teams_by_season(self, season_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取赛季内的所有球队"""
        return await self._request_raw(f"/teams/seasons/{season_id}", {"include": include} if include else None)

    async def get_players(self, page: int = 1, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        params = {"page": page}
        if include: params["include"] = include
        return await self._request_raw("/players", params)

    async def get_player_by_id(self, player_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        return await self._request_raw(f"/players/{player_id}", {"include": include} if include else None)

    async def get_squad_by_team_and_season(self, team_id: int, season_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取球队在特定赛季的阵容"""
        return await self._request_raw(f"/teams/{team_id}/squads/seasons/{season_id}", {"include": include} if include else None)

    # ==================== 6. Referees, Coaches & Venues (裁判、教练与场馆) ====================

    async def get_referees(self, page: int = 1, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        params = {"page": page}
        if include: params["include"] = include
        return await self._request_raw("/referees", params)

    async def get_referee_by_id(self, referee_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        return await self._request_raw(f"/referees/{referee_id}", {"include": include} if include else None)

    async def get_coaches(self, page: int = 1, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        params = {"page": page}
        if include: params["include"] = include
        return await self._request_raw("/coaches", params)

    async def get_coach_by_id(self, coach_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        return await self._request_raw(f"/coaches/{coach_id}", {"include": include} if include else None)

    async def get_venues(self, page: int = 1, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        params = {"page": page}
        if include: params["include"] = include
        return await self._request_raw("/venues", params)

    async def get_venue_by_id(self, venue_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        return await self._request_raw(f"/venues/{venue_id}", {"include": include} if include else None)

    # ==================== 7. Transfers (转会) ====================

    async def get_transfers(self, page: int = 1, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        params = {"page": page}
        if include: params["include"] = include
        return await self._request_raw("/transfers", params)

    async def get_transfers_between(self, start_date: str, end_date: str, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取日期范围内的转会 (YYYY-MM-DD)"""
        return await self._request_raw(f"/transfers/between/{start_date}/{end_date}", {"include": include} if include else None)

    async def get_transfers_by_team(self, team_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        return await self._request_raw(f"/transfers/teams/{team_id}", {"include": include} if include else None)

    # ==================== 8. Expected Data (xG) ====================

    async def get_expected_goals_by_fixture(self, fixture_id: int) -> Optional[Dict[str, Any]]:
        """获取特定比赛的深度 xG 数据"""
        return await self._request_raw(f"/expected/fixtures/{fixture_id}")

    async def get_expected_goals_by_season(self, season_id: int) -> Optional[Dict[str, Any]]:
        """获取整个赛季的 xG 数据统计"""
        return await self._request_raw(f"/expected/seasons/{season_id}")

    # ==================== 9. Odds (赔率数据) ====================

    async def get_prematch_odds_by_fixture(self, fixture_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取单场比赛的赛前赔率"""
        return await self._request_raw(f"/odds/pre-match/fixtures/{fixture_id}", {"include": include} if include else None)

    async def get_inplay_odds_by_fixture(self, fixture_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取单场比赛的滚球赔率"""
        return await self._request_raw(f"/odds/inplay/fixtures/{fixture_id}", {"include": include} if include else None)

    async def get_markets(self) -> Optional[Dict[str, Any]]:
        """获取所有可用的盘口/市场类型"""
        return await self._request_raw("/odds/markets")

    async def get_bookmakers(self) -> Optional[Dict[str, Any]]:
        """获取所有支持的博彩公司"""
        return await self._request_raw("/odds/bookmakers")

    # ==================== 10. Predictions (预测数据) ====================

    async def get_predictions_by_fixture(self, fixture_id: int) -> Optional[Dict[str, Any]]:
        """获取单场比赛的胜平负概率预测"""
        return await self._request_raw(f"/predictions/probabilities/fixtures/{fixture_id}")

    async def get_value_bets(self) -> Optional[Dict[str, Any]]:
        """获取当前具有价值的投注项 (Value Bets)"""
        return await self._request_raw("/predictions/value-bets")

    # ==================== 11. Other (其他辅助数据) ====================

    async def get_topscorers_by_season(self, season_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取赛季射手榜"""
        return await self._request_raw(f"/topscorers/seasons/{season_id}", {"include": include} if include else None)

    async def get_schedules_by_season(self, season_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取赛季赛程计划"""
        return await self._request_raw(f"/schedules/seasons/{season_id}", {"include": include} if include else None)

    async def get_schedules_by_team(self, team_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取球队赛程计划"""
        return await self._request_raw(f"/schedules/teams/{team_id}", {"include": include} if include else None)

    async def get_stages_by_season(self, season_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        return await self._request_raw(f"/stages/seasons/{season_id}", {"include": include} if include else None)

    async def get_rounds_by_season(self, season_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        return await self._request_raw(f"/rounds/seasons/{season_id}", {"include": include} if include else None)

    async def get_commentaries_by_fixture(self, fixture_id: int) -> Optional[Dict[str, Any]]:
        """获取比赛文字直播/评论"""
        return await self._request_raw(f"/commentaries/fixtures/{fixture_id}")

    async def get_tv_stations(self) -> Optional[Dict[str, Any]]:
        """获取所有电视频道信息"""
        return await self._request_raw("/tv-stations")

    async def get_states(self) -> Optional[Dict[str, Any]]:
        """获取比赛状态码表 (如: Finished, NS, TBD 等)"""
        return await self._request_raw("/states")

    async def get_types(self) -> Optional[Dict[str, Any]]:
        """获取数据类型码表 (如: Shots, Corners 等 ID 定义)"""
        return await self._request_raw("/types")

    async def get_news_by_season(self, season_id: int) -> Optional[Dict[str, Any]]:
        """获取赛季相关新闻"""
        return await self._request_raw(f"/news/seasons/{season_id}")

    async def get_trophies_by_player(self, player_id: int) -> Optional[Dict[str, Any]]:
        """获取球员获得的荣誉/奖杯"""
        return await self._request_raw(f"/trophies/players/{player_id}")

    # ==================== 兼容性方法 (适配 Goalcast 现有接口) ====================

    async def get_standings(self, competition: str, season_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """获取积分榜 (兼容性接口)"""
        if season_id:
            return await self.get_standings_by_season(season_id)
        return None

    async def get_matches(self, season_id: int, include: str = "league,participants") -> Optional[Dict[str, Any]]:
        """获取赛季所有比赛 (兼容性接口)"""
        return await self.get_fixtures_by_season(season_id, include)

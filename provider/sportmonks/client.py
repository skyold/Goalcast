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
    DEFAULT_TIMEOUT = 60.0

    def __init__(self, api_key: str = "", timeout: float = DEFAULT_TIMEOUT, debug: bool = False):
        """
        初始化 Sportmonks Provider
        
        Args:
            api_key: API 密钥，如果不传则使用配置文件中的 SPORTMONKS_API_KEY
            timeout: 请求超时时间（秒）
            debug: 是否打印调试信息
        """
        super().__init__(api_key=api_key or settings.SPORTMONKS_API_KEY, timeout=timeout)
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

    async def get_fixtures(self, page: int = 1, include: Optional[str] = None, filters: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取所有赛程 (分页)，支持联赛过滤"""
        params = {"page": page}
        if include: params["include"] = include
        if filters: params["filters"] = filters
        return await self._request_raw("/fixtures", params)

    async def get_fixtures_by_date(self, date: str, include: Optional[str] = None, filters: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定日期的比赛 (YYYY-MM-DD)"""
        params = {}
        if include: params["include"] = include
        if filters: params["filters"] = filters
        return await self._request_raw(f"/fixtures/date/{date}", params)

    async def get_fixtures_between(self, start_date: str, end_date: str, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取日期范围内的比赛 (YYYY-MM-DD)"""
        return await self._request_raw(f"/fixtures/between/{start_date}/{end_date}", {"include": include} if include else None)

    async def get_fixtures_between_for_team(self, start_date: str, end_date: str, team_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定球队在日期范围内的比赛 (YYYY-MM-DD)"""
        return await self._request_raw(f"/fixtures/between/{start_date}/{end_date}/{team_id}", {"include": include} if include else None)

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

    async def get_fixtures_by_search(self, name: str, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """通过名称搜索赛程"""
        return await self._request_raw(f"/fixtures/search/{name}", {"include": include} if include else None)

    async def get_upcoming_fixtures_by_market(self, market_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """通过盘口 ID 获取即将开始的比赛"""
        return await self._request_raw(f"/fixtures/upcoming/markets/{market_id}", {"include": include} if include else None)

    async def get_upcoming_fixtures_by_tv_station(self, tv_station_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """通过电视台 ID 获取即将开始的比赛"""
        return await self._request_raw(f"/fixtures/upcoming/tv-stations/{tv_station_id}", {"include": include} if include else None)

    async def get_past_fixtures_by_tv_station(self, tv_station_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """通过电视台 ID 获取过去的比赛"""
        return await self._request_raw(f"/fixtures/past/tv-stations/{tv_station_id}", {"include": include} if include else None)

    async def get_fixtures_latest(self, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取最近更新的比赛"""
        return await self._request_raw("/fixtures/latest", {"include": include} if include else None)

    # ==================== 3. States (比赛状态) ====================

    async def get_states(self, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取所有比赛状态 (如: Finished, NS, TBD 等)"""
        return await self._request_raw("/states", {"include": include} if include else None)

    async def get_state_by_id(self, state_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定 ID 的比赛状态"""
        return await self._request_raw(f"/states/{state_id}", {"include": include} if include else None)

    # ==================== 4. Types (数据类型) ====================

    async def get_types(self, page: int = 1, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取所有数据类型 (分页)"""
        params = {"page": page}
        if include: params["include"] = include
        return await self._request_raw("/types", params)

    async def get_type_by_id(self, type_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定 ID 的数据类型"""
        return await self._request_raw(f"/types/{type_id}", {"include": include} if include else None)

    async def get_types_by_entity(self, entity: str, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """通过实体获取数据类型 (如: fixtures, teams)"""
        return await self._request_raw(f"/types/entities/{entity}", {"include": include} if include else None)

    # ==================== 5. Leagues & Seasons (联赛与赛季) ====================

    async def get_leagues(self, page: int = 1, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取所有联赛 (分页)"""
        params = {"page": page}
        if include: params["include"] = include
        return await self._request_raw("/leagues", params)

    async def get_league_by_id(self, league_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定 ID 的联赛"""
        return await self._request_raw(f"/leagues/{league_id}", {"include": include} if include else None)

    async def get_leagues_live(self, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取当前正在进行的联赛"""
        return await self._request_raw("/leagues/live", {"include": include} if include else None)

    async def get_leagues_by_date(self, date: str, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取在特定日期有比赛的联赛 (YYYY-MM-DD)"""
        return await self._request_raw(f"/leagues/date/{date}", {"include": include} if include else None)

    async def get_leagues_by_country(self, country_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定国家的联赛"""
        return await self._request_raw(f"/leagues/countries/{country_id}", {"include": include} if include else None)

    async def get_leagues_by_search(self, name: str, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """通过名称搜索联赛"""
        return await self._request_raw(f"/leagues/search/{name}", {"include": include} if include else None)

    async def get_leagues_by_team(self, team_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定球队参加的所有联赛"""
        return await self._request_raw(f"/leagues/teams/{team_id}", {"include": include} if include else None)

    async def get_current_leagues_by_team(self, team_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定球队当前参加的联赛"""
        return await self._request_raw(f"/leagues/teams/{team_id}/current", {"include": include} if include else None)

    async def get_seasons(self, page: int = 1, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取所有赛季 (分页)"""
        params = {"page": page}
        if include: params["include"] = include
        return await self._request_raw("/seasons", params)

    async def get_season_by_id(self, season_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定 ID 的赛季"""
        return await self._request_raw(f"/seasons/{season_id}", {"include": include} if include else None)

    async def get_seasons_by_team(self, team_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定球队参加的所有赛季"""
        return await self._request_raw(f"/seasons/teams/{team_id}", {"include": include} if include else None)

    async def get_seasons_by_search(self, name: str, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """通过名称搜索赛季"""
        return await self._request_raw(f"/seasons/search/{name}", {"include": include} if include else None)

    # ==================== 6. Statistics (统计数据) ====================

    async def get_season_statistics_by_participant(self, season_id: int, participant_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定参与者在特定赛季的统计数据"""
        return await self._request_raw(f"/statistics/seasons/participants/{participant_id}", {"season_id": season_id, "include": include} if include else {"season_id": season_id})

    async def get_stage_statistics(self, stage_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定阶段的统计数据"""
        return await self._request_raw(f"/statistics/stages/{stage_id}", {"include": include} if include else None)

    async def get_round_statistics(self, round_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定轮次的统计数据"""
        return await self._request_raw(f"/statistics/rounds/{round_id}", {"include": include} if include else None)

    # ==================== 7. Schedules (赛程安排) ====================

    async def get_schedules_by_season(self, season_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定赛季的赛程安排"""
        return await self._request_raw(f"/schedules/seasons/{season_id}", {"include": include} if include else None)

    async def get_schedules_by_team(self, team_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定球队的赛程安排"""
        return await self._request_raw(f"/schedules/teams/{team_id}", {"include": include} if include else None)

    async def get_schedules_by_season_and_team(self, season_id: int, team_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定球队在特定赛季的赛程安排"""
        return await self._request_raw(f"/schedules/seasons/{season_id}/teams/{team_id}", {"include": include} if include else None)

    # ==================== 8. Stages & Rounds (阶段与轮次) ====================

    async def get_stages(self, page: int = 1, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取所有阶段 (分页)"""
        params = {"page": page}
        if include: params["include"] = include
        return await self._request_raw("/stages", params)

    async def get_stage_by_id(self, stage_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定 ID 的阶段"""
        return await self._request_raw(f"/stages/{stage_id}", {"include": include} if include else None)

    async def get_stages_by_season(self, season_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定赛季的所有阶段"""
        return await self._request_raw(f"/stages/seasons/{season_id}", {"include": include} if include else None)

    async def get_stages_by_search(self, name: str, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """通过名称搜索阶段"""
        return await self._request_raw(f"/stages/search/{name}", {"include": include} if include else None)

    async def get_rounds(self, page: int = 1, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取所有轮次 (分页)"""
        params = {"page": page}
        if include: params["include"] = include
        return await self._request_raw("/rounds", params)

    async def get_round_by_id(self, round_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定 ID 的轮次"""
        return await self._request_raw(f"/rounds/{round_id}", {"include": include} if include else None)

    async def get_rounds_by_season(self, season_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定赛季的所有轮次"""
        return await self._request_raw(f"/rounds/seasons/{season_id}", {"include": include} if include else None)

    async def get_rounds_by_search(self, name: str, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """通过名称搜索轮次"""
        return await self._request_raw(f"/rounds/search/{name}", {"include": include} if include else None)

    # ==================== 9. Standings (积分榜) ====================

    async def get_standings(self, page: int = 1, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取所有积分榜 (分页)"""
        params = {"page": page}
        if include: params["include"] = include
        return await self._request_raw("/standings", params)

    async def get_standings_by_season(self, season_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定赛季的积分榜"""
        return await self._request_raw(f"/standings/seasons/{season_id}", {"include": include} if include else None)

    async def get_standings_by_round(self, round_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定轮次的积分榜"""
        return await self._request_raw(f"/standings/rounds/{round_id}", {"include": include} if include else None)

    async def get_standing_corrections_by_season(self, season_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定赛季的积分榜修正"""
        return await self._request_raw(f"/standings/corrections/seasons/{season_id}", {"include": include} if include else None)

    async def get_standings_live_by_league(self, league_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取实时积分榜 (基于当前进行中的比赛)"""
        return await self._request_raw(f"/standings/live/leagues/{league_id}", {"include": include} if include else None)

    # ==================== 10. Topscorers (射手榜) ====================

    async def get_topscorers_by_season(self, season_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定赛季的射手榜"""
        return await self._request_raw(f"/topscorers/seasons/{season_id}", {"include": include} if include else None)

    async def get_topscorers_by_stage(self, stage_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定阶段的射手榜"""
        return await self._request_raw(f"/topscorers/stages/{stage_id}", {"include": include} if include else None)

    # ==================== 11. Teams (球队) ====================

    async def get_teams(self, page: int = 1, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取所有球队 (分页)"""
        params = {"page": page}
        if include: params["include"] = include
        return await self._request_raw("/teams", params)

    async def get_team_by_id(self, team_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定 ID 的球队"""
        return await self._request_raw(f"/teams/{team_id}", {"include": include} if include else None)

    async def get_teams_by_country(self, country_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定国家的球队"""
        return await self._request_raw(f"/teams/countries/{country_id}", {"include": include} if include else None)

    async def get_teams_by_season(self, season_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定赛季的所有球队"""
        return await self._request_raw(f"/teams/seasons/{season_id}", {"include": include} if include else None)

    async def get_teams_by_search(self, name: str, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """通过名称搜索球队"""
        return await self._request_raw(f"/teams/search/{name}", {"include": include} if include else None)

    # ==================== 12. Players (球员) ====================

    async def get_players(self, page: int = 1, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取所有球员 (分页)"""
        params = {"page": page}
        if include: params["include"] = include
        return await self._request_raw("/players", params)

    async def get_player_by_id(self, player_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定 ID 的球员"""
        return await self._request_raw(f"/players/{player_id}", {"include": include} if include else None)

    async def get_players_by_country(self, country_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定国家的球员"""
        return await self._request_raw(f"/players/countries/{country_id}", {"include": include} if include else None)

    async def get_players_by_search(self, name: str, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """通过名称搜索球员"""
        return await self._request_raw(f"/players/search/{name}", {"include": include} if include else None)

    async def get_players_latest(self, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取最近更新的球员"""
        return await self._request_raw("/players/latest", {"include": include} if include else None)

    # ==================== 13. Team Squads (球队阵容) ====================

    async def get_squad_by_team(self, team_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取球队的当前阵容"""
        return await self._request_raw(f"/teams/{team_id}/squads", {"include": include} if include else None)

    async def get_extended_squad_by_team(self, team_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取球队的扩展阵容"""
        return await self._request_raw(f"/teams/{team_id}/squads/extended", {"include": include} if include else None)

    async def get_squad_by_team_and_season(self, team_id: int, season_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取球队在特定赛季的阵容"""
        return await self._request_raw(f"/teams/{team_id}/squads/seasons/{season_id}", {"include": include} if include else None)

    # ==================== 14. Match Facts (比赛事实 - Beta) ====================

    async def get_match_facts(self, page: int = 1, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取所有可用的比赛事实"""
        params = {"page": page}
        if include: params["include"] = include
        return await self._request_raw("/match-facts", params)

    async def get_match_facts_by_fixture(self, fixture_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定比赛的比赛事实"""
        return await self._request_raw(f"/match-facts/fixtures/{fixture_id}", {"include": include} if include else None)

    async def get_match_facts_between(self, start_date: str, end_date: str, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取日期范围内的比赛事实"""
        return await self._request_raw(f"/match-facts/between/{start_date}/{end_date}", {"include": include} if include else None)

    async def get_match_facts_by_league(self, league_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定联赛的比赛事实"""
        return await self._request_raw(f"/match-facts/leagues/{league_id}", {"include": include} if include else None)

    # ==================== 15. Team Rankings (球队排名 - Beta) ====================

    async def get_team_rankings(self, page: int = 1, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取所有可用的球队排名"""
        params = {"page": page}
        if include: params["include"] = include
        return await self._request_raw("/team-rankings", params)

    async def get_team_rankings_by_team(self, team_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定球队的排名"""
        return await self._request_raw(f"/team-rankings/teams/{team_id}", {"include": include} if include else None)

    async def get_team_rankings_by_date(self, date: str, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定日期的球队排名 (YYYY-MM-DD)"""
        return await self._request_raw(f"/team-rankings/date/{date}", {"include": include} if include else None)

    # ==================== 16. Team of the Week (TOTW - Beta) ====================

    async def get_totws(self, page: int = 1, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取所有可用的周最佳阵容"""
        params = {"page": page}
        if include: params["include"] = include
        return await self._request_raw("/totws", params)

    async def get_totw_by_round(self, round_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定轮次的周最佳阵容"""
        return await self._request_raw(f"/totws/rounds/{round_id}", {"include": include} if include else None)

    async def get_latest_totw(self, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取最近的周最佳阵容"""
        return await self._request_raw("/totws/latest", {"include": include} if include else None)

    # ==================== 17. Coaches (教练) ====================

    async def get_coaches(self, page: int = 1, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取所有教练 (分页)"""
        params = {"page": page}
        if include: params["include"] = include
        return await self._request_raw("/coaches", params)

    async def get_coach_by_id(self, coach_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定 ID 的教练"""
        return await self._request_raw(f"/coaches/{coach_id}", {"include": include} if include else None)

    async def get_coaches_by_country(self, country_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定国家的教练"""
        return await self._request_raw(f"/coaches/countries/{country_id}", {"include": include} if include else None)

    async def get_coaches_by_search(self, name: str, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """通过名称搜索教练"""
        return await self._request_raw(f"/coaches/search/{name}", {"include": include} if include else None)

    async def get_coaches_latest(self, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取最近更新的教练"""
        return await self._request_raw("/coaches/latest", {"include": include} if include else None)

    # ==================== 18. Referees (裁判) ====================

    async def get_referees(self, page: int = 1, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取所有裁判 (分页)"""
        params = {"page": page}
        if include: params["include"] = include
        return await self._request_raw("/referees", params)

    async def get_referee_by_id(self, referee_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定 ID 的裁判"""
        return await self._request_raw(f"/referees/{referee_id}", {"include": include} if include else None)

    async def get_referees_by_country(self, country_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定国家的裁判"""
        return await self._request_raw(f"/referees/countries/{country_id}", {"include": include} if include else None)

    async def get_referees_by_season(self, season_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定赛季的所有裁判"""
        return await self._request_raw(f"/referees/seasons/{season_id}", {"include": include} if include else None)

    async def get_referees_by_search(self, name: str, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """通过名称搜索裁判"""
        return await self._request_raw(f"/referees/search/{name}", {"include": include} if include else None)

    # ==================== 19. Transfers & Rumours (转会与传闻) ====================

    async def get_transfers(self, page: int = 1, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取所有转会 (分页)"""
        params = {"page": page}
        if include: params["include"] = include
        return await self._request_raw("/transfers", params)

    async def get_transfer_by_id(self, transfer_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定 ID 的转会详情"""
        return await self._request_raw(f"/transfers/{transfer_id}", {"include": include} if include else None)

    async def get_transfers_latest(self, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取最近的转会记录"""
        return await self._request_raw("/transfers/latest", {"include": include} if include else None)

    async def get_transfers_between(self, start_date: str, end_date: str, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取日期范围内的转会 (YYYY-MM-DD)"""
        return await self._request_raw(f"/transfers/between/{start_date}/{end_date}", {"include": include} if include else None)

    async def get_transfers_by_team(self, team_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定球队的转会记录"""
        return await self._request_raw(f"/transfers/teams/{team_id}", {"include": include} if include else None)

    async def get_transfers_by_player(self, player_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定球员的转会记录"""
        return await self._request_raw(f"/transfers/players/{player_id}", {"include": include} if include else None)

    async def get_transfer_rumours(self, page: int = 1, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取所有转会传闻 (分页)"""
        params = {"page": page}
        if include: params["include"] = include
        return await self._request_raw("/transfer-rumours", params)

    async def get_transfer_rumour_by_id(self, rumour_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定 ID 的转会传闻"""
        return await self._request_raw(f"/transfer-rumours/{rumour_id}", {"include": include} if include else None)

    async def get_transfer_rumours_between(self, start_date: str, end_date: str, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取日期范围内的转会传闻 (YYYY-MM-DD)"""
        return await self._request_raw(f"/transfer-rumours/between/{start_date}/{end_date}", {"include": include} if include else None)

    async def get_transfer_rumours_by_team(self, team_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定球队的转会传闻"""
        return await self._request_raw(f"/transfer-rumours/teams/{team_id}", {"include": include} if include else None)

    async def get_transfer_rumours_by_player(self, player_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定球员的转会传闻"""
        return await self._request_raw(f"/transfer-rumours/players/{player_id}", {"include": include} if include else None)

    # ==================== 20. Venues (场馆) ====================

    async def get_venues(self, page: int = 1, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取所有场馆 (分页)"""
        params = {"page": page}
        if include: params["include"] = include
        return await self._request_raw("/venues", params)

    async def get_venue_by_id(self, venue_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定 ID 的场馆详情"""
        return await self._request_raw(f"/venues/{venue_id}", {"include": include} if include else None)

    async def get_venues_by_season(self, season_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定赛季的所有场馆"""
        return await self._request_raw(f"/venues/seasons/{season_id}", {"include": include} if include else None)

    async def get_venues_by_search(self, name: str, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """通过名称搜索场馆"""
        return await self._request_raw(f"/venues/search/{name}", {"include": include} if include else None)

    # ==================== 21. TV Stations (电视台) ====================

    async def get_tv_stations(self, page: int = 1, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取所有电视台 (分页)"""
        params = {"page": page}
        if include: params["include"] = include
        return await self._request_raw("/tv-stations", params)

    async def get_tv_station_by_id(self, tv_station_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定 ID 的电视台"""
        return await self._request_raw(f"/tv-stations/{tv_station_id}", {"include": include} if include else None)

    async def get_tv_stations_by_fixture(self, fixture_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取转播特定比赛的电视台"""
        return await self._request_raw(f"/tv-stations/fixtures/{fixture_id}", {"include": include} if include else None)

    # ==================== 22. Expected Data (xG) ====================

    async def get_expected_by_team(self, team_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定球队的 xG 数据"""
        return await self._request_raw("/expected/fixtures", {"participant_id": team_id, "include": include} if include else {"participant_id": team_id})

    async def get_expected_by_fixture(self, fixture_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定比赛的 xG 数据"""
        return await self._request_raw("/expected/fixtures", {"fixture_id": fixture_id, "include": include} if include else {"fixture_id": fixture_id})

    async def get_expected_by_player(self, player_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定球员的 xG 数据 (基于阵容)"""
        return await self._request_raw("/expected/lineups", {"player_id": player_id, "include": include} if include else {"player_id": player_id})

    async def get_all_expected_goals(self, page: int = 1, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取所有 xG 数据 (分页)"""
        params = {"page": page}
        if include: params["include"] = include
        return await self._request_raw("/expected/fixtures", params)

    # ==================== 23. Premium Expected Lineups (高级预期阵容) ====================

    async def get_expected_lineup_by_team(self, team_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定球队的预期阵容"""
        return await self._request_raw(f"/expected/lineups/teams/{team_id}", {"include": include} if include else None)

    async def get_expected_lineups_by_player(self, player_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定球员的预期阵容"""
        return await self._request_raw(f"/expected/lineups/players/{player_id}", {"include": include} if include else None)

    # ==================== 24. Predictions (预测数据) ====================

    async def get_probabilities(self, page: int = 1, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取所有概率预测 (分页)"""
        params = {"page": page}
        if include: params["include"] = include
        return await self._request_raw("/predictions/probabilities", params)

    async def get_predictability_by_league(self, league_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定联赛的预测准确度 (Predictability)"""
        return await self._request_raw(f"/predictions/probabilities/leagues/{league_id}", {"include": include} if include else None)

    async def get_probabilities_by_fixture(self, fixture_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定比赛的胜平负概率预测"""
        return await self._request_raw(f"/predictions/probabilities/fixtures/{fixture_id}", {"include": include} if include else None)

    async def get_value_bets(self, page: int = 1, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取当前具有价值的投注项 (Value Bets)"""
        params = {"page": page}
        if include: params["include"] = include
        return await self._request_raw("/predictions/value-bets", params)

    async def get_value_bets_by_fixture(self, fixture_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定比赛的价值投注项"""
        return await self._request_raw(f"/predictions/value-bets/fixtures/{fixture_id}", {"include": include} if include else None)

    # ==================== 25. Odds (赛前赔率) ====================

    async def get_prematch_odds(self, page: int = 1, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取所有赛前赔率 (分页)"""
        params = {"page": page}
        if include: params["include"] = include
        return await self._request_raw("/odds/pre-match", params)

    async def get_prematch_odds_by_fixture(self, fixture_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取单场比赛的赛前赔率"""
        return await self._request_raw(f"/odds/pre-match/fixtures/{fixture_id}", {"include": include} if include else None)

    async def get_prematch_odds_by_fixture_and_bookmaker(self, fixture_id: int, bookmaker_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定比赛和博彩公司的赛前赔率"""
        return await self._request_raw(f"/odds/pre-match/fixtures/{fixture_id}/bookmakers/{bookmaker_id}", {"include": include} if include else None)

    async def get_prematch_odds_by_fixture_and_market(self, fixture_id: int, market_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定比赛和盘口的赛前赔率"""
        return await self._request_raw(f"/odds/pre-match/fixtures/{fixture_id}/markets/{market_id}", {"include": include} if include else None)

    async def get_prematch_odds_latest(self, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取最近更新的赛前赔率"""
        return await self._request_raw("/odds/pre-match/latest", {"include": include} if include else None)

    # ==================== 26. Inplay Odds (滚球赔率) ====================

    async def get_inplay_odds(self, page: int = 1, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取所有滚球赔率 (分页)"""
        params = {"page": page}
        if include: params["include"] = include
        return await self._request_raw("/odds/inplay", params)

    async def get_inplay_odds_by_fixture(self, fixture_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取单场比赛的滚球赔率"""
        return await self._request_raw(f"/odds/inplay/fixtures/{fixture_id}", {"include": include} if include else None)

    async def get_inplay_odds_by_fixture_and_bookmaker(self, fixture_id: int, bookmaker_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定比赛和博彩公司的滚球赔率"""
        return await self._request_raw(f"/odds/inplay/fixtures/{fixture_id}/bookmakers/{bookmaker_id}", {"include": include} if include else None)

    async def get_inplay_odds_by_fixture_and_market(self, fixture_id: int, market_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定比赛和盘口的滚球赔率"""
        return await self._request_raw(f"/odds/inplay/fixtures/{fixture_id}/markets/{market_id}", {"include": include} if include else None)

    async def get_inplay_odds_latest(self, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取最近更新的滚球赔率"""
        return await self._request_raw("/odds/inplay/latest", {"include": include} if include else None)

    # ==================== 27. Premium Odds (高级/历史/初盘赔率) ====================

    async def get_premium_odds(self, page: int = 1, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取全量高级赔率（含历史记录）"""
        params = {"page": page}
        if include: params["include"] = include
        return await self._request_raw("/odds/premium", params)

    async def get_premium_odds_by_fixture(self, fixture_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定比赛的高级赔率变动历史 (包含初盘)"""
        return await self._request_raw(f"/odds/premium/fixtures/{fixture_id}", {"include": include} if include else None)

    async def get_premium_odds_updated_between(self, start_ts: int, end_ts: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定时间戳范围内产生变动的高级赔率"""
        params = {"include": include} if include else {}
        return await self._request_raw(f"/odds/premium/updated/between/{start_ts}/{end_ts}", params)

    # ==================== 28. Markets (盘口/市场) ====================

    async def get_markets(self, page: int = 1, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取所有盘口 (分页)"""
        params = {"page": page}
        if include: params["include"] = include
        return await self._request_raw("/markets", params)

    async def get_market_by_id(self, market_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定 ID 的盘口"""
        return await self._request_raw(f"/markets/{market_id}", {"include": include} if include else None)

    async def get_markets_by_search(self, name: str, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """通过名称搜索盘口"""
        return await self._request_raw(f"/markets/search/{name}", {"include": include} if include else None)

    # ==================== 28. Bookmakers (博彩公司) ====================

    async def get_bookmakers(self, page: int = 1, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取所有博彩公司 (分页)"""
        params = {"page": page}
        if include: params["include"] = include
        return await self._request_raw("/bookmakers", params)

    async def get_bookmaker_by_id(self, bookmaker_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定 ID 的博彩公司"""
        return await self._request_raw(f"/bookmakers/{bookmaker_id}", {"include": include} if include else None)

    async def get_bookmakers_by_search(self, name: str, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """通过名称搜索博彩公司"""
        return await self._request_raw(f"/bookmakers/search/{name}", {"include": include} if include else None)

    async def get_bookmakers_by_fixture(self, fixture_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定比赛的博彩公司"""
        return await self._request_raw(f"/bookmakers/fixtures/{fixture_id}", {"include": include} if include else None)

    async def get_bookmaker_match_mappings(self, fixture_id: int) -> Optional[Dict[str, Any]]:
        """获取博彩公司的比赛 ID映射"""
        return await self._request_raw(f"/bookmakers/mapping/fixtures/{fixture_id}")

    # ==================== 29. News (新闻) ====================

    async def get_prematch_news(self, page: int = 1, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取所有赛前新闻 (分页)"""
        params = {"page": page}
        if include: params["include"] = include
        return await self._request_raw("/news/pre-match", params)

    async def get_prematch_news_by_season(self, season_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定赛季的赛前新闻"""
        return await self._request_raw(f"/news/pre-match/seasons/{season_id}", {"include": include} if include else None)

    async def get_prematch_news_upcoming(self, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取即将开始比赛的赛前新闻"""
        return await self._request_raw("/news/pre-match/upcoming", {"include": include} if include else None)

    async def get_postmatch_news(self, page: int = 1, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取所有赛后新闻 (分页)"""
        params = {"page": page}
        if include: params["include"] = include
        return await self._request_raw("/news/post-match", params)

    async def get_postmatch_news_by_season(self, season_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定赛季的赛后新闻"""
        return await self._request_raw(f"/news/post-match/seasons/{season_id}", {"include": include} if include else None)

    # ==================== 30. Rivals (死敌/竞争对手) ====================

    async def get_rivals(self, page: int = 1, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取所有竞争对手关系 (分页)"""
        params = {"page": page}
        if include: params["include"] = include
        return await self._request_raw("/rivals", params)

    async def get_rivals_by_team(self, team_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定球队的竞争对手"""
        return await self._request_raw(f"/rivals/teams/{team_id}", {"include": include} if include else None)

    # ==================== 31. Commentaries (解说/评论) ====================

    async def get_commentaries(self, page: int = 1, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取所有解说 (分页)"""
        params = {"page": page}
        if include: params["include"] = include
        return await self._request_raw("/commentaries", params)

    async def get_commentaries_by_fixture(self, fixture_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取特定比赛的文字直播/评论"""
        return await self._request_raw(f"/commentaries/fixtures/{fixture_id}", {"include": include} if include else None)

    async def get_trophies_by_player(self, player_id: int, include: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取球员获得的荣誉/奖杯"""
        return await self._request_raw(f"/trophies/players/{player_id}", {"include": include} if include else None)

    # ==================== 兼容性方法 (适配 Goalcast 现有接口) ====================

    async def get_standings(self, competition: str, season_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """获取积分榜 (兼容性接口)"""
        if season_id:
            return await self.get_standings_by_season(season_id)
        return None

    async def get_matches(self, season_id: int, include: str = "league,participants") -> Optional[Dict[str, Any]]:
        """获取赛季所有比赛 (兼容性接口)"""
        return await self.get_fixtures_by_season(season_id, include)

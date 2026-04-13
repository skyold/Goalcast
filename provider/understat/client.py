"""
Understat API Provider

提供 Understat.com 的高级足球统计数据，包括：
- xG (Expected Goals) - 期望进球
- xGA (Expected Goals Against) - 期望失球
- xGD (Expected Goals Difference) - 期望进球差
- NPxG (Non-Penalty xG) - 非点球期望进球
- 射门地图
- 球员详细统计
- 球队详细统计

Understat 是一个免费的足球数据网站，提供基于 xG 模型的高级统计。

支持的联赛：
- EPL (英格兰超级联赛)
- La Liga (西班牙甲级联赛)
- Bundesliga (德国甲级联赛)
- Serie A (意大利甲级联赛)
- Ligue 1 (法国甲级联赛)
- RFPL (俄罗斯超级联赛)

数据来源：https://understat.com

依赖：
- understatapi: 推荐使用成熟的 understatapi 库获取完整功能
- aiohttp: 用于直接 HTTP 请求（部分功能）
"""

import asyncio
import aiohttp
import json
from typing import Dict, Any, Optional, List
from provider.base import BaseProvider
from utils.logger import logger
import datetime

# 尝试导入 understatapi 库
try:
    from understatapi import UnderstatClient
    UNDERSTAT_API_AVAILABLE = True
except ImportError:
    UnderstatClient = None
    UNDERSTAT_API_AVAILABLE = False
    logger.warning("understatapi library not installed. Run: pip install understatapi")


class UnderstatProvider(BaseProvider):
    """Understat API 提供者
    
    提供两种方式使用 Understat 数据：
    1. 使用 understatapi 库（推荐，功能完整）
    2. 直接 HTTP 请求（部分功能可用）
    """
    
    BASE_URL = "https://understat.com"
    DEFAULT_TIMEOUT = 30.0
    
    # 可用的联赛代码
    LEAGUES = {
        "EPL": "EPL",
        "LALIGA": "La_liga",
        "BUNDESLIGA": "Bundesliga",
        "SERIEA": "Serie_A",
        "LIGUE1": "Ligue_1",
        "RFPL": "RFPL",
    }
    
    def __init__(self, timeout: float = DEFAULT_TIMEOUT, debug: bool = False, use_library: bool = True):
        """
        初始化 Understat Provider
        
        Args:
            timeout: 请求超时时间（秒）
            debug: 是否打印调试信息
            use_library: 是否使用 understatapi 库（推荐）
        """
        super().__init__(api_key="", timeout=timeout)
        self.debug = debug
        self.use_library = use_library
        self._session: Optional[aiohttp.ClientSession] = None
        self._understat: Optional[Any] = None
        
        if use_library and not UNDERSTAT_API_AVAILABLE:
            logger.warning("Falling back to HTTP requests. Install understatapi for full functionality.")
    
    @property
    def name(self) -> str:
        """返回提供者名称"""
        return "understat"
    
    @property
    def using_library(self) -> bool:
        """是否正在使用 understatapi 库"""
        return self.use_library and UNDERSTAT_API_AVAILABLE
    
    async def is_available(self) -> bool:
        """检查 API 是否可用"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.BASE_URL, timeout=self.timeout) as response:
                    return response.status == 200
        except Exception:
            return False
    
    def _normalize_league_code(self, league: str) -> str:
        if not league:
            return league
        key = league.strip()
        lower = key.lower()
        if lower == "epl":
            return "EPL"
        if lower in ("la_liga", "la_liga".lower(), "la-liga"):
            return "La_Liga"
        if lower == "bundesliga":
            return "Bundesliga"
        if lower in ("serie_a", "serie a"):
            return "Serie_A"
        if lower in ("ligue_1", "ligue 1"):
            return "Ligue_1"
        if lower == "rfpl":
            return "RFPL"
        return key

    async def _get_understat(self) -> Optional[Any]:
        """获取 understatapi client 实例（同步库，通过线程调用）。"""
        if not UNDERSTAT_API_AVAILABLE:
            return None
        
        if self._understat is None:
            self._understat = UnderstatClient()
        
        return self._understat
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """获取或创建 HTTP 会话"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "application/json, text/javascript, */*; q=0.01",
                }
            )
        return self._session
    
    async def close(self):
        """关闭所有连接"""
        if self._understat:
            try:
                if hasattr(self._understat, "close"):
                    self._understat.close()
                elif hasattr(self._understat, "session") and getattr(self._understat, "session", None):
                    self._understat.session.close()
            except Exception:
                pass
            self._understat = None
        
        # 关闭 HTTP 会话
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    # ==================== 使用 understatapi 库的方法（推荐）====================
    
    async def get_league_teams_lib(self, league: str, season: str) -> Optional[List[Dict[str, Any]]]:
        """
        使用 understatapi 库获取联赛球队数据
        
        Args:
            league: 联赛代码
            season: 赛季
            
        Returns:
            球队数据列表
        """
        if not self.using_library:
            logger.warning("understatapi library not available")
            return None
        
        understat = await self._get_understat()
        if not understat:
            return None
        
        try:
            code = self._normalize_league_code(league)
            raw = await asyncio.to_thread(
                understat.league(league=code).get_team_data,
                season=season,
            )
            if isinstance(raw, dict):
                teams = raw.get("teams")
                if isinstance(teams, list):
                    return teams
            return None
        except Exception as e:
            logger.error(f"Error getting league teams: {e}")
            return None
    
    async def get_league_players_lib(self, league: str, season: str) -> Optional[List[Dict[str, Any]]]:
        """
        使用 understatapi 库获取联赛球员数据
        
        Args:
            league: 联赛代码
            season: 赛季
            
        Returns:
            球员数据列表
        """
        if not self.using_library:
            logger.warning("understatapi library not available")
            return None
        
        understat = await self._get_understat()
        if not understat:
            return None
        
        try:
            code = self._normalize_league_code(league)
            players = await asyncio.to_thread(
                understat.league(league=code).get_player_data,
                season=season,
            )
            return players if isinstance(players, list) else None
        except Exception as e:
            logger.error(f"Error getting league players: {e}")
            return None
    
    async def get_league_matches_lib(self, league: str, season: str) -> Optional[List[Dict[str, Any]]]:
        """
        使用 understatapi 库获取联赛比赛数据
        
        Args:
            league: 联赛代码
            season: 赛季
            
        Returns:
            比赛数据列表
        """
        if not self.using_library:
            logger.warning("understatapi library not available")
            return None
        
        understat = await self._get_understat()
        if not understat:
            return None
        
        try:
            code = self._normalize_league_code(league)
            matches = await asyncio.to_thread(
                understat.league(league=code).get_match_data,
                season=season,
            )
            return matches if isinstance(matches, list) else None
        except Exception as e:
            logger.error(f"Error getting league matches: {e}")
            return None
    
    async def get_match_stats_lib(self, match_id: int) -> Optional[Dict[str, Any]]:
        """
        使用 understatapi 库获取比赛统计数据
        
        Args:
            match_id: 比赛 ID
            
        Returns:
            比赛统计数据（包含射门数据、球员数据等）
        """
        if not self.using_library:
            logger.warning("understatapi library not available")
            return None
        
        understat = await self._get_understat()
        if not understat:
            return None
        
        try:
            shots_data = await asyncio.to_thread(
                understat.match(match=str(match_id)).get_shot_data
            )
            roster_data = await asyncio.to_thread(
                understat.match(match=str(match_id)).get_roster_data
            )
            
            # 整合数据
            match_stats = {
                "match_id": match_id,
                "shots": shots_data or [],
                "players": roster_data or {},
            }
            
            # 如果有射门数据，计算基本统计
            if shots_data and isinstance(shots_data, list):
                home_shots = [s for s in shots_data if str(s.get("h_a", "")).lower() in ("h", "home")]
                away_shots = [s for s in shots_data if str(s.get("h_a", "")).lower() in ("a", "away")]
                
                match_stats["home_shots"] = len(home_shots)
                match_stats["away_shots"] = len(away_shots)
                match_stats["home_xg"] = sum(float(s.get("xG", 0)) for s in home_shots)
                match_stats["away_xg"] = sum(float(s.get("xG", 0)) for s in away_shots)
                match_stats["total_shots"] = len(shots_data)
                match_stats["total_xg"] = sum(float(s.get("xG", 0)) for s in shots_data)
            
            return match_stats
        except Exception as e:
            logger.error(f"Error getting match stats: {e}")
            return None
    
    async def get_team_stats_lib(self, team_id: int, season: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        使用 understatapi 库获取球队统计数据
        
        Args:
            team_id: 球队 ID
            season: 赛季（可选，如果不提供则尝试获取所有赛季数据）
            
        Returns:
            球队统计数据
        """
        if not self.using_library:
            logger.warning("understatapi library not available")
            return None
        
        logger.warning("understatapi does not support fetching team stats by team_id. Provide league/team name mapping if needed.")
        return None
    
    async def get_team_stats_by_season(self, team_id: int, season: str) -> Optional[Dict[str, Any]]:
        """
        获取球队在特定赛季的统计数据（便捷方法）
        
        Args:
            team_id: 球队 ID
            season: 赛季（如 "2024"）
            
        Returns:
            球队统计数据
        """
        return await self.get_team_stats_lib(team_id, season)
    
    async def get_player_stats_lib(self, player_id: int) -> Optional[Dict[str, Any]]:
        """
        使用 understatapi 库获取球员统计数据
        
        Args:
            player_id: 球员 ID
            
        Returns:
            球员统计数据（字典格式）
        """
        if not self.using_library:
            logger.warning("understatapi library not available")
            return None
        
        understat = await self._get_understat()
        if not understat:
            return None
        
        try:
            stats_list = await asyncio.to_thread(
                understat.player(player=str(player_id)).get_season_data
            )
            
            if not stats_list:
                return None
            
            # 处理返回列表格式
            if isinstance(stats_list, list):
                # 如果有多个赛季数据，返回最新赛季或汇总数据
                if len(stats_list) > 0:
                    # 尝试找到最新赛季的数据（通常列表最后一个元素是最新的）
                    latest_stats = stats_list[-1] if stats_list else {}
                    
                    # 整合所有赛季的数据
                    aggregated_stats = {
                        "player_id": player_id,
                        "seasons": stats_list,  # 保留所有赛季数据
                        "latest_season": latest_stats,
                    }
                    
                    # 如果有多个赛季，计算总和
                    if len(stats_list) > 1:
                        total_goals = sum(int(s.get("goals", 0)) for s in stats_list if isinstance(s, dict))
                        total_xg = sum(float(s.get("xG", 0)) for s in stats_list if isinstance(s, dict))
                        total_assists = sum(int(s.get("assists", 0)) for s in stats_list if isinstance(s, dict))
                        total_xa = sum(float(s.get("xA", 0)) for s in stats_list if isinstance(s, dict))
                        
                        aggregated_stats["career_totals"] = {
                            "goals": total_goals,
                            "xG": total_xg,
                            "assists": total_assists,
                            "xA": total_xa,
                        }
                    
                    # 合并最新赛季的数据到顶层，方便访问
                    if isinstance(latest_stats, dict):
                        aggregated_stats.update(latest_stats)
                    
                    return aggregated_stats
                else:
                    return None
            elif isinstance(stats_list, dict):
                # 如果返回的是字典，直接添加 player_id
                stats_list["player_id"] = player_id
                return stats_list
            else:
                logger.error(f"Unexpected return type from get_player_stats: {type(stats_list)}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting player stats: {e}")
            return None
    
    async def get_player_shots_lib(self, player_id: int) -> Optional[List[Dict[str, Any]]]:
        """
        使用 understatapi 库获取球员射门数据
        
        Args:
            player_id: 球员 ID
            
        Returns:
            射门数据列表
        """
        if not self.using_library:
            logger.warning("understatapi library not available")
            return None
        
        understat = await self._get_understat()
        if not understat:
            return None
        
        try:
            shots = await asyncio.to_thread(
                understat.player(player=str(player_id)).get_shot_data
            )
            return shots if isinstance(shots, list) else None
        except Exception as e:
            logger.error(f"Error getting player shots: {e}")
            return None
    
    # ==================== 直接 HTTP 请求方法（备用方案）====================
    
    async def get_league_players_http(self, league: str, season: str) -> Optional[List[Dict[str, Any]]]:
        """
        通过直接 HTTP 请求获取联赛球员数据
        
        Args:
            league: 联赛代码
            season: 赛季
            
        Returns:
            球员数据列表
        """
        endpoint = f"/main/getPlayersStats/{league}/{season}"
        
        if not endpoint.startswith('/'):
            endpoint = '/' + endpoint
        
        url = f"{self.BASE_URL}{endpoint}"
        
        if self.debug:
            logger.info(f"Understat HTTP Request: {url}")
        
        session = await self._get_session()
        
        try:
            async with session.get(url, timeout=self.timeout) as response:
                if response.status == 200:
                    content_type = response.headers.get('Content-Type', '')
                    if 'json' in content_type:
                        data = await response.json()
                        if self.debug:
                            logger.info(f"Understat Response (JSON): Success")
                        
                        if isinstance(data, list):
                            return data
                        elif isinstance(data, dict) and "data" in data:
                            return data["data"]
                    
                    if self.debug:
                        logger.warning(f"Received HTML instead of JSON for {url}")
                else:
                    if self.debug:
                        logger.error(f"Understat HTTP error {response.status} for {url}")
                return None
        except Exception as e:
            logger.error(f"Understat request failed: {e}")
            return None
    
    # ==================== 统一接口方法 ====================
    
    async def get_league_teams(self, league: str, season: str) -> Optional[List[Dict[str, Any]]]:
        """
        获取联赛球队数据（自动选择最佳方法）
        
        Args:
            league: 联赛代码
            season: 赛季
            
        Returns:
            球队数据列表
        """
        # 优先使用库
        if self.using_library:
            result = await self.get_league_teams_lib(league, season)
            if result:
                return result
        
        # 回退到 HTTP 请求（当前未实现 HTML 解析）
        logger.warning(f"Using library recommended for get_league_teams")
        return None
    
    async def get_league_players(self, league: str, season: str) -> Optional[List[Dict[str, Any]]]:
        """
        获取联赛球员数据（自动选择最佳方法）
        
        Args:
            league: 联赛代码
            season: 赛季
            
        Returns:
            球员数据列表
        """
        # 优先使用库
        if self.using_library:
            result = await self.get_league_players_lib(league, season)
            if result:
                return result
        
        # 回退到 HTTP 请求
        return await self.get_league_players_http(league, season)
    
    async def get_league_matches(self, league: str, season: str) -> Optional[List[Dict[str, Any]]]:
        """
        获取联赛比赛数据（自动选择最佳方法）
        
        Args:
            league: 联赛代码
            season: 赛季
            
        Returns:
            比赛数据列表
        """
        if self.using_library:
            result = await self.get_league_matches_lib(league, season)
            if result:
                return result
        
        logger.warning(f"Using library recommended for get_league_matches")
        return None
    
    async def get_match_stats(self, match_id: int) -> Optional[Dict[str, Any]]:
        """
        获取比赛统计数据（自动选择最佳方法）
        
        Args:
            match_id: 比赛 ID
            
        Returns:
            比赛统计数据
        """
        if self.using_library:
            result = await self.get_match_stats_lib(match_id)
            if result:
                return result
        
        logger.warning(f"Using library recommended for get_match_stats")
        return None
    
    async def get_team_stats(self, team_id: int, season: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        获取球队统计数据（自动选择最佳方法）
        
        Args:
            team_id: 球队 ID
            season: 赛季（可选，建议提供）
            
        Returns:
            球队统计数据
        """
        if self.using_library:
            result = await self.get_team_stats_lib(team_id, season)
            if result:
                return result
        
        logger.warning(f"Using library recommended for get_team_stats. Season parameter recommended.")
        return None
    
    async def get_player_stats(self, player_id: int) -> Optional[Dict[str, Any]]:
        """
        获取球员统计数据（自动选择最佳方法）
        
        Args:
            player_id: 球员 ID
            
        Returns:
            球员统计数据（字典格式，包含最新赛季数据和职业生涯总和）
        """
        if self.using_library:
            result = await self.get_player_stats_lib(player_id)
            if result:
                return result
        
        logger.warning(f"Using library recommended for get_player_stats")
        return None
    
    async def get_player_shots(self, player_id: int) -> Optional[List[Dict[str, Any]]]:
        """
        获取球员射门数据（自动选择最佳方法）
        
        Args:
            player_id: 球员 ID
            
        Returns:
            射门数据列表
        """
        if self.using_library:
            result = await self.get_player_shots_lib(player_id)
            if result:
                return result
        
        logger.warning(f"Using library recommended for get_player_shots")
        return None
    
    # ==================== 辅助方法 ====================
    
    async def get_available_seasons(self, league: str) -> List[str]:
        """
        获取联赛可用的赛季列表
        
        Args:
            league: 联赛代码
            
        Returns:
            赛季列表
        """
        current_year = datetime.datetime.now().year
        seasons = []
        
        for year in range(current_year - 10, current_year + 1):
            seasons.append(str(year))
        
        return seasons
    
    def parse_xg_data(self, match_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析比赛中的 xG 数据
        
        Args:
            match_data: 比赛原始数据
            
        Returns:
            解析后的 xG 数据
        """
        result = {
            "home_xg": 0.0,
            "away_xg": 0.0,
            "home_goals": 0,
            "away_goals": 0,
            "shots": []
        }
        
        if isinstance(match_data, dict):
            result["home_xg"] = float(match_data.get("h_xG", 0))
            result["away_xg"] = float(match_data.get("a_xG", 0))
            result["home_goals"] = int(match_data.get("h_goals", 0))
            result["away_goals"] = int(match_data.get("a_goals", 0))
            
            shots = match_data.get("shots", [])
            for shot in shots:
                result["shots"].append({
                    "player": shot.get("player"),
                    "team": shot.get("team"),
                    "minute": shot.get("min"),
                    "xg": float(shot.get("xG", 0)),
                    "result": shot.get("result"),
                    "shot_type": shot.get("shotType"),
                    "situation": shot.get("situation")
                })
        
        return result


# 便捷的工厂函数
def create_provider(use_library: bool = True, **kwargs) -> UnderstatProvider:
    """
    创建 Understat Provider 实例
    
    Args:
        use_library: 是否使用 understatapi 库（推荐）
        **kwargs: 其他配置参数
        
    Returns:
        UnderstatProvider 实例
    """
    return UnderstatProvider(use_library=use_library, **kwargs)

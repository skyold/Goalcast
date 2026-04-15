"""
internal.py — Goalcast MCP Server 内部实现层

包含所有 provider 包装函数、helper 工具函数和内部逻辑。
MCP 接口见 server.py。
"""

import asyncio
import datetime
import os
import sys
import yaml
from pathlib import Path
from typing import Optional, List, Dict, Any
from mcp.server.fastmcp import FastMCP

# 确保项目根目录在 sys.path 中，无论从哪里启动 server 都能找到各包
_project_root = str(Path(__file__).parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from provider.footystats.client import FootyStatsProvider
from provider.sportmonks.client import SportmonksProvider
from provider.understat.client import UnderstatProvider
from analytics.poisson import poisson_distribution, dixon_coles_distribution, calculate_ah_probability
from analytics.ev_calculator import calculate_ev, calculate_kelly, calculate_risk_adjusted_ev, best_bet_recommendation
from analytics.confidence import calculate_confidence, calculate_confidence_v25, confidence_breakdown
from utils.logger import logger
from datasource.datafusion.fusion import DataFusion
from datasource.datafusion.resolvers.sportmonks_resolver import SportmonksResolver
from datasource.sportmonks.models import SportmonksMatchData

# ── 联赛关键词映射（供 goalcast_sm_get_fixtures 使用）──────────────────────────
_SM_LEAGUE_KEYWORDS: Dict[str, List[str]] = {
    "Premier League":  ["premier league"],
    "Championship":    ["championship"],
    "Serie A":         ["serie a"],
    "La Liga":         ["la liga", "laliga"],
    "Bundesliga":      ["bundesliga"],
    "Ligue 1":         ["ligue 1", "ligue1"],
    "Eredivisie":      ["eredivisie"],
    "Primeira Liga":   ["primeira liga"],
}


def _infer_season(match_date: str) -> str:
    """从比赛日期推断赛季年份（赛季跨年取后一年）。"""
    try:
        year = int(match_date[:4])
        month = int(match_date[5:7])
        return str(year) if month >= 8 else str(year - 1)
    except Exception:
        return str(datetime.date.today().year - 1)


def _extract_standing_for_team(raw_standings: Any, team_id: int) -> Optional[Dict[str, Any]]:
    """从 Sportmonks standings 原始响应中提取指定球队的积分榜数据。"""
    try:
        data = raw_standings.get("data", []) if isinstance(raw_standings, dict) else []
        for entry in data:
            if isinstance(entry, dict) and entry.get("participant_id") == team_id:
                details = entry.get("details", [])
                stat = {
                    d["type"]["name"]: d["value"]
                    for d in details
                    if isinstance(d, dict) and "type" in d and "value" in d
                }
                return {
                    "position":        entry.get("position"),
                    "points":          stat.get("Points"),
                    "wins":            stat.get("Won"),
                    "draws":           stat.get("Draw"),
                    "losses":          stat.get("Lost"),
                    "goals_for":       stat.get("Goals For"),
                    "goals_against":   stat.get("Goals Against"),
                    "goal_difference": stat.get("Goal Difference"),
                    "matches_played":  stat.get("Matches Played"),
                }
    except Exception:
        pass
    return None


# Initialize FastMCP server.
# FASTMCP_HOST defaults to 127.0.0.1 (local) but can be overridden via env var,
# e.g. set FASTMCP_HOST=0.0.0.0 in docker-compose.yml for remote access.
mcp = FastMCP(
    "Goalcast Data Providers",
    host=os.environ.get("FASTMCP_HOST", "127.0.0.1"),
    port=int(os.environ.get("FASTMCP_PORT", "8000")),
)

# Initialize providers
# Using lazy initialization to ensure the providers are only created when needed
# or during the server startup.
_footystats = None
_sportmonks = None
_understat = None

def get_footystats():
    global _footystats
    if _footystats is None:
        _footystats = FootyStatsProvider()
    return _footystats

def get_sportmonks():
    global _sportmonks
    if _sportmonks is None:
        _sportmonks = SportmonksProvider()
    return _sportmonks

def get_understat():
    global _understat
    if _understat is None:
        _understat = UnderstatProvider(use_library=True)
    return _understat

# Helper to handle API errors and key issues
async def handle_api_call(provider_name: str, coro):
    try:
        result = await coro
        # Some providers might return error status in the response body instead of raising exception
        if isinstance(result, dict):
            error_msg = str(result.get("error", "")).lower() or str(result.get("message", "")).lower()
            if "api key" in error_msg or "unauthorized" in error_msg or "401" in error_msg:
                return {
                    "error": "API_KEY_INVALID",
                    "message": f"Critical Error: The {provider_name} API Key is missing or invalid. Data from this source is currently unavailable.",
                    "provider": provider_name
                }
        return result
    except Exception as e:
        error_msg = str(e).lower()
        if "api key" in error_msg or "unauthorized" in error_msg or "401" in error_msg:
            return {
                "error": "API_KEY_INVALID",
                "message": f"Critical Error: The {provider_name} API Key is missing or invalid. Please check your .env file or environment variables.",
                "provider": provider_name
            }
        logger.error(f"Error calling {provider_name}: {e}")
        return {
            "error": "PROVIDER_ERROR",
            "message": f"An error occurred while fetching data from {provider_name}: {str(e)}",
            "provider": provider_name
        }

# --- FootyStats Tools ---
# 内部函数：不暴露为 MCP tool，由 goalcast_resolve_match 通过 DataFusion 内部调用。
# V4.0 路径不使用这些函数；v2.5/v3.0 通过 DataFusion 调用。

async def footystats_get_league_list(chosen_leagues_only: bool = False, country: Optional[int] = None) -> Any:
    """Get list of available leagues from FootyStats.
    Args:
        chosen_leagues_only: Whether to only return chosen leagues.
        country: Country ISO ID to filter leagues.
    """
    return await handle_api_call("FootyStats", get_footystats().get_league_list(chosen_leagues_only, country))

async def footystats_get_country_list() -> Any:
    """Get list of all countries and their ISO IDs from FootyStats."""
    return await handle_api_call("FootyStats", get_footystats().get_country_list())

async def footystats_get_todays_matches(
    date: Optional[str] = None,
    timezone: Optional[str] = None,
    league_filter: Optional[str] = None,
) -> Any:
    """Get matches for a specific date from FootyStats.

    WARNING: Global fixture weekends can return 200+ matches (>1MB response).
    Use league_filter to reduce data volume and avoid timeouts.

    Recommended workflow:
      1. Call this tool with league_filter to get match_ids for your target league.
      2. Call get_match_details(match_id) for per-match deep analysis.

    Args:
        date: Date in YYYY-MM-DD format. Defaults to today.
        timezone: Timezone for match times (e.g. 'Europe/London').
        league_filter: Optional league name substring to filter results
            (e.g. 'Premier League', 'Champions League'). Case-insensitive.
            Greatly reduces response size when only one league is needed.
    """
    result = await handle_api_call("FootyStats", get_footystats().get_todays_matches(date, timezone))
    if league_filter and isinstance(result, dict) and isinstance(result.get("data"), list):
        filtered = [
            m for m in result["data"]
            if league_filter.lower() in str(m.get("competition_name", "")).lower()
        ]
        return {**result, "data": filtered}
    return result

async def footystats_get_league_stats(season_id: int) -> Any:
    """Get detailed statistics for a league season from FootyStats."""
    return await handle_api_call("FootyStats", get_footystats().get_league_stats(season_id))

async def footystats_get_league_matches(season_id: int, page: int = 1) -> Any:
    """Get all matches for a specific league season from FootyStats.

    WARNING: Each match contains extensive statistical fields. Even page=1
    can exceed 1MB and cause timeouts for large leagues.

    Recommended alternative for daily analysis:
      get_todays_matches(league_filter=...) → get_match_details(match_id)

    Args:
        season_id: League season ID.
        page: Page number for pagination (default: 1).
    """
    return await handle_api_call("FootyStats", get_footystats().get_league_matches(season_id, page))

async def footystats_get_league_teams(season_id: int) -> Any:
    """Get all teams and their stats for a league season from FootyStats."""
    return await handle_api_call("FootyStats", get_footystats().get_league_teams(season_id))

async def footystats_get_league_tables(season_id: int) -> Any:
    """Get standings table for a specific league season from FootyStats."""
    return await handle_api_call("FootyStats", get_footystats().get_league_tables(season_id))

async def footystats_get_match_details(match_id: int) -> Any:
    """Get detailed statistics, H2H, lineups, and odds for a specific match from FootyStats.
    Includes team stats, goal timings, and starting 11 if available.
    """
    return await handle_api_call("FootyStats", get_footystats().get_match_details(match_id))

async def footystats_get_lineups(match_id: int) -> Any:
    """Get starting lineups and substitutes for a match from FootyStats."""
    return await handle_api_call("FootyStats", get_footystats().get_match_details(match_id))

async def footystats_get_team_details(team_id: int) -> Any:
    """Get complete statistics for a specific team from FootyStats."""
    return await handle_api_call("FootyStats", get_footystats().get_team(team_id))

async def footystats_get_team_last_x_stats(team_id: int) -> Any:
    """Get recent form statistics (last 5/6/10) for a specific team from FootyStats."""
    return await handle_api_call("FootyStats", get_footystats().get_team_last_x_stats(team_id))

async def footystats_get_btts_stats() -> Any:
    """Get top teams and fixtures for BTTS (Both Teams To Score) from FootyStats."""
    return await handle_api_call("FootyStats", get_footystats().get_btts_stats())

async def footystats_get_over25_stats() -> Any:
    """Get top teams and fixtures for Over 2.5 Goals from FootyStats."""
    return await handle_api_call("FootyStats", get_footystats().get_over_2_5_stats())


# --- Understat Tools ---
# Advanced football statistics (xG, xA) - Free, no API key required

async def understat_get_league_players(league: str, season: str) -> Any:
    """Get player statistics for a league season from Understat.
    
    Provides advanced metrics including xG (Expected Goals), xA (Expected Assists),
    shots, key passes, and more.
    
    ## 📊 支持的联赛
    - `EPL`: 英格兰超级联赛
    - `La_liga`: 西班牙甲级联赛
    - `Bundesliga`: 德国甲级联赛
    - `Serie_A`: 意大利甲级联赛
    - `Ligue_1`: 法国甲级联赛
    - `RFPL`: 俄罗斯超级联赛
    
    ## 📋 返回数据字段
    | 字段 | 说明 | 类型 |
    |------|------|------|
    | player_name | 球员姓名 | str |
    | team_title | 球队名称 | str |
    | games | 出场次数 | int |
    | time | 出场时间（分钟） | int |
    | goals | 进球数 | int |
    | xG | 期望进球 | float |
    | xA | 期望助攻 | float |
    | shots | 射门次数 | int |
    | shots_on_target | 射正次数 | int |
    | key_passes | 关键传球 | int |
    | xG_chain | 参与进攻的 xG | float |
    | xGBuildup | 组织进攻的 xG | float |
    
    ## 🎯 典型用途
    1. **按 xG 排序找最佳射手**: `sorted(players, key=lambda x: float(x['xG']), reverse=True)`
    2. **分析 xG vs 实际进球**: `diff = goals - xG` 判断球员表现
    3. **比较不同联赛**: 获取多个联赛数据进行对比
    
    ## 💡 使用示例
    ```python
    # 获取德甲 2024 球员
    players = await understat_get_league_players("Bundesliga", "2024")
    
    # 按 xG 排序 Top 10
    top_scorers = sorted(players, key=lambda x: float(x.get('xG', 0)), reverse=True)[:10]
    
    # 分析 xG 表现
    for p in top_scorers:
        diff = int(p['goals']) - float(p['xG'])
        print(f"{p['player_name']}: {p['goals']} goals vs {p['xG']:.2f} xG ({diff:+.2f})")
    ```
    
    ## ⚠️ 注意事项
    - ✅ 数据免费，无需 API Key
    - ✅ 建议使用 understatapi 库（已集成）
    - ⚠️ 返回数据包含 xG_chain, xGBuildup 等高级指标
    
    Args:
        league: League code. Options: EPL, La_liga, Bundesliga, Serie_A, Ligue_1, RFPL
        season: Season year (e.g. "2024")
    
    Returns:
        List of players with statistics including:
        - player_name, team_title, games, time
        - goals, xG, xA, shots, shots_on_target
        - key_passes, yellow_cards, red_cards
        - xG_chain, xGBuildup
    
    Example:
        # Get Bundesliga 2024 players
        players = await understat_get_league_players("Bundesliga", "2024")
        
        # Sort by xG
        top_scorers = sorted(players, key=lambda x: float(x.get('xG', 0)), reverse=True)
    """
    return await handle_api_call("Understat", get_understat().get_league_players(league, season))


async def understat_get_league_teams(league: str, season: str) -> Any:
    """Get team list for a league season from Understat.
    
    ## 📊 支持的联赛
    - `EPL`: 英格兰超级联赛
    - `La_liga`: 西班牙甲级联赛
    - `Bundesliga`: 德国甲级联赛 (18 支球队)
    - `Serie_A`: 意大利甲级联赛
    - `Ligue_1`: 法国甲级联赛
    - `RFPL`: 俄罗斯超级联赛
    
    ## 📋 返回数据字段
    | 字段 | 说明 | 类型 |
    |------|------|------|
    | id | 球队 ID | int |
    | title | 球队名称 | str |
    | history | 历史数据列表 | list |
    
    ## 🎯 典型用途
    1. **获取球队 ID**: 用于后续查询 `understat_get_team_stats`
    2. **球队列表分析**: 统计球队数量、名称
    3. **历史数据追踪**: 分析 `history` 字段中的赛季表现
    
    ## 💡 使用示例
    ```python
    # 获取德甲球队
    teams = await understat_get_league_teams("Bundesliga", "2024")
    
    print(f"德甲共有 {len(teams)} 支球队:")
    for team in teams:
        print(f"  - {team['title']} (ID: {team['id']})")
    
    # 获取拜仁 ID 用于后续查询
    bayern = next(t for t in teams if "Bayern" in t['title'])
    bayern_id = bayern['id']  # 117
    ```
    
    ## ⚠️ 注意事项
    - ✅ 数据免费，无需 API Key
    - ⚠️ 球队数量因联赛而异（德甲 18 支，英超/西甲 20 支）
    - 💡 `history` 字段包含球队历史赛季数据
    
    Args:
        league: League code. Options: EPL, La_liga, Bundesliga, Serie_A, Ligue_1, RFPL
        season: Season year (e.g. "2024")
    
    Returns:
        List of teams with basic info (id, title, history)
    
    Example:
        # Get Bundesliga teams
        teams = await understat_get_league_teams("Bundesliga", "2024")
    """
    return await handle_api_call("Understat", get_understat().get_league_teams(league, season))


async def understat_get_league_matches(league: str, season: str) -> Any:
    """Get match results for a league season from Understat.
    
    ## 📊 支持的联赛
    - `EPL`: 英格兰超级联赛
    - `La_liga`: 西班牙甲级联赛
    - `Bundesliga`: 德国甲级联赛 (306 场比赛)
    - `Serie_A`: 意大利甲级联赛
    - `Ligue_1`: 法国甲级联赛
    - `RFPL`: 俄罗斯超级联赛
    
    ## 📋 返回数据字段
    | 字段 | 说明 | 类型 |
    |------|------|------|
    | id | 比赛 ID | int |
    | h_team | 主队名称 | str |
    | a_team | 客队名称 | str |
    | h_goals | 主队进球 | int |
    | a_goals | 客队进球 | int |
    | h_xG | 主队期望进球 | float |
    | a_xG | 客队期望进球 | float |
    | date | 比赛日期 | str |
    
    ## 🎯 典型用途
    1. **获取比赛 ID**: 用于 `understat_get_match_stats` 查询详细数据
    2. **分析 xG 表现**: 比较 `h_xG/a_xG` 与实际比分
    3. **赛程分析**: 按日期筛选比赛
    
    ## 💡 使用示例
    ```python
    # 获取德甲比赛
    matches = await understat_get_league_matches("Bundesliga", "2024")
    
    print(f"德甲共有 {len(matches)} 场比赛")
    
    # 分析 xG vs 实际进球差异
    for match in matches[:5]:
        h_diff = int(match['h_goals']) - float(match['h_xG'])
        a_diff = int(match['a_goals']) - float(match['a_xG'])
        print(f"{match['h_team']} {match['h_goals']}-{match['a_goals']} {match['a_team']}")
        print(f"  xG: {match['h_xG']:.2f}-{match['a_xG']:.2f} (差异：{h_diff:+.2f}/{a_diff:+.2f})")
    
    # 获取比赛 ID 用于详细分析
    match_id = matches[0]['id']
    ```
    
    ## ⚠️ 注意事项
    - ✅ 数据免费，无需 API Key
    - ⚠️ 比赛数量因联赛而异（德甲 306 场，英超/西甲 380 场）
    - 💡 比赛 ID 可用于 `understat_get_match_stats` 获取射门详情
    
    Args:
        league: League code. Options: EPL, La_liga, Bundesliga, Serie_A, Ligue_1, RFPL
        season: Season year (e.g. "2024")
    
    Returns:
        List of matches with basic info (id, teams, scores, xG)
    
    Example:
        # Get Bundesliga matches
        matches = await understat_get_league_matches("Bundesliga", "2024")
    """
    return await handle_api_call("Understat", get_understat().get_league_matches(league, season))


async def understat_get_match_stats(match_id: int) -> Any:
    """Get detailed match statistics including shots and player performance.
    
    ## 📋 返回数据结构
    ```python
    {
        "match_id": 12345,
        "shots": [...],      # 所有射门数据列表
        "players": {...},    # 球员表现数据
        "total_shots": 25,   # 总射门次数
        "total_xg": 2.456,   # 总期望进球
        "home_shots": 15,    # 主队射门
        "home_xg": 1.789,    # 主队 xG
        "away_shots": 10,    # 客队射门
        "away_xg": 0.667     # 客队 xG
    }
    ```
    
    ## 📊 射门数据字段
    | 字段 | 说明 | 类型 |
    |------|------|------|
    | player_name | 射门球员 | str |
    | minute | 射门时间（分钟） | int |
    | xG | 期望进球值 | float |
    | result | 射门结果 (goal/miss/save) | str |
    | shot_type | 射门方式 (head/foot) | str |
    | situation | 进攻情景 (open_play/set_piece) | str |
    | is_goal | 是否进球 | bool |
    
    ## 🎯 典型用途
    1. **比赛射门分析**: 统计总射门数、总 xG
    2. **最佳机会识别**: 找出 xG 最高的射门
    3. **球员表现评估**: 分析特定球员的射门质量
    4. **xG vs 实际进球**: 判断球队表现是否超常
    
    ## 💡 使用示例
    ```python
    # 获取比赛射门数据
    stats = await understat_get_match_stats(match_id=12345)
    
    # 基本统计
    print(f"总射门：{stats['total_shots']}, 总 xG: {stats['total_xg']:.2f}")
    print(f"主队：{stats['home_shots']} 射门，{stats['home_xg']:.2f} xG")
    print(f"客队：{stats['away_shots']} 射门，{stats['away_xg']:.2f} xG")
    
    # 找出最佳机会 (Top 5)
    best_chances = sorted(stats['shots'], key=lambda x: float(x.get('xG', 0)), reverse=True)[:5]
    print("\n最佳机会 Top 5:")
    for shot in best_chances:
        print(f"  {shot['player_name']} {shot['minute']}' xG:{float(shot['xG']):.2f} - {shot['result']}")
    
    # 分析进球
    goals = [s for s in stats['shots'] if s.get('is_goal', False)]
    print(f"\n进球数：{len(goals)}")
    for goal in goals:
        print(f"  {goal['player_name']} {goal['minute']}' ({goal['shot_type']})")
    ```
    
    ## ⚠️ 注意事项
    - ✅ 比赛 ID 从 `understat_get_league_matches` 获取
    - ✅ 包含每次射门的详细 xG 值
    - 💡 `xG` 值范围 0-1，越高表示进球概率越大
    - 💡 `situation`: open_play(运动战), set_piece(定位球), counter(反击)
    
    Args:
        match_id: Match ID from understat_get_league_matches
    
    Returns:
        Match statistics including:
        - shots: List of all shots with xG values
        - players: Player performance data
        - total_shots, total_xg
        - home_shots, home_xg, away_shots, away_xg
    
    Example:
        # Get match shots data
        stats = await understat_get_match_stats(match_id=12345)
        print(f"Total shots: {stats['total_shots']}, Total xG: {stats['total_xg']:.2f}")
    """
    return await handle_api_call("Understat", get_understat().get_match_stats(match_id))


async def understat_get_team_stats(team_id: int, season: str) -> Any:
    """Get team statistics for a specific season.
    
    ## 📋 返回数据结构
    ```python
    {
        "id": 117,
        "title": "Bayern Munich",
        "season": "2024",
        "players": [...]  # 球队球员列表和统计
    }
    ```
    
    ## 📊 球员数据字段 (players 列表)
    | 字段 | 说明 | 类型 |
    |------|------|------|
    | player_name | 球员姓名 | str |
    | games | 出场次数 | int |
    | time | 出场时间（分钟） | int |
    | goals | 进球数 | int |
    | xG | 期望进球 | float |
    | xA | 期望助攻 | float |
    | shots | 射门次数 | int |
    | key_passes | 关键传球 | int |
    
    ## 🎯 典型用途
    1. **球队阵容分析**: 获取球队所有球员数据
    2. **球员贡献评估**: 按 xG/进球排序找核心球员
    3. **赛季表现追踪**: 比较不同赛季的球队数据
    4. **青训分析**: 识别年轻球员和高潜力球员
    
    ## 💡 使用示例
    ```python
    # 获取拜仁 2024 赛季数据
    stats = await understat_get_team_stats(team_id=117, season="2024")
    
    print(f"球队：{stats['title']}")
    print(f"赛季：{stats['season']}")
    
    # 分析球员
    if 'players' in stats:
        players = stats['players']
        print(f"\n球员数量：{len(players)}")
        
        # 按 xG 排序 Top 5
        top_xg = sorted(players, key=lambda x: float(x.get('xG', 0)), reverse=True)[:5]
        print("\nTop 5 by xG:")
        for p in top_xg:
            print(f"  {p['player_name']}: {p['xG']:.2f} xG, {p['goals']} goals")
        
        # 找出最高效射手
        efficient = [p for p in players if int(p['goals']) > float(p['xG']) * 1.2]
        print("\n高效射手 (进球>xG*1.2):")
        for p in efficient:
            diff = int(p['goals']) - float(p['xG'])
            print(f"  {p['player_name']}: {p['goals']} goals vs {p['xG']:.2f} xG (+{diff:+.2f})")
    ```
    
    ## ⚠️ 注意事项
    - ✅ 球队 ID 从 `understat_get_league_teams` 获取
    - ⚠️ **必须提供 season 参数**（如 "2024"）
    - ✅ 返回数据包含球队所有球员的统计
    - 💡 如果返回空数据，可能是赛季参数不正确
    
    Args:
        team_id: Team ID from understat_get_league_teams
        season: Season year (e.g. "2024")
    
    Returns:
        Team statistics including:
        - Basic team info (id, title)
        - Season performance data
        - players: List of team players with stats
    
    Example:
        # Get Bayern Munich 2024 stats
        stats = await understat_get_team_stats(team_id=117, season="2024")
    """
    return await handle_api_call("Understat", get_understat().get_team_stats(team_id, season))


async def understat_get_player_stats(player_id: int) -> Any:
    """Get detailed player statistics across all seasons.
    
    ## 📋 返回数据结构
    ```python
    {
        "player_id": 12345,
        "player_name": "Harry Kane",
        "latest_season": {...},      # 最新赛季数据
        "seasons": [...],            # 所有赛季数据列表
        "career_totals": {           # 职业生涯总和
            "goals": 150,
            "xG": 142.5,
            "assists": 45,
            "xA": 38.2
        },
        # 最新赛季数据也合并到顶层，方便访问
        "goals": 26,
        "xG": 24.84,
        ...
    }
    ```
    
    ## 📊 数据层次说明
    1. **player_id**: 球员唯一标识
    2. **latest_season**: 最近一个赛季的详细数据
    3. **seasons**: 所有赛季数据列表（可用于趋势分析）
    4. **career_totals**: 职业生涯总和（总进球、总 xG、总助攻、总 xA）
    5. **顶层字段**: 最新赛季数据直接合并，方便快速访问
    
    ## 🎯 典型用途
    1. **职业生涯追踪**: 查看球员多个赛季的表现趋势
    2. **xG 表现分析**: 比较职业生涯总进球 vs 总 xG
    3. **最新状态评估**: 使用 latest_season 分析当前表现
    4. **效率分析**: 计算 xG 转化率、射门效率等
    
    ## 💡 使用示例
    ```python
    # 获取球员完整统计
    stats = await understat_get_player_stats(player_id=12345)
    
    print(f"球员：{stats.get('player_name', 'Unknown')}")
    
    # 职业生涯总和
    if 'career_totals' in stats:
        totals = stats['career_totals']
        print(f"\n职业生涯总和:")
        print(f"  - 总进球：{totals['goals']}")
        print(f"  - 总 xG: {totals['xG']:.2f}")
        print(f"  - 总助攻：{totals['assists']}")
        print(f"  - 总 xA: {totals['xA']:.2f}")
        
        # xG 表现差异
        diff = totals['goals'] - totals['xG']
        print(f"  - 进球 vs xG 差异：{diff:+.2f}")
    
    # 最新赛季表现
    if 'latest_season' in stats:
        latest = stats['latest_season']
        print(f"\n最新赛季:")
        print(f"  - 进球：{latest.get('goals', 0)}")
        print(f"  - xG: {float(latest.get('xG', 0)):.2f}")
        print(f"  - 助攻：{latest.get('assists', 0)}")
    
    # 多赛季趋势分析
    if 'seasons' in stats:
        print(f"\n赛季趋势 ({len(stats['seasons'])} 个赛季):")
        for season in stats['seasons'][-3:]:  # 最近 3 个赛季
            print(f"  {season.get('season', 'N/A')}: "
                  f"{season.get('goals', 0)} goals, {float(season.get('xG', 0)):.2f} xG")
    ```
    
    ## ⚠️ 注意事项
    - ✅ 球员 ID 从 `understat_get_league_players` 获取
    - ✅ 自动处理 understatapi 返回的列表格式
    - ✅ 提供多层数据结构满足不同需求
    - 💡 `career_totals` 仅在有多个赛季数据时提供
    - 💡 xG 表现差异：正数表示表现优于预期，负数表示低于预期
    
    Args:
        player_id: Player ID from understat_get_league_players
    
    Returns:
        Player statistics including:
        - player_id
        - latest_season: Most recent season data
        - seasons: List of all season data
        - career_totals: Career summary (goals, xG, assists, xA)
        - Individual season stats merged at top level
    
    Example:
        # Get player career stats
        stats = await understat_get_player_stats(player_id=12345)
        print(f"Career goals: {stats['career_totals']['goals']}")
        print(f"Latest season xG: {stats['latest_season']['xG']:.2f}")
    """
    return await handle_api_call("Understat", get_understat().get_player_stats(player_id))


async def understat_get_player_shots(player_id: int) -> Any:
    """Get all shots for a specific player.
    
    ## 📋 返回数据结构
    ```python
    [
        {
            "id": 1234,
            "minute": 25,         # 射门时间（分钟）
            "xG": 0.45,           # 期望进球值
            "result": "goal",     # 射门结果
            "shot_type": "foot",  # 射门方式
            "situation": "open_play",  # 进攻情景
            "is_goal": True       # 是否进球
        },
        ...
    ]
    ```
    
    ## 📊 射门数据字段详解
    | 字段 | 说明 | 可能值 |
    |------|------|--------|
    | minute | 射门时间（分钟） | 0-90+ |
    | xG | 期望进球值 | 0.0-1.0 |
    | result | 射门结果 | goal, miss, saved, blocked |
    | shot_type | 射门方式 | foot, head, other |
    | situation | 进攻情景 | open_play, set_piece, counter, fastbreak |
    | is_goal | 是否进球 | true/false |
    
    ## 🎯 典型用途
    1. **射门质量分析**: 计算平均 xG、射门转化率
    2. **射门偏好分析**: 分析头球/脚射比例、运动战/定位球偏好
    3. **效率评估**: 比较实际进球 vs 总 xG
    4. **关键时刻分析**: 找出高 xG 射门和错失机会
    
    ## 💡 使用示例
    ```python
    # 获取球员射门数据
    shots = await understat_get_player_shots(player_id=12345)
    
    # 基本统计
    goals = sum(1 for s in shots if s.get('is_goal', False))
    total_xg = sum(float(s.get('xG', 0)) for s in shots)
    
    print(f"射门分析:")
    print(f"  - 总射门：{len(shots)}")
    print(f"  - 进球数：{goals}")
    print(f"  - 总 xG: {total_xg:.2f}")
    print(f"  - 射门转化率：{goals/len(shots)*100:.1f}%")
    print(f"  - 平均每次射门 xG: {total_xg/len(shots):.3f}")
    
    # xG 表现差异
    diff = goals - total_xg
    print(f"  - 进球 vs xG: {diff:+.2f} ({'优于预期' if diff > 0 else '低于预期'})")
    
    # 射门方式分析
    foot_shots = [s for s in shots if s.get('shot_type') == 'foot']
    head_shots = [s for s in shots if s.get('shot_type') == 'head']
    print(f"\n射门方式:")
    print(f"  - 脚射：{len(foot_shots)} ({len(foot_shots)/len(shots)*100:.1f}%)")
    print(f"  - 头球：{len(head_shots)} ({len(head_shots)/len(shots)*100:.1f}%)")
    
    # 进攻情景分析
    open_play = [s for s in shots if s.get('situation') == 'open_play']
    set_piece = [s for s in shots if s.get('situation') == 'set_piece']
    print(f"\n进攻情景:")
    print(f"  - 运动战：{len(open_play)} ({len(open_play)/len(shots)*100:.1f}%)")
    print(f"  - 定位球：{len(set_piece)} ({len(set_piece)/len(shots)*100:.1f}%)")
    
    # 找出最佳机会（高 xG 射门）
    best_chances = sorted(shots, key=lambda x: float(x.get('xG', 0)), reverse=True)[:5]
    print(f"\n最佳机会 Top 5:")
    for i, shot in enumerate(best_chances, 1):
        print(f"  {i}. {shot['minute']}' xG:{float(shot['xG']):.2f} - {shot['result']}")
    ```
    
    ## ⚠️ 注意事项
    - ✅ 球员 ID 从 `understat_get_league_players` 获取
    - ✅ 包含球员所有射门数据（不限赛季）
    - 💡 xG 值范围 0-1，越高表示进球概率越大
    - 💡 **射门转化率**: 进球数/总射门，衡量效率
    - 💡 **xG 表现差异**: 正数表示射门效率高，负数表示效率低
    
    Args:
        player_id: Player ID from understat_get_league_players
    
    Returns:
        List of shots with details:
        - xG value for each shot
        - Shot type (head, foot, etc.)
        - Situation (open play, set piece, etc.)
        - Result (goal, miss, save, etc.)
        - Minute of shot
    
    Example:
        # Analyze player shooting
        shots = await understat_get_player_shots(player_id=12345)
        goals = sum(1 for s in shots if s.get('is_goal', False))
        total_xg = sum(float(s.get('xG', 0)) for s in shots)
        print(f"Goals: {goals}, Total xG: {total_xg:.2f}")
    """
    return await handle_api_call("Understat", get_understat().get_player_shots(player_id))

# --- Sportmonks Tools ---

async def sportmonks_get_livescores(include: Optional[str] = "events,lineups,statistics") -> Any:
    """Get current live scores from Sportmonks with default inclusions.
    Args:
        include: Relationships to include (default: 'events,lineups,statistics').
    """
    return await handle_api_call("Sportmonks", get_sportmonks().get_livescores(include))

async def sportmonks_get_fixtures_by_date(date: str, include: Optional[str] = "league,participants") -> Any:
    """Get fixtures for a specific date from Sportmonks.
    Args:
        date: Date in YYYY-MM-DD format.
        include: Relationships to include (default: 'league,participants').
    """
    return await handle_api_call("Sportmonks", get_sportmonks().get_fixtures_by_date(date, include))

async def sportmonks_get_fixture_by_id(fixture_id: int, include: Optional[str] = None) -> Any:
    """Get detailed fixture information by ID from Sportmonks."""
    return await handle_api_call("Sportmonks", get_sportmonks().get_fixture_by_id(fixture_id, include))

async def sportmonks_get_lineups(fixture_id: int) -> Any:
    """Get detailed starting lineups, substitutes, and formations for a fixture from Sportmonks.
    Includes player names, positions, and ratings.
    """
    return await handle_api_call("Sportmonks", get_sportmonks().get_fixture_by_id(fixture_id, include="lineups.player,formations"))

async def sportmonks_get_player_stats(fixture_id: int) -> Any:
    """Get individual player performance statistics for a specific fixture from Sportmonks.
    Includes passes, shots, tackles, etc., for each player.
    """
    return await handle_api_call("Sportmonks", get_sportmonks().get_fixture_by_id(fixture_id, include="statistics.player"))

async def sportmonks_get_odds_movement(fixture_id: int, market_id: Optional[int] = None) -> Any:
    """Get historical odds movements for a fixture from Sportmonks to analyze market trends.
    Args:
        fixture_id: The ID of the match.
        market_id: Optional specific market ID (e.g. 1 for 1x2) to filter.
    """
    return await handle_api_call("Sportmonks", get_sportmonks().get_prematch_odds_by_fixture(fixture_id, include="bookmaker,market"))

async def sportmonks_get_head_to_head(team1_id: int, team2_id: int, include: Optional[str] = None) -> Any:
    """Get Head-to-Head (H2H) fixtures between two teams from Sportmonks."""
    return await handle_api_call("Sportmonks", get_sportmonks().get_head_to_head(team1_id, team2_id, include))

async def sportmonks_get_standings(season_id: int, include: Optional[str] = None) -> Any:
    """Get league standings for a specific season from Sportmonks."""
    return await handle_api_call("Sportmonks", get_sportmonks().get_standings_by_season(season_id, include))

async def sportmonks_get_expected_goals(fixture_id: int) -> Any:
    """Get Expected Goals (xG) depth data for a fixture from Sportmonks."""
    return await handle_api_call("Sportmonks", get_sportmonks().get_expected_goals_by_fixture(fixture_id))

async def sportmonks_get_prematch_odds(fixture_id: int, include: Optional[str] = None) -> Any:
    """Get pre-match odds for a fixture from Sportmonks."""
    return await handle_api_call("Sportmonks", get_sportmonks().get_prematch_odds_by_fixture(fixture_id, include))

async def sportmonks_get_predictions(fixture_id: int) -> Any:
    """Get match predictions (probabilities) for a fixture from Sportmonks."""
    return await handle_api_call("Sportmonks", get_sportmonks().get_predictions_by_fixture(fixture_id))

async def sportmonks_get_value_bets() -> Any:
    """Get currently identified Value Bets from Sportmonks."""
    return await handle_api_call("Sportmonks", get_sportmonks().get_value_bets())



def _normalize_sportmonks_fixtures(raw, league_filter: Optional[str]) -> List[Dict]:
    data = raw.get("data", []) if isinstance(raw, dict) else []
    result = []
    for fix in data:
        if not isinstance(fix, dict):
            continue
        league_name = fix.get("league", {}).get("name", "") if isinstance(fix.get("league"), dict) else ""
        if league_filter and league_filter.lower() not in league_name.lower():
            continue
        participants = fix.get("participants", [])
        home = next((p for p in participants if p.get("meta", {}).get("location") == "home"), {})
        away = next((p for p in participants if p.get("meta", {}).get("location") == "away"), {})
        result.append({
            "home_team": home.get("name", ""),
            "away_team": away.get("name", ""),
            "competition": league_name,
            "kickoff_time": fix.get("starting_at", ""),
            "match_id": str(fix.get("id", "")),
            "home_team_id": str(home.get("id", "")),
            "away_team_id": str(away.get("id", "")),
            "season_id": str(fix.get("season_id", "")),
        })
    return result


def _normalize_footystats_fixtures(raw, league_filter: Optional[str]) -> List[Dict]:
    matches = raw.get("data", []) if isinstance(raw, dict) else []
    result = []
    for m in matches:
        if not isinstance(m, dict):
            continue
        comp_name = m.get("competition_name", "")
        if league_filter and league_filter.lower() not in comp_name.lower():
            continue
        result.append({
            "home_team": m.get("home_name", ""),
            "away_team": m.get("away_name", ""),
            "competition": comp_name,
            "kickoff_time": m.get("date_unix", ""),
            "match_id": str(m.get("id", "")),
            "home_team_id": str(m.get("homeID", "")),
            "away_team_id": str(m.get("awayID", "")),
            "season_id": str(m.get("competition_id", "")),
        })
    return result


async def goalcast_prefetch_today(
    data_provider: str,
    leagues: Optional[List[str]] = None,
    date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    预热今日/指定日期比赛的数据缓存。

    适合在批量分析前调用：并发拉取所有比赛的原始数据，
    写入 data/cache/，后续 goalcast_resolve_match 调用均为缓存命中。

    Args:
        data_provider: "sportmonks" | "footystats"
        leagues:       联赛名列表。为 None 时读取 config/watchlist.yaml。
        date:          YYYY-MM-DD，默认今天

    Returns:
        { matches_found, matches_cached, provider, date, leagues, match_list }
    """
    target_date = date or datetime.date.today().isoformat()

    # 读取 watchlist（未指定 leagues 时使用）
    if leagues is None:
        watchlist_path = Path(__file__).resolve().parent.parent / "config" / "watchlist.yaml"
        if watchlist_path.exists():
            with open(watchlist_path) as f:
                wl = yaml.safe_load(f)
            provider_cfg = wl.get(data_provider, {})
            leagues = [lg["name"] for lg in provider_cfg.get("leagues", [])]
        else:
            leagues = []

    all_matches: List[Dict[str, Any]] = []
    for league in (leagues or [None]):
        try:
            matches = await goalcast_get_todays_matches(
                data_provider=data_provider,
                date=target_date,
                league_filter=league,
            )
            all_matches.extend(m for m in matches if "error" not in m)
        except Exception as exc:
            logger.warning(f"[prefetch] Failed to list {league}: {exc}")

    # 并发预热每场比赛
    async def _prefetch_one(match: Dict[str, Any]) -> bool:
        try:
            await goalcast_resolve_match(
                match_id=match["match_id"],
                fixture_id=match.get("fixture_id") or match["match_id"],
                home_team=match["home_team"],
                home_team_id=match["home_team_id"],
                away_team=match["away_team"],
                away_team_id=match["away_team_id"],
                season_id=match["season_id"],
                league=match["competition"],
                data_provider=data_provider,
                match_date=target_date,
            )
            return True
        except Exception as exc:
            logger.warning(
                f"[prefetch] Failed {match.get('home_team')} vs {match.get('away_team')}: {exc}"
            )
            return False

    results = await asyncio.gather(
        *(_prefetch_one(m) for m in all_matches), return_exceptions=True
    )
    cached_count = sum(1 for r in results if r is True)

    return {
        "matches_found": len(all_matches),
        "matches_cached": cached_count,
        "provider": data_provider,
        "date": target_date,
        "leagues": leagues or [],
        "match_list": [
            {
                "home_team": m["home_team"],
                "away_team": m["away_team"],
                "competition": m["competition"],
                "kickoff_time": m.get("kickoff_time", ""),
            }
            for m in all_matches
        ],
    }


def _sportmonks_available() -> bool:
    """检查 Sportmonks API key 是否已配置。"""
    from config.settings import settings
    return bool(getattr(settings, "SPORTMONKS_API_KEY", ""))



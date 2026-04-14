import asyncio
import datetime
import os
import yaml
from pathlib import Path
from typing import Optional, List, Dict, Any
from mcp.server.fastmcp import FastMCP

from provider.footystats.client import FootyStatsProvider
from provider.sportmonks.client import SportmonksProvider
from provider.understat.client import UnderstatProvider
from analytics.poisson import poisson_distribution, dixon_coles_distribution, calculate_ah_probability
from analytics.ev_calculator import calculate_ev, calculate_kelly, calculate_risk_adjusted_ev, best_bet_recommendation
from analytics.confidence import calculate_confidence, calculate_confidence_v25, confidence_breakdown
from utils.logger import logger
from data_strategy.fusion import DataFusion
from data_strategy.resolvers.sportmonks_resolver import SportmonksResolver
from data_strategy.sportmonks.models import SportmonksMatchData

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


# ─── V4.0 专用工具：数据获取（直连 SportmonksResolver，跳过 DataFusion）────

# Sportmonks 联赛名称 → 名称匹配关键词（子字符串，不区分大小写）
# 用于 goalcast_sm_get_fixtures 的联赛过滤
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
    """从比赛日期推断 Understat 赛季年份（赛季跨年取后一年）。"""
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
                stat = {d["type"]["name"]: d["value"] for d in details if isinstance(d, dict) and "type" in d and "value" in d}
                return {
                    "position": entry.get("position"),
                    "points": stat.get("Points"),
                    "wins": stat.get("Won"),
                    "draws": stat.get("Draw"),
                    "losses": stat.get("Lost"),
                    "goals_for": stat.get("Goals For"),
                    "goals_against": stat.get("Goals Against"),
                    "goal_difference": stat.get("Goal Difference"),
                    "matches_played": stat.get("Matches Played"),
                }
    except Exception:
        pass
    return None


@mcp.tool()
async def goalcast_sm_get_fixtures(
    leagues: List[str],
    date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    V4.0 专用：获取指定日期在目标联赛的所有比赛。

    一次调用返回多联赛赛程，每条记录包含 goalcast_sm_fetch 所需的全部 ID。
    内置联赛名称过滤，支持常见写法（不区分大小写子字符串匹配）。

    Args:
        leagues: 联赛名称列表，如 ["Premier League", "Championship", "Serie A"]
                 支持的名称见 _SM_LEAGUE_KEYWORDS 映射。
        date:    YYYY-MM-DD，默认今天。

    Returns:
        {
          "date": "YYYY-MM-DD",
          "count": N,
          "fixtures": [
            {
              "fixture_id": int,
              "home_team": str,  "home_team_id": int,
              "away_team": str,  "away_team_id": int,
              "season_id": int,
              "league": str,
              "kickoff_time": str,   # ISO 字符串
            }, ...
          ]
        }
    """
    target_date = date or datetime.date.today().isoformat()
    sm = get_sportmonks()

    try:
        raw = await sm.get_fixtures_by_date(
            target_date,
            include="participants;league;season",
        )
    except Exception as exc:
        logger.error(f"[goalcast_sm_get_fixtures] API error: {exc}")
        return {"error": str(exc), "date": target_date, "count": 0, "fixtures": []}

    # 构建目标关键词集合（全部小写）
    target_keywords: List[str] = []
    for league_name in leagues:
        kws = _SM_LEAGUE_KEYWORDS.get(league_name)
        if kws:
            target_keywords.extend(kws)
        else:
            target_keywords.append(league_name.lower())

    fixtures = []
    for fix in raw.get("data", []):
        if not isinstance(fix, dict):
            continue

        league_obj = fix.get("league") or {}
        league_name = league_obj.get("name", "") if isinstance(league_obj, dict) else ""
        league_name_lower = league_name.lower()

        # 联赛过滤
        if not any(kw in league_name_lower for kw in target_keywords):
            continue

        participants = fix.get("participants", [])
        home = next((p for p in participants if isinstance(p, dict) and
                     p.get("meta", {}).get("location") == "home"), {})
        away = next((p for p in participants if isinstance(p, dict) and
                     p.get("meta", {}).get("location") == "away"), {})

        if not home or not away:
            continue

        fixtures.append({
            "fixture_id":   fix.get("id"),
            "home_team":    home.get("name", ""),
            "home_team_id": home.get("id"),
            "away_team":    away.get("name", ""),
            "away_team_id": away.get("id"),
            "season_id":    fix.get("season_id"),
            "league":       league_name,
            "kickoff_time": fix.get("starting_at", ""),
        })

    return {"date": target_date, "count": len(fixtures), "fixtures": fixtures}


@mcp.tool()
async def goalcast_sm_fetch(
    fixture_id: int,
    home_team: str,
    home_team_id: int,
    away_team: str,
    away_team_id: int,
    season_id: int,
    league: str,
    match_date: str,
    season: Optional[str] = None,
) -> Dict[str, Any]:
    """
    V4.0 专用数据获取。直连 SportmonksResolver，完全跳过 DataFusion。

    并行拉取单场比赛的全部 V4.0 所需数据，返回 SportmonksMatchData 序列化字典。
    Sportmonks 专有字段（亚盘、赔率时序、官方预测、原生 xG）原生保留，不经归一化。

    Args:
        fixture_id:    Sportmonks fixture ID（来自 goalcast_sm_get_fixtures）
        home_team:     主队名称
        home_team_id:  主队 Sportmonks ID
        away_team:     客队名称
        away_team_id:  客队 Sportmonks ID
        season_id:     Sportmonks season ID
        league:        联赛名（如 "Premier League"）
        match_date:    YYYY-MM-DD
        season:        Understat 赛季年（如 "2025"）；不传时从 match_date 自动推断

    Returns:
        SportmonksMatchData.to_dict() — V4.0 九层分析直接消费的数据结构
    """
    sm = get_sportmonks()
    us = get_understat()
    resolver = SportmonksResolver(sm, us)
    effective_season = season or _infer_season(match_date)
    fixture_id_str = str(fixture_id)
    home_id_str    = str(home_team_id)
    away_id_str    = str(away_team_id)
    season_id_str  = str(season_id)

    # ── 并行拉取所有数据层 ────────────────────────────────────────
    results = await asyncio.gather(
        resolver.resolve_xg(
            home_team, away_team, league, effective_season,
            home_id_str, away_id_str,
        ),
        resolver.resolve_standings(season_id_str),
        resolver.resolve_odds(fixture_id_str),
        resolver.resolve_odds_movement(fixture_id_str),
        resolver.resolve_lineups(fixture_id_str, home_id_str, away_id_str),
        resolver.resolve_head_to_head(home_id_str, away_id_str),
        resolver.resolve_predictions(fixture_id_str),
        return_exceptions=True,
    )
    xg_r, standings_r, odds_r, odds_mv_r, lineups_r, h2h_r, pred_r = results

    # ── xG ───────────────────────────────────────────────────────
    xg_data = xg_r.data if not isinstance(xg_r, Exception) and xg_r.data else {}
    xg_source  = xg_r.source  if not isinstance(xg_r, Exception) else "league_avg"
    xg_quality = xg_r.quality if not isinstance(xg_r, Exception) else 0.35

    # ── 积分榜（主客分别提取）───────────────────────────────────
    home_standing = None
    away_standing = None
    if not isinstance(standings_r, Exception) and standings_r.data:
        raw_std = standings_r.data.get("raw", {})
        home_standing = _extract_standing_for_team(raw_std, home_team_id)
        away_standing = _extract_standing_for_team(raw_std, away_team_id)

    # ── 赔率（1X2 + 亚盘）──────────────────────────────────────
    odds_data = odds_r.data if not isinstance(odds_r, Exception) else {}
    odds_mv   = odds_mv_r.data.get("movements") if (
        not isinstance(odds_mv_r, Exception) and odds_mv_r.data
    ) else None

    # ── 阵容 ─────────────────────────────────────────────────────
    lineups_data = lineups_r.data if not isinstance(lineups_r, Exception) else None

    # ── H2H ──────────────────────────────────────────────────────
    h2h_data = h2h_r.data if not isinstance(h2h_r, Exception) else None

    # ── 官方预测 ─────────────────────────────────────────────────
    pred_data = pred_r.data if not isinstance(pred_r, Exception) else None

    # ── data_gaps ────────────────────────────────────────────────
    data_gaps: List[str] = []
    if xg_source == "league_avg":      data_gaps.append("xg")
    if home_standing is None:          data_gaps.append("standings")
    if not odds_data:                  data_gaps.append("odds")
    if odds_mv is None:                data_gaps.append("odds_movement")
    if lineups_data is None:           data_gaps.append("lineups")
    if h2h_data is None:               data_gaps.append("h2h")
    if pred_data is None:              data_gaps.append("predictions")

    # ── 综合质量评分（简化：各层质量加权均值）────────────────────
    qualities = [xg_quality]
    if home_standing:  qualities.append(0.80)
    if odds_data:      qualities.append(odds_r.quality if not isinstance(odds_r, Exception) else 0.0)
    if odds_mv:        qualities.append(0.85)
    if lineups_data:   qualities.append(0.90)
    overall_quality = sum(qualities) / len(qualities) if qualities else 0.35

    match_data = SportmonksMatchData(
        fixture_id    = fixture_id,
        home_team     = home_team,
        away_team     = away_team,
        home_team_id  = home_team_id,
        away_team_id  = away_team_id,
        league        = league,
        season_id     = season_id,
        season        = effective_season,
        match_date    = match_date,
        kickoff_time  = "",  # 由 goalcast_sm_get_fixtures 提供，此处无需重复
        # xG
        xg_home_for     = float(xg_data.get("home_xg_for", 0.0) or 0.0),
        xg_home_against = float(xg_data.get("home_xg_against", 0.0) or 0.0),
        xg_away_for     = float(xg_data.get("away_xg_for", 0.0) or 0.0),
        xg_away_against = float(xg_data.get("away_xg_against", 0.0) or 0.0),
        xg_source       = xg_source,
        xg_quality      = xg_quality,
        # 积分榜
        home_standing = home_standing,
        away_standing = away_standing,
        # 欧盘
        odds_home_win = odds_data.get("home_win"),
        odds_draw     = odds_data.get("draw"),
        odds_away_win = odds_data.get("away_win"),
        odds_bookmaker = odds_data.get("bookmaker"),
        # 亚盘（Sportmonks 专有，完整保留）
        ah_line       = odds_data.get("ah_line"),
        ah_home_odds  = odds_data.get("ah_home_odds"),
        ah_away_odds  = odds_data.get("ah_away_odds"),
        # 赔率时序
        odds_movement = odds_mv,
        # 阵容
        lineups       = lineups_data,
        # H2H
        h2h           = h2h_data,
        # 官方预测
        predictions   = pred_data,
        # 质量
        overall_quality = round(overall_quality, 3),
        data_gaps       = data_gaps,
    )

    return match_data.to_dict()


# ─── Quantitative Model Tools (Poisson, EV, Kelly, Confidence) ──────────

@mcp.tool()
async def goalcast_calculate_poisson(
    home_lambda: float,
    away_lambda: float,
    max_goals: int = 6,
    model: str = "standard",
    rho: float = -0.13,
) -> Any:
    """Calculate score probability matrix using Poisson or Dixon-Coles distribution.

    Args:
        home_lambda: Expected goals for home team (λ)
        away_lambda: Expected goals for away team (λ)
        max_goals: Maximum goals to model per side (default 6, covers 0-6)
        model: "standard" (v2.5) or "dixon_coles" (v3.0)
        rho: Dixon-Coles correction parameter (default -0.13, only used for dixon_coles)

    Returns:
        Score probability matrix with:
        - score_matrix: 2D array P(home_goals × away_goals)
        - home_win_pct / draw_pct / away_win_pct
        - top_scores: Top 5 most likely scorelines
        - over_25_pct / btts_pct
    """
    try:
        if model == "dixon_coles":
            result = dixon_coles_distribution(home_lambda, away_lambda, max_goals, rho)
        else:
            result = poisson_distribution(home_lambda, away_lambda, max_goals)
        return result
    except Exception as e:
        return {"error": "POISSON_CALC_ERROR", "message": str(e)}


@mcp.tool()
async def goalcast_calculate_ah_prob(
    score_matrix: list,
    ah_line: float,
) -> Any:
    """Calculate Asian Handicap coverage probability from a Poisson/Dixon-Coles score matrix.

    Derives the probability that each side covers the Asian Handicap line by summing
    the relevant cells of the score matrix returned by goalcast_calculate_poisson.

    Supports all standard AH line types:
      - Half-ball (±0.5, ±1.5, …): no push possible
      - Whole-ball (0, ±1, ±2, …): push (refund) possible on exact margin
      - Quarter-ball (±0.25, ±0.75, …): stake split across two adjacent lines

    Args:
        score_matrix: 2D list from goalcast_calculate_poisson result["score_matrix"].
                      matrix[i][j] = P(home=i goals, away=j goals).
        ah_line:      Home team handicap line.
                      Negative = home gives goals (e.g. -0.5 = home -½).
                      Positive = home receives goals (e.g. +0.5 = home +½).

    Returns:
        {
          "ah_line": float,
          "p_home_cover": float,    # raw probability (0-1)
          "p_away_cover": float,
          "p_push": float,          # refund probability (whole-ball lines only)
          "p_home_cover_pct": float,
          "p_away_cover_pct": float,
          "p_push_pct": float,
          "ah_type": "half" | "whole" | "quarter"
        }
    """
    try:
        return calculate_ah_probability(score_matrix, ah_line)
    except Exception as e:
        return {"error": "AH_PROB_CALC_ERROR", "message": str(e)}


@mcp.tool()
async def goalcast_calculate_ev(
    model_probability: float,
    market_odds: float,
) -> Any:
    """Calculate Expected Value for a single direction.

    EV = (model_probability / 100) × market_odds - 1

    Args:
        model_probability: Model's probability as percentage (0-100)
        market_odds: Decimal odds from bookmaker (e.g., 1.85, 3.50)

    Returns:
        EV calculation with break-even odds and value flag.
    """
    try:
        return calculate_ev(model_probability, market_odds)
    except Exception as e:
        return {"error": "EV_CALC_ERROR", "message": str(e)}


@mcp.tool()
async def goalcast_calculate_kelly(
    model_probability: float,
    market_odds: float,
    fraction: float = 0.25,
    bankroll: float = None,
) -> Any:
    """Calculate Kelly Criterion stake recommendation.

    f* = (b × p - q) / b where b = odds - 1, p = probability, q = 1 - p

    Args:
        model_probability: Model's probability as percentage (0-100)
        market_odds: Decimal odds
        fraction: Fraction of full Kelly (default 0.25 = quarter Kelly)
        bankroll: Optional total bankroll for absolute stake amount

    Returns:
        Kelly percentage and stake recommendation.
    """
    try:
        return calculate_kelly(model_probability, market_odds, fraction, bankroll)
    except Exception as e:
        return {"error": "KELLY_CALC_ERROR", "message": str(e)}


@mcp.tool()
async def goalcast_calculate_risk_adjusted_ev(
    raw_ev: float,
    lineup_uncertainty: bool = False,
    market_low_confidence: bool = False,
    data_quality: str = "medium",
) -> Any:
    """Calculate risk-adjusted EV by applying multiplicative risk factors.

    Risk multipliers:
    - lineup_uncertainty: × 0.85
    - market_low_confidence: × 0.90
    - data_quality=low: × 0.80

    Args:
        raw_ev: Raw expected value
        lineup_uncertainty: True if lineup data unavailable
        market_low_confidence: True if market analysis low confidence
        data_quality: "low", "medium", or "high"

    Returns:
        Risk-adjusted EV value.
    """
    try:
        ev_adj = calculate_risk_adjusted_ev(raw_ev, lineup_uncertainty, market_low_confidence, data_quality)
        return {"raw_ev": raw_ev, "risk_adjusted_ev": ev_adj, "recommendation": "bet" if ev_adj > 0.05 else "no_bet"}
    except Exception as e:
        return {"error": "RISK_EV_CALC_ERROR", "message": str(e)}


@mcp.tool()
async def goalcast_calculate_confidence(
    method: str = "v3.0",
    base_score: int = 70,
    market_agrees: bool = False,
    data_complete: bool = False,
    understat_available: bool = False,
    odds_available: bool = False,
    lineup_unavailable: bool = True,
    xG_proxy_used: bool = False,
    market_disagrees: bool = False,
    data_quality_low: bool = False,
    understat_failed: bool = False,
    match_type_c: bool = False,
    major_uncertainty: bool = False,
    market_downgraded: bool = False,
    prediction_diverged: bool = False,
) -> Any:
    """Calculate confidence score for a match prediction.

    Args:
        method: "v2.5" or "v3.0" or "v4.0" (affects weighting)
        base_score: Starting confidence (default 70)
        market_agrees: Market direction agrees with model
        data_complete: Both teams have recent form data
        understat_available: Direct xG from Understat available
        odds_available: Valid odds data available
        lineup_unavailable: Lineup data missing (expected, default True)
        xG_proxy_used: Using proxy instead of direct xG
        market_disagrees: Market odds contradict model
        data_quality_low: Form data unavailable
        understat_failed: Understat match lookup failed
        match_type_c: Type C match (second leg)
        major_uncertainty: Major pre-match uncertainty
        market_downgraded: Market layer downgraded
        prediction_diverged: Sportmonks prediction significantly diverges from model

    Returns:
        Confidence score [30-90] with detailed breakdown.
    """
    try:
        kwargs = {
            "base_score": base_score,
            "market_agrees": market_agrees,
            "data_complete": data_complete,
            "understat_available": understat_available,
            "odds_available": odds_available,
            "lineup_unavailable": lineup_unavailable,
            "xG_proxy_used": xG_proxy_used,
            "market_disagrees": market_disagrees,
            "data_quality_low": data_quality_low,
            "understat_failed": understat_failed,
            "match_type_c": match_type_c,
            "major_uncertainty": major_uncertainty,
            "market_downgraded": market_downgraded,
            "prediction_diverged": prediction_diverged,
        }

        if method == "v2.5":
            final = calculate_confidence_v25(**kwargs)
        else:
            final = calculate_confidence(**kwargs)

        breakdown = confidence_breakdown(**kwargs)
        return {"confidence": final, "breakdown": breakdown}
    except Exception as e:
        return {"error": "CONFIDENCE_CALC_ERROR", "message": str(e)}


# ── 数据策略层：单一入口工具 ──────────────────────────────────

@mcp.tool()
async def goalcast_resolve_match(
    match_id: str,
    home_team: str,
    home_team_id: str,
    away_team: str,
    away_team_id: str,
    season_id: str,
    league: str,
    match_date: Optional[str] = None,
    season: Optional[str] = None,
    data_provider: str = "footystats",
    fixture_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    数据策略层核心工具：并行采集并融合单场比赛所需的全部数据，
    返回结构化的 MatchContext 字典。

    Skill 应优先调用此工具（而非逐一调用 provider 工具），
    自动处理数据来源选择、fallback 链、缓存和质量评分。

    Args:
        match_id:      FootyStats 比赛 ID（Step 1 从 get_todays_matches 提取）
        home_team:     主队名称（如 "Arsenal"）
        home_team_id:  FootyStats 主队 ID（homeID 字段）
        away_team:     客队名称（如 "Chelsea"）
        away_team_id:  FootyStats 客队 ID（awayID 字段）
        season_id:     FootyStats competition/season ID（competition_id 字段，用于积分榜）
        league:        联赛名（如 "Premier League"，用于 Understat 映射 + 联赛参数）
        match_date:    比赛日期 YYYY-MM-DD（可选，帮助推断 Understat 赛季）
        season:        Understat 赛季年份（如 "2025"），不传时自动从 match_date 推断
        data_provider: 数据提供商，"footystats"（默认）或 "sportmonks"
        fixture_id:    Sportmonks fixture ID（当 data_provider="sportmonks" 时使用）；
                       不传时回退到 match_id

    Returns:
        MatchContext 序列化字典，包含以下顶层字段：
        - match_id, league, home_team, away_team, match_date
        - xg: {home_xg_for, home_xg_against, away_xg_for, away_xg_against, source, quality}
        - home_form_5 / home_form_10 / away_form_5 / away_form_10: 近况统计窗口
        - home_standing / away_standing: 积分榜状态
        - odds: {home_win, draw, away_win, source, quality}
        - data_gaps: 缺失数据项列表（如 ["lineups", "injuries", "odds_movement"]）
        - overall_quality: 综合质量评分 0.0–1.0
        - sources: 各层数据来源字典

    数据策略（自动处理，Skill 无需关心）：
        xG    : Understat 球队统计（6 大联赛）→ FootyStats 近况代理 → 联赛均值
        近况   : FootyStats get_team_last_x_stats（主/客并行）
        积分榜  : FootyStats get_league_tables → Sportmonks get_standings
        赔率   : FootyStats match_details → Sportmonks prematch_odds
        伤停/阵容: v1 标注缺失（data_gaps 中可见）
    """
    try:
        effective_fixture_id = fixture_id or match_id
        sportmonks = get_sportmonks() if data_provider == "sportmonks" else None

        fusion = DataFusion(
            data_provider=data_provider,
            footystats=get_footystats(),
            understat=get_understat(),
            sportmonks=sportmonks,
        )
        ctx = await fusion.build(
            fixture_id=str(effective_fixture_id),
            match_id=str(match_id),
            home_team=home_team,
            home_team_id=str(home_team_id),
            away_team=away_team,
            away_team_id=str(away_team_id),
            season_id=str(season_id),
            league=league,
            match_date=match_date,
            season=season,
        )
        return ctx.to_dict()
    except Exception as exc:
        logger.error(f"[goalcast_resolve_match] {exc}")
        return {
            "error": "RESOLVE_ERROR",
            "message": str(exc),
            "match_id": match_id,
            "home_team": home_team,
            "away_team": away_team,
        }


@mcp.tool()
async def goalcast_get_todays_matches(
    data_provider: str,
    date: Optional[str] = None,
    league_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    通过指定 data_provider 获取今日/指定日期的比赛列表。
    返回标准化 MatchSummary 列表，字段与 provider 无关。

    Args:
        data_provider: "sportmonks" | "footystats"
        date:          YYYY-MM-DD，默认今天
        league_filter: 联赛名过滤（子字符串匹配，不区分大小写）

    Returns:
        [{ home_team, away_team, competition, kickoff_time,
           match_id, home_team_id, away_team_id, season_id }, ...]
    """
    target_date = date or datetime.date.today().isoformat()

    try:
        if data_provider == "sportmonks":
            raw = await handle_api_call(
                "Sportmonks",
                get_sportmonks().get_fixtures_by_date(
                    target_date,
                    include="participants;scores;league;season",
                ),
            )
            return _normalize_sportmonks_fixtures(raw, league_filter)

        elif data_provider == "footystats":
            raw = await handle_api_call(
                "FootyStats",
                get_footystats().get_todays_matches(target_date, timezone=None),
            )
            return _normalize_footystats_fixtures(raw, league_filter)

        else:
            return [{"error": f"Unknown data_provider: {data_provider}"}]

    except Exception as exc:
        logger.error(f"[goalcast_get_todays_matches] {exc}")
        return [{"error": str(exc)}]


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


if __name__ == "__main__":
    import os
    import sys
    # Default to stdio for local use, but support SSE for remote/Docker.
    # FastMCP reads host/port from FASTMCP_HOST / FASTMCP_PORT env vars.
    # Defaults: FASTMCP_HOST=0.0.0.0, FASTMCP_PORT=8000 for SSE mode.
    if len(sys.argv) > 1 and sys.argv[1] == "sse":
        mcp.run(transport="sse")
    else:
        mcp.run()

import asyncio
import os
from typing import Optional, List, Dict, Any
from mcp.server.fastmcp import FastMCP

from provider.footystats.client import FootyStatsProvider
from provider.sportmonks.client import SportmonksProvider
from provider.understat.client import UnderstatProvider
from utils.logger import logger

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

@mcp.tool()
async def footystats_get_league_list(chosen_leagues_only: bool = False, country: Optional[int] = None) -> Any:
    """Get list of available leagues from FootyStats.
    Args:
        chosen_leagues_only: Whether to only return chosen leagues.
        country: Country ISO ID to filter leagues.
    """
    return await handle_api_call("FootyStats", get_footystats().get_league_list(chosen_leagues_only, country))

@mcp.tool()
async def footystats_get_country_list() -> Any:
    """Get list of all countries and their ISO IDs from FootyStats."""
    return await handle_api_call("FootyStats", get_footystats().get_country_list())

@mcp.tool()
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

@mcp.tool()
async def footystats_get_league_stats(season_id: int) -> Any:
    """Get detailed statistics for a league season from FootyStats."""
    return await handle_api_call("FootyStats", get_footystats().get_league_stats(season_id))

@mcp.tool()
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

@mcp.tool()
async def footystats_get_league_teams(season_id: int) -> Any:
    """Get all teams and their stats for a league season from FootyStats."""
    return await handle_api_call("FootyStats", get_footystats().get_league_teams(season_id))

@mcp.tool()
async def footystats_get_league_tables(season_id: int) -> Any:
    """Get standings table for a specific league season from FootyStats."""
    return await handle_api_call("FootyStats", get_footystats().get_league_tables(season_id))

@mcp.tool()
async def footystats_get_match_details(match_id: int) -> Any:
    """Get detailed statistics, H2H, lineups, and odds for a specific match from FootyStats.
    Includes team stats, goal timings, and starting 11 if available.
    """
    return await handle_api_call("FootyStats", get_footystats().get_match_details(match_id))

@mcp.tool()
async def footystats_get_lineups(match_id: int) -> Any:
    """Get starting lineups and substitutes for a match from FootyStats."""
    return await handle_api_call("FootyStats", get_footystats().get_match_details(match_id))

@mcp.tool()
async def footystats_get_team_details(team_id: int) -> Any:
    """Get complete statistics for a specific team from FootyStats."""
    return await handle_api_call("FootyStats", get_footystats().get_team(team_id))

@mcp.tool()
async def footystats_get_team_last_x_stats(team_id: int) -> Any:
    """Get recent form statistics (last 5/6/10) for a specific team from FootyStats."""
    return await handle_api_call("FootyStats", get_footystats().get_team_last_x_stats(team_id))

@mcp.tool()
async def footystats_get_btts_stats() -> Any:
    """Get top teams and fixtures for BTTS (Both Teams To Score) from FootyStats."""
    return await handle_api_call("FootyStats", get_footystats().get_btts_stats())

@mcp.tool()
async def footystats_get_over25_stats() -> Any:
    """Get top teams and fixtures for Over 2.5 Goals from FootyStats."""
    return await handle_api_call("FootyStats", get_footystats().get_over_2_5_stats())


# --- Understat Tools ---
# Advanced football statistics (xG, xA) - Free, no API key required

@mcp.tool()
async def understat_get_league_players(league: str, season: str) -> Any:
    """Get player statistics for a league season from Understat.
    
    Provides advanced metrics including xG (Expected Goals), xA (Expected Assists),
    shots, key passes, and more.
    
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


@mcp.tool()
async def understat_get_league_teams(league: str, season: str) -> Any:
    """Get team list for a league season from Understat.
    
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


@mcp.tool()
async def understat_get_league_matches(league: str, season: str) -> Any:
    """Get match results for a league season from Understat.
    
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


@mcp.tool()
async def understat_get_match_stats(match_id: int) -> Any:
    """Get detailed match statistics including shots and player performance.
    
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


@mcp.tool()
async def understat_get_team_stats(team_id: int, season: str) -> Any:
    """Get team statistics for a specific season.
    
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


@mcp.tool()
async def understat_get_player_stats(player_id: int) -> Any:
    """Get detailed player statistics across all seasons.
    
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


@mcp.tool()
async def understat_get_player_shots(player_id: int) -> Any:
    """Get all shots for a specific player.
    
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

@mcp.tool()
async def sportmonks_get_livescores(include: Optional[str] = "events,lineups,statistics") -> Any:
    """Get current live scores from Sportmonks with default inclusions.
    Args:
        include: Relationships to include (default: 'events,lineups,statistics').
    """
    return await handle_api_call("Sportmonks", get_sportmonks().get_livescores(include))

@mcp.tool()
async def sportmonks_get_fixtures_by_date(date: str, include: Optional[str] = "league,participants") -> Any:
    """Get fixtures for a specific date from Sportmonks.
    Args:
        date: Date in YYYY-MM-DD format.
        include: Relationships to include (default: 'league,participants').
    """
    return await handle_api_call("Sportmonks", get_sportmonks().get_fixtures_by_date(date, include))

@mcp.tool()
async def sportmonks_get_fixture_by_id(fixture_id: int, include: Optional[str] = None) -> Any:
    """Get detailed fixture information by ID from Sportmonks."""
    return await handle_api_call("Sportmonks", get_sportmonks().get_fixture_by_id(fixture_id, include))

@mcp.tool()
async def sportmonks_get_lineups(fixture_id: int) -> Any:
    """Get detailed starting lineups, substitutes, and formations for a fixture from Sportmonks.
    Includes player names, positions, and ratings.
    """
    return await handle_api_call("Sportmonks", get_sportmonks().get_fixture_by_id(fixture_id, include="lineups.player,formations"))

@mcp.tool()
async def sportmonks_get_player_stats(fixture_id: int) -> Any:
    """Get individual player performance statistics for a specific fixture from Sportmonks.
    Includes passes, shots, tackles, etc., for each player.
    """
    return await handle_api_call("Sportmonks", get_sportmonks().get_fixture_by_id(fixture_id, include="statistics.player"))

@mcp.tool()
async def sportmonks_get_odds_movement(fixture_id: int, market_id: Optional[int] = None) -> Any:
    """Get historical odds movements for a fixture from Sportmonks to analyze market trends.
    Args:
        fixture_id: The ID of the match.
        market_id: Optional specific market ID (e.g. 1 for 1x2) to filter.
    """
    return await handle_api_call("Sportmonks", get_sportmonks().get_prematch_odds_by_fixture(fixture_id, include="bookmaker,market"))

@mcp.tool()
async def sportmonks_get_head_to_head(team1_id: int, team2_id: int, include: Optional[str] = None) -> Any:
    """Get Head-to-Head (H2H) fixtures between two teams from Sportmonks."""
    return await handle_api_call("Sportmonks", get_sportmonks().get_head_to_head(team1_id, team2_id, include))

@mcp.tool()
async def sportmonks_get_standings(season_id: int, include: Optional[str] = None) -> Any:
    """Get league standings for a specific season from Sportmonks."""
    return await handle_api_call("Sportmonks", get_sportmonks().get_standings_by_season(season_id, include))

@mcp.tool()
async def sportmonks_get_expected_goals(fixture_id: int) -> Any:
    """Get Expected Goals (xG) depth data for a fixture from Sportmonks."""
    return await handle_api_call("Sportmonks", get_sportmonks().get_expected_goals_by_fixture(fixture_id))

@mcp.tool()
async def sportmonks_get_prematch_odds(fixture_id: int, include: Optional[str] = None) -> Any:
    """Get pre-match odds for a fixture from Sportmonks."""
    return await handle_api_call("Sportmonks", get_sportmonks().get_prematch_odds_by_fixture(fixture_id, include))

@mcp.tool()
async def sportmonks_get_predictions(fixture_id: int) -> Any:
    """Get match predictions (probabilities) for a fixture from Sportmonks."""
    return await handle_api_call("Sportmonks", get_sportmonks().get_predictions_by_fixture(fixture_id))

@mcp.tool()
async def sportmonks_get_value_bets() -> Any:
    """Get currently identified Value Bets from Sportmonks."""
    return await handle_api_call("Sportmonks", get_sportmonks().get_value_bets())

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

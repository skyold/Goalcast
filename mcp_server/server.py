import asyncio
from typing import Optional, List, Dict, Any
from mcp.server.fastmcp import FastMCP

from provider.footystats.client import FootyStatsProvider
from provider.sportmonks.client import SportmonksProvider
from utils.logger import logger

# Initialize FastMCP server
mcp = FastMCP("Goalcast Data Providers")

# Initialize providers
# Using lazy initialization to ensure the providers are only created when needed
# or during the server startup.
_footystats = None
_sportmonks = None

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
async def footystats_get_todays_matches(date: Optional[str] = None, timezone: Optional[str] = None) -> Any:
    """Get matches for a specific date from FootyStats.
    Args:
        date: Date in YYYY-MM-DD format. Defaults to today.
        timezone: Timezone for match times (e.g. 'Europe/London').
    """
    return await handle_api_call("FootyStats", get_footystats().get_todays_matches(date, timezone))

@mcp.tool()
async def footystats_get_league_stats(season_id: int) -> Any:
    """Get detailed statistics for a league season from FootyStats."""
    return await handle_api_call("FootyStats", get_footystats().get_league_stats(season_id))

@mcp.tool()
async def footystats_get_league_matches(season_id: int, page: int = 1) -> Any:
    """Get all matches for a specific league season from FootyStats."""
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
        os.environ.setdefault("FASTMCP_HOST", "0.0.0.0")
        os.environ.setdefault("FASTMCP_PORT", "8000")
        mcp.run(transport="sse")
    else:
        mcp.run()

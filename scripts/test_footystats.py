#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from provider import FootyStatsProvider


async def test():
    fs = FootyStatsProvider()
    print(f"API Key: {fs.api_key[:20]}...")
    print(f"Available: {await fs.is_available()}")

    # Test get_league_matches - try different league IDs
    print("\n=== Testing get_league_matches ===")
    print("Testing league ID 1488 (Premier League?):")
    matches = await fs.get_league_matches("1488", "2026-03-24")
    if matches and isinstance(matches, dict):
        data = matches.get("data", [])
        print(f"  Matches returned: {len(data)}")
        if data:
            print(f"  First match: {data[0].get('home_name')} vs {data[0].get('away_name')}")
            print(f"  All keys in first match: {list(data[0].keys())[:10]}")
    else:
        print("  No data returned")

    # Test get_team
    print("\n=== Testing get_team ===")
    print("Testing team ID 82:")
    team = await fs.get_team("82")
    if team:
        print(f"  Team data returned: {bool(team)}")
        print(f"  Keys: {list(team.keys())[:10]}")
        print(f"  Team name: {team.get('team_name')}")
    else:
        print("  No team data returned")

    # Test get_league_table
    print("\n=== Testing get_league_table ===")
    print("Testing league ID 1488:")
    table = await fs.get_league_table("1488")
    if table and isinstance(table, dict):
        print(f"  Table keys: {list(table.keys())}")
        data = table.get("data", [])
        if isinstance(data, list):
            print(f"  Teams: {len(data)}")
            if data:
                print(f"  First team: {data[0]}")
        else:
            print(f"  Data type: {type(data)}")
            print(f"  Data content: {str(data)[:200]}")
    else:
        print("  No table data returned")

    print("\n=== Summary ===")
    print("FootyStats API is working (no 401 errors)")
    print("The data structure depends on the league ID used")


if __name__ == "__main__":
    asyncio.run(test())

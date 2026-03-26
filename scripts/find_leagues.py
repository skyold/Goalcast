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

    print("=== ID 10 Analysis (380 matches - likely Premier League) ===")
    result = await fs.get_league_table("10")
    if result and result.get('data'):
        data = result['data']
        teams = data.get('league_table', [])
        if teams:
            print(f"\nFirst team raw data (all keys):")
            first_team = teams[0]
            print(f"Keys: {list(first_team.keys())}")
            for k, v in first_team.items():
                print(f"  {k}: {v}")

    print("\n" + "="*50)
    print("=== Checking matches to get team names ===")
    matches = await fs.get_league_matches("10", "2026-03-24")
    if matches and matches.get('data'):
        data = matches.get('data', [])
        print(f"\nFirst match raw data (all keys):")
        first_match = data[0]
        print(f"Keys: {list(first_match.keys())}")
        for k, v in first_match.items():
            print(f"  {k}: {v}")

    print("\n" + "="*50)
    print("=== Summary of available leagues ===")
    test_ids = ['3', '4', '5', '7', '9', '10', '11', '12', '13', '14', '17', '19', '20']
    for league_id in test_ids:
        try:
            result = await fs.get_league_table(league_id)
            if result and result.get('data'):
                data = result['data']
                teams = data.get('league_table', [])
                matches = await fs.get_league_matches(league_id, "2026-03-24")
                match_count = len(matches.get('data', [])) if matches else 0
                print(f"ID {league_id}: {len(teams)} teams, {match_count} matches on 2026-03-24")
        except Exception as e:
            print(f"ID {league_id}: Error - {e}")


if __name__ == "__main__":
    asyncio.run(test())

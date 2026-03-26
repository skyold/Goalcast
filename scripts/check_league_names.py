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

    test_ids = ['9', '10', '11', '12']

    for league_id in test_ids:
        print(f"\n=== League ID: {league_id} ===")
        result = await fs.get_league_table(league_id)
        if result and result.get('data'):
            data = result['data']
            print(f"Top-level keys: {list(data.keys())}")

            for key in ['league_name', 'name', 'competition', 'league', 'title', 'country']:
                if key in data and data[key]:
                    print(f"  {key}: {data[key]}")

            if 'league_table' in data and data['league_table']:
                first_team = data['league_table'][0]
                if 'country' in first_team:
                    print(f"  team country: {first_team.get('country')}")

            matches = await fs.get_league_matches(league_id, "2016-05-15")
            if matches and matches.get('data'):
                first_match = matches['data'][0]
                print(f"  Sample match: {first_match.get('home_name')} vs {first_match.get('away_name')}")


if __name__ == "__main__":
    asyncio.run(test())

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

    # Test various IDs to find the top leagues
    test_ids = ['9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20']

    print("Finding top European leagues:")
    print("=" * 60)

    for league_id in test_ids:
        result = await fs.get_league_table(league_id)
        if result and result.get('data'):
            data = result['data']
            teams = data.get('league_table', [])
            if teams and len(teams) >= 18:
                # Get sample match to identify league
                matches = await fs.get_league_matches(league_id, "2016-05-15")
                sample = ""
                if matches and matches.get('data'):
                    match_data = matches['data'][0]
                    sample = f"{match_data.get('home_name')} vs {match_data.get('away_name')}"

                league_name = "Unknown"
                country = teams[0].get('country', 'unknown') if teams else 'unknown'

                # Guess based on team count and country
                if country == 'england' and len(teams) == 20:
                    if 'Leicester' in str(teams[0]) or 'Manchester' in sample:
                        league_name = "Premier League"
                    else:
                        league_name = "Championship"
                elif country == 'spain' and len(teams) == 20:
                    league_name = "La Liga"
                elif country == 'germany' and len(teams) == 18:
                    league_name = "Bundesliga"
                elif country == 'italy' and len(teams) == 20:
                    league_name = "Serie A"
                elif country == 'france' and len(teams) == 20:
                    league_name = "Ligue 1"

                print(f"ID {league_id}: {league_name} ({country}) - {len(teams)} teams")
                print(f"         Sample: {sample}")


if __name__ == "__main__":
    asyncio.run(test())

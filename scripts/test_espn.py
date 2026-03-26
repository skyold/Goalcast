#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from provider import ESPNProvider


async def test():
    print("=== Testing ESPNProvider ===\n")

    espn = ESPNProvider()
    print(f"Available: {await espn.is_available()}\n")

    print("Testing get_schedule('Premier League', '2024')...")
    schedule = await espn.get_schedule('Premier League', '2024')
    print(f"Schedule: {len(schedule) if schedule else 0} matches")
    if schedule:
        for m in schedule[:3]:
            print(f"  {m.get('home_team')} vs {m.get('away_team')} ({m.get('date', '?')[:10]})")
    else:
        print("  No schedule data")

    print("\nTesting get_match with first match ID...")
    if schedule:
        match_id = schedule[0].get('match_id')
        print(f"Match ID: {match_id}")
        match = await espn.get_match(match_id)
        if match:
            print(f"Match: {match.get('home_team')} vs {match.get('away_team')}")
            print(f"Status: {match.get('status')}")
            print(f"Score: {match.get('home_score')}-{match.get('away_score')}")
        else:
            print("No match data")

    print("\nTesting get_team_matches('Arsenal', 'Premier League')...")
    team_matches = await espn.get_team_matches("Arsenal", "Premier League")
    print(f"Team matches: {len(team_matches) if team_matches else 0} matches")
    if team_matches:
        for m in team_matches[:3]:
            print(f"  {m.get('home_team')} vs {m.get('away_team')}")

    print("\n=== ESPNProvider Test Complete ===")


if __name__ == "__main__":
    asyncio.run(test())

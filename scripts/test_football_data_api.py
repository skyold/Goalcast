import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.collectors.football_data import FootballDataClient
from dotenv import load_dotenv

load_dotenv()


async def test_api():
    api_key = os.getenv("FOOTBALL_DATA_API_KEY", "")
    print(f"API Key: {api_key[:8]}..." if api_key else "No API Key found!")
    
    client = FootballDataClient(api_key=api_key, timeout=10.0)
    
    print("\n=== Testing Football-Data API ===")
    print("Timeout: 10 seconds\n")
    
    print("1. Testing Premier League matches...")
    matches = await client.get_matches("PL")
    if matches:
        print(f"   Found {len(matches)} matches")
        for m in matches[:3]:
            print(f"   - {m['home_name']} vs {m['away_name']} ({m['status']})")
    else:
        print("   No matches found or API error")
    
    print("\n2. Testing upcoming matches (next 7 days)...")
    upcoming = await client.get_upcoming_matches("PL", days=7)
    if upcoming:
        print(f"   Found {len(upcoming)} upcoming matches")
        for m in upcoming[:5]:
            print(f"   - {m['utc_date']}: {m['home_name']} vs {m['away_name']}")
    else:
        print("   No upcoming matches found")
    
    print("\n3. Testing standings...")
    standings = await client.get_standings("PL")
    if standings:
        print(f"   Found {len(standings)} teams in standings")
        for s in standings[:5]:
            print(f"   {s['position']}. {s['team_name']} - {s['points']} pts")
    else:
        print("   No standings found")
    
    print("\n=== Test Complete ===")


if __name__ == "__main__":
    asyncio.run(test_api())

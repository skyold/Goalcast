import asyncio
import os
import sys
import json

# Add project root to path
project_root = "/Users/zhengningdai/workspace/skyold/Goalcast/"
sys.path.append(project_root)

from provider.footystats.client import FootyStatsProvider
from dotenv import load_dotenv

async def test():
    load_dotenv(os.path.join(project_root, ".env"))
    provider = FootyStatsProvider()
    print("Testing get_todays_matches for 2026-04-11...")
    result = await provider.get_todays_matches(date="2026-04-11")
    
    # Filter for La Liga in the script to be sure
    if isinstance(result, dict) and "data" in result:
        matches = result["data"]
        la_liga_matches = [m for m in matches if "La Liga" in str(m.get("competition_name", ""))]
        print(f"Total matches: {len(matches)}")
        print(f"La Liga matches: {len(la_liga_matches)}")
        for m in la_liga_matches:
            print(f"- {m.get('home_name')} vs {m.get('away_name')} ({m.get('date_unix')})")
    else:
        print(f"Result: {result}")

if __name__ == "__main__":
    asyncio.run(test())

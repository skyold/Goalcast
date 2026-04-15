
import asyncio
import httpx
import sys
import os
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).parent.parent
sys.path.append(str(BASE_DIR))

from config.settings import settings

async def check_odds():
    api_key = settings.SPORTMONKS_API_KEY
    fixture_id = 19648225
    url = f"https://api.sportmonks.com/v3/football/odds/pre-match/fixtures/{fixture_id}?api_token={api_key}"
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.get(url)
            print(f"Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json().get("data", [])
                print(f"Odds count: {len(data)}")
                market_names = set()
                for item in data:
                    name = item.get("market_description") or item.get("market_name")
                    if name:
                        market_names.add(name)
                
                # Check for Fulltime Result specifically
                ft_result = [d for d in data if (d.get("market_description") or d.get("market_name") or "").lower() in ("fulltime result", "full time result", "match winner")]
                print(f"Fulltime Result count: {len(ft_result)}")
                if ft_result:
                    for item in ft_result[:10]:
                        print(f"Item: label={item.get('label')}, market_id={item.get('market_id')}, type={type(item.get('market_id'))}, bookmaker_id={item.get('bookmaker_id')}, value={item.get('value')}")
            else:
                print(f"Error: {resp.text}")
        except Exception as e:
            print(f"Request failed: {e}")

if __name__ == "__main__":
    asyncio.run(check_odds())

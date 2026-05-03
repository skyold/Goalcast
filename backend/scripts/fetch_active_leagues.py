import os
import json
import time
import requests

from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("SPORTMONKS_API_KEY")

if not API_KEY:
    print("Error: SPORTMONKS_API_KEY not found in .env")
    exit(1)

OUTPUT_FILE = "backend/config/sportmonks_leagues.json"
BASE_URL = "https://api.sportmonks.com/v3/football/leagues"

active_leagues = {}
page = 1
has_more = True

print("Starting to fetch active leagues from Sportmonks...")

while has_more:
    print(f"Fetching page {page}...")
    try:
        response = requests.get(BASE_URL, params={
            "api_token": API_KEY,
            "page": page
        })
        response.raise_for_status()
        data = response.json()
        
        for league in data.get("data", []):
            if league.get("active") is True:
                active_leagues[str(league["id"])] = {
                    "id": league["id"],
                    "name": league["name"],
                    "country_id": league.get("country_id")
                }
                
        pagination = data.get("pagination", {})
        has_more = pagination.get("has_more", False)
        page += 1
        
        time.sleep(0.5)  # 避免触发限流
        
    except Exception as e:
        print(f"Error fetching page {page}: {e}")
        break

print(f"Successfully fetched {len(active_leagues)} active leagues.")

# 确保目录存在
os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(active_leagues, f, ensure_ascii=False, indent=2)

print(f"Saved dictionary to {OUTPUT_FILE}")

import asyncio
import json
import sqlite3
import argparse
from datetime import datetime
from pathlib import Path

from provider.sportmonks.client import SportmonksProvider
# from provider.footystats.client import FootystatsProvider
from utils.config_parser import load_config

async def prewarm_sportmonks(date_str: str, config: dict, base_path: Path, db: sqlite3.Connection):
    provider = SportmonksProvider()
    if not await provider.is_available():
        print("Sportmonks API unavailable")
        return
        
    # Get configured leagues
    leagues_config = config.get("sportmonks", {}).get("leagues", [])
    
    # Use fixtures between to get matches for the specific date
    res = await provider.get_fixtures_between(
        date_str, 
        date_str, 
        include="participants,league,statistics,lineups,odds"
    )
    
    matches = res.get("data", []) if res else []
    
    # Save to JSON
    out_dir = base_path / date_str / "sportmonks"
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "matches.json", "w", encoding="utf-8") as f:
        json.dump(matches, f, ensure_ascii=False, indent=2)
        
    # Save to SQLite
    cursor = db.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS raw_sportmonks_matches (
            match_id INTEGER PRIMARY KEY,
            date TEXT,
            league_id INTEGER,
            raw_data TEXT
        )
    """)
    for m in matches:
        cursor.execute(
            "INSERT OR REPLACE INTO raw_sportmonks_matches VALUES (?, ?, ?, ?)",
            (m.get("id"), date_str, m.get("league_id"), json.dumps(m))
        )
    db.commit()
    print(f"Pre-warmed {len(matches)} Sportmonks matches for {date_str}")

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    args = parser.parse_args()
    
    config = load_config("config/watchlist.yaml")
    base_path = Path("data/cache")
    base_path.mkdir(parents=True, exist_ok=True)
    
    db_path = base_path / "goalcast.db"
    db = sqlite3.connect(db_path)
    
    await asyncio.gather(
        prewarm_sportmonks(args.date, config, base_path, db),
        # Add Footystats prewarming here later if needed
    )
    
    db.close()

if __name__ == "__main__":
    asyncio.run(main())
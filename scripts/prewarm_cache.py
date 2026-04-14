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
    
    # Prepare extended data
    extended_data = {}
    
    # Get additional data for each match
    for match in matches:
        match_id = match.get("id")
        if not match_id:
            continue
        
        # Get xG data
        xg_data = await provider.get_expected_goals_by_fixture(match_id)
        
        # Get predictions data
        predictions_data = await provider.get_predictions_by_fixture(match_id)
        
        # Get head-to-head data if teams are available
        home_team_id = None
        away_team_id = None
        participants = match.get("participants", [])
        if len(participants) >= 2:
            home_team_id = participants[0].get("id")
            away_team_id = participants[1].get("id")
        
        head_to_head_data = None
        if home_team_id and away_team_id:
            head_to_head_data = await provider.get_head_to_head(home_team_id, away_team_id)
        
        # Get team form data (last 10 matches)
        home_form_data = None
        away_form_data = None
        if home_team_id:
            home_form_data = await provider.get_fixtures_by_team(home_team_id)
        if away_team_id:
            away_form_data = await provider.get_fixtures_by_team(away_team_id)
        
        # Get standings data if league_id is available
        standings_data = None
        league_id = match.get("league_id")
        if league_id:
            # Try to get season_id from the match
            season_id = match.get("season_id")
            if not season_id and match.get("league"):
                season_id = match.get("league").get("current_season_id")
            if season_id:
                standings_data = await provider.get_standings_by_season(season_id)
        
        extended_data[match_id] = {
            "xg": xg_data,
            "predictions": predictions_data,
            "head_to_head": head_to_head_data,
            "home_form": home_form_data,
            "away_form": away_form_data,
            "standings": standings_data
        }
    
    # Save to JSON with extended structure
    out_dir = base_path / date_str / "sportmonks"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Save matches
    with open(out_dir / "matches.json", "w", encoding="utf-8") as f:
        json.dump(matches, f, ensure_ascii=False, indent=2)
    
    # Save extended data
    with open(out_dir / "extended_data.json", "w", encoding="utf-8") as f:
        json.dump(extended_data, f, ensure_ascii=False, indent=2)
        
    # Save to SQLite
    cursor = db.cursor()
    
    # Create main matches table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS raw_sportmonks_matches (
            match_id INTEGER PRIMARY KEY,
            date TEXT,
            league_id INTEGER,
            raw_data TEXT
        )
    """)
    
    # Create xG table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS raw_sportmonks_xg (
            match_id INTEGER PRIMARY KEY,
            raw_data TEXT
        )
    """)
    
    # Create predictions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS raw_sportmonks_predictions (
            match_id INTEGER PRIMARY KEY,
            raw_data TEXT
        )
    """)
    
    # Create head-to-head table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS raw_sportmonks_head_to_head (
            match_id INTEGER PRIMARY KEY,
            home_team_id INTEGER,
            away_team_id INTEGER,
            raw_data TEXT
        )
    """)
    
    # Create team form table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS raw_sportmonks_team_form (
            match_id INTEGER PRIMARY KEY,
            home_team_id INTEGER,
            away_team_id INTEGER,
            home_form TEXT,
            away_form TEXT
        )
    """)
    
    # Create standings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS raw_sportmonks_standings (
            match_id INTEGER PRIMARY KEY,
            league_id INTEGER,
            season_id INTEGER,
            raw_data TEXT
        )
    """)
    
    # Insert data
    for match in matches:
        match_id = match.get("id")
        if not match_id:
            continue
        
        # Insert into matches table
        cursor.execute(
            "INSERT OR REPLACE INTO raw_sportmonks_matches VALUES (?, ?, ?, ?)",
            (match_id, date_str, match.get("league_id"), json.dumps(match))
        )
        
        # Insert extended data
        ext_data = extended_data.get(match_id, {})
        
        # Insert xG data
        if ext_data.get("xg"):
            cursor.execute(
                "INSERT OR REPLACE INTO raw_sportmonks_xg VALUES (?, ?)",
                (match_id, json.dumps(ext_data["xg"]))
            )
        
        # Insert predictions data
        if ext_data.get("predictions"):
            cursor.execute(
                "INSERT OR REPLACE INTO raw_sportmonks_predictions VALUES (?, ?)",
                (match_id, json.dumps(ext_data["predictions"]))
            )
        
        # Insert head-to-head data
        if ext_data.get("head_to_head"):
            participants = match.get("participants", [])
            home_team_id = participants[0].get("id") if len(participants) >= 1 else None
            away_team_id = participants[1].get("id") if len(participants) >= 2 else None
            cursor.execute(
                "INSERT OR REPLACE INTO raw_sportmonks_head_to_head VALUES (?, ?, ?, ?)",
                (match_id, home_team_id, away_team_id, json.dumps(ext_data["head_to_head"]))
            )
        
        # Insert team form data
        if ext_data.get("home_form") or ext_data.get("away_form"):
            participants = match.get("participants", [])
            home_team_id = participants[0].get("id") if len(participants) >= 1 else None
            away_team_id = participants[1].get("id") if len(participants) >= 2 else None
            cursor.execute(
                "INSERT OR REPLACE INTO raw_sportmonks_team_form VALUES (?, ?, ?, ?, ?)",
                (match_id, home_team_id, away_team_id, 
                 json.dumps(ext_data["home_form"]), json.dumps(ext_data["away_form"]))
            )
        
        # Insert standings data
        if ext_data.get("standings"):
            league_id = match.get("league_id")
            season_id = match.get("season_id")
            if not season_id and match.get("league"):
                season_id = match.get("league").get("current_season_id")
            cursor.execute(
                "INSERT OR REPLACE INTO raw_sportmonks_standings VALUES (?, ?, ?, ?)",
                (match_id, league_id, season_id, json.dumps(ext_data["standings"]))
            )
    
    db.commit()
    print(f"Pre-warmed {len(matches)} Sportmonks matches for {date_str}")
    print(f"Extended data collected for {len(extended_data)} matches")

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
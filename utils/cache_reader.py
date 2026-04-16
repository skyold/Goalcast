import json
from pathlib import Path
from typing import List, Dict, Any, Optional

def get_cached_matches(
    provider: str, 
    date: str, 
    leagues: Optional[List[int]] = None,
    base_path: Path = Path("data/cache")
) -> List[Dict[str, Any]]:
    """
    Reads pre-warmed JSON cache for a given provider and date.
    Filters by league_id if provided.
    """
    file_path = base_path / provider / date / "matches.json"
    if not file_path.exists():
        return []
        
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []
        
    if not isinstance(data, list):
        return []
        
    if leagues is not None:
        # Assumes the raw data has 'league_id' for Sportmonks or 'competition_id' for Footystats
        # We try to find the standard league ID field
        filtered = []
        for match in data:
            match_league = match.get("league_id") or match.get("competition_id")
            if match_league in leagues:
                filtered.append(match)
        return filtered
        
    return data

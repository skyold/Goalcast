import json
import pytest
from pathlib import Path
from utils.cache_reader import get_cached_matches

def test_get_cached_matches(tmp_path):
    # Setup mock cache
    date_str = "2026-04-14"
    provider = "sportmonks"
    cache_dir = tmp_path / "cache" / provider / date_str
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    mock_data = [{"id": 1, "league_id": 10}, {"id": 2, "league_id": 20}]
    (cache_dir / "matches.json").write_text(json.dumps(mock_data))
    
    # Test read all
    res = get_cached_matches(provider, date_str, base_path=tmp_path / "cache")
    assert len(res) == 2
    
    # Test read with league filter
    res_filtered = get_cached_matches(provider, date_str, leagues=[10], base_path=tmp_path / "cache")
    assert len(res_filtered) == 1
    assert res_filtered[0]["id"] == 1

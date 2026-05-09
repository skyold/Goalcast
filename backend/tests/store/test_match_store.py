import pytest
from pathlib import Path
import store.match_store as match_store_mod


def _make_store(tmp_path):
    """直接替换模块级 MATCHES_DIR，保证测试期间始终生效。"""
    matches_dir = tmp_path / "matches"
    match_store_mod.MATCHES_DIR = matches_dir
    return match_store_mod, matches_dir


def test_save_and_get(tmp_path):
    match_store, _ = _make_store(tmp_path)
    record = {
        "match_id": "MC-TEST-001",
        "status": "pending",
        "metadata": {
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "league": "Premier League",
            "kickoff_time": "2025-05-10 20:00:00",
            "provider_ids": {"sportmonks": 100},
            "collected_at": None,
        },
        "raw_data": {},
        "analysis": {},
    }
    match_store.save(record)
    loaded = match_store.get("MC-TEST-001")
    assert loaded["match_id"] == "MC-TEST-001"
    assert loaded["status"] == "pending"


def test_update_status(tmp_path):
    match_store, _ = _make_store(tmp_path)
    record = {
        "match_id": "MC-TEST-002",
        "status": "pending",
        "metadata": {"home_team": "A", "away_team": "B", "league": "", "kickoff_time": "", "provider_ids": {}, "collected_at": None},
        "raw_data": {},
        "analysis": {},
    }
    match_store.save(record)
    match_store.update("MC-TEST-002", {"status": "collected"})
    assert match_store.get("MC-TEST-002")["status"] == "collected"


def test_list_matches_filter_by_status(tmp_path):
    match_store, _ = _make_store(tmp_path)
    for i, status in enumerate(["pending", "collected", "analyzed"]):
        match_store.save({
            "match_id": f"MC-TEST-{i:03d}",
            "status": status,
            "metadata": {"home_team": "A", "away_team": "B", "league": "PL", "kickoff_time": "2025-05-10 20:00:00", "provider_ids": {}, "collected_at": None},
            "raw_data": {},
            "analysis": {},
        })
    result = match_store.list_matches(status="collected")
    assert len(result) == 1
    assert result[0]["status"] == "collected"


def test_list_matches_filter_by_date(tmp_path):
    match_store, _ = _make_store(tmp_path)
    for date in ["2025-05-09 20:00:00", "2025-05-10 20:00:00", "2025-05-11 20:00:00"]:
        mid = f"MC-{date[:10].replace('-', '')}-001"
        match_store.save({
            "match_id": mid,
            "status": "collected",
            "metadata": {"home_team": "A", "away_team": "B", "league": "PL", "kickoff_time": date, "provider_ids": {}, "collected_at": None},
            "raw_data": {},
            "analysis": {},
        })
    result = match_store.list_matches(date="2025-05-10")
    assert len(result) == 1
    assert result[0]["metadata"]["kickoff_time"] == "2025-05-10 20:00:00"


def test_get_returns_none_for_missing(tmp_path):
    match_store, _ = _make_store(tmp_path)
    assert match_store.get("MC-NOTEXIST") is None

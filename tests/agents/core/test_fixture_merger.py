"""Tests for the OddAlerts fixture normalizer."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))

from agents.core.fixture_merger import normalize_oddalerts_fixture


def test_normalize_basic_fixture():
    raw = {
        "id": 12345,
        "name": "Arsenal vs Chelsea",
        "starting_at": "2026-05-14T20:00:00Z",
        "league": {"id": 8, "name": "Premier League", "country": "England"},
        "participants": [
            {"id": 1, "name": "Arsenal", "meta": {"location": "home"}},
            {"id": 2, "name": "Chelsea", "meta": {"location": "away"}},
        ],
    }
    out = normalize_oddalerts_fixture(raw)
    assert out["fixture_id"] == 12345
    assert out["home_team"]["name"] == "Arsenal"
    assert out["away_team"]["name"] == "Chelsea"
    assert out["league"]["name"] == "Premier League"
    assert out["kickoff_utc"] == "2026-05-14T20:00:00Z"


def test_normalize_missing_participants_returns_none():
    raw = {"id": 999, "name": "Unknown", "starting_at": "2026-05-14T20:00:00Z"}
    assert normalize_oddalerts_fixture(raw) is None


def test_normalize_only_home_returns_none():
    raw = {
        "id": 555,
        "name": "Arsenal vs ?",
        "starting_at": "2026-05-14T20:00:00Z",
        "participants": [
            {"id": 1, "name": "Arsenal", "meta": {"location": "home"}},
        ],
    }
    assert normalize_oddalerts_fixture(raw) is None


def test_raw_payload_preserved():
    raw = {
        "id": 42,
        "name": "A vs B",
        "starting_at": "2026-05-14T20:00:00Z",
        "league": {"id": 1, "name": "L"},
        "participants": [
            {"id": 11, "name": "A", "meta": {"location": "home"}},
            {"id": 22, "name": "B", "meta": {"location": "away"}},
        ],
        "extra_field": "preserved",
    }
    out = normalize_oddalerts_fixture(raw)
    assert out["raw"] is raw

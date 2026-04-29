import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.core import match_store


def _sample_match(match_id: str) -> dict:
    return {
        "schema_version": "1.0",
        "match_id": match_id,
        "status": "pending",
        "orchestrator": {
            "home_team": "Manchester City",
            "away_team": "Arsenal",
            "league": "Premier League",
            "kickoff_time": "2026-04-30T19:00:00+08:00",
            "data_source": "sportmonks",
            "model_version": "v4.0",
            "prepared_at": "2026-04-28T10:00:00+08:00",
        },
    }


def test_generate_match_id_format():
    match_id = match_store.generate_match_id()
    assert re.fullmatch(r"MC-\d{8}-\d{6}-[A-F0-9]{8}", match_id)


def test_save_and_load(tmp_path, monkeypatch):
    monkeypatch.setattr(match_store, "MATCHES_DIR", tmp_path)

    record = _sample_match("MC-20260428-100000-A1B2C3D4")
    match_store.save(record)

    loaded = match_store.load(record["match_id"])
    assert loaded is not None
    assert loaded["match_id"] == record["match_id"]
    assert loaded["orchestrator"]["home_team"] == "Manchester City"
    assert loaded["status"] == "pending"


def test_append_layer_and_status_transition(tmp_path, monkeypatch):
    monkeypatch.setattr(match_store, "MATCHES_DIR", tmp_path)

    match_id = "MC-20260428-100000-A1B2C3D4"
    match_store.save(_sample_match(match_id))

    match_store.append_layer(
        match_id,
        "analysis",
        {
            "home_xg": 1.82,
            "away_xg": 1.15,
            "confidence": 78,
            "analyzed_at": "2026-04-28T10:05:00+08:00",
        },
    )
    record = match_store.load(match_id)
    assert record["status"] == "analyzed"
    assert record["analysis"]["home_xg"] == 1.82

    match_store.append_layer(
        match_id,
        "trade",
        {
            "direction": "home",
            "ah_line": -0.5,
            "best_odds": 1.91,
            "stake": 2.5,
            "traded_at": "2026-04-28T10:08:00+08:00",
        },
    )
    record = match_store.load(match_id)
    assert record["status"] == "traded"
    assert record["trade"]["stake"] == 2.5

    match_store.append_layer(
        match_id,
        "review",
        {
            "verdict": "approved",
            "checks": {"confidence": "pass", "ev": "pass"},
            "reviewed_at": "2026-04-28T10:12:00+08:00",
        },
    )
    record = match_store.load(match_id)
    assert record["status"] == "reviewed"
    assert record["review"]["verdict"] == "approved"


def test_update_status(tmp_path, monkeypatch):
    monkeypatch.setattr(match_store, "MATCHES_DIR", tmp_path)

    match_id = "MC-20260428-100000-A1B2C3D4"
    match_store.save(_sample_match(match_id))

    match_store.update_status(match_id, "feedback")
    record = match_store.load(match_id)
    assert record["status"] == "feedback"


def test_claim_oldest(tmp_path, monkeypatch):
    monkeypatch.setattr(match_store, "MATCHES_DIR", tmp_path)

    r1 = _sample_match("MC-20260428-100000-AAAAAAAA")
    r1["orchestrator"]["prepared_at"] = "2026-04-28T09:00:00+08:00"
    match_store.save(r1)

    r2 = _sample_match("MC-20260428-101000-BBBBBBBB")
    r2["orchestrator"]["prepared_at"] = "2026-04-28T08:00:00+08:00"
    match_store.save(r2)

    claimed = match_store.claim_oldest(["pending"], "analyzing")
    assert claimed is not None
    assert claimed["match_id"] == "MC-20260428-101000-BBBBBBBB"
    assert claimed["status"] == "analyzing"

    loaded = match_store.load("MC-20260428-101000-BBBBBBBB")
    assert loaded["status"] == "analyzing"


def test_list_all(tmp_path, monkeypatch):
    monkeypatch.setattr(match_store, "MATCHES_DIR", tmp_path)

    match_store.save(_sample_match("MC-20260428-100000-AAAAAAAA"))
    match_store.save(_sample_match("MC-20260428-101000-BBBBBBBB"))

    all_records = match_store.list_all()
    assert len(all_records) == 2

    pending_records = match_store.list_all(status="pending")
    assert len(pending_records) == 2


def test_finalize(tmp_path, monkeypatch):
    monkeypatch.setattr(match_store, "MATCHES_DIR", tmp_path)

    match_id = "MC-20260428-100000-A1B2C3D4"
    match_store.save(_sample_match(match_id))

    match_store.finalize(match_id, report_ref="data/reports/2026-04-30.md")
    record = match_store.load(match_id)
    assert record["status"] == "reported"
    assert record["report_ref"] == "data/reports/2026-04-30.md"


def test_load_nonexistent():
    result = match_store.load("MC-NONEXISTENT")
    assert result is None

"""Normalize OddAlerts fixture responses into a canonical internal shape.

After the 2026-05-14 single-source pivot, the multi-provider merge step is
no longer needed: every fixture comes from OddAlerts. This module is now a
thin adapter that flattens a raw OddAlerts `/api/fixtures/id` payload into
the canonical dict the rest of the codebase consumes.
"""
from __future__ import annotations
from typing import Any, Optional


def normalize_oddalerts_fixture(raw: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Convert an OddAlerts fixture payload into a canonical fixture dict.

    Returns None if the payload is unusable (missing either home or away
    participant). The original payload is included under ``raw`` so callers
    that need provider-specific fields can still reach them.
    """
    participants = raw.get("participants") or []
    home = next(
        (p for p in participants if (p.get("meta") or {}).get("location") == "home"),
        None,
    )
    away = next(
        (p for p in participants if (p.get("meta") or {}).get("location") == "away"),
        None,
    )
    if not home or not away:
        return None

    league = raw.get("league") or {}
    return {
        "fixture_id": raw.get("id"),
        "name": raw.get("name"),
        "kickoff_utc": raw.get("starting_at"),
        "league": {
            "id": league.get("id"),
            "name": league.get("name"),
            "country": league.get("country"),
        },
        "home_team": {"id": home.get("id"), "name": home.get("name")},
        "away_team": {"id": away.get("id"), "name": away.get("name")},
        "raw": raw,
    }

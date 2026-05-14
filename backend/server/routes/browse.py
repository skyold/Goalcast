"""Browse-layer HTTP API — wraps OddAlertsProvider for the new frontend."""
from __future__ import annotations
from pathlib import Path

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from provider.base import get_provider
from utils.cache import Cache

router = APIRouter(prefix="/api", tags=["browse"])

_CACHE_PATH = Path(__file__).resolve().parents[2] / "data" / "cache.db"
_cache = Cache(_CACHE_PATH)


def _normalize_competitions(raw: dict) -> list[dict]:
    items = raw.get("data") or []
    return [{"id": c.get("id"), "name": c.get("name"), "country": c.get("country")} for c in items]


@router.get("/competitions")
async def get_competitions():
    cache_key = "competitions:all"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached
    provider = get_provider()
    raw = await provider.get_competitions()
    if not raw:
        raise HTTPException(status_code=502, detail="OddAlerts unavailable")
    result = _normalize_competitions(raw)
    _cache.set(cache_key, result, ttl_seconds=86_400)
    return result


def _normalize_fixture_item(item: dict) -> dict:
    league = item.get("league") or {}
    return {
        "fixture_id": item.get("id"),
        "name": item.get("fixture_name") or item.get("name"),
        "kickoff_utc": item.get("starting_at"),
        "league": {"id": league.get("id"), "name": league.get("name")},
        "drop_percentage": item.get("drop_percentage"),
        "closing": item.get("closing"),
        "opening": item.get("opening"),
    }


@router.get("/fixtures")
async def get_fixtures(
    date: str = Query(..., description="ISO date YYYY-MM-DD"),
    competition_id: Optional[int] = Query(None),
):
    cache_key = f"fixtures:{date}:{competition_id or 'all'}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached
    provider = get_provider()
    raw = await provider.get_dropping_odds()
    if not raw:
        raise HTTPException(status_code=502, detail="OddAlerts unavailable")
    items = raw.get("data") or []
    out = []
    for item in items:
        starting_at = item.get("starting_at") or ""
        if not starting_at.startswith(date):
            continue
        if competition_id is not None:
            league = item.get("league") or {}
            if league.get("id") != competition_id:
                continue
        out.append(_normalize_fixture_item(item))
    _cache.set(cache_key, out, ttl_seconds=300)
    return out

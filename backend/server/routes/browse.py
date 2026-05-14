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


@router.get("/fixtures/{fixture_id}")
async def get_fixture_detail(fixture_id: int):
    from agents.core.fixture_merger import normalize_oddalerts_fixture

    cache_key = f"fixture:{fixture_id}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached
    provider = get_provider()
    bundle = await provider.collect_fixture_data(fixture_id)
    if not bundle or not bundle.get("fixture"):
        raise HTTPException(status_code=404, detail="Fixture not found")
    canonical = normalize_oddalerts_fixture(bundle["fixture"])
    if canonical is None:
        raise HTTPException(status_code=422, detail="Unusable fixture payload")
    result = dict(canonical)
    result["raw_bundle"] = bundle
    _cache.set(cache_key, result, ttl_seconds=300)
    return result


_TREND_TYPES = {"homeWin", "awayWin", "btts"}


@router.get("/trends/{trend_type}")
async def get_trends(trend_type: str):
    if trend_type not in _TREND_TYPES:
        raise HTTPException(status_code=400, detail=f"Unknown trend type: {trend_type}")
    cache_key = f"trends:{trend_type}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached
    provider = get_provider()
    raw = await provider.get_trends(market=trend_type)
    if not raw:
        raise HTTPException(status_code=502, detail="OddAlerts unavailable")
    data = raw.get("data") or []
    _cache.set(cache_key, data, ttl_seconds=900)
    return data


@router.get("/odds/dropping")
async def get_dropping(window: str = Query("1h", pattern="^(1h|6h|24h)$")):
    cache_key = f"odds:dropping:{window}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached
    provider = get_provider()
    raw = await provider.get_dropping_odds()
    if not raw:
        raise HTTPException(status_code=502, detail="OddAlerts unavailable")
    data = raw.get("data") or []
    _cache.set(cache_key, data, ttl_seconds=300)
    return data

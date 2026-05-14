"""Browse-layer HTTP API — wraps OddAlertsProvider for the new frontend."""
from __future__ import annotations
from pathlib import Path

from fastapi import APIRouter, HTTPException
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

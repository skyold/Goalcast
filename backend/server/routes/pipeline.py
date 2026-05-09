from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Query

from store import match_store
from pipeline.scheduler import get_scheduler

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["pipeline"])

_LEAGUES_FILE = Path(__file__).resolve().parents[2] / "config" / "sportmonks_leagues.json"


@router.get("/matches")
async def get_matches(
    league: str = Query(default=None),
    date: str = Query(default=None),
    status: str = Query(default=None),
) -> dict:
    items = match_store.list_matches(league=league, date=date, status=status)
    return {"items": items, "total": len(items)}


@router.get("/matches/{match_id}")
async def get_match(match_id: str) -> dict:
    record = match_store.get(match_id)
    if record is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="比赛不存在")
    return record


@router.post("/pipeline/run")
async def trigger_pipeline(body: dict = None) -> dict:
    scheduler = get_scheduler()
    await scheduler.trigger()
    return {"message": "已触发 pipeline 执行"}


@router.get("/pipeline/status")
async def get_pipeline_status() -> dict:
    scheduler = get_scheduler()
    return {
        "running": scheduler.is_running,
        "last_result": scheduler.last_result,
    }


@router.get("/pipeline/leagues")
async def get_leagues() -> dict:
    import json
    available = []
    if _LEAGUES_FILE.exists():
        try:
            all_leagues = json.loads(_LEAGUES_FILE.read_text(encoding="utf-8"))
            seen: set[str] = set()
            for lid, info in all_leagues.items():
                cn = info.get("chinese_name", info.get("name", ""))
                if cn in seen:
                    continue
                seen.add(cn)
                available.append({
                    "id": info.get("id"),
                    "chinese_name": cn,
                    "name": info.get("name", ""),
                })
        except Exception:
            pass
    available.sort(key=lambda x: x["chinese_name"])
    return {"available": available}

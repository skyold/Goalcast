from __future__ import annotations

import logging

from fastapi import APIRouter

from provider import registry

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("/providers")
async def get_providers() -> dict:
    cfg = registry.get_config()
    return {
        "providers": cfg.get("providers", {}),
        "analyst": cfg.get("analyst", {"enabled": True}),
        "schedule": cfg.get("schedule", {"interval_hours": 1}),
    }


@router.post("/providers")
async def update_providers(body: dict) -> dict:
    """
    body 示例:
    {
      "providers": {"oddalerts": true, "sportmonks": false},
      "analyst": true
    }
    """
    providers = body.get("providers", {})
    for name, enabled in providers.items():
        registry.set_provider_enabled(name, bool(enabled))

    if "analyst" in body:
        registry.set_analyst_enabled(bool(body["analyst"]))

    return {"message": "配置已更新", "config": registry.get_config()}


@router.get("/schedule")
async def get_schedule() -> dict:
    return {"interval_hours": registry.get_schedule_hours()}


@router.post("/schedule")
async def update_schedule(body: dict) -> dict:
    hours = int(body.get("interval_hours", 1))
    registry.set_schedule_hours(hours)
    return {"interval_hours": hours}

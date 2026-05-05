import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])

_CST = timezone(timedelta(hours=8))


@router.post("/api/chat/")
async def send_chat(body: dict) -> dict:
    message = body.get("message", "")
    history = body.get("history", [])
    logger.info("Chat request: %s (history: %d messages)", message[:80], len(history))

    return {
        "id": f"assistant-{datetime.now(_CST).timestamp()}",
        "role": "assistant",
        "content": f"Received: {message[:200]}\n\n(View analysis progress on Pipeline Monitor page)",
        "timestamp": datetime.now(_CST).isoformat(),
    }


@router.get("/api/agents/status")
async def get_agent_status() -> list:
    return []


@router.get("/api/pipelines/status")
async def get_pipeline_status() -> list:
    return []


@router.get("/api/tokens/summary")
async def get_token_summary() -> dict:
    return {
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "total_cache_creation_tokens": 0,
        "total_cache_read_tokens": 0,
        "total_tokens": 0,
        "total_cost": 0,
        "run_count": 0,
        "by_agent": [],
        "by_day": [],
        "recent_records": [],
    }


@router.get("/api/tokens/records")
async def get_token_records() -> dict:
    return {"items": [], "total": 0, "limit": 20, "offset": 0}


@router.get("/api/tokens/agents/{agent_id}")
async def get_agent_token_stats(agent_id: str) -> dict:
    return {
        "total_records": 0,
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "total_cost": 0,
        "recent_runs": [],
    }

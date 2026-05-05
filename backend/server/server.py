import os
import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

IS_DEV = os.environ.get("UI_DEV_MODE", "").lower() in ("1", "true", "yes")

app = FastAPI(title="Goalcast API", version="0.1.0")

if IS_DEV:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:5174"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

from .routes.config import router as config_router
from .routes.board import router as board_router
from .routes.chat import router as chat_router

app.include_router(config_router)
app.include_router(board_router)
app.include_router(chat_router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.websocket("/ws/status")
async def ws_status(websocket: WebSocket):
    from .ws.manager import manager
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket):
    """Goalcast orchestrator chat WebSocket."""
    await websocket.accept()
    logger.info("Chat WebSocket connected")

    from agents.core.events import EventEmitter
    from agents.adapters.adapter import ClaudeAdapter
    from agents.core.orchestrator import Orchestrator
    from datetime import datetime, timedelta, timezone
    import asyncio
    import json

    _CST = timezone(timedelta(hours=8))

    emitter = EventEmitter()

    async def on_event(name: str, payload: dict):
        try:
            await websocket.send_json({"type": name, "payload": payload})
        except Exception:
            pass

    emitter.subscribe(on_event)

    try:
        while True:
            text = await websocket.receive_text()

            await websocket.send_json({
                "type": "chat_chunk",
                "payload": {"text": f"Processing: {text}"}
            })

            async def handle_request():
                try:
                    adapter = ClaudeAdapter()
                    intent = await _parse_intent(text, adapter)
                    leagues = intent.get("leagues", [])
                    date = intent.get("date")
                    models = intent.get("models", ["v4.0"])

                    orchestrator = Orchestrator(
                        adapter=adapter, semi_mode=False, emitter=emitter
                    )
                    await orchestrator.run(
                        leagues=leagues, date=date, models=models
                    )
                except Exception as e:
                    logger.error("Pipeline error: %s", e, exc_info=True)
                    await emitter.emit("match_step_error", {
                        "match_id": "system",
                        "message": str(e),
                    })

            asyncio.create_task(handle_request())
    except WebSocketDisconnect:
        logger.info("Chat WebSocket disconnected")
    finally:
        emitter.unsubscribe(on_event)


async def _parse_intent(text: str, adapter) -> dict:
    from datetime import datetime, timedelta, timezone
    import json

    _CST = timezone(timedelta(hours=8))
    today = datetime.now(_CST).strftime("%Y-%m-%d")

    prompt = f"""
    Parse the following user request into JSON.
    Format: {{"leagues": [], "date": "YYYY-MM-DD", "models": []}}
    Today is {today}.
    If the request says today, use {today} as the date.
    `leagues` may contain either league names or numeric league IDs.
    If `models` is omitted, return an empty list.
    Request: {text}
    Return ONLY valid JSON.
    """

    try:
        result = await adapter.run_agent(
            "backend/agents/roles/orchestrator", prompt
        )
        response_text = result.final_text
        cleaned = response_text.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(cleaned)

        leagues = parsed.get("leagues")
        if not isinstance(leagues, list):
            leagues = []
        date = parsed.get("date")
        if date is not None and not isinstance(date, str):
            date = None
        models = parsed.get("models")
        if not isinstance(models, list) or not models:
            models = ["v4.0"]

        return {"leagues": leagues, "date": date, "models": models}
    except Exception as e:
        logger.error("Intent parsing failed: %s", e)
        return {"leagues": [], "date": None, "models": ["v4.0"]}

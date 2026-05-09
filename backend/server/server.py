import os
import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

IS_DEV = os.environ.get("UI_DEV_MODE", "").lower() in ("1", "true", "yes")

app = FastAPI(title="Goalcast API", version="2.0.0")

if IS_DEV:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:5174"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

from .routes.config import router as config_router
from .routes.pipeline import router as pipeline_router

app.include_router(config_router)
app.include_router(pipeline_router)


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


@app.websocket("/ws/logs")
async def ws_logs(websocket: WebSocket):
    import asyncio
    from pathlib import Path

    await websocket.accept()
    logger.info("Log WebSocket connected")

    log_dir = Path(__file__).resolve().parent.parent / "data" / "logs"
    log_file = log_dir / "goalcast.log"

    last_size = 0
    if log_file.exists():
        content = log_file.read_text(encoding="utf-8")
        if content.strip():
            await websocket.send_text(content)
        last_size = log_file.stat().st_size

    try:
        while True:
            if log_file.exists():
                current_size = log_file.stat().st_size
                if current_size > last_size:
                    with open(log_file, "r", encoding="utf-8") as f:
                        f.seek(last_size)
                        new_lines = f.read()
                        if new_lines:
                            await websocket.send_text(new_lines)
                    last_size = current_size
            await asyncio.sleep(1)
    except Exception:
        logger.info("Log WebSocket disconnected")
        try:
            await websocket.close()
        except Exception:
            pass


@app.websocket("/ws/events")
async def ws_events(websocket: WebSocket):
    """实时推送 pipeline 事件（发现/收集/分析进度）。"""
    from .ws.manager import manager
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

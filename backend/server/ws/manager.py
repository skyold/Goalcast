from fastapi import WebSocket
from typing import Any
import json
import asyncio
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

PIPELINE_EVENTS_FILE = Path(__file__).resolve().parents[2] / "data" / "pipeline_events.jsonl"


class ConnectionManager:
    def __init__(self):
        self._connections: list[WebSocket] = []
        self._events_task: asyncio.Task | None = None
        self._last_seq = 0

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._connections.append(ws)
        logger.info("WebSocket connected (%d total)", len(self._connections))
        if self._events_task is None:
            self._events_task = asyncio.create_task(self._poll_pipeline_events())

    def disconnect(self, ws: WebSocket):
        if ws in self._connections:
            self._connections.remove(ws)
            logger.info("WebSocket disconnected (%d remaining)", len(self._connections))
        if not self._connections and self._events_task:
            self._events_task.cancel()
            self._events_task = None

    async def broadcast(self, message: dict[str, Any]):
        dead: list[WebSocket] = []
        data = json.dumps(message)
        for ws in self._connections:
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    async def _poll_pipeline_events(self):
        while True:
            try:
                if PIPELINE_EVENTS_FILE.exists():
                    with open(PIPELINE_EVENTS_FILE, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                event = json.loads(line)
                            except json.JSONDecodeError:
                                continue
                            seq = event.get("seq", 0)
                            if seq > self._last_seq:
                                self._last_seq = seq
                                await self.broadcast({
                                    "type": event["type"],
                                    "payload": event["payload"],
                                })
            except Exception as e:
                logger.warning("[WS] 流水线事件轮询错误: %s", e)
            await asyncio.sleep(2)


manager = ConnectionManager()

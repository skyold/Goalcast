import asyncio
from typing import Callable, Awaitable, List
import logging

logger = logging.getLogger(__name__)

class EventEmitter:
    def __init__(self):
        self._subscribers: List[Callable[[str, dict], Awaitable[None]]] = []

    def subscribe(self, callback: Callable[[str, dict], Awaitable[None]]):
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[str, dict], Awaitable[None]]):
        self._subscribers = [cb for cb in self._subscribers if cb is not callback]

    async def emit(self, event_name: str, payload: dict):
        tasks = [callback(event_name, payload) for callback in list(self._subscribers)]
        if not tasks:
            return

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for callback, result in zip(list(self._subscribers), results):
            if isinstance(result, Exception):
                logger.warning(
                    "[EventEmitter] subscriber failed for %s: %s",
                    event_name,
                    result,
                )

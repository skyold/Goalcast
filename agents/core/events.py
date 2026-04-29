import asyncio
from typing import Callable, Awaitable, List

class EventEmitter:
    def __init__(self):
        self._subscribers: List[Callable[[str, dict], Awaitable[None]]] = []

    def subscribe(self, callback: Callable[[str, dict], Awaitable[None]]):
        self._subscribers.append(callback)

    async def emit(self, event_name: str, payload: dict):
        tasks = [callback(event_name, payload) for callback in self._subscribers]
        if tasks:
            await asyncio.gather(*tasks)

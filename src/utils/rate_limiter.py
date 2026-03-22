import asyncio
import time
from typing import Dict, Optional
from collections import defaultdict


class RateLimiter:
    def __init__(self):
        self._tokens: Dict[str, float] = defaultdict(float)
        self._last_refill: Dict[str, float] = defaultdict(float)
        self._lock = asyncio.Lock()

    async def acquire(self, source: str, rate_limit: float, period: float = 1.0):
        async with self._lock:
            now = time.time()
            elapsed = now - self._last_refill[source]

            if elapsed >= period:
                self._tokens[source] = rate_limit
                self._last_refill[source] = now

            while self._tokens[source] <= 0:
                await asyncio.sleep(0.1)
                now = time.time()
                elapsed = now - self._last_refill[source]
                if elapsed >= period:
                    self._tokens[source] = rate_limit
                    self._last_refill[source] = now

            self._tokens[source] -= 1

    async def sleep(self, seconds: float):
        await asyncio.sleep(seconds)


class SyncRateLimiter:
    def __init__(self):
        self._delays: Dict[str, float] = {}

    def configure(self, source: str, min_interval_seconds: float):
        self._delays[source] = min_interval_seconds

    async def acquire(self, source: str):
        if source not in self._delays:
            return

        delay = self._delays[source]
        if delay > 0:
            await asyncio.sleep(delay)

    def sleep(self, seconds: float):
        time.sleep(seconds)


_global_rate_limiter = RateLimiter()
_global_sync_limiter = SyncRateLimiter()


async def async_acquire(source: str, requests_per_hour: Optional[float] = None):
    if requests_per_hour is not None:
        await _global_rate_limiter.acquire(source, requests_per_hour, 3600.0)
    else:
        await _global_sync_limiter.acquire(source)


def configure_sync_limit(source: str, min_interval_seconds: float):
    _global_sync_limiter.configure(source, min_interval_seconds)


rate_limiter = _global_rate_limiter
sync_limiter = _global_sync_limiter

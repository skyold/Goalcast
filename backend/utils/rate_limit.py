"""Token-bucket rate limiter — sync + async."""
from __future__ import annotations
import asyncio
import time
from threading import Lock


class TokenBucket:
    def __init__(self, capacity: int, refill_per_sec: float):
        self.capacity = float(capacity)
        self.refill = float(refill_per_sec)
        self._tokens = float(capacity)
        self._last = time.monotonic()
        self._lock = Lock()

    def _replenish(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last
        self._tokens = min(self.capacity, self._tokens + elapsed * self.refill)
        self._last = now

    def try_acquire(self, n: int = 1) -> bool:
        with self._lock:
            self._replenish()
            if self._tokens >= n:
                self._tokens -= n
                return True
            return False

    async def acquire(self, n: int = 1) -> None:
        while True:
            with self._lock:
                self._replenish()
                if self._tokens >= n:
                    self._tokens -= n
                    return
                shortfall = n - self._tokens
                wait = shortfall / max(self.refill, 1e-9)
            await asyncio.sleep(max(wait, 0.01))

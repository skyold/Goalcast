import time
import asyncio
from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class RateLimitConfig:
    requests_per_second: float
    requests_per_minute: Optional[float] = None
    burst_size: int = 5
    retry_after_429: float = 60.0


class RateLimiter:
    """基于令牌桶算法的异步速率限制器"""

    _instances: Dict[str, 'RateLimiter'] = {}

    def __init__(self, name: str, config: RateLimitConfig):
        self.name = name
        self.config = config
        self.rate = config.requests_per_second
        self.burst = config.burst_size
        self.tokens = float(self.burst)
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()
        self._last_request_time: Optional[float] = None
        self._request_count = 0
        self._minute_start = time.monotonic()

    @classmethod
    def get(cls, name: str, config: RateLimitConfig) -> 'RateLimiter':
        if name not in cls._instances:
            cls._instances[name] = cls(name, config)
        return cls._instances[name]

    @classmethod
    def create(cls, name: str, config: RateLimitConfig) -> 'RateLimiter':
        cls._instances[name] = cls(name, config)
        return cls._instances[name]

    @classmethod
    def reset_all(cls):
        cls._instances.clear()

    async def acquire(self, blocking: bool = True) -> bool:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.last_update = now

            self.tokens = min(self.burst, self.tokens + elapsed * self.rate)

            if self._minute_start and now - self._minute_start >= 60:
                self._request_count = 0
                self._minute_start = now

            if self.config.requests_per_minute and self._request_count >= self.config.requests_per_minute:
                wait_time = 60 - (now - self._minute_start)
                if wait_time > 0:
                    if blocking:
                        await asyncio.sleep(wait_time)
                        self._request_count = 0
                        self._minute_start = time.monotonic()
                    else:
                        return False

            if self.tokens >= 1:
                self.tokens -= 1
                self._request_count += 1
                self._last_request_time = now
                return True

            if blocking:
                wait_time = (1 - self.tokens) / self.rate
                await asyncio.sleep(wait_time)
                self.tokens = 0
                self._request_count += 1
                self._last_request_time = time.monotonic()
                return True

            return False

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    def get_stats(self) -> dict:
        return {
            "name": self.name,
            "rate": self.rate,
            "tokens_available": self.tokens,
            "burst_size": self.burst,
            "request_count_minute": self._request_count,
            "last_request": self._last_request_time,
        }


PROVIDER_RATE_LIMITS = {
    "football_data": RateLimitConfig(
        requests_per_second=1.0,
        requests_per_minute=60,
        burst_size=5,
    ),
    "espn": RateLimitConfig(
        requests_per_second=0.5,
        requests_per_minute=30,
        burst_size=3,
    ),
    "footystats": RateLimitConfig(
        requests_per_second=1.0,
        requests_per_minute=60,
        burst_size=5,
    ),
    "understat": RateLimitConfig(
        requests_per_second=0.5,
        requests_per_minute=30,
        burst_size=3,
    ),
    "clubelo": RateLimitConfig(
        requests_per_second=0.2,
        requests_per_minute=12,
        burst_size=2,
    ),
    "odds": RateLimitConfig(
        requests_per_second=1.0,
        requests_per_minute=60,
        burst_size=5,
    ),
    "weather": RateLimitConfig(
        requests_per_second=3.0,
        requests_per_minute=180,
        burst_size=15,
    ),
    "transfermarkt": RateLimitConfig(
        requests_per_second=0.1,
        requests_per_minute=6,
        burst_size=2,
    ),
}


def get_rate_limiter(provider_name: str) -> RateLimiter:
    config = PROVIDER_RATE_LIMITS.get(provider_name.lower())
    if not config:
        config = RateLimitConfig(requests_per_second=1.0, burst_size=5)
    return RateLimiter.get(provider_name, config)

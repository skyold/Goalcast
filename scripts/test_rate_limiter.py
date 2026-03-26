#!/usr/bin/env python3
import asyncio
import time
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from utils.rate_limiter import RateLimiter, RateLimitConfig, PROVIDER_RATE_LIMITS, get_rate_limiter

print("=== Rate Limiter Test ===")
print()

print("All Rate Limiters:")
for name, config in PROVIDER_RATE_LIMITS.items():
    rpm = config.requests_per_minute or "N/A"
    print(f"  {name}: {config.requests_per_second} req/s ({rpm} req/min)")

print()
print("=== Testing Rate Limiting ===")

async def test_rate_limit():
    limiter = get_rate_limiter("espn")

    print(f"Testing 5 rapid requests with ESPN limiter (0.5 req/s)...")
    start = time.time()
    for i in range(5):
        before = limiter.tokens
        await limiter.acquire()
        after = limiter.tokens
        elapsed = time.time() - start
        print(f"  Request {i+1}: tokens before={before:.2f}, after={after:.2f}, elapsed={elapsed:.2f}s")
    total = time.time() - start
    print(f"Total time for 5 requests: {total:.2f}s (expected ~10s at 0.5 req/s)")

asyncio.run(test_rate_limit())

print()
print("=== Test BaseProvider Rate Limiting ===")

async def test_provider_rate_limit():
    from provider import FootballDataProvider

    print("Testing FootballDataProvider with rate limiting...")
    fd = FootballDataProvider()

    start = time.time()
    for i in range(3):
        print(f"  Request {i+1}...")
        result = await fd.get_matches("Premier League", "2026-03-24", "2026-03-25")
        elapsed = time.time() - start
        print(f"    Done in {elapsed:.2f}s, result: {'OK' if result else 'Failed'}")

asyncio.run(test_provider_rate_limit())

print()
print("=== Rate Limiter Stats ===")
for name in PROVIDER_RATE_LIMITS.keys():
    limiter = get_rate_limiter(name)
    stats = limiter.get_stats()
    print(f"{name}: {stats}")

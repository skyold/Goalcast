import time
import pytest
from utils.rate_limit import TokenBucket


def test_initial_burst_allowed():
    b = TokenBucket(capacity=5, refill_per_sec=1.0)
    for _ in range(5):
        assert b.try_acquire() is True


def test_exhaustion_blocks():
    b = TokenBucket(capacity=2, refill_per_sec=1.0)
    assert b.try_acquire()
    assert b.try_acquire()
    assert b.try_acquire() is False


def test_refill_over_time():
    b = TokenBucket(capacity=2, refill_per_sec=10.0)
    b.try_acquire(); b.try_acquire()
    assert b.try_acquire() is False
    time.sleep(0.25)
    assert b.try_acquire() is True


@pytest.mark.asyncio
async def test_acquire_async_waits_for_refill():
    b = TokenBucket(capacity=1, refill_per_sec=10.0)
    assert b.try_acquire()
    t0 = time.time()
    await b.acquire()
    assert time.time() - t0 >= 0.08

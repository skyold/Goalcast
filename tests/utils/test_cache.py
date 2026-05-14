import time
import pytest
from utils.cache import Cache


@pytest.fixture
def cache(tmp_path):
    return Cache(tmp_path / "cache.db")


def test_set_get_roundtrip(cache):
    cache.set("k1", {"a": 1}, ttl_seconds=60)
    assert cache.get("k1") == {"a": 1}


def test_expiry(cache):
    cache.set("k2", "v", ttl_seconds=1)
    assert cache.get("k2") == "v"
    time.sleep(1.1)
    assert cache.get("k2") is None


def test_permanent_ttl_zero(cache):
    cache.set("k3", "forever", ttl_seconds=0)
    assert cache.get("k3") == "forever"


def test_missing_key_returns_none(cache):
    assert cache.get("nope") is None


def test_delete(cache):
    cache.set("k4", "v", ttl_seconds=60)
    cache.delete("k4")
    assert cache.get("k4") is None

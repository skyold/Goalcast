import json
import time
from pathlib import Path
from typing import Any, Dict, Optional
from config.settings import BASE_DIR

CACHE_DIR = BASE_DIR / "data" / "cache"


class Cache:
    def __init__(self, cache_dir: Path = CACHE_DIR):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, source: str, key: str) -> Path:
        source_dir = self.cache_dir / source
        source_dir.mkdir(parents=True, exist_ok=True)
        safe_key = key.replace("/", "_").replace(":", "_")
        return source_dir / f"{safe_key}.json"

    def get(self, source: str, key: str) -> Optional[Dict[str, Any]]:
        path = self._get_path(source, key)
        if not path.exists():
            return None

        try:
            with open(path, "r") as f:
                data = json.load(f)

            if "expires_at" in data and data["expires_at"] < time.time():
                path.unlink()
                return None

            return data.get("value")
        except (json.JSONDecodeError, IOError):
            return None

    def set(self, source: str, key: str, value: Dict[str, Any], ttl_hours: float = 1.0):
        path = self._get_path(source, key)
        expires_at = time.time() + (ttl_hours * 3600)

        data = {"value": value, "expires_at": expires_at}

        try:
            with open(path, "w") as f:
                json.dump(data, f)
        except IOError:
            pass

    def delete(self, source: str, key: str):
        path = self._get_path(source, key)
        if path.exists():
            path.unlink()

    def clear_source(self, source: str):
        source_dir = self.cache_dir / source
        if source_dir.exists():
            for path in source_dir.iterdir():
                if path.is_file():
                    path.unlink()


_cache = Cache()


def cache_get(source: str, key: str) -> Optional[Dict[str, Any]]:
    return _cache.get(source, key)


def cache_set(source: str, key: str, value: Dict[str, Any], ttl_hours: float = 1.0):
    _cache.set(source, key, value, ttl_hours)


def cache_delete(source: str, key: str):
    _cache.delete(source, key)


def cache_clear_source(source: str):
    _cache.clear_source(source)

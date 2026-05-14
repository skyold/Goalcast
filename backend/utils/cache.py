"""SQLite-backed key/value cache with TTL."""
from __future__ import annotations
import json
import sqlite3
import time
from pathlib import Path
from threading import RLock
from typing import Any, Optional


_SCHEMA = """
CREATE TABLE IF NOT EXISTS cache (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    expires_at INTEGER NOT NULL,
    created_at INTEGER NOT NULL
);
"""


class Cache:
    def __init__(self, db_path: Path):
        db_path = Path(db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._path = str(db_path)
        self._lock = RLock()
        with self._conn() as conn:
            conn.executescript(_SCHEMA)

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path, timeout=5.0)

    def get(self, key: str) -> Optional[Any]:
        with self._lock, self._conn() as conn:
            row = conn.execute(
                "SELECT value, expires_at FROM cache WHERE key = ?", (key,)
            ).fetchone()
        if row is None:
            return None
        value, expires_at = row
        if expires_at != 0 and expires_at <= int(time.time()):
            self.delete(key)
            return None
        return json.loads(value)

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        now = int(time.time())
        expires_at = 0 if ttl_seconds == 0 else now + ttl_seconds
        payload = json.dumps(value)
        with self._lock, self._conn() as conn:
            conn.execute(
                "INSERT INTO cache(key,value,expires_at,created_at) VALUES(?,?,?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value, expires_at=excluded.expires_at",
                (key, payload, expires_at, now),
            )
            conn.commit()

    def delete(self, key: str) -> None:
        with self._lock, self._conn() as conn:
            conn.execute("DELETE FROM cache WHERE key = ?", (key,))
            conn.commit()

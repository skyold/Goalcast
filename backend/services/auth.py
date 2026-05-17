"""Password hashing + JWT issuance + FastAPI `current_user` dependency.

Token policy:
- 7-day expiry, HS256.
- Carried in httpOnly cookie `gc_token` (SameSite=Lax). No refresh — re-login on expiry.
- Secret from `GOALCAST_JWT_SECRET` env var; falls back to a dev-only constant so
  local tests just work. Production deploys MUST set the env var.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import aiosqlite
from fastapi import Cookie, Depends, HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext

from database import get_db

_DEV_SECRET = "dev-only-secret-do-not-use-in-prod"
JWT_SECRET = os.getenv("GOALCAST_JWT_SECRET", _DEV_SECRET)
JWT_ALGORITHM = "HS256"
JWT_TTL_DAYS = 7
COOKIE_NAME = "gc_token"

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


def create_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=JWT_TTL_DAYS)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[int]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        return None


async def get_current_user(
    gc_token: Optional[str] = Cookie(default=None),
    db: aiosqlite.Connection = Depends(get_db),
) -> dict:
    """Strict dependency — 401 if no/invalid token."""
    user = await _resolve_user(gc_token, db)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    return user


async def get_current_user_optional(
    gc_token: Optional[str] = Cookie(default=None),
    db: aiosqlite.Connection = Depends(get_db),
) -> Optional[dict]:
    """Lenient dependency — returns None for anonymous requests. Use on data endpoints
    that want to apply user prefs when logged in but stay public when not."""
    return await _resolve_user(gc_token, db)


async def _resolve_user(token: Optional[str], db: aiosqlite.Connection) -> Optional[dict]:
    if not token:
        return None
    user_id = decode_token(token)
    if user_id is None:
        return None
    async with db.execute(
        "SELECT id, email, created_at FROM users WHERE id=?", (user_id,)
    ) as cur:
        row = await cur.fetchone()
    return dict(row) if row else None


async def get_user_competition_prefs(
    user: Optional[dict],
    db: aiosqlite.Connection,
) -> Optional[set[int]]:
    """Return the set of competition_ids the user has whitelisted, or None for
    anonymous (no filter applies). An empty set means the user is logged in but
    has saved no prefs — data endpoints should return empty results."""
    if user is None:
        return None
    async with db.execute(
        "SELECT competition_id FROM user_competition_prefs WHERE user_id=?",
        (user["id"],),
    ) as cur:
        rows = await cur.fetchall()
    return {r[0] for r in rows}

"""Email + password auth.

Endpoints (prefix /api):
- POST /auth/signup  body: {email, password}  -> sets gc_token cookie, returns {id, email}
- POST /auth/login   body: {email, password}  -> sets gc_token cookie, returns {id, email}
- POST /auth/logout                            -> clears gc_token cookie
- GET  /auth/me                                -> returns current user or 401

Token: httpOnly cookie `gc_token`, SameSite=Lax, 7-day expiry. See services/auth.py.
"""
from __future__ import annotations

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, EmailStr, Field

from database import get_db
from services.auth import (
    COOKIE_NAME,
    JWT_TTL_DAYS,
    create_token,
    get_current_user,
    hash_password,
    verify_password,
)

router = APIRouter()


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    id: int
    email: str


def _set_cookie(resp: Response, token: str) -> None:
    resp.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=JWT_TTL_DAYS * 24 * 60 * 60,
        httponly=True,
        samesite="lax",
        secure=False,  # Production: set True behind HTTPS; flip via env if needed.
        path="/",
    )


@router.post("/auth/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def signup(
    creds: Credentials,
    response: Response,
    db: aiosqlite.Connection = Depends(get_db),
):
    async with db.execute("SELECT id FROM users WHERE email=?", (creds.email,)) as cur:
        if await cur.fetchone():
            raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    pwd_hash = hash_password(creds.password)
    cur = await db.execute(
        "INSERT INTO users (email, password_hash) VALUES (?, ?)",
        (creds.email, pwd_hash),
    )
    user_id = cur.lastrowid
    await db.execute(
        "INSERT INTO user_settings (user_id, locale) VALUES (?, 'zh')", (user_id,)
    )
    await db.commit()
    _set_cookie(response, create_token(user_id))
    return {"id": user_id, "email": creds.email}


@router.post("/auth/login", response_model=UserOut)
async def login(
    creds: Credentials,
    response: Response,
    db: aiosqlite.Connection = Depends(get_db),
):
    async with db.execute(
        "SELECT id, email, password_hash FROM users WHERE email=?", (creds.email,)
    ) as cur:
        row = await cur.fetchone()
    if not row or not verify_password(creds.password, row["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    _set_cookie(response, create_token(row["id"]))
    return {"id": row["id"], "email": row["email"]}


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response):
    response.delete_cookie(key=COOKIE_NAME, path="/")


@router.get("/auth/me", response_model=UserOut)
async def me(user: dict = Depends(get_current_user)):
    return {"id": user["id"], "email": user["email"]}

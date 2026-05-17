"""Per-user settings (whitelist of competitions, locale, ...).

Endpoints (prefix /api):
- GET  /me/competitions          -> {competition_ids: int[]}
- PUT  /me/competitions          body: {competition_ids: int[]}  -> same shape

Whole-set replace semantics keeps the wire format trivial: the client posts the
full set of IDs it wants, server diffs nothing — just `DELETE WHERE user_id=?`
then bulk INSERT inside one transaction.
"""
from __future__ import annotations

from typing import Literal

import aiosqlite
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from database import get_db
from services.auth import get_current_user

router = APIRouter()


class CompetitionPrefs(BaseModel):
    competition_ids: list[int]


class LocalePref(BaseModel):
    locale: Literal["zh", "en"]


@router.get("/me/competitions", response_model=CompetitionPrefs)
async def get_my_competitions(
    user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    async with db.execute(
        "SELECT competition_id FROM user_competition_prefs WHERE user_id=?",
        (user["id"],),
    ) as cur:
        rows = await cur.fetchall()
    return {"competition_ids": [r[0] for r in rows]}


@router.put("/me/competitions", response_model=CompetitionPrefs)
async def put_my_competitions(
    prefs: CompetitionPrefs,
    user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    # dedupe + sort for deterministic storage and easier debugging.
    ids = sorted({int(i) for i in prefs.competition_ids})
    await db.execute("DELETE FROM user_competition_prefs WHERE user_id=?", (user["id"],))
    if ids:
        await db.executemany(
            "INSERT INTO user_competition_prefs (user_id, competition_id) VALUES (?, ?)",
            [(user["id"], cid) for cid in ids],
        )
    await db.commit()
    return {"competition_ids": ids}


@router.get("/me/locale", response_model=LocalePref)
async def get_my_locale(
    user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    async with db.execute(
        "SELECT locale FROM user_settings WHERE user_id=?", (user["id"],)
    ) as cur:
        row = await cur.fetchone()
    return {"locale": (row[0] if row else "zh")}


@router.put("/me/locale", response_model=LocalePref)
async def put_my_locale(
    pref: LocalePref,
    user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    # UPSERT — signup row may exist from auth.signup, but stay safe for migrated users.
    await db.execute(
        """INSERT INTO user_settings (user_id, locale) VALUES (?, ?)
           ON CONFLICT(user_id) DO UPDATE SET locale=excluded.locale""",
        (user["id"], pref.locale),
    )
    await db.commit()
    return {"locale": pref.locale}

"""Per-user settings (whitelist of competitions, locale, ...).

Endpoints (prefix /api):
- GET  /me/competitions          -> {competition_ids: int[]}
- PUT  /me/competitions          body: {competition_ids: int[]}  -> same shape

Whole-set replace semantics keeps the wire format trivial: the client posts the
full set of IDs it wants, server diffs nothing — just `DELETE WHERE user_id=?`
then bulk INSERT inside one transaction.
"""
from __future__ import annotations

import json
from typing import Literal

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from database import get_db
from services.alerts import scan_alerts
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


# ---------- Phase 3: Sharp/Square divergence alerts ----------


class AlertOut(BaseModel):
    id: int
    fixture_id: int
    alert_type: str
    payload: dict
    created_at: str
    expires_at: str


class AlertSettings(BaseModel):
    divergence_threshold: float = Field(ge=0.5, le=50.0, default=5.0)
    enabled: bool = True


@router.get("/me/alerts")
async def list_my_alerts(
    user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Active alerts: not dismissed AND not expired. Joined with fixture data
    so the client can render team names + kickoff without a second roundtrip.
    """
    async with db.execute(
        """SELECT a.id, a.fixture_id, a.alert_type, a.payload, a.created_at, a.expires_at,
                  f.home_team, f.away_team, f.competition_name, f.kickoff_utc,
                  th.name_zh AS home_team_zh, ta.name_zh AS away_team_zh,
                  c.name_zh AS competition_name_zh
           FROM alerts a
           JOIN fixtures f ON f.id = a.fixture_id
           LEFT JOIN teams th ON th.id = f.home_team_id
           LEFT JOIN teams ta ON ta.id = f.away_team_id
           LEFT JOIN competitions c ON c.id = f.competition_id
           WHERE a.user_id = ?
             AND a.dismissed_at IS NULL
             AND datetime(a.expires_at) > datetime('now')
           ORDER BY a.created_at DESC
           LIMIT 50""",
        (user["id"],),
    ) as cur:
        rows = await cur.fetchall()
    items = []
    for r in rows:
        d = dict(r)
        d["payload"] = json.loads(d["payload"])
        items.append(d)
    return {"items": items, "count": len(items)}


@router.post("/me/alerts/{alert_id}/dismiss", status_code=status.HTTP_204_NO_CONTENT)
async def dismiss_alert(
    alert_id: int,
    user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    cur = await db.execute(
        """UPDATE alerts SET dismissed_at = CURRENT_TIMESTAMP
           WHERE id=? AND user_id=? AND dismissed_at IS NULL""",
        (alert_id, user["id"]),
    )
    if cur.rowcount == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Alert not found or already dismissed")
    await db.commit()


@router.get("/me/alert-settings", response_model=AlertSettings)
async def get_alert_settings(
    user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    async with db.execute(
        "SELECT divergence_threshold, enabled FROM user_alert_settings WHERE user_id=?",
        (user["id"],),
    ) as cur:
        row = await cur.fetchone()
    if row is None:
        return AlertSettings()  # defaults
    return {"divergence_threshold": row["divergence_threshold"], "enabled": bool(row["enabled"])}


@router.put("/me/alert-settings", response_model=AlertSettings)
async def put_alert_settings(
    settings: AlertSettings,
    user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    await db.execute(
        """INSERT INTO user_alert_settings (user_id, divergence_threshold, enabled)
           VALUES (?, ?, ?)
           ON CONFLICT(user_id) DO UPDATE SET
             divergence_threshold = excluded.divergence_threshold,
             enabled              = excluded.enabled""",
        (user["id"], settings.divergence_threshold, int(settings.enabled)),
    )
    await db.commit()
    return settings


@router.post("/me/alerts/scan")
async def trigger_scan(
    user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Manual scan trigger — useful for testing and for the user-facing 'check
    now' button. In production the scheduler runs every 5 min independently."""
    inserted = await scan_alerts(db)
    return {"inserted": inserted}

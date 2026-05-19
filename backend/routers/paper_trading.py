"""Paper-trading read endpoints.

V1 surfaces:
  GET /paper-trading/house  — legacy single-band House Book aggregate
                              (filtered by book_type)
  GET /paper-trading/books  — Phase 4b multi-Book list with per-book summary,
                              powers the multi-curve ROI comparison chart
"""
from __future__ import annotations

import json
from typing import Annotated, Optional

import aiosqlite
from fastapi import APIRouter, Depends, Query

from database import get_db
from services import paper_trading as pt_svc
from services.auth import get_current_user_optional

router = APIRouter()


@router.get("/paper-trading/house")
async def get_house(
    book_type: Annotated[str, Query()] = "house_5pct",
    start_bankroll: Annotated[float, Query(gt=0, le=1_000_000)] = 1000.0,
    db: aiosqlite.Connection = Depends(get_db),
):
    return await pt_svc.house_book_summary(
        db, book_type=book_type, start_bankroll=start_bankroll,
    )


@router.get("/paper-trading/books")
async def get_books(
    include_archived: Annotated[bool, Query()] = False,
    user: Optional[dict] = Depends(get_current_user_optional),
    db: aiosqlite.Connection = Depends(get_db),
):
    """List all visible Books with per-book summary metrics.

    Visibility:
      - Anonymous → only House Books (user_id=0)
      - Authenticated → House Books + that user's Personal Books

    Each item carries the static Book fields plus a `summary` block with
    settled/pending counts, current bankroll, ROI, win rate and the bankroll
    timeseries (oldest → newest). The frontend multi-curve ROI chart slices
    the summary.timeseries directly into a polyline.
    """
    where = "WHERE (user_id=0"
    params: list = []
    if user is not None:
        where += " OR user_id=?"
        params.append(user["id"])
    where += ")"
    if not include_archived:
        where += " AND archived_at IS NULL"

    async with db.execute(
        f"""SELECT id, user_id, name, signal_type, signal_version,
                   conditions_json, starting_units, match_scope,
                   created_at, archived_at
            FROM simulated_books {where}
            ORDER BY user_id ASC, id ASC""",
        params,
    ) as cur:
        rows = [dict(r) for r in await cur.fetchall()]

    items: list[dict] = []
    for r in rows:
        summary = await pt_svc.book_summary(
            db, book_id=r["id"], starting_units=r["starting_units"],
        )
        try:
            conditions = json.loads(r["conditions_json"]) if r["conditions_json"] else {}
        except (TypeError, ValueError):
            conditions = {}
        items.append({
            "id":             r["id"],
            "user_id":        r["user_id"],
            "name":           r["name"],
            "signal_type":    r["signal_type"],
            "signal_version": r["signal_version"],
            "conditions":     conditions,
            "starting_units": r["starting_units"],
            "match_scope":    r["match_scope"],
            "scope":          "house" if r["user_id"] == 0 else "personal",
            "created_at":     r["created_at"],
            "archived_at":    r["archived_at"],
            "summary":        summary,
        })
    return {"items": items, "count": len(items)}

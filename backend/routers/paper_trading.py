"""Paper-trading read endpoints — public, audit-style House Book view.

V1 surfaces only House Book aggregates (auto-follow Goalcast signals). Personal
Book POST endpoint + auth-gated reads land in Phase B after 100+ settled bets
prove the design is worth exposing.
"""
from __future__ import annotations

from typing import Annotated

import aiosqlite
from fastapi import APIRouter, Depends, Query

from database import get_db
from services import paper_trading as pt_svc

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

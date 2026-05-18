"""Backtest center read endpoints.

Pure aggregation over historical_predictions × FT fixtures (status='FT').
Cold-start safe: every response includes `samples` count and `enough` flag.
"""
from __future__ import annotations

from typing import Annotated, Optional

import aiosqlite
from fastapi import APIRouter, Depends, Query

from database import get_db
from services import backtest as backtest_svc

router = APIRouter()


@router.get("/backtest/summary")
async def get_summary(
    competition_id: Annotated[Optional[int], Query()] = None,
    waypoint: Annotated[str, Query()] = "kickoff",
    min_samples: Annotated[int, Query(ge=1, le=10000)] = 500,
    db: aiosqlite.Connection = Depends(get_db),
):
    return await backtest_svc.summary(
        db,
        competition_id=competition_id,
        waypoint=waypoint,
        min_samples=min_samples,
    )


@router.get("/backtest/by-league")
async def get_by_league(
    waypoint: Annotated[str, Query()] = "kickoff",
    min_samples: Annotated[int, Query(ge=1, le=10000)] = 100,
    db: aiosqlite.Connection = Depends(get_db),
):
    return await backtest_svc.by_league(
        db, waypoint=waypoint, min_samples=min_samples,
    )

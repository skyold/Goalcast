"""GS-Mispricing — model probability vs de-vigged market probability.

For each fixture × waypoint, computes (model_pct - de_vig_implied_pct) for
each of the three 1X2 outcomes and emits the selection with the largest |Δ|.
Mirrors dedupe logic from routers/insights.py list_mispricings (commit
ba27fab), but reads from waypoint-stamped historical tables instead of the
live predictions / bookmaker_odds upsert tables.

value_json schema:
    {"delta_pct": float,   # signed: positive = model > market
     "selection": "home" | "draw" | "away"}

strength: min(|delta_pct| / 10.0, 1.0)  — |Δ| of 10pp caps at 1.0.
"""
from __future__ import annotations

import json
from typing import ClassVar

import aiosqlite

from .base import BaseSignal, register


@register
class GSMispricing(BaseSignal):
    signal_type: ClassVar[str] = "GS-Mispricing"
    signal_version: ClassVar[str] = "v1.0"
    scope: ClassVar[str] = "public"

    async def compute(
        self,
        db: aiosqlite.Connection,
        fixture_id: int,
        waypoint: str,
    ) -> dict | None:
        async with db.execute(
            """SELECT home_win_pct, draw_pct, away_win_pct
               FROM historical_predictions
               WHERE fixture_id=? AND waypoint=?""",
            (fixture_id, waypoint),
        ) as cur:
            pred = await cur.fetchone()
        if pred is None:
            return None

        async with db.execute(
            """SELECT outcome, odds FROM historical_odds
               WHERE fixture_id=? AND waypoint=?
                 AND bookmaker_id=1 AND market_id=6
                 AND outcome IN ('home','draw','away')""",
            (fixture_id, waypoint),
        ) as cur:
            odds = {r["outcome"]: r["odds"] for r in await cur.fetchall()}
        if any(o not in odds or not odds[o] for o in ("home", "draw", "away")):
            return None

        oh, od, oa = odds["home"], odds["draw"], odds["away"]
        raw_sum = (1.0 / oh) + (1.0 / od) + (1.0 / oa)
        implied = {
            "home": (1.0 / oh) / raw_sum * 100.0,
            "draw": (1.0 / od) / raw_sum * 100.0,
            "away": (1.0 / oa) / raw_sum * 100.0,
        }
        model = {
            "home": pred["home_win_pct"],
            "draw": pred["draw_pct"],
            "away": pred["away_win_pct"],
        }
        deltas = {sel: model[sel] - implied[sel] for sel in ("home", "draw", "away")}

        top_sel = max(deltas, key=lambda s: abs(deltas[s]))
        top_delta = deltas[top_sel]

        return {
            "value_json": json.dumps(
                {"delta_pct": round(top_delta, 2), "selection": top_sel},
                separators=(",", ":"),
            ),
            "strength": min(abs(top_delta) / 10.0, 1.0),
        }

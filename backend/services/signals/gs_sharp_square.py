"""GS-SharpSquare — Pinnacle vs Bet365 de-vigged 1X2 disagreement.

value_json:
    {"selection":    "home" | "draw" | "away",
     "delta_pct":    float (signed; +X% = Pinnacle gives more probability),
     "pinnacle_pct": float,
     "bet365_pct":   float}

strength = min(|delta_pct| / 10.0, 1.0)  — 10pp disagreement caps at 1.0.

Bookmaker IDs follow OddAlerts seed convention: 1 = Pinnacle (sharp),
2 = Bet365 (square). See backend/services/oddalerts.py if those ever change.
"""
from __future__ import annotations

import json
from typing import ClassVar

import aiosqlite

from .base import BaseSignal, register


PINNACLE_ID = 1
BET365_ID = 2


def _devig_1x2(odds: dict[str, float]) -> dict[str, float] | None:
    """De-vigged implied probability percentages per outcome, or None if invalid."""
    if any(o is None or o <= 0 for o in odds.values()):
        return None
    inv = {sel: 1.0 / odds[sel] for sel in odds}
    total = sum(inv.values())
    if total <= 0:
        return None
    return {sel: inv[sel] / total * 100.0 for sel in inv}


@register
class GSSharpSquare(BaseSignal):
    signal_type: ClassVar[str] = "GS-SharpSquare"
    signal_version: ClassVar[str] = "v1.0"
    scope: ClassVar[str] = "member"
    description: ClassVar[str] = "Pinnacle 与 Bet365 de-vig 后 1X2 隐含概率的最大分歧"
    output_schema: ClassVar[dict[str, str]] = {
        "selection":    "home|draw|away — 两书商最大分歧那一面",
        "delta_pct":    "float, signed; +X% = Pinnacle 比 Bet365 更看好该 selection",
        "pinnacle_pct": "float, Pinnacle de-vig 后的隐含 pct",
        "bet365_pct":   "float, Bet365 de-vig 后的隐含 pct",
    }
    strength_formula: ClassVar[str] = "min(|delta_pct| / 10.0, 1.0)"
    failure_modes: ClassVar[list[str]] = [
        "Pinnacle (bookmaker_id=1) 或 Bet365 (bookmaker_id=2) 任一书商的 1X2 三档不全 → 不出信号",
        "任一赔率 ≤ 0 (脏数据) → 不出信号",
    ]

    async def compute(
        self,
        db: aiosqlite.Connection,
        fixture_id: int,
        waypoint: str,
    ) -> dict | None:
        async with db.execute(
            """SELECT bookmaker_id, outcome, odds FROM historical_odds
               WHERE fixture_id=? AND waypoint=? AND market_id=6
                 AND bookmaker_id IN (?, ?)
                 AND outcome IN ('home','draw','away')""",
            (fixture_id, waypoint, PINNACLE_ID, BET365_ID),
        ) as cur:
            rows = await cur.fetchall()

        books: dict[int, dict[str, float]] = {PINNACLE_ID: {}, BET365_ID: {}}
        for r in rows:
            books[r["bookmaker_id"]][r["outcome"]] = r["odds"]

        for bkm in (PINNACLE_ID, BET365_ID):
            if not all(o in books[bkm] for o in ("home", "draw", "away")):
                return None

        pin = _devig_1x2(books[PINNACLE_ID])
        b65 = _devig_1x2(books[BET365_ID])
        if pin is None or b65 is None:
            return None

        deltas = {sel: pin[sel] - b65[sel] for sel in ("home", "draw", "away")}
        top_sel = max(deltas, key=lambda s: abs(deltas[s]))
        top_delta = deltas[top_sel]

        return {
            "value_json": json.dumps(
                {
                    "selection":    top_sel,
                    "delta_pct":    round(top_delta, 2),
                    "pinnacle_pct": round(pin[top_sel], 2),
                    "bet365_pct":   round(b65[top_sel], 2),
                },
                separators=(",", ":"),
            ),
            "strength": min(abs(top_delta) / 10.0, 1.0),
        }

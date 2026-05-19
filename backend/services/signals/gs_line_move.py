"""GS-LineMove — Pinnacle 1X2 odds drift between earliest waypoint and current.

value_json:
    {"selection":    "home" | "draw" | "away",
     "move_pct":     float (signed; +X%/-X% from open),
     "open_odds":    float,
     "current_odds": float}

strength = min(|move_pct| / 20.0, 1.0)  — 20pp move caps at 1.0.
"""
from __future__ import annotations

import json
from typing import ClassVar

import aiosqlite

from .base import BaseSignal, register


# Time-ordered, earliest first. Local copy of services/snapshot.WAYPOINTS keys
# to keep the signal self-contained.
WAYPOINT_ORDER = ("48h", "24h", "6h", "1h", "kickoff")


@register
class GSLineMove(BaseSignal):
    signal_type: ClassVar[str] = "GS-LineMove"
    signal_version: ClassVar[str] = "v1.0"
    scope: ClassVar[str] = "member"
    description: ClassVar[str] = "Pinnacle 1X2 赔率从开盘 waypoint 到当前的最大百分比漂移"
    output_schema: ClassVar[dict[str, str]] = {
        "selection":    "home|draw|away — 漂移幅度最大那一面",
        "move_pct":     "float, signed; +X% / -X% 相对开盘的赔率变动",
        "open_odds":    "float, 最早 waypoint 的 Pinnacle 赔率",
        "current_odds": "float, 当前 waypoint 的 Pinnacle 赔率",
    }
    strength_formula: ClassVar[str] = "min(|move_pct| / 20.0, 1.0)"
    failure_modes: ClassVar[list[str]] = [
        "找不到一个比当前 waypoint 更早的、三档完整的开盘 waypoint → 不出信号",
        "当前 waypoint 三档赔率任一缺失 → 不出信号",
        "开盘 waypoint == 当前 waypoint (信号要求至少跨一个 waypoint) → 不出信号",
    ]

    async def compute(
        self,
        db: aiosqlite.Connection,
        fixture_id: int,
        waypoint: str,
    ) -> dict | None:
        async with db.execute(
            """SELECT waypoint, outcome, odds FROM historical_odds
               WHERE fixture_id=? AND bookmaker_id=1 AND market_id=6
                 AND outcome IN ('home','draw','away')""",
            (fixture_id,),
        ) as cur:
            rows = await cur.fetchall()
        if not rows:
            return None

        by_wp: dict[str, dict[str, float]] = {}
        for r in rows:
            wp = r["waypoint"]
            if wp not in WAYPOINT_ORDER:
                continue
            by_wp.setdefault(wp, {})[r["outcome"]] = r["odds"]

        opening_wp: str | None = None
        for wp in WAYPOINT_ORDER:
            if wp in by_wp and all(o in by_wp[wp] for o in ("home", "draw", "away")):
                opening_wp = wp
                break
        if opening_wp is None or opening_wp == waypoint:
            return None

        if waypoint not in by_wp:
            return None
        current = by_wp[waypoint]
        if not all(o in current for o in ("home", "draw", "away")):
            return None
        opening = by_wp[opening_wp]

        deltas: dict[str, dict[str, float]] = {}
        for sel in ("home", "draw", "away"):
            op = opening[sel]
            cu = current[sel]
            if op <= 0:
                return None
            move_pct = (cu - op) / op * 100.0
            deltas[sel] = {"move_pct": move_pct, "open": op, "current": cu}

        top_sel = max(deltas, key=lambda s: abs(deltas[s]["move_pct"]))
        top = deltas[top_sel]

        return {
            "value_json": json.dumps(
                {
                    "selection":    top_sel,
                    "move_pct":     round(top["move_pct"], 2),
                    "open_odds":    round(top["open"],    3),
                    "current_odds": round(top["current"], 3),
                },
                separators=(",", ":"),
            ),
            "strength": min(abs(top["move_pct"]) / 20.0, 1.0),
        }

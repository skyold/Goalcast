"""GS-KEN-HT-EV — 上半场平手盘 EV 5%~28% 反推香港盘赔率区间.

Mirrors docs/OA_HT_V2.py — but as a Pure Function on the snapshot pipeline.

The signal fires only when the FT main AH line sits in {0, ±0.25, ±0.5}
(平手 / 平半 / 半球, i.e. the script's "上半场自动筛选" band), because the
EV-on-draw-AH framing assumes a near-balanced match. Output reports the
香港 odds bands for betting the HT 平手盘 (draw, line=0) at EV=5% and EV=28%,
derived from the de-vigged 2-way HT 1X2 probabilities.

Math (verbatim from OA_HT_V2.py):
    rH, rA  = ht_home_pct / 100, ht_away_pct / 100
    eff_h   = rH / (rH + rA)                  # de-vig: drop draw, renormalise
    eff_a   = rA / (rH + rA)
    hk_h_ev = (ev + eff_a) / eff_h            # HK odds for HT-draw-AH home at EV
    hk_a_ev = (ev + eff_h) / eff_a            # HK odds for HT-draw-AH away at EV

value_json schema:
    {"ah_line":      float,
     "ah_label":     "draw" | "draw_half_home" | "draw_half_away"
                                | "half_home" | "half_away",
     "ht_home_pct":  float, "ht_draw_pct": float, "ht_away_pct": float,
     "eff_home":     float, "eff_away":    float,
     "hk_home_5":    float, "hk_home_28":  float,
     "hk_away_5":    float, "hk_away_28":  float,
     "selection":    "home" | "away"}

strength = min(2 * |eff_home - 0.5|, 1.0).
"""
from __future__ import annotations

import json
from typing import ClassVar

import aiosqlite

from services.ah import parse_ah_outcome_line

from .base import BaseSignal, register

# BET365 first (popular reference book per OA_HT_V2.py), Pinnacle fallback.
_BOOKMAKER_PRIORITY: tuple[int, ...] = (2, 1)

_AH_LABEL_BY_LINE: dict[float, str] = {
    0.0:   "draw",
    -0.25: "draw_half_home",
    0.25:  "draw_half_away",
    -0.5:  "half_home",
    0.5:   "half_away",
}


def _derive_main_line_from_history(
    rows: list[dict], bookmaker_id: int,
) -> tuple[float, float, float] | None:
    """Pick the AH line whose two-side odds are closest to each other for the
    given bookmaker. Mirrors services.ah.derive_main_ah_line, adapted for
    historical_odds rows whose odds field is named `odds` (not `current`)."""
    buckets: dict[float, dict[str, float]] = {}
    for r in rows:
        if r["bookmaker_id"] != bookmaker_id or r["market_id"] != 51:
            continue
        parsed = parse_ah_outcome_line(r["outcome"])
        if parsed is None:
            continue
        side, line = parsed
        home_line = line if side == "home" else -line
        try:
            o = float(r["odds"] or 0)
        except (TypeError, ValueError):
            continue
        if o <= 0:
            continue
        buckets.setdefault(home_line, {})[side] = o
    candidates = [
        (ln, b["home"], b["away"])
        for ln, b in buckets.items()
        if "home" in b and "away" in b
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda t: abs(t[1] - t[2]))


@register
class GSHtEv(BaseSignal):
    signal_type: ClassVar[str] = "GS-KEN-HT-EV"
    signal_version: ClassVar[str] = "v1.0"
    scope: ClassVar[str] = "public"

    async def compute(
        self,
        db: aiosqlite.Connection,
        fixture_id: int,
        waypoint: str,
    ) -> dict | None:
        async with db.execute(
            """SELECT home_win_ht_pct, draw_ht_pct, away_win_ht_pct
               FROM historical_predictions
               WHERE fixture_id=? AND waypoint=?""",
            (fixture_id, waypoint),
        ) as cur:
            pred = await cur.fetchone()
        if pred is None:
            return None
        ht_h = pred["home_win_ht_pct"]
        ht_d = pred["draw_ht_pct"]
        ht_a = pred["away_win_ht_pct"]
        if ht_h is None or ht_d is None or ht_a is None:
            return None
        if ht_h <= 0 or ht_a <= 0:
            return None

        async with db.execute(
            """SELECT bookmaker_id, market_id, outcome, odds
               FROM historical_odds
               WHERE fixture_id=? AND waypoint=? AND market_id=51""",
            (fixture_id, waypoint),
        ) as cur:
            ah_rows = [dict(r) for r in await cur.fetchall()]
        if not ah_rows:
            return None

        main: tuple[float, float, float] | None = None
        for bk in _BOOKMAKER_PRIORITY:
            main = _derive_main_line_from_history(ah_rows, bk)
            if main is not None:
                break
        if main is None:
            return None
        ah_line, _oh, _oa = main
        if ah_line not in _AH_LABEL_BY_LINE:
            return None

        rH = ht_h / 100.0
        rA = ht_a / 100.0
        eff_h = rH / (rH + rA)
        eff_a = rA / (rH + rA)

        def _hk(side_prob: float, opp_prob: float, ev: float) -> float:
            return (ev + opp_prob) / side_prob

        value = {
            "ah_line":     ah_line,
            "ah_label":    _AH_LABEL_BY_LINE[ah_line],
            "ht_home_pct": round(ht_h, 2),
            "ht_draw_pct": round(ht_d, 2),
            "ht_away_pct": round(ht_a, 2),
            "eff_home":    round(eff_h, 4),
            "eff_away":    round(eff_a, 4),
            "hk_home_5":   round(_hk(eff_h, eff_a, 0.05), 3),
            "hk_home_28":  round(_hk(eff_h, eff_a, 0.28), 3),
            "hk_away_5":   round(_hk(eff_a, eff_h, 0.05), 3),
            "hk_away_28":  round(_hk(eff_a, eff_h, 0.28), 3),
            "selection":   "home" if eff_h >= eff_a else "away",
        }

        return {
            "value_json": json.dumps(value, separators=(",", ":")),
            "strength":   min(2.0 * abs(eff_h - 0.5), 1.0),
        }

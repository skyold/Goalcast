"""GS-KEN-HT-EV — 上半场平手盘 EV 5%~28% 反推香港盘赔率区间.

Inspired by docs/OA_HT_V2.py — but with the EV formula corrected to honour
the HT-draw-AH (line=0) push semantic. The reference script's formula
(`eff_h = rH / (rH + rA)`, then `hk = (ev + eff_a) / eff_h`) silently
2-way de-vigged the HT-draw probability, which gives the wrong fair-odds
threshold. We use the **raw** HT 1X2 probabilities directly because the
draw outcome is a refund (push), contributing 0 to EV.

Settlement (HT-平手盘, line=0):
    - HT home leads → bet home wins, bet away loses
    - HT away leads → bet home loses, bet away wins
    - HT draw → push (stake refunded, pnl = 0)

EV math (HK odds, 1u stake):
    EV(bet home) = o · P_home_HT - 1 · P_away_HT + 0 · P_draw_HT
                 = o · P_home_HT - P_away_HT
    Setting EV = X and solving for o:
        o_home = (X + P_away_HT) / P_home_HT
        o_away = (X + P_home_HT) / P_away_HT
    (No draw term — push contributes 0.)

The signal fires only when the FT main AH line sits in {0, ±0.25, ±0.5}
(平手 / 平半 / 半球, i.e. the script's "上半场自动筛选" band), because the
EV-on-draw-AH framing assumes a near-balanced match.

value_json schema:
    {"ah_line":      float,
     "ah_label":     "draw" | "draw_half_home" | "draw_half_away"
                                | "half_home" | "half_away",
     "p_home_ht":    float, "p_draw_ht": float, "p_away_ht": float,
                                                # raw HT 1X2 probabilities (0..1)
     "hk_home_5":    float, "hk_home_28":  float,
     "hk_away_5":    float, "hk_away_28":  float,
     "selection":    "home" | "away"}   # model's stronger HT side

strength = min(|p_home_ht - p_away_ht| · 2, 1.0) — asymmetry of HT
probabilities, normalised so a 50pp gap caps at 1.0.
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
    description: ClassVar[str] = "上半场平手盘 EV 5%~28% 反推香港盘赔率区间"
    output_schema: ClassVar[dict[str, str]] = {
        "ah_line":    "float, FT 主盘从主队视角",
        "ah_label":   "draw|draw_half_home|draw_half_away|half_home|half_away",
        "p_home_ht": "float (0..1), OA 模型 HT 主胜概率(原始,未 de-vig)",
        "p_draw_ht": "float (0..1), OA 模型 HT 平局概率(EV 计算时 = push 贡献 0)",
        "p_away_ht": "float (0..1), OA 模型 HT 客胜概率(原始)",
        "hk_home_5":  "float, 主队 HT 平手盘 EV=5% 应得 HK 赔率: (0.05 + p_away_ht) / p_home_ht",
        "hk_home_28": "float, 主队 HT 平手盘 EV=28% 应得 HK 赔率: (0.28 + p_away_ht) / p_home_ht",
        "hk_away_5":  "float, 客队 HT 平手盘 EV=5% 应得 HK 赔率: (0.05 + p_home_ht) / p_away_ht",
        "hk_away_28": "float, 客队 HT 平手盘 EV=28% 应得 HK 赔率: (0.28 + p_home_ht) / p_away_ht",
        "selection":  "home|away — 原始 HT 概率较高的一面",
    }
    strength_formula: ClassVar[str] = "min(2 * |p_home_ht - p_away_ht|, 1.0)"
    failure_modes: ClassVar[list[str]] = [
        "FT 主盘 AH 不在 {0, ±0.25, ±0.5} 区间 → 不出信号",
        "historical_predictions HT 1X2 任一列 NULL → 不出信号",
        "BET365 (id=2) 与 Pinnacle (id=1) 都缺 AH market_id=51 行 → 不出信号",
        "HT 主胜或客胜概率 ≤ 0 (脏数据) → 不出信号",
    ]

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

        # RAW HT 1X2 probabilities (no 2-way de-vig). The HT-平手盘 push
        # contributes 0 to EV, so we don't drop the draw probability.
        rH = ht_h / 100.0
        rD = ht_d / 100.0
        rA = ht_a / 100.0

        def _hk(side_prob: float, opp_prob: float, ev: float) -> float:
            """HK fair odds for `EV(side) = side · o - opp = ev` → o = (ev + opp) / side.
            See module docstring §"EV math" for derivation."""
            return (ev + opp_prob) / side_prob

        value = {
            "ah_line":    ah_line,
            "ah_label":   _AH_LABEL_BY_LINE[ah_line],
            "p_home_ht":  round(rH, 4),
            "p_draw_ht":  round(rD, 4),
            "p_away_ht":  round(rA, 4),
            "hk_home_5":  round(_hk(rH, rA, 0.05), 3),
            "hk_home_28": round(_hk(rH, rA, 0.28), 3),
            "hk_away_5":  round(_hk(rA, rH, 0.05), 3),
            "hk_away_28": round(_hk(rA, rH, 0.28), 3),
            "selection":  "home" if rH >= rA else "away",
        }

        return {
            "value_json": json.dumps(value, separators=(",", ":")),
            # asymmetry of raw HT probabilities; 50pp gap → strength=1.0
            "strength":   min(2.0 * abs(rH - rA), 1.0),
        }

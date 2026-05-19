"""GS-KEN-HT-EV — 上半场平手盘 EV 5%~28% 反推香港盘赔率区间.

Verbatim port of docs/OA_HT_V2.py:281-288 (author-confirmed). The signal
lists the upper/lower water-line of HK odds at which a HT-平手盘 (line=0)
bet would clear the author's EV thresholds, computed in **2-way de-vigged
HT probability space** (the HT-draw outcome is folded out via
`eff_h = rH / (rH + rA)` before EV is applied).

Author's EV convention (`hk = (EV + eff_a) / eff_h`):
    eff_h = rH / (rH + rA)        # de-vig: drop HT draw, renormalise
    eff_a = rA / (rH + rA)
    hk_h_ev = (ev + eff_a) / eff_h   # HK odds at de-vigged EV = ev for home
    hk_a_ev = (ev + eff_h) / eff_a   # ...away

EV thresholds: 5% (下线/lower bound) and 28% (上线/upper bound). The signal
emits both bands as 4 numbers per side so users see the full water-line
range. Anything beyond the upper line is exceptional value; below the
lower line is sub-threshold.

Filter: signal fires only when the FT main AH line sits in
{0, ±0.25, ±0.5} (平手 / 平半 / 半球), i.e. near-balanced matches where
the HT-平手盘 framing applies. AH main line is picked at the closest-odds
balance per bookmaker, preferring BET365 (id=2) then Pinnacle (id=1).

value_json schema:
    {"ah_line":      float,
     "ah_label":     "draw" | "draw_half_home" | "draw_half_away"
                                | "half_home" | "half_away",
     "ht_home_pct":  float, "ht_draw_pct": float, "ht_away_pct": float,
     "eff_home":     float, "eff_away":    float,
     "hk_home_5":    float, "hk_home_28":  float,
     "hk_away_5":    float, "hk_away_28":  float,
     "selection":    "home" | "away"}

strength = min(2 * |eff_home - 0.5|, 1.0) — de-vigged 2-way asymmetry.
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
    given bookmaker. Mirrors services.ah.derive_main_ah_line and matches
    OA_HT_V2.py:113-123 — only lines whose **both** sides have odds in
    [0.6, 2.5] are considered candidates (filters out extreme handicaps
    that shouldn't be treated as the "main line")."""
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
    # Per OA_HT_V2.py:119 — both sides' odds must be in [0.6, 2.5] for a
    # line to qualify as the "main line" candidate. Lines outside this
    # band are extreme handicaps (e.g. home_-2 with odds 5.0 vs 1.15).
    candidates = [
        (ln, b["home"], b["away"])
        for ln, b in buckets.items()
        if "home" in b and "away" in b
           and 0.6 <= b["home"] <= 2.5
           and 0.6 <= b["away"] <= 2.5
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda t: abs(t[1] - t[2]))


@register
class GSHtEv(BaseSignal):
    signal_type: ClassVar[str] = "GS-KEN-HT-EV"
    signal_version: ClassVar[str] = "v1.0"
    scope: ClassVar[str] = "public"
    # Settles on AH market_id=51 at HT 平手盘 (line=0), not FT 1X2 (market_id=6).
    # Phase A of paper-trading-realism PRD: this gates the signal out of the
    # 1X2-only place_bets_for_books loop until Phase B adds AH settlement.
    settle_market: ClassVar[tuple[int, str]] = (51, "AH_0_HT")
    description: ClassVar[str] = "上半场平手盘 EV 5%~28% 反推香港盘赔率区间"
    output_schema: ClassVar[dict[str, str]] = {
        "ah_line":     "float, FT 主盘从主队视角",
        "ah_label":    "draw|draw_half_home|draw_half_away|half_home|half_away",
        "ht_home_pct": "float, OA 模型 HT 主胜概率 (0-100)",
        "ht_draw_pct": "float, OA 模型 HT 平局概率 (0-100)",
        "ht_away_pct": "float, OA 模型 HT 客胜概率 (0-100)",
        "eff_home":    "float, 2-way de-vig 后主胜概率 = home/(home+away)",
        "eff_away":    "float, 2-way de-vig 后客胜概率 = away/(home+away)",
        "hk_home_5":   "float, 主队 EV=5% (下线) HK 水位赔率",
        "hk_home_28":  "float, 主队 EV=28% (上线) HK 水位赔率",
        "hk_away_5":   "float, 客队 EV=5% (下线) HK 水位赔率",
        "hk_away_28":  "float, 客队 EV=28% (上线) HK 水位赔率",
        "selection":   "home|away — 2-way de-vig 后概率更高那一面",
    }
    strength_formula: ClassVar[str] = "min(2 * |eff_home - 0.5|, 1.0)"
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

        rH = ht_h / 100.0
        rA = ht_a / 100.0
        # 2-way de-vig: drop HT-draw probability and renormalise. Author's
        # EV convention operates in this de-vigged space (see module docstring).
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

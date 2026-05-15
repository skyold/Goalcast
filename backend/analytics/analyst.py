"""Deterministic Analyst — generates a short Chinese summary from analytics output.

No LLM dependency. Template-based on (pick, ev, confidence_stars, model_prob).
Swap for ClaudeAdapter call when LLM credentials and role definitions are wired.
"""
from __future__ import annotations
from typing import Optional


_PICK_LABEL = {"H": "主胜", "D": "平局", "A": "客胜"}


def generate_summary(analysis: dict | None, fixture: dict | None = None) -> Optional[str]:
    """Return a 1-2 sentence Chinese narrative, or None if input too sparse.

    Args:
        analysis: MatchRecord.analysis dict (model_prob, pick, ev, kelly, confidence_stars, ...)
        fixture:  Optional fixture context for team names (currently unused, reserved).
    """
    if not isinstance(analysis, dict):
        return None
    pick = analysis.get("pick")
    if pick not in _PICK_LABEL:
        return None

    model_prob = analysis.get("model_prob") or {}
    pick_prob = model_prob.get(pick)
    ev = analysis.get("ev")
    stars = analysis.get("confidence_stars", 0)
    kelly = analysis.get("kelly")

    if pick_prob is None or ev is None:
        return None

    pick_label = _PICK_LABEL[pick]
    prob_pct = pick_prob * 100
    ev_pct = ev * 100
    stars_int = int(stars or 0)
    star_str = "★" * stars_int + "☆" * (5 - stars_int)

    # First sentence: probability + recommendation
    lead = f"模型评估 {pick_label} 概率约 {prob_pct:.1f}%，对应预期收益 {ev_pct:+.1f}%。"

    # Second sentence: confidence + sizing
    if ev_pct <= 0:
        tail = f"置信度 {star_str}（{stars_int}/5），预期收益为非正，建议观望。"
    elif stars_int >= 4 and ev_pct >= 3:
        kelly_str = f"，Kelly 建议仓位 {kelly * 100:.2f}%" if isinstance(kelly, (int, float)) else ""
        tail = f"置信度 {star_str}（{stars_int}/5），赔率结构与模型一致，可重点关注{kelly_str}。"
    elif stars_int >= 3:
        tail = f"置信度 {star_str}（{stars_int}/5），存在正向期望，建议小注尝试。"
    else:
        tail = f"置信度 {star_str}（{stars_int}/5），信号偏弱，建议观望。"

    return lead + tail

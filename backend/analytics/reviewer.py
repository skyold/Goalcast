"""Deterministic Reviewer — rule-based pass/fail/skip verdict on Analyst output.

No LLM dependency. Based on EV, confidence stars, and analysis completeness.
"""
from __future__ import annotations
from typing import Literal, Optional


Verdict = Literal["pass", "fail", "skip"]


# Thresholds — tune in SettingsPage in future.
MIN_EV_PCT = 2.0       # Minimum positive EV for pass
MIN_STARS = 3          # Minimum confidence stars
MAX_EV_PCT_SUSPICIOUS = 30.0  # Above this, model likely overshot — skip


def review(analysis: dict | None) -> Optional[Verdict]:
    """Return verdict, or None if analysis missing / unreviewable."""
    if not isinstance(analysis, dict):
        return None
    ev = analysis.get("ev")
    stars = analysis.get("confidence_stars")
    pick = analysis.get("pick")
    if ev is None or stars is None or pick is None:
        return None
    ev_pct = ev * 100
    stars_int = int(stars)

    # Skip degenerate / suspicious cases
    if ev_pct > MAX_EV_PCT_SUSPICIOUS:
        return "skip"

    # Pass: positive EV above threshold AND confident
    if ev_pct >= MIN_EV_PCT and stars_int >= MIN_STARS:
        return "pass"

    return "fail"

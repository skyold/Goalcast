"""Extract analytics-ready features from raw OddAlerts API responses.

Bridges:
- `/api/stats` season-type payloads → Poisson λ inputs
- `/api/odds/history` → closing 1X2 odds
- `/api/trends/...` → 1X2 prior probabilities

After the 2026-05-14 single-source pivot, these are the only mapping
adapters the analytics layer needs.
"""
from __future__ import annotations
from typing import Any, Optional


def extract_team_lambdas(
    home_stats: dict[str, Any],
    away_stats: dict[str, Any],
) -> Optional[dict[str, Any]]:
    """Compute home_lambda / away_lambda from OddAlerts season-stats payloads.

    Signal preference: xg_for > goals_for_avg (xG is more predictive).
    Returns None if either team lacks both attack and defense signal.

    Output:
        {
          "home_lambda": float,
          "away_lambda": float,
          "source": "oddalerts_stats",
        }
    """
    def _team_lambda(team_for: dict, opp_against: dict) -> Optional[float]:
        for_signal = team_for.get("xg_for") or team_for.get("goals_for_avg")
        against_signal = (
            opp_against.get("xg_against") or opp_against.get("goals_against_avg")
        )
        if for_signal is None or against_signal is None:
            return None
        # Weighted blend: 60% own attack, 40% opponent defense leakage.
        return float(for_signal) * 0.6 + float(against_signal) * 0.4

    lam_h = _team_lambda(home_stats, away_stats)
    lam_a = _team_lambda(away_stats, home_stats)
    if lam_h is None or lam_a is None:
        return None

    return {
        "home_lambda": round(lam_h, 4),
        "away_lambda": round(lam_a, 4),
        "source": "oddalerts_stats",
    }


def extract_market_odds(
    odds_history: dict[str, Any],
    market: str = "ft_result",
    bookmaker: str = "Bet365",
) -> Optional[dict[str, float]]:
    """Pull closing 1X2 odds for the requested market/bookmaker.

    Returns {"H": ..., "D": ..., "A": ...} or None if any of the three
    direction closings is missing/non-numeric.
    """
    try:
        block = odds_history["markets"][market][bookmaker]
        return {
            "H": float(block["home"]["closing"]),
            "D": float(block["draw"]["closing"]),
            "A": float(block["away"]["closing"]),
        }
    except (KeyError, TypeError, ValueError):
        return None


def extract_trend_priors(trends: dict[str, Any]) -> dict[str, float]:
    """Convert OddAlerts trends.{homeWin, awayWin, btts} into 1X2 prior probs.

    Draw is implied: D = clamp(1 - H - A, 0, 1).
    """
    h = float(trends.get("homeWin") or 0.0)
    a = float(trends.get("awayWin") or 0.0)
    d = max(0.0, 1.0 - h - a)
    return {"H": h, "D": d, "A": a}

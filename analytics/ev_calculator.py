"""
Goalcast EV & Kelly Calculator
==============================

Deterministic calculation of:
1. Expected Value (EV) per direction
2. Kelly Criterion fraction
3. Risk-adjusted EV

All math is precise — no LLM approximation.
"""

from typing import Dict, Optional


def calculate_ev(
    model_probability: float,
    market_odds: float,
) -> Dict:
    """
    Calculate Expected Value for a single direction.

    EV = model_prob × odds - 1

    Args:
        model_probability: Model's probability as percentage (0-100)
        market_odds: Decimal odds from bookmaker (e.g., 1.85, 3.50)

    Returns:
        {
            "ev": float,              # Raw EV value
            "ev_pct": float,          # EV as percentage
            "is_value": bool,         # Whether EV > 0
            "break_even_odds": float  # Odds needed for EV = 0
        }
    """
    prob_decimal = model_probability / 100.0

    if market_odds <= 0:
        return {
            "ev": 0.0,
            "ev_pct": 0.0,
            "is_value": False,
            "break_even_odds": None,
            "error": "Invalid market odds (<= 0)",
        }

    ev = prob_decimal * market_odds - 1.0
    break_even = 1.0 / prob_decimal if prob_decimal > 0 else None

    return {
        "ev": round(ev, 4),
        "ev_pct": round(ev * 100, 2),
        "is_value": ev > 0,
        "break_even_odds": round(break_even, 4) if break_even else None,
    }


def calculate_kelly(
    model_probability: float,
    market_odds: float,
    fraction: float = 0.25,
    bankroll: Optional[float] = None,
) -> Dict:
    """
    Calculate Kelly Criterion stake recommendation.

    f* = (b × p - q) / b
    where:
        b = odds - 1 (net odds)
        p = model probability (decimal)
        q = 1 - p

    Uses fractional Kelly (default 25%) for risk management.

    Args:
        model_probability: Model's probability as percentage (0-100)
        market_odds: Decimal odds
        fraction: Fraction of full Kelly (0.25 = quarter Kelly)
        bankroll: Optional total bankroll for absolute stake

    Returns:
        {
            "full_kelly_pct": float,   # Full Kelly as % of bankroll
            "fractional_kelly_pct": float,  # Actual recommended %
            "stake": float,            # Absolute stake if bankroll provided
            "ev": float,               # EV for this bet
            "recommended": bool        # Whether to bet (Kelly > 0)
        }
    """
    prob = model_probability / 100.0
    b = market_odds - 1.0  # Net odds
    q = 1.0 - prob

    if b <= 0 or market_odds <= 1.0:
        return {
            "full_kelly_pct": 0.0,
            "fractional_kelly_pct": 0.0,
            "stake": 0.0,
            "ev": 0.0,
            "recommended": False,
            "error": "Invalid odds",
        }

    full_kelly = (b * prob - q) / b

    if full_kelly <= 0:
        return {
            "full_kelly_pct": 0.0,
            "fractional_kelly_pct": 0.0,
            "stake": 0.0,
            "ev": round(prob * market_odds - 1, 4),
            "recommended": False,
        }

    frac_kelly = full_kelly * fraction
    stake = frac_kelly * bankroll if bankroll else None

    return {
        "full_kelly_pct": round(full_kelly * 100, 4),
        "fractional_kelly_pct": round(frac_kelly * 100, 4),
        "stake": round(stake, 2) if stake is not None else None,
        "ev": round(prob * market_odds - 1, 4),
        "recommended": True,
    }


def calculate_risk_adjusted_ev(
    raw_ev: float,
    lineup_uncertainty: bool = False,
    market_low_confidence: bool = False,
    data_quality: str = "medium",
) -> float:
    """
    Apply risk multipliers to raw EV.

    Risk factors (multiplicative):
    - lineup_uncertainty: × 0.85
    - market_low_confidence: × 0.90
    - data_quality=low: × 0.80

    Args:
        raw_ev: Raw expected value
        lineup_uncertainty: True if lineup data unavailable
        market_low_confidence: True if market analysis is low confidence
        data_quality: "low", "medium", or "high"

    Returns:
        Risk-adjusted EV value
    """
    multiplier = 1.0

    if lineup_uncertainty:
        multiplier *= 0.85
    if market_low_confidence:
        multiplier *= 0.90
    if data_quality == "low":
        multiplier *= 0.80

    return round(raw_ev * multiplier, 4)


def best_bet_recommendation(
    ev_home: float,
    ev_draw: float,
    ev_away: float,
    risk_adjusted: bool = False,
    ev_adj_home: float = None,
    ev_adj_draw: float = None,
    ev_adj_away: float = None,
    confidence: int = 50,
) -> Dict:
    """
    Determine the best bet direction based on EV values.

    v2.5 thresholds:
    - EV > 0.08 → 推荐
    - EV 0.04~0.08 → 小注
    - EV < 0.04 → 不推荐

    v3.0 thresholds (with risk adjustment):
    - EV_adj > 0.10 & confidence > 70 → 推荐
    - EV_adj 0.05~0.10 & confidence >= 60 → 小注
    - EV_adj < 0.05 → 不推荐

    Returns:
        {
            "best_bet": "主胜 | 平 | 客胜 | 不推荐",
            "bet_rating": "推荐 | 小注 | 不推荐",
            "max_ev": float,
            "max_ev_direction": str
        }
    """
    ev_map = {"home": ev_home, "draw": ev_draw, "away": ev_away}
    if risk_adjusted and ev_adj_home is not None:
        ev_map = {"home": ev_adj_home, "draw": ev_adj_draw, "away": ev_adj_away}

    best_direction = max(ev_map, key=ev_map.get)
    max_ev = ev_map[best_direction]

    direction_map = {"home": "主胜", "draw": "平", "away": "客胜"}

    if risk_adjusted:
        # v3.0 thresholds
        if max_ev > 0.10 and confidence > 70:
            rating = "推荐"
        elif max_ev >= 0.05 and confidence >= 60:
            rating = "小注"
        else:
            rating = "不推荐"
    else:
        # v2.5 thresholds
        if max_ev > 0.08:
            rating = "推荐"
        elif max_ev >= 0.04:
            rating = "小注"
        else:
            rating = "不推荐"

    if max_ev <= 0:
        return {
            "best_bet": "不推荐",
            "bet_rating": "不推荐",
            "max_ev": round(max_ev, 4),
            "max_ev_direction": "none",
        }

    return {
        "best_bet": direction_map.get(best_direction, "不推荐"),
        "bet_rating": rating,
        "max_ev": round(max_ev, 4),
        "max_ev_direction": best_direction,
    }

"""
Goalcast Poisson Distribution Engine
====================================

Calculates score probability matrices using:
1. Standard Poisson (v2.5)
2. Dixon-Coles corrected Poisson (v3.0)

All computation is deterministic — no LLM "mental math".
"""

import math
from typing import Dict, List, Tuple


def poisson_pmf(k: int, lam: float) -> float:
    """P(k;λ) = e^(-λ) × λ^k / k!"""
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def poisson_distribution(
    home_lambda: float,
    away_lambda: float,
    max_goals: int = 6,
) -> Dict:
    """
    Standard Poisson distribution for match scorelines.

    Args:
        home_lambda: Expected goals for home team (λ_home)
        away_lambda: Expected goals for away team (λ_away)
        max_goals: Maximum goals to model per side (default 6, covers 0-6)

    Returns:
        {
            "score_matrix": [[P(0-0), P(0-1), ...], ...],
            "home_win_pct": float,
            "draw_pct": float,
            "away_win_pct": float,
            "top_scores": [{"score": "X-X", "probability_pct": float}, ...],
            "over_25_pct": float,
            "btts_pct": float,
        }
    """
    matrix: List[List[float]] = []
    home_win = 0.0
    draw = 0.0
    away_win = 0.0
    over_25 = 0.0
    btts = 0.0
    score_probs: List[Tuple[str, float]] = []

    for i in range(max_goals + 1):  # home goals
        row = []
        for j in range(max_goals + 1):  # away goals
            p = poisson_pmf(i, home_lambda) * poisson_pmf(j, away_lambda)
            row.append(p)
            score_label = f"{i}-{j}"
            score_probs.append((score_label, p * 100))

            if i > j:
                home_win += p
            elif i == j:
                draw += p
            else:
                away_win += p

            if i + j > 2.5:
                over_25 += p
            if i > 0 and j > 0:
                btts += p

        matrix.append(row)

    # Normalize to ensure probabilities sum to 1
    total = home_win + draw + away_win
    if total > 0 and abs(total - 1.0) > 1e-10:
        home_win /= total
        draw /= total
        away_win /= total

    # Top scores
    score_probs.sort(key=lambda x: x[1], reverse=True)
    top_scores = [
        {"score": label, "probability_pct": round(prob, 2)}
        for label, prob in score_probs[:5]
    ]

    return {
        "score_matrix": [[round(p, 6) for p in row] for row in matrix],
        "home_win_pct": round(home_win * 100, 4),
        "draw_pct": round(draw * 100, 4),
        "away_win_pct": round(away_win * 100, 4),
        "top_scores": top_scores,
        "over_25_pct": round(over_25 * 100, 4),
        "btts_pct": round(btts * 100, 4),
        "lambda_home": home_lambda,
        "lambda_away": away_lambda,
    }


def _dixon_coles_tau(
    home_goals: int,
    away_goals: int,
    home_lambda: float,
    away_lambda: float,
    rho: float,
) -> float:
    """
    Dixon-Coles adjustment factor τ(x, y).

    Corrects the standard Poisson for low-scoring bias:
    - 0-0: (1 - λ_home × λ_away × ρ)
    - 0-1: (1 + λ_home × ρ)
    - 1-0: (1 + λ_away × ρ)
    - 1-1: (1 - ρ)
    - other: 1.0
    """
    if home_goals == 0 and away_goals == 0:
        return 1.0 - home_lambda * away_lambda * rho
    elif home_goals == 0 and away_goals == 1:
        return 1.0 + home_lambda * rho
    elif home_goals == 1 and away_goals == 0:
        return 1.0 + away_lambda * rho
    elif home_goals == 1 and away_goals == 1:
        return 1.0 - rho
    else:
        return 1.0


def dixon_coles_distribution(
    home_lambda: float,
    away_lambda: float,
    max_goals: int = 6,
    rho: float = -0.13,
) -> Dict:
    """
    Dixon-Coles corrected Poisson distribution.

    The Dixon-Coles model corrects the systematic underestimation
    of low-scoring results in the standard Poisson.

    Args:
        home_lambda: Expected goals for home team
        away_lambda: Expected goals for away team
        max_goals: Maximum goals to model per side
        rho: Dixon-Coles correction parameter (default -0.13,
             empirically optimal for major European leagues)

    Returns:
        Same structure as poisson_distribution, with DC-corrected probabilities
    """
    matrix: List[List[float]] = []
    home_win = 0.0
    draw = 0.0
    away_win = 0.0
    over_25 = 0.0
    btts = 0.0
    score_probs: List[Tuple[str, float]] = []

    for i in range(max_goals + 1):
        row = []
        for j in range(max_goals + 1):
            # Standard Poisson
            p_poisson = poisson_pmf(i, home_lambda) * poisson_pmf(j, away_lambda)
            # Dixon-Coles correction
            tau = _dixon_coles_tau(i, j, home_lambda, away_lambda, rho)
            p = p_poisson * tau
            row.append(p)

            score_label = f"{i}-{j}"
            score_probs.append((score_label, p * 100))

            if i > j:
                home_win += p
            elif i == j:
                draw += p
            else:
                away_win += p

            if i + j > 2.5:
                over_25 += p
            if i > 0 and j > 0:
                btts += p

        matrix.append(row)

    # Normalize
    total = home_win + draw + away_win
    if total > 0 and abs(total - 1.0) > 1e-10:
        home_win /= total
        draw /= total
        away_win /= total

    # Renormalize top scores
    score_probs.sort(key=lambda x: x[1], reverse=True)
    top_scores = [
        {"score": label, "probability_pct": round(prob, 2)}
        for label, prob in score_probs[:5]
    ]

    return {
        "score_matrix": [[round(p, 6) for p in row] for row in matrix],
        "home_win_pct": round(home_win * 100, 4),
        "draw_pct": round(draw * 100, 4),
        "away_win_pct": round(away_win * 100, 4),
        "top_scores": top_scores,
        "over_25_pct": round(over_25 * 100, 4),
        "btts_pct": round(btts * 100, 4),
        "lambda_home": home_lambda,
        "lambda_away": away_lambda,
        "rho": rho,
        "model": "dixon_coles",
    }

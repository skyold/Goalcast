"""
Goalcast Poisson Distribution Engine
====================================

Calculates score probability matrices using:
1. Standard Poisson (v2.5)
2. Dixon-Coles corrected Poisson (v3.0)

All computation is deterministic — no LLM "mental math".
"""

import math
from typing import Dict, List, Optional, Tuple


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


# ─── Asian Handicap 概率计算 ──────────────────────────────────────────────────

def calculate_ah_probability(
    score_matrix: List[List[float]],
    ah_line: float,
) -> Dict:
    """
    从 Dixon-Coles/Poisson 比分矩阵推导亚盘（Asian Handicap）覆盖概率。

    亚盘规则说明：
    ─────────────────────────────────────────────────────────
    ah_line 为主队让球线（负值=主队让球，正值=主队受让）。

    结算逻辑（以 ah_line=-0.5 为例，主队让半球）：
      净胜球 net = home_goals - away_goals
      net >  0.5  → 主队赢（主队覆盖）
      net <= 0.5  → 客队赢（客队覆盖）
      无平局（亚盘两路返还）

    四分之一盘（±0.25 / ±0.75）：
      将 ah_line 分解为两个相邻整/半球盘各投一半。
      例：ah_line=-0.25 = 平手盘(-0.0) + 让半球盘(-0.5) 各 50%
      例：ah_line=-0.75 = 让半球盘(-0.5) + 让一球盘(-1.0) 各 50%

    Args:
        score_matrix: poisson/dixon_coles 返回的 score_matrix，
                      matrix[i][j] = P(home=i, away=j)，未归一化原始概率。
        ah_line:      主队让球线，如 -0.5, -1.0, +0.5, -0.25, -0.75。

    Returns:
        {
          "ah_line": float,
          "p_home_cover": float,   # 主队覆盖概率（0~1）
          "p_away_cover": float,   # 客队覆盖概率（0~1）
          "p_push": float,         # 退水概率（整球盘时存在）
          "p_home_cover_pct": float,
          "p_away_cover_pct": float,
          "p_push_pct": float,
          "ah_type": str,          # "half" | "whole" | "quarter"
        }
    """
    # 检查是否为四分之一盘（0.25 或 0.75 小数部分）
    remainder = abs(ah_line) % 1
    is_quarter = abs(remainder - 0.25) < 1e-9 or abs(remainder - 0.75) < 1e-9

    if is_quarter:
        # 四分之一盘 = 两个相邻盘各 50%
        # 规则：round down & up（向更接近 0 和更远离 0 的方向）
        if ah_line < 0:
            line_low = math.floor(ah_line * 2) / 2   # 更接近 0（让球少）
            line_high = math.ceil(ah_line * 2) / 2   # 更远离 0（让球多）
        else:
            line_low = math.floor(ah_line * 2) / 2
            line_high = math.ceil(ah_line * 2) / 2

        res_low = _calc_single_ah(score_matrix, line_low)
        res_high = _calc_single_ah(score_matrix, line_high)

        p_home = 0.5 * res_low["p_home_cover"] + 0.5 * res_high["p_home_cover"]
        p_away = 0.5 * res_low["p_away_cover"] + 0.5 * res_high["p_away_cover"]
        p_push = 0.5 * res_low["p_push"] + 0.5 * res_high["p_push"]
        ah_type = "quarter"
    else:
        res = _calc_single_ah(score_matrix, ah_line)
        p_home = res["p_home_cover"]
        p_away = res["p_away_cover"]
        p_push = res["p_push"]
        remainder_half = abs(ah_line) % 1
        ah_type = "half" if abs(remainder_half - 0.5) < 1e-9 else "whole"

    return {
        "ah_line": ah_line,
        "p_home_cover": round(p_home, 6),
        "p_away_cover": round(p_away, 6),
        "p_push": round(p_push, 6),
        "p_home_cover_pct": round(p_home * 100, 4),
        "p_away_cover_pct": round(p_away * 100, 4),
        "p_push_pct": round(p_push * 100, 4),
        "ah_type": ah_type,
    }


def _calc_single_ah(
    score_matrix: List[List[float]],
    ah_line: float,
) -> Dict:
    """
    计算单一（非四分之一）亚盘线的覆盖概率。

    net_goal_margin = home_goals - away_goals + ah_line
    (ah_line 为负数时，主队需赢超过该让球数)

    结算：
      net > 0  → 主队覆盖
      net < 0  → 客队覆盖
      net == 0 → 退水（push），仅整球盘时发生
    """
    p_home = 0.0
    p_away = 0.0
    p_push = 0.0

    for i, row in enumerate(score_matrix):
        for j, prob in enumerate(row):
            if prob <= 0:
                continue
            # net > 0 意味着 home_goals - away_goals > -ah_line
            # 等价于 home_goals - away_goals + ah_line > 0
            net = (i - j) + ah_line
            if net > 1e-9:
                p_home += prob
            elif net < -1e-9:
                p_away += prob
            else:
                p_push += prob  # 整球盘退水

    total = p_home + p_away + p_push
    if total > 1e-9:
        p_home /= total
        p_away /= total
        p_push /= total

    return {"p_home_cover": p_home, "p_away_cover": p_away, "p_push": p_push}

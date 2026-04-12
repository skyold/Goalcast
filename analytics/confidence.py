"""
Goalcast Confidence Calculator
==============================

Deterministic confidence score calculation based on:
1. Data availability
2. Model-market agreement
3. Data quality
4. Known uncertainty factors

All adjustments are additive and bounded [30, 90].
"""

from typing import Dict, List, Optional


def calculate_confidence(
    base_score: int = 70,
    # Additions
    market_agrees: bool = False,
    data_complete: bool = False,
    understat_available: bool = False,
    odds_available: bool = False,
    # Deductions
    lineup_unavailable: bool = True,  # Expected to be missing by default
    xG_proxy_used: bool = False,
    market_disagrees: bool = False,
    data_quality_low: bool = False,
    understat_failed: bool = False,
    match_type_c: bool = False,
    major_uncertainty: bool = False,
    market_downgraded: bool = False,
) -> int:
    """
    Calculate confidence score for a match prediction.

    Args:
        base_score: Starting confidence (default 70)
        market_agrees: Market direction agrees with model (+8 for v2.5, +10 for v3.0)
        data_complete: Both teams have recent form data (+5)
        understat_available: Direct xG data from Understat available (+5)
        odds_available: Valid odds data available (+3)
        lineup_unavailable: Expected lineup data missing (-10)
        xG_proxy_used: Using proxy instead of direct xG (-5)
        market_disagrees: Market odds contradict model (-5)
        data_quality_low: Form data unavailable, using league average (-8)
        understat_failed: Understat match lookup failed (-5)
        match_type_c: Type C match (second leg of two-legged tie) (-10)
        major_uncertainty: Major pre-match uncertainty event (-5)
        market_downgraded: Market analysis layer downgraded (-5)

    Returns:
        Confidence score clamped to [30, 90]
    """
    score = base_score

    # Additions
    if market_agrees:
        score += 10  # v3.0 default; v2.5 passes different base
    if data_complete:
        score += 5
    if understat_available:
        score += 5
    if odds_available:
        score += 3

    # Deductions
    if lineup_unavailable:
        score -= 10  # Expected, always deducted unless lineup data exists
    if xG_proxy_used:
        score -= 5
    if market_disagrees:
        score -= 5
    if data_quality_low:
        score -= 8
    if understat_failed:
        score -= 5
    if match_type_c:
        score -= 10
    if major_uncertainty:
        score -= 5
    if market_downgraded:
        score -= 5

    # Clamp to [30, 90]
    return max(30, min(90, score))


def calculate_confidence_v25(
    base_score: int = 70,
    market_agrees: bool = False,
    data_complete: bool = False,
    understat_available: bool = False,
    odds_available: bool = False,
    lineup_unavailable: bool = True,
    xG_proxy_used: bool = False,
    market_disagrees: bool = False,
    data_quality_low: bool = False,
    understat_failed: bool = False,
) -> int:
    """
    v2.5 specific confidence calculation.

    Differences from v3.0:
    - market_agrees: +8 (not +10)
    - No market_downgraded deduction (v2.5 doesn't have this concept)
    """
    return calculate_confidence(
        base_score=base_score,
        market_agrees=market_agrees,
        # v2.5 uses +8 instead of +10, adjust after
        data_complete=data_complete,
        understat_available=understat_available,
        odds_available=odds_available,
        lineup_unavailable=lineup_unavailable,
        xG_proxy_used=xG_proxy_used,
        market_disagrees=market_disagrees,
        data_quality_low=data_quality_low,
        understat_failed=understat_failed,
    ) - (2 if market_agrees else 0)  # Adjust +10 → +8 for market_agrees


def confidence_breakdown(
    base_score: int = 70,
    **kwargs,
) -> Dict:
    """
    Return a detailed breakdown of confidence score components.

    Useful for the reasoning_summary field.
    """
    additions = []
    deductions = []

    if kwargs.get("market_agrees"):
        additions.append("市场方向与模型一致 (+10)")
    if kwargs.get("data_complete"):
        additions.append("近况数据完整 (+5)")
    if kwargs.get("understat_available"):
        additions.append("Understat xG 数据可用 (+5)")
    if kwargs.get("odds_available"):
        additions.append("赔率数据可用 (+3)")

    if kwargs.get("lineup_unavailable", True):
        deductions.append("阵容数据不可用 (-10)")
    if kwargs.get("xG_proxy_used"):
        deductions.append("xG 使用代理值 (-5)")
    if kwargs.get("market_disagrees"):
        deductions.append("赔率方向与模型相反 (-5)")
    if kwargs.get("data_quality_low"):
        deductions.append("近况数据不可用 (-8)")
    if kwargs.get("understat_failed"):
        deductions.append("Understat 匹配失败 (-5)")
    if kwargs.get("match_type_c"):
        deductions.append("C 类比赛 (-10)")
    if kwargs.get("major_uncertainty"):
        deductions.append("赛前重大不确定 (-5)")
    if kwargs.get("market_downgraded"):
        deductions.append("市场层权重降级 (-5)")

    final = calculate_confidence(base_score=base_score, **kwargs)

    return {
        "base": base_score,
        "additions": additions,
        "deductions": deductions,
        "final": final,
    }

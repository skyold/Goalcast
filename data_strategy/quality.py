"""
数据策略层 — 质量评估

为每类数据打质量分（0.0 – 1.0），驱动 Resolver 的 fallback 决策
以及 MatchContext.overall_quality 的综合计算。

评分逻辑：
- 基础分由数据来源决定（黄金 > 代理 > 估算）
- 字段完整性：缺少关键字段扣分
- 时效性：不影响评分（由 TTL 控制缓存失效）
"""

from typing import Any, Optional


# ── xG 质量评估 ──────────────────────────────────────────────

# Understat 覆盖联赛的 xG 是黄金标准
_XG_SOURCE_BASE: dict[str, float] = {
    "understat_direct": 0.95,
    "sportmonks_xg": 0.80,
    "footystats_proxy": 0.60,   # 近况进球均值代理
    "league_avg": 0.35,         # 联赛均值兜底
    "missing": 0.0,
}


def assess_xg_quality(raw: Optional[dict[str, Any]], source: str) -> float:
    """
    评估 xG 数据质量。

    Args:
        raw:    原始 provider 返回值（None 表示请求失败）
        source: 数据来源标识（见 _XG_SOURCE_BASE）

    Returns:
        质量分 0.0 – 1.0
    """
    if raw is None:
        return 0.0

    score = _XG_SOURCE_BASE.get(source, 0.40)

    if source == "understat_direct":
        # 必须包含实际射门数据，否则只是 stub
        if not raw.get("shots") and not raw.get("home_xg"):
            score -= 0.20
        elif raw.get("home_xg", 0) == 0 and raw.get("away_xg", 0) == 0:
            score -= 0.15  # 双方 xG 均为 0，数据存疑
    elif source == "footystats_proxy":
        # 代理值需要近况数据支撑
        if not raw.get("avg_scored_home") and not raw.get("form_5"):
            score -= 0.10

    return max(0.0, min(1.0, score))


# ── 近况质量评估 ─────────────────────────────────────────────


def assess_form_quality(
    raw_5: Optional[dict[str, Any]],
    raw_10: Optional[dict[str, Any]],
    source: str,
) -> float:
    """
    评估球队近况数据质量。

    Args:
        raw_5:  近 5 场数据
        raw_10: 近 10 场数据
        source: "footystats" | "missing"
    """
    if raw_5 is None and raw_10 is None:
        return 0.0

    if source == "footystats":
        score = 0.85
        # 仅有其中一个窗口
        if raw_5 is None or raw_10 is None:
            score -= 0.15
        # 关键字段校验
        sample = raw_5 or raw_10
        if sample and "avg_scored" not in sample and "seasonScoredAVG_overall" not in str(sample):
            score -= 0.10
    else:
        score = 0.40  # 未知来源

    return max(0.0, min(1.0, score))


# ── 积分榜质量评估 ────────────────────────────────────────────


def assess_standings_quality(
    home: Optional[dict[str, Any]],
    away: Optional[dict[str, Any]],
    source: str,
) -> float:
    """
    评估积分榜数据质量。

    Args:
        home:   主队积分榜条目原始数据
        away:   客队积分榜条目原始数据
        source: "footystats" | "sportmonks" | "missing"
    """
    if home is None or away is None:
        return 0.0 if (home is None and away is None) else 0.35

    score = 0.90 if source in ("footystats", "sportmonks") else 0.50

    # 关键字段完整性
    for entry in (home, away):
        if entry and "points" not in entry and "pts" not in str(entry):
            score -= 0.10
            break

    return max(0.0, min(1.0, score))


# ── 赔率质量评估 ─────────────────────────────────────────────


def assess_odds_quality(raw: Optional[dict[str, Any]], source: str) -> float:
    """
    评估赔率数据质量。

    赔率是 L3 层市场信号的核心。质量要求较高：
    三个方向必须齐全且值合理（> 1.0）。
    """
    if raw is None:
        return 0.0

    home_odds = float(raw.get("home_win", 0) or raw.get("odds_ft_1", 0) or 0)
    draw_odds = float(raw.get("draw", 0) or raw.get("odds_ft_x", 0) or 0)
    away_odds = float(raw.get("away_win", 0) or raw.get("odds_ft_2", 0) or 0)

    if home_odds <= 1.0 or draw_odds <= 1.0 or away_odds <= 1.0:
        return 0.0  # 非法赔率，不可用

    score = 0.90 if source == "footystats" else 0.85

    # 超售率合理性检查（正常应在 1.03 – 1.12 之间）
    overround = 1 / home_odds + 1 / draw_odds + 1 / away_odds
    if overround < 0.95 or overround > 1.20:
        score -= 0.15

    return max(0.0, min(1.0, score))


# ── 综合质量评估 ─────────────────────────────────────────────

# 各数据层权重（总和 = 1.0）
_QUALITY_WEIGHTS: dict[str, float] = {
    "xg": 0.35,
    "form": 0.30,
    "standings": 0.20,
    "odds": 0.15,
}


def compute_overall_quality(
    xg_quality: float,
    form_quality: float,
    standings_quality: float,
    odds_quality: float,
) -> float:
    """
    加权计算 MatchContext 的综合数据质量分。

    Returns:
        综合质量分 0.0 – 1.0
    """
    score = (
        xg_quality * _QUALITY_WEIGHTS["xg"]
        + form_quality * _QUALITY_WEIGHTS["form"]
        + standings_quality * _QUALITY_WEIGHTS["standings"]
        + odds_quality * _QUALITY_WEIGHTS["odds"]
    )
    return round(max(0.0, min(1.0, score)), 3)


def quality_to_label(quality: float) -> str:
    """将质量分转换为人类可读标签。"""
    if quality >= 0.75:
        return "high"
    if quality >= 0.50:
        return "medium"
    if quality >= 0.25:
        return "low"
    return "minimal"

"""Backtest aggregations — model accuracy on (FT × kickoff_snap) pairs.

Pure aggregation: read historical_predictions × fixtures (status='FT'), compute
top-1 hit rate, Brier score, and Wilson 95% CI for hit rate. No writes.

Cold-start contract: a `samples` count is always returned. `enough` is False
when samples < min_samples; callers (UI) gate display on that flag, not by
forcing the underlying metric to None.
"""
from __future__ import annotations

import math
from typing import Optional

import aiosqlite

MODEL_ID_DEFAULT = "oddalerts_default"


def _actual_outcome(score_home: int, score_away: int) -> str:
    if score_home > score_away:
        return "home"
    if score_home < score_away:
        return "away"
    return "draw"


def _brier(model_pct: tuple[float, float, float], actual: str) -> float:
    """Brier score for a single 1X2 prediction. model_pct is (home, draw, away)
    in 0..100 units; converted to probabilities here."""
    p_home, p_draw, p_away = (x / 100.0 for x in model_pct)
    one_hot = {"home": (1, 0, 0), "draw": (0, 1, 0), "away": (0, 0, 1)}[actual]
    return (p_home - one_hot[0]) ** 2 + (p_draw - one_hot[1]) ** 2 + (p_away - one_hot[2]) ** 2


def _wilson_ci(hits: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion. Stable in small N
    (unlike Wald). Returns (lower, upper) in [0, 1]."""
    if n == 0:
        return (0.0, 0.0)
    p = hits / n
    denom = 1.0 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, center - half), min(1.0, center + half))


async def fetch_pairs(
    db: aiosqlite.Connection,
    competition_id: Optional[int] = None,
    waypoint: str = "kickoff",
) -> list[dict]:
    """Return list of paired rows: model probs + actual outcome per fixture."""
    sql = """
        SELECT f.id AS fixture_id, f.competition_id, f.score_home, f.score_away,
               hp.home_win_pct, hp.draw_pct, hp.away_win_pct
        FROM fixtures f
        JOIN historical_predictions hp
          ON hp.fixture_id = f.id AND hp.waypoint = ?
        WHERE f.status = 'FT'
          AND f.score_home IS NOT NULL AND f.score_away IS NOT NULL
    """
    params: list = [waypoint]
    if competition_id is not None:
        sql += " AND f.competition_id = ?"
        params.append(competition_id)
    async with db.execute(sql, params) as cur:
        return [dict(r) for r in await cur.fetchall()]


def _aggregate(pairs: list[dict]) -> dict:
    """Compute hit_rate + Brier + CI from already-fetched pairs."""
    n = len(pairs)
    if n == 0:
        return {"samples": 0, "top1_hit_rate": None, "top1_hit_rate_ci95": None, "brier": None}
    hits = 0
    brier_sum = 0.0
    for r in pairs:
        probs = (r["home_win_pct"], r["draw_pct"], r["away_win_pct"])
        actual = _actual_outcome(r["score_home"], r["score_away"])
        top_idx = max(range(3), key=lambda i: probs[i])
        top_sel = ("home", "draw", "away")[top_idx]
        if top_sel == actual:
            hits += 1
        brier_sum += _brier(probs, actual)
    lo, hi = _wilson_ci(hits, n)
    return {
        "samples": n,
        "top1_hit_rate": round(hits / n, 4),
        "top1_hit_rate_ci95": [round(lo, 4), round(hi, 4)],
        "brier": round(brier_sum / n, 4),
    }


async def summary(
    db: aiosqlite.Connection,
    *,
    competition_id: Optional[int] = None,
    waypoint: str = "kickoff",
    min_samples: int = 500,
) -> dict:
    """Top-level summary endpoint payload (single scope)."""
    pairs = await fetch_pairs(db, competition_id=competition_id, waypoint=waypoint)
    metrics = _aggregate(pairs)
    return {
        "model_id": MODEL_ID_DEFAULT,
        "signal_version": None,  # reserved for future per-signal eval (proprietary-signals)
        "scope": {"competition_id": competition_id, "waypoint": waypoint},
        "samples": metrics["samples"],
        "enough": metrics["samples"] >= min_samples,
        "min_samples": min_samples,
        "metrics": metrics,
    }


async def calibration(
    db: aiosqlite.Connection,
    *,
    competition_id: Optional[int] = None,
    waypoint: str = "kickoff",
    bins: int = 10,
    min_per_bin: int = 30,
) -> dict:
    """Top-1 reliability buckets.

    For each (FT × kickoff_snap) pair, the model's top-1 probability becomes
    the bin key; the bin's actual_rate is the fraction of those pairs where
    top-1 was the actual outcome. Perfect calibration ⇒ predicted_avg ≈
    actual_rate per bin (the diagonal).

    Returns `bins` as a fixed 10-array (bin_index 0..9 = [0,10), [10,20), ...,
    [90,100]). Empty bins still appear (n=0) so the UI can render a stable
    x-axis without conditional rendering per bin.
    """
    pairs = await fetch_pairs(db, competition_id=competition_id, waypoint=waypoint)

    buckets: list[dict] = []
    for i in range(bins):
        lo = i / bins
        hi = (i + 1) / bins
        buckets.append({
            "bin_index": i,
            "lower": lo,
            "upper": hi,
            "n": 0,
            "_prob_sum": 0.0,
            "_hits": 0,
        })

    for r in pairs:
        probs = (r["home_win_pct"], r["draw_pct"], r["away_win_pct"])
        top_idx = max(range(3), key=lambda i: probs[i])
        top_prob = probs[top_idx] / 100.0
        # Clamp: a probability of 1.0 lands in the last bin.
        bin_idx = min(int(top_prob * bins), bins - 1)
        actual = _actual_outcome(r["score_home"], r["score_away"])
        top_sel = ("home", "draw", "away")[top_idx]

        b = buckets[bin_idx]
        b["n"] += 1
        b["_prob_sum"] += top_prob
        if top_sel == actual:
            b["_hits"] += 1

    items = []
    for b in buckets:
        n = b["n"]
        items.append({
            "bin_index": b["bin_index"],
            "lower": round(b["lower"], 2),
            "upper": round(b["upper"], 2),
            "n": n,
            "predicted_avg": round(b["_prob_sum"] / n, 4) if n else None,
            "actual_rate":   round(b["_hits"]    / n, 4) if n else None,
            "enough": n >= min_per_bin,
        })
    return {
        "model_id": MODEL_ID_DEFAULT,
        "scope": {"competition_id": competition_id, "waypoint": waypoint},
        "bins_count": bins,
        "min_per_bin": min_per_bin,
        "bins": items,
    }


async def by_league(
    db: aiosqlite.Connection,
    *,
    waypoint: str = "kickoff",
    min_samples: int = 100,
) -> dict:
    """One row per competition with FT+kickoff_snap pairs, ordered by samples desc."""
    pairs = await fetch_pairs(db, competition_id=None, waypoint=waypoint)
    by_comp: dict[int, list[dict]] = {}
    for p in pairs:
        by_comp.setdefault(p["competition_id"], []).append(p)

    # Resolve competition names in one query.
    comp_ids = list(by_comp.keys())
    names: dict[int, dict] = {}
    if comp_ids:
        placeholders = ",".join("?" * len(comp_ids))
        async with db.execute(
            f"SELECT id, name_en, name_zh FROM competitions WHERE id IN ({placeholders})",
            comp_ids,
        ) as cur:
            for r in await cur.fetchall():
                names[r["id"]] = {"name_en": r["name_en"], "name_zh": r["name_zh"]}

    items = []
    for comp_id, comp_pairs in by_comp.items():
        agg = _aggregate(comp_pairs)
        items.append({
            "competition_id": comp_id,
            "competition_name": names.get(comp_id, {}).get("name_en"),
            "competition_name_zh": names.get(comp_id, {}).get("name_zh"),
            "samples": agg["samples"],
            "enough": agg["samples"] >= min_samples,
            "top1_hit_rate": agg["top1_hit_rate"],
            "top1_hit_rate_ci95": agg["top1_hit_rate_ci95"],
            "brier": agg["brier"],
        })
    items.sort(key=lambda x: x["samples"], reverse=True)
    return {
        "model_id": MODEL_ID_DEFAULT,
        "scope": {"waypoint": waypoint},
        "min_samples": min_samples,
        "items": items,
    }

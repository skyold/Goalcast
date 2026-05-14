"""Single-source data collector — OddAlerts only.

2026-05-14 pivot: SportMonks/FootyStats/etc. all removed. The analysis layer
consumes a single OddAlerts-derived bundle. See plan Task 9.

The fixture-bundle assembly itself lives on the provider
(``OddAlertsProvider.collect_fixture_data``); this module is now a thin
wrapper that surfaces the plan-spec keys to ``collect_all``.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

_CST = timezone(timedelta(hours=8))


def _now_iso() -> str:
    return datetime.now(_CST).isoformat()


async def collect_oddalerts(oa_fixture_id: int) -> Optional[dict[str, Any]]:
    """Thin wrapper around :meth:`OddAlertsProvider.collect_fixture_data`.

    Returns a dict with keys (subset of):
        fixture, odds_history, h2h, stats_home, stats_away, trends
    """
    from provider.base import get_provider
    provider = get_provider()
    return await provider.collect_fixture_data(oa_fixture_id)


# Bundle keys that ``collect_all`` surfaces alongside ``source``/``collected_at``.
_BUNDLE_PASSTHROUGH_KEYS = (
    "fixture",
    "odds_history",
    "h2h",
    "stats_home",
    "stats_away",
    "trends",
)


def _compute_analysis(bundle: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Run poisson → EV → confidence on the OddAlerts bundle.

    Returns ``None`` if any stage produces no usable signal (e.g. missing
    team stats or odds). All wrappers handle their own degenerate inputs.
    """
    try:
        from analytics.poisson import poisson_from_oddalerts
        from analytics.ev_calculator import ev_from_oddalerts
        from analytics.confidence import confidence_from_oddalerts
    except Exception:  # pragma: no cover - import safety
        logger.exception("analytics import failed")
        return None

    stats_home = bundle.get("stats_home") or {}
    stats_away = bundle.get("stats_away") or {}
    odds_history = bundle.get("odds_history") or {}
    trends = bundle.get("trends") or {}

    poisson = poisson_from_oddalerts(stats_home, stats_away)
    if poisson is None:
        return None

    model_prob = {
        "H": poisson["home_win_pct"] / 100.0,
        "D": poisson["draw_pct"] / 100.0,
        "A": poisson["away_win_pct"] / 100.0,
    }

    ev_dict = ev_from_oddalerts(model_prob, odds_history)
    if ev_dict is None:
        return None

    conf = confidence_from_oddalerts(
        model_prob,
        trends,
        odds_history_present=bool(odds_history),
    )

    return {
        "model_prob": model_prob,
        "poisson": poisson,
        "ev": {k: ev_dict[k]["ev"] for k in ("H", "D", "A")},
        "kelly": {k: ev_dict[k]["kelly"] for k in ("H", "D", "A")},
        "ev_detail": ev_dict,
        "confidence_score": conf["score"],
        "confidence_stars": conf["stars"],
        "confidence_agreement": conf["agreement"],
    }


async def collect_all(oa_fixture_id: int) -> Optional[dict[str, Any]]:
    """Collect OddAlerts data for a single fixture.

    Returns ``None`` if the provider yields no usable fixture record.
    On success, returns a dict tagged with ``source="oddalerts"`` and a
    ``collected_at`` ISO timestamp, plus passthrough of any plan-spec
    bundle keys the provider produced, plus an ``analysis`` block from
    the deterministic poisson/EV/confidence pipeline (``None`` when the
    bundle is too sparse to analyze).
    """
    bundle = await collect_oddalerts(oa_fixture_id)
    if not bundle or "fixture" not in bundle:
        return None

    out: dict[str, Any] = {
        "source": "oddalerts",
        "collected_at": _now_iso(),
    }
    for key in _BUNDLE_PASSTHROUGH_KEYS:
        if key in bundle:
            out[key] = bundle[key]

    out["analysis"] = _compute_analysis(bundle)
    return out

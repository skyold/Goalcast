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


async def collect_all(oa_fixture_id: int) -> Optional[dict[str, Any]]:
    """Collect OddAlerts data for a single fixture.

    Returns ``None`` if the provider yields no usable fixture record.
    On success, returns a dict tagged with ``source="oddalerts"`` and a
    ``collected_at`` ISO timestamp, plus passthrough of any plan-spec
    bundle keys the provider produced.
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
    return out

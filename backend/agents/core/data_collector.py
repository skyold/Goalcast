"""Single-source data collector — OddAlerts only.

2026-05-14 pivot: SportMonks/FootyStats/etc. all removed. The analysis layer
consumes a single OddAlerts-derived bundle. See plan Task 9.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from provider.oddalerts.client import OddAlertsProvider

logger = logging.getLogger(__name__)

_CST = timezone(timedelta(hours=8))


def _now_iso() -> str:
    return datetime.now(_CST).isoformat()


def _extract_team_from_stats(stats_resp: object, team_id: object) -> dict | None:
    """从 stats API 响应中提取指定球队的统计行。"""
    if not isinstance(stats_resp, dict):
        return None
    rows = stats_resp.get("data") or []
    if not isinstance(rows, list):
        return None
    for row in rows:
        if isinstance(row, dict) and row.get("team_id") == team_id:
            return row
    return None


async def collect_oddalerts(oa_fixture_id: int) -> Optional[dict[str, Any]]:
    """从 OddAlerts 收集完整数据包：赔率 + 赛前统计 + 蒙特卡洛 + H2H + 近期状态。

    Returns a dict with keys (subset of):
        _meta, fixture, odds_history, stats, predictions, h2h, correct_scores,
        recent_stats — plus any additional keys the provider may surface.
    """
    provider = OddAlertsProvider()
    if not await provider.is_available():
        logger.debug("[DataCollector] OddAlerts API key 未配置，跳过")
        return None

    try:
        fixture, odds, stats, predictions, fixture_h2h = await asyncio.gather(
            provider.get_fixture(oa_fixture_id),
            provider.get_odds_history(oa_fixture_id),
            provider.get_stats("fixture", oa_fixture_id),
            provider.get_predictions_generate(oa_fixture_id),
            provider.get_fixture_h2h(oa_fixture_id),
            return_exceptions=True,
        )

        result: dict = {
            "_meta": {
                "collected_at": _now_iso(),
                "oa_fixture_id": oa_fixture_id,
            }
        }

        if isinstance(fixture, dict):
            result["fixture"] = fixture
        if isinstance(odds, dict):
            result["odds_history"] = odds
        if isinstance(stats, dict):
            result["stats"] = stats
        if isinstance(predictions, dict):
            result["predictions"] = predictions
        if isinstance(fixture_h2h, dict):
            h2h_list = fixture_h2h.get("h2h") or []
            result["h2h"] = h2h_list[:6]
            if fixture_h2h.get("correct_scores"):
                result["correct_scores"] = fixture_h2h["correct_scores"]

        if len(result) == 1:
            logger.warning("[DataCollector] OddAlerts fixture %d 未返回任何数据", oa_fixture_id)
            return None

        season_id = isinstance(fixture, dict) and fixture.get("season_id")
        home_id = isinstance(fixture, dict) and fixture.get("home_id")
        away_id = isinstance(fixture, dict) and fixture.get("away_id")

        if season_id and home_id and away_id:
            home5h_resp, away5a_resp, overall10_resp = await asyncio.gather(
                provider.get_stats_recent(season_id, "5_home"),
                provider.get_stats_recent(season_id, "5_away"),
                provider.get_stats_recent(season_id, "10_overall"),
                return_exceptions=True,
            )
            recent: dict = {}
            home5h = _extract_team_from_stats(home5h_resp, home_id)
            away5a = _extract_team_from_stats(away5a_resp, away_id)
            home10 = _extract_team_from_stats(overall10_resp, home_id)
            away10 = _extract_team_from_stats(overall10_resp, away_id)
            if home5h:
                recent["home_5h"] = home5h
            if away5a:
                recent["away_5a"] = away5a
            if home10:
                recent["home_10"] = home10
            if away10:
                recent["away_10"] = away10
            if recent:
                result["recent_stats"] = recent
        else:
            logger.debug(
                "[DataCollector] OddAlerts fixture %d 缺少 season/team_id，跳过近期状态",
                oa_fixture_id,
            )

        return result

    except Exception as exc:
        logger.warning("[DataCollector] OddAlerts 收集失败 oa_fixture_id=%d: %s", oa_fixture_id, exc)
        return None
    finally:
        await provider.close()


# Bundle keys that collect_all surfaces alongside `source`/`collected_at`.
_BUNDLE_PASSTHROUGH_KEYS = (
    "fixture",
    "odds_history",
    "stats",
    "stats_home",
    "stats_away",
    "predictions",
    "h2h",
    "correct_scores",
    "recent_stats",
    "trends",
)


async def collect_all(oa_fixture_id: int) -> Optional[dict[str, Any]]:
    """Collect OddAlerts data for a single fixture.

    Returns ``None`` if the provider yields no usable fixture record.
    On success, returns a dict tagged with ``source="oddalerts"`` and a
    ``collected_at`` ISO timestamp, plus passthrough of any standard bundle
    keys the provider produced.
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

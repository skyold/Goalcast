"""
多数据源收集器。

负责并行从各 provider 获取数据，结果存入 raw_data.{provider_name}。
每个 provider 完全独立，互不干扰。分析层自行决定使用哪个数据源。
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from provider.oddalerts.client import OddAlertsProvider

logger = logging.getLogger(__name__)

_CST = timezone(timedelta(hours=8))


def _now_iso() -> str:
    return datetime.now(_CST).isoformat()


async def collect_sportmonks(executor: Any, fixture_id: int) -> dict | None:
    """从 SportMonks executor 收集比赛数据。"""
    res = None
    get_match = getattr(executor, "_tool_goalcast_sportmonks_get_match", None)
    if callable(get_match):
        res = await get_match(fixture_id=fixture_id)
    if not isinstance(res, dict):
        resolve_match = getattr(executor, "_tool_goalcast_sportmonks_resolve_match", None)
        if callable(resolve_match):
            res = await resolve_match(fixture_id=fixture_id)
    if not isinstance(res, dict):
        return None
    data = res.get("data", {})
    return {
        "_meta": {"collected_at": _now_iso(), "fixture_id": fixture_id},
        **data,
    }


async def collect_oddalerts(oa_fixture_id: int) -> dict | None:
    """从 OddAlerts 收集赔率/统计/概率数据。

    oa_fixture_id: OddAlerts fixture ID（已由 discover_fixtures 阶段确定）。
    """
    provider = OddAlertsProvider()
    if not await provider.is_available():
        logger.debug("[DataCollector] OddAlerts API key 未配置，跳过")
        return None

    try:
        odds_task = provider.get_odds_history(oa_fixture_id)
        stats_task = provider.get_stats("fixture", oa_fixture_id)
        fixture_task = provider.get_fixture(oa_fixture_id)

        odds, stats, fixture = await asyncio.gather(
            odds_task, stats_task, fixture_task, return_exceptions=True
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

        if len(result) == 1:
            logger.warning("[DataCollector] OddAlerts fixture %d 未返回任何数据", oa_fixture_id)
            return None

        return result

    except Exception as exc:
        logger.warning("[DataCollector] OddAlerts 收集失败 oa_fixture_id=%d: %s", oa_fixture_id, exc)
        return None
    finally:
        await provider.close()


async def collect_all(
    executor: Any,
    provider_ids: dict[str, int],
    providers: list[str] | None = None,
) -> dict:
    """
    并行收集所有启用的 provider 数据。

    Args:
        executor:     SportMonks executor（现有机制）
        provider_ids: 各 provider 的 fixture ID 映射，如
                      {"sportmonks": 18329, "oddalerts": 54201}
                      某 provider 无对应比赛时该 key 不存在。
        providers:    指定要收集的 provider 列表，None = 全部

    Returns:
        raw_data dict，结构为 {provider_name: {_meta, ...数据}}
    """
    enabled = set(providers) if providers else {"sportmonks", "oddalerts"}

    tasks: dict[str, asyncio.Task] = {}

    sm_id = provider_ids.get("sportmonks")
    if "sportmonks" in enabled and sm_id is not None:
        tasks["sportmonks"] = asyncio.create_task(collect_sportmonks(executor, sm_id))

    oa_id = provider_ids.get("oddalerts")
    if "oddalerts" in enabled and oa_id is not None:
        tasks["oddalerts"] = asyncio.create_task(collect_oddalerts(oa_id))

    if not tasks:
        return {}

    results = await asyncio.gather(*tasks.values(), return_exceptions=True)

    raw_data: dict = {}
    for provider_name, result in zip(tasks.keys(), results):
        if isinstance(result, Exception):
            logger.warning("[DataCollector] %s 收集异常: %s", provider_name, result)
        elif isinstance(result, dict):
            raw_data[provider_name] = result
        else:
            logger.debug("[DataCollector] %s 无数据（provider_ids=%s）", provider_name, provider_ids)

    return raw_data

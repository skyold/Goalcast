"""
从所有激活的 provider 并行拉取 fixtures，合并去重。
"""
from __future__ import annotations

import asyncio
import logging

from provider import registry
from provider.models import UnifiedFixture
from agents.core.fixture_merger import merge_fixtures

logger = logging.getLogger(__name__)


async def discover_fixtures(
    dates: list[str],
    league_ids_by_provider: dict[str, list[int]] | None = None,
) -> list[UnifiedFixture]:
    """
    从所有激活 provider 并行发现 fixtures，合并去重。

    Args:
        dates: ISO 日期字符串列表，如 ["2025-05-10", "2025-05-11"]
        league_ids_by_provider: 各 provider 的联赛 ID 过滤，如
            {"sportmonks": [271], "oddalerts": [8]}。
            None 或 key 不存在时不过滤。

    Returns:
        合并去重后的 UnifiedFixture 列表。
    """
    providers = registry.get_active_providers()
    if not providers:
        logger.info("[Discovery] 无激活 provider，跳过")
        return []

    league_ids_by_provider = league_ids_by_provider or {}

    async def _discover_one(provider):
        league_ids = league_ids_by_provider.get(provider.name, [])
        try:
            fixtures = await provider.discover_fixtures(league_ids, dates)
            logger.info("[Discovery] %s 发现 %d 场", provider.name, len(fixtures))
            return provider.name, fixtures
        except Exception as exc:
            logger.warning("[Discovery] %s 失败: %s", provider.name, exc)
            return provider.name, []
        finally:
            try:
                await provider.close()
            except Exception:
                pass

    results = await asyncio.gather(*[_discover_one(p) for p in providers])
    unified = merge_fixtures([(name, fixtures) for name, fixtures in results if fixtures])
    logger.info("[Discovery] 合并后共 %d 场", len(unified))
    return unified

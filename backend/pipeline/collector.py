"""
从所有激活 provider 并行收集单场比赛数据。
"""
from __future__ import annotations

import asyncio
import logging

from provider import registry

logger = logging.getLogger(__name__)


async def collect_match_data(provider_ids: dict[str, int]) -> dict:
    """
    并行从所有激活 provider 收集单场比赛数据。

    Args:
        provider_ids: 各 provider 的 fixture ID 映射，
                      如 {"sportmonks": 18329, "oddalerts": 54201}。
                      provider 在此 dict 中无对应 key 时跳过。

    Returns:
        raw_data dict，结构为 {provider_name: {_meta, ...数据}}
    """
    providers = registry.get_active_providers()

    async def _collect_one(provider):
        pid = provider_ids.get(provider.name)
        if pid is None:
            return provider.name, None
        try:
            data = await provider.collect_match(pid)
            return provider.name, data
        except Exception as exc:
            logger.warning("[Collector] %s 收集失败 fixture_id=%s: %s", provider.name, pid, exc)
            return provider.name, None
        finally:
            try:
                await provider.close()
            except Exception:
                pass

    results = await asyncio.gather(*[_collect_one(p) for p in providers])
    return {name: data for name, data in results if data is not None}

"""
Pipeline Runner — 核心编排器。
顺序执行：发现 fixtures → 收集数据 → 分析（可选）。
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from pipeline.discovery import discover_fixtures
from pipeline.collector import collect_match_data
from pipeline.league_resolver import resolve_league_ids
from provider import registry
from store import match_store
from agents.analyst import run_analyst

logger = logging.getLogger(__name__)

_CST = timezone(timedelta(hours=8))


def _default_dates() -> list[str]:
    now = datetime.now(_CST)
    return [(now + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(5)]


async def run_pipeline(
    leagues: list[str] | None = None,
    dates: list[str] | None = None,
    adapter: Any = None,
    model: str = "v4.0",
    force: bool = False,
) -> dict:
    """
    执行一次完整的 pipeline。

    Args:
        leagues:  联赛名称列表（支持中英文），None 则不过滤
        dates:    日期列表 YYYY-MM-DD，None 则取今日起 5 天
        adapter:  ClaudeAdapter 实例（analyst 启用时必须提供）
        model:    分析模型版本
        force:    True 时重新处理已有比赛

    Returns:
        {"discovered": int, "collected": int, "analyzed": int, "errors": int}
    """
    dates = dates or _default_dates()
    league_ids_by_provider: dict[str, list[int]] = {}

    if leagues:
        resolved = resolve_league_ids(leagues)
        league_ids_by_provider = resolved
        logger.info("[Runner] 联赛解析: %s → %s", leagues, resolved)

    logger.info("[Runner] 开始 pipeline, dates=%s", dates)

    # ── 1. 发现 fixtures ──────────────────────────────────────────────
    unified_fixtures = await discover_fixtures(dates, league_ids_by_provider)
    discovered = len(unified_fixtures)
    logger.info("[Runner] 发现 %d 场", discovered)

    collected = 0
    analyzed = 0
    errors = 0
    analyst_enabled = registry.is_analyst_enabled()

    for uf in unified_fixtures:
        # ── 2. 跳过已存在的 match（除非 force）──────────────────────
        existing_id = None
        for provider_name, fid in uf.provider_ids.items():
            existing_id = match_store.exists_for_fixture(provider_name, fid)
            if existing_id:
                break

        if existing_id and not force:
            existing = match_store.get(existing_id)
            if existing and existing.get("status") in ("collected", "analyzed"):
                logger.debug("[Runner] 跳过已存在比赛: %s", existing_id)
                continue

        match_id = existing_id or match_store.generate_match_id()

        kickoff_str = (
            datetime.fromtimestamp(uf.kickoff_unix, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            if uf.kickoff_unix else ""
        )
        league_name = getattr(uf, "league_name", "") or ""

        metadata = {
            "match_id": match_id,
            "home_team": uf.home_team,
            "away_team": uf.away_team,
            "league": league_name,
            "kickoff_time": kickoff_str,
            "provider_ids": uf.provider_ids,
            "collected_at": None,
        }

        # ── 3. 收集数据 ───────────────────────────────────────────────
        try:
            raw_data = await collect_match_data(uf.provider_ids)
        except Exception as exc:
            logger.error("[Runner] 收集失败 %s vs %s: %s", uf.home_team, uf.away_team, exc)
            errors += 1
            continue

        metadata["collected_at"] = datetime.now(_CST).isoformat()

        record = {
            "match_id": match_id,
            "status": "collected",
            "metadata": metadata,
            "raw_data": raw_data,
            "analysis": {},
        }
        match_store.save(record)
        collected += 1
        logger.info("[Runner] 收集完成: %s vs %s (%s)", uf.home_team, uf.away_team, match_id)

        # ── 4. 分析（可选）───────────────────────────────────────────
        if not analyst_enabled or adapter is None:
            continue

        try:
            analysis = await run_analyst(adapter, metadata, raw_data, model)
            if "error" in analysis:
                match_store.update(match_id, {"status": "error", "analysis": analysis})
                errors += 1
            else:
                match_store.update(match_id, {"status": "analyzed", "analysis": analysis})
                analyzed += 1
        except Exception as exc:
            logger.error("[Runner] 分析失败 %s: %s", match_id, exc)
            match_store.update(match_id, {"status": "error"})
            errors += 1

    logger.info("[Runner] 完成: discovered=%d collected=%d analyzed=%d errors=%d",
                discovered, collected, analyzed, errors)
    return {
        "discovered": discovered,
        "collected": collected,
        "analyzed": analyzed,
        "errors": errors,
    }

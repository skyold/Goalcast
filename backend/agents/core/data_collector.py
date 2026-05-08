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


async def collect_oddalerts(oa_fixture_id: int) -> dict | None:
    """从 OddAlerts 收集完整数据包：赔率 + 赛前统计 + 蒙特卡洛 + H2H + 近期状态。

    oa_fixture_id: OddAlerts fixture ID（已由 discover_fixtures 阶段确定）。

    存储结构:
        _meta            收集元信息
        fixture          比赛基础信息（含 probability 模型概率）
        odds_history     全市场赔率历史（ft_result / asian_handicap / goal_line 等）
        stats            赛前冻结整体统计（xG / 进失球 / BTTS 等）
        predictions      蒙特卡洛模拟（50k 次），含 xG / 胜率 / 大小球 / 比分分布
        h2h              近期 H2H 对阵记录（最多 6 场）
        correct_scores   正确比分概率分布（来自 H2H 接口附带数据）
        recent_stats     近期状态（主队近5场主场 / 客队近5场客场 / 双方近10场总体）
    """
    provider = OddAlertsProvider()
    if not await provider.is_available():
        logger.debug("[DataCollector] OddAlerts API key 未配置，跳过")
        return None

    try:
        # ── 批次 1：可完全并行的 5 个请求 ─────────────────────────────────────
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

        # ── 批次 2：近期状态（需要 fixture 提供 season_id / team_id）──────────
        season_id = isinstance(fixture, dict) and fixture.get("season_id")
        home_id   = isinstance(fixture, dict) and fixture.get("home_id")
        away_id   = isinstance(fixture, dict) and fixture.get("away_id")

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
            if home5h: recent["home_5h"] = home5h
            if away5a: recent["away_5a"] = away5a
            if home10: recent["home_10"] = home10
            if away10: recent["away_10"] = away10
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

"""
数据策略层 — DataResolver（数据解析器）

职责：
1. 按优先级链（primary → fallback → league_avg）尝试获取数据
2. 接入 utils/cache.py 做 TTL 缓存，避免重复 API 调用
3. 失败时标记缺失项（MARK_MISSING），不抛出异常

覆盖范围说明：
- xG 数据：Understat 仅覆盖 6 大联赛（见 UNDERSTAT_LEAGUE_MAP）
           非覆盖联赛自动降级到 FootyStats proxy
- 伤停/阵容：当前版本 MARK_MISSING，不依赖不稳定的 Web Search

Provider 注入：resolver 不自行创建 provider 实例，
由上层（DataFusion / server.py）传入，便于测试 mock。
"""

import asyncio
import time
from typing import Any, Optional, TYPE_CHECKING

from utils.cache import cache_get, cache_set
from utils.logger import logger
from data_strategy.models import get_understat_league_code
from data_strategy.quality import (
    assess_xg_quality,
    assess_form_quality,
    assess_standings_quality,
    assess_odds_quality,
)

if TYPE_CHECKING:
    from provider.footystats.client import FootyStatsProvider
    from provider.sportmonks.client import SportmonksProvider
    from provider.understat.client import UnderstatProvider


# ── 缓存 TTL 配置（单位：小时）───────────────────────────────

CACHE_TTL: dict[str, float] = {
    "xg": 24.0,           # xG 数据赛前稳定
    "form": 12.0,         # 近况数据随比赛更新
    "standings": 6.0,     # 积分榜随比赛日更新
    "odds": 0.5,          # 赔率变动快
    "match_meta": 2.0,    # 比赛基础信息
    "lineups": 2.0,       # 阵容数据赛前更新
    "h2h": 24.0,          # 历史交锋数据稳定
}

# 最低可接受质量阈值（低于此值触发 fallback）
MIN_QUALITY: dict[str, float] = {
    "xg": 0.50,
    "form": 0.60,
    "standings": 0.60,
    "odds": 0.70,
}


# ── 解析结果封装 ──────────────────────────────────────────────


class ResolvedData:
    """单次解析的结果，包含原始数据、来源与质量评分。"""

    __slots__ = ("data", "source", "quality", "fallback_used", "error")

    def __init__(
        self,
        data: Optional[dict[str, Any]],
        source: str,
        quality: float,
        *,
        fallback_used: bool = False,
        error: Optional[str] = None,
    ) -> None:
        self.data = data
        self.source = source
        self.quality = quality
        self.fallback_used = fallback_used
        self.error = error

    @property
    def ok(self) -> bool:
        return self.data is not None and self.quality > 0.0

    @classmethod
    def missing(cls, data_type: str) -> "ResolvedData":
        return cls(
            data=None,
            source="missing",
            quality=0.0,
            error=f"{data_type} not available from any provider",
        )


# ── DataResolver ─────────────────────────────────────────────


class DataResolver:
    """
    按优先级链解析各类数据，内置 TTL 缓存与 fallback 逻辑。

    使用示例（由 DataFusion 调用）：
        resolver = DataResolver(footystats=fs, understat=us, sportmonks=sm)
        xg = await resolver.resolve_xg(
            home_team="Arsenal", away_team="Chelsea",
            league="Premier League", season="2025"
        )
    """

    def __init__(
        self,
        footystats: "FootyStatsProvider",
        understat: "UnderstatProvider",
        sportmonks: Optional["SportmonksProvider"] = None,
    ) -> None:
        self._fs = footystats
        self._us = understat
        self._sm = sportmonks

    # ── xG 解析 ──────────────────────────────────────────────

    async def resolve_xg(
        self,
        home_team: str,
        away_team: str,
        league: str,
        season: str,
        home_team_id: str,
        away_team_id: str,
    ) -> ResolvedData:
        """
        解析双方 xG 攻防代理值。

        优先级链：
          1. Understat 联赛球队 xG 统计（仅覆盖 6 大联赛）
          2. FootyStats get_team_last_x_stats（进球均值代理）
          3. league_avg 兜底（由 fusion 层填充联赛参数均值）
        """
        cache_key = f"xg_{home_team}_{away_team}_{league}_{season}"
        cached = cache_get("data_strategy_xg", cache_key)
        if cached:
            logger.debug(f"[Resolver] xG cache hit: {cache_key}")
            return ResolvedData(
                data=cached["data"],
                source=cached["source"],
                quality=cached["quality"],
            )

        understat_code = get_understat_league_code(league)

        # Primary：Understat 联赛球队统计
        if understat_code:
            result = await self._resolve_xg_understat(
                home_team, away_team, understat_code, season
            )
            if result.ok and result.quality >= MIN_QUALITY["xg"]:
                cache_set(
                    "data_strategy_xg",
                    cache_key,
                    {"data": result.data, "source": result.source, "quality": result.quality},
                    ttl_hours=CACHE_TTL["xg"],
                )
                return result
            logger.info(
                f"[Resolver] Understat xG fallback (quality={result.quality:.2f}): {result.error}"
            )

        # Fallback：FootyStats 近况进球均值代理
        result = await self._resolve_xg_footystats_proxy(home_team_id, away_team_id)
        if result.ok:
            cache_set(
                "data_strategy_xg",
                cache_key,
                {"data": result.data, "source": result.source, "quality": result.quality},
                ttl_hours=CACHE_TTL["xg"],
            )
            return result

        # 最终兜底：league_avg（由 fusion 层根据 LEAGUE_PARAMS 填充）
        logger.warning(f"[Resolver] xG all sources failed, falling back to league_avg")
        return ResolvedData(
            data={"fallback": "league_avg"},
            source="league_avg",
            quality=0.35,
        )

    async def _resolve_xg_understat(
        self, home_team: str, away_team: str, league_code: str, season: str
    ) -> ResolvedData:
        """从 Understat 联赛球队统计中提取 xG 攻防均值。"""
        try:
            teams_data = await self._us.get_league_teams(league_code, season)
            if not teams_data:
                return ResolvedData.missing("understat_teams")

            home_stats = _find_team(teams_data, home_team)
            away_stats = _find_team(teams_data, away_team)

            if not home_stats or not away_stats:
                return ResolvedData(
                    data=None,
                    source="understat_direct",
                    quality=0.0,
                    error=f"Team not found in Understat: home={not bool(home_stats)}, away={not bool(away_stats)}",
                )

            data = {
                "home_xg_for": _safe_float(home_stats, "xG"),
                "home_xg_against": _safe_float(home_stats, "xGA"),
                "away_xg_for": _safe_float(away_stats, "xG"),
                "away_xg_against": _safe_float(away_stats, "xGA"),
                "home_team_understat": home_stats.get("title", ""),
                "away_team_understat": away_stats.get("title", ""),
            }
            quality = assess_xg_quality(data, "understat_direct")
            return ResolvedData(data=data, source="understat_direct", quality=quality)

        except Exception as exc:
            logger.error(f"[Resolver] Understat xG error: {exc}")
            return ResolvedData(
                data=None, source="understat_direct", quality=0.0, error=str(exc)
            )

    async def _resolve_xg_footystats_proxy(
        self, home_team_id: str, away_team_id: str
    ) -> ResolvedData:
        """从 FootyStats 近况统计提取进球均值作为 xG 代理。"""
        try:
            home_raw, away_raw = await asyncio.gather(
                self._fs.get_team_last_x_stats(int(home_team_id)),
                self._fs.get_team_last_x_stats(int(away_team_id)),
                return_exceptions=True,
            )

            if isinstance(home_raw, Exception) or isinstance(away_raw, Exception):
                return ResolvedData.missing("footystats_proxy")

            home_form = _extract_footystats_form(home_raw)
            away_form = _extract_footystats_form(away_raw)

            if not home_form or not away_form:
                return ResolvedData.missing("footystats_proxy")

            # xG proxy：近 10 场场均进球（如无则用近 5 场）
            home_avg = home_form.get("avg_scored_10") or home_form.get("avg_scored_5", 0.0)
            away_avg = away_form.get("avg_scored_10") or away_form.get("avg_scored_5", 0.0)
            home_def = home_form.get("avg_conceded_10") or home_form.get("avg_conceded_5", 0.0)
            away_def = away_form.get("avg_conceded_10") or away_form.get("avg_conceded_5", 0.0)

            data = {
                "home_xg_for": home_avg,
                "home_xg_against": home_def,
                "away_xg_for": away_avg,
                "away_xg_against": away_def,
                "home_form_raw": home_form,
                "away_form_raw": away_form,
            }
            quality = assess_xg_quality(data, "footystats_proxy")
            return ResolvedData(
                data=data, source="footystats_proxy", quality=quality, fallback_used=True
            )

        except Exception as exc:
            logger.error(f"[Resolver] FootyStats xG proxy error: {exc}")
            return ResolvedData.missing("footystats_proxy")

    # ── 近况解析 ─────────────────────────────────────────────

    async def resolve_form(
        self, home_team_id: str, away_team_id: str
    ) -> ResolvedData:
        """
        解析双方近 5/10 场近况统计。
        Primary：FootyStats get_team_last_x_stats
        """
        cache_key = f"form_{home_team_id}_{away_team_id}"
        cached = cache_get("data_strategy_form", cache_key)
        if cached:
            return ResolvedData(
                data=cached["data"], source=cached["source"], quality=cached["quality"]
            )

        try:
            home_raw, away_raw = await asyncio.gather(
                self._fs.get_team_last_x_stats(int(home_team_id)),
                self._fs.get_team_last_x_stats(int(away_team_id)),
                return_exceptions=True,
            )

            if isinstance(home_raw, Exception) or isinstance(away_raw, Exception):
                return ResolvedData.missing("form")

            home_form = _extract_footystats_form(home_raw)
            away_form = _extract_footystats_form(away_raw)

            data = {
                "home": home_form,
                "away": away_form,
                "raw_home": home_raw,
                "raw_away": away_raw,
            }
            quality = assess_form_quality(
                home_form.get("window_5") if home_form else None,
                home_form.get("window_10") if home_form else None,
                source="footystats",
            )
            result = ResolvedData(data=data, source="footystats", quality=quality)
            cache_set(
                "data_strategy_form",
                cache_key,
                {"data": data, "source": "footystats", "quality": quality},
                ttl_hours=CACHE_TTL["form"],
            )
            return result

        except Exception as exc:
            logger.error(f"[Resolver] Form resolve error: {exc}")
            return ResolvedData.missing("form")

    # ── 积分榜解析 ────────────────────────────────────────────

    async def resolve_standings(self, season_id: str) -> ResolvedData:
        """
        解析联赛积分榜。
        Primary：FootyStats get_league_tables
        Fallback：Sportmonks get_standings（如已配置）
        """
        cache_key = f"standings_{season_id}"
        cached = cache_get("data_strategy_standings", cache_key)
        if cached:
            return ResolvedData(
                data=cached["data"], source=cached["source"], quality=cached["quality"]
            )

        # Primary：FootyStats
        try:
            raw = await self._fs.get_league_tables(int(season_id))
            if raw and not _is_error_response(raw):
                quality = assess_standings_quality(raw, raw, source="footystats")
                result = ResolvedData(data={"raw": raw}, source="footystats", quality=quality)
                cache_set(
                    "data_strategy_standings",
                    cache_key,
                    {"data": result.data, "source": result.source, "quality": result.quality},
                    ttl_hours=CACHE_TTL["standings"],
                )
                return result
        except Exception as exc:
            logger.warning(f"[Resolver] FootyStats standings error: {exc}")

        # Fallback：Sportmonks（可选）
        if self._sm:
            try:
                raw = await self._sm.get_standings(int(season_id))
                if raw and not _is_error_response(raw):
                    quality = assess_standings_quality(raw, raw, source="sportmonks")
                    result = ResolvedData(
                        data={"raw": raw}, source="sportmonks", quality=quality, fallback_used=True
                    )
                    cache_set(
                        "data_strategy_standings",
                        cache_key,
                        {"data": result.data, "source": result.source, "quality": result.quality},
                        ttl_hours=CACHE_TTL["standings"],
                    )
                    return result
            except Exception as exc:
                logger.warning(f"[Resolver] Sportmonks standings fallback error: {exc}")

        logger.warning(f"[Resolver] Standings unavailable for season_id={season_id}")
        return ResolvedData.missing("standings")

    # ── 赔率解析 ─────────────────────────────────────────────

    async def resolve_odds(self, match_id: str) -> ResolvedData:
        """
        解析开盘赔率。
        Primary：FootyStats get_match_details（odds_ft_1/x/2 字段）
        Fallback：Sportmonks get_prematch_odds（如已配置）
        """
        cache_key = f"odds_{match_id}"
        cached = cache_get("data_strategy_odds", cache_key)
        if cached:
            return ResolvedData(
                data=cached["data"], source=cached["source"], quality=cached["quality"]
            )

        # Primary：从 FootyStats match_details 提取
        try:
            raw = await self._fs.get_match_details(int(match_id))
            if raw and not _is_error_response(raw):
                odds_data = _extract_footystats_odds(raw)
                if odds_data:
                    quality = assess_odds_quality(odds_data, source="footystats")
                    if quality > 0.0:
                        result = ResolvedData(
                            data=odds_data, source="footystats", quality=quality
                        )
                        cache_set(
                            "data_strategy_odds",
                            cache_key,
                            {"data": odds_data, "source": "footystats", "quality": quality},
                            ttl_hours=CACHE_TTL["odds"],
                        )
                        return result
        except Exception as exc:
            logger.warning(f"[Resolver] FootyStats odds error: {exc}")

        # Fallback：Sportmonks prematch odds
        if self._sm:
            try:
                raw = await self._sm.get_prematch_odds(int(match_id))
                if raw and not _is_error_response(raw):
                    odds_data = _extract_sportmonks_odds(raw)
                    if odds_data:
                        quality = assess_odds_quality(odds_data, source="sportmonks")
                        if quality > 0.0:
                            result = ResolvedData(
                                data=odds_data,
                                source="sportmonks",
                                quality=quality,
                                fallback_used=True,
                            )
                            cache_set(
                                "data_strategy_odds",
                                cache_key,
                                {"data": odds_data, "source": "sportmonks", "quality": quality},
                                ttl_hours=CACHE_TTL["odds"],
                            )
                            return result
            except Exception as exc:
                logger.warning(f"[Resolver] Sportmonks odds fallback error: {exc}")

        logger.info(f"[Resolver] Odds unavailable for match_id={match_id}")
        return ResolvedData.missing("odds")

    # ── 预测解析 ─────────────────────────────────────────────

    async def resolve_predictions(self, fixture_id: str) -> ResolvedData:
        """
        解析胜平负预测概率。
        仅 Sportmonks 提供，FootyStats 返回 missing。
        """
        if self._sm:
            cache_key = f"predictions_{fixture_id}"
            cached = cache_get("data_strategy_predictions", cache_key)
            if cached:
                return ResolvedData(
                    data=cached["data"], source=cached["source"], quality=cached["quality"]
                )

            try:
                raw = await self._sm.get_predictions_by_fixture(int(fixture_id))
                if raw and not _is_error_response(raw):
                    from data_strategy.resolvers.sportmonks_resolver import _extract_predictions
                    pred_data = _extract_predictions(raw)
                    if pred_data:
                        result = ResolvedData(
                            data=pred_data, source="sportmonks", quality=0.90
                        )
                        cache_set(
                            "data_strategy_predictions",
                            cache_key,
                            {"data": pred_data, "source": "sportmonks", "quality": 0.90},
                            ttl_hours=12.0,
                        )
                        return result
            except Exception as exc:
                logger.warning(f"[Resolver] Sportmonks predictions error: {exc}")

        return ResolvedData.missing("predictions")


# ── 私有辅助函数 ──────────────────────────────────────────────


def _find_team(
    teams_data: list[dict[str, Any]], team_name: str
) -> Optional[dict[str, Any]]:
    """在 Understat 球队列表中模糊匹配球队名。"""
    if not teams_data or not team_name:
        return None

    name_lower = team_name.lower().strip()

    # 精确匹配
    for team in teams_data:
        title = (team.get("title") or team.get("name") or "").lower()
        if title == name_lower:
            return team

    # 包含匹配（处理名称差异，如 "Man United" vs "Manchester United"）
    keywords = [w for w in name_lower.split() if len(w) > 3]
    for team in teams_data:
        title = (team.get("title") or team.get("name") or "").lower()
        if any(kw in title for kw in keywords):
            return team

    return None


def _safe_float(obj: dict[str, Any], key: str, default: float = 0.0) -> float:
    """安全提取 float 值，失败时返回默认值。"""
    try:
        val = obj.get(key, default)
        return float(val) if val is not None else default
    except (TypeError, ValueError):
        return default


def _extract_footystats_form(
    raw: Any,
) -> Optional[dict[str, Any]]:
    """
    从 FootyStats get_team_last_x_stats 响应中提取近况统计。

    FootyStats 返回的 data 数组包含多个窗口（last_x_match_num = 5, 6, 10）：
    {
      "data": [
        {"last_x_match_num": 5, "stats": {"seasonScoredAVG_overall": 1.4, ...}},
        {"last_x_match_num": 10, "stats": {"seasonScoredAVG_overall": 1.6, ...}},
      ]
    }
    """
    if not raw or _is_error_response(raw):
        return None

    # 支持两种响应格式
    data_list = raw if isinstance(raw, list) else (raw.get("data") or [])
    if not data_list:
        return None

    windows: dict[int, dict[str, Any]] = {}
    for entry in data_list:
        if not isinstance(entry, dict):
            continue
        num = entry.get("last_x_match_num") or entry.get("num")
        stats = entry.get("stats") or entry
        if num and stats:
            windows[int(num)] = stats

    result: dict[str, Any] = {}

    for window in (5, 10):
        s = windows.get(window)
        if not s:
            continue
        result[f"avg_scored_{window}"] = _safe_float(s, "seasonScoredAVG_overall")
        result[f"avg_conceded_{window}"] = _safe_float(s, "seasonConcededAVG_overall")
        result[f"wins_{window}"] = int(s.get("seasonWinsNum_overall", 0) or 0)
        result[f"draws_{window}"] = int(s.get("seasonDrawsNum_overall", 0) or 0)
        result[f"losses_{window}"] = int(s.get("seasonLossesNum_overall", 0) or 0)
        result[f"goals_scored_{window}"] = _safe_float(s, "seasonScoredNum_overall")
        result[f"goals_conceded_{window}"] = _safe_float(s, "seasonConcededNum_overall")
        result[f"window_{window}"] = s  # 保留原始 stats 供 fusion 层深度访问

    return result if result else None


def _extract_footystats_odds(raw: Any) -> Optional[dict[str, Any]]:
    """
    从 FootyStats match_details 响应中提取赔率字段。
    支持顶层字段或 data[0] 包装格式。
    """
    obj: dict[str, Any] = {}

    if isinstance(raw, dict):
        obj = raw.get("data") or raw
        if isinstance(obj, list):
            obj = obj[0] if obj else {}
    elif isinstance(raw, list):
        obj = raw[0] if raw else {}

    home = _safe_float(obj, "odds_ft_1")
    draw = _safe_float(obj, "odds_ft_x")
    away = _safe_float(obj, "odds_ft_2")

    if home <= 0 or draw <= 0 or away <= 0:
        return None

    return {"home_win": home, "draw": draw, "away_win": away}


def _extract_sportmonks_odds(raw: Any) -> Optional[dict[str, Any]]:
    """
    从 Sportmonks prematch_odds 响应中提取 1X2 赔率。
    Sportmonks v3 返回 data 数组，包含多个博彩公司的赔率。
    取第一个（通常为 Pinnacle 或平均值）。
    """
    data = raw if isinstance(raw, list) else (raw.get("data") or [] if isinstance(raw, dict) else [])

    for item in data:
        if not isinstance(item, dict):
            continue
        odds = item.get("odds") or item
        home = _safe_float(odds, "home") or _safe_float(odds, "dp3")
        draw = _safe_float(odds, "draw") or _safe_float(odds, "dp1")
        away = _safe_float(odds, "away") or _safe_float(odds, "dp2")
        if home > 1.0 and draw > 1.0 and away > 1.0:
            return {"home_win": home, "draw": draw, "away_win": away}

    return None


def _is_error_response(raw: Any) -> bool:
    """检测 provider 返回的是否为错误响应。"""
    if not isinstance(raw, dict):
        return False
    error = raw.get("error") or raw.get("status")
    if error in ("API_KEY_INVALID", "PROVIDER_ERROR", "error"):
        return True
    return False

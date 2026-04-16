"""
数据策略层 — DataFusion（数据融合引擎）

职责：
1. 使用 FootyStatsResolver 聚合多方数据
2. 并行调用 resolver 获取所有数据类
3. 将 provider 原始响应映射到 MatchContext 类型化结构
4. 计算综合数据质量评分
5. 返回 MatchContext（Skill 唯一依赖的数据对象）

设计原则：
- 并行 I/O（asyncio.gather），不串行等待
- 失败不抛出：缺失项记录到 data_gaps，分析层自行降级
- 联赛均值兜底由此层注入（来自 config.settings.LEAGUE_PARAMS）
"""

import asyncio
import datetime
import time
from typing import Any, Optional, TYPE_CHECKING

from utils.logger import logger
from config.settings import settings
from datasource.datafusion.models import (
    MatchContext,
    TeamFormWindow,
    StandingsEntry,
    OddsSnapshot,
    XGStats,
)
from datasource.datafusion.quality import compute_overall_quality
from datasource.datafusion.resolver import ResolvedData
from datasource.datafusion.resolvers.footystats_resolver import FootyStatsResolver

if TYPE_CHECKING:
    from provider.footystats.client import FootyStatsProvider
    from provider.understat.client import UnderstatProvider


_DEFAULT_ODDS_MOVEMENT_HOURS = 48  # default movement window when not provided by resolver


class DataFusion:
    """
    将多个 provider 的数据融合为单个 MatchContext。

    使用示例（由 goalcast_footystats_resolve_match MCP 工具调用）：
        fusion = DataFusion(
            data_provider="footystats",
            footystats=fs,
            understat=us,
        )
        ctx = await fusion.build(
            fixture_id="8255851",
            match_id="8255851",
            home_team="Arsenal",
            home_team_id="86",
            away_team="Chelsea",
            away_team_id="83",
            season_id="1980",
            league="Premier League",
            match_date="2026-04-09",
        )
    """

    def __init__(
        self,
        footystats: "FootyStatsProvider",
        understat: "UnderstatProvider",
    ) -> None:
        self._resolver = FootyStatsResolver(footystats=footystats, understat=understat)

    async def build(
        self,
        fixture_id: str,
        match_id: str,
        home_team: str,
        home_team_id: str,
        away_team: str,
        away_team_id: str,
        season_id: str,
        league: str,
        match_date: Optional[str] = None,
        season: Optional[str] = None,
    ) -> MatchContext:
        """
        并行解析所有数据层，构建并返回 MatchContext。

        Args:
            fixture_id:    比赛 fixture ID（Sportmonks 使用）
            match_id:      FootyStats 比赛 ID
            home_team:     主队名称
            home_team_id:  主队 ID
            away_team:     客队名称
            away_team_id:  客队 ID
            season_id:     competition/season ID（用于积分榜）
            league:        联赛名（如 "Premier League"）
            match_date:    比赛日期 YYYY-MM-DD（可选，用于日志）
            season:        Understat 赛季年份（如 "2025"），默认从 match_date 推断

        Returns:
            MatchContext
        """
        # 推断赛季年份（Understat 需要）
        resolved_season = season or _infer_season(match_date)

        logger.info(
            f"[Fusion] Building context: {home_team} vs {away_team} "
            f"| league={league} | season={resolved_season}"
        )

        # 并行解析所有 8 类数据
        (
            xg_res,
            form_res,
            standings_res,
            odds_res,
            lineups_res,
            odds_mv_res,
            h2h_res,
            predictions_res,
        ) = await asyncio.gather(
            self._resolver.resolve_xg(
                home_team=home_team,
                away_team=away_team,
                league=league,
                season=resolved_season,
                home_team_id=home_team_id,
                away_team_id=away_team_id,
            ),
            self._resolver.resolve_form(
                home_team_id=home_team_id,
                away_team_id=away_team_id,
            ),
            self._resolver.resolve_standings(season_id=season_id),
            self._resolver.resolve_odds(match_id=match_id),
            self._resolver.resolve_lineups(
                fixture_id=fixture_id,
                home_team_id=home_team_id,
                away_team_id=away_team_id,
            ),
            self._resolver.resolve_odds_movement(fixture_id=fixture_id),
            self._resolver.resolve_head_to_head(
                home_team_id=home_team_id,
                away_team_id=away_team_id,
            ),
            self._resolver.resolve_predictions(fixture_id=fixture_id),
            return_exceptions=True,
        )

        # 将异常转为 missing
        xg_res = _safe_result(xg_res, "xg")
        form_res = _safe_result(form_res, "form")
        standings_res = _safe_result(standings_res, "standings")
        odds_res = _safe_result(odds_res, "odds")
        lineups_res = _safe_result(lineups_res, "lineups")
        odds_mv_res = _safe_result(odds_mv_res, "odds_movement")
        h2h_res = _safe_result(h2h_res, "head_to_head")
        predictions_res = _safe_result(predictions_res, "predictions")

        # 映射到类型化结构
        xg = self._map_xg(xg_res, home_team, away_team, league)
        home_form_5, home_form_10, away_form_5, away_form_10 = self._map_form(form_res)
        home_standing, away_standing, total_teams = self._map_standings(
            standings_res, home_team, away_team
        )
        odds = self._map_odds(odds_res)

        # 收集缺失项
        data_gaps: list[str] = []
        if xg is None:
            data_gaps.append("xg")
        if home_form_5 is None and home_form_10 is None:
            data_gaps.append("form")
        if home_standing is None or away_standing is None:
            data_gaps.append("standings")
        if odds is None:
            data_gaps.append("odds")
        data_gaps.append("injuries")

        # 质量评分
        xg_quality = xg_res.quality if xg_res.ok else 0.0
        form_quality = form_res.quality if form_res.ok else 0.0
        standings_quality = standings_res.quality if standings_res.ok else 0.0
        odds_quality = odds_res.quality if odds_res.ok else 0.0
        overall_quality = compute_overall_quality(
            xg_quality, form_quality, standings_quality, odds_quality
        )

        sources = {
            "xg": xg_res.source,
            "form": form_res.source,
            "standings": standings_res.source,
            "odds": odds_res.source,
        }

        logger.info(
            f"[Fusion] Done: quality={overall_quality:.2f} "
            f"| gaps={data_gaps} | sources={sources}"
        )

        return MatchContext(
            data_provider="footystats",
            match_id=match_id,
            league=league,
            home_team=home_team,
            home_team_id=home_team_id,
            away_team=away_team,
            away_team_id=away_team_id,
            season_id=season_id,
            match_date=match_date,
            xg=xg,
            home_form_5=home_form_5,
            home_form_10=home_form_10,
            away_form_5=away_form_5,
            away_form_10=away_form_10,
            form_source=form_res.source,
            form_quality=form_quality,
            home_standing=home_standing,
            away_standing=away_standing,
            total_teams=total_teams,
            standings_source=standings_res.source,
            standings_quality=standings_quality,
            odds=odds,
            data_gaps=tuple(data_gaps),
            overall_quality=overall_quality,
            sources=sources,
            resolved_at=time.time(),
        )

    # ── 私有映射方法 ──────────────────────────────────────────

    def _map_xg(
        self,
        res: ResolvedData,
        home_team: str,
        away_team: str,
        league: str,
    ) -> Optional[XGStats]:
        """
        将 resolver xG 结果映射为 XGStats。
        league_avg 兜底：从 LEAGUE_PARAMS 填充联赛均值。
        """
        if not res.ok:
            return None

        data = res.data or {}

        if res.source == "league_avg":
            # 联赛均值兜底：50/50 分配
            league_params = settings.get_league_params(league)
            avg = league_params.get("avg_goals", settings.AVG_GOALS_DEFAULT) / 2
            return XGStats(
                home_xg_for=avg,
                home_xg_against=avg,
                away_xg_for=avg,
                away_xg_against=avg,
                source="league_avg",
                quality=res.quality,
            )

        return XGStats(
            home_xg_for=float(data.get("home_xg_for") or 0.0),
            home_xg_against=float(data.get("home_xg_against") or 0.0),
            away_xg_for=float(data.get("away_xg_for") or 0.0),
            away_xg_against=float(data.get("away_xg_against") or 0.0),
            source=res.source,
            quality=res.quality,
        )

    def _map_form(
        self, res: ResolvedData
    ) -> tuple[
        Optional[TeamFormWindow],
        Optional[TeamFormWindow],
        Optional[TeamFormWindow],
        Optional[TeamFormWindow],
    ]:
        """将 resolver form 结果映射为 (home_5, home_10, away_5, away_10)。"""
        if not res.ok or not res.data:
            return None, None, None, None

        home = res.data.get("home") or {}
        away = res.data.get("away") or {}

        home_5 = _build_form_window(home, 5)
        home_10 = _build_form_window(home, 10)
        away_5 = _build_form_window(away, 5)
        away_10 = _build_form_window(away, 10)

        return home_5, home_10, away_5, away_10

    def _map_standings(
        self,
        res: ResolvedData,
        home_team: str,
        away_team: str,
    ) -> tuple[Optional[StandingsEntry], Optional[StandingsEntry], int]:
        """
        从积分榜数据中提取主客队条目。
        返回：(home_standing, away_standing, total_teams)
        """
        if not res.ok or not res.data:
            return None, None, 0

        raw = res.data.get("raw")
        if not raw:
            return None, None, 0

        # FootyStats league_tables 格式：{"data": [...]} 或直接列表
        table_list: list[dict] = []
        if isinstance(raw, dict):
            table_list = raw.get("data") or raw.get("standings") or []
        elif isinstance(raw, list):
            table_list = raw

        if not table_list:
            return None, None, 0

        total_teams = len(table_list)
        home_entry = _find_standing(table_list, home_team)
        away_entry = _find_standing(table_list, away_team)

        return home_entry, away_entry, total_teams

    def _map_odds(self, res: ResolvedData) -> Optional[OddsSnapshot]:
        """将 resolver odds 结果映射为 OddsSnapshot。"""
        if not res.ok or not res.data:
            return None

        data = res.data
        home = float(data.get("home_win") or 0)
        draw = float(data.get("draw") or 0)
        away = float(data.get("away_win") or 0)

        if home <= 1.0 or draw <= 1.0 or away <= 1.0:
            return None

        return OddsSnapshot(
            home_win=home,
            draw=draw,
            away_win=away,
            source=res.source,
            quality=res.quality,
        )

# ── 模块级辅助函数 ────────────────────────────────────────────


def _infer_season(match_date: Optional[str]) -> str:
    """
    从比赛日期推断 Understat 赛季年份。
    足球赛季一般 8 月开始，因此 1–7 月用上一年。
    """
    if not match_date:
        now = datetime.datetime.now()
        year = now.year - 1 if now.month < 8 else now.year
        return str(year)

    try:
        year = int(match_date[:4])
        month = int(match_date[5:7])
        return str(year - 1 if month < 8 else year)
    except (ValueError, IndexError):
        return str(datetime.datetime.now().year - 1)


def _safe_result(result: Any, data_type: str) -> ResolvedData:
    """将 asyncio.gather 异常或无效值转为 missing ResolvedData。"""
    if isinstance(result, BaseException):
        logger.opt(exception=result).error(f"[Fusion] {data_type} task failed")
        return ResolvedData.missing(data_type)
    if not isinstance(result, ResolvedData):
        return ResolvedData.missing(data_type)
    return result


def _build_form_window(
    form_data: dict[str, Any], window: int
) -> Optional[TeamFormWindow]:
    """从提取的 form dict 构建 TeamFormWindow。"""
    avg_scored = form_data.get(f"avg_scored_{window}")
    if avg_scored is None:
        return None

    return TeamFormWindow(
        games=window,
        wins=int(form_data.get(f"wins_{window}", 0)),
        draws=int(form_data.get(f"draws_{window}", 0)),
        losses=int(form_data.get(f"losses_{window}", 0)),
        goals_scored=float(form_data.get(f"goals_scored_{window}", 0.0)),
        goals_conceded=float(form_data.get(f"goals_conceded_{window}", 0.0)),
        avg_scored=float(avg_scored),
        avg_conceded=float(form_data.get(f"avg_conceded_{window}", 0.0)),
    )


def _find_standing(
    table: list[dict[str, Any]], team_name: str
) -> Optional[StandingsEntry]:
    """在积分榜列表中匹配球队并返回 StandingsEntry。"""
    name_lower = team_name.lower().strip()
    keywords = [w for w in name_lower.split() if len(w) > 3]

    for row in table:
        if not isinstance(row, dict):
            continue

        # FootyStats league_tables 格式字段尝试
        row_name = (
            row.get("name")
            or row.get("team_name")
            or row.get("cleanName")
            or str(row.get("id", ""))
        ).lower()

        # TODO: improve team name matching — substring keyword match can produce false
        # positives (e.g. "West Ham" keywords matching "West Brom").
        if row_name == name_lower or any(kw in row_name for kw in keywords):
            return StandingsEntry(
                position=int(row.get("position") or row.get("pos") or 0),
                points=int(row.get("points") or row.get("pts") or 0),
                played=int(row.get("played") or row.get("gp") or 0),
                wins=int(row.get("wins") or row.get("won") or 0),
                draws=int(row.get("draws") or row.get("draw") or 0),
                losses=int(row.get("losses") or row.get("lost") or 0),
                goals_for=int(row.get("goals_for") or row.get("gf") or 0),
                goals_against=int(row.get("goals_against") or row.get("ga") or 0),
            )

    return None

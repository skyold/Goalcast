"""
OddAlerts Football Data API Provider

API 文档: https://documenter.getpostman.com/view/17615275/2s935uG1WF
基础 URL: https://data.oddalerts.com/api
认证: api_token 查询参数（所有请求）
速率限制: x-ratelimit-limit=300（每单位时间）

注意：服务器对未知路径返回 "OddAlerts Data Engine"（HTML 200），
      需要开启 follow_redirects=True 才能正常访问各端点。

━━━ 已验证可用端点 ━━━

【赛事端点】
  GET /api/fixtures/id           单场比赛详情（id=fixture_id）
  GET /api/fixtures/between      日期范围赛程（实测始终返回空，疑似 API bug）

【赔率端点】
  GET /api/odds/history          单场比赛完整赔率历史
                                 字段: opening / closing / peak
                                 市场: ft_result, ht_result, dnb, btts, btts_1h/2h,
                                       total_goals, total_goals_1h/2h, asian_corners,
                                       total_corners, away_goals, home_goals,
                                       goal_line, asian_handicap, double_chance,
                                       highest_scoring_half, btts_o25
                                 博彩: Bet365, Pinnacle, 1xBet, WilliamHill, Kambi Group
  GET /api/odds/dropping         跌水赔率（用于发现当日/近期有赔率的比赛）
                                 字段: fixture_id, fixture_name, opening, closing,
                                       drop_percentage, bookmaker, market_key

【统计端点】
  GET /api/stats                 球队完整赛季/赛前统计（type="season"|"fixture"，id=...）
                                 字段涵盖: 胜平负/进失球/角球/卡牌/射门/控球
                                 xG 字段: xg_for, xg_against, xg_total, most_xg,
                                           xg_performance

【概率模型端点】
  GET /api/trends/homeWin        主场胜趋势赛事（含 OddAlerts 概率预测 + 当前赔率）
  GET /api/trends/awayWin        客场胜趋势赛事
  GET /api/trends/btts           双方进球趋势赛事
                                 probability 字段: home_win/draw/away_win/btts/
                                   o15/o25/o35/o45/o05_home/away_goals/o85_corners

【联赛端点】
  GET /api/competitions          所有联赛/杯赛列表（2412 条）
  GET /api/user                  账户信息
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta
from typing import TYPE_CHECKING, Dict, Any, Optional, Literal
import httpx

from provider.base import BaseProvider
from utils.logger import logger
from config.settings import settings

if TYPE_CHECKING:
    from provider.models import ProviderFixture

TrendMarket = Literal["homeWin", "awayWin", "btts"]
StatsType = Literal["season", "fixture"]


def _extract_team_row(stats_resp: object, team_id: object) -> Optional[Dict[str, Any]]:
    """Pick the stats row for a given team_id from an OddAlerts /stats response."""
    if not isinstance(stats_resp, dict):
        return None
    rows = stats_resp.get("data") or []
    if not isinstance(rows, list):
        return None
    for row in rows:
        if isinstance(row, dict) and row.get("team_id") == team_id:
            return row
    return None


class OddAlertsProvider(BaseProvider):
    """OddAlerts Football Data API 提供者（Pro 订阅）"""

    BASE_URL = "https://data.oddalerts.com/api"
    DEFAULT_TIMEOUT = 30.0

    def __init__(self, api_key: str = "", timeout: float = DEFAULT_TIMEOUT):
        super().__init__(api_key or settings.ODDALERTS_API_KEY, timeout)
        if not self.api_key:
            logger.warning("OddAlerts API key not configured")

    async def _get_client(self) -> httpx.AsyncClient:
        # OddAlerts 服务器对所有端点先 302 再返回数据，必须开启重定向跟随
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
            )
        return self._client

    @property
    def name(self) -> str:
        return "oddalerts"

    async def is_available(self) -> bool:
        return bool(self.api_key)

    async def _request_raw(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        if not self.api_key:
            logger.error("OddAlerts API key is not set")
            return None

        all_params: Dict[str, Any] = {"api_token": self.api_key}
        if params:
            all_params.update(params)

        result = await self._request(endpoint, all_params)

        # 服务器对无效路径/权限不足时返回纯文本 "OddAlerts Data Engine"
        # _request() 会因为 response.json() 抛 JSONDecodeError 而返回 None，已经处理
        return result

    # ==================== 赛事端点 ====================

    async def get_fixture(self, fixture_id: int) -> Optional[Dict[str, Any]]:
        """
        获取单场比赛详情

        Returns 字段:
            id, home_name, away_name, competition_id, competition_name,
            competition_country, season_id, season, home_id, away_id,
            status (NS/FT/...), home_goals, away_goals, ht_score,
            unix, date, ko_human, has_odds, is_friendly, is_cup
        """
        logger.debug(f"Provider {self.name}: get_fixture(fixture_id={fixture_id})")
        result = await self._request_raw("/fixtures/id", {"id": fixture_id})
        if result and isinstance(result.get("data"), list):
            return result["data"][0] if result["data"] else None
        return result

    async def get_fixtures_between(
        self,
        start_date: str,
        end_date: str,
    ) -> Optional[Dict[str, Any]]:
        """
        获取日期范围内的赛程（注：API 实测此端点始终返回空数据，疑似 bug）

        Args:
            start_date: 开始日期，格式 YYYY-MM-DD
            end_date:   结束日期，格式 YYYY-MM-DD
        """
        logger.debug("Provider %s: get_fixtures_between(%s, %s)", self.name, start_date, end_date)
        return await self._request_raw("/fixtures/between", {"start": start_date, "end": end_date})

    # ==================== 赔率端点 ====================

    async def get_odds_history(self, fixture_id: int) -> Optional[Dict[str, Any]]:
        """
        获取单场比赛完整赔率历史（开盘/收盘/最高）

        Returns 字段（每条记录）:
            fixture_id, market_key, market_id, outcome,
            opening, closing, peak,
            bookmaker_id, bookmaker_name

        市场 market_key 包括:
            ft_result, ht_result, dnb, double_chance, btts,
            btts_1h, btts_2h, btts_o25, total_goals, total_goals_1h,
            total_goals_2h, asian_corners, asian_corners_1h, total_corners,
            away_goals, home_goals, goal_line, asian_handicap,
            highest_scoring_half

        博彩公司: Bet365, Pinnacle, 1xBet, WilliamHill, Kambi Group
        """
        logger.debug(f"Provider {self.name}: get_odds_history(fixture_id={fixture_id})")
        return await self._request_raw("/odds/history", {"id": fixture_id})

    async def get_dropping_odds(
        self,
        page: int = 1,
    ) -> Optional[Dict[str, Any]]:
        """
        获取跌水赔率（赔率大幅下跌的比赛，用于发现近期有赔率的赛事）

        Returns 字段（每条记录）:
            fixture_id, fixture_name, season_id, season,
            competition_id, competition_name, competition_type, competition_country,
            market_key, market_id, outcome,
            opening, closing, drop_percentage,
            unix, ko_human, bookmaker_id, bookmaker_name

        注: total=29685，约 250 条/页，按跌幅排序
        """
        logger.debug(f"Provider {self.name}: get_dropping_odds(page={page})")
        return await self._request_raw("/odds/dropping", {"page": page})

    # ==================== 预测端点 ====================

    async def get_predictions_generate(self, fixture_id: int) -> Optional[Dict[str, Any]]:
        """
        蒙特卡洛模拟（50k 次）—— /predictions/generate/{fixture_id}

        Returns 字段:
            home_win_percentage, draw_percentage, away_win_percentage
            btts_percentage, btts_no_percentage
            o15/o25/o35_goals_percentage
            expected_goals: {home, away, total}
            scorelines: {"1_0": 15.2, "0_0": 8.1, ...}
            first_half: {home_win_percentage, draw_percentage, away_win_percentage}
            asian_handicap: {home_p025: 52.1, away_p025: 47.9, ...}
        """
        logger.debug("Provider %s: get_predictions_generate(fixture_id=%s)", self.name, fixture_id)
        result = await self._request_raw(f"/predictions/generate/{fixture_id}")
        if result and isinstance(result.get("data"), list):
            return result["data"][0] if result["data"] else None
        return result

    async def get_fixture_h2h(self, fixture_id: int) -> Optional[Dict[str, Any]]:
        """
        获取比赛详情，含 H2H 历史和正确比分概率 —— /fixtures/{fixture_id}?include=h2h,correctScores

        注意：URL 使用路径参数，与 get_fixture 的查询参数 (?id=) 不同。

        Returns 字段:
            h2h: 近期对阵记录列表，每条含
                date, home_name, away_name, home_goals, away_goals,
                home_win, away_win, draw, btts, over_25
            correct_scores: {score_string: probability, ...}
                e.g. {"1_0": 14.2, "0_0": 8.5, "1_1": 11.3, ...}
        """
        logger.debug("Provider %s: get_fixture_h2h(fixture_id=%s)", self.name, fixture_id)
        result = await self._request_raw(f"/fixtures/{fixture_id}", {"include": "h2h,correctScores"})
        if result and isinstance(result.get("data"), list):
            return result["data"][0] if result["data"] else None
        return result

    async def get_stats_recent(self, season_id: int, last_x: str) -> Optional[Dict[str, Any]]:
        """
        获取赛季内近期状态统计 —— /stats/season/{season_id}?last_x=...

        Args:
            season_id: 赛季 ID（来自 fixture.season_id）
            last_x:    "5_home"    → 主队近 5 场主场数据
                       "5_away"    → 客队近 5 场客场数据
                       "10_overall"→ 近 10 场总体数据

        Returns: 包含赛季内所有球队的统计列表，取用 team_id 匹配目标球队。
                 字段同 get_stats（PPG、进失球均值、BTTS、大球率、xG 等）
        """
        logger.debug(
            "Provider %s: get_stats_recent(season_id=%s, last_x=%s)", self.name, season_id, last_x
        )
        return await self._request_raw(f"/stats/season/{season_id}", {
            "last_x": last_x,
            "include_frozen": "false",
        })

    # ==================== 统计端点 ====================

    async def get_stats(
        self,
        stats_type: StatsType,
        id: int,
        include_frozen: bool = False,
        last_x: Optional[int] = None,
        include_avg: bool = False,
        page: int = 1,
    ) -> Optional[Dict[str, Any]]:
        """
        获取球队完整统计数据（赛季维度或赛前冻结快照）

        Args:
            stats_type:     "season"（赛季总统计）或 "fixture"（赛前冻结统计，更准确）
            id:             season_id 或 fixture_id（与 stats_type 对应）
            include_frozen: 是否返回冻结版本（赛前快照）
            last_x:         只取最近 x 场的统计
            include_avg:    是否包含均值字段

        Returns 字段（每支球队一条记录）:
            team_id, name, season_id, fixture_id（fixture 模式）
            played, won, drawn, lost, points
            goals_total, goals_for, goals_against, goals_difference
            goals_over (大球场次), btts, clean_sheet, failed_to_score
            goals_1h/2h, btts_1h/2h
            fouls, yellow_cards, red_cards, cards_over
            corners_total/for/against/over, corners_1h/2h
            xg_total, xg_for, xg_against         ← xG 数据
            most_xg, xg_performance              ← xG 超表现
            shots_total/for/against, shots_on_*
            attacks_*, dangerous_attacks_*
            possession_for, possession_against
            shot_conversion, sot_accuracy, sot_conversion
            dangerous_attack_conversion
            goal_timing, first_goal_time
        """
        logger.debug(f"Provider {self.name}: get_stats(type={stats_type}, id={id})")
        params: Dict[str, Any] = {"type": stats_type, "id": id, "page": page}
        if include_frozen:
            params["include_frozen"] = 1
        if last_x is not None:
            params["last_x"] = last_x
        if include_avg:
            params["include_avg"] = 1
        return await self._request_raw("/stats", params)

    # ==================== 概率模型端点 ====================

    async def get_trends(
        self,
        market: TrendMarket,
        min_stat: Optional[float] = None,
        max_stat: Optional[float] = None,
        sort: Literal["stat", "odds", "time"] = "odds",
        page: int = 1,
    ) -> Optional[Dict[str, Any]]:
        """
        获取 OddAlerts 趋势赛事（含概率模型预测）

        Args:
            market:   "homeWin" | "awayWin" | "btts"
            min_stat: 统计值下限（百分比，如 65 表示主场胜率 ≥ 65%）
            max_stat: 统计值上限
            sort:     "odds"（默认）| "stat" | "time"

        Returns 字段（每场比赛）:
            home_name, away_name, id, unix, ko_time
            competition_name, competition_id, country
            home_win_per / away_win_per / combined_btts_per（对应 market）
            probability:
                home_win, draw, away_win   ← OddAlerts 概率模型
                btts, o15/o25/o35/o45
                o05_home_goals, o15_home_goals
                o05_away_goals, o15_away_goals
                o85_corners
            stats.home / stats.away:
                played, won, drawn, lost, scored, conceded 及均值
            odds: {"odds": "3.75", "updated_at": ...}  ← 当前盘口赔率
        """
        logger.debug(f"Provider {self.name}: get_trends(market={market})")
        params: Dict[str, Any] = {"sort": sort, "page": page}
        if min_stat is not None:
            params["minStat"] = min_stat
        if max_stat is not None:
            params["maxStat"] = max_stat
        return await self._request_raw(f"/trends/{market}", params)

    # ==================== 联赛端点 ====================

    async def get_competitions(self, page: int = 1) -> Optional[Dict[str, Any]]:
        """
        获取所有联赛/杯赛列表（共 2412 条）

        Returns 字段: id, name, slug, country, country_id, type, current_season
        """
        logger.debug(f"Provider {self.name}: get_competitions(page={page})")
        return await self._request_raw("/competitions", {"page": page})

    async def get_account_info(self) -> Optional[Dict[str, Any]]:
        """
        获取账户信息（用于验证 API key 及订阅状态）

        Returns 字段: id, name, role, api, pro_activated_at, league_limit ...
        """
        logger.debug(f"Provider {self.name}: get_account_info()")
        return await self._request_raw("/user", {})

    # ==================== Provider 抽象接口实现 ====================

    async def discover_fixtures(
        self,
        league_ids: list[int],
        dates: list[str],
    ) -> list[ProviderFixture]:
        """
        两阶段发现策略：
        1. 尝试 /fixtures/between（快速但已知 API 有 bug，通常返回空）
        2. 合并 homeWin / awayWin / btts 三个趋势端点扫描（无 min_stat 过滤）

        league_ids: OddAlerts competition_id 列表，空表示不过滤。
        dates:      ISO 日期字符串列表。
        """
        from provider.models import ProviderFixture

        if not dates:
            return []

        start_date = min(dates)
        end_date = max(dates)

        # 将日期转为 unix 范围 [day_start, day_end + 24h)
        day_start_unix = int(datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())
        day_end_unix = int(
            (datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)).replace(tzinfo=timezone.utc).timestamp()
        )

        # ── 策略 1：/fixtures/between ──────────────────────────────────────────
        resp = await self.get_fixtures_between(start_date, end_date)
        tier1_items: list[dict] = []
        if isinstance(resp, dict):
            tier1_items = resp.get("data", [])

        if tier1_items:
            logger.info("oddalerts: discover_fixtures tier-1 returned %d items", len(tier1_items))
            return self._parse_fixtures_list(tier1_items, league_ids, day_start_unix, day_end_unix)

        # ── 策略 2：合并三个趋势端点 ──────────────────────────────────────────
        logger.info("oddalerts: tier-1 empty, falling back to trends scan")
        seen: set[int] = set()
        result: list[ProviderFixture] = []

        for market in ("homeWin", "awayWin", "btts"):
            page = 1
            while True:
                resp = await self.get_trends(market, page=page)
                if not isinstance(resp, dict):
                    break
                items = resp.get("data", [])
                if not items:
                    break

                found_in_window = False
                for item in items:
                    fid = item.get("id")
                    if fid is None or fid in seen:
                        continue

                    unix = item.get("unix")
                    if unix is None:
                        continue
                    unix = int(unix)
                    if not (day_start_unix <= unix < day_end_unix):
                        continue

                    found_in_window = True
                    if league_ids and item.get("competition_id") not in league_ids:
                        continue

                    seen.add(fid)
                    result.append(ProviderFixture(
                        provider=self.name,
                        fixture_id=fid,
                        home_team=item.get("home_name", ""),
                        away_team=item.get("away_name", ""),
                        kickoff_unix=unix,
                        league_name=item.get("competition_name"),
                        raw=item,
                    ))

                meta = resp.get("meta", {})
                current_page = meta.get("current_page", page)
                last_page = meta.get("last_page", 1)
                if current_page >= last_page:
                    break
                # 如果本页无任何目标日期内的比赛且已翻超 10 页，停止扫描
                if not found_in_window and page >= 10:
                    break
                page += 1

        logger.info("oddalerts: discover_fixtures found %d fixtures via trends", len(result))
        return result

    def _parse_fixtures_list(
        self,
        items: list[dict],
        league_ids: list[int],
        day_start_unix: int,
        day_end_unix: int,
    ) -> list[ProviderFixture]:
        from provider.models import ProviderFixture

        seen: set[int] = set()
        result: list[ProviderFixture] = []
        for item in items:
            fid = item.get("id")
            if fid is None or fid in seen:
                continue
            unix = item.get("unix")
            if unix is None:
                continue
            unix = int(unix)
            if not (day_start_unix <= unix < day_end_unix):
                continue
            if league_ids and item.get("competition_id") not in league_ids:
                continue
            seen.add(fid)
            result.append(ProviderFixture(
                provider=self.name,
                fixture_id=fid,
                home_team=item.get("home_name", ""),
                away_team=item.get("away_name", ""),
                kickoff_unix=unix,
                league_name=item.get("competition_name"),
                raw=item,
            ))
        return result

    # ==================== 组合方法 ====================

    async def collect_fixture_data(self, oa_fixture_id: int) -> Optional[Dict[str, Any]]:
        """Assemble the analytics-spec bundle for one fixture.

        Performs parallel fetches against fixture / odds-history / stats /
        predictions / h2h endpoints. Maps OddAlerts-internal shapes onto the
        plan-spec keys so downstream analytics see a stable contract.

        Returns a dict with keys (a subset of):
            fixture, odds_history, h2h, stats_home, stats_away, trends

        Returns ``None`` when the provider is not configured or yields no
        usable data. The internal http client is closed before returning.
        """
        if not await self.is_available():
            logger.debug("OddAlerts API key 未配置，跳过 collect_fixture_data")
            return None

        try:
            fixture, odds, stats, predictions, fixture_h2h = await asyncio.gather(
                self.get_fixture(oa_fixture_id),
                self.get_odds_history(oa_fixture_id),
                self.get_stats("fixture", oa_fixture_id),
                self.get_predictions_generate(oa_fixture_id),
                self.get_fixture_h2h(oa_fixture_id),
                return_exceptions=True,
            )

            result: Dict[str, Any] = {}

            if isinstance(fixture, dict):
                result["fixture"] = fixture
            if isinstance(odds, dict):
                result["odds_history"] = odds
            if isinstance(fixture_h2h, dict):
                h2h_list = fixture_h2h.get("h2h") or []
                result["h2h"] = h2h_list[:6]

            home_id = fixture.get("home_id") if isinstance(fixture, dict) else None
            away_id = fixture.get("away_id") if isinstance(fixture, dict) else None

            # Map stats[data][...] rows → stats_home / stats_away
            if isinstance(stats, dict) and home_id is not None and away_id is not None:
                stats_home = _extract_team_row(stats, home_id)
                stats_away = _extract_team_row(stats, away_id)
                if stats_home:
                    result["stats_home"] = stats_home
                if stats_away:
                    result["stats_away"] = stats_away

            # Map Monte-Carlo predictions → trends shape consumed by analytics
            if isinstance(predictions, dict):
                trends: Dict[str, Any] = {}
                hw = predictions.get("home_win_percentage")
                aw = predictions.get("away_win_percentage")
                dw = predictions.get("draw_percentage")
                bt = predictions.get("btts_percentage")
                if hw is not None:
                    trends["homeWin"] = float(hw) / 100.0
                if aw is not None:
                    trends["awayWin"] = float(aw) / 100.0
                if dw is not None:
                    trends["draw"] = float(dw) / 100.0
                if bt is not None:
                    trends["btts"] = float(bt) / 100.0
                if trends:
                    result["trends"] = trends

            if not result:
                logger.warning("OddAlerts fixture %d 未返回任何数据", oa_fixture_id)
                return None

            return result

        except Exception as exc:
            logger.warning("OddAlerts collect_fixture_data failed oa_fixture_id=%d: %s", oa_fixture_id, exc)
            return None
        finally:
            await self.close()

    async def get_fixture_full(self, fixture_id: int) -> Dict[str, Any]:
        """
        获取单场比赛的完整数据包：赛事详情 + 开盘/收盘赔率 + 赛前统计（含 xG）

        Returns:
            {
                "fixture": {...},       # 比赛基本信息
                "odds":    {"data": [...], ...},  # 开盘/收盘/最高赔率（多市场多博彩）
                "stats":   {"data": [...], ...},  # 双队赛前冻结统计（含 xG）
            }
        """
        import asyncio
        fixture_task = self.get_fixture(fixture_id)
        odds_task    = self.get_odds_history(fixture_id)
        stats_task   = self.get_stats("fixture", fixture_id)

        fixture, odds, stats = await asyncio.gather(fixture_task, odds_task, stats_task)
        return {"fixture": fixture, "odds": odds, "stats": stats}

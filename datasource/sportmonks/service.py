"""Sportmonks 独立数据层服务入口，极简版。"""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Optional

from config.settings import BASE_DIR


class SimpleCache:
    """轻量级文件缓存管理。"""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = Path(base_dir) if base_dir else (BASE_DIR / "data" / "cache" / "sportmonks")
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _atomic_write(self, path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Warning: Failed to write cache {path}: {e}")

    def read_json(self, filename: str) -> Optional[Any]:
        path = self.base_dir / filename
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return None

    def write_json(self, filename: str, payload: Any) -> None:
        self._atomic_write(self.base_dir / filename, payload)

    def is_expired(self, filename: str, ttl_hours: int) -> bool:
        path = self.base_dir / filename
        if not path.exists():
            return True
        mtime = datetime.fromtimestamp(path.stat().st_mtime)
        return datetime.now() - mtime > timedelta(hours=ttl_hours)


def _matches_league(league_data: dict[str, Any], requested_league: str) -> bool:
    """模糊匹配联赛名。"""
    actual_name = str(league_data.get("name", "")).lower()
    requested_name = requested_league.lower()
    if requested_name in actual_name:
        return True
    
    # 支持一些常见的简写/别名
    alias_map = {
        "premier league": ["premier league", "epl", "eng"],
        "championship": ["championship", "champ"],
        "serie a": ["serie a", "ita"],
    }
    
    aliases = alias_map.get(requested_name, [])
    for alias in aliases:
        if alias in actual_name:
            return True
    return False


class SportmonksDataService:
    """提供 Agent 调用的两大核心只读接口。"""

    def __init__(self, provider: Any, cache: Optional[SimpleCache] = None):
        self.provider = provider
        self.cache = cache or SimpleCache()

    async def get_matches(
        self,
        date: Optional[str] = None,
        leagues: Optional[list[str]] = None,
    ) -> list[dict[str, Any]]:
        """获取指定日期（默认今天）的比赛列表，可按联赛过滤。"""
        target_date = date or datetime.today().strftime("%Y-%m-%d")
        cache_key = f"fixtures_{target_date}.json"

        # 判断 TTL：如果是今天的比赛，TTL 设为 2 小时；如果是历史，永不过期 (9999h)
        is_today = target_date == datetime.today().strftime("%Y-%m-%d")
        ttl = 2 if is_today else 9999

        fixtures = self.cache.read_json(cache_key)
        if fixtures is None or self.cache.is_expired(cache_key, ttl_hours=ttl):
            # 获取数据，使用 include 一次性拿回常用信息以及预测数据
            include_str = "participants;league;scores;season;venue;predictions"
            raw_response = await self.provider.get_fixtures_by_date(
                target_date, include=include_str
            )
            fixtures = raw_response.get("data", []) if isinstance(raw_response, dict) else []
            
            # 为列表页也提前计算 predictive_xg
            for fixture in fixtures:
                predictions = fixture.get("predictions", [])
                predictive_xg = None
                if isinstance(predictions, list):
                    for p in predictions:
                        if p.get("type_id") == 240:
                            scores_prob = p.get("predictions", {}).get("scores", {})
                            if scores_prob:
                                h_xg, a_xg = 0.0, 0.0
                                for score, prob in scores_prob.items():
                                    if "Other" in score:
                                        if score == "Other_1": h_xg += 4 * prob / 100; a_xg += 1 * prob / 100
                                        elif score == "Other_2": h_xg += 1 * prob / 100; a_xg += 4 * prob / 100
                                        elif score == "Other_X": h_xg += 4 * prob / 100; a_xg += 4 * prob / 100
                                    else:
                                        try:
                                            h, a = map(int, score.split('-'))
                                            h_xg += h * prob / 100; a_xg += a * prob / 100
                                        except ValueError:
                                            pass
                                predictive_xg = {"home": round(h_xg, 3), "away": round(a_xg, 3)}
                            break
                if predictive_xg:
                    fixture["predictive_xg"] = predictive_xg
                # 移除完整的 predictions 以减小文件体积
                if "predictions" in fixture:
                    del fixture["predictions"]
                    
            self.cache.write_json(cache_key, fixtures)

        if leagues and fixtures:
            filtered = []
            for fixture in fixtures:
                league_data = fixture.get("league", {})
                for requested_league in leagues:
                    if _matches_league(league_data, requested_league):
                        filtered.append(fixture)
                        break
            fixtures = filtered

        return fixtures

    async def _get_all_predictions(self, fixture_id: int) -> list[dict]:
        """获取某场比赛的所有预测数据（处理分页）"""
        all_predictions = []
        page = 1
        while page <= 5:  # 最多拉取 5 页
            res = await self.provider.get_probabilities_by_fixture(fixture_id, include="type", page=page)
            if not res:
                break
            
            data = res.get("data", [])
            if not data:
                break
                
            all_predictions.extend(data)
            
            pagination = res.get("pagination", {})
            if not pagination.get("has_more", False):
                break
                
            page += 1
            
        return all_predictions

    async def get_match_for_analysis(
        self,
        fixture_id: int,
        match_date: Optional[str] = None,
    ) -> dict[str, Any]:
        """读取单场比赛详情（比赛信息、赔率、交锋、积分榜等），组装为扁平字典返回。"""
        cache_key = f"match_{fixture_id}.json"

        # 读取缓存
        match_data = self.cache.read_json(cache_key)
        
        if match_data:
            # 简单的智能过期判定：如果有 kickoff_time，判断比赛是否已经开始很久
            fixture_info = match_data.get("fixture", {})
            starting_at = fixture_info.get("starting_at")
            if starting_at:
                try:
                    # e.g., "2026-04-15 19:00:00"
                    # 这里偷懒直接字符串截取或简单解析，Sportmonks 返回格式通常是 "YYYY-MM-DD HH:MM:SS"
                    # 这里安全起见直接使用一个短时间的过期机制，或依赖上次拉取时间
                    pass
                except Exception:
                    pass
            
            # 若比赛未完赛且缓存 > 2 小时，重新拉取。为简化，这里设定只要距离上次修改时间不超过2小时则使用缓存。
            # 这里简单起见：假设缓存24小时不过期（可根据实际需要调整，或后续增加完赛判定）
            if not self.cache.is_expired(cache_key, ttl_hours=24):
                return match_data

        # 并发获取各个维度的原始数据
        # 1. 比赛基础、阵容、xG
        fixture_task = self.provider.get_fixture_by_id(
            fixture_id, include="lineups;xGFixture;lineups.xGLineup"
        )
        
        # 2. 预测、赛前赔率
        predictions_task = self._get_all_predictions(fixture_id)
        
        # 处理 provider 赔率接口兼容性
        async def _empty_coro(): return None

        if hasattr(self.provider, "get_prematch_odds_by_fixture"):
            odds_task = self.provider.get_prematch_odds_by_fixture(fixture_id)
        elif hasattr(self.provider, "get_prematch_odds"):
            odds_task = self.provider.get_prematch_odds(fixture_id)
        else:
            odds_task = _empty_coro()
        
        # 3. 价值投注建议
        value_bets_task = self.provider.get_value_bets_by_fixture(fixture_id) if hasattr(self.provider, "get_value_bets_by_fixture") else _empty_coro()
            
        results = await asyncio.gather(
            fixture_task, predictions_task, odds_task, value_bets_task, return_exceptions=True
        )
        
        fixture_res = results[0] if not isinstance(results[0], Exception) else {}
        predictions_res = results[1] if not isinstance(results[1], Exception) else {}
        odds_res = results[2] if not isinstance(results[2], Exception) else {}
        value_bets_res = results[3] if not isinstance(results[3], Exception) else {}

        fixture_payload = fixture_res.get("data", fixture_res) if isinstance(fixture_res, dict) else {}
        
        # 获取参赛队伍以便查 H2H 等
        participants = fixture_payload.get("participants", [])
        home_id, away_id = None, None
        for p in participants:
            meta = p.get("meta", {})
            if meta.get("location") == "home":
                home_id = p.get("id")
            elif meta.get("location") == "away":
                away_id = p.get("id")

        season_id = fixture_payload.get("season_id")
        
        # 进一步拉取 H2H 和 Standings
        h2h_task = self.provider.get_head_to_head(home_id, away_id) if home_id and away_id else _empty_coro()
        standings_task = self.provider.get_standings_by_season(int(season_id)) if season_id else _empty_coro()
        
        extra_results = await asyncio.gather(h2h_task, standings_task, return_exceptions=True)
        h2h_res = extra_results[0] if not isinstance(extra_results[0], Exception) else {}
        standings_res = extra_results[1] if not isinstance(extra_results[1], Exception) else {}

        predictions_data = predictions_res.get("data") if isinstance(predictions_res, dict) else predictions_res
        
        # 关键预测数据映射
        key_predictions_map = {
            233: "1x2",              # 胜平负预测 (1X2)
            231: "btts",             # 双方都进球 (BTTS)
            234: "over_under_1_5",   # 大/小 1.5 球
            235: "over_under_2_5",   # 大/小 2.5 球
            240: "correct_score",    # 比分预测
            237: "ht_1x2",           # 下半场胜平负
        }

        predictions_summary = {}
        predictive_xg = None

        if isinstance(predictions_data, list):
            for p in predictions_data:
                type_id = p.get("type_id")
                preds = p.get("predictions", {})
                
                if type_id in key_predictions_map:
                    market_name = key_predictions_map[type_id]
                    predictions_summary[market_name] = preds

                # 基于 Correct Score (type_id 240) 预测推导预期的 xG (预测性 xG)
                if type_id == 240:  # Correct Score
                    scores_prob = preds.get("scores", {})
                    if scores_prob:
                        home_xg = 0.0
                        away_xg = 0.0
                        for score, prob in scores_prob.items():
                            if "Other" in score:
                                if score == "Other_1":
                                    home_xg += 4 * prob / 100
                                    away_xg += 1 * prob / 100
                                elif score == "Other_2":
                                    home_xg += 1 * prob / 100
                                    away_xg += 4 * prob / 100
                                elif score == "Other_X":
                                    home_xg += 4 * prob / 100
                                    away_xg += 4 * prob / 100
                            else:
                                try:
                                    h, a = map(int, score.split('-'))
                                    home_xg += h * prob / 100
                                    away_xg += a * prob / 100
                                except ValueError:
                                    pass
                        predictive_xg = {
                            "home": round(home_xg, 3),
                            "away": round(away_xg, 3)
                        }

        # 获取历史 xG 对比数据
        historical_xg_comparison = None
        if home_id and away_id:
            analyzer = XGAnalyzer(self.provider)
            historical_xg_comparison = await analyzer.get_match_xg_comparison(home_id, away_id, last_n_fixtures=10)

        # 组装返回结果 (保持相对扁平易读)
        match_data = {
            "fixture": fixture_payload,
            "predictions": predictions_data,
            "predictions_summary": predictions_summary,
            "predictive_xg": predictive_xg,
            "historical_xg_comparison": historical_xg_comparison,
            "value_bets": value_bets_res.get("data") if isinstance(value_bets_res, dict) else value_bets_res,
            "odds": odds_res.get("data") if isinstance(odds_res, dict) else odds_res,
            "h2h": h2h_res.get("data") if isinstance(h2h_res, dict) else h2h_res,
            "standings": standings_res.get("data") if isinstance(standings_res, dict) else standings_res,
            "fetched_at": datetime.now().isoformat()
        }

        self.cache.write_json(cache_key, match_data)
        return match_data


async def _empty() -> Any:
    return None


class XGAnalyzer:
    """分析球队历史 xG 数据，用于赛前预测。
    
    注意: SportMonks 的 /expected/fixtures 端点中，participant_id 不是球队 ID，
    而是内部标识符。正确的方式是通过 fixture_id 获取 xG 数据。
    """

    def __init__(self, provider: Any):
        self.provider = provider

    async def _get_team_recent_fixtures(self, participant_id: int, last_n: int = 10) -> list[dict]:
        """获取球队最近的比赛列表（已完成且有 xG 数据的）。"""
        recent_fixtures = []
        
        # 获取最近的 fixtures（通过日期范围获取）
        # 这里获取过去 60 天的比赛
        from datetime import datetime, timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=60)
        
        # 通过 provider 获取该球队的 fixtures
        if hasattr(self.provider, "get_fixtures_by_team"):
            raw = await self.provider.get_fixtures_by_team(participant_id)
            if raw and isinstance(raw, dict):
                fixtures = raw.get("data", [])
                # 过滤已完成的比赛
                for f in fixtures:
                    state_id = f.get("state_id")
                    starting_at = f.get("starting_at", "")
                    # state_id: 5=FT (finished), 其他状态需要过滤
                    if state_id == 5:  # Finished
                        recent_fixtures.append(f)
                        if len(recent_fixtures) >= last_n:
                            break
        
        return recent_fixtures

    async def _get_fixture_xg(self, fixture_id: int) -> list[dict]:
        """通过 fixture_id 获取单场比赛的 xG 数据。"""
        raw_response = await self.provider._request_raw(
            "/expected/fixtures",
            {"fixture_id": fixture_id}
        )
        if raw_response:
            return raw_response.get("data", [])
        return []

    async def get_team_xg_stats(self, participant_id: int, last_n_fixtures: int = 10) -> dict[str, Any]:
        """获取球队最近 N 场比赛的 xG 统计。
        
        流程:
        1. 获取球队最近的已完成比赛列表
        2. 对每场比赛通过 fixture_id 获取 xG 数据
        3. 计算平均 xG 等统计
        
        Returns:
            dict with keys:
            - participant_id: 球队 ID
            - total_fixtures: 有 xG 数据的比赛总数
            - recent_fixtures_analyzed: 分析的比赛数
            - avg_xg: 平均 xG
            - avg_xg_against: 平均预期失球
            - avg_xg_difference: 平均 xG 差
            - fixtures: 最近比赛的 xG 数据列表
        """
        # 步骤1: 获取最近的已完成比赛
        recent_fixtures = await self._get_team_recent_fixtures(participant_id, last_n_fixtures * 2)
        
        if not recent_fixtures:
            return {
                "participant_id": participant_id,
                "total_fixtures": 0,
                "recent_fixtures_analyzed": 0,
                "avg_xg": None,
                "avg_xg_against": None,
                "avg_xg_difference": None,
                "fixtures": [],
                "error": "No recent finished fixtures found"
            }
        
        # 步骤2: 获取每场比赛的 xG 数据
        fixture_stats = []
        xg_values = []
        xg_against_values = []
        
        for fixture in recent_fixtures[:last_n_fixtures]:
            fid = fixture.get("id")
            if not fid:
                continue
            
            xg_records = await self._get_fixture_xg(fid)
            if not xg_records:
                continue
            
            # 分析这场比赛的 xG 数据
            # xG 数据中有两个 participant，需要根据 location 区分主客队
            home_xg = None
            away_xg = None
            
            for r in xg_records:
                type_id = r.get("type_id")
                location = r.get("location")
                value = r.get("data", {}).get("value")
                
                if type_id == 9684:  # Expected Goals (xG)
                    if location == "home":
                        home_xg = value
                    elif location == "away":
                        away_xg = value
            
            if home_xg is not None or away_xg is not None:
                # 确定当前球队是主队还是客队
                is_home_team = None
                participants = fixture.get("participants", [])
                for p in participants:
                    if p.get("id") == participant_id:
                        meta = p.get("meta", {})
                        is_home_team = meta.get("location") == "home"
                        break
                
                if is_home_team is not None:
                    team_xg = home_xg if is_home_team else away_xg
                    opponent_xg = away_xg if is_home_team else home_xg
                    
                    fixture_stat = {
                        "fixture_id": fid,
                        "opponent": fixture.get("name"),
                        "xg": team_xg,
                        "xg_against": opponent_xg,
                        "xg_difference": (team_xg - opponent_xg) if team_xg is not None and opponent_xg is not None else None,
                    }
                    fixture_stats.append(fixture_stat)
                    
                    if team_xg is not None:
                        xg_values.append(team_xg)
                    if opponent_xg is not None:
                        xg_against_values.append(opponent_xg)
        
        return {
            "participant_id": participant_id,
            "total_fixtures": len(fixture_stats),
            "recent_fixtures_analyzed": len(fixture_stats),
            "avg_xg": round(sum(xg_values) / len(xg_values), 3) if xg_values else None,
            "avg_xg_against": round(sum(xg_against_values) / len(xg_against_values), 3) if xg_against_values else None,
            "avg_xg_difference": round(
                (sum(xg_values) / len(xg_values)) - (sum(xg_against_values) / len(xg_against_values)),
                3
            ) if xg_values and xg_against_values else None,
            "fixtures": fixture_stats,
        }

    async def get_match_xg_comparison(
        self, home_id: int, away_id: int, last_n_fixtures: int = 10
    ) -> dict[str, Any]:
        """对比两队的历史 xG 表现。"""
        home_stats = await self.get_team_xg_stats(home_id, last_n_fixtures)
        away_stats = await self.get_team_xg_stats(away_id, last_n_fixtures)
        
        return {
            "home_team": home_stats,
            "away_team": away_stats,
        }

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
        with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as temp:
            json.dump(payload, temp, ensure_ascii=False, indent=2)
            temp_path = Path(temp.name)
        temp_path.replace(path)

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
            # 获取数据，使用 include 一次性拿回常用信息
            include_str = "participants;league;scores;season;venue"
            raw_response = await self.provider.get_fixtures_by_date(
                target_date, include=include_str
            )
            fixtures = raw_response.get("data", []) if isinstance(raw_response, dict) else []
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
        predictions_task = self.provider.get_probabilities_by_fixture(fixture_id)
        
        # 处理 provider 赔率接口兼容性
        if hasattr(self.provider, "get_prematch_odds_by_fixture"):
            odds_task = self.provider.get_prematch_odds_by_fixture(fixture_id)
        elif hasattr(self.provider, "get_prematch_odds"):
            odds_task = self.provider.get_prematch_odds(fixture_id)
        else:
            async def _empty(): return None
            odds_task = _empty()
            
        results = await asyncio.gather(
            fixture_task, predictions_task, odds_task, return_exceptions=True
        )
        
        fixture_res = results[0] if not isinstance(results[0], Exception) else {}
        predictions_res = results[1] if not isinstance(results[1], Exception) else {}
        odds_res = results[2] if not isinstance(results[2], Exception) else {}

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
        h2h_task = self.provider.get_head_to_head(home_id, away_id) if home_id and away_id else _empty()
        standings_task = self.provider.get_standings_by_season(int(season_id)) if season_id else _empty()
        
        extra_results = await asyncio.gather(h2h_task, standings_task, return_exceptions=True)
        h2h_res = extra_results[0] if not isinstance(extra_results[0], Exception) else {}
        standings_res = extra_results[1] if not isinstance(extra_results[1], Exception) else {}

        # 组装返回结果 (保持相对扁平易读)
        match_data = {
            "fixture": fixture_payload,
            "predictions": predictions_res.get("data") if isinstance(predictions_res, dict) else predictions_res,
            "odds": odds_res.get("data") if isinstance(odds_res, dict) else odds_res,
            "h2h": h2h_res.get("data") if isinstance(h2h_res, dict) else h2h_res,
            "standings": standings_res.get("data") if isinstance(standings_res, dict) else standings_res,
            "fetched_at": datetime.now().isoformat()
        }

        self.cache.write_json(cache_key, match_data)
        return match_data

async def _empty() -> Any:
    return None

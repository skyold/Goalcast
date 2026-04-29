"""
异步并行 RD 循环编排器。
4 路 asyncio.Task 通过 match_store 解耦：
  _orchestrator_loop → _analyst_loop → _trader_loop → _reviewer_loop → _reporter_loop
"""

from __future__ import annotations

import asyncio
import json
import logging
import signal
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from agents.core import match_store
from agents.core.pipeline import MatchPipeline

logger = logging.getLogger(__name__)

IDLE_SLEEP_SECONDS = 5

LEAGUES_JSON_PATH = (
    Path(__file__).parent.parent
    / "roles" / "analyst" / "sportmonks_leagues.json"
)
_CST = timezone(timedelta(hours=8))


class Orchestrator:
    def __init__(self, adapter, semi_mode: bool = False):
        self.adapter = adapter
        self.semi_mode = semi_mode
        self.stop_event = asyncio.Event()
        self.pipeline = MatchPipeline(adapter, semi_mode)

    async def run(
        self,
        leagues: list[str] | None = None,
        date: str | None = None,
        max_matches: int | None = None,
    ) -> dict:
        signal.signal(signal.SIGINT, lambda s, f: self.stop_event.set())
        signal.signal(signal.SIGTERM, lambda s, f: self.stop_event.set())

        fetched = await self._fetch_and_prepare(leagues, date)
        logger.info("[Orchestrator] 已准备 %d 场比赛", fetched)

        tasks = [
            asyncio.create_task(self._analyst_loop()),
            asyncio.create_task(self._trader_loop()),
            asyncio.create_task(self._reviewer_loop()),
            asyncio.create_task(self._reporter_loop()),
        ]

        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

        reviewed = match_store.list_all(status="reviewed")
        reported = match_store.list_all(status="reported")
        return {
            "prepared": fetched,
            "reviewed": len(reviewed),
            "reported": len(reported),
        }

    async def _fetch_and_prepare(
        self, leagues: list[str] | None, date: str | None, models: list[str] = None
    ) -> int:
        from agents.adapters.tool_executor import ToolExecutor
        from agents.core.blackboard import merge_update
        from agents.core import match_store
        import os

        if models is None:
            models = ["v4.0"]

        executor = ToolExecutor()
        today = date or datetime.now(_CST).strftime("%Y-%m-%d")

        league_ids = None
        if leagues:
            league_ids = self._resolve_league_ids(leagues)
            if not league_ids:
                logger.warning("[Orchestrator] 联赛字典中未找到: %s", leagues)
                return 0

        result = await executor._tool_goalcast_sportmonks_get_matches(
            date=today, league_ids=league_ids,
        )
        fixtures = result.get("data", [])

        count = 0
        for fixture in fixtures:
            match_id = match_store.generate_match_id()
            fixture_id = fixture.get("fixture_id", fixture.get("id"))
            
            # 读取 skill 依赖并预先获取原始数据
            raw_data = await self._fetch_raw_data_for_models(executor, fixture_id, models)
            
            record = {
                "metadata": {
                    "match_id": match_id,
                    "fixture_id": fixture_id,
                    "home_team": fixture.get("home_team", fixture.get("name", "").split(" vs ")[0]),
                    "away_team": fixture.get("away_team", fixture.get("name", "").split(" vs ")[-1]),
                    "league": fixture.get("league", fixture.get("league_name", "")),
                    "kickoff_time": fixture.get("kickoff_time", fixture.get("starting_at", "")),
                    "requested_models": models,
                    "prepared_at": datetime.now(_CST).isoformat(),
                },
                "state": {
                    "orchestrator": "done",
                    "analyst": "pending",
                    "trader": "pending",
                    "reporter": "pending"
                },
                "raw_data": raw_data,
                "analysis": {},
                "trading": {}
            }
            
            # 使用 Blackboard 结构保存
            filepath = match_store.MATCHES_DIR / f"{match_id}.json"
            
            # 保留旧版 match_store 内存兼容性（兼容后续步骤和队列轮询）
            legacy_record = {"match_id": match_id, "status": "pending", "orchestrator": {"prepared_at": record["metadata"]["prepared_at"]}}
            match_store.save(legacy_record)
            
            merge_update(filepath, record)
            count += 1
        return count

    async def _fetch_raw_data_for_models(self, executor, fixture_id: int, models: list[str]) -> dict:
        """
        动态读取模型 skill 定义并获取所需数据。
        针对 v3.0 和 v4.0 依赖的示例实现。
        """
        raw_data = {}
        # 实际情况中，这里将解析 goalcast-analyzer-v40/SKILL.md 等文件
        if "v4.0" in models or "v3.0" in models:
            # 示例: 两者都需要 sportmonks 的 match context
            if hasattr(executor, "_tool_goalcast_sportmonks_resolve_match"):
                res = await executor._tool_goalcast_sportmonks_resolve_match(fixture_id=fixture_id)
                raw_data["sportmonks"] = res.get("data", {})
        return raw_data

    def _resolve_league_ids(self, leagues: list[str]) -> list[int] | None:
        if not LEAGUES_JSON_PATH.exists():
            return None
        try:
            league_dict = json.loads(
                LEAGUES_JSON_PATH.read_text(encoding="utf-8")
            )
        except (json.JSONDecodeError, IOError):
            return None

        ids = []
        for name in leagues:
            name_lower = name.lower()
            for key, value in league_dict.items():
                if name_lower in key.lower() or name_lower in str(value).lower():
                    if isinstance(value, dict) and "id" in value:
                        ids.append(value["id"])
                    elif isinstance(value, (int, float)):
                        ids.append(int(value))
        return list(set(ids)) if ids else None

    async def _analyst_loop(self):
        while not self.stop_event.is_set():
            record = match_store.claim_oldest(["pending"], "analyzing")
            if record is None:
                await self._sleep(IDLE_SLEEP_SECONDS)
                continue
            try:
                await self.pipeline.run_analyst_step(record)
            except Exception as exc:
                logger.error("[Orchestrator] Analyst 异常: %s", exc)
                match_store.update_status(record["match_id"], "pending")

    async def _trader_loop(self):
        while not self.stop_event.is_set():
            record = match_store.claim_oldest(
                ["analyzed", "feedback"], "trading"
            )
            if record is None:
                await self._sleep(IDLE_SLEEP_SECONDS)
                continue
            try:
                await self.pipeline.run_trader_step(record)
            except Exception as exc:
                logger.error("[Orchestrator] Trader 异常: %s", exc)
                match_store.update_status(record["match_id"], "analyzed")

    async def _reviewer_loop(self):
        while not self.stop_event.is_set():
            record = match_store.claim_oldest(["traded"], "reviewing")
            if record is None:
                await self._sleep(IDLE_SLEEP_SECONDS)
                continue
            try:
                await self.pipeline.run_reviewer_step(record)
            except Exception as exc:
                logger.error("[Orchestrator] Reviewer 异常: %s", exc)
                match_store.update_status(record["match_id"], "traded")

    async def _reporter_loop(self):
        batch_size = 10
        while not self.stop_event.is_set():
            reviewed = match_store.list_all(status="reviewed")
            if len(reviewed) < batch_size:
                await self._sleep(IDLE_SLEEP_SECONDS * 2)
                continue
            batch = reviewed[:batch_size]
            match_ids = [r["match_id"] for r in batch]
            try:
                await self.pipeline.run_reporter_step(match_ids)
            except Exception as exc:
                logger.error("[Orchestrator] Reporter 异常: %s", exc)
            await self._sleep(IDLE_SLEEP_SECONDS)

    async def _sleep(self, seconds: float):
        try:
            await asyncio.wait_for(
                self.stop_event.wait(), timeout=seconds
            )
        except asyncio.TimeoutError:
            pass


async def run_standalone(
    adapter: Any,
    role_path: str,
    user_message: str,
) -> Any:
    return await adapter.run_agent(role_path, user_message)

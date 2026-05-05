"""
异步并行 RD 循环编排器。
5 路 asyncio.Task 通过 match_store 解耦：
  _orchestrator_loop（定时拉取比赛）→ _analyst_loop → _trader_loop → _reviewer_loop → _reporter_loop
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
from agents.core import league_config as lc
from agents.core.pipeline import MatchPipeline
from agents.core.events import EventEmitter

logger = logging.getLogger(__name__)

IDLE_SLEEP_SECONDS = 5
FETCH_INTERVAL_SECONDS = 3600

TRIGGER_FILE = Path(__file__).parent.parent.parent / "data" / "trigger.json"
PIPELINE_EVENTS_FILE = Path(__file__).parent.parent.parent / "data" / "pipeline_events.jsonl"

LEAGUES_JSON_PATH = (
    Path(__file__).parent.parent.parent / "config" / "sportmonks_leagues.json"
)
LEAGUES_JSON_CANDIDATE_PATHS: list[Path] | None = None
LEAGUES_JSON_FALLBACK_PATH = (
    Path(__file__).parent.parent.parent / "skills" / "goalcast-analysis-orchestrator" / "sportmonks_leagues.json"
)
_CST = timezone(timedelta(hours=8))


class Orchestrator:
    def __init__(self, adapter, semi_mode: bool = False, emitter: EventEmitter | None = None):
        self.adapter = adapter
        self.semi_mode = semi_mode
        self.stop_event = asyncio.Event()
        self.pipeline = MatchPipeline(adapter, semi_mode)
        self.emitter = emitter or EventEmitter()
        self._events_seq = 0

    def _write_pipeline_event(self, event_name: str, payload: dict):
        PIPELINE_EVENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        self._events_seq += 1
        line = json.dumps({
            "seq": self._events_seq,
            "ts": datetime.now(_CST).isoformat(),
            "type": event_name,
            "payload": payload,
        }, ensure_ascii=False)
        try:
            with open(PIPELINE_EVENTS_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception as e:
            logger.warning("[Orchestrator] 写入流水线事件失败: %s", e)

    async def _emit_and_write(self, event_name: str, payload: dict):
        self._write_pipeline_event(event_name, payload)
        await self.emitter.emit(event_name, payload)

    async def run(
        self,
        leagues: list[str] | None = None,
        date: str | None = None,
        max_matches: int | None = None,
        models: list[str] | None = None,
        fetch_interval: int = 3600,
    ) -> dict:
        await self._emit_and_write("pipeline_start", {"message": "Starting pipeline..."})

        if leagues:
            lc.init(leagues)
        
        signal.signal(signal.SIGINT, lambda s, f: self.stop_event.set())
        signal.signal(signal.SIGTERM, lambda s, f: self.stop_event.set())

        match_store.abandon_active()

        loops = [
            asyncio.create_task(self._orchestrator_loop(leagues, date, models, fetch_interval)),
            asyncio.create_task(self._analyst_loop()),
            asyncio.create_task(self._trader_loop()),
            asyncio.create_task(self._reviewer_loop()),
            asyncio.create_task(self._reporter_loop()),
        ]
        print("[Orchestrator] 5 个 Agent loop 已启动（orchestrator + 4 个处理 loop）")

        try:
            await asyncio.gather(*loops)
        except asyncio.CancelledError:
            for t in loops:
                t.cancel()
            await asyncio.gather(*loops, return_exceptions=True)

        reviewed = match_store.list_all(status="reviewed")
        reported = match_store.list_all(status="reported")
        
        await self._emit_and_write("pipeline_complete", {"message": "所有比赛分析已完成。"})
        
        return {
            "prepared": 0,
            "reviewed": len(reviewed),
            "reported": len(reported),
        }

    async def _orchestrator_loop(
        self,
        leagues: list[str] | None,
        date: str | None,
        models: list[str] | None,
        fetch_interval: int,
    ) -> None:
        _TRIGGER_CHECK_SECONDS = 5

        async def _sleep_with_trigger_check(seconds: int) -> bool:
            elapsed = 0
            while elapsed < seconds:
                if self.stop_event.is_set():
                    return True
                if TRIGGER_FILE.exists():
                    return True
                chunk = min(_TRIGGER_CHECK_SECONDS, seconds - elapsed)
                try:
                    await asyncio.wait_for(self.stop_event.wait(), timeout=chunk)
                except asyncio.TimeoutError:
                    pass
                elapsed += chunk
            return False

        while not self.stop_event.is_set():
            active_leagues = lc.get_active()
            if not active_leagues:
                print("[Orchestrator] 当前无活跃联赛，跳过拉取（使用 leagues add <联赛名> 添加）")
                if await _sleep_with_trigger_check(fetch_interval):
                    if TRIGGER_FILE.exists():
                        TRIGGER_FILE.unlink()
                        print("[Orchestrator] Trigger 收到，但无活跃联赛，跳过")
                continue
            print(f"[Orchestrator] 正在拉取比赛数据... 当前联赛: {active_leagues}")
            fetched = await self._fetch_and_prepare(active_leagues, date, models=models)
            print(f"[Orchestrator] 已准备 {fetched} 场比赛")

            if TRIGGER_FILE.exists():
                TRIGGER_FILE.unlink()
                print("[Orchestrator] Trigger 完成，恢复正常等待间隔")

            if self.stop_event.is_set():
                break

            triggered = await _sleep_with_trigger_check(fetch_interval)
            if triggered and not self.stop_event.is_set():
                print("[Orchestrator] Trigger 信号接收，立即开始下一轮拉取")

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

        league_ids = None
        if leagues:
            league_ids = await self._resolve_league_ids(leagues)
            if not league_ids:
                print(f"[Orchestrator] 联赛字典中未找到: {leagues}")
                logger.warning("[Orchestrator] 联赛字典中未找到: %s", leagues)
                return 0
            print(f"[Orchestrator] 联赛映射: {leagues} → league_ids={league_ids}")

        dates = self._resolve_date_range(date)
        print(f"[Orchestrator] 日期范围: {dates}")
        fixtures = []
        seen_fixture_ids = set()
        for d in dates:
            print(f"[Orchestrator] 拉取 {d} 的比赛...")
            result = await executor._tool_goalcast_sportmonks_get_matches(
                date=d, league_ids=league_ids,
            )
            day_fixtures = result.get("data", []) if isinstance(result, dict) else []
            new_count = 0
            for f in day_fixtures:
                fid = f.get("fixture_id", f.get("id"))
                if fid not in seen_fixture_ids:
                    seen_fixture_ids.add(fid)
                    fixtures.append(f)
                    new_count += 1
            print(f"[Orchestrator] {d}: 获取 {len(day_fixtures)} 场, 新增 {new_count} 场")

        count = 0
        prepared_matches = []
        trigger_force = False
        if TRIGGER_FILE.exists():
            try:
                tdata = json.loads(TRIGGER_FILE.read_text(encoding="utf-8"))
                trigger_force = tdata.get("force", False)
            except Exception:
                pass

        existing_fixture_ids = self._load_existing_fixture_ids()
        active_fixture_ids = self._load_existing_fixture_ids(active_only=True)
        skipped = 0
        for fixture in fixtures:
            fixture_id = fixture.get("fixture_id", fixture.get("id"))
            # Always skip fixtures currently in-flight (non-terminal status)
            if fixture_id in active_fixture_ids:
                skipped += 1
                continue
            # Without force, also skip terminal fixtures to avoid reprocessing
            if not trigger_force and fixture_id in existing_fixture_ids:
                skipped += 1
                continue
            match_id = match_store.generate_match_id()
            
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
                    "reviewer": "pending",
                    "reporter": "pending"
                },
                "raw_data": raw_data,
                "analysis": {},
                "trading": {}
            }
            
            # 使用 Blackboard 结构保存
            filepath = match_store.MATCHES_DIR / f"{match_id}.json"
            
            # 保留旧版 match_store 内存兼容性（兼容后续步骤和队列轮询）
            legacy_record = {
                "match_id": match_id,
                "status": "pending",
                "orchestrator": {
                    "prepared_at": record["metadata"]["prepared_at"],
                    "fixture_id": fixture_id,
                    "home_team": record["metadata"]["home_team"],
                    "away_team": record["metadata"]["away_team"],
                    "league": record["metadata"]["league"],
                    "kickoff_time": record["metadata"]["kickoff_time"],
                },
            }
            match_store.save(legacy_record)
            
            merge_update(filepath, record)
            print(f"[Orchestrator] 已写入黑板: {match_id} ({record['metadata']['home_team']} vs {record['metadata']['away_team']})")
            prepared_matches.append(
                {
                    "match_id": match_id,
                    "home_team": record["metadata"]["home_team"],
                    "away_team": record["metadata"]["away_team"],
                    "kickoff_time": record["metadata"]["kickoff_time"],
                    "league": record["metadata"]["league"],
                }
            )
            count += 1
        if skipped > 0:
            print(f"[Orchestrator] 跳过 {skipped} 场已存在的比赛（盘上已有记录）")
        await self._emit_and_write(
            "matches_found",
            {"total": count, "matches": prepared_matches},
        )
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
            res = None
            get_match = getattr(executor, "_tool_goalcast_sportmonks_get_match", None)
            if callable(get_match):
                res = await get_match(fixture_id=fixture_id)
            if not isinstance(res, dict):
                resolve_match = getattr(executor, "_tool_goalcast_sportmonks_resolve_match", None)
                if callable(resolve_match):
                    res = await resolve_match(fixture_id=fixture_id)
            if isinstance(res, dict):
                raw_data["sportmonks"] = res.get("data", {})
        return raw_data

    def _has_active_work(self) -> bool:
        active_statuses = [
            "pending",
            "analyzing",
            "analyzed",
            "trading",
            "traded",
            "reviewing",
            "feedback",
        ]
        return any(match_store.count_by_status([status]) > 0 for status in active_statuses)

    _TERMINAL_STATUSES = {"reported", "abandoned"}

    def _load_existing_fixture_ids(self, active_only: bool = False) -> set:
        existing = set()
        for fp in match_store.MATCHES_DIR.glob("MC-*.json"):
            try:
                record = json.loads(fp.read_text(encoding="utf-8"))
                if active_only:
                    status = record.get("status", "")
                    if status in self._TERMINAL_STATUSES:
                        continue
                fid = (
                    record.get("orchestrator", {}).get("fixture_id")
                    or record.get("metadata", {}).get("fixture_id")
                )
                if fid:
                    existing.add(fid)
            except (json.JSONDecodeError, IOError):
                continue
        return existing

    def _resolve_date_range(self, date: str | None) -> list[str]:
        if date:
            return [date]
        tz = _CST
        now = datetime.now(tz)
        today = now.strftime("%Y-%m-%d")
        tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")
        day_after = (now + timedelta(days=2)).strftime("%Y-%m-%d")
        day3 = (now + timedelta(days=3)).strftime("%Y-%m-%d")
        day4 = (now + timedelta(days=4)).strftime("%Y-%m-%d")
        return [today, tomorrow, day_after, day3, day4]

    def _load_league_dict(self) -> dict | None:
        candidate_paths = LEAGUES_JSON_CANDIDATE_PATHS or [
            LEAGUES_JSON_PATH,
            LEAGUES_JSON_FALLBACK_PATH,
        ]
        for path in candidate_paths:
            if not path.exists():
                continue
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, IOError):
                continue
        return None

    def _simple_league_match(self, leagues: list[str | int], league_dict: dict) -> list[int] | None:
        ids = []
        for name in leagues:
            if isinstance(name, int):
                ids.append(name)
                continue
            if isinstance(name, str) and name.isdigit():
                ids.append(int(name))
                continue
            if not isinstance(name, str):
                continue
            name_lower = name.lower()
            for key, value in league_dict.items():
                if (name_lower in key.lower() or 
                    name_lower in str(value.get("name", "")).lower() or 
                    name_lower in str(value.get("chinese_name", "")).lower()):
                    if isinstance(value, dict) and "id" in value:
                        ids.append(value["id"])
                    elif isinstance(value, (int, float)):
                        ids.append(int(value))
        return list(set(ids)) if ids else None

    def _build_league_matching_prompt(self, leagues: list[str], league_dict: dict) -> str:
        league_candidates = []
        for key, info in league_dict.items():
            names = [info.get("name", "")]
            if info.get("chinese_name"):
                names.append(info["chinese_name"])
            league_candidates.append({
                "id": info.get("id", int(key)),
                "names": [n for n in names if n]
            })
        
        return f"""你是一个足球联赛名称智能匹配器。

任务：将用户输入的联赛名称映射到正确的联赛 ID。

规则：
1. 支持中文、英文、缩写、别名的智能匹配
2. 允许模糊匹配和同义词转换
3. 一个输入可能匹配多个联赛（如"英超"可能匹配多个国家的英超联赛）
4. 如果完全无法匹配，返回空数组 []

联赛候选列表（JSON格式）：
{json.dumps(league_candidates, ensure_ascii=False, indent=2)}

用户输入：{json.dumps(leagues)}

请直接返回匹配的联赛 ID 数组（纯JSON格式，不要有其他文字）："""

    async def _resolve_league_ids_with_llm(self, leagues: list[str | int]) -> list[int] | None:
        league_dict = self._load_league_dict()
        if league_dict is None:
            return None

        simple_result = self._simple_league_match(leagues, league_dict)
        if simple_result:
            logger.debug("[Orchestrator] 简单匹配成功: %s → %s", leagues, simple_result)
            return simple_result

        str_leagues = [str(l) for l in leagues if isinstance(l, str) and not str(l).isdigit()]
        if not str_leagues:
            return simple_result

        logger.debug("[Orchestrator] 简单匹配失败，尝试 LLM 匹配: %s", str_leagues)
        prompt = self._build_league_matching_prompt(str_leagues, league_dict)
        
        try:
            result = await self.adapter.run_agent(
                "agents/roles/analyst",
                prompt
            )
            llm_result = json.loads(result.final_text.strip())
            if isinstance(llm_result, list):
                valid_ids = [int(id_) for id_ in llm_result if isinstance(id_, (int, str)) and str(id_).isdigit()]
                if valid_ids:
                    logger.info("[Orchestrator] LLM 匹配成功: %s → %s", str_leagues, valid_ids)
                    return valid_ids
        except Exception as e:
            logger.warning("[Orchestrator] LLM 匹配失败: %s", e)

        return None

    async def _resolve_league_ids(self, leagues: list[str | int]) -> list[int] | None:
        return await self._resolve_league_ids_with_llm(leagues)

    async def _analyst_loop(self):
        while not self.stop_event.is_set():
            record = match_store.claim_oldest(["pending"], "analyzing")
            if record is None:
                await self._sleep(IDLE_SLEEP_SECONDS)
                continue
            print(f"[Analyst] 开始分析: {record['match_id']} ({record.get('orchestrator', {}).get('home_team', '?')} vs {record.get('orchestrator', {}).get('away_team', '?')})")
            await self._emit_and_write("match_step_start", {"match_id": record["match_id"], "step": "analyst"})
            try:
                await self.pipeline.run_analyst_step(record)
                print(f"[Analyst] 分析完成: {record['match_id']}")
            except Exception as exc:
                print(f"[Analyst] 分析异常: {record['match_id']}: {exc}")
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
            print(f"[Trader] 开始交易分析: {record['match_id']}")
            await self._emit_and_write("match_step_start", {"match_id": record["match_id"], "step": "trader"})
            try:
                trade = await self.pipeline.run_trader_step(record)
                print(f"[Trader] 交易分析完成: {record['match_id']}")
                await self._emit_and_write(
                    "match_result_ready",
                    {
                        "match_id": record["match_id"],
                        "predictions": trade.get("predictions", {}),
                        "ev": trade.get("ev"),
                        "recommendation": trade.get("recommendation")
                        or trade.get("ah_recommendation")
                        or trade.get("bet_direction")
                        or trade.get("direction"),
                    },
                )
            except Exception as exc:
                print(f"[Trader] 交易分析异常: {record['match_id']}: {exc}")
                logger.error("[Orchestrator] Trader 异常: %s", exc)
                match_store.update_status(record["match_id"], "analyzed")

    async def _reviewer_loop(self):
        while not self.stop_event.is_set():
            record = match_store.claim_oldest(["traded"], "reviewing")
            if record is None:
                await self._sleep(IDLE_SLEEP_SECONDS)
                continue
            print(f"[Reviewer] 开始审核: {record['match_id']}")
            try:
                await self.pipeline.run_reviewer_step(record)
                print(f"[Reviewer] 审核完成: {record['match_id']}")
            except Exception as exc:
                print(f"[Reviewer] 审核异常: {record['match_id']}: {exc}")
                logger.error("[Orchestrator] Reviewer 异常: %s", exc)
                match_store.update_status(record["match_id"], "traded")

    async def _reporter_loop(self):
        batch_size = 10
        while not self.stop_event.is_set():
            reviewed = match_store.list_all(status="reviewed")
            active_work = self._has_active_work()

            if len(reviewed) >= batch_size:
                batch = reviewed[:batch_size]
            elif reviewed and not active_work:
                batch = reviewed
            else:
                await self._sleep(IDLE_SLEEP_SECONDS * 2)
                continue

            match_ids = [r["match_id"] for r in batch]
            try:
                print(f"[Reporter] 开始生成报告: {len(match_ids)} 场比赛")
                await self.pipeline.run_reporter_step(match_ids)
                print(f"[Reporter] 报告生成完成")
            except Exception as exc:
                print(f"[Reporter] 报告异常: {exc}")
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

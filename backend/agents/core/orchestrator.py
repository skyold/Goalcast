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
    def __init__(self, adapter=None, semi_mode: bool = False, emitter: EventEmitter | None = None):
        self.adapter = adapter
        self.semi_mode = semi_mode
        self.stop_event = asyncio.Event()
        # Pipeline construction needs an adapter for legacy run() loops. The
        # adapter-less ctor path is only used by run_once() (RD smoke cycle).
        self.pipeline = MatchPipeline(adapter, semi_mode) if adapter is not None else None
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
        """Stub — single-source rewrite pending (Task 9)."""
        raise NotImplementedError("Provider removed — see 2026-05-14 pivot: orchestrator._fetch_and_prepare needs Task 9 rewrite")

    def _resolve_oa_league_ids_from_names(self, leagues: list[str]) -> list[int]:
        """2026-05-14 pivot stub: resolve league names to OddAlerts IDs.

        TODO Task 9: implement proper name→OA-ID resolution.
        """
        raise NotImplementedError("Provider removed — see 2026-05-14 pivot: _resolve_oa_league_ids_from_names needs Task 9 implementation")

    async def _fetch_raw_data_for_models(
        self,
        executor,
        provider_ids: dict[str, int],
        models: list[str],
    ) -> dict:
        """Single-source raw-data fetch (OddAlerts only).

        TODO Task 19: rework the orchestrator's broader fetch/prepare flow now
        that ``data_collector.collect_all`` takes only ``oa_fixture_id`` and
        returns a flat OddAlerts-tagged bundle (no more per-provider keys).
        """
        from agents.core.data_collector import collect_all

        oa_id = provider_ids.get("oddalerts")
        if oa_id is None:
            return {}
        bundle = await collect_all(oa_fixture_id=oa_id)
        # Preserve the legacy {provider_name: bundle} shape downstream
        # consumers still expect until Task 19 lands.
        return {"oddalerts": bundle} if bundle else {}

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

    def _find_match_id_for_fixture(self, fixture_id: int) -> str | None:
        """返回已存在的某个 fixture_id 对应的 match_id（取最新文件）。"""
        found = None
        for fp in sorted(match_store.MATCHES_DIR.glob("MC-*.json")):
            try:
                record = json.loads(fp.read_text(encoding="utf-8"))
                fid = (
                    record.get("orchestrator", {}).get("fixture_id")
                    or record.get("metadata", {}).get("fixture_id")
                )
                if fid == fixture_id:
                    found = record.get("match_id", fp.stem)
            except (json.JSONDecodeError, IOError):
                continue
        return found

    def _load_fixture_ids_by_status(self, statuses: set[str]) -> set:
        """返回状态在 statuses 中的所有 fixture_id。"""
        result = set()
        for fp in match_store.MATCHES_DIR.glob("MC-*.json"):
            try:
                record = json.loads(fp.read_text(encoding="utf-8"))
                if record.get("status", "") not in statuses:
                    continue
                fid = (
                    record.get("orchestrator", {}).get("fixture_id")
                    or record.get("metadata", {}).get("fixture_id")
                )
                if fid:
                    result.add(fid)
            except (json.JSONDecodeError, IOError):
                continue
        return result

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

    async def run_once(self, max_matches: int = 5) -> dict:
        """One-shot RD cycle: fetch dropping odds → collect_all per fixture → write match_store."""
        import secrets
        from agents.core.data_collector import collect_all
        from provider.base import get_provider

        run_id = secrets.token_hex(4)
        provider = get_provider()
        dropping = await provider.get_dropping_odds()
        fixtures = (dropping or {}).get("data") or []
        processed = 0
        for f in fixtures[:max_matches]:
            oa_id = f.get("id")
            if oa_id is None:
                continue
            bundle = await collect_all(oa_fixture_id=oa_id)
            if not bundle:
                continue
            record = {
                "match_id": match_store.generate_match_id(),
                "run_id": run_id,
                "status": "analyzed",
                "fixture": bundle.get("fixture"),
                "analysis": bundle.get("analysis"),
                "collected_at": bundle.get("collected_at"),
            }
            match_store.save(record)
            processed += 1
        return {"run_id": run_id, "status": "completed", "processed": processed}

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

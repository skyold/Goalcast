"""
Pipeline Scheduler。
支持：定时运行（从 providers.json 读取间隔）+ 手动触发。
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from provider import registry
from pipeline.runner import run_pipeline

logger = logging.getLogger(__name__)

_CST = timezone(timedelta(hours=8))


class PipelineScheduler:
    def __init__(self):
        self._stop = asyncio.Event()
        self._manual_trigger = asyncio.Event()
        self._running = False
        self._last_result: dict = {}

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def last_result(self) -> dict:
        return self._last_result

    async def trigger(self) -> None:
        """手动触发立即执行一次 pipeline。"""
        self._manual_trigger.set()

    def stop(self) -> None:
        self._stop.set()

    async def run_forever(
        self,
        leagues: list[str] | None = None,
        adapter: Any = None,
        model: str = "v4.0",
    ) -> None:
        """持续运行：执行一次 pipeline，等待间隔，再执行。"""
        logger.info("[Scheduler] 启动")
        while not self._stop.is_set():
            interval_hours = registry.get_schedule_hours()
            interval_seconds = interval_hours * 3600

            self._running = True
            try:
                logger.info("[Scheduler] 开始执行 pipeline")
                self._last_result = await run_pipeline(
                    leagues=leagues,
                    adapter=adapter,
                    model=model,
                )
                logger.info("[Scheduler] 执行完成: %s", self._last_result)
            except Exception as exc:
                logger.error("[Scheduler] Pipeline 执行异常: %s", exc)
            finally:
                self._running = False

            # 等待定时间隔或手动触发
            self._manual_trigger.clear()
            logger.info("[Scheduler] 等待 %d 秒（%d 小时）或手动触发", interval_seconds, interval_hours)
            try:
                await asyncio.wait_for(
                    self._manual_trigger.wait(),
                    timeout=interval_seconds,
                )
                logger.info("[Scheduler] 手动触发，立即执行")
            except asyncio.TimeoutError:
                pass

            if self._stop.is_set():
                break

        logger.info("[Scheduler] 已停止")


_scheduler = PipelineScheduler()


def get_scheduler() -> PipelineScheduler:
    return _scheduler

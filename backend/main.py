#!/usr/bin/env python3
"""
Goalcast 后端服务启动入口。

启动方式：
  python main.py          # 直接启动（含 Scheduler）
  uvicorn server.server:app --reload --port 8000  # 开发模式（无 Scheduler）

环境变量：
  GOALCAST_LEAGUES  逗号分隔的联赛名称，如 "英超,西甲"（为空则不过滤）
  UI_DEV_MODE       设为 1 时启用 CORS（开发用）
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv
load_dotenv(_ROOT / ".env")


def _setup_logging(verbose: bool = False) -> None:
    import time
    from logging.handlers import RotatingFileHandler

    logging.Formatter.converter = lambda *args: time.gmtime(time.time() + 8 * 3600)

    level = logging.DEBUG if verbose else logging.INFO
    formatter = logging.Formatter(
        fmt="%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    log_dir = _ROOT / "data" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "goalcast.log"

    from logging.handlers import RotatingFileHandler
    file_handler = RotatingFileHandler(
        filename=log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    logging.basicConfig(level=level, handlers=[console_handler, file_handler])
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


logger = logging.getLogger(__name__)


async def _start_scheduler():
    from agents.adapters.adapter import ClaudeAdapter
    from pipeline.scheduler import get_scheduler

    adapter = ClaudeAdapter()
    scheduler = get_scheduler()

    leagues_env = os.environ.get("GOALCAST_LEAGUES", "")
    leagues = [lg.strip() for lg in leagues_env.split(",") if lg.strip()] or None

    logger.info("[Main] 启动 Pipeline Scheduler，联赛过滤: %s", leagues or "全部")
    await scheduler.run_forever(leagues=leagues, adapter=adapter)


def main():
    import uvicorn
    from server.server import app

    _setup_logging(verbose=os.environ.get("DEBUG", "").lower() in ("1", "true"))

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    scheduler_task = loop.create_task(_start_scheduler())

    config = uvicorn.Config(app, host="0.0.0.0", port=8000, loop="none")
    server = uvicorn.Server(config)

    try:
        loop.run_until_complete(server.serve())
    finally:
        scheduler_task.cancel()
        loop.run_until_complete(asyncio.gather(scheduler_task, return_exceptions=True))
        loop.close()


if __name__ == "__main__":
    main()

from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
import logging

logger = logging.getLogger(__name__)

async def scheduled_task():
    """
    定时任务：每天早上 10:00 自动启动 Orchestrator 拉取当天+明天的赛程。
    Orchestrator 会在数据准备完成后自动启动 4 条异步轮询循环，
    各 Agent（Analyst/Trader/Reviewer/Reporter）将按状态驱动独立工作。
    """
    logger.info("[Scheduler] 定时任务触发，启动 Orchestrator 流水线...")
    from agents.core.orchestrator import Orchestrator
    from agents.adapters.adapter import AgentAdapter

    adapter = AgentAdapter()
    orch = Orchestrator(adapter, semi_mode=False)

    result = await orch.run(
        leagues=["Premier League", "Serie A", "La Liga", "Bundesliga", "Ligue 1"],
    )
    logger.info("[Scheduler] 流水线完成: %s", result)

def start_scheduler():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(scheduled_task, 'cron', hour=10, minute=0)
    scheduler.start()
    logger.info("[Scheduler] 定时器已启动，每天 10:00 触发")
    return scheduler

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    scheduler = start_scheduler()
    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass

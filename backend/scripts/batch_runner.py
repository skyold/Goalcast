#!/usr/bin/env python3
"""
batch_runner.py — Goalcast 数据预热批处理脚本

无 LLM 参与，仅拉取并缓存比赛数据。
适用于定时任务（cron）和大批量预热场景。

用法：
  python scripts/batch_runner.py --provider sportmonks
  python scripts/batch_runner.py --provider footystats --date 2026-04-12
  python scripts/batch_runner.py --provider sportmonks --league "Premier League"
"""
import sys
import asyncio
import argparse
import datetime
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "mcp_server"))

from utils.logger import logger
from config.settings import settings


async def _load_watchlist(provider: str, league_filter: str | None) -> list[str]:
    """Load league list from config/watchlist.yaml."""
    try:
        import yaml
        wl_path = Path(__file__).resolve().parent.parent / "config" / "watchlist.yaml"
        if not wl_path.exists():
            logger.warning("config/watchlist.yaml not found — fetching all leagues")
            return [None]
        with open(wl_path) as f:
            wl = yaml.safe_load(f)
        leagues = [lg["name"] for lg in wl.get(provider, {}).get("leagues", [])]
        if league_filter:
            leagues = [lg for lg in leagues if league_filter.lower() in lg.lower()]
        return leagues or [None]
    except Exception as exc:
        logger.error(f"Failed to load watchlist: {exc}")
        return [None]


async def run_prefetch(date: str, league_filter: str | None) -> dict:
    """Stub — single-source rewrite pending (Task 9)."""
    # 2026-05-14 pivot: footystats/understat/datafusion providers removed.
    raise NotImplementedError("Provider removed — see 2026-05-14 pivot")


def main():
    parser = argparse.ArgumentParser(description="Goalcast batch data prefetcher")
    parser.add_argument("--date", default=datetime.date.today().isoformat(), help="YYYY-MM-DD")
    parser.add_argument("--league", default=None, help="League name filter")
    args = parser.parse_args()

    result = asyncio.run(run_prefetch(args.date, args.league))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

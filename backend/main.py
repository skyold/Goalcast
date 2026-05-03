#!/usr/bin/env python3
"""
Goalcast CLI —— 足球量化分析系统。

Subcommands:
  run      一键启动 RD 循环（Orchestrator → Analyst → Trader → Reviewer → Reporter）
  analyze  单独跑 Analyst
  trade    单独跑 Trader
  review   单独跑 Reviewer
  report   单独跑 Reporter
  backtest 单独跑 Backtester
  status   查看系统状态
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

from dotenv import load_dotenv

load_dotenv()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="goalcast",
        description="Goalcast 足球量化分析系统",
    )
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="一键启动 RD 循环")
    run_parser.add_argument(
        "--leagues", nargs="+", default=["英超"], help="目标联赛"
    )
    run_parser.add_argument("--date", help="日期 (YYYY-MM-DD)，默认今天")
    run_parser.add_argument(
        "--mode", choices=["full", "semi"], default="full"
    )
    run_parser.add_argument("--model", default=None, help="Claude 模型名")

    analyze_parser = subparsers.add_parser("analyze", help="单独跑 Analyst")
    analyze_parser.add_argument(
        "--match-file", required=True, help="比赛 JSON 文件路径"
    )
    analyze_parser.add_argument("--model", default=None)

    trade_parser = subparsers.add_parser("trade", help="单独跑 Trader")
    trade_parser.add_argument("--match-file", required=True)
    trade_parser.add_argument("--model", default=None)

    review_parser = subparsers.add_parser("review", help="单独跑 Reviewer")
    review_parser.add_argument("--match-file", required=True)
    review_parser.add_argument("--model", default=None)

    report_parser = subparsers.add_parser("report", help="单独跑 Reporter")
    report_parser.add_argument(
        "--match-files", nargs="+", required=True
    )
    report_parser.add_argument("--model", default=None)

    backtest_parser = subparsers.add_parser(
        "backtest", help="单独跑 Backtester"
    )
    backtest_parser.add_argument("--start-date", default=None)
    backtest_parser.add_argument("--end-date", default=None)
    backtest_parser.add_argument("--method", default=None)

    subparsers.add_parser("status", help="查看系统状态")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    asyncio.run(_dispatch(args))


async def _dispatch(args: argparse.Namespace) -> None:
    from agents.adapters import ClaudeAdapter, ToolExecutor
    from agents.core.directory_agent import DirectoryAgentLoader

    loader = DirectoryAgentLoader()
    executor = ToolExecutor()

    model = getattr(args, "model", None) or os.environ.get(
        "GOALCAST_MODEL", "claude-sonnet-4-20250514"
    )

    if args.command == "run":
        from agents.core.orchestrator import Orchestrator

        adapter = ClaudeAdapter(
            model=model, executor=executor, loader=loader
        )
        orch = Orchestrator(adapter, semi_mode=(args.mode == "semi"))
        result = await orch.run(leagues=args.leagues, date=args.date)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == "analyze":
        adapter = ClaudeAdapter(
            model=model, executor=executor, loader=loader
        )
        from agents.core import match_store
        record = match_store.load_from_file(args.match_file)
        if record is None:
            record = json.loads(
                open(args.match_file, encoding="utf-8").read()
            )
        from agents.core.pipeline import MatchPipeline
        pipeline = MatchPipeline(adapter)
        result = await pipeline.run_analyst_step(record)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == "trade":
        adapter = ClaudeAdapter(
            model=model, executor=executor, loader=loader
        )
        from agents.core import match_store
        record = match_store.load_from_file(args.match_file)
        if record is None:
            record = json.loads(
                open(args.match_file, encoding="utf-8").read()
            )
        from agents.core.pipeline import MatchPipeline
        pipeline = MatchPipeline(adapter)
        result = await pipeline.run_trader_step(record)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == "review":
        adapter = ClaudeAdapter(
            model=model, executor=executor, loader=loader
        )
        from agents.core import match_store
        record = match_store.load_from_file(args.match_file)
        if record is None:
            record = json.loads(
                open(args.match_file, encoding="utf-8").read()
            )
        from agents.core.pipeline import MatchPipeline
        pipeline = MatchPipeline(adapter)
        result = await pipeline.run_reviewer_step(record)
        print(f"Verdict: {result}")

    elif args.command == "report":
        adapter = ClaudeAdapter(
            model=model, executor=executor, loader=loader
        )
        from agents.core.pipeline import MatchPipeline
        pipeline = MatchPipeline(adapter)
        result = await pipeline.run_reporter_step(args.match_files)
        print(f"Report saved: {result}")

    elif args.command == "backtest":
        result = await executor._tool_goalcast_run_backtest(
            start_date=args.start_date,
            end_date=args.end_date,
            method=args.method,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == "status":
        from agents.core import match_store
        statuses = [
            "pending", "analyzed", "traded", "reviewed",
            "reported", "feedback", "rejected",
        ]
        print("=== Goalcast 系统状态 ===")
        for s in statuses:
            count = match_store.count_by_status([s])
            if count > 0:
                print(f"  {s}: {count}")
        all_records = match_store.list_all()
        if not all_records:
            print("  (无比赛记录)")
        print(f"  总计: {len(all_records)} 场比赛")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Goalcast CLI —— 足球量化分析系统。

运行模式：

  run      一键启动 RD 循环（Orchestrator → Analyst → Trader → Reviewer → Reporter）
          --infinite 无限循环模式，每轮分析完成后冷却指定时间再开始下一轮
  analyze  单独跑 Analyst
  trade    单独跑 Trader
  review   单独跑 Reviewer
  report   单独跑 Reporter
  backtest 单独跑 Backtester
  status   查看系统状态
  check    检查环境配置
  list-agents 列出所有 Agent 角色

LLM 提供商选择（全局参数，所有子命令均支持）：

  # 使用 Anthropic 代理端点
    python main.py --provider anthropic \\
        --base-url https://token-plan-cn.xiaomimimo.com/anthropic \\
        --api-key tp-xxx run

  # 使用 OpenAI 兼容端点
    python main.py --provider openai \\
        --base-url https://token-plan-cn.xiaomimimo.com/v1 \\
        --api-key tp-xxx run

  # 也可通过环境变量配置（推荐生产环境）：
    export LLM_PROVIDER=openai
    export LLM_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
    export LLM_API_KEY=tp-xxx
    python main.py run

工具命令：
    python main.py list-agents   # 查看所有 Agent 角色
    python main.py check         # 检查环境配置

Docker 部署推荐命令：
    python main.py run --mode full
  容器启动后持续分析比赛，docker stop 时等当前任务完成后优雅退出。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import signal
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

    for key in ("NO_PROXY", "no_proxy"):
        val = os.environ.get(key, "")
        if "xiaomimimo.com" not in val:
            os.environ[key] = f"{val},xiaomimimo.com" if val else "xiaomimimo.com"

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

    file_handler = RotatingFileHandler(
        filename=log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    logging.basicConfig(
        level=level,
        handlers=[console_handler, file_handler]
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)


def _make_stop_handler(stop_event: asyncio.Event, target: str):
    def _request_stop(sig: signal.Signals) -> None:
        if stop_event.is_set():
            return
        logging.getLogger(__name__).warning(f"[Shutdown] 收到 {sig.name} 信号，等待当前任务完成后退出")
        print(f"\n\n  ⚠️  收到停止信号，正在等待当前任务完成后退出...\n")
        stop_event.set()
    return _request_stop


def _add_llm_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--provider", default=None, choices=["anthropic", "openai"],
        help="LLM 提供商（默认读 LLM_PROVIDER 环境变量）",
    )
    parser.add_argument(
        "--base-url", default=None, dest="base_url", metavar="URL",
        help="自定义 API 端点，如 https://token-plan-cn.xiaomimimo.com/v1",
    )
    parser.add_argument(
        "--api-key", default=None, dest="api_key", metavar="KEY",
        help="API Key（覆盖 LLM_API_KEY 环境变量）",
    )


async def _create_adapter(
    model: str | None,
    provider: str | None,
    base_url: str | None,
    api_key: str | None,
):
    from agents.adapters import ClaudeAdapter, ToolExecutor
    from agents.core.directory_agent import DirectoryAgentLoader

    loader = DirectoryAgentLoader()
    executor = ToolExecutor()

    return ClaudeAdapter(
        model=model or os.environ.get("LLM_MODEL", "mimo-v2.5-pro"),
        executor=executor,
        loader=loader,
        base_url=base_url,
        api_key=api_key,
    )


async def cmd_run(
    leagues: list[str],
    date: str | None,
    mode: str,
    infinite: bool,
    cooldown: float,
    fetch_interval: int,
    model: str | None,
    provider: str | None,
    base_url: str | None,
    api_key: str | None,
) -> None:
    from agents.core.orchestrator import Orchestrator

    adapter = await _create_adapter(model, provider, base_url, api_key)

    print(f"\n{'═'*60}")
    print(f"  Goalcast 足球量化分析系统")
    print(f"  联赛           : {', '.join(leagues)}")
    print(f"  模式           : {mode.upper()}")
    print(f"  数据拉取间隔   : {fetch_interval}s（自动更新赛程）")
    if infinite:
        print(f"  运行方式       : ∞（无限循环，docker stop 可优雅退出）")
    else:
        print(f"  运行方式       : 单次运行")
    print(f"  提供商         : {adapter.__class__.__name__.replace('Adapter','')}  |  模型：{adapter.model}")
    print(f"{'═'*60}\n")

    stop_event = asyncio.Event()
    loop = asyncio.get_event_loop()
    stop_handler = _make_stop_handler(stop_event, "run")

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, lambda sig=sig: stop_handler(sig))
        except NotImplementedError:
            pass

    try:
        orch = Orchestrator(adapter, semi_mode=(mode == "semi"))
        result = await orch.run(
            leagues=leagues,
            date=date,
            fetch_interval=fetch_interval,
        )

        reviewed = result.get("reviewed", 0)
        print(f"\n{'─'*60}")
        print(f"  运行结束")
        print(f"  已审核比赛   : {reviewed} 场")
        print(f"{'─'*60}\n")
    finally:
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.remove_signal_handler(sig)
            except NotImplementedError:
                pass


async def cmd_analyze(
    match_file: str,
    model: str | None,
    provider: str | None,
    base_url: str | None,
    api_key: str | None,
) -> None:
    from agents.core import match_store
    from agents.core.pipeline import MatchPipeline

    adapter = await _create_adapter(model, provider, base_url, api_key)
    record = match_store.load_from_file(match_file)
    if record is None:
        record = json.loads(open(match_file, encoding="utf-8").read())

    print(f"\n{'═'*60}")
    print(f"  Goalcast Analyst")
    print(f"  比赛文件   : {match_file}")
    print(f"  提供商     : {adapter.__class__.__name__.replace('Adapter','')}  |  模型：{adapter.model}")
    print(f"{'═'*60}\n")

    pipeline = MatchPipeline(adapter)
    result = await pipeline.run_analyst_step(record)
    print(json.dumps(result, ensure_ascii=False, indent=2))


async def cmd_trade(
    match_file: str,
    model: str | None,
    provider: str | None,
    base_url: str | None,
    api_key: str | None,
) -> None:
    from agents.core import match_store
    from agents.core.pipeline import MatchPipeline

    adapter = await _create_adapter(model, provider, base_url, api_key)
    record = match_store.load_from_file(match_file)
    if record is None:
        record = json.loads(open(match_file, encoding="utf-8").read())

    print(f"\n{'═'*60}")
    print(f"  Goalcast Trader")
    print(f"  比赛文件   : {match_file}")
    print(f"  提供商     : {adapter.__class__.__name__.replace('Adapter','')}  |  模型：{adapter.model}")
    print(f"{'═'*60}\n")

    pipeline = MatchPipeline(adapter)
    result = await pipeline.run_trader_step(record)
    print(json.dumps(result, ensure_ascii=False, indent=2))


async def cmd_review(
    match_file: str,
    model: str | None,
    provider: str | None,
    base_url: str | None,
    api_key: str | None,
) -> None:
    from agents.core import match_store
    from agents.core.pipeline import MatchPipeline

    adapter = await _create_adapter(model, provider, base_url, api_key)
    record = match_store.load_from_file(match_file)
    if record is None:
        record = json.loads(open(match_file, encoding="utf-8").read())

    print(f"\n{'═'*60}")
    print(f"  Goalcast Reviewer")
    print(f"  比赛文件   : {match_file}")
    print(f"  提供商     : {adapter.__class__.__name__.replace('Adapter','')}  |  模型：{adapter.model}")
    print(f"{'═'*60}\n")

    pipeline = MatchPipeline(adapter)
    result = await pipeline.run_reviewer_step(record)
    print(f"Verdict: {result}")


async def cmd_report(
    match_files: list[str],
    model: str | None,
    provider: str | None,
    base_url: str | None,
    api_key: str | None,
) -> None:
    from agents.core.pipeline import MatchPipeline

    adapter = await _create_adapter(model, provider, base_url, api_key)

    print(f"\n{'═'*60}")
    print(f"  Goalcast Reporter")
    print(f"  比赛文件   : {len(match_files)} 个")
    print(f"  提供商     : {adapter.__class__.__name__.replace('Adapter','')}  |  模型：{adapter.model}")
    print(f"{'═'*60}\n")

    pipeline = MatchPipeline(adapter)
    result = await pipeline.run_reporter_step(match_files)
    print(f"Report saved: {result}")


async def cmd_backtest(
    start_date: str | None,
    end_date: str | None,
    method: str | None,
) -> None:
    from agents.adapters import ToolExecutor

    executor = ToolExecutor()
    result = await executor._tool_goalcast_run_backtest(
        start_date=start_date,
        end_date=end_date,
        method=method,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_status() -> None:
    from agents.core import match_store

    statuses = ["pending", "analyzed", "traded", "reviewed", "reported", "feedback", "rejected"]
    print("\n─── Goalcast 系统状态 ───\n")
    for s in statuses:
        count = match_store.count_by_status([s])
        if count > 0:
            print(f"  {s}: {count}")
    all_records = match_store.list_all()
    if not all_records:
        print("  （无比赛记录）")
    print(f"  总计: {len(all_records)} 场比赛\n")


def cmd_list_agents() -> None:
    from agents.core.directory_agent import DirectoryAgentLoader

    loader = DirectoryAgentLoader()
    roles = loader.list_roles()
    print(f"\n已发现 {len(roles)} 个 Agent 角色：\n")
    for role_path in roles:
        try:
            agent_def = loader.load_agent(role_path)
            tools_str = ", ".join(agent_def.allowed_mcp_tools) or "（无 MCP 工具）"
            print(f"  {role_path:<35}  MCP: {tools_str}")
        except Exception as e:
            print(f"  {role_path:<35}  ⚠️  加载失败: {e}")
    print()


def cmd_check(
    provider: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
) -> None:
    print("\n── 环境检查 ──\n")

    try:
        from config.settings import Settings
        override_kwargs: dict = {}
        if provider:
            override_kwargs["LLM_PROVIDER"] = provider
        if base_url:
            override_kwargs["LLM_BASE_URL"] = base_url
        if api_key:
            override_kwargs["LLM_API_KEY"] = api_key

        if override_kwargs:
            cfg = Settings(**{k: v for k, v in override_kwargs.items()})
        else:
            cfg = Settings()

        print(f"  ✅ LLM_PROVIDER       {cfg.llm_provider}")
        key = cfg.resolved_api_key
        if key:
            print(f"  ✅ API Key            已设置（{key[:8]}...）")
        else:
            print(f"  ❌ API Key            未设置")
        print(f"  ✅ 默认模型           {cfg.resolved_model}")
        endpoint = cfg.llm_base_url or "官方端点"
        print(f"  ✅ API 端点           {endpoint}")
    except Exception as exc:
        print(f"  ⚠️  Settings 加载失败：{exc}")

    try:
        import anthropic
        print(f"  ✅ anthropic SDK      已安装（{anthropic.__version__}）")
    except ImportError:
        print(f"  ⚠️  anthropic SDK      未安装")

    try:
        import openai
        print(f"  ✅ openai SDK         已安装（{openai.__version__}）")
    except ImportError:
        print(f"  ⚠️  openai SDK         未安装")

    from agents.core.directory_agent import DirectoryAgentLoader
    loader = DirectoryAgentLoader()
    roles = loader.list_roles()
    print(f"  ✅ agents/roles/      发现 {len(roles)} 个角色")

    skills_dir = _ROOT / "skills"
    if skills_dir.exists():
        skill_count = len(list(skills_dir.rglob("SKILL.md")))
        print(f"  ✅ skills/            发现 {skill_count} 个 SKILL.md")
    else:
        print(f"  ⚠️  skills/            目录不存在")

    data_dir = _ROOT / "data"
    if data_dir.exists():
        print(f"  ✅ data/              目录存在")
        matches_dir = data_dir / "matches"
        if matches_dir.exists():
            match_count = len(list(matches_dir.glob("*.json")))
            print(f"  ✅ data/matches/     {match_count} 个比赛文件")
    else:
        print(f"  ⚠️  data/              目录不存在")

    print()


def cmd_leagues(args: argparse.Namespace) -> None:
    from agents.core.league_config import list_leagues, add, remove

    action = args.league_action

    if action == "list" or action is None:
        current = list_leagues()
        if not current:
            print("当前无活跃联赛。可使用以下命令添加：")
            print("  python main.py leagues add <联赛名>")
            return
        print(f"\n当前活跃联赛（{len(current)} 个）:")
        for i, league in enumerate(current, 1):
            print(f"  {i}. {league}")
        print()
        return

    if action == "add":
        ok = add(args.name)
        if ok:
            print(f"✅ 已添加联赛: {args.name}")
        else:
            print(f"ℹ️  联赛已存在: {args.name}")
        print(f"当前活跃联赛: {list_leagues()}")
        return

    if action == "remove":
        ok = remove(args.name)
        if ok:
            print(f"✅ 已移除联赛: {args.name}")
        else:
            print(f"ℹ️  联赛不存在: {args.name}")
        print(f"当前活跃联赛: {list_leagues()}")
        return


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="goalcast",
        description="Goalcast 足球量化分析系统 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="显示 DEBUG 日志")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="一键启动 RD 循环")
    run_parser.add_argument(
        "--leagues", nargs="+", default=["英超"], help="目标联赛"
    )
    run_parser.add_argument("--date", help="日期 (YYYY-MM-DD)，默认今天")
    run_parser.add_argument(
        "--mode", choices=["full", "semi"], default="full"
    )
    run_parser.add_argument(
        "--infinite", action="store_true", default=True,
        help="无限循环分析（默认开启，docker stop 可优雅退出）"
    )
    run_parser.add_argument(
        "--fetch-interval", type=int, default=3600,
        help="定时拉取比赛间隔秒数（默认 3600，即 1 小时）"
    )
    run_parser.add_argument("--model", default=None, help="Claude 模型名")
    _add_llm_args(run_parser)

    analyze_parser = subparsers.add_parser("analyze", help="单独跑 Analyst")
    analyze_parser.add_argument(
        "--match-file", required=True, help="比赛 JSON 文件路径"
    )
    analyze_parser.add_argument("--model", default=None)
    _add_llm_args(analyze_parser)

    trade_parser = subparsers.add_parser("trade", help="单独跑 Trader")
    trade_parser.add_argument("--match-file", required=True)
    trade_parser.add_argument("--model", default=None)
    _add_llm_args(trade_parser)

    review_parser = subparsers.add_parser("review", help="单独跑 Reviewer")
    review_parser.add_argument("--match-file", required=True)
    review_parser.add_argument("--model", default=None)
    _add_llm_args(review_parser)

    report_parser = subparsers.add_parser("report", help="单独跑 Reporter")
    report_parser.add_argument(
        "--match-files", nargs="+", required=True
    )
    report_parser.add_argument("--model", default=None)
    _add_llm_args(report_parser)

    backtest_parser = subparsers.add_parser("backtest", help="单独跑 Backtester")
    backtest_parser.add_argument("--start-date", default=None)
    backtest_parser.add_argument("--end-date", default=None)
    backtest_parser.add_argument("--method", default=None)

    leagues_parser = subparsers.add_parser("leagues", help="运行时动态管理联赛")
    leagues_sub = leagues_parser.add_subparsers(dest="league_action")
    leagues_sub.add_parser("list", help="列出当前活跃联赛")
    leagues_add = leagues_sub.add_parser("add", help="添加联赛到运行时")
    leagues_add.add_argument("name", help="联赛名称（如 西甲、意甲）")
    leagues_rm = leagues_sub.add_parser("remove", help="从运行时移除联赛")
    leagues_rm.add_argument("name", help="联赛名称（如 英超）")

    subparsers.add_parser("status", help="查看系统状态")
    subparsers.add_parser("list-agents", help="列出所有 Agent 角色")
    p_check = subparsers.add_parser("check", help="检查环境配置")
    _add_llm_args(p_check)

    args = parser.parse_args()
    _setup_logging(args.verbose)

    if args.command == "run":
        asyncio.run(cmd_run(
            leagues=args.leagues,
            date=args.date,
            mode=args.mode,
            infinite=args.infinite,
            cooldown=0,
            fetch_interval=args.fetch_interval,
            model=args.model,
            provider=args.provider,
            base_url=args.base_url,
            api_key=args.api_key,
        ))
    elif args.command == "analyze":
        asyncio.run(cmd_analyze(
            match_file=args.match_file,
            model=args.model,
            provider=args.provider,
            base_url=args.base_url,
            api_key=args.api_key,
        ))
    elif args.command == "trade":
        asyncio.run(cmd_trade(
            match_file=args.match_file,
            model=args.model,
            provider=args.provider,
            base_url=args.base_url,
            api_key=args.api_key,
        ))
    elif args.command == "review":
        asyncio.run(cmd_review(
            match_file=args.match_file,
            model=args.model,
            provider=args.provider,
            base_url=args.base_url,
            api_key=args.api_key,
        ))
    elif args.command == "report":
        asyncio.run(cmd_report(
            match_files=args.match_files,
            model=args.model,
            provider=args.provider,
            base_url=args.base_url,
            api_key=args.api_key,
        ))
    elif args.command == "backtest":
        asyncio.run(cmd_backtest(
            start_date=args.start_date,
            end_date=args.end_date,
            method=args.method,
        ))
    elif args.command == "status":
        cmd_status()
    elif args.command == "list-agents":
        cmd_list_agents()
    elif args.command == "check":
        cmd_check(
            provider=getattr(args, "provider", None),
            base_url=getattr(args, "base_url", None),
            api_key=getattr(args, "api_key", None),
        )
    elif args.command == "leagues":
        cmd_leagues(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

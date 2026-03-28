#!/usr/bin/env python3
"""
get_schedule - FootyStats 比赛日程查询工具

查询足球比赛日程表，支持多种查询模式和输出格式。

使用示例:
    # 查询最近比赛日
    python -m cmd.get_schedule --nearest
    
    # 查询未来 7 天比赛
    python -m cmd.get_schedule --next-days 7
    
    # 查询日期范围
    python -m cmd.get_schedule --date-range 2026-03-28 2026-04-05
    
    # 查询球队比赛
    python -m cmd.get_schedule --team "Manchester United" --next-days 7
    
    # JSON 格式输出
    python -m cmd.get_schedule --next-days 7 --json
    
    # 简洁格式输出
    python -m cmd.get_schedule --next-days 7 --compact
"""

import asyncio
import argparse
import sys
import json
from pathlib import Path
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional

# 设置项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.datasource.match import MatchDataSource
from src.datasource.types import Match, MatchStatus


class ScheduleError(Exception):
    """日程查询错误"""
    
    def __init__(self, message: str, error_code: int = 0, suggestion: str = ""):
        self.message = message
        self.error_code = error_code
        self.suggestion = suggestion
        super().__init__(self.message)


def create_parser() -> argparse.ArgumentParser:
    """
    创建命令行参数解析器
    
    Returns:
        配置好的 ArgumentParser 对象
    """
    parser = argparse.ArgumentParser(
        description="FootyStats 比赛日程查询工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  %(prog)s --nearest                      查询最近比赛日
  %(prog)s --next-days 7                  查询未来 7 天比赛
  %(prog)s --date-range 2026-03-28 2026-04-05
                                          查询指定日期范围
  %(prog)s --team "Manchester United" --nearest
                                          查询球队最近比赛
  %(prog)s --next-days 7 --json           JSON 格式输出
  %(prog)s --next-days 7 --compact        简洁格式输出
        """
    )
    
    # 查询模式（互斥组）
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--nearest",
        action="store_true",
        help="获取最近有比赛的一天的所有比赛"
    )
    mode_group.add_argument(
        "--next-days",
        type=int,
        metavar="N",
        help="获取未来 N 天内的所有比赛（N: 1-365）"
    )
    mode_group.add_argument(
        "--date-range",
        nargs=2,
        metavar=("YYYY-MM-DD", "YYYY-MM-DD"),
        help="获取指定日期范围内的所有比赛"
    )
    
    # 球队过滤
    parser.add_argument(
        "--team",
        type=str,
        metavar="TEAM_NAME",
        help="球队名称（支持模糊匹配，不区分大小写）"
    )
    
    # 输出格式
    format_group = parser.add_mutually_exclusive_group()
    format_group.add_argument(
        "--json",
        action="store_true",
        help="输出 JSON 格式"
    )
    format_group.add_argument(
        "--compact",
        action="store_true",
        help="输出简洁格式（每行一场比赛）"
    )
    
    # 其他选项
    parser.add_argument(
        "--debug",
        action="store_true",
        help="打印调试信息"
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="不使用缓存（强制刷新）"
    )
    
    return parser


def validate_date(date_str: str) -> date:
    """
    验证并解析日期字符串
    
    Args:
        date_str: 日期字符串（格式：YYYY-MM-DD）
        
    Returns:
        date 对象
        
    Raises:
        ScheduleError: 日期格式无效
    """
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise ScheduleError(
            f"日期格式无效：{date_str}",
            error_code=2001,
            suggestion="请使用 YYYY-MM-DD 格式，例如：2026-03-28"
        )


def validate_next_days(days: int) -> int:
    """
    验证未来天数参数
    
    Args:
        days: 天数
        
    Returns:
        有效的天数
        
    Raises:
        ScheduleError: 天数超出范围
    """
    if days < 1:
        raise ScheduleError(
            f"天数必须大于 0: {days}",
            error_code=2002,
            suggestion="请输入 1-365 之间的数字"
        )
    if days > 365:
        raise ScheduleError(
            f"天数超出范围：{days}",
            error_code=2003,
            suggestion="最多支持查询 365 天的比赛"
        )
    return days


async def query_nearest(
    match_ds: MatchDataSource,
    team_name: Optional[str] = None,
    debug: bool = False
) -> List[Match]:
    """
    查询最近比赛日
    
    Args:
        match_ds: MatchDataSource 实例
        team_name: 球队名称（可选）
        debug: 是否启用调试模式
        
    Returns:
        比赛列表
    """
    if debug:
        print("[DEBUG] Query mode: nearest match day")
        if team_name:
            print(f"[DEBUG] Filtering by team: {team_name}")
    
    if team_name:
        # 查询球队最近比赛
        # 策略：查询未来 30 天，找到第一个有比赛的日期
        end_date = date.today() + timedelta(days=30)
        all_matches = await match_ds.fetch_team_matches(team_name, date.today(), end_date)
        
        if not all_matches:
            return []
        
        # 找到第一个比赛日期
        first_date = all_matches[0].kickoff_time.date() if all_matches[0].kickoff_time else date.today()
        
        # 过滤出该日期的比赛
        day_matches = [
            m for m in all_matches
            if m.kickoff_time and m.kickoff_time.date() == first_date
        ]
        
        return day_matches
    else:
        # 查询所有球队最近比赛日
        result = await match_ds.fetch_nearest_match_day()
        
        if not result:
            return []
        
        # 返回第一天的比赛
        return result[0].get("matches", []) if isinstance(result[0], dict) else []


async def query_next_days(
    match_ds: MatchDataSource,
    days: int,
    team_name: Optional[str] = None,
    debug: bool = False
) -> List[Match]:
    """
    查询未来 N 天比赛
    
    Args:
        match_ds: MatchDataSource 实例
        days: 天数
        team_name: 球队名称（可选）
        debug: 是否启用调试模式
        
    Returns:
        比赛列表
    """
    if debug:
        print(f"[DEBUG] Query mode: next {days} days")
        if team_name:
            print(f"[DEBUG] Filtering by team: {team_name}")
    
    if team_name:
        # 查询球队比赛
        end_date = date.today() + timedelta(days=days)
        matches = await match_ds.fetch_team_matches(team_name, date.today(), end_date)
        return matches
    else:
        # 查询所有比赛
        result = await match_ds.fetch_next_n_days(days)
        
        # 合并所有比赛
        all_matches = []
        for day_data in result:
            if isinstance(day_data, dict):
                all_matches.extend(day_data.get("matches", []))
            else:
                all_matches.append(day_data)
        
        return all_matches


async def query_date_range(
    match_ds: MatchDataSource,
    start_date: date,
    end_date: date,
    team_name: Optional[str] = None,
    debug: bool = False
) -> List[Match]:
    """
    查询日期范围内的比赛
    
    Args:
        match_ds: MatchDataSource 实例
        start_date: 开始日期
        end_date: 结束日期
        team_name: 球队名称（可选）
        debug: 是否启用调试模式
        
    Returns:
        比赛列表
    """
    if debug:
        print(f"[DEBUG] Query mode: date range {start_date} to {end_date}")
        if team_name:
            print(f"[DEBUG] Filtering by team: {team_name}")
    
    if team_name:
        # 查询球队比赛
        matches = await match_ds.fetch_team_matches(team_name, start_date, end_date)
        return matches
    else:
        # 查询所有比赛
        result = await match_ds.fetch_in_date_range(start_date, end_date)
        
        # 合并所有比赛
        all_matches = []
        for day_data in result:
            if isinstance(day_data, dict):
                all_matches.extend(day_data.get("matches", []))
            else:
                all_matches.append(day_data)
        
        return all_matches



async def format_table(matches: List[Match]) -> str:
    """
    表格格式输出
    
    Args:
        matches: 比赛列表
        
    Returns:
        格式化的表格字符串
    """
    if not matches:
        return "没有比赛数据"
    
    # 表头
    headers = ["比赛时间", "比赛 ID", "赛季", "轮次", "主队名称", "主队 ID", "客队名称", "客队 ID", "比赛状态"]
    
    # 计算列宽
    widths = [len(h) for h in headers]
    
    rows = []
    for match in matches:
        # 比赛时间
        time_str = ""
        if match.kickoff_time:
            time_str = match.kickoff_time.strftime("%Y-%m-%d\n%H:%M")
        
        # 比赛 ID
        match_id = str(match.match_id) if match.match_id else ""
        
        # 赛季
        season = match.season or "Unknown"
        
        # 轮次
        round_info = f"R{match.game_week}" if match.game_week else f"ID:{match.competition_id}"
        
        # 主队
        home_team = match.home_team or ""
        home_id = str(match.home_team_id) if match.home_team_id else ""
        
        # 客队
        away_team = match.away_team or ""
        away_id = str(match.away_team_id) if match.away_team_id else ""
        
        # 状态
        status = match.status.value if match.status else ""
        
        row = [time_str, match_id, season, round_info, home_team, home_id, away_team, away_id, status]
        rows.append(row)
        
        # 更新列宽
        for i, cell in enumerate(row):
            cell_height = len(cell.split('\n')) if '\n' in cell else 1
            if i < len(widths):
                widths[i] = max(widths[i], max(len(line) for line in cell.split('\n')))
    
    # 构建表格
    lines = []
    
    # 顶边框
    top_border = "┌" + "┬".join("─" * w for w in widths) + "┐"
    lines.append(top_border)
    
    # 表头
    header_line = "│" + "│".join(h.center(w) for h, w in zip(headers, widths)) + "│"
    lines.append(header_line)
    
    # 分隔线
    sep_line = "├" + "┼".join("─" * w for w in widths) + "┤"
    lines.append(sep_line)
    
    # 数据行
    for row in rows:
        # 处理多行单元格
        max_lines = max(len(cell.split('\n')) if '\n' in cell else 1 for cell in row)
        
        for line_idx in range(max_lines):
            row_parts = []
            for cell, width in zip(row, widths):
                cell_lines = cell.split('\n') if '\n' in cell else [cell]
                if line_idx < len(cell_lines):
                    row_parts.append(cell_lines[line_idx].ljust(width))
                else:
                    row_parts.append(" " * width)
            
            row_line = "│" + "│".join(row_parts) + "│"
            lines.append(row_line)
    
    # 底边框
    bottom_border = "└" + "┴".join("─" * w for w in widths) + "┘"
    lines.append(bottom_border)
    
    return "\n".join(lines)


async def format_json(matches: List[Match]) -> str:
    """
    JSON 格式输出
    
    Args:
        matches: 比赛列表
        
    Returns:
        JSON 字符串
    """
    data = []
    
    for match in matches:
        match_data = {
            "kickoff_time": match.kickoff_time.isoformat() if match.kickoff_time else None,
            "match_id": match.match_id,
            "season": match.season,
            "round": match.game_week,
            "home_team": match.home_team,
            "home_team_id": match.home_team_id,
            "away_team": match.away_team,
            "away_team_id": match.away_team_id,
            "status": match.status.value if match.status else None,
        }
        data.append(match_data)
    
    return json.dumps(data, indent=2, ensure_ascii=False)


async def format_compact(matches: List[Match]) -> str:
    """
    简洁格式输出
    
    Args:
        matches: 比赛列表
        
    Returns:
        简洁格式字符串，每行一场比赛
    """
    if not matches:
        return "没有比赛数据"
    
    lines = []
    
    for match in matches:
        # 时间
        time_str = match.kickoff_time.strftime("%Y-%m-%d %H:%M") if match.kickoff_time else "Unknown"
        
        # 赛季 - 轮次
        season = match.season or "Unknown"
        round_info = f"R{match.game_week}" if match.game_week else ""
        if round_info:
            season_round = f"{season} - {round_info}"
        else:
            season_round = season
        
        # 对阵
        home = match.home_team or "Unknown"
        away = match.away_team or "Unknown"
        
        # 状态
        status = match.status.value if match.status else "Unknown"
        
        line = f"{time_str} [{season_round}] {home} vs {away} ({status})"
        lines.append(line)
    
    return "\n".join(lines)


def print_summary(matches: List[Match]):
    """
    打印汇总统计
    
    Args:
        matches: 比赛列表
    """
    if not matches:
        return
    
    # 统计有比赛的天数和赛季
    dates = set()
    seasons = set()
    total_rounds = 0
    
    for match in matches:
        if match.kickoff_time:
            dates.add(match.kickoff_time.date())
        if match.season:
            seasons.add(match.season)
        if match.game_week:
            total_rounds += 1
    
    print("\n" + "═" * 50)
    print("汇总统计")
    print("═" * 50)
    print(f"总比赛数：{len(matches)}")
    print(f"有比赛的天数：{len(dates)}")
    print(f"涉及赛季数：{len(seasons)}")
    
    # 显示赛季列表
    if seasons:
        season_list = sorted(list(seasons))
        print(f"赛季列表：{', '.join(season_list)}")
    
    # 显示轮次信息
    if total_rounds > 0:
        print(f"有轮次的比赛数：{total_rounds}")
    
    print("═" * 50)


def show_error(error: ScheduleError):
    """
    显示错误信息
    
    Args:
        error: ScheduleError 实例
    """
    print(f"\n❌ 错误：{error.message}")
    if error.suggestion:
        print(f"💡 提示：{error.suggestion}")
    sys.exit(error.error_code or 1)


async def main():
    """主函数"""
    # 解析参数
    parser = create_parser()
    args = parser.parse_args()
    
    try:
        # 初始化 Provider 和 DataSource
        if args.debug:
            print("[DEBUG] Initializing Provider and DataSource...")
        
        from src.provider.footystats import FootyStatsProvider
        provider = FootyStatsProvider(debug=args.debug)
        match_ds = MatchDataSource(providers=[provider])
        
        # 检查 Provider 是否可用
        if not await provider.is_available():
            raise ScheduleError(
                "API 不可用",
                error_code=1002,
                suggestion="请检查网络连接和 API Key 配置"
            )
        
        # 清除缓存（如果需要）
        if args.no_cache:
            if args.debug:
                print("[DEBUG] Clearing cache...")
            match_ds.clear_cache()
        
        # 验证参数
        if args.next_days:
            days = validate_next_days(args.next_days)
        elif args.date_range:
            start_date = validate_date(args.date_range[0])
            end_date = validate_date(args.date_range[1])
            
            if start_date > end_date:
                raise ScheduleError(
                    f"起始日期不能晚于结束日期：{start_date} > {end_date}",
                    error_code=2004,
                    suggestion="请检查日期范围"
                )
        
        # 执行查询
        if args.nearest:
            matches = await query_nearest(match_ds, args.team, args.debug)
        elif args.next_days:
            matches = await query_next_days(match_ds, days, args.team, args.debug)
        elif args.date_range:
            matches = await query_date_range(match_ds, start_date, end_date, args.team, args.debug)
        else:
            matches = []
        
        # 检查是否有比赛
        if not matches:
            if args.debug:
                print("[DEBUG] No matches found")
            
            date_info = ""
            if args.nearest:
                date_info = "最近比赛日"
            elif args.next_days:
                date_info = f"未来{args.next_days}天"
            elif args.date_range:
                date_info = f"{start_date} 至 {end_date}"
            
            team_info = f"球队 '{args.team}' 的" if args.team else ""
            print(f"ℹ️  提示：{date_info}期间没有{team_info}比赛")
            return
        
        if args.debug:
            print(f"[DEBUG] Found {len(matches)} matches")
        
        # 格式化输出
        if args.json:
            output = await format_json(matches)
        elif args.compact:
            output = await format_compact(matches)
        else:
            output = await format_table(matches)
        
        print(output)
        
        # 打印汇总统计（非 JSON 模式）
        if not args.json:
            print_summary(matches)
        
    except ScheduleError as e:
        show_error(e)
    except Exception as e:
        if args.debug:
            import traceback
            print(f"[DEBUG] Exception: {e}")
            traceback.print_exc()
        print(f"\n❌ 错误：{e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

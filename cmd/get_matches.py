"""
FootyStats 比赛日程查询脚本（使用 DataSource 层）

专注于获取比赛日程/赛程，不获取比赛详情和球队详情

提供三种查询模式：
1. 获取最近有比赛的一天的所有比赛
2. 获取未来 N 天内的所有比赛
3. 获取指定日期的所有比赛

使用方法：
----------

1. 从项目根目录执行（推荐）：
   cd /Users/zhengningdai/workspace/skyold/Goalcast
   python -m cmd.get_matches --nearest

2. 从 cmd 目录执行：
   cd /Users/zhengningdai/workspace/skyold/Goalcast/cmd
   PYTHONPATH=/Users/zhengningdai/workspace/skyold/Goalcast python -m get_matches --nearest

   带参数运行：
   # 获取最近有比赛的一天的所有比赛
   python -m cmd.get_matches --nearest

   # 获取未来 7 天内的所有比赛
   python -m cmd.get_matches --next-days 7

   # 获取指定日期的所有比赛
   python -m cmd.get_matches --date 2026-03-28

   # 组合使用：获取未来 14 天并显示汇总
   python -m cmd.get_matches --next-days 14 --summary

2. 作为模块导入使用：

   from datetime import date
   from datasource.match import MatchDataSource
   from provider.footystats import FootyStatsProvider
   from cmd.get_matches import (
       get_nearest_match_day,
       get_next_n_days_matches,
       get_matches_for_date,
       get_matches_in_date_range
   )

   async def main():
       provider = FootyStatsProvider()
       match_ds = MatchDataSource(providers=[provider])

       # 1. 获取最近有比赛的一天的所有比赛
       nearest = await get_nearest_match_day(match_ds)

       # 2. 获取未来 7 天内的所有比赛
       upcoming = await get_next_n_days_matches(match_ds, days=7)

       # 3. 获取指定日期的所有比赛
       today_matches = await get_matches_for_date(match_ds, date.today())

       # 4. 获取日期范围内的所有比赛
       from datetime import timedelta
       start = date.today()
       end = start + timedelta(days=14)
       range_matches = await get_matches_in_date_range(match_ds, start, end)

   asyncio.run(main())
"""
import asyncio
import argparse
import sys
import json
from pathlib import Path
from datetime import date, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import asdict

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.datasource.match import MatchDataSource
from src.provider.footystats import FootyStatsProvider


async def get_matches_for_date(
    match_ds: MatchDataSource,
    target_date: date,
    debug: bool = False
) -> List[Any]:
    """
    获取指定日期的所有比赛

    Args:
        match_ds: MatchDataSource 实例
        target_date: 目标日期
        debug: 是否打印调试信息

    Returns:
        比赛列表
    """
    if debug:
        print(f"\n[DEBUG] Fetching matches for {target_date.strftime('%Y-%m-%d')}")
    
    matches = await match_ds.fetch_for_date(target_date)
    
    if debug:
        print(f"  Matches found: {len(matches)}")
        if matches:
            print(f"  First match: {matches[0]}")
    
    return matches


async def get_matches_in_date_range(
    match_ds: MatchDataSource,
    start_date: date,
    end_date: date,
    debug: bool = False
) -> List[Dict[str, Any]]:
    """
    获取指定日期范围内所有比赛

    Args:
        match_ds: MatchDataSource 实例
        start_date: 开始日期（包含）
        end_date: 结束日期（包含）
        debug: 是否打印调试信息

    Returns:
        包含每日比赛数据的列表
    """
    if debug:
        print(f"\n[DEBUG] Fetching matches from {start_date} to {end_date}")
    
    result = await match_ds.fetch_in_date_range(start_date, end_date)
    
    if debug:
        print(f"  Days with matches: {len(result)}")
        total_matches = sum(len(day_data["matches"]) for day_data in result)
        print(f"  Total matches: {total_matches}")
    
    return result


async def get_next_n_days_matches(
    match_ds: MatchDataSource,
    days: int = 7,
    debug: bool = False
) -> List[Dict[str, Any]]:
    """
    获取未来 N 天内的所有比赛

    Args:
        match_ds: MatchDataSource 实例
        days: 天数，默认 7 天
        debug: 是否打印调试信息

    Returns:
        包含每日比赛数据的列表
    """
    if debug:
        print(f"\n[DEBUG] Fetching matches for next {days} days")
    
    result = await match_ds.fetch_next_n_days(days)
    
    if debug:
        print(f"  Days with matches: {len(result)}")
        total_matches = sum(len(day_data["matches"]) for day_data in result)
        print(f"  Total matches: {total_matches}")
    
    return result


async def get_nearest_match_day(
    match_ds: MatchDataSource,
    max_lookahead_days: int = 30,
    debug: bool = False
) -> Optional[Dict[str, Any]]:
    """
    获取最近有比赛的一天的所有比赛
    从今天开始向前查找，找到第一个有比赛的日期

    Args:
        match_ds: MatchDataSource 实例
        max_lookahead_days: 最大向前查找天数，默认 30 天
        debug: 是否打印调试信息

    Returns:
        包含日期和比赛列表的字典，如果没有找到则返回 None
    """
    if debug:
        print(f"\n[DEBUG] Finding nearest match day (max {max_lookahead_days} days)")
    
    result = await match_ds.fetch_nearest_match_day(max_lookahead_days)
    
    if debug:
        if result:
            print(f"  Found: {result['date']} with {len(result['matches'])} matches")
        else:
            print(f"  No matches found")
    
    return result


async def get_upcoming_matches_summary(
    match_ds: MatchDataSource,
    days: int = 7
) -> Dict[str, Any]:
    """
    获取未来 N 天比赛的汇总信息

    Args:
        match_ds: MatchDataSource 实例
        days: 天数

    Returns:
        汇总信息字典
    """
    return await match_ds.fetch_upcoming_summary(days)


async def run_nearest(match_ds: MatchDataSource, debug: bool = False, show_analysis: bool = False):
    print("=" * 60)
    print("获取最近有比赛的一天的所有比赛")
    print("=" * 60)
    nearest = await get_nearest_match_day(match_ds, debug=debug)
    if nearest:
        print(f"\n日期：{nearest['date']}")
        print(f"比赛数量：{len(nearest['matches'])}")

        high_xg_matches = []
        high_btts_matches = []

        for i, match in enumerate(nearest["matches"][:10], 1):
            print(f"\n--- 比赛 {i} ---")
            print(f"  {match.home_team} vs {match.away_team}")
            print(f"  联赛：{match.competition}")
            print(f"  状态：{match.status.value}")
            print(f"  开球时间：{match.kickoff_time}")

            if show_analysis:
                if match.home_xg_prematch and match.away_xg_prematch:
                    xg_diff = match.home_xg_prematch - match.away_xg_prematch
                    print(f"  [分析] xG: {match.home_xg_prematch:.2f} vs {match.away_xg_prematch:.2f} (差值: {xg_diff:+.2f})")
                    print(f"  [分析] 总xG: {match.total_xg_prematch:.2f}")
                    if match.total_xg_prematch and match.total_xg_prematch > 2.5:
                        high_xg_matches.append((match.home_team, match.away_team, match.total_xg_prematch))

                if match.btts_potential:
                    print(f"  [分析] BTTS概率: {match.btts_potential}%")
                    if match.btts_potential >= 60:
                        high_btts_matches.append((match.home_team, match.away_team, match.btts_potential))

                if match.o25_potential:
                    print(f"  [分析] 大球(>2.5)概率: {match.o25_potential}%")

                if match.home_ppg and match.away_ppg:
                    ppg_diff = match.home_ppg - match.away_ppg
                    print(f"  [分析] PPG: 主队 {match.home_ppg:.2f} vs 客队 {match.away_ppg:.2f} (差值: {ppg_diff:+.2f})")

                if match.corners_potential:
                    print(f"  [分析] 角球潜力: {match.corners_potential:.1f}")

                if match.avg_potential:
                    print(f"  [分析] 场均进球潜力: {match.avg_potential:.1f}")

            if match.home_odds and match.away_odds:
                print(f"  赔率：主胜 {match.home_odds} | 平局 {match.draw_odds} | 客胜 {match.away_odds}")

            if match.home_stats:
                print(f"  主队统计：控球率 {match.home_stats.possession}% | 射门 {match.home_stats.shots} | xG {match.home_stats.xg}")
            if match.away_stats:
                print(f"  客队统计：控球率 {match.away_stats.possession}% | 射门 {match.away_stats.shots} | xG {match.away_stats.xg}")

            if debug:
                print(f"\n  完整数据结构:")
                match_dict = asdict(match)
                if 'raw_data' in match_dict and match_dict['raw_data']:
                    del match_dict['raw_data']
                print(f"  {json.dumps(match_dict, indent=4, default=str, ensure_ascii=False)}")

        if show_analysis and high_xg_matches:
            print(f"\n{'='*60}")
            print("[高xG比赛推荐]")
            for home, away, total_xg in sorted(high_xg_matches, key=lambda x: x[2], reverse=True)[:3]:
                print(f"  - {home} vs {away} (总xG: {total_xg:.2f})")

        if show_analysis and high_btts_matches:
            print(f"\n{'='*60}")
            print("[高BTTS概率比赛推荐]")
            for home, away, btts in sorted(high_btts_matches, key=lambda x: x[2], reverse=True)[:3]:
                print(f"  - {home} vs {away} (BTTS: {btts}%)")

        if len(nearest["matches"]) > 10:
            print(f"\n  ... and {len(nearest['matches']) - 10} more matches")
    else:
        print("未找到最近有比赛的日期")


async def run_next_days(match_ds: MatchDataSource, days: int, show_summary: bool = False, debug: bool = False):
    print("=" * 60)
    print(f"获取未来{days}天内的所有比赛")
    print("=" * 60)
    upcoming = await get_next_n_days_matches(match_ds, days=days, debug=debug)

    if show_summary:
        summary = await get_upcoming_matches_summary(match_ds, days=days)
        print(f"\n日期范围：{summary['start_date']} ~ {summary['end_date']}")
        print(f"有比赛的天数：{summary['days_with_matches']}")
        print(f"总比赛数：{summary['total_matches']}")
        print(f"涉及联赛数：{summary['unique_leagues']}")
        print(f"联赛列表：{', '.join(summary['leagues'][:10])}")
        if len(summary['leagues']) > 10:
            print(f"  ... and {len(summary['leagues']) - 10} more leagues")
        print()
        print("每日详细数据：")

    for day_data in upcoming:
        print(f"\n{day_data['date']}: {len(day_data['matches'])} matches")
        for match in day_data["matches"][:3]:
            print(f"  - {match.home_team} vs {match.away_team} [{match.competition}]")
        if len(day_data["matches"]) > 3:
            print(f"  ... and {len(day_data['matches']) - 3} more matches")


async def run_date(match_ds: MatchDataSource, target_date: date, debug: bool = False):
    print("=" * 60)
    print(f"获取指定日期的所有比赛")
    print("=" * 60)
    matches = await get_matches_for_date(match_ds, target_date, debug=debug)
    if matches:
        print(f"\n日期：{target_date.strftime('%Y-%m-%d')}")
        print(f"比赛数量：{len(matches)}")
        for match in matches[:10]:
            print(f"  - {match.home_team} vs {match.away_team} [{match.competition}]")
        if len(matches) > 10:
            print(f"  ... and {len(matches) - 10} more matches")
    else:
        print(f"\n日期 {target_date.strftime('%Y-%m-%d')} 没有比赛")


async def main():
    parser = argparse.ArgumentParser(
        description="FootyStats 比赛日程查询工具（使用 DataSource 层）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python -m cmd.get_matches --nearest
  python -m cmd.get_matches --nearest --debug
  python -m cmd.get_matches --next-days 7
  python -m cmd.get_matches --date 2026-03-28
  python -m cmd.get_matches --next-days 14 --summary
        """
    )
    parser.add_argument("--nearest", action="store_true",
                        help="获取最近有比赛的一天的所有比赛")
    parser.add_argument("--next-days", type=int, metavar="N",
                        help="获取未来 N 天内的所有比赛")
    parser.add_argument("--date", type=str, metavar="YYYY-MM-DD",
                        help="获取指定日期的所有比赛")
    parser.add_argument("--summary", action="store_true",
                        help="显示汇总信息（与 --next-days 配合使用）")
    parser.add_argument("--analysis", action="store_true",
                        help="显示比赛分析数据（xG、BTTS概率等）")
    parser.add_argument("--debug", action="store_true",
                        help="打印调试信息")

    args = parser.parse_args()

    provider = FootyStatsProvider(debug=args.debug)
    match_ds = MatchDataSource(providers=[provider])

    if not await provider.is_available():
        print("API is not available. Please check your API key.")
        return

    if args.nearest:
        await run_nearest(match_ds, debug=args.debug, show_analysis=args.analysis)
    elif args.next_days:
        await run_next_days(match_ds, args.next_days, args.summary, args.debug)
    elif args.date:
        try:
            target_date = date.fromisoformat(args.date)
            await run_date(match_ds, target_date, debug=args.debug)
        except ValueError:
            print(f"日期格式错误，请使用 YYYY-MM-DD 格式，例如：2026-03-28")
    else:
        print("请指定查询模式，使用 --help 查看帮助")
        print()
        print("运行演示（所有三种模式）：")
        print("-" * 40)
        await run_nearest(match_ds)
        print()
        await run_next_days(match_ds, 7)
        print()
        await run_date(match_ds, date.today())


if __name__ == "__main__":
    asyncio.run(main())

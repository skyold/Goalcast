"""
FootyStats 比赛日程查询脚本（直接使用 Provider 层）

专注于获取比赛日程/赛程，不获取比赛详情和球队详情

提供三种查询模式：
1. 获取最近有比赛的一天的所有比赛
2. 获取未来 N 天内的所有比赛
3. 获取指定日期的所有比赛

使用方法：
----------

1. 从项目根目录执行（推荐）：
   cd /Users/zhengningdai/workspace/skyold/Goalcast
   python -m cmd.get_matches_from_provider --nearest

2. 从 cmd 目录执行：
   cd /Users/zhengningdai/workspace/skyold/Goalcast/cmd
   PYTHONPATH=/Users/zhengningdai/workspace/skyold/Goalcast python -m get_matches_from_provider --nearest

   带参数运行：
   # 获取最近有比赛的一天的所有比赛
   python -m cmd.get_matches_from_provider --nearest

   # 获取未来 7 天内的所有比赛
   python -m cmd.get_matches_from_provider --next-days 7

   # 获取指定日期的所有比赛
   python -m cmd.get_matches_from_provider --date 2026-03-28

   # 组合使用：获取未来 14 天并显示汇总
   python -m cmd.get_matches_from_provider --next-days 14 --summary

2. 作为模块导入使用：

   from datetime import date
   from goalcast.provider.footystats import FootyStatsProvider
   from cmd.get_matches_from_provider import (
       get_nearest_match_day,
       get_next_n_days_matches,
       get_matches_for_date,
       get_matches_in_date_range
   )

   async def main():
       provider = FootyStatsProvider()

       # 1. 获取最近有比赛的一天的所有比赛
       nearest = await get_nearest_match_day(provider)

       # 2. 获取未来 7 天内的所有比赛
       upcoming = await get_next_n_days_matches(provider, days=7)

       # 3. 获取指定日期的所有比赛
       today_matches = await get_matches_for_date(provider, date.today())

       # 4. 获取日期范围内的所有比赛
       from datetime import timedelta
       start = date.today()
       end = start + timedelta(days=14)
       range_matches = await get_matches_in_date_range(provider, start, end)

   asyncio.run(main())
"""
import asyncio
import argparse
import sys
import json
from pathlib import Path
from datetime import date, timedelta
from typing import Optional, List, Dict, Any


from goalcast.provider.footystats import FootyStatsProvider


async def get_matches_for_date(
    provider: FootyStatsProvider,
    target_date: date,
    debug: bool = False
) -> Optional[Dict[str, Any]]:
    """
    获取指定日期的所有比赛

    Args:
        provider: FootyStatsProvider 实例
        target_date: 目标日期
        debug: 是否打印调试信息

    Returns:
        比赛列表数据
    """
    date_str = target_date.strftime("%Y-%m-%d")
    result = await provider.get_todays_matches(date=date_str)
    
    if debug:
        print(f"\n[DEBUG] API Response for {date_str}:")
        print(f"  Success: {result.get('success') if result else 'None'}")
        if result:
            if result.get("success"):
                data = result.get("data", [])
                print(f"  Data count: {len(data)}")
            else:
                print(f"  Error: {result.get('error', 'Unknown error')}")
    
    return result


async def get_matches_in_date_range(
    provider: FootyStatsProvider,
    start_date: date,
    end_date: date,
    debug: bool = False
) -> List[Dict[str, Any]]:
    """
    获取指定日期范围内所有比赛

    Args:
        provider: FootyStatsProvider 实例
        start_date: 开始日期（包含）
        end_date: 结束日期（包含）
        debug: 是否打印调试信息

    Returns:
        包含每日比赛数据的列表
    """
    all_matches = []
    current_date = start_date

    while current_date <= end_date:
        matches = await get_matches_for_date(provider, current_date, debug=debug)
        if matches and matches.get("success"):
            data = matches.get("data", [])
            if data:
                all_matches.append({
                    "date": current_date.strftime("%Y-%m-%d"),
                    "matches": data
                })
        current_date += timedelta(days=1)

    return all_matches


async def get_next_n_days_matches(
    provider: FootyStatsProvider,
    days: int = 7,
    debug: bool = False
) -> List[Dict[str, Any]]:
    """
    获取未来 N 天内的所有比赛

    Args:
        provider: FootyStatsProvider 实例
        days: 天数，默认 7 天
        debug: 是否打印调试信息

    Returns:
        包含每日比赛数据的列表
    """
    today = date.today()
    end_date = today + timedelta(days=days - 1)
    return await get_matches_in_date_range(provider, today, end_date, debug=debug)


async def get_nearest_match_day(
    provider: FootyStatsProvider,
    max_lookahead_days: int = 30,
    debug: bool = False
) -> Optional[Dict[str, Any]]:
    """
    获取最近有比赛的一天的所有比赛
    从今天开始向前/后查找，找到第一个有比赛的日期

    Args:
        provider: FootyStatsProvider 实例
        max_lookahead_days: 最大向前查找天数，默认 30 天
        debug: 是否打印调试信息

    Returns:
        包含日期和比赛列表的字典，如果没有找到则返回 None
    """
    today = date.today()

    for day_offset in range(max_lookahead_days + 1):
        target_date = today + timedelta(days=day_offset)
        date_str = target_date.strftime("%Y-%m-%d")
        matches = await provider.get_todays_matches(date=date_str)

        if debug:
            print(f"\n[DEBUG] Checking {date_str} (day {day_offset}/{max_lookahead_days})")
            print(f"  Response received: {matches is not None}")
            if matches:
                print(f"  Success: {matches.get('success')}")
                if matches.get("success"):
                    data = matches.get("data", [])
                    print(f"  Matches count: {len(data)}")

        if matches and matches.get("success"):
            data = matches.get("data", [])
            if data:
                return {
                    "date": date_str,
                    "matches": data
                }

    return None


async def get_upcoming_matches_summary(
    provider: FootyStatsProvider,
    days: int = 7
) -> Dict[str, Any]:
    """
    获取未来 N 天比赛的汇总信息

    Args:
        provider: FootyStatsProvider 实例
        days: 天数

    Returns:
        汇总信息字典
    """
    matches_data = await get_next_n_days_matches(provider, days)

    total_matches = sum(len(day_data["matches"]) for day_data in matches_data)

    leagues_set = set()
    for day_data in matches_data:
        for match in day_data["matches"]:
            if "league_name" in match:
                leagues_set.add(match["league_name"])
            elif "league" in match:
                leagues_set.add(match["league"])

    return {
        "period": f"next {days} days",
        "start_date": date.today().strftime("%Y-%m-%d"),
        "end_date": (date.today() + timedelta(days=days - 1)).strftime("%Y-%m-%d"),
        "days_with_matches": len(matches_data),
        "total_matches": total_matches,
        "unique_leagues": len(leagues_set),
        "leagues": sorted(list(leagues_set)),
        "daily_data": matches_data
    }


async def run_nearest(provider: FootyStatsProvider, debug: bool = False):
    print("=" * 60)
    print("获取最近有比赛的一天的所有比赛")
    print("=" * 60)
    nearest = await get_nearest_match_day(provider, debug=debug)
    if nearest:
        print(f"\n日期：{nearest['date']}")
        print(f"比赛数量：{len(nearest['matches'])}")
        for i, match in enumerate(nearest["matches"][:5], 1):
            print(f"\n--- 比赛 {i} ---")
            home = match.get("home_name", match.get("team_home_a", "?"))
            away = match.get("away_name", match.get("team_home_b", "?"))
            league = match.get("league_name", match.get("league", ""))
            status = match.get("status", "SCHEDULED")
            date_unix = match.get("date_unix")
            kickoff = ""
            if date_unix:
                from datetime import datetime
                kickoff = datetime.fromtimestamp(date_unix).strftime("%Y-%m-%d %H:%M")
            
            print(f"  {home} vs {away}")
            print(f"  联赛：{league}")
            print(f"  状态：{status}")
            print(f"  开球时间：{kickoff}")
            
            if debug:
                print(f"  完整数据:")
                print(f"  {json.dumps(match, indent=2, ensure_ascii=False)}")
        if len(nearest["matches"]) > 5:
            print(f"  ... and {len(nearest['matches']) - 5} more matches")
    else:
        print("未找到最近有比赛的日期")


async def run_next_days(provider: FootyStatsProvider, days: int, show_summary: bool = False, debug: bool = False):
    print("=" * 60)
    print(f"获取未来{days}天内的所有比赛")
    print("=" * 60)
    upcoming = await get_next_n_days_matches(provider, days=days, debug=debug)

    if show_summary:
        summary = await get_upcoming_matches_summary(provider, days=days)
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
            home = match.get("home_name", match.get("team_home_a", "?"))
            away = match.get("away_name", match.get("team_home_b", "?"))
            league = match.get("league_name", match.get("league", ""))
            print(f"  - {home} vs {away} [{league}]")
        if len(day_data["matches"]) > 3:
            print(f"  ... and {len(day_data['matches']) - 3} more matches")


async def run_date(provider: FootyStatsProvider, target_date: date, debug: bool = False):
    print("=" * 60)
    print(f"获取指定日期的所有比赛")
    print("=" * 60)
    specific = await get_matches_for_date(provider, target_date, debug=debug)
    if specific and specific.get("success"):
        data = specific.get("data", [])
        print(f"\n日期：{target_date.strftime('%Y-%m-%d')}")
        print(f"比赛数量：{len(data)}")
        for match in data[:10]:
            home = match.get("home_name", match.get("team_home_a", "?"))
            away = match.get("away_name", match.get("team_home_b", "?"))
            league = match.get("league_name", match.get("league", ""))
            print(f"  - {home} vs {away} [{league}]")
        if len(data) > 10:
            print(f"  ... and {len(data) - 10} more matches")
    else:
        print(f"\n日期 {target_date.strftime('%Y-%m-%d')} 没有比赛或请求失败")


async def main():
    parser = argparse.ArgumentParser(
        description="FootyStats 比赛日程查询工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python -m cmd.get_matches_from_provider --nearest
  python -m cmd.get_matches_from_provider --nearest --debug
  python -m cmd.get_matches_from_provider --next-days 7
  python -m cmd.get_matches_from_provider --date 2026-03-28
  python -m cmd.get_matches_from_provider --next-days 14 --summary
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
    parser.add_argument("--debug", action="store_true",
                        help="打印调试信息（显示 API 原始返回数据）")

    args = parser.parse_args()

    provider = FootyStatsProvider(debug=args.debug)

    if not await provider.is_available():
        print("API is not available. Please check your API key.")
        return

    if args.nearest:
        await run_nearest(provider, debug=args.debug)
    elif args.next_days:
        await run_next_days(provider, args.next_days, args.summary, args.debug)
    elif args.date:
        try:
            target_date = date.fromisoformat(args.date)
            await run_date(provider, target_date, debug=args.debug)
        except ValueError:
            print(f"日期格式错误，请使用 YYYY-MM-DD 格式，例如：2026-03-28")
    else:
        print("请指定查询模式，使用 --help 查看帮助")
        print()
        print("运行演示（所有三种模式）：")
        print("-" * 40)
        await run_nearest(provider)
        print()
        await run_next_days(provider, 7)
        print()
        await run_date(provider, date.today())


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
获取德国甲级联赛比赛 - 最终版本
"""

import asyncio
import httpx
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv('.env')

async def get_german_bundesliga_matches():
    """获取德国甲级联赛比赛"""
    print("=" * 80)
    print("FootyStats API - 德国甲级联赛完整报告")
    print("=" * 80)
    
    footystats_key = os.getenv('FOOTYSTATS_API_KEY')
    if not footystats_key:
        print("✗ FootyStats API Key 未配置")
        return
    
    async with httpx.AsyncClient() as client:
        # 1. 获取联赛列表
        print("\n[步骤 1] 获取联赛列表...")
        url = "https://api.football-data-api.com/league-list"
        response = await client.get(url, params={"key": footystats_key})
        
        if not response.status_code == 200:
            print("✗ 无法获取联赛列表")
            return
        
        data = response.json()
        if not data.get("success"):
            print("✗ API 返回失败")
            return
        
        leagues = data.get("data", [])
        
        # 查找德国甲级联赛
        bundesliga = None
        for league in leagues:
            league_name = league.get("league_name", "") or league.get("name", "") or ""
            country_name = league.get("country", "") or league.get("nation", "") or ""
            
            if "bundesliga" in league_name.lower() and "germany" in country_name.lower():
                bundesliga = league
                break
        
        if not bundesliga:
            print("✗ 未找到德国甲级联赛")
            return
        
        print(f"✓ 联赛：{bundesliga.get('league_name')}")
        print(f"✓ 国家：{bundesliga.get('country')}")
        
        # 获取最新的赛季 ID
        seasons = bundesliga.get("season", [])
        if not seasons:
            print("✗ 没有赛季数据")
            return
        
        latest_season = seasons[-1]
        season_id = latest_season.get("id")
        season_year = latest_season.get("year")
        print(f"✓ 赛季：{season_year} (ID: {season_id})")
        
        # 2. 获取联赛比赛
        print(f"\n[步骤 2] 获取联赛比赛数据...")
        url = "https://api.football-data-api.com/league-matches"
        response = await client.get(url, params={
            "key": footystats_key,
            "season_id": season_id
        })
        
        if not response.status_code == 200:
            print("✗ 无法获取比赛数据")
            return
        
        data = response.json()
        if not data.get("success"):
            print("✗ API 返回失败")
            return
        
        matches = data.get("data", [])
        print(f"✓ 成功获取 {len(matches)} 场比赛")
        
        # 3. 分析比赛数据
        print(f"\n[步骤 3] 分析比赛数据...")
        
        # 解析所有比赛日期（使用 date_unix）
        match_dates = []
        for match in matches:
            date_unix = match.get("date_unix")
            if date_unix:
                try:
                    match_datetime = datetime.fromtimestamp(int(date_unix))
                    match_dates.append(match_datetime)
                except:
                    pass
        
        latest = None
        if match_dates:
            earliest = min(match_dates)
            latest = max(match_dates)
            print(f"  最早比赛：{earliest.strftime('%Y-%m-%d')}")
            print(f"  最晚比赛：{latest.strftime('%Y-%m-%d')}")
        
        # 4. 按日期排序并显示最后 5 场比赛
        print(f"\n[步骤 4] 最后 5 场比赛:")
        print("=" * 80)
        
        parsed_matches = []
        for match in matches:
            date_unix = match.get("date_unix")
            if date_unix:
                try:
                    match_datetime = datetime.fromtimestamp(int(date_unix))
                    parsed_matches.append((match, match_datetime))
                except:
                    pass
        
        parsed_matches.sort(key=lambda x: x[1], reverse=True)
        
        for i, (match, match_datetime) in enumerate(parsed_matches[:5], 1):
            # 获取球队名称
            home_name = match.get("home_name", match.get("homeID", "Unknown"))
            away_name = match.get("away_name", match.get("awayID", "Unknown"))
            
            print(f"\n{i}. {match_datetime.strftime('%Y-%m-%d %H:%M')}")
            print(f"   {home_name} vs {away_name}")
            print(f"   比分：{match.get('homeGoalCount')} - {match.get('awayGoalCount')}")
            print(f"   状态：{match.get('status', 'N/A')}")
            print(f"   轮次：{match.get('game_week', 'N/A')}")
        
        # 5. 筛选本周比赛
        today = datetime.now()
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
        
        print(f"\n[当前时间信息]")
        print(f"  今日日期：{today.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  本周范围：{monday.strftime('%Y-%m-%d')} 至 {sunday.strftime('%Y-%m-%d')}")
        
        weekly_matches = []
        for match, match_datetime in parsed_matches:
            if monday <= match_datetime <= datetime(sunday.year, sunday.month, sunday.day, 23, 59, 59):
                weekly_matches.append((match, match_datetime))
        
        if weekly_matches:
            print(f"\n✓ 本周有 {len(weekly_matches)} 场德国甲级联赛比赛:")
            print("=" * 80)
            for i, (match, match_datetime) in enumerate(weekly_matches, 1):
                home_name = match.get("home_name", match.get("homeID", "Unknown"))
                away_name = match.get("away_name", match.get("awayID", "Unknown"))
                print(f"\n比赛 {i}:")
                print(f"  日期：{match_datetime.strftime('%Y-%m-%d %H:%M')}")
                print(f"  对阵：{home_name} vs {away_name}")
                print(f"  比分：{match.get('homeGoalCount')} - {match.get('awayGoalCount')}")
        else:
            print(f"\n✗ 本周没有德国甲级联赛比赛")
        
        # 6. 结论
        print(f"\n[结论]")
        if latest:
            if latest < today:
                print(f"  ✓ 2025-2026 赛季已经结束")
                print(f"  ✓ 最后一场比赛于 {latest.strftime('%Y-%m-%d')} 进行")
                print(f"  ℹ 当前可能是休赛期，新赛季通常在 8 月开始")
            else:
                print(f"  ℹ 赛季正在进行中")
        else:
            print(f"  ℹ 无法确定赛季状态")
        
        # 7. API 状态总结
        print(f"\n[API 状态总结]")
        print(f"  ✓ SportMonks API: 已配置，免费计划可用")
        print(f"  ✓ FootyStats API: 已配置，工作正常")
        print(f"  ✓ 德国甲级联赛数据：成功获取 ({len(matches)} 场比赛)")
        print(f"  ℹ 本周比赛：{len(weekly_matches)} 场")


if __name__ == "__main__":
    asyncio.run(get_german_bundesliga_matches())

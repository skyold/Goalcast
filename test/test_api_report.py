#!/usr/bin/env python3
"""
完整的 API 测试报告：SportMonks 和 FootyStats
"""

import asyncio
import httpx
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv('.env')

async def test_sportmonks():
    """测试 SportMonks API"""
    print("=" * 80)
    print("SportMonks API 测试")
    print("=" * 80)
    
    api_key = os.getenv('SPORTMONKS_API_KEY')
    if not api_key:
        print("✗ API Key 未配置")
        return False
    
    print(f"✓ API Key 已配置 ({api_key[:15]}...)")
    
    async with httpx.AsyncClient() as client:
        # 测试基础端点
        url = "https://api.sportmonks.com/v3/football/fixtures"
        response = await client.get(url, params={"api_token": api_key})
        
        if response.status_code == 200:
            data = response.json()
            if "data" in data:
                print(f"✓ 基础端点可用 (返回 {len(data['data'])} 条数据)")
                print(f"⚠ 免费计划限制：只能访问有限的历史数据")
                return True
        
        print(f"✗ API 访问失败：{response.status_code}")
        return False


async def test_footystats():
    """测试 FootyStats API"""
    print("\n" + "=" * 80)
    print("FootyStats API 测试")
    print("=" * 80)
    
    api_key = os.getenv('FOOTYSTATS_API_KEY')
    if not api_key:
        print("✗ API Key 未配置")
        return False
    
    print(f"✓ API Key 已配置 ({api_key[:15]}...)")
    
    async with httpx.AsyncClient() as client:
        # 测试：获取联赛列表
        url = "https://api.football-data-api.com/league-list"
        response = await client.get(url, params={"key": api_key})
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                print(f"✓ API 工作正常")
                
                # 查找德国联赛
                leagues = data.get("data", [])
                print(f"✓ 可用联赛数量：{len(leagues)}")
                
                # 搜索德国联赛
                german_leagues = [l for l in leagues if "germany" in l.get("country", "").lower() or "bundesliga" in l.get("league", "").lower()]
                if german_leagues:
                    print(f"✓ 找到 {len(german_leagues)} 个德国相关联赛:")
                    for league in german_leagues[:5]:
                        print(f"  - {league.get('league')} ({league.get('country')})")
                        print(f"    Season ID: {league.get('season_id')}")
                
                return True
            else:
                print(f"✗ API 返回错误：{data.get('message', 'Unknown error')}")
        
        print(f"✗ API 访问失败：{response.status_code}")
        print(f"  响应：{response.text[:200]}")
        return False


async def get_german_bundesliga_matches():
    """尝试获取德国甲级联赛比赛"""
    print("\n" + "=" * 80)
    print("获取德国甲级联赛比赛")
    print("=" * 80)
    
    footystats_key = os.getenv('FOOTYSTATS_API_KEY')
    if not footystats_key:
        print("✗ FootyStats API Key 未配置")
        return
    
    async with httpx.AsyncClient() as client:
        # 1. 获取联赛列表，找到德国甲级联赛
        url = "https://api.football-data-api.com/league-list"
        response = await client.get(url, params={"key": footystats_key})
        
        if not response.status_code == 200:
            print("✗ 无法获取联赛列表")
            return
        
        data = response.json()
        if not data.get("success"):
            print("✗ API 返回失败")
            return
        
        # 查找德国甲级联赛
        bundesliga = None
        for league in data.get("data", []):
            league_name = league.get("league", "").lower()
            country_name = league.get("country", "").lower()
            
            # 查找德国甲级联赛
            if "bundesliga" in league_name and "germany" in country_name:
                bundesliga = league
                break
        
        if not bundesliga:
            print("✗ 未找到德国甲级联赛")
            return
        
        print(f"✓ 找到德国甲级联赛:")
        print(f"  联赛：{bundesliga.get('league')}")
        print(f"  赛季 ID: {bundesliga.get('season_id')}")
        print(f"  国家：{bundesliga.get('country')}")
        
        # 2. 获取联赛比赛
        season_id = bundesliga.get('season_id')
        url = f"https://api.football-data-api.com/league-matches"
        response = await client.get(url, params={
            "key": footystats_key,
            "season_id": season_id
        })
        
        if not response.status_code == 200:
            print("✗ 无法获取比赛数据")
            print(f"  状态码：{response.status_code}")
            print(f"  响应：{response.text[:200]}")
            return
        
        data = response.json()
        if not data.get("success"):
            print("✗ API 返回失败")
            print(f"  消息：{data.get('message', 'Unknown error')}")
            return
        
        matches = data.get("data", [])
        print(f"\n✓ 成功获取 {len(matches)} 场比赛")
        
        # 3. 筛选本周比赛
        today = datetime.now()
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
        
        print(f"\n本周范围：{monday.strftime('%Y-%m-%d')} 至 {sunday.strftime('%Y-%m-%d')}")
        
        weekly_matches = []
        for match in matches:
            match_date = match.get("Date", "")
            try:
                match_datetime = datetime.strptime(match_date, "%Y-%m-%d %H:%M:%S")
                if monday <= match_datetime <= datetime(sunday.year, sunday.month, sunday.day, 23, 59, 59):
                    weekly_matches.append(match)
            except:
                pass
        
        if weekly_matches:
            print(f"\n✓ 本周有 {len(weekly_matches)} 场德国甲级联赛比赛:")
            print("=" * 80)
            for i, match in enumerate(weekly_matches, 1):
                print(f"\n比赛 {i}:")
                print(f"  日期：{match.get('Date')}")
                print(f"  主队：{match.get('HomeTeam')}")
                print(f"  客队：{match.get('AwayTeam')}")
                print(f"  球场：{match.get('Stadium', 'N/A')}")
        else:
            print(f"\n✗ 本周没有德国甲级联赛比赛")
            print(f"  提示：可能是休赛期或比赛不在本周进行")
            
            # 显示接下来的比赛
            upcoming = []
            for match in matches:
                match_date = match.get("Date", "")
                try:
                    match_datetime = datetime.strptime(match_date, "%Y-%m-%d %H:%M:%S")
                    if match_datetime >= today:
                        upcoming.append((match, match_datetime))
                except:
                    pass
            
            upcoming.sort(key=lambda x: x[1])
            
            if upcoming:
                print(f"\n接下来的 {min(5, len(upcoming))} 场比赛:")
                print("=" * 80)
                for i, (match, _) in enumerate(upcoming[:5], 1):
                    print(f"\n{i}. {match.get('Date')}")
                    print(f"   {match.get('HomeTeam')} vs {match.get('AwayTeam')}")
                    print(f"   球场：{match.get('Stadium', 'N/A')}")


async def main():
    print("\n" + "=" * 80)
    print("Goalcast - API 完整性测试报告")
    print("=" * 80)
    print(f"测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 测试 SportMonks
    sportmonks_ok = await test_sportmonks()
    
    # 测试 FootyStats
    footystats_ok = await test_footystats()
    
    # 获取德国甲级联赛比赛
    if footystats_ok:
        await get_german_bundesliga_matches()
    
    # 最终总结
    print("\n" + "=" * 80)
    print("最终总结")
    print("=" * 80)
    print(f"SportMonks API: {'✓ 可用 (免费计划)' if sportmonks_ok else '✗ 不可用'}")
    print(f"FootyStats API: {'✓ 可用' if footystats_ok else '✗ 不可用'}")
    
    if sportmonks_ok and footystats_ok:
        print("\n✓ 两个 API 都已正确配置并可以工作")
        print("\n建议:")
        print("  1. 使用 FootyStats API 获取德国甲级联赛数据（推荐）")
        print("  2. SportMonks API 免费计划限制较多，建议升级或仅用于特定功能")
    elif sportmonks_ok:
        print("\n⚠ 只有 SportMonks API 可用")
        print("建议:")
        print("  1. SportMonks 免费计划限制较多")
        print("  2. 考虑升级到付费计划以获取完整功能")
    elif footystats_ok:
        print("\n✓ FootyStats API 可用")
        print("建议:")
        print("  1. 使用 FootyStats API 获取德国甲级联赛数据")


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
测试 SportMonks API 并获取德国甲级联赛本周比赛时刻表
"""

import asyncio
import sys
from datetime import datetime, timedelta
from provider.sportmonks.client import SportmonksProvider


async def test_api():
    """测试 SportMonks API"""
    print("=" * 60)
    print("SportMonks API 测试")
    print("=" * 60)
    
    # 初始化 provider
    provider = SportmonksProvider(debug=True)
    
    # 检查 API 是否可用
    available = await provider.is_available()
    print(f"\nAPI 可用性：{'✓ 可用' if available else '✗ 不可用'}")
    
    if not available:
        print("\n错误：API Key 未配置")
        return
    
    # 1. 获取所有联赛，找到德国甲级联赛
    print("\n" + "=" * 60)
    print("步骤 1: 查找德国甲级联赛")
    print("=" * 60)
    
    leagues_response = await provider.get_leagues(page=1, include="country,currentSeason")
    
    if not leagues_response:
        print("错误：无法获取联赛列表")
        return
    
    # 查找德国甲级联赛 (Bundesliga)
    bundesliga = None
    if "data" in leagues_response:
        for league in leagues_response["data"]:
            league_name = league.get("name", "")
            country = league.get("country", {})
            country_name = country.get("name", "") if country else ""
            
            # 查找德国甲级联赛
            if "bundesliga" in league_name.lower() and country_name.lower() == "germany":
                bundesliga = league
                print(f"\n✓ 找到德国甲级联赛:")
                print(f"  联赛 ID: {bundesliga.get('id')}")
                print(f"  联赛名称：{league_name}")
                print(f"  国家：{country_name}")
                
                # 获取当前赛季信息
                current_season = league.get("currentSeason", {})
                if current_season:
                    print(f"  当前赛季 ID: {current_season.get('id')}")
                    print(f"  当前赛季名称：{current_season.get('name')}")
                break
    
    if not bundesliga:
        print("\n未找到德国甲级联赛，尝试搜索所有联赛...")
        # 尝试获取更多页面
        for page in range(2, 6):
            leagues_response = await provider.get_leagues(page=page, include="country,currentSeason")
            if leagues_response and "data" in leagues_response:
                for league in leagues_response["data"]:
                    league_name = league.get("name", "")
                    country = league.get("country", {})
                    country_name = country.get("name", "") if country else ""
                    
                    if "bundesliga" in league_name.lower() and country_name.lower() == "germany":
                        bundesliga = league
                        print(f"\n✓ 找到德国甲级联赛 (第{page}页):")
                        print(f"  联赛 ID: {bundesliga.get('id')}")
                        print(f"  联赛名称：{league_name}")
                        print(f"  国家：{country_name}")
                        
                        current_season = league.get("currentSeason", {})
                        if current_season:
                            print(f"  当前赛季 ID: {current_season.get('id')}")
                            print(f"  当前赛季名称：{current_season.get('name')}")
                        break
            if bundesliga:
                break
    
    if not bundesliga:
        print("\n错误：未找到德国甲级联赛")
        print("\n所有可用联赛:")
        if "data" in leagues_response:
            for league in leagues_response["data"][:20]:  # 只显示前 20 个
                print(f"  - {league.get('name')} ({league.get('country', {}).get('name', 'Unknown')})")
        return
    
    # 2. 获取当前赛季信息
    current_season_id = bundesliga.get("currentSeason", {}).get("id")
    if not current_season_id:
        print("\n错误：未找到当前赛季信息")
        return
    
    # 3. 获取本周的日期范围
    today = datetime.now()
    # 找到本周的周一和周日
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    
    start_date = monday.strftime("%Y-%m-%d")
    end_date = sunday.strftime("%Y-%m-%d")
    
    print("\n" + "=" * 60)
    print(f"步骤 2: 获取本周 ({start_date} 至 {end_date}) 比赛")
    print("=" * 60)
    
    # 4. 获取本周所有比赛
    fixtures_response = await provider.get_fixtures_between(
        start_date, 
        end_date, 
        include="league,participants,venue"
    )
    
    if not fixtures_response:
        print("\n错误：无法获取比赛数据")
        return
    
    # 5. 筛选德国甲级联赛的比赛
    bundesliga_fixtures = []
    if "data" in fixtures_response:
        for fixture in fixtures_response["data"]:
            league = fixture.get("league", {})
            league_id = league.get("id") if league else None
            
            if league_id == bundesliga.get("id"):
                bundesliga_fixtures.append(fixture)
    
    # 6. 显示结果
    print("\n" + "=" * 60)
    print(f"本周德国甲级联赛比赛时刻表 (共 {len(bundesliga_fixtures)} 场)")
    print("=" * 60)
    
    if not bundesliga_fixtures:
        print("\n本周没有德国甲级联赛比赛")
        print("\n提示：可能是休赛期，或者比赛不在本周进行")
    else:
        for i, fixture in enumerate(bundesliga_fixtures, 1):
            starting_at = fixture.get("starting_at", "")
            result_info = fixture.get("result_info", "未开赛")
            participants = fixture.get("participants", [])
            venue = fixture.get("venue", {})
            
            # 获取主队和客队
            home_team = None
            away_team = None
            for participant in participants:
                if participant.get("location") == "home":
                    home_team = participant.get("name", "Unknown")
                elif participant.get("location") == "away":
                    away_team = participant.get("name", "Unknown")
            
            print(f"\n比赛 {i}:")
            print(f"  时间：{starting_at}")
            print(f"  对阵：{home_team} vs {away_team}")
            print(f"  状态：{result_info}")
            if venue:
                print(f"  场地：{venue.get('name', 'Unknown')}")
    
    # 7. 获取当前赛季的完整赛程（如果本周没有比赛）
    if not bundesliga_fixtures:
        print("\n" + "=" * 60)
        print("步骤 3: 获取当前赛季完整赛程")
        print("=" * 60)
        
        season_fixtures = await provider.get_fixtures_by_season(
            current_season_id,
            include="league,participants"
        )
        
        if season_fixtures and "data" in season_fixtures:
            # 获取未来 5 场比赛
            upcoming = []
            for fixture in season_fixtures["data"]:
                starting_at = fixture.get("starting_at", "")
                if starting_at >= today.strftime("%Y-%m-%d"):
                    upcoming.append(fixture)
                    if len(upcoming) >= 5:
                        break
            
            if upcoming:
                print(f"\n接下来 5 场比赛:")
                for i, fixture in enumerate(upcoming, 1):
                    starting_at = fixture.get("starting_at", "")
                    participants = fixture.get("participants", [])
                    result_info = fixture.get("result_info", "未开赛")
                    
                    home_team = away_team = None
                    for participant in participants:
                        if participant.get("location") == "home":
                            home_team = participant.get("name", "Unknown")
                        elif participant.get("location") == "away":
                            away_team = participant.get("name", "Unknown")
                    
                    print(f"\n  {i}. {starting_at} - {home_team} vs {away_team} ({result_info})")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_api())

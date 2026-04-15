#!/usr/bin/env python3
"""
检查 understatapi 库的实际 API
"""

import asyncio
import aiohttp
from understat import Understat


async def check_understat_api():
    """检查 understatapi 的实际 API"""
    
    # 创建 session
    session = aiohttp.ClientSession(
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
    )
    
    # 创建 Understat 实例
    understat = Understat(session=session)
    
    print("Understat 对象方法:")
    methods = [m for m in dir(understat) if not m.startswith('_')]
    for method in methods:
        print(f"  - {method}")
    
    # 测试获取联赛球队
    print("\n\n测试获取 Bundesliga 2024 球队...")
    try:
        # 注意：understatapi 使用小写联赛代码
        teams = await understat.get_league_teams("bundesliga", "2024")
        print(f"✓ 成功获取 {len(teams)} 支球队")
        if teams:
            print(f"示例：{teams[0]}")
    except Exception as e:
        print(f"✗ 失败：{e}")
    
    # 测试获取联赛球员
    print("\n测试获取 Bundesliga 2024 球员...")
    try:
        players = await understat.get_league_players("bundesliga", "2024")
        print(f"✓ 成功获取 {len(players)} 名球员")
        if players:
            print(f"示例球员：{players[0].get('player_name')}")
    except Exception as e:
        print(f"✗ 失败：{e}")
    
    # 测试获取联赛比赛
    print("\n测试获取 Bundesliga 2024 比赛...")
    try:
        matches = await understat.get_league_matches("bundesliga", "2024")
        print(f"✓ 成功获取 {len(matches)} 场比赛")
        if matches:
            print(f"示例比赛：{matches[0]}")
    except Exception as e:
        print(f"✗ 失败：{e}")
    
    # 关闭 session
    await session.close()


if __name__ == "__main__":
    asyncio.run(check_understat_api())

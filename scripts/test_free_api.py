#!/usr/bin/env python3

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.collectors.football_data import FootballDataClient, COMPETITION_IDS
from src.utils.logger import logger


async def test_free_api():
    print("\n" + "=" * 60)
    print("🧪 Football-Data.org 免费API测试")
    print("=" * 60)
    print("\n💡 这个API有免费层，每分钟10次请求限制")
    print("   免费层支持: 英超、西甲、意甲、德甲、法甲、欧冠")
    
    client = FootballDataClient()
    
    print("\n📋 测试 1: 获取英超积分榜...")
    try:
        standings = await client.get_standings("Premier League")
        if standings:
            print(f"   ✅ 成功获取积分榜 ({len(standings)} 支球队)")
            for t in standings[:5]:
                print(f"      {t['position']}. {t['team_name']} - {t['points']} pts")
        else:
            print("   ⚠️  未获取到数据 (可能需要API Key)")
    except Exception as e:
        print(f"   ❌ 错误: {e}")
    
    print("\n📋 测试 2: 获取未来7天比赛...")
    try:
        matches = await client.get_upcoming_matches("Premier League", days=7)
        if matches:
            print(f"   ✅ 成功获取 {len(matches)} 场比赛")
            for m in matches[:5]:
                print(f"      - {m['home_name']} vs {m['away_name']} ({m['utc_date'][:10]})")
        else:
            print("   ⚠️  未获取到比赛数据")
    except Exception as e:
        print(f"   ❌ 错误: {e}")
    
    print("\n" + "=" * 60)


async def test_without_api_key():
    print("\n" + "=" * 60)
    print("🧪 测试无API Key模式")
    print("=" * 60)
    print("\n💡 football-data.org 免费层不需要API Key也能访问部分数据")
    
    client = FootballDataClient(api_key="")
    
    for comp_name in ["Premier League", "La Liga", "Serie A"]:
        print(f"\n📋 {comp_name}...")
        try:
            standings = await client.get_standings(comp_name)
            if standings:
                print(f"   ✅ 成功: {len(standings)} 支球队")
            else:
                print("   ❌ 失败")
            await asyncio.sleep(7)
        except Exception as e:
            print(f"   ❌ 错误: {e}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Test free football APIs")
    parser.add_argument("--no-key", action="store_true", help="Test without API key")
    args = parser.parse_args()
    
    if args.no_key:
        asyncio.run(test_without_api_key())
    else:
        asyncio.run(test_free_api())


if __name__ == "__main__":
    main()

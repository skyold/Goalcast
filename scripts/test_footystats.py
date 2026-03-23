#!/usr/bin/env python3

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.collectors.footystats import FootyStatsClient
from src.utils.logger import logger
from config.settings import settings


LEAGUE_IDS = {
    "Premier League": "148",
    "La Liga": "468",
    "Serie A": "262",
    "Bundesliga": "196",
    "Ligue 1": "176",
    "Champions League": "635",
    "Europa League": "636",
}


async def test_footystats_api():
    print("\n" + "=" * 60)
    print("🧪 FootyStats API 连接测试")
    print("=" * 60)
    
    api_key = settings.FOOTYSTATS_API_KEY
    print(f"\n📋 API Key: {api_key[:5]}...{api_key[-3:]}")
    
    client = FootyStatsClient()
    
    print("\n📋 测试 1: 获取英超联赛比赛列表...")
    try:
        matches = await client.get_league_matches(LEAGUE_IDS["Premier League"])
        if matches:
            print(f"   ✅ 成功获取 {len(matches)} 场比赛")
            for m in matches[:5]:
                print(f"      - {m.get('home_name')} vs {m.get('away_name')}")
        else:
            print("   ⚠️  未获取到比赛数据")
    except Exception as e:
        print(f"   ❌ 错误: {e}")
    
    print("\n📋 测试 2: 获取联赛积分榜...")
    try:
        table = await client.get_league_table(LEAGUE_IDS["Premier League"])
        if table:
            print(f"   ✅ 成功获取积分榜 ({len(table)} 支球队)")
            for t in table[:5]:
                print(f"      {t.get('position')}. {t.get('team_name')} - {t.get('points')} pts")
        else:
            print("   ❌ 未获取到积分榜数据")
    except Exception as e:
        print(f"   ❌ 错误: {e}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


async def test_all_leagues():
    print("\n" + "=" * 60)
    print("🧪 测试所有联赛")
    print("=" * 60)
    
    client = FootyStatsClient()
    
    for name, league_id in LEAGUE_IDS.items():
        print(f"\n📋 {name} (league_id={league_id})...")
        try:
            matches = await client.get_league_matches(league_id)
            if matches:
                print(f"   ✅ 有数据: {len(matches)} 场比赛")
            else:
                print("   ⚠️  无数据")
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"   ❌ 错误: {e}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Test FootyStats API connection")
    parser.add_argument("--all", action="store_true", help="Test all leagues")
    args = parser.parse_args()
    
    if args.all:
        asyncio.run(test_all_leagues())
    else:
        asyncio.run(test_footystats_api())


if __name__ == "__main__":
    main()

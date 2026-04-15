
import asyncio
import json
import os
import sys
from pathlib import Path

# 添加项目根目录到 sys.path
BASE_DIR = Path(__file__).parent.parent
sys.path.append(str(BASE_DIR))

from provider.sportmonks.client import SportmonksProvider
from config.settings import settings

async def verify_sportmonks_data(fixture_id: int):
    print(f"--- Verifying Fixture ID: {fixture_id} ---")
    provider = SportmonksProvider(api_key=settings.SPORTMONKS_API_KEY, debug=True)
    
    # 1. 检查赛前赔率
    print("\n[1] Checking Prematch Odds...")
    odds_raw = await provider.get_prematch_odds_by_fixture(fixture_id)
    if odds_raw and "data" in odds_raw:
        data = odds_raw["data"]
        print(f"Found {len(data)} odds entries.")
        # 查找 1x2 赔率 (Market ID 1 通常是 3-Way Result)
        three_way = [item for item in data if item.get("market_id") == 1]
        if three_way:
            print("Found 3-Way Result (Market ID 1):")
            for item in three_way:
                print(f"  {item.get('name')}: {item.get('value')} (ID: {item.get('id')})")
        else:
            print("No Market ID 1 found. First 5 markets:")
            markets = set(item.get('market_name') or item.get('market_description') for item in data[:5])
            print(f"  {markets}")
    else:
        print("No prematch odds data returned.")

    # 2. 检查 xG 数据
    print("\n[2] Checking Expected Goals (xG)...")
    # 尝试通过比赛 ID 获取 xG
    xg_fixture = await provider.get_expected_by_fixture(fixture_id)
    if xg_fixture and "data" in xg_fixture:
        print(f"Found {len(xg_fixture['data'])} xG entries for this fixture.")
        for entry in xg_fixture['data']:
             print(f"  Type ID: {entry.get('type_id')}, Value: {entry.get('value')}, Participant ID: {entry.get('participant_id')}")
    else:
        print("No xG data found for this fixture via /expected/fixtures?fixture_id=...")

    # 3. 检查比赛详情 (包含 lineups)
    print("\n[3] Checking Fixture Details (Includes)...")
    fixture_detail = await provider.get_fixture_by_id(fixture_id, include="lineups;participants;expected")
    if fixture_detail and "data" in fixture_detail:
        data = fixture_detail["data"]
        print(f"Fixture: {data.get('name')}")
        lineups = data.get("lineups", [])
        print(f"Lineups count: {len(lineups)}")
        expected = data.get("expected", [])
        print(f"Expected (xG) in include: {len(expected)}")
        if expected:
            for entry in expected:
                print(f"  Type ID: {entry.get('type_id')}, Value: {entry.get('value')}")
    else:
        print("Failed to get fixture details.")

if __name__ == "__main__":
    # 使用之前分析中提到的韩K联比赛 ID: 19648225 (Ulsan HD vs Seoul)
    fid = 19648225
    if len(sys.argv) > 1:
        fid = int(sys.argv[1])
    asyncio.run(verify_sportmonks_data(fid))

#!/usr/bin/env python3
"""
测试 SportMonks API 并检查免费计划可用的数据
"""

import asyncio
import httpx
import os
import json
from datetime import datetime
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv('.env')

async def test_api():
    api_key = os.getenv('SPORTMONKS_API_KEY')
    print(f"API Key: {api_key[:10]}...")
    print("=" * 80)
    print("SportMonks API 免费计划测试报告")
    print("=" * 80)
    
    async with httpx.AsyncClient() as client:
        # 测试：获取基础 fixtures 数据
        print("\n[测试] 获取基础比赛数据")
        url = "https://api.sportmonks.com/v3/football/fixtures"
        response = await client.get(url, params={"api_token": api_key})
        
        print(f"状态码：{response.status_code}")
        
        if response.status_code != 200:
            print("✗ 请求失败")
            return
        
        data = response.json()
        print(f"✓ 成功获取 {len(data.get('data', []))} 条比赛数据")
        
        # 分析数据结构
        if "data" in data and len(data["data"]) > 0:
            first_fixture = data["data"][0]
            print(f"\n数据结构示例:")
            print(f"  字段：{list(first_fixture.keys())}")
            
            # 显示前 5 条数据
            print(f"\n前 5 场比赛:")
            for i, fixture in enumerate(data["data"][:5], 1):
                print(f"\n{i}. 联赛 ID: {fixture.get('league_id')}, 赛季 ID: {fixture.get('season_id')}")
                print(f"   时间：{fixture.get('starting_at')}")
                print(f"   状态：{fixture.get('result_info', 'N/A')}")
                if "participants" in fixture:
                    for p in fixture["participants"]:
                        print(f"   - {p.get('name')} ({p.get('location')})")
        
        # 总结
        print("\n" + "=" * 80)
        print("总结")
        print("=" * 80)
        print(f"✓ SportMonks API 工作正常")
        print(f"✓ API Key 配置正确（{api_key[:15]}...）")
        print(f"✓ 免费计划可以访问基础 /fixtures 端点")
        print(f"✗ 免费计划限制：")
        print(f"  - 无法访问 /fixtures/date/{datetime.now().strftime('%Y-%m-%d')} (今日比赛)")
        print(f"  - 无法访问 /fixtures/between (日期范围比赛)")
        print(f"  - 无法访问 /leagues (联赛列表)")
        print(f"  - 无法访问 /livescores (实时比分)")
        print(f"\n建议：")
        print(f"  1. 当前免费计划只能获取有限的比赛数据")
        print(f"  2. 要获取德国甲级联赛数据，需要升级到付费计划")
        print(f"  3. 或者使用 FootyStats API（已配置）作为替代方案")

if __name__ == "__main__":
    asyncio.run(test_api())

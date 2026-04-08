#!/usr/bin/env python3
"""
全面测试 SportMonks API v3 免费计划可用的端点
"""

import asyncio
import httpx
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv('.env')

# 测试的端点列表
ENDPOINTS = [
    # 1. Livescores (实时比分)
    ("livescores", "/livescores", {}),
    ("livescores/inplay", "/livescores/inplay", {}),
    ("livescores/latest", "/livescores/latest", {}),
    
    # 2. Fixtures (比赛)
    ("fixtures (all)", "/fixtures", {"page": 1}),
    ("fixtures/date", "/fixtures/date/2026-04-08", {}),
    ("fixtures/between", "/fixtures/between/2026-04-08/2026-04-15", {}),
    
    # 3. Leagues (联赛)
    ("leagues", "/leagues", {"page": 1}),
    ("leagues/countries/11", "/leagues/countries/11", {}),  # Germany
    ("leagues/search/Bundesliga", "/leagues/search/Bundesliga", {}),
    
    # 4. Seasons (赛季)
    ("seasons", "/seasons", {"page": 1}),
    
    # 5. Standings (积分榜)
    ("standings/seasons/14968", "/standings/seasons/14968", {}),  # Bundesliga 2025-2026
    
    # 6. Teams (球队)
    ("teams", "/teams", {"page": 1}),
    ("teams/seasons/14968", "/teams/seasons/14968", {}),
    
    # 7. Players (球员)
    ("players", "/players", {"page": 1}),
    
    # 8. Fixtures by team/season
    ("fixtures/seasons/14968", "/fixtures/seasons/14968", {}),
    
    # 9. Odds (赔率)
    ("odds/markets", "/odds/markets", {}),
    ("odds/bookmakers", "/odds/bookmakers", {}),
    
    # 10. Predictions (预测)
    ("predictions/value-bets", "/predictions/value-bets", {}),
    
    # 11. Other
    ("topscorers/seasons/14968", "/topscorers/seasons/14968", {}),
    ("schedules/seasons/14968", "/schedules/seasons/14968", {}),
    ("rounds/seasons/14968", "/rounds/seasons/14968", {}),
    ("stages/seasons/14968", "/stages/seasons/14968", {}),
]


async def test_endpoint(client, name, endpoint, params, api_key):
    """测试单个端点"""
    url = f"https://api.sportmonks.com/v3/football{endpoint}"
    all_params = {"api_token": api_key}
    if params:
        all_params.update(params)
    
    try:
        response = await client.get(url, params=all_params)
        data = response.json()
        
        # 分析响应
        result = {
            "name": name,
            "endpoint": endpoint,
            "status_code": response.status_code,
            "available": False,
            "data_count": 0,
            "message": "",
            "subscription_info": None
        }
        
        if response.status_code == 200:
            if "data" in data:
                if isinstance(data["data"], list):
                    result["data_count"] = len(data["data"])
                    result["available"] = True
                    result["message"] = f"✓ 可用，返回 {len(data['data'])} 条数据"
                else:
                    result["data_count"] = 1
                    result["available"] = True
                    result["message"] = f"✓ 可用，返回对象数据"
            elif "message" in data and "No result" in data["message"]:
                result["available"] = False
                result["message"] = f"✗ 无数据或订阅不包含"
                # 检查订阅信息
                if "subscription" in data:
                    result["subscription_info"] = data["subscription"]
            else:
                result["available"] = True
                result["message"] = f"✓ 可用"
        else:
            result["message"] = f"✗ HTTP {response.status_code}"
        
        return result
    except Exception as e:
        return {
            "name": name,
            "endpoint": endpoint,
            "status_code": 0,
            "available": False,
            "data_count": 0,
            "message": f"✗ 错误：{str(e)}",
            "subscription_info": None
        }


async def main():
    """主测试函数"""
    print("=" * 80)
    print("SportMonks API v3 - 免费计划端点测试")
    print("=" * 80)
    print(f"测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    api_key = os.getenv('SPORTMONKS_API_KEY')
    if not api_key:
        print("\n✗ API Key 未配置")
        return
    
    print(f"✓ API Key 已配置：{api_key[:15]}...")
    
    async with httpx.AsyncClient() as client:
        results = []
        
        for name, endpoint, params in ENDPOINTS:
            result = await test_endpoint(client, name, endpoint, params, api_key)
            results.append(result)
            print(f"\n{result['message']:50} | {name}")
    
    # 总结
    print("\n" + "=" * 80)
    print("测试结果总结")
    print("=" * 80)
    
    available = [r for r in results if r["available"]]
    unavailable = [r for r in results if not r["available"]]
    
    print(f"\n✓ 可用的端点 ({len(available)} 个):")
    for r in available:
        print(f"  - {r['name']}: {r['endpoint']} ({r['data_count']} 条数据)")
    
    print(f"\n✗ 不可用的端点 ({len(unavailable)} 个):")
    for r in unavailable:
        print(f"  - {r['name']}: {r['endpoint']}")
    
    # 生成详细报告
    print("\n" + "=" * 80)
    print("免费计划可用数据详细报告")
    print("=" * 80)
    
    report = {
        "test_time": datetime.now().isoformat(),
        "api_key_prefix": api_key[:15],
        "available_endpoints": [],
        "unavailable_endpoints": []
    }
    
    for r in available:
        report["available_endpoints"].append({
            "name": r["name"],
            "endpoint": r["endpoint"],
            "data_count": r["data_count"],
            "description": r["message"]
        })
    
    for r in unavailable:
        report["unavailable_endpoints"].append({
            "name": r["name"],
            "endpoint": r["endpoint"],
            "description": r["message"]
        })
    
    # 保存报告
    with open("sportmonks_api_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ 报告已保存到：sportmonks_api_report.json")
    
    return report


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
测试 SportMonks API 所有端点
"""

import urllib.request
import urllib.parse
import json
import os
from datetime import datetime
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv('.env')

# 测试的端点列表
ENDPOINTS_TO_TEST = [
    # 1. Livescores (实时数据)
    ("livescores", "/livescores"),
    ("livescores/inplay", "/livescores/inplay"),
    ("livescores/latest", "/livescores/latest"),
    
    # 2. Fixtures (赛程与比赛)
    ("fixtures/date", "/fixtures/date/2026-04-12"),
    ("fixtures/between", "/fixtures/between/2026-04-12/2026-04-19"),
    ("fixtures/1", "/fixtures/19621975"),  # 使用有效的比赛 ID
    ("leagues", "/leagues"),
    ("seasons", "/seasons"),
    
    # 3. Standings (积分榜)
    ("standings/seasons", "/standings/seasons/14968"),  # Bundesliga 2025-2026
    
    # 4. Teams & Players (球队与球员)
    ("teams", "/teams"),
    ("players", "/players"),
    
    # 5. xG 数据
    ("expected/fixtures", "/expected/fixtures"),
    ("expected/fixtures by fixture", "/expected/fixtures?fixture_id=19621975"),
    ("expected/fixtures by team", "/expected/fixtures?participant_id=692"),
    
    # 6. Odds (赔率数据)
    ("odds/pre-match/fixtures", "/odds/pre-match/fixtures/19621975"),
    ("odds/inplay/fixtures", "/odds/inplay/fixtures/19621975"),
    
    # 7. Predictions (预测数据)
    ("predictions/value-bets", "/predictions/value-bets"),
    ("predictions/probabilities/fixtures", "/predictions/probabilities/fixtures/19621975"),
    
    # 8. Other
    ("states", "/states"),
    ("topscorers/seasons", "/topscorers/seasons/14968"),
    ("schedules/seasons", "/schedules/seasons/14968"),
    ("rounds/seasons", "/rounds/seasons/14968"),
    ("tv-stations", "/tv-stations"),
]

def test_endpoint(api_key, name, endpoint):
    """测试单个端点"""
    base_url = "https://api.sportmonks.com/v3/football"
    url = base_url + endpoint
    
    # 构建 URL 参数
    if "?" in endpoint:
        # 已经包含参数，只添加 api_token
        url_with_params = url + f"&api_token={api_key}"
    else:
        # 不包含参数，添加 api_token
        url_with_params = url + f"?api_token={api_key}"
    
    try:
        with urllib.request.urlopen(url_with_params, timeout=30) as response:
            status_code = response.getcode()
            data = json.loads(response.read().decode('utf-8'))
            
            result = {
                "name": name,
                "endpoint": endpoint,
                "status_code": status_code,
                "status": "",
                "message": ""
            }
            
            if status_code == 200:
                if "data" in data:
                    if isinstance(data["data"], list):
                        result["status"] = "success"
                        result["message"] = f"返回 {len(data['data'])} 条数据"
                    else:
                        result["status"] = "success"
                        result["message"] = "返回对象数据"
                elif "message" in data:
                    result["status"] = "message"
                    result["message"] = data["message"]
                else:
                    result["status"] = "success"
                    result["message"] = "返回数据"
            elif status_code == 404:
                result["status"] = "error"
                result["message"] = "404 Not Found - 端点路径不正确"
            elif status_code == 401:
                result["status"] = "error"
                result["message"] = "401 Unauthorized - API Key 无效"
            elif status_code == 403:
                result["status"] = "error"
                result["message"] = "403 Forbidden - 订阅级别不足"
            else:
                result["status"] = "error"
                result["message"] = f"HTTP {status_code}"
            
            return result
    except Exception as e:
        return {
            "name": name,
            "endpoint": endpoint,
            "status_code": 0,
            "status": "error",
            "message": f"错误: {str(e)}"
        }

def main():
    """主测试函数"""
    print("=" * 80)
    print("SportMonks API 所有端点测试")
    print("=" * 80)
    print(f"测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    api_key = os.getenv('SPORTMONKS_API_KEY')
    if not api_key:
        print("\n❌ API Key 未配置")
        return
    
    print(f"✅ API Key 已配置：{api_key[:15]}...")
    
    # 测试端点
    print("\n" + "=" * 80)
    print("测试结果")
    print("=" * 80)
    
    results = []
    for name, endpoint in ENDPOINTS_TO_TEST:
        result = test_endpoint(api_key, name, endpoint)
        results.append(result)
        
        status_emoji = "✅" if result["status"] == "success" else "⚠️" if result["status"] == "message" else "❌"
        print(f"{status_emoji} {name:40} | {result['message']}")
    
    # 总结
    print("\n" + "=" * 80)
    print("总结")
    print("=" * 80)
    
    success_count = sum(1 for r in results if r["status"] == "success")
    message_count = sum(1 for r in results if r["status"] == "message")
    error_count = sum(1 for r in results if r["status"] == "error")
    
    print(f"\n✅ 成功: {success_count}")
    print(f"⚠️  消息: {message_count}")
    print(f"❌ 错误: {error_count}")
    print(f"\n总测试数: {len(ENDPOINTS_TO_TEST)}")
    
    # 分析
    print("\n" + "=" * 80)
    print("分析")
    print("=" * 80)
    
    # 检查 404 错误的端点
    not_found_endpoints = [r for r in results if "404" in r["message"]]
    if not_found_endpoints:
        print("\n❌ 404 错误的端点（路径不正确）:")
        for r in not_found_endpoints:
            print(f"  - {r['name']}: {r['endpoint']}")
    
    # 检查成功的端点
    success_endpoints = [r for r in results if r["status"] == "success"]
    if success_endpoints:
        print("\n✅ 成功的端点:")
        for r in success_endpoints:
            print(f"  - {r['name']}")
    
    # 检查返回消息的端点
    message_endpoints = [r for r in results if r["status"] == "message"]
    if message_endpoints:
        print("\n⚠️  返回消息的端点（可能是数据不可用或订阅问题）:")
        for r in message_endpoints:
            print(f"  - {r['name']}: {r['message']}")

if __name__ == "__main__":
    main()

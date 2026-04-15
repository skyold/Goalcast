#!/usr/bin/env python3
"""
测试 Understat API - 直接访问数据端点
"""

import asyncio
import aiohttp
import json


async def test_understat_api_endpoints():
    """测试 Understat 可能的 API 端点"""
    
    async with aiohttp.ClientSession(
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest"
        }
    ) as session:
        # 测试可能的 API 端点
        test_urls = [
            "https://understat.com/match/matchData",
            "https://understat.com/api/league/tables/Bundesliga/2024",
            "https://understat.com/api/league/players/Bundesliga/2024",
            "https://understat.com/api/league/matches/Bundesliga/2024",
        ]
        
        print("测试 API 端点:")
        for url in test_urls:
            try:
                async with session.get(url, timeout=10) as response:
                    print(f"\n{url}")
                    print(f"  状态码：{response.status}")
                    
                    if response.status == 200:
                        content_type = response.headers.get('Content-Type', '')
                        print(f"  Content-Type: {content_type}")
                        
                        if 'json' in content_type:
                            data = await response.json()
                            print(f"  ✓ JSON 数据：{len(str(data))} bytes")
                        else:
                            text = await response.text()
                            print(f"  响应：{len(text)} bytes")
            except Exception as e:
                print(f"  ✗ 错误：{e}")
        
        # 检查实际网页中的 JavaScript 文件
        print("\n\n检查 league.min.js:")
        async with session.get("https://understat.com/js/league.min.js", timeout=10) as response:
            if response.status == 200:
                js_content = await response.text()
                # 查找 API 调用
                import re
                api_calls = re.findall(r'["\'](/api/[^"\']+)["\']', js_content)
                if api_calls:
                    print(f"  找到的 API 调用:")
                    for api_call in api_calls[:10]:
                        print(f"    - {api_call}")
                
                # 查找 AJAX 请求
                ajax_urls = re.findall(r'url:\s*["\']([^"\']+)["\']', js_content)
                if ajax_urls:
                    print(f"\n  AJAX 请求 URLs:")
                    for url in ajax_urls[:10]:
                        print(f"    - {url}")


if __name__ == "__main__":
    asyncio.run(test_understat_api_endpoints())

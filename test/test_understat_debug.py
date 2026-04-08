#!/usr/bin/env python3
"""
调试 Understat 数据提取
"""

import asyncio
import aiohttp
import re
import json


async def debug_understat_extraction():
    """调试 Understat 数据提取"""
    
    async with aiohttp.ClientSession(
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    ) as session:
        # 访问 Bundesliga 2024 页面
        url = "https://understat.com/league/Bundesliga/2024"
        print(f"访问：{url}")
        
        async with session.get(url) as response:
            html = await response.text()
            print(f"状态码：{response.status}")
            print(f"HTML 长度：{len(html)} 字符")
            
            # 查找所有 JavaScript 变量
            patterns = [
                (r"var\s+teamsData\s*=\s*JSON\.parse\('([^']+)'\)", "teamsData"),
                (r"var\s+playersData\s*=\s*JSON\.parse\('([^']+)'\)", "playersData"),
                (r"var\s+matchData\s*=\s*JSON\.parse\('([^']+)'\)", "matchData"),
                (r"var\s+statisticsData\s*=\s*JSON\.parse\('([^']+)'\)", "statisticsData"),
            ]
            
            print("\n查找的数据:")
            for pattern, name in patterns:
                match = re.search(pattern, html)
                if match:
                    print(f"\n✓ 找到 {name}")
                    json_str = match.group(1)
                    print(f"  JSON 长度：{len(json_str)}")
                    
                    # 尝试解析
                    try:
                        json_str_clean = json_str.replace("\\", "")
                        data = json.loads(json_str_clean)
                        if isinstance(data, list):
                            print(f"  数据类型：列表，{len(data)} 项")
                            if data:
                                print(f"  第一项键：{list(data[0].keys()) if isinstance(data[0], dict) else 'N/A'}")
                        elif isinstance(data, dict):
                            print(f"  数据类型：字典，键：{list(data.keys())}")
                    except Exception as e:
                        print(f"  解析失败：{e}")
                else:
                    print(f"✗ 未找到 {name}")
            
            # 保存 HTML 以便进一步分析
            with open("understat_debug.html", "w", encoding="utf-8") as f:
                f.write(html)
            print("\n✓ HTML 已保存到：understat_debug.html")


if __name__ == "__main__":
    asyncio.run(debug_understat_extraction())

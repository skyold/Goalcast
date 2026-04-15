#!/usr/bin/env python3
"""
测试 Understat 网站结构
"""

import asyncio
import aiohttp
import re
from bs4 import BeautifulSoup


async def test_understat_structure():
    """测试 Understat 网站结构"""
    
    async with aiohttp.ClientSession() as session:
        # 访问首页
        print("访问 Understat 首页...")
        async with session.get("https://understat.com") as response:
            html = await response.text()
            print(f"状态码：{response.status}")
            
            # 查找所有链接
            soup = BeautifulSoup(html, 'html.parser')
            links = soup.find_all('a', href=True)
            
            print("\n找到的联赛链接:")
            for link in links[:50]:
                href = link['href']
                if 'league' in href or 'bundesliga' in href.lower():
                    print(f"  - {href}")
        
        # 尝试不同的 URL 格式
        test_urls = [
            "https://understat.com/league/Bundesliga/2024",
            "https://understat.com/league/Bundesliga/2025",
            "https://understat.com/bundesliga/2024",
            "https://understat.com/bundesliga/2025",
        ]
        
        print("\n\n测试不同的 URL 格式:")
        for url in test_urls:
            async with session.get(url) as response:
                print(f"{url}: {response.status}")
                
                if response.status == 200:
                    html = await response.text()
                    # 查找 JavaScript 数据
                    if 'teamsData' in html:
                        print(f"  ✓ 找到 teamsData")
                    if 'playersData' in html:
                        print(f"  ✓ 找到 playersData")
                    if 'matchData' in html:
                        print(f"  ✓ 找到 matchData")


if __name__ == "__main__":
    asyncio.run(test_understat_structure())

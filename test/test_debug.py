#!/usr/bin/env python3
"""
获取德国甲级联赛比赛 - 查找日期字段
"""

import asyncio
import httpx
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv('.env')

async def get_german_bundesliga_matches():
    """获取德国甲级联赛比赛"""
    footystats_key = os.getenv('FOOTYSTATS_API_KEY')
    if not footystats_key:
        print("✗ FootyStats API Key 未配置")
        return
    
    async with httpx.AsyncClient() as client:
        # 1. 获取联赛列表
        url = "https://api.football-data-api.com/league-list"
        response = await client.get(url, params={"key": footystats_key})
        
        if not response.status_code == 200:
            print("✗ 无法获取联赛列表")
            return
        
        data = response.json()
        if not data.get("success"):
            print("✗ API 返回失败")
            return
        
        leagues = data.get("data", [])
        
        # 查找德国甲级联赛
        bundesliga = None
        for league in leagues:
            league_name = league.get("league_name", "") or league.get("name", "") or ""
            country_name = league.get("country", "") or league.get("nation", "") or ""
            
            if "bundesliga" in league_name.lower() and "germany" in country_name.lower():
                bundesliga = league
                break
        
        if not bundesliga:
            print("✗ 未找到德国甲级联赛")
            return
        
        # 2. 获取联赛比赛
        season_id = bundesliga.get("season", [])[-1].get("id")
        url = "https://api.football-data-api.com/league-matches"
        response = await client.get(url, params={
            "key": footystats_key,
            "season_id": season_id
        })
        
        if not response.status_code == 200:
            print("✗ 无法获取比赛数据")
            return
        
        data = response.json()
        if not data.get("success"):
            print("✗ API 返回失败")
            return
        
        matches = data.get("data", [])
        
        # 查找所有包含日期的字段
        print("查找日期字段:")
        date_keywords = ['date', 'time', 'kick', 'start', 'when', 'day']
        
        for i, match in enumerate(matches[:3], 1):
            print(f"\n比赛 {i} 的可能日期字段:")
            for key, value in match.items():
                key_lower = key.lower()
                if any(keyword in key_lower for keyword in date_keywords):
                    print(f"  {key}: {value}")
            
            # 打印所有字段名
            if i == 1:
                print(f"\n所有字段名：{list(match.keys())}")

if __name__ == "__main__":
    asyncio.run(get_german_bundesliga_matches())

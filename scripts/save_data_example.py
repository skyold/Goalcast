#!/usr/bin/env python3
"""
数据文件保存示例脚本
演示如何将 API 数据保存到 data/ 目录
"""
import asyncio
from pathlib import Path
from utils.data_manager import save_json_data, get_data_file_path
from provider.footystats.client import FootyStatsProvider


async def main():
    """示例：获取并保存数据到 data/ 目录"""
    provider = FootyStatsProvider()
    
    # 示例 1: 保存今日比赛到 data/todays_matches.json
    print("获取今日比赛数据...")
    todays_matches = await provider.get_todays_matches()
    if todays_matches:
        file_path = save_json_data(todays_matches, "todays_matches")
        print(f"✓ 已保存到：{file_path}")
    
    # 示例 2: 保存英超积分榜到 data/epl_standings.json
    # 需要使用实际的赛季 ID
    # print("\n获取英超积分榜...")
    # epl_standings = await provider.get_league_tables(season_id=xxx)
    # if epl_standings:
    #     file_path = save_json_data(epl_standings, "epl_standings")
    #     print(f"✓ 已保存到：{file_path}")
    
    # 示例 3: 保存到子目录
    # file_path = save_json_data(data, "matches", subdir="epl")
    # 将保存到：data/epl/matches.json
    
    print("\n数据文件位置说明:")
    print("  - 所有数据文件保存在：data/")
    print("  - *.json 文件已被 .gitignore 忽略，不会提交到 repo")
    print("  - data/ 目录本身会被追踪（通过 .gitkeep 文件）")


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
测试 Understat API Provider
"""

import asyncio
import sys
import os

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from provider.understat.client import UnderstatProvider


async def test_basic():
    """测试基本连接"""
    print("=" * 80)
    print("Understat API 基础测试")
    print("=" * 80)
    
    provider = UnderstatProvider(debug=True)
    
    # 测试连接
    print("\n[测试 1] 检查 API 可用性...")
    available = await provider.is_available()
    print(f"API 可用性：{'✓ 可用' if available else '✗ 不可用'}")
    
    if not available:
        print("无法连接到 Understat，测试终止")
        return
    
    await provider.close()
    print("\n✓ 基础测试通过")


async def test_league_data():
    """测试联赛数据获取"""
    print("\n" + "=" * 80)
    print("Understat API 联赛数据测试")
    print("=" * 80)
    
    provider = UnderstatProvider(debug=True)
    
    # 测试德国甲级联赛
    league = "Bundesliga"
    season = "2025"
    
    print(f"\n[测试 1] 获取 {league} {season} 赛季球队数据...")
    teams = await provider.get_league_teams(league, season)
    
    if teams:
        print(f"✓ 成功获取 {len(teams)} 支球队")
        if teams:
            first_team = teams[0]
            print(f"  示例球队：{first_team.get('team_name', 'Unknown')}")
            print(f"  数据字段：{list(first_team.keys())}")
    else:
        print(f"✗ 获取失败，尝试其他赛季...")
        # 尝试 2024 赛季
        season = "2024"
        print(f"  尝试 {league} {season} 赛季...")
        teams = await provider.get_league_teams(league, season)
        if teams:
            print(f"✓ 成功获取 {len(teams)} 支球队")
    
    # 测试球员数据
    print(f"\n[测试 2] 获取 {league} {season} 赛季球员数据...")
    players = await provider.get_league_players(league, season)
    
    if players:
        print(f"✓ 成功获取 {len(players)} 名球员")
        if players:
            first_player = players[0]
            print(f"  示例球员：{first_player.get('player_name', 'Unknown')}")
            print(f"  数据字段：{list(first_player.keys())}")
    else:
        print(f"✗ 获取失败")
    
    # 测试比赛数据
    print(f"\n[测试 3] 获取 {league} {season} 赛季比赛数据...")
    matches = await provider.get_league_matches(league, season)
    
    if matches:
        print(f"✓ 成功获取 {len(matches)} 场比赛")
        if matches:
            first_match = matches[0]
            print(f"  示例比赛：{first_match.get('h_team', 'Unknown')} vs {first_match.get('a_team', 'Unknown')}")
            print(f"  xG 数据：{first_match.get('h_xG', 0)} - {first_match.get('a_xG', 0)}")
            print(f"  比分：{first_match.get('h_goals', 0)} - {first_match.get('a_goals', 0)}")
    else:
        print(f"✗ 获取失败")
    
    await provider.close()


async def test_team_data():
    """测试球队数据获取"""
    print("\n" + "=" * 80)
    print("Understat API 球队数据测试")
    print("=" * 80)
    
    provider = UnderstatProvider(debug=True)
    
    # 先获取球队列表找到球队 ID
    league = "Bundesliga"
    season = "2024"
    
    print(f"\n[步骤 1] 获取 {league} 球队列表...")
    teams = await provider.get_league_teams(league, season)
    
    if not teams or len(teams) == 0:
        print("✗ 无法获取球队列表")
        return
    
    # 选择第一支球队测试
    team_id = teams[0].get("id")
    team_name = teams[0].get("team_name", "Unknown")
    
    print(f"  测试球队：{team_name} (ID: {team_id})")
    
    # 获取球队统计
    print(f"\n[步骤 2] 获取球队详细统计...")
    team_stats = await provider.get_team_stats(team_id)
    
    if team_stats:
        print(f"✓ 成功获取球队统计")
        print(f"  数据字段：{list(team_stats.keys())}")
    else:
        print(f"✗ 获取失败")
    
    # 获取球队比赛
    print(f"\n[步骤 3] 获取球队比赛数据...")
    team_matches = await provider.get_team_matches(team_id)
    
    if team_matches:
        print(f"✓ 成功获取 {len(team_matches)} 场比赛")
        if team_matches:
            match = team_matches[0]
            print(f"  示例：{match.get('h_team', 'Unknown')} vs {match.get('a_team', 'Unknown')}")
            print(f"  xG: {match.get('h_xG', 0)} - {match.get('a_xG', 0)}")
    else:
        print(f"✗ 获取失败")
    
    await provider.close()


async def test_match_data():
    """测试比赛数据获取"""
    print("\n" + "=" * 80)
    print("Understat API 比赛数据测试")
    print("=" * 80)
    
    provider = UnderstatProvider(debug=True)
    
    # 先获取比赛列表
    league = "Bundesliga"
    season = "2024"
    
    print(f"\n[步骤 1] 获取 {league} {season} 比赛列表...")
    matches = await provider.get_league_matches(league, season)
    
    if not matches or len(matches) == 0:
        print("✗ 无法获取比赛列表")
        return
    
    # 选择第一场比赛测试
    match_id = matches[0].get("id")
    h_team = matches[0].get("h_team", "Unknown")
    a_team = matches[0].get("a_team", "Unknown")
    
    print(f"  测试比赛：{h_team} vs {a_team} (ID: {match_id})")
    
    # 获取比赛详情
    print(f"\n[步骤 2] 获取比赛详细数据...")
    match_stats = await provider.get_match_stats(match_id)
    
    if match_stats:
        print(f"✓ 成功获取比赛数据")
        
        # 解析 xG 数据
        xg_data = provider.parse_xg_data(match_stats)
        print(f"\n  xG 分析:")
        print(f"    主队 xG: {xg_data['home_xg']:.2f}")
        print(f"    客队 xG: {xg_data['away_xg']:.2f}")
        print(f"    实际比分：{xg_data['home_goals']} - {xg_data['away_goals']}")
        
        if xg_data.get("shots"):
            print(f"\n  射门数据 ({len(xg_data['shots'])} 次):")
            for shot in xg_data["shots"][:5]:  # 只显示前 5 次
                print(f"    {shot['minute']}' {shot['player']}: xG={shot['xg']:.3f}, {shot['result']}")
    else:
        print(f"✗ 获取失败")
    
    await provider.close()


async def main():
    """主测试函数"""
    print("\n" + "=" * 80)
    print("Understat API Provider 完整测试")
    print("=" * 80)
    
    # 测试 1: 基础连接
    await test_basic()
    
    # 测试 2: 联赛数据
    await test_league_data()
    
    # 测试 3: 球队数据
    await test_team_data()
    
    # 测试 4: 比赛数据
    await test_match_data()
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

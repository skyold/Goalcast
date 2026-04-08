#!/usr/bin/env python3
"""
Understat Provider 完整能力测试

测试 Understat Provider 在使用 understatapi 库时的所有功能
"""

import asyncio
import sys
import os

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from provider.understat.client import UnderstatProvider, UNDERSTAT_API_AVAILABLE


async def test_library_availability():
    """测试库是否可用"""
    print("=" * 80)
    print("Understat Provider 能力测试")
    print("=" * 80)
    
    print(f"\n[检查] understatapi 库状态:")
    print(f"  库已安装：{'✓ 是' if UNDERSTAT_API_AVAILABLE else '✗ 否'}")
    
    if not UNDERSTAT_API_AVAILABLE:
        print("\n⚠️ understatapi 库未安装，请运行：pip install understatapi")
        return False
    
    return True


async def test_basic_connection():
    """测试基础连接"""
    print("\n" + "=" * 80)
    print("[测试 1] 基础连接测试")
    print("=" * 80)
    
    provider = UnderstatProvider(debug=True, use_library=True)
    
    print(f"\n  Provider 名称：{provider.name}")
    print(f"  使用库模式：{provider.using_library}")
    
    # 测试连接
    print(f"\n  测试 API 可用性...")
    available = await provider.is_available()
    print(f"  API 可用性：{'✓ 可用' if available else '✗ 不可用'}")
    
    await provider.close()
    
    return available


async def test_league_teams():
    """测试获取联赛球队数据"""
    print("\n" + "=" * 80)
    print("[测试 2] 获取联赛球队数据")
    print("=" * 80)
    
    provider = UnderstatProvider(debug=True, use_library=True)
    
    # 测试不同联赛
    test_cases = [
        ("Bundesliga", "2024", "德国甲级联赛"),
        ("EPL", "2024", "英格兰超级联赛"),
        ("La_liga", "2024", "西班牙甲级联赛"),
    ]
    
    for league, season, name in test_cases:
        print(f"\n  测试 {name} ({league} {season})...")
        teams = await provider.get_league_teams(league, season)
        
        if teams:
            print(f"    ✓ 成功获取 {len(teams)} 支球队")
            if teams:
                first_team = teams[0]
                print(f"    示例球队：{first_team.get('title', 'Unknown')}")
                print(f"    数据字段：{list(first_team.keys())[:10]}")
        else:
            print(f"    ✗ 获取失败")
    
    await provider.close()


async def test_league_players():
    """测试获取联赛球员数据"""
    print("\n" + "=" * 80)
    print("[测试 3] 获取联赛球员数据")
    print("=" * 80)
    
    provider = UnderstatProvider(debug=True, use_library=True)
    
    # 测试德甲
    league = "Bundesliga"
    season = "2024"
    
    print(f"\n  测试 {league} {season} 赛季...")
    players = await provider.get_league_players(league, season)
    
    if players:
        print(f"    ✓ 成功获取 {len(players)} 名球员")
        
        # 按 xG 排序
        sorted_players = sorted(
            players,
            key=lambda x: float(x.get('xG', 0)),
            reverse=True
        )
        
        print(f"\n    Top 10 by xG:")
        print(f"    {'球员':<25} {'球队':<20} {'xG':<8} {'进球':<8} {'差值':<8}")
        print(f"    {'-'*75}")
        
        for player in sorted_players[:10]:
            name = player.get('player_name', 'Unknown')[:25]
            team = player.get('team_title', 'Unknown')[:20]
            xg = float(player.get('xG', 0))
            goals = int(player.get('goals', 0))
            diff = goals - xg
            
            print(f"    {name:<25} {team:<20} {xg:<8.2f} {goals:<8} {diff:+<8.2f}")
    else:
        print(f"    ✗ 获取失败")
    
    await provider.close()


async def test_league_matches():
    """测试获取联赛比赛数据"""
    print("\n" + "=" * 80)
    print("[测试 4] 获取联赛比赛数据")
    print("=" * 80)
    
    provider = UnderstatProvider(debug=True, use_library=True)
    
    league = "Bundesliga"
    season = "2024"
    
    print(f"\n  测试 {league} {season} 赛季...")
    matches = await provider.get_league_matches(league, season)
    
    if matches:
        print(f"    ✓ 成功获取 {len(matches)} 场比赛")
        
        # 显示最近 5 场比赛
        print(f"\n    最近 5 场比赛:")
        for match in matches[-5:]:
            h_team = match.get('h_team', 'Unknown')
            a_team = match.get('a_team', 'Unknown')
            h_goals = match.get('h_goals', 'N/A')
            a_goals = match.get('a_goals', 'N/A')
            h_xg = match.get('h_xG', 0)
            a_xg = match.get('a_xG', 0)
            
            print(f"    {h_team} {h_goals}-{a_goals} {a_team} (xG: {h_xg:.2f}-{a_xg:.2f})")
    else:
        print(f"    ✗ 获取失败")
    
    await provider.close()


async def test_match_stats():
    """测试获取比赛统计数据"""
    print("\n" + "=" * 80)
    print("[测试 5] 获取比赛统计数据")
    print("=" * 80)
    
    provider = UnderstatProvider(debug=True, use_library=True)
    
    # 先获取比赛列表
    league = "Bundesliga"
    season = "2024"
    
    print(f"\n  获取 {league} {season} 比赛列表...")
    matches = await provider.get_league_matches(league, season)
    
    if matches and len(matches) > 0:
        # 获取第一场比赛的 ID
        match_id = matches[0].get('id')
        h_team = matches[0].get('h_team', 'Unknown')
        a_team = matches[0].get('a_team', 'Unknown')
        
        print(f"  测试比赛：{h_team} vs {a_team} (ID: {match_id})")
        
        # 获取比赛统计
        print(f"\n  获取比赛详细数据...")
        match_stats = await provider.get_match_stats(match_id)
        
        if match_stats:
            print(f"    ✓ 成功获取比赛数据")
            
            # 解析 xG 数据
            xg_data = provider.parse_xg_data(match_stats)
            print(f"\n    xG 分析:")
            print(f"      主队 xG: {xg_data['home_xg']:.2f}")
            print(f"      客队 xG: {xg_data['away_xg']:.2f}")
            print(f"      实际比分：{xg_data['home_goals']} - {xg_data['away_goals']}")
            
            if xg_data.get('shots'):
                print(f"\n    射门数据 ({len(xg_data['shots'])} 次):")
                for shot in xg_data['shots'][:5]:
                    print(f"      {shot['minute']}' {shot['player']}: xG={shot['xg']:.3f}, {shot['result']}")
        else:
            print(f"    ✗ 获取失败")
    else:
        print(f"    ✗ 无比赛数据")
    
    await provider.close()


async def test_team_stats():
    """测试获取球队统计数据"""
    print("\n" + "=" * 80)
    print("[测试 6] 获取球队统计数据")
    print("=" * 80)
    
    provider = UnderstatProvider(debug=True, use_library=True)
    
    # 先获取球队列表
    league = "Bundesliga"
    season = "2024"
    
    print(f"\n  获取 {league} {season} 球队列表...")
    teams = await provider.get_league_teams(league, season)
    
    if teams and len(teams) > 0:
        # 获取第一支球队的 ID
        team_id = teams[0].get('id')
        team_name = teams[0].get('title', 'Unknown')
        
        print(f"  测试球队：{team_name} (ID: {team_id})")
        
        # 获取球队统计
        print(f"\n  获取球队详细统计...")
        team_stats = await provider.get_team_stats(team_id)
        
        if team_stats:
            print(f"    ✓ 成功获取球队统计")
            print(f"    数据字段：{list(team_stats.keys())}")
        else:
            print(f"    ✗ 获取失败")
    else:
        print(f"    ✗ 无球队数据")
    
    await provider.close()


async def test_player_stats():
    """测试获取球员统计数据"""
    print("\n" + "=" * 80)
    print("[测试 7] 获取球员统计数据")
    print("=" * 80)
    
    provider = UnderstatProvider(debug=True, use_library=True)
    
    # 先获取球员列表
    league = "Bundesliga"
    season = "2024"
    
    print(f"\n  获取 {league} {season} 球员列表...")
    players = await provider.get_league_players(league, season)
    
    if players and len(players) > 0:
        # 获取第一个球员的 ID
        player_id = players[0].get('id')
        player_name = players[0].get('player_name', 'Unknown')
        
        print(f"  测试球员：{player_name} (ID: {player_id})")
        
        # 获取球员统计
        print(f"\n  获取球员详细统计...")
        player_stats = await provider.get_player_stats(player_id)
        
        if player_stats:
            print(f"    ✓ 成功获取球员统计")
            print(f"    数据字段：{list(player_stats.keys())}")
        else:
            print(f"    ✗ 获取失败")
    else:
        print(f"    ✗ 无球员数据")
    
    await provider.close()


async def test_both_modes():
    """测试两种模式（库模式和 HTTP 模式）"""
    print("\n" + "=" * 80)
    print("[测试 8] 两种模式对比")
    print("=" * 80)
    
    league = "Bundesliga"
    season = "2024"
    
    # 测试库模式
    print(f"\n  模式 1: 使用库 (use_library=True)")
    provider_lib = UnderstatProvider(use_library=True)
    print(f"    库可用：{provider_lib.using_library}")
    
    players_lib = await provider_lib.get_league_players(league, season)
    if players_lib:
        print(f"    ✓ 获取 {len(players_lib)} 名球员")
    else:
        print(f"    ✗ 获取失败")
    
    await provider_lib.close()
    
    # 测试 HTTP 模式
    print(f"\n  模式 2: 不使用库 (use_library=False)")
    provider_http = UnderstatProvider(use_library=False)
    print(f"    库可用：{provider_http.using_library}")
    
    players_http = await provider_http.get_league_players(league, season)
    if players_http:
        print(f"    ✓ 获取 {len(players_http)} 名球员")
    else:
        print(f"    ✗ 获取失败")
    
    await provider_http.close()
    
    # 对比结果
    print(f"\n  结果对比:")
    if players_lib and players_http:
        print(f"    两种模式都成功")
        print(f"    库模式：{len(players_lib)} 名球员")
        print(f"    HTTP 模式：{len(players_http)} 名球员")
    elif players_lib:
        print(f"    仅库模式成功 (推荐)")
    elif players_http:
        print(f"    仅 HTTP 模式成功")
    else:
        print(f"    两种模式都失败")


async def main():
    """主测试函数"""
    print("\n" + "=" * 80)
    print("Understat Provider 完整能力测试")
    print("=" * 80)
    print(f"测试时间：{asyncio.get_event_loop().time()}")
    
    # 测试 1: 检查库是否可用
    if not await test_library_availability():
        print("\n⚠️ 测试终止：understatapi 库未安装")
        return
    
    # 测试 2: 基础连接
    await test_basic_connection()
    
    # 测试 3-7: 各种数据获取
    await test_league_teams()
    await test_league_players()
    await test_league_matches()
    await test_match_stats()
    await test_team_stats()
    await test_player_stats()
    
    # 测试 8: 两种模式对比
    await test_both_modes()
    
    # 总结
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)
    print("✓ Understat Provider 能力测试完成")
    print("✓ understatapi 库已集成并可用")
    print("✓ 所有主要功能已测试")
    print("\n详细文档：docs/UNDERSTAT_INTEGRATION.md")
    print("使用指南：skills/understat-provider/SKILL.md")


if __name__ == "__main__":
    asyncio.run(main())

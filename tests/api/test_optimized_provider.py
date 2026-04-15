"""
测试优化后的 Understat Provider 功能

测试内容：
1. get_match_stats - 比赛详细统计
2. get_team_stats - 球队统计（带 season 参数）
3. get_player_stats - 球员统计（处理返回列表）
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from provider.understat.client import UnderstatProvider


async def test_match_stats():
    """测试优化后的比赛统计功能"""
    print("\n" + "="*80)
    print("测试 1: 比赛详细统计 (get_match_stats)")
    print("="*80)
    
    provider = UnderstatProvider(debug=True, use_library=True)
    
    try:
        # 首先获取一场比赛的 ID
        matches = await provider.get_league_matches("Bundesliga", "2024")
        
        if matches and len(matches) > 0:
            match_id = matches[0]["id"]
            print(f"\n使用比赛 ID: {match_id}")
            
            # 测试优化后的 get_match_stats
            stats = await provider.get_match_stats(match_id)
            
            if stats:
                print(f"✓ 成功获取比赛统计数据")
                print(f"  - 总射门次数：{stats.get('total_shots', 'N/A')}")
                print(f"  - 总 xG: {stats.get('total_xg', 'N/A'):.3f}" if stats.get('total_xg') else "  - 总 xG: N/A")
                print(f"  - 主队射门：{stats.get('home_shots', 'N/A')}")
                print(f"  - 客队射门：{stats.get('away_shots', 'N/A')}")
                print(f"  - 射门数据条目：{len(stats.get('shots', []))}")
                print(f"  - 球员数据：{'有' if stats.get('players') else '无'}")
                
                # 显示前 3 次射门详情
                shots = stats.get('shots', [])
                if shots and len(shots) > 0:
                    print(f"\n  前 3 次射门详情:")
                    for i, shot in enumerate(shots[:3], 1):
                        player = shot.get('player_name', 'Unknown')
                        xg = float(shot.get('xG', 0))
                        result = shot.get('result', 'N/A')
                        minute = shot.get('minute', 0)
                        print(f"    {i}. {player} - {minute}' - xG: {xg:.3f} - 结果：{result}")
            else:
                print("✗ 未能获取比赛统计数据")
        else:
            print("✗ 未能获取比赛列表")
            
    except Exception as e:
        print(f"✗ 测试失败：{e}")
        import traceback
        traceback.print_exc()
    finally:
        await provider.close()


async def test_team_stats():
    """测试优化后的球队统计功能"""
    print("\n" + "="*80)
    print("测试 2: 球队统计 (get_team_stats with season)")
    print("="*80)
    
    provider = UnderstatProvider(debug=True, use_library=True)
    
    try:
        # 首先获取球队列表
        teams = await provider.get_league_teams("Bundesliga", "2024")
        
        if teams and len(teams) > 0:
            team_id = teams[0]["id"]
            team_name = teams[0].get("title", "Unknown")
            print(f"\n使用球队：{team_name} (ID: {team_id})")
            
            # 测试带 season 参数的 get_team_stats
            stats = await provider.get_team_stats(team_id, "2024")
            
            if stats:
                print(f"✓ 成功获取球队统计数据（2024 赛季）")
                
                # 显示关键统计
                print(f"\n  球队统计:")
                print(f"    - 球队 ID: {stats.get('id', 'N/A')}")
                print(f"    - 球队名称：{stats.get('title', 'N/A')}")
                
                # 显示球员数据（如果有）
                if stats.get('players'):
                    players = stats['players']
                    print(f"    - 球员数量：{len(players)}")
                    if players and len(players) > 0:
                        print(f"    - 前 3 名球员:")
                        for i, player in enumerate(players[:3], 1):
                            name = player.get('player_name', 'Unknown')
                            goals = player.get('goals', 0)
                            xg = float(player.get('xG', 0))
                            print(f"      {i}. {name} - 进球：{goals}, xG: {xg:.2f}")
            else:
                print("✗ 未能获取球队统计数据")
        else:
            print("✗ 未能获取球队列表")
            
    except Exception as e:
        print(f"✗ 测试失败：{e}")
        import traceback
        traceback.print_exc()
    finally:
        await provider.close()


async def test_player_stats():
    """测试优化后的球员统计功能"""
    print("\n" + "="*80)
    print("测试 3: 球员统计 (get_player_stats - 处理返回列表)")
    print("="*80)
    
    provider = UnderstatProvider(debug=True, use_library=True)
    
    try:
        # 首先获取球员列表
        players = await provider.get_league_players("Bundesliga", "2024")
        
        if players and len(players) > 0:
            # 找一个有 ID 的球员
            player = None
            for p in players:
                if 'id' in p:
                    player = p
                    break
            
            if player:
                player_id = player['id']
                player_name = player.get('player_name', 'Unknown')
                print(f"\n使用球员：{player_name} (ID: {player_id})")
                
                # 测试优化后的 get_player_stats
                stats = await provider.get_player_stats(player_id)
                
                if stats:
                    print(f"✓ 成功获取球员统计数据")
                    print(f"\n  数据结构:")
                    print(f"    - player_id: {stats.get('player_id', 'N/A')}")
                    print(f"    - 最新赛季数据：{'有' if stats.get('latest_season') else '无'}")
                    print(f"    - 所有赛季数据：{len(stats.get('seasons', []))} 个")
                    print(f"    - 职业生涯总和：{'有' if stats.get('career_totals') else '无'}")
                    
                    # 显示职业生涯总和（如果有）
                    if stats.get('career_totals'):
                        totals = stats['career_totals']
                        print(f"\n  职业生涯总和:")
                        print(f"    - 总进球：{totals.get('goals', 0)}")
                        print(f"    - 总 xG: {totals.get('xG', 0):.2f}")
                        print(f"    - 总助攻：{totals.get('assists', 0)}")
                        print(f"    - 总 xA: {totals.get('xA', 0):.2f}")
                    
                    # 显示最新赛季数据
                    if stats.get('latest_season'):
                        latest = stats['latest_season']
                        print(f"\n  最新赛季数据:")
                        print(f"    - 赛季：{latest.get('season', 'N/A')}")
                        print(f"    - 进球：{latest.get('goals', 0)}")
                        print(f"    - xG: {float(latest.get('xG', 0)):.2f}")
                        print(f"    - 助攻：{latest.get('assists', 0)}")
                        print(f"    - xA: {float(latest.get('xA', 0)):.2f}")
                else:
                    print("✗ 未能获取球员统计数据")
            else:
                print("✗ 未能找到合适的球员")
        else:
            print("✗ 未能获取球员列表")
            
    except Exception as e:
        print(f"✗ 测试失败：{e}")
        import traceback
        traceback.print_exc()
    finally:
        await provider.close()


async def main():
    """运行所有测试"""
    print("\n" + "="*80)
    print("Understat Provider 优化功能测试")
    print("测试日期：2026-04-08")
    print("="*80)
    
    # 测试 1: 比赛统计
    await test_match_stats()
    
    # 测试 2: 球队统计
    await test_team_stats()
    
    # 测试 3: 球员统计
    await test_player_stats()
    
    print("\n" + "="*80)
    print("测试完成")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())

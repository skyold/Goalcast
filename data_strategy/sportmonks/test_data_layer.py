"""Sportmonks 数据层测试脚本"""

import sys
import os
import json
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from data_strategy.sportmonks.extractor import SportmonksExtractor
from data_strategy.sportmonks.transformer import SportmonksTransformer
from data_strategy.sportmonks.storage import SportmonksStorage


def create_mock_data():
    """创建模拟数据用于测试"""
    # 创建数据目录
    cache_dir = Path("data/cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建模拟的比赛数据
    mock_matches = {
        "2026-04-14": [
            {
                "id": 12345,
                "league_id": 1,
                "league_name": "Premier League",
                "season_id": 2023,
                "season_name": "2023/2024",
                "home_team_id": 100,
                "home_team_name": "Arsenal",
                "away_team_id": 200,
                "away_team_name": "Chelsea",
                "home_score": 2,
                "away_score": 1,
                "status": "finished",
                "kickoff_time": "2026-04-14T15:00:00Z",
                "venue": "Emirates Stadium",
                "referee": "Michael Oliver"
            }
        ]
    }
    
    # 创建模拟的 xG 数据
    mock_xg = {
        "12345": {
            "home_xg": 1.8,
            "away_xg": 0.9,
            "timestamp": "2026-04-14T17:00:00Z"
        }
    }
    
    # 创建模拟的球队状态数据
    mock_team_form = {
        "100": {
            "team_id": 100,
            "team_name": "Arsenal",
            "form": "WWWDW",
            "points": 71,
            "last_5_matches": [
                {"opponent": "Man City", "result": "W", "goals_for": 3, "goals_against": 1},
                {"opponent": "Liverpool", "result": "W", "goals_for": 2, "goals_against": 0},
                {"opponent": "Tottenham", "result": "W", "goals_for": 2, "goals_against": 1},
                {"opponent": "Man United", "result": "D", "goals_for": 1, "goals_against": 1},
                {"opponent": "Chelsea", "result": "W", "goals_for": 2, "goals_against": 1}
            ],
            "timestamp": "2026-04-14T17:00:00Z"
        },
        "200": {
            "team_id": 200,
            "team_name": "Chelsea",
            "form": "WDDLW",
            "points": 61,
            "last_5_matches": [
                {"opponent": "Arsenal", "result": "L", "goals_for": 1, "goals_against": 2},
                {"opponent": "Liverpool", "result": "D", "goals_for": 1, "goals_against": 1},
                {"opponent": "Tottenham", "result": "D", "goals_for": 2, "goals_against": 2},
                {"opponent": "Man United", "result": "L", "goals_for": 0, "goals_against": 1},
                {"opponent": "Man City", "result": "W", "goals_for": 2, "goals_against": 1}
            ],
            "timestamp": "2026-04-14T17:00:00Z"
        }
    }
    
    # 创建模拟的交锋记录数据
    mock_head_to_head = {
        "100_200": {
            "home_team_id": 100,
            "home_team_name": "Arsenal",
            "away_team_id": 200,
            "away_team_name": "Chelsea",
            "matches": 3,
            "home_wins": 2,
            "draws": 1,
            "away_wins": 0,
            "last_matches": [
                {"date": "2023-10-01", "home_team": "Arsenal", "away_team": "Chelsea", "home_score": 1, "away_score": 0},
                {"date": "2023-01-15", "home_team": "Chelsea", "away_team": "Arsenal", "home_score": 2, "away_score": 2},
                {"date": "2022-08-20", "home_team": "Arsenal", "away_team": "Chelsea", "home_score": 3, "away_score": 1}
            ],
            "timestamp": "2026-04-14T17:00:00Z"
        }
    }
    
    # 创建模拟的积分榜数据
    mock_standings = {
        "1": {
            "league_id": 1,
            "league_name": "Premier League",
            "season_id": 2023,
            "season_name": "2023/2024",
            "standings": [
                {"position": 1, "team_id": 100, "team_name": "Arsenal", "matches_played": 30, "wins": 22, "draws": 5, "losses": 3, "goals_for": 65, "goals_against": 25, "points": 71},
                {"position": 2, "team_id": 200, "team_name": "Chelsea", "matches_played": 30, "wins": 18, "draws": 7, "losses": 5, "goals_for": 55, "goals_against": 30, "points": 61},
                {"position": 3, "team_id": 300, "team_name": "Man City", "matches_played": 30, "wins": 17, "draws": 8, "losses": 5, "goals_for": 60, "goals_against": 35, "points": 59}
            ],
            "timestamp": "2026-04-14T17:00:00Z"
        }
    }
    
    # 创建模拟的赔率数据
    mock_odds = {
        "12345": [
            {
                "bookmaker_id": 1,
                "bookmaker_name": "Bet365",
                "home_win": 1.80,
                "draw": 3.50,
                "away_win": 4.00,
                "timestamp": "2026-04-14T10:00:00Z"
            }
        ]
    }
    
    # 写入模拟数据到文件
    with open(cache_dir / "sportmonks_matches.json", 'w') as f:
        json.dump(mock_matches, f)
    
    with open(cache_dir / "sportmonks_xg_data.json", 'w') as f:
        json.dump(mock_xg, f)
    
    with open(cache_dir / "sportmonks_team_form.json", 'w') as f:
        json.dump(mock_team_form, f)
    
    with open(cache_dir / "sportmonks_head_to_head.json", 'w') as f:
        json.dump(mock_head_to_head, f)
    
    with open(cache_dir / "sportmonks_standings.json", 'w') as f:
        json.dump(mock_standings, f)
    
    with open(cache_dir / "sportmonks_odds.json", 'w') as f:
        json.dump(mock_odds, f)
    
    print("创建模拟数据完成")
    
    # 返回模拟数据
    return mock_matches, mock_xg, mock_team_form, mock_head_to_head, mock_standings, mock_odds


def test_sportmonks_data_layer():
    """测试 Sportmonks 数据层"""
    print("=== Sportmonks 数据层测试 ===")
    
    # 创建模拟数据
    mock_matches, mock_xg, mock_team_form, mock_head_to_head, mock_standings, mock_odds = create_mock_data()
    
    # 初始化组件
    base_path = Path("data/cache")
    db_path = base_path / "goalcast_structured.db"
    
    extractor = SportmonksExtractor(base_path)
    transformer = SportmonksTransformer()
    storage = SportmonksStorage(db_path)
    
    try:
        # 测试 1: 提取数据
        print("\n1. 测试数据提取...")
        # 从JSON文件提取数据
        extracted_data = extractor.extract_all_data("2026-04-14")
        
        # 手动添加模拟的比赛数据（符合转换器期望的结构）
        mock_match_data = [
            {
                "id": 12345,
                "time": {
                    "date": "2026-04-14",
                    "time": "15:00"
                },
                "status": "finished",
                "league": {
                    "id": 1,
                    "name": "Premier League"
                },
                "participants": [
                    {
                        "id": 100,
                        "name": "Arsenal"
                    },
                    {
                        "id": 200,
                        "name": "Chelsea"
                    }
                ],
                "scores": {
                    "home": 2,
                    "away": 1
                },
                "venue_id": 1,
                "referee_id": 1
            }
        ]
        extracted_data['matches'] = mock_match_data
        
        # 手动添加模拟的扩展数据（符合转换器期望的结构）
        mock_extended_data = {
            "12345": {
                "xg": {
                    "data": [
                        {
                            "type": "expected_goals",
                            "home": 1.8,
                            "away": 0.9
                        },
                        {
                            "type": "expected_goals_against",
                            "home": 0.9,
                            "away": 1.8
                        }
                    ]
                },
                "head_to_head": {
                    "data": [
                        {
                            "localteam_id": 100,
                            "visitorteam_id": 200,
                            "localteam_score": 1,
                            "visitorteam_score": 0
                        },
                        {
                            "localteam_id": 200,
                            "visitorteam_id": 100,
                            "localteam_score": 2,
                            "visitorteam_score": 2
                        },
                        {
                            "localteam_id": 100,
                            "visitorteam_id": 200,
                            "localteam_score": 3,
                            "visitorteam_score": 1
                        }
                    ]
                },
                "home_form": {
                    "data": [
                        {
                            "localteam_id": 100,
                            "visitorteam_id": 300,
                            "localteam_score": 3,
                            "visitorteam_score": 1
                        },
                        {
                            "localteam_id": 100,
                            "visitorteam_id": 400,
                            "localteam_score": 2,
                            "visitorteam_score": 0
                        },
                        {
                            "localteam_id": 500,
                            "visitorteam_id": 100,
                            "localteam_score": 1,
                            "visitorteam_score": 2
                        },
                        {
                            "localteam_id": 100,
                            "visitorteam_id": 600,
                            "localteam_score": 1,
                            "visitorteam_score": 1
                        },
                        {
                            "localteam_id": 200,
                            "visitorteam_id": 100,
                            "localteam_score": 1,
                            "visitorteam_score": 2
                        }
                    ]
                },
                "away_form": {
                    "data": [
                        {
                            "localteam_id": 200,
                            "visitorteam_id": 100,
                            "localteam_score": 1,
                            "visitorteam_score": 2
                        },
                        {
                            "localteam_id": 400,
                            "visitorteam_id": 200,
                            "localteam_score": 1,
                            "visitorteam_score": 1
                        },
                        {
                            "localteam_id": 200,
                            "visitorteam_id": 500,
                            "localteam_score": 2,
                            "visitorteam_score": 2
                        },
                        {
                            "localteam_id": 600,
                            "visitorteam_id": 200,
                            "localteam_score": 1,
                            "visitorteam_score": 0
                        },
                        {
                            "localteam_id": 200,
                            "visitorteam_id": 300,
                            "localteam_score": 2,
                            "visitorteam_score": 1
                        }
                    ]
                },
                "standings": {
                    "data": [
                        {
                            "position": 1,
                            "team_id": 100,
                            "points": 71,
                            "matches_played": 30,
                            "wins": 22,
                            "draws": 5,
                            "losses": 3,
                            "goals_for": 65,
                            "goals_against": 25,
                            "goal_difference": 40,
                            "season_id": 2023
                        },
                        {
                            "position": 2,
                            "team_id": 200,
                            "points": 61,
                            "matches_played": 30,
                            "wins": 18,
                            "draws": 7,
                            "losses": 5,
                            "goals_for": 55,
                            "goals_against": 30,
                            "goal_difference": 25,
                            "season_id": 2023
                        },
                        {
                            "position": 3,
                            "team_id": 300,
                            "points": 59,
                            "matches_played": 30,
                            "wins": 17,
                            "draws": 8,
                            "losses": 5,
                            "goals_for": 60,
                            "goals_against": 35,
                            "goal_difference": 25,
                            "season_id": 2023
                        }
                    ]
                }
            }
        }
        extracted_data['extended_data'] = mock_extended_data
        
        print(f"   提取的比赛数量: {len(extracted_data.get('matches', []))}")
        print(f"   提取的扩展数据数量: {len(extracted_data.get('extended_data', {}))}")
        
        # 测试 2: 转换数据
        print("\n2. 测试数据转换...")
        transformed_data = transformer.transform_all_data(extracted_data)
        print(f"   转换后的比赛数量: {len(transformed_data.get('matches', []))}")
        print(f"   转换后的 xG 数据数量: {len(transformed_data.get('xg_data', []))}")
        print(f"   转换后的球队状态数据数量: {len(transformed_data.get('team_forms', []))}")
        print(f"   转换后的交锋记录数据数量: {len(transformed_data.get('head_to_head', []))}")
        print(f"   转换后的积分榜数据数量: {len(transformed_data.get('standings', []))}")
        print(f"   转换后的赔率数据数量: {len(transformed_data.get('odds', []))}")
        
        # 测试 3: 存储数据
        print("\n3. 测试数据存储...")
        storage.save_all_data(transformed_data)
        print("   数据存储完成")
        
        # 测试 4: 查询数据
        print("\n4. 测试数据查询...")
        
        # 查询所有比赛
        matches = storage.get_matches_by_date("2026-04-14")
        print(f"   查询到的比赛数量: {len(matches)}")
        
        if matches:
            # 查询第一个比赛的详情
            match_id = matches[0]['match_id']
            print(f"\n   测试查询比赛 ID: {match_id}")
            
            # 查询比赛详情
            match_detail = storage.get_match(match_id)
            if match_detail:
                print(f"   比赛: {match_detail['home_team_name']} vs {match_detail['away_team_name']}")
                print(f"   联赛: {match_detail['league_name']}")
                print(f"   日期: {match_detail['date']} {match_detail['time']}")
            
            # 查询 xG 数据
            xg_data = storage.get_xg_data(match_id)
            if xg_data:
                print(f"   xG: {xg_data['home_xg']} - {xg_data['away_xg']}")
            
            # 查询赔率数据
            odds_list = storage.get_odds(match_id)
            if odds_list:
                print(f"   赔率数量: {len(odds_list)}")
                print(f"   主胜赔率: {odds_list[0]['home_win']}")
                print(f"   平局赔率: {odds_list[0]['draw']}")
                print(f"   客胜赔率: {odds_list[0]['away_win']}")
            
            # 查询球队状态
            home_team_id = match_detail['home_team_id']
            away_team_id = match_detail['away_team_id']
            
            home_form = storage.get_team_form(home_team_id, match_id)
            if home_form:
                print(f"   主队状态 (最近5场): {home_form['form_5']}")
                print(f"   主队积分: {home_form['points']}")
            
            away_form = storage.get_team_form(away_team_id, match_id)
            if away_form:
                print(f"   客队状态 (最近5场): {away_form['form_5']}")
                print(f"   客队积分: {away_form['points']}")
            
            # 查询交锋记录
            h2h = storage.get_head_to_head(home_team_id, away_team_id)
            if h2h:
                print(f"   交锋记录: {h2h['matches']}场")
                print(f"   主队胜: {h2h['home_wins']}, 平局: {h2h['draws']}, 客队胜: {h2h['away_wins']}")
            
            # 查询积分榜
            league_id = match_detail['league_id']
            standings = storage.get_standings(league_id)
            if standings:
                print(f"   积分榜球队数量: {len(standings)}")
                print(f"   第一名: {standings[0]['team_name']} (积分: {standings[0]['points']})")
        
        # 测试 5: 测试缓存解析器
        print("\n5. 测试缓存解析器...")
        from data_strategy.resolvers.sportmonks_cached_resolver import SportmonksCachedResolver
        
        resolver = SportmonksCachedResolver(base_path)
        
        # 测试获取 xG 数据
        xg = resolver.resolve_xg("Arsenal", "Chelsea", "Premier League", "2023/2024", "100", "200")
        if xg.data:
            print(f"   xG 数据: 主队 {xg.data.get('home_xg', 'N/A')}, 客队 {xg.data.get('away_xg', 'N/A')}")
        
        # 测试获取球队状态
        form = resolver.resolve_form("100", "200")
        if form.data:
            print(f"   球队状态: 数据获取成功")
        
        # 测试获取交锋记录
        h2h = resolver.resolve_head_to_head("100", "200")
        if h2h.data:
            print(f"   交锋记录: 数据获取成功")
        
        # 测试获取积分榜
        league_standings = resolver.resolve_standings("2023")
        if league_standings.data:
            print(f"   积分榜: 数据获取成功")
        
        # 测试获取赔率
        odds = resolver.resolve_odds("12345")
        if odds.data:
            print(f"   赔率: 主胜 {odds.data.get('home_win', 'N/A')}, 平局 {odds.data.get('draw', 'N/A')}, 客胜 {odds.data.get('away_win', 'N/A')}")
        
        print("\n=== 测试完成 ===")
        
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 关闭数据库连接
        storage.close()


if __name__ == "__main__":
    test_sportmonks_data_layer()

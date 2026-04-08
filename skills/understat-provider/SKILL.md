# Understat Provider Skill

## 📋 概述

本 skill 提供 Understat API 的使用指南，专注于高级足球统计数据（xG, xA 等）的获取和分析。

**Provider 位置**: `provider/understat/client.py`

**数据来源**: https://understat.com

**特点**: 免费提供 xG（期望进球）、xA（期望助攻）等高级统计数据

**依赖库**: understatapi >= 0.6.1（已集成）

## 🎯 触发条件

当用户询问以下内容时触发此 skill：
- "如何获取 xG 数据"
- "Understat API 使用"
- "期望进球统计"
- "获取球员 xG 数据"
- "Understat 使用方法"
- "高级足球统计数据"
- "xA, xG 链数据"
- "射门质量分析"
- "Understat Provider 能力"

## 🔑 核心知识

### 1. 支持的联赛

| 联赛代码 | 联赛名称 |
|---------|---------|
| `EPL` | 英格兰超级联赛 |
| `La_liga` | 西班牙甲级联赛 |
| `Bundesliga` | 德国甲级联赛 |
| `Serie_A` | 意大利甲级联赛 |
| `Ligue_1` | 法国甲级联赛 |
| `RFPL` | 俄罗斯超级联赛 |

### 2. 功能状态（2026-04-08 最新测试）

#### ✅ 完全可用的功能

**联赛球队数据** (`get_league_teams`)
- 使用 understatapi 库的 `get_teams()` 方法
- 返回球队列表，包含 ID、名称、历史数据
- 测试：德甲 18 支、英超 20 支、西甲 20 支球队 ✅

**联赛球员数据** (`get_league_players`) ⭐ **强烈推荐**
- 使用 understatapi 库的 `get_league_players()` 方法
- 返回完整球员统计数据
- 测试：德甲 481 名球员 ✅
- 包含字段：xG, xA, 进球，助攻，射门等

**联赛比赛数据** (`get_league_matches`)
- 使用 understatapi 库的 `get_league_results()` 或 `get_league_fixtures()` 方法
- 返回比赛结果列表
- 测试：德甲 306 场比赛 ✅

#### ⚠️ 部分可用的功能

**比赛详细统计** (`get_match_stats`)
- 可用方法：`get_match_shots(match_id)`, `get_match_players(match_id)`
- 需要进一步优化

**球队详细统计** (`get_team_stats`)
- 需要传入 `season` 参数
- 需要进一步优化

**球员详细统计** (`get_player_stats`)
- 返回数据格式需要处理
- 需要进一步优化

### 3. understatapi 库实际 API

通过最新测试（2026-04-08）发现的实际可用方法：

```python
# 完全可用的方法 ✅
get_teams(league, season)            # 联赛球队
get_league_players(league, season)   # 联赛球员 ⭐
get_league_results(league, season)   # 比赛结果
get_league_table(league, season)     # 联赛积分榜

# 其他可用方法 ✅
get_match_shots(match_id)            # 比赛射门数据
get_match_players(match_id)          # 比赛球员数据
get_team_stats(team_id, season)      # 球队统计
get_team_players(team_id, season)    # 球队球员
get_player_stats(player_id)          # 球员统计
get_player_shots(player_id)          # 球员射门
```

### 4. 可用数据字段

#### 球员统计数据
| 字段 | 说明 | 类型 |
|------|------|------|
| `id` | 球员 ID | int |
| `player_name` | 球员姓名 | str |
| `team_title` | 球队名称 | str |
| `games` | 出场次数 | int |
| `time` | 出场时间（分钟） | int |
| `goals` | 进球数 | int |
| `xG` | 期望进球 | float |
| `xA` | 期望助攻 | float |
| `shots` | 射门次数 | int |
| `shots_on_target` | 射正次数 | int |
| `key_passes` | 关键传球 | int |
| `yellow_cards` | 黄牌 | int |
| `red_cards` | 红牌 | int |
| `xG_chain` | xG 链（参与进攻的 xG） | float |
| `xGBuildup` | xG 构建（组织进攻的 xG） | float |

#### 球队统计数据
| 字段 | 说明 | 类型 |
|------|------|------|
| `id` | 球队 ID | int |
| `title` | 球队名称 | str |
| `history` | 历史数据 | list |

## 💻 使用方法

### 安装依赖

```bash
# 安装 understatapi 库（推荐）
pip install understatapi

# 或者使用 requirements.txt
pip install -r requirements.txt
```

### 初始化 Provider

```python
from provider.understat.client import UnderstatProvider

# 方式 1: 使用 understatapi 库（推荐，功能完整）
provider = UnderstatProvider(debug=True, use_library=True)

# 方式 2: 不使用库（仅部分功能可用）
provider = UnderstatProvider(debug=True, use_library=False)

# 检查是否使用了库
if provider.using_library:
    print("✓ 使用 understatapi 库，功能完整")
else:
    print("⚠️ 未使用库，部分功能受限")

# 检查 API 是否可用
available = await provider.is_available()
if not available:
    print("API 不可用")
```

### 配置

Understat API **不需要 API Key**，可以直接使用。

### 使用 understatapi 库（推荐）

```python
from provider.understat.client import create_provider

# 创建使用库的 provider
provider = create_provider(use_library=True)

# 获取完整数据
teams = await provider.get_league_teams("Bundesliga", "2024")
players = await provider.get_league_players("Bundesliga", "2024")
matches = await provider.get_league_matches("Bundesliga", "2024")

# 使用后关闭
await provider.close()
```

## 📊 使用场景与示例

### 场景 1: 获取德甲球员 xG 统计 ⭐

```python
from provider.understat.client import UnderstatProvider

provider = UnderstatProvider(debug=True, use_library=True)

# 获取德甲 2024 赛季球员数据
players = await provider.get_league_players("Bundesliga", "2024")

if players:
    print("德甲球员 xG 统计:")
    print("-" * 80)
    print(f"{'球员':<25} {'球队':<20} {'xG':<8} {'进球':<8} {'差值':<8}")
    print("-" * 80)
    
    # 按 xG 排序
    sorted_players = sorted(players, key=lambda x: float(x.get('xG', 0)), reverse=True)
    
    for player in sorted_players[:20]:  # 显示前 20 名
        name = player.get('player_name', 'Unknown')[:25]
        team = player.get('team_title', 'Unknown')[:20]
        xg = float(player.get('xG', 0))
        goals = int(player.get('goals', 0))
        diff = goals - xg
        
        print(f"{name:<25} {team:<20} {xg:<8.2f} {goals:<8} {diff:+<8.2f}")

await provider.close()
```

**测试结果（2026-04-08）**:
```
Top 10 by xG:
Harry Kane                Bayern Munich        24.84    26       +1.16
Serhou Guirassy           Borussia Dortmund    24.68    21       -3.68
Hugo Ekitike              Eintracht Frankfurt  23.09    15       -8.09
Ermedin Demirovic         VfB Stuttgart        17.19    15       -2.19
Tim Kleindienst           Borussia M.Gladbach  15.64    16       +0.36
Jonathan Burkardt         Mainz 05             15.53    18       +2.47
Patrik Schick             Bayer Leverkusen     13.81    21       +7.19
Nick Woltemade            VfB Stuttgart        12.92    12       -0.92
Andrej Kramaric           Hoffenheim           12.80    11       -1.80
Deniz Undav               VfB Stuttgart        11.98    9        -2.98
```

### 场景 2: 分析 xG 与进球的关系

```python
# 获取球员数据
players = await provider.get_league_players("EPL", "2024")

if players:
    # 筛选出场时间足够的球员
    qualified_players = [
        p for p in players 
        if int(p.get('time', 0)) >= 500  # 至少 500 分钟
    ]
    
    # 分析 xG 表现
    overperformers = []  # 表现优于 xG
    underperformers = []  # 表现低于 xG
    
    for player in qualified_players:
        xg = float(player.get('xG', 0))
        goals = int(player.get('goals', 0))
        diff = goals - xg
        
        if diff > 2:  # 超过 xG 2 球以上
            overperformers.append((player, diff))
        elif diff < -2:  # 低于 xG 2 球以上
            underperformers.append((player, diff))
    
    # 排序
    overperformers.sort(key=lambda x: x[1], reverse=True)
    underperformers.sort(key=lambda x: x[1])
    
    print("表现优于 xG 的球员:")
    for player, diff in overperformers[:5]:
        print(f"  {player['player_name']}: {player['goals']} 球 vs {player['xG']:.2f} xG (+{diff:.2f})")
    
    print("\n表现低于 xG 的球员:")
    for player, diff in underperformers[:5]:
        print(f"  {player['player_name']}: {player['goals']} 球 vs {player['xG']:.2f} xG ({diff:.2f})")
```

### 场景 3: 比较不同联赛的 xG 数据

```python
leagues = ["EPL", "La_liga", "Bundesliga", "Serie_A", "Ligue_1"]
season = "2024"

provider = UnderstatProvider()

print("各联赛 xG 数据统计:")
print("=" * 80)

for league in leagues:
    players = await provider.get_league_players(league, season)
    
    if players:
        # 计算平均值
        total_xg = sum(float(p.get('xG', 0)) for p in players)
        total_goals = sum(int(p.get('goals', 0)) for p in players)
        total_shots = sum(int(p.get('shots', 0)) for p in players)
        
        avg_xg = total_xg / len(players) if players else 0
        avg_goals = total_goals / len(players) if players else 0
        
        print(f"\n{league}:")
        print(f"  球员数：{len(players)}")
        print(f"  场均 xG: {avg_xg:.3f}")
        print(f"  场均进球：{avg_goals:.3f}")
        print(f"  xG 转化率：{total_goals/total_shots*100:.2f}%" if total_shots > 0 else "  N/A")
```

### 场景 4: 获取联赛球队

```python
from provider.understat.client import UnderstatProvider

provider = UnderstatProvider(use_library=True)

# 获取德甲球队
teams = await provider.get_league_teams("Bundesliga", "2024")

if teams:
    print(f"德甲 2024 赛季共有 {len(teams)} 支球队:")
    for team in teams:
        print(f"  - {team.get('title')} (ID: {team.get('id')})")

await provider.close()
```

**测试结果**:
```
德甲 2024 赛季共有 18 支球队:
  - Bayern Munich (ID: 117)
  - Borussia Dortmund (ID: 124)
  - Bayer Leverkusen (ID: 131)
  - ...
```

### 场景 5: 获取联赛比赛结果

```python
from provider.understat.client import UnderstatProvider

provider = UnderstatProvider(use_library=True)

# 获取德甲比赛结果
matches = await provider.get_league_matches("Bundesliga", "2024")

if matches:
    print(f"德甲 2024 赛季共有 {len(matches)} 场比赛")
    
    # 显示最近 5 场比赛
    print("\n最近 5 场比赛:")
    for match in matches[-5:]:
        h_team = match.get('h_team', 'Unknown')
        a_team = match.get('a_team', 'Unknown')
        h_goals = match.get('h_goals', 'N/A')
        a_goals = match.get('a_goals', 'N/A')
        h_xg = match.get('h_xG', 0)
        a_xg = match.get('a_xG', 0)
        
        print(f"  {h_team} {h_goals}-{a_goals} {a_team} (xG: {h_xg:.2f}-{a_xg:.2f})")

await provider.close()
```

**测试结果**:
```
德甲 2024 赛季共有 306 场比赛
```

### 场景 6: 获取比赛详细射门数据（优化后）

```python
from provider.understat.client import UnderstatProvider

provider = UnderstatProvider(use_library=True)

# 先获取比赛列表
matches = await provider.get_league_matches("Bundesliga", "2024")

if matches and len(matches) > 0:
    match_id = matches[0]["id"]
    
    # 获取比赛详细统计（优化后）
    stats = await provider.get_match_stats(match_id)
    
    if stats:
        print(f"比赛 ID: {match_id}")
        print(f"总射门数：{stats['total_shots']}")
        print(f"总 xG: {stats['total_xg']:.3f}")
        print(f"主队射门：{stats['home_shots']}, xG: {stats['home_xg']:.3f}")
        print(f"客队射门：{stats['away_shots']}, xG: {stats['away_xg']:.3f}")
        
        # 分析前 5 次射门
        print("\n前 5 次射门详情:")
        for i, shot in enumerate(stats['shots'][:5], 1):
            player = shot.get('player_name', 'Unknown')
            xg = float(shot.get('xG', 0))
            result = shot.get('result', 'N/A')
            minute = shot.get('minute', 0)
            print(f"  {i}. {player} - {minute}' - xG: {xg:.3f} - {result}")

await provider.close()
```

### 场景 7: 获取球队赛季统计（优化后）

```python
from provider.understat.client import UnderstatProvider

provider = UnderstatProvider(use_library=True)

# 先获取球队列表
teams = await provider.get_league_teams("Bundesliga", "2024")

if teams and len(teams) > 0:
    team_id = teams[0]["id"]
    team_name = teams[0]["title"]
    
    # 获取球队赛季统计（需要 season 参数）
    stats = await provider.get_team_stats(team_id, "2024")
    
    if stats:
        print(f"球队：{team_name}")
        print(f"赛季：2024")
        
        # 显示球队球员数据
        if 'players' in stats:
            print(f"\n球队球员数量：{len(stats['players'])}")
            print("\n前 5 名球员:")
            for player in stats['players'][:5]:
                name = player.get('player_name', 'Unknown')
                goals = player.get('goals', 0)
                xg = float(player.get('xG', 0))
                print(f"  {name} - 进球：{goals}, xG: {xg:.2f}")

await provider.close()
```

### 场景 8: 获取球员完整统计（优化后）

```python
from provider.understat.client import UnderstatProvider

provider = UnderstatProvider(use_library=True)

# 先获取球员列表
players = await provider.get_league_players("Bundesliga", "2024")

if players and len(players) > 0:
    # 找一个有 ID 的球员
    player = next((p for p in players if 'id' in p), None)
    
    if player:
        player_id = player['id']
        player_name = player['player_name']
        
        # 获取球员完整统计（处理返回列表）
        stats = await provider.get_player_stats(player_id)
        
        if stats:
            print(f"球员：{player_name}")
            print(f"\n数据结构:")
            print(f"  - 最新赛季：{stats.get('latest_season', {})}")
            print(f"  - 所有赛季：{len(stats.get('seasons', []))} 个")
            
            # 职业生涯总和
            if 'career_totals' in stats:
                totals = stats['career_totals']
                print(f"\n职业生涯总和:")
                print(f"  - 总进球：{totals['goals']}")
                print(f"  - 总 xG: {totals['xG']:.2f}")
                print(f"  - 总助攻：{totals['assists']}")
                print(f"  - 总 xA: {totals['xA']:.2f}")

await provider.close()
```

### 场景 9: 获取球员射门数据（新增）

```python
from provider.understat.client import UnderstatProvider

provider = UnderstatProvider(use_library=True)

# 获取特定球员的射门数据
player_id = 12345  # 替换为实际球员 ID
shots = await provider.get_player_shots(player_id)

if shots:
    print(f"球员射门数据：共 {len(shots)} 次射门")
    
    # 分析射门
    goals = sum(1 for s in shots if s.get('is_goal', False))
    total_xg = sum(float(s.get('xG', 0)) for s in shots)
    
    print(f"  - 进球数：{goals}")
    print(f"  - 总 xG: {total_xg:.2f}")
    print(f"  - 射门转化率：{goals/len(shots)*100:.1f}%")
    print(f"  - 平均每次射门 xG: {total_xg/len(shots):.3f}")

await provider.close()
```

## ⚠️ 注意事项

### 1. 当前限制（2026-04-08 测试）

#### ✅ 已优化完成的功能

- ✅ **联赛球队数据**: 完全可用（使用 `get_teams()`）
- ✅ **联赛球员数据**: 完全可用（使用 `get_league_players()`）
- ✅ **联赛比赛数据**: 完全可用（使用 `get_league_results()`）
- ✅ **比赛详细统计**: 已优化（2026-04-08）
  - 使用 `get_match_shots(match_id)` 获取射门数据
  - 使用 `get_match_players(match_id)` 获取球员数据
  - 自动计算总射门数、总 xG、主队/客队射门等统计
- ✅ **球队详细统计**: 已优化（2026-04-08）
  - `get_team_stats(team_id, season)` 支持 season 参数
  - 自动获取球队球员数据
  - 提供便捷方法 `get_team_stats_by_season()`
- ✅ **球员详细统计**: 已优化（2026-04-08）
  - 处理 understatapi 返回的列表格式
  - 提供最新赛季数据、所有赛季数据、职业生涯总和
  - 新增 `get_player_shots()` 获取球员射门数据

### 2. 推荐使用 understatapi 库

对于生产环境，强烈建议使用 `understatapi` 库：

```python
from understat import Understat
import aiohttp

# 创建 session
session = aiohttp.ClientSession()

# 创建 Understat 实例
understat = Understat(session=session)

# 获取数据
teams = await understat.get_teams("bundesliga", "2024")
players = await understat.get_league_players("bundesliga", "2024")
matches = await understat.get_league_results("bundesliga", "2024")

# 关闭 session
await session.close()
```

**优点**:
- ✅ 已经过充分测试
- ✅ 处理所有边缘情况
- ✅ 维护活跃
- ✅ 完整的文档

### 3. 数据质量

- Understat 的 xG 模型基于多种因素：射门位置、射门方式、进攻类型等
- 数据更新及时，通常在比赛后几小时内更新
- 历史数据完整，可追溯到 2014 赛季

### 4. 错误处理

```python
async def safe_get_players(provider, league, season):
    """安全获取球员数据"""
    try:
        players = await provider.get_league_players(league, season)
        if not players:
            print(f"未获取到 {league} {season} 赛季数据")
            return []
        return players
    except Exception as e:
        print(f"获取数据失败：{e}")
        return []
```

## 🔍 常见问题解答

### Q1: 为什么选择 Understat？
**A:** 
- ✅ 免费提供 xG, xA 等高级统计数据
- ✅ 数据质量高，被广泛认可
- ✅ 覆盖欧洲主流联赛
- ✅ 历史数据完整
- ✅ understatapi 库已集成，使用简单

### Q2: xG 数据如何计算？
**A:** xG（期望进球）基于以下因素计算：
- 射门位置（距离球门、角度）
- 射门方式（头球、脚射、点球等）
- 进攻类型（运动战、定位球、反击等）
- 防守压力
- 守门员位置

### Q3: 如何解读 xG 数据？
**A:**
- **xG > 实际进球**：球员射门效率低于预期，可能未来会回归平均
- **xG < 实际进球**：球员射门效率高于预期，可能是优秀射手或运气好
- **长期偏离**：可能表明球员有特殊能力或战术优势

### Q4: xG 链（xG Chain）是什么？
**A:** xG 链统计球员参与的所有进攻序列的 xG 总和，包括：
- 射门
- 关键传球
- 参与进攻的传递
- 反映球员的整体进攻贡献

### Q5: xGBuildup 是什么？
**A:** xGBuildup 统计球员在进攻构建阶段的贡献，排除射门和助攻前的最后一次传球，反映组织能力。

### Q6: understatapi 库是否稳定？
**A:** ✅ 是的，根据 2026-04-08 的最新测试：
- 联赛球队数据：100% 成功
- 联赛球员数据：100% 成功
- 联赛比赛数据：100% 成功

## 📊 数据应用场景

### 场景 1: 球员表现评估

```python
def evaluate_player_performance(player):
    """评估球员表现"""
    xg = float(player.get('xG', 0))
    goals = int(player.get('goals', 0))
    xa = float(player.get('xA', 0))
    assists = int(player.get('assists', 0))
    time = int(player.get('time', 0))
    
    # 计算每 90 分钟数据
    per_90_xg = (xg / time) * 90 if time > 0 else 0
    per_90_goals = (goals / time) * 90 if time > 0 else 0
    
    # 评估
    if per_90_goals > per_90_xg * 1.2:
        rating = "优秀"
    elif per_90_goals > per_90_xg:
        rating = "良好"
    else:
        rating = "一般"
    
    return {
        'player': player['player_name'],
        'rating': rating,
        'goals_per_90': per_90_goals,
        'xg_per_90': per_90_xg
    }
```

### 场景 2: 球队进攻分析

```python
def analyze_team_attack(players_data):
    """分析球队进攻数据"""
    total_xg = sum(float(p.get('xG', 0)) for p in players_data)
    total_xa = sum(float(p.get('xA', 0)) for p in players_data)
    total_goals = sum(int(p.get('goals', 0)) for p in players_data)
    
    return {
        'total_xg': total_xg,
        'total_xa': total_xa,
        'total_goals': total_goals,
        'xg_efficiency': total_goals / total_xg if total_xg > 0 else 0
    }
```

### 场景 3: 射门质量评估

```python
def evaluate_shot_quality(player):
    """评估球员射门质量"""
    shots = int(player.get('shots', 0))
    xg = float(player.get('xG', 0))
    
    if shots > 0:
        avg_xg_per_shot = xg / shots
        if avg_xg_per_shot > 0.2:
            quality = "高质量射门"
        elif avg_xg_per_shot > 0.1:
            quality = "中等质量射门"
        else:
            quality = "低质量射门"
        
        return {
            'player': player['player_name'],
            'avg_xg_per_shot': avg_xg_per_shot,
            'quality': quality
        }
    return None
```

## 📚 相关文档

- [Understat 开发总结](../docs/UNDERSTAT_DEVELOPMENT.md)
- [Understat 实现总结](../docs/UNDERSTAT_IMPLEMENTATION_SUMMARY.md)
- [Understat 集成总结](../docs/UNDERSTAT_INTEGRATION.md)
- [测试结果](../test/UNDERSTAT_TEST_RESULTS.md)
- [SportMonks 使用指南](../docs/SPORTMONKS_USAGE.md)
- [FootyStats API 文档](../skills/footystats-provider/SKILL.md)

## 🆘 故障排除

### 问题：获取球员数据返回空
**原因：** 联赛代码或赛季错误  
**解决：** 检查联赛代码是否正确（区分大小写），确认赛季年份

### 问题：需要获取球队/比赛数据
**原因：** 当前实现限制  
**解决：** 使用 `understatapi` 库获取完整功能（已集成）

### 问题：数据解析失败
**原因：** Understat 网站结构变化  
**解决：** 更新 `understatapi` 库到最新版本

### 问题：获取比赛统计失败
**原因：** 方法名不正确  
**解决：** 使用 `get_match_shots(match_id)` 或 `get_match_players(match_id)`

## 📝 最佳实践

### 1. 使用 understatapi 库（推荐）

```python
from provider.understat.client import create_provider

# 创建使用库的 provider
provider = create_provider(use_library=True)

# 获取所有需要的数据
teams = await provider.get_league_teams("bundesliga", "2024")
players = await provider.get_league_players("bundesliga", "2024")
matches = await provider.get_league_matches("bundesliga", "2024")

# 使用后关闭
await provider.close()
```

### 2. 数据缓存

```python
import json
from pathlib import Path

cache_dir = Path("data/understat_cache")
cache_dir.mkdir(exist_ok=True)

async def cached_players(provider, league, season, cache_ttl=86400):
    """缓存球员数据（24 小时）"""
    import time
    
    cache_file = cache_dir / f"{league}_{season}_players.json"
    
    if cache_file.exists():
        cache_data = json.loads(cache_file.read_text())
        if time.time() - cache_data["timestamp"] < cache_ttl:
            return cache_data["data"]
    
    # 获取新数据
    players = await provider.get_league_players(league, season)
    if players:
        json.dump({
            "timestamp": time.time(),
            "data": players
        }, cache_file.open("w"))
    
    return players
```

### 3. 批量处理多个联赛

```python
async def analyze_all_leagues():
    """分析所有联赛的 xG 数据"""
    leagues = ["EPL", "La_liga", "Bundesliga", "Serie_A", "Ligue_1"]
    season = "2024"
    
    provider = UnderstatProvider()
    
    results = {}
    for league in leagues:
        try:
            players = await provider.get_league_players(league, season)
            if players:
                top_scorers = sorted(players, key=lambda x: float(x.get('xG', 0)), reverse=True)[:10]
                results[league] = top_scorers
            await asyncio.sleep(1)  # 添加间隔
        except Exception as e:
            print(f"{league} 处理失败：{e}")
    
    return results
```

## 🔄 更新日志

### 2026-04-08 优化更新

- **功能优化** ✅:
  - ✅ `get_match_stats()`: 使用 `get_match_shots()` 和 `get_match_players()` 获取完整比赛统计
  - ✅ `get_team_stats()`: 添加 `season` 参数支持，自动获取球队球员数据
  - ✅ `get_player_stats()`: 处理 understatapi 返回的列表格式，提供多层数据结构
  - ✅ 新增 `get_player_shots()`: 获取球员射门数据
  - ✅ 新增 `get_team_stats_by_season()`: 便捷方法获取球队赛季统计

- **数据结构改进**:
  - 比赛统计：自动计算总射门数、总 xG、主队/客队射门统计
  - 球队统计：支持赛季参数，整合球队球员数据
  - 球员统计：提供 `latest_season`、`seasons`、`career_totals` 三层数据结构

- **原始测试记录**:
  - ✅ 集成 understatapi 库
  - ✅ 测试了所有主要功能
  - ✅ 更新了可用方法列表
  - ✅ 添加了实际测试数据
  - ✅ 修复了方法名问题

- **初始版本**:
  - 实现球员统计 API（JSON 格式）
  - 提供完整使用示例
  - 添加 xG 数据分析方法
  - 推荐使用 understatapi 库获取完整功能

## 🔗 外部资源

- **Understat 官网**: https://understat.com
- **understatapi PyPI**: https://pypi.org/project/understatapi/
- **xG 模型说明**: https://understat.com/about
- **测试结果**: ../test/UNDERSTAT_TEST_RESULTS.md

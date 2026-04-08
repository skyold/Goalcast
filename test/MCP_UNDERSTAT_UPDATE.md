# MCP Server 更新总结 - Understat Provider 集成

**更新日期**: 2026-04-08  
**更新内容**: 集成 Understat Provider，新增 7 个 MCP 工具

---

## 📋 更新概览

### 新增数据源

**Understat API** - 高级足球统计数据
- ✅ 完全免费
- ✅ 无需 API Key
- ✅ 专注于 xG（期望进球）、xA（期望助攻）等高级指标

### 新增 MCP 工具（7 个）

| 工具名称 | 功能 | 参数 |
|---------|------|------|
| `understat_get_league_players` | 获取联赛球员统计数据 | league, season |
| `understat_get_league_teams` | 获取联赛球队列表 | league, season |
| `understat_get_league_matches` | 获取联赛比赛结果 | league, season |
| `understat_get_match_stats` | 获取比赛详细统计 | match_id |
| `understat_get_team_stats` | 获取球队赛季统计 | team_id, season |
| `understat_get_player_stats` | 获取球员完整统计 | player_id |
| `understat_get_player_shots` | 获取球员射门数据 | player_id |

---

## 🔧 代码变更

### 1. mcp_server/server.py

#### 导入 Understat Provider
```python
from provider.understat.client import UnderstatProvider
```

#### 添加 Understat 实例管理
```python
_understat = None

def get_understat():
    global _understat
    if _understat is None:
        _understat = UnderstatProvider(use_library=True)
    return _understat
```

#### 新增 7 个工具函数
- `understat_get_league_players()` - 第 186 行
- `understat_get_league_teams()` - 第 210 行
- `understat_get_league_matches()` - 第 226 行
- `understat_get_match_stats()` - 第 242 行
- `understat_get_team_stats()` - 第 262 行
- `understat_get_player_stats()` - 第 282 行
- `understat_get_player_shots()` - 第 306 行

### 2. mcp_server/README.md

#### 更新内容
- 添加 Understat API 介绍（数据源状态部分）
- 新增 Understat 工具列表
- 添加 4 个 Understat 使用示例
- 更新最佳实践表格
- 添加相关文档链接

---

## 📊 功能详情

### 1. 联赛球员统计 (`understat_get_league_players`)

**用途**: 获取联赛所有球员的完整统计数据

**参数**:
- `league`: 联赛代码（EPL, La_liga, Bundesliga, Serie_A, Ligue_1, RFPL）
- `season`: 赛季年份（如 "2024"）

**返回数据**:
```python
[
    {
        "id": 12345,
        "player_name": "Harry Kane",
        "team_title": "Bayern Munich",
        "games": 25,
        "time": 2250,
        "goals": 26,
        "xG": 24.84,
        "xA": 5.67,
        "shots": 98,
        "shots_on_target": 56,
        "key_passes": 34,
        "xG_chain": 28.45,
        "xGBuildup": 12.34
    },
    ...
]
```

**使用示例**:
```python
players = await understat_get_league_players("Bundesliga", "2024")
top_scorers = sorted(players, key=lambda x: float(x.get('xG', 0)), reverse=True)
```

---

### 2. 联赛球队列表 (`understat_get_league_teams`)

**用途**: 获取联赛所有球队的基本信息

**参数**:
- `league`: 联赛代码
- `season`: 赛季年份

**返回数据**:
```python
[
    {
        "id": 117,
        "title": "Bayern Munich",
        "history": [...]
    },
    ...
]
```

---

### 3. 联赛比赛结果 (`understat_get_league_matches`)

**用途**: 获取联赛所有比赛的结果

**参数**:
- `league`: 联赛代码
- `season`: 赛季年份

**返回数据**:
```python
[
    {
        "id": 12345,
        "h_team": "Bayern Munich",
        "a_team": "Dortmund",
        "h_goals": 2,
        "a_goals": 1,
        "h_xG": 2.45,
        "a_xG": 1.23
    },
    ...
]
```

---

### 4. 比赛详细统计 (`understat_get_match_stats`)

**用途**: 获取比赛的详细射门数据和球员表现

**参数**:
- `match_id`: 比赛 ID（从 `understat_get_league_matches` 获取）

**返回数据**:
```python
{
    "match_id": 12345,
    "shots": [...],  # 所有射门数据
    "players": {...},  # 球员表现数据
    "total_shots": 25,
    "total_xg": 2.456,
    "home_shots": 15,
    "home_xg": 1.789,
    "away_shots": 10,
    "away_xg": 0.667
}
```

**射门数据详情**:
```python
{
    "id": 1234,
    "player_name": "Harry Kane",
    "minute": 25,
    "xG": 0.45,
    "result": "goal",
    "shot_type": "foot",
    "situation": "open_play",
    "is_goal": True
}
```

---

### 5. 球队赛季统计 (`understat_get_team_stats`)

**用途**: 获取球队在特定赛季的详细统计

**参数**:
- `team_id`: 球队 ID
- `season`: 赛季年份

**返回数据**:
```python
{
    "id": 117,
    "title": "Bayern Munich",
    "season": "2024",
    "players": [...]  # 球队球员列表和统计
}
```

---

### 6. 球员完整统计 (`understat_get_player_stats`)

**用途**: 获取球员的完整职业生涯统计

**参数**:
- `player_id`: 球员 ID

**返回数据**:
```python
{
    "player_id": 12345,
    "player_name": "Harry Kane",
    "latest_season": {...},  # 最新赛季数据
    "seasons": [...],  # 所有赛季数据列表
    "career_totals": {
        "goals": 150,
        "xG": 142.5,
        "assists": 45,
        "xA": 38.2
    },
    # 最新赛季数据也合并到顶层
    "goals": 26,
    "xG": 24.84,
    ...
}
```

---

### 7. 球员射门数据 (`understat_get_player_shots`)

**用途**: 获取球员的所有射门数据

**参数**:
- `player_id`: 球员 ID

**返回数据**:
```python
[
    {
        "id": 1234,
        "minute": 25,
        "xG": 0.45,
        "result": "goal",
        "shot_type": "foot",
        "situation": "open_play",
        "is_goal": True
    },
    ...
]
```

---

## 🎯 使用场景

### 场景 1: 分析联赛 xG 排名

```python
# 获取球员数据
players = await understat_get_league_players("EPL", "2024")

# 按 xG 排序
top_xg = sorted(players, key=lambda x: float(x.get('xG', 0)), reverse=True)[:20]

# 分析 xG vs 实际进球
for player in top_xg:
    name = player['player_name']
    xg = float(player['xG'])
    goals = int(player['goals'])
    diff = goals - xg
    print(f"{name}: {goals} goals vs {xg:.2f} xG ({diff:+.2f})")
```

---

### 场景 2: 比赛射门质量分析

```python
# 获取比赛射门数据
stats = await understat_get_match_stats(match_id=12345)

# 分析射门
print(f"总射门：{stats['total_shots']}")
print(f"总 xG: {stats['total_xg']:.2f}")

# 找出最佳机会
best_chances = sorted(stats['shots'], key=lambda x: float(x.get('xG', 0)), reverse=True)[:5]
for shot in best_chances:
    print(f"{shot['player_name']} - {shot['minute']}' - xG: {float(shot['xG']):.2f} - {shot['result']}")
```

---

### 场景 3: 球员职业生涯追踪

```python
# 获取球员完整统计
stats = await understat_get_player_stats(player_id=12345)

# 职业生涯总和
print(f"职业生涯总进球：{stats['career_totals']['goals']}")
print(f"职业生涯总 xG: {stats['career_totals']['xG']:.2f}")

# 多赛季趋势
for season in stats['seasons']:
    print(f"{season['season']}: {season['goals']} goals, {float(season['xG']):.2f} xG")
```

---

### 场景 4: 射门质量评估

```python
# 获取球员射门数据
shots = await understat_get_player_shots(player_id=12345)

# 计算各项指标
goals = sum(1 for s in shots if s.get('is_goal', False))
total_xg = sum(float(s.get('xG', 0)) for s in shots)
conversion = goals / len(shots) * 100 if shots else 0
avg_xg = total_xg / len(shots) if shots else 0

print(f"射门分析:")
print(f"  - 总射门：{len(shots)}")
print(f"  - 进球数：{goals}")
print(f"  - 总 xG: {total_xg:.2f}")
print(f"  - 转化率：{conversion:.1f}%")
print(f"  - 平均 xG: {avg_xg:.3f}")
```

---

## 📝 配置说明

### 环境变量

Understat **不需要 API Key**，无需配置环境变量。

### 依赖要求

确保已安装 understatapi 库：

```bash
pip install understatapi aiohttp beautifulsoup4 lxml
```

或更新 requirements.txt：

```bash
pip install -r requirements.txt
```

---

## 🧪 测试方法

### 快速测试

```python
# 测试基本功能
players = await understat_get_league_players("Bundesliga", "2024")
print(f"获取到 {len(players)} 名球员")

# 测试射门数据
stats = await understat_get_match_stats(match_id=12345)
print(f"获取到 {stats['total_shots']} 次射门")
```

### 完整测试

运行测试脚本：

```bash
python test/test_optimized_provider.py
```

---

## 📚 相关文档

- [Understat Skill 完整文档](../skills/understat-provider/SKILL.md)
- [Understat Provider 优化总结](../test/OBSIDIAN_SYNC_SUMMARY.md)
- [Understat Provider 代码](../provider/understat/client.py)

---

## ✅ 总结

### 新增功能

- ✅ 7 个 Understat MCP 工具
- ✅ 完整的 xG/xA 高级统计数据支持
- ✅ 无需 API Key，完全免费
- ✅ 支持 6 个主流联赛
- ✅ 球员、球队、比赛全方位数据

### 使用建议

1. **xG/xA 数据** → 使用 Understat（免费且完整）
2. **实时比分** → 使用 FootyStats
3. **积分榜** → 使用 FootyStats
4. **基础信息** → 使用 SportMonks

### 下一步

- [ ] 添加更多使用示例
- [ ] 优化数据缓存策略
- [ ] 添加数据可视化功能
- [ ] 集成到更多分析场景

---

**更新完成时间**: 2026-04-08  
**更新状态**: ✅ 完成  
**测试状态**: ⏳ 待验证

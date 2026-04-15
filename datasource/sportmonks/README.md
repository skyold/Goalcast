# Sportmonks 数据层设计

## 1. 架构概述

Sportmonks 数据层负责从预热数据中提取、转换和存储结构化的足球比赛数据，为 Goalcast 分析模型提供标准化的数据源。

### 1.1 目录结构

```
data_strategy/
├── sportmonks/
│   ├── __init__.py
│   ├── extractor.py      # 数据提取模块
│   ├── transformer.py    # 数据转换模块
│   ├── storage.py        # 数据存储模块
│   ├── models.py         # 数据模型定义
│   └── utils.py          # 工具函数
└── __init__.py
```

### 1.2 数据流

1. **数据提取**：从预热数据（JSON 文件和 SQLite 数据库）中提取原始数据
2. **数据转换**：将原始数据转换为标准化的 Python 对象
3. **数据存储**：将结构化数据存储到数据库中
4. **数据访问**：提供统一的接口供分析模型访问数据

## 2. 数据模型

### 2.1 核心实体

#### Match (比赛)
- match_id: int (主键)
- date: str (比赛日期)
- time: str (比赛时间)
- status: str (比赛状态)
- league_id: int (联赛 ID)
- league_name: str (联赛名称)
- home_team_id: int (主队 ID)
- home_team_name: str (主队名称)
- away_team_id: int (客队 ID)
- away_team_name: str (客队名称)
- home_score: int (主队进球)
- away_score: int (客队进球)
- venue_id: int (场馆 ID)
- referee_id: int (裁判 ID)

#### Team (球队)
- team_id: int (主键)
- name: str (球队名称)
- short_name: str (球队简称)
- logo: str (球队 logo URL)
- country: str (国家)

#### Player (球员)
- player_id: int (主键)
- name: str (球员名称)
- position: str (位置)
- team_id: int (所属球队 ID)
- nationality: str (国籍)
- birth_date: str (出生日期)

#### League (联赛)
- league_id: int (主键)
- name: str (联赛名称)
- country: str (国家)
- season_id: int (赛季 ID)
- season_name: str (赛季名称)

#### XGData (预期进球数据)
- match_id: int (主键)
- home_xg: float (主队预期进球)
- away_xg: float (客队预期进球)
- home_xg_against: float (主队被预期进球)
- away_xg_against: float (客队被预期进球)
- source: str (数据来源)

#### Odds (赔率数据)
- match_id: int (主键)
- home_win: float (主胜赔率)
- draw: float (平局赔率)
- away_win: float (客胜赔率)
- over_25: float (大 2.5 赔率)
- under_25: float (小 2.5 赔率)
- btts_yes: float (双方进球赔率)
- btts_no: float (双方不进球赔率)
- bookmaker: str (博彩公司)

#### TeamForm (球队状态)
- team_id: int (主键)
- match_id: int (比赛 ID)
- form_5: str (最近 5 场状态)
- form_10: str (最近 10 场状态)
- goals_for: int (进球数)
- goals_against: int (失球数)
- points: int (积分)

#### HeadToHead (交锋记录)
- id: int (主键)
- home_team_id: int (主队 ID)
- away_team_id: int (客队 ID)
- matches: int (比赛场次)
- home_wins: int (主队获胜次数)
- draws: int (平局次数)
- away_wins: int (客队获胜次数)
- home_goals: int (主队进球)
- away_goals: int (客队进球)

#### Standings (积分榜)
- id: int (主键)
- league_id: int (联赛 ID)
- team_id: int (球队 ID)
- position: int (排名)
- points: int (积分)
- matches_played: int (已赛场次)
- wins: int (胜场)
- draws: int (平局)
- losses: int (负场)
- goals_for: int (进球数)
- goals_against: int (失球数)
- goal_difference: int (净胜球)

### 2.2 关系图

```
Match ──┬──► Team (home_team)
        ├──► Team (away_team)
        ├──► League
        ├──► XGData
        ├──► Odds
        ├──► TeamForm (home)
        ├──► TeamForm (away)
        ├──► HeadToHead
        └──► Standings (home)
            └──► Standings (away)

Team ──┬──► Player
        └──► TeamForm

League ──► Standings
```

## 3. 数据提取

### 3.1 提取来源

1. **JSON 文件**：
   - `data/cache/{date}/sportmonks/matches.json`
   - `data/cache/{date}/sportmonks/extended_data.json`

2. **SQLite 数据库**：
   - `data/cache/goalcast.db`
   - 表：`raw_sportmonks_matches`, `raw_sportmonks_xg`, `raw_sportmonks_predictions`, `raw_sportmonks_head_to_head`, `raw_sportmonks_team_form`, `raw_sportmonks_standings`

### 3.2 提取策略

1. **增量提取**：只提取新的或更新的数据
2. **全量提取**：定期提取所有数据以确保完整性
3. **按需提取**：根据分析需求提取特定比赛的数据

## 4. 数据转换

### 4.1 转换规则

1. **标准化字段**：将不同来源的字段映射到标准字段
2. **数据清洗**：处理缺失值、异常值和重复数据
3. **计算派生字段**：如球队状态、交锋记录统计等
4. **数据验证**：确保数据的一致性和完整性

### 4.2 转换流程

1. 提取原始数据
2. 解析 JSON 或数据库记录
3. 映射到标准数据模型
4. 计算派生字段
5. 验证数据
6. 存储结构化数据

## 5. 数据存储

### 5.1 存储方案

1. **SQLite 数据库**：用于存储结构化数据
2. **缓存文件**：用于存储计算结果和中间数据
3. **索引**：为频繁查询的字段创建索引

### 5.2 表结构

#### `sportmonks_matches`
- match_id (INTEGER PRIMARY KEY)
- date (TEXT)
- time (TEXT)
- status (TEXT)
- league_id (INTEGER)
- league_name (TEXT)
- home_team_id (INTEGER)
- home_team_name (TEXT)
- away_team_id (INTEGER)
- away_team_name (TEXT)
- home_score (INTEGER)
- away_score (INTEGER)
- venue_id (INTEGER)
- referee_id (INTEGER)
- created_at (TIMESTAMP)
- updated_at (TIMESTAMP)

#### `sportmonks_teams`
- team_id (INTEGER PRIMARY KEY)
- name (TEXT)
- short_name (TEXT)
- logo (TEXT)
- country (TEXT)
- created_at (TIMESTAMP)
- updated_at (TIMESTAMP)

#### `sportmonks_players`
- player_id (INTEGER PRIMARY KEY)
- name (TEXT)
- position (TEXT)
- team_id (INTEGER)
- nationality (TEXT)
- birth_date (TEXT)
- created_at (TIMESTAMP)
- updated_at (TIMESTAMP)

#### `sportmonks_leagues`
- league_id (INTEGER PRIMARY KEY)
- name (TEXT)
- country (TEXT)
- season_id (INTEGER)
- season_name (TEXT)
- created_at (TIMESTAMP)
- updated_at (TIMESTAMP)

#### `sportmonks_xg`
- match_id (INTEGER PRIMARY KEY)
- home_xg (REAL)
- away_xg (REAL)
- home_xg_against (REAL)
- away_xg_against (REAL)
- source (TEXT)
- created_at (TIMESTAMP)
- updated_at (TIMESTAMP)

#### `sportmonks_odds`
- id (INTEGER PRIMARY KEY AUTOINCREMENT)
- match_id (INTEGER)
- home_win (REAL)
- draw (REAL)
- away_win (REAL)
- over_25 (REAL)
- under_25 (REAL)
- btts_yes (REAL)
- btts_no (REAL)
- bookmaker (TEXT)
- timestamp (TIMESTAMP)
- created_at (TIMESTAMP)

#### `sportmonks_team_form`
- id (INTEGER PRIMARY KEY AUTOINCREMENT)
- team_id (INTEGER)
- match_id (INTEGER)
- form_5 (TEXT)
- form_10 (TEXT)
- goals_for (INTEGER)
- goals_against (INTEGER)
- points (INTEGER)
- created_at (TIMESTAMP)

#### `sportmonks_head_to_head`
- id (INTEGER PRIMARY KEY AUTOINCREMENT)
- home_team_id (INTEGER)
- away_team_id (INTEGER)
- matches (INTEGER)
- home_wins (INTEGER)
- draws (INTEGER)
- away_wins (INTEGER)
- home_goals (INTEGER)
- away_goals (INTEGER)
- created_at (TIMESTAMP)

#### `sportmonks_standings`
- id (INTEGER PRIMARY KEY AUTOINCREMENT)
- league_id (INTEGER)
- team_id (INTEGER)
- position (INTEGER)
- points (INTEGER)
- matches_played (INTEGER)
- wins (INTEGER)
- draws (INTEGER)
- losses (INTEGER)
- goals_for (INTEGER)
- goals_against (INTEGER)
- goal_difference (INTEGER)
- season_id (INTEGER)
- created_at (TIMESTAMP)

## 6. 数据访问

### 6.1 API 接口

```python
class SportmonksDataLayer:
    def get_match(self, match_id: int) -> Match:
        """获取单场比赛数据"""
        pass
    
    def get_matches_by_date(self, date: str) -> List[Match]:
        """获取指定日期的所有比赛"""
        pass
    
    def get_matches_by_league(self, league_id: int) -> List[Match]:
        """获取指定联赛的所有比赛"""
        pass
    
    def get_team(self, team_id: int) -> Team:
        """获取球队信息"""
        pass
    
    def get_team_form(self, team_id: int, match_id: int) -> TeamForm:
        """获取球队在指定比赛时的状态"""
        pass
    
    def get_head_to_head(self, home_team_id: int, away_team_id: int) -> HeadToHead:
        """获取两队交锋记录"""
        pass
    
    def get_standings(self, league_id: int) -> List[Standings]:
        """获取联赛积分榜"""
        pass
    
    def get_xg_data(self, match_id: int) -> XGData:
        """获取比赛的 xG 数据"""
        pass
    
    def get_odds(self, match_id: int) -> List[Odds]:
        """获取比赛的赔率数据"""
        pass
```

### 6.2 缓存策略

1. **内存缓存**：缓存频繁访问的数据
2. **文件缓存**：缓存计算结果和中间数据
3. **数据库缓存**：使用 SQLite 缓存结构化数据

## 7. 性能优化

1. **索引优化**：为频繁查询的字段创建索引
2. **批量操作**：使用批量插入和更新减少数据库操作次数
3. **异步处理**：使用异步 I/O 提高数据处理速度
4. **数据压缩**：压缩存储大量历史数据

## 8. 扩展性

1. **模块化设计**：便于添加新的数据类型和处理逻辑
2. **插件架构**：支持自定义数据处理插件
3. **配置驱动**：通过配置文件调整数据处理行为
4. **监控机制**：监控数据处理的性能和质量

## 9. 总结

Sportmonks 数据层提供了一个统一、标准化的接口，用于从预热数据中提取、转换和存储结构化的足球比赛数据。它支持 Goalcast 分析模型的各种数据需求，包括比赛基本信息、球队状态、交锋记录、积分榜、xG 数据和赔率数据等。通过模块化设计和性能优化，数据层能够高效地处理大量数据，为分析模型提供及时、准确的数据支持。
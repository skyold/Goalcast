# 数据源填充计划

## 目标
使用 FootyStats API 作为唯一数据源填充 `/Users/zhengningdai/workspace/skyold/Goalcast/src/datasource` 中的数据结构。

**重要原则**：
1. 只保留 FootyStats API 提供的字段
2. 移除所有 FootyStats 没有的字段
3. 数据分类只保留：Match（比赛信息）、Odds（市场数据）、Team（队伍信息）、Standings（排名信息）
4. 移除的数据类：Elo, Weather, Injury, Lineup

---

## 1. 数据缓存机制分析

### 当前缓存实现
位置：`/Users/zhengningdai/workspace/skyold/Goalcast/src/datasource/base.py`

```python
class DataSource(ABC, Generic[T]):
    def __init__(self, providers: List[BaseProvider] = None):
        self._providers: List[BaseProvider] = providers or []
        self._cache: Dict[str, Dict[str, Any]] = {}  # 内存缓存
        self._cache_ttl: float = 30.0  # 默认30秒
```

### 缓存特点
1. **内存缓存**：使用 Python 字典存储
2. **TTL 过期机制**：每个数据源有不同的缓存时间
   - MatchDataSource: 30秒（比赛数据变化快）
   - TeamDataSource: 3600秒（1小时）
   - StandingsDataSource: 3600秒（1小时）

3. **缓存键生成**：基于参数排序生成唯一键
4. **缓存命中**：检查时间戳
5. **无持久化缓存**：重启后缓存丢失

### 缓存方法
- `_cache_key(**params)`: 生成缓存键
- `_get_from_cache(key)`: 获取缓存
- `_set_cache(key, data)`: 设置缓存
- `clear_cache()`: 清空缓存

---

## 2. types.py 数据结构精简

### Match 数据结构（只保留 FootyStats 有的）

| types.py 字段 | FootyStats API 字段 | 说明 |
|--------------|---------------------|------|
| match_id | id | 比赛 ID |
| home_team | home_name | 主队名称 |
| away_team | away_name | 客队名称 |
| home_team_id | homeID | 主队 ID |
| away_team_id | awayID | 客队 ID |
| competition | league_name | 联赛名称 |
| status | status | 比赛状态 |
| kickoff_time | date_unix | 开球时间（UNIX 时间戳） |
| home_score | homeGoalCount | 主队进球 |
| away_score | awayGoalCount | 客队进球 |
| venue | stadium_name | 场地名称 |

**移除的字段**：
- `match_type` - FootyStats 无此字段
- `first_leg_score` - FootyStats 无此字段
- `home_team_elo` / `away_team_elo` - FootyStats 无此字段
- `odds_home` / `odds_draw` / `odds_away` - 移到 Odds 类

### Odds 数据结构（与 Match 关联）

| types.py 字段 | FootyStats API 字段 | 说明 |
|--------------|---------------------|------|
| match_id | id | 关联的比赛 ID（必需） |
| home | odds_ft_1 | 主胜赔率 |
| draw | odds_ft_x | 平局赔率 |
| away | odds_ft_2 | 客胜赔率 |
| over_2_5 | odds_ft_over25 | 大2.5球赔率 |
| under_2_5 | odds_ft_under25 | 小2.5球赔率 |
| btts_yes | odds_btts_yes | 双方进球-是 |
| btts_no | odds_btts_no | 双方进球-否 |
| bookmaker | - | 留空（FootyStats 不提供） |
| timestamp | - | 留空 |

**移除的字段**：
- `home_prob`, `draw_prob`, `away_prob` - 需自行计算
- `home_prob_fair`, `draw_prob_fair`, `away_prob_fair` - 需自行计算
- `opening_odds` - FootyStats 无此字段

**设计说明**：
Odds 必须包含 match_id，用于关联比赛。示例：
```python
odds = Odds(
    match_id="12345",  # 关联到比赛
    home=1.85,
    draw=3.50,
    away=4.20
)
```

### Team 数据结构（只保留 FootyStats 有的）

| types.py 字段 | FootyStats API 字段 | 说明 |
|--------------|---------------------|------|
| team_id | team_id | 球队 ID |
| name | team_name | 球队名称 |
| xg_home | xg_for_avg_home | 主场期望进球 |
| xg_away | xg_for_avg_away | 客场期望进球 |
| xga_home | xg_against_avg_home | 主场期望失球 |
| xga_away | xg_against_avg_away | 客场期望失球 |
| shots | shotsTotal_overall | 总射门 |
| shots_on_target | shotsOnTargetTotal_overall | 射正 |
| ppg | ppg_overall | 场均积分 |
| position | league_position | 联赛排名 |
| played | played | 已赛场次 |
| won | won | 胜场 |
| drawn | drawn | 平场 |
| lost | lost | 负场 |
| goals_for | goalsFor | 进球 |
| goals_against | goalsAgainst | 失球 |
| goal_difference | goalDifference | 净胜球 |
| points | points | 积分 |
| recent_xg | xg_for_avg_overall | 场均期望进球 |
| recent_xga | xg_against_avg_overall | 场均期望失球 |
| possession | possession_overall | 控球率 |
| dangerous_attacks | dangerous_attacks_avg_overall | 危险进攻 |
| country | country | 国家 |
| founded | founded | 成立年份 |
| venue | stadium_name | 主场 |

**移除的字段**：
- `short_name` - FootyStats 无此字段
- `big_chances` - FootyStats 无此字段
- `conversion_rate` - 需自行计算
- `clean_sheet_rate` - 需自行计算
- `opp_shots` - FootyStats 无此字段
- `corners_for` / `corners_against` - FootyStats 无此字段
- `recent_form` - FootyStats 无此字段
- `ppda` - FootyStats 无此字段
- `elo` - FootyStats 无此字段
- `injuries` / `injury_details` / `suspensions` - FootyStats 无此字段
- `schedule_density_7d` - 需自行计算
- `last_match_time` - FootyStats 无此字段

### StandingsEntry 数据结构（只保留 FootyStats 有的）

| types.py 字段 | FootyStats API 字段 | 说明 |
|--------------|---------------------|------|
| position | position | 排名 |
| team_id | team_id | 球队 ID |
| team_name | team_name | 球队名称 |
| played | played | 已赛场次 |
| won | won | 胜场 |
| drawn | drawn | 平场 |
| lost | lost | 负场 |
| goals_for | goalsFor | 进球 |
| goals_against | goalsAgainst | 失球 |
| goal_difference | goalDifference | 净胜球 |
| points | points | 积分 |
| ppg | ppg_overall | 场均积分 |

**移除的字段**：
- `form` - FootyStats 无此字段
- `competition` - 需从参数传入

---

## 3. 需要移除的数据类和文件

### 移除的数据类（types.py）
- `Elo` - FootyStats 无 ELO 数据
- `Weather` - FootyStats 无天气数据
- `Injury` - FootyStats 无伤病数据
- `Lineup` - FootyStats 无阵容数据

### 移除的 DataSource 文件
- `/src/datasource/elo/` - 删除整个目录
- `/src/datasource/weather/` - 删除整个目录
- `/src/datasource/injury/` - 删除整个目录

### 移除的 Provider 文件
- `/src/provider/clubelo/` - 删除整个目录
- `/src/provider/weather/` - 删除整个目录

---

## 4. 实施步骤

### 步骤 1：更新 types.py
- 精简 Match 类，移除 FootyStats 没有的字段
- 精简 Team 类，移除 FootyStats 没有的字段
- 精简 StandingsEntry 类，移除 FootyStats 没有的字段
- 精简 Odds 类，移除计算字段
- 删除 Elo, Weather, Injury, Lineup 类
- 删除相关的枚举类（InjurySeverity 等）
- 删除辅助函数（compute_xg_adjustment, classify_player_importance）

### 步骤 2：更新 MatchDataSource
- 更新 `parse()` 方法，映射 FootyStats 字段
- 移除对其他数据源的依赖

### 步骤 3：更新 TeamDataSource
- 更新 `parse()` 方法，映射 FootyStats 字段
- 移除 `_enrich_team_data()` 方法
- 移除 `parse_understat()` 方法

### 步骤 4：更新 StandingsDataSource
- 更新 `parse()` 方法，映射 FootyStats 字段

### 步骤 5：删除不需要的文件
- 删除 `/src/datasource/elo/`
- 删除 `/src/datasource/weather/`
- 删除 `/src/datasource/injury/`
- 删除 `/src/provider/clubelo/`
- 删除 `/src/provider/weather/`

### 步骤 6：更新 registry.py
- 移除对已删除 DataSource 的引用

---

## 5. FootyStats API 端点映射

| 数据类型 | FootyStats API 端点 | Provider 方法 |
|---------|---------------------|---------------|
| Match | `/todays-matches`, `/match` | `get_todays_matches()`, `get_match_details()` |
| Team | `/team`, `/league-teams` | `get_team()`, `get_league_teams()` |
| Standings | `/league-tables` | `get_league_tables()` |

---

## 6. 注意事项

1. **字段名称差异**：FootyStats 使用下划线命名（如 `home_name`），需要正确映射
2. **数据位置**：有些数据在 `data` 数组中，有些直接在根对象
3. **缺失字段处理**：使用 `Optional` 类型，默认值为 `None`
4. **缓存策略**：保持现有缓存机制，只调整数据解析逻辑

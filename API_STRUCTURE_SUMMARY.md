# FootyStats API 数据结构快速参考

## 核心发现

通过查阅项目中的 API 文档（`footystats API document.md`），我们已经掌握了完整的 JSON 数据结构。

## API 响应通用格式

所有 API 响应遵循统一格式：

```json
{
    "success": true,
    "data": { ... },  // 或数组 [...]
    "pager": {        // 可选，分页信息
        "current_page": 1,
        "max_page": 1,
        "results_per_page": 200,
        "total_results": 2
    }
}
```

错误响应：
```json
{
    "success": false,
    "error": {
        "code": 401,
        "message": "Invalid API Key"
    }
}
```

## 关键数据字段命名规范

### 比赛数据字段
- `id` - 比赛 ID
- `homeID` / `awayID` - 球队 ID（注意大写）
- `homeGoalCount` / `awayGoalCount` - 进球数
- `team_a_corners` / `team_b_corners` - 角球数（注意 team_a/team_b 格式）
- `team_a_shotsOnTarget` / `team_b_shotsOnTarget` - 射正
- `team_a_possession` / `team_b_possession` - 控球率
- `odds_ft_1` / `odds_ft_x` / `odds_ft_2` - 赔率（1=主胜，x=平，2=客胜）
- `btts` - 双方进球（bool）
- `over25` - 大球 2.5（bool）

### 球队数据字段
- `team_id` / `team_name` - 球队 ID/名称
- `goalsFor` / `goalsAgainst` - 进球/失球（注意驼峰）
- `goalDifference` - 净胜球
- `home_record` / `away_record` - 主客场记录（对象）
- `seasonWinsNum_overall` - 胜场（lastx 端点）
- `seasonCSPercentage_overall` - 零封百分比

### 球员数据字段
- `full_name` - 全名
- `minutes_played_overall` - 出场分钟
- `appearances_overall` - 出场次数
- `goals_overall` / `assists_overall` - 进球/助攻

## 字段别名处理策略

由于 API 字段命名不规范（混合使用 snake_case 和 camelCase），**必须使用 Pydantic 的 alias 功能**：

```python
from pydantic import BaseModel, Field

class Match(BaseModel):
    id: str
    home_team_id: str = Field(alias="homeID")
    away_team_id: str = Field(alias="awayID")
    home_goals: Optional[int] = Field(None, alias="homeGoalCount")
    team_a_possession: Optional[float] = Field(None, alias="team_a_possession")
    
    class Config:
        populate_by_name = True  # 支持使用字段名或别名
```

## 数据结构层次

### 1. 比赛列表端点 (`/todays-matches`, `/league-matches`)
```
{
  "success": true,
  "pager": {...},
  "data": [
    {
      "id": 579362,
      "homeID": 155,
      "awayID": 93,
      "season": "2019/2020",
      "status": "incomplete",
      "homeGoalCount": 0,
      "awayGoalCount": 0,
      "team_a_corners": -1,
      "odds_ft_1": 8.75,
      ...
    }
  ]
}
```

### 2. 比赛详情端点 (`/match`)
```
{
  "success": true,
  "pager": {...},
  "data": {
    "id": 579101,
    "homeID": 251,
    "awayID": 145,
    "status": "complete",
    "homeGoalCount": 3,
    "awayGoalCount": 0,
    "lineups": {...},      // 阵容
    "h2h": {...},          // 交锋记录
    "odds_comparison": {...}, // 赔率对比
    "weather": {...},      // 天气
    ...
  }
}
```

### 3. 球队详情端点 (`/team`)
```
{
  "success": true,
  "data": {
    "team_id": 1,
    "team_name": "Manchester City",
    "league": "Premier League",
    "played": 38,
    "wins": 26,
    "draws": 3,
    "losses": 9,
    "goalsFor": 102,
    "goalsAgainst": 35,
    "points": 81,
    "position": 2,
    "form": "WWLWW",
    "home_record": {...},
    "away_record": {...}
  }
}
```

### 4. 球队近况端点 (`/lastx`)
```
{
  "success": true,
  "pager": {...},
  "data": [
    {
      "id": 59,
      "name": "Arsenal",
      "last_x_match_num": 5,
      "stats": {
        "seasonWinsNum_overall": 4,
        "seasonDrawsNum_overall": 1,
        "seasonLossesNum_overall": 0,
        "seasonGoalsTotal_overall": 9,
        "seasonCSPercentage_overall": 80,
        ...
      }
    }
  ]
}
```

### 5. 联赛积分榜端点 (`/league-tables`)
```
{
  "success": true,
  "data": {
    "all_matches_table_overall": [...],
    "all_matches_table_home": [...],
    "all_matches_table_away": [...],
    "specific_tables": [
      {
        "round": "Group Stage",
        "groups": [
          {
            "name": "Group A",
            "table": [...]
          }
        ]
      }
    ]
  }
}
```

## Parser 实现要点

### 1. 处理字段别名
```python
def parse_match(self, raw: Dict) -> Match:
    data = raw.get("data", raw)
    return Match(
        id=str(data.get("id", "")),
        home_team_id=str(data.get("homeID", "")),
        away_team_id=str(data.get("awayID", "")),
        home_goals=data.get("homeGoalCount"),
        # ...
    )
```

### 2. 处理嵌套结构
```python
def parse_team(self, raw: Dict) -> Team:
    data = raw.get("data", raw)
    
    # 处理主场/客场记录
    home_record = None
    if "home_record" in data:
        hr = data["home_record"]
        home_record = TeamRecord(
            played=hr.get("played", 0),
            wins=hr.get("wins", 0),
            ...
        )
    
    return Team(
        team_id=data.get("team_id"),
        team_name=data.get("team_name"),
        home_record=home_record,
        ...
    )
```

### 3. 处理 lastx 的多重统计
```python
def parse_lastx(self, raw: Dict) -> List[LastXData]:
    data_list = raw.get("data", [])
    results = []
    
    for item in data_list:
        last_x_num = item.get("last_x_match_num")
        stats = item.get("stats", {})
        
        result = LastXData(
            team_id=item.get("id"),
            team_name=item.get("name"),
            matches_count=last_x_num,
            wins=stats.get("seasonWinsNum_overall", 0),
            draws=stats.get("seasonDrawsNum_overall", 0),
            ...
        )
        results.append(result)
    
    return results
```

## 实施建议

### 优先级 1：核心端点
1. **比赛详情** (`/match`) - 最复杂，包含阵容、赔率等
2. **球队详情** (`/team`) - 包含主客场记录
3. **联赛比赛** (`/league-matches`) - 大量数据

### 优先级 2：统计端点
4. **球队近况** (`/lastx`) - 特殊的多重统计结构
5. **联赛积分榜** (`/league-tables`) - 嵌套结构
6. **联赛球队** (`/league-teams`) - 基础统计

### 优先级 3：其他端点
7-16. 球员、裁判、BTTS、Over 2.5 等

## 下一步行动

1. ✅ **已完成**: 查阅 API 文档，了解 JSON 结构
2. ✅ **已完成**: 更新 spec.md 中的模型定义
3. 🔄 **进行中**: 创建基于真实 API 的 Parser
4. ⏳ **待开始**: 实现缓存机制

## 关键代码示例

### 完整 Parser 示例
```python
from provider.footystats.models import Match, MatchResponse, FootyStatsMeta
from datetime import datetime

class FootyStatsParser:
    def parse_match_details(self, raw: Dict) -> Optional[MatchResponse]:
        if not raw or not raw.get("success"):
            return None
        
        data = raw.get("data", {})
        
        try:
            match = Match(
                id=str(data.get("id", "")),
                season=data.get("season", ""),
                status=data.get("status", "incomplete"),
                home_team_id=str(data.get("homeID", "")),
                away_team_id=str(data.get("awayID", "")),
                home_goals=data.get("homeGoalCount"),
                away_goals=data.get("awayGoalCount"),
                home_corners=data.get("team_a_corners"),
                away_corners=data.get("team_b_corners"),
                home_possession=data.get("team_a_possession"),
                away_possession=data.get("team_b_possession"),
                odds_home=data.get("odds_ft_1"),
                odds_draw=data.get("odds_ft_x"),
                odds_away=data.get("odds_ft_2"),
                btts=data.get("btts"),
                over_2_5=data.get("over25"),
                # 高级数据
                lineups=data.get("lineups"),
                h2h=data.get("h2h"),
                odds_comparison=data.get("odds_comparison"),
                raw_data=data,
            )
            
            return MatchResponse(
                data=match,
                meta=FootyStatsMeta(
                    endpoint="/match",
                    timestamp=datetime.now(),
                ),
                raw_data=raw
            )
        except Exception as e:
            logger.error(f"Error parsing match: {e}")
            return None
```

## 参考资料

- 完整 API 文档：`src/provider/footystats/footystats API document.md`
- 使用示例：`src/provider/footystats/README.md`
- 规范文档：`spec.md`
- 任务分解：`tasks.md`
- 检查清单：`checklist.md`

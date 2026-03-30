---
name: footystats
description: "【仅用于调试和原始 API 探索】直接通过 curl 调用 FootyStats API 获取原始数据。正式赛程查询请使用 goalcast-schedule，正式比赛分析请使用 goalcast-analyze。仅在以下场景触发：
- 调试 API 响应或探索原始数据结构
- 查看球队/球员/裁判的原始历史数据
- 获取联赛积分榜、BTTS、Over 2.5 等统计原始值
- 用户明确要求'直接调 API'或'查原始数据'"
---

# FootyStats Skill

> **注意**：本技能仅适用于 API 调试和原始数据探索。
> 查看赛程请使用 `goalcast-schedule` 技能；进行比赛量化分析请使用 `goalcast-analyze` 技能。

基于 FootyStats API，通过 curl 直接调用，无需 Python 依赖。

## API Key 配置

**方式 1: 环境变量（推荐）**

```bash
export FOOTYSTATS_API_KEY="your_api_key_here"
```

**方式 2: 直接传入**

```bash
API_KEY="your_api_key_here"
curl -s "https://api.football-data-api.com/todays-matches?key=$API_KEY"
```

**方式 3: 从 .env 文件读取**

```bash
API_KEY=$(grep FOOTYSTATS_API_KEY .env | cut -d'=' -f2 | tr -d ' ')
```

**获取 API Key**: 访问 https://footystats.org/api/ 注册获取

---

## 快速查询

### 今日比赛

```bash
API_KEY="${FOOTYSTATS_API_KEY:-your_default_key}"
curl -s "https://api.football-data-api.com/todays-matches?key=$API_KEY"
```

### 指定日期比赛

```bash
curl -s "https://api.football-data-api.com/todays-matches?key=$API_KEY&date=2024-01-15"
```

### 联赛列表

```bash
curl -s "https://api.football-data-api.com/league-list?key=$API_KEY"
```

---

## 球队数据

### 球队详情

```bash
curl -s "https://api.football-data-api.com/team?key=$API_KEY&team_id=59"
```

### 球队近况（最近 5/6/10 场）

```bash
curl -s "https://api.football-data-api.com/lastx?key=$API_KEY&team_id=59"
```

### 联赛球队列表

```bash
curl -s "https://api.football-data-api.com/league-teams?key=$API_KEY&season_id=2012"
```

---

## 联赛数据

### 联赛积分榜

```bash
curl -s "https://api.football-data-api.com/league-tables?key=$API_KEY&season_id=2012"
```

### 联赛比赛列表

```bash
curl -s "https://api.football-data-api.com/league-matches?key=$API_KEY&season_id=2012"
```

### 联赛统计

```bash
curl -s "https://api.football-data-api.com/league-season?key=$API_KEY&season_id=2012"
```

---

## 比赛详情

### 单场比赛详情

```bash
curl -s "https://api.football-data-api.com/match?key=$API_KEY&match_id=579101"
```

---

## 统计数据

### BTTS（双方进球）统计

```bash
curl -s "https://api.football-data-api.com/stats-data-btts?key=$API_KEY"
```

### Over 2.5（大球）统计

```bash
curl -s "https://api.football-data-api.com/stats-data-over25?key=$API_KEY"
```

---

## 数据解析

### 今日比赛完整查询（含联赛名称）

```bash
#!/bin/bash
API_KEY="${FOOTYSTATS_API_KEY}"

# 获取联赛映射
LEAGUE_RESP=$(curl -s "https://api.football-data-api.com/league-list?key=$API_KEY")
echo "$LEAGUE_RESP" > /tmp/leagues.json

# 获取今日比赛
curl -s "https://api.football-data-api.com/todays-matches?key=$API_KEY" | python3 -c '
import sys, json
from datetime import datetime

data = json.load(sys.stdin)
leagues = json.load(open("/tmp/leagues.json"))

# 构建联赛映射
league_map = {}
for l in leagues.get("data", []):
    for s in l.get("season", []):
        league_map[s["id"]] = l["name"]

# 输出比赛
for m in data.get("data", []):
    ts = m.get("date_unix", 0)
    t = datetime.fromtimestamp(ts).strftime("%H:%M") if ts else "TBD"
    league = league_map.get(m.get("competition_id"), f"ID:{m.get(competition_id)}")
    print(f"{t} | {league} | {m[\"home_name\"]} vs {m[\"away_name\"]}")
'
```

### 常用字段说明

| 字段 | 说明 |
|------|------|
| `date_unix` | UNIX 时间戳，需 `datetime.fromtimestamp()` 转换 |
| `competition_id` | 联赛 ID，需关联 league-list 获取名称 |
| `home_name` / `away_name` | 球队名称（直接可用） |
| `season` | 赛季，如 "2024" |
| `status` | 比赛状态：complete/incomplete/suspended |

---

## API 端点速查

| 端点 | URL | 用途 |
|------|-----|------|
| `/todays-matches` | `?key=$KEY` | 今日比赛 |
| `/league-list` | `?key=$KEY` | 联赛列表 |
| `/league-season` | `?key=$KEY&season_id=X` | 联赛统计 |
| `/league-teams` | `?key=$KEY&season_id=X` | 联赛球队 |
| `/league-matches` | `?key=$KEY&season_id=X` | 联赛比赛 |
| `/league-tables` | `?key=$KEY&season_id=X` | 联赛积分榜 |
| `/team` | `?key=$KEY&team_id=X` | 球队详情 |
| `/lastx` | `?key=$KEY&team_id=X` | 球队近况 |
| `/match` | `?key=$KEY&match_id=X` | 比赛详情 |
| `/stats-data-btts` | `?key=$KEY` | BTTS 统计 |
| `/stats-data-over25` | `?key=$KEY` | Over 2.5 统计 |
| `/country-list` | `?key=$KEY` | 国家列表 |
| `/league-players` | `?key=$KEY&season_id=X` | 联赛球员 |
| `/league-referees` | `?key=$KEY&season_id=X` | 联赛裁判 |
| `/player-stats` | `?key=$KEY&player_id=X` | 球员详情 |
| `/referee` | `?key=$KEY&referee_id=X` | 裁判详情 |

---

## 典型场景

### 查询英超积分榜

```bash
# 1. 获取英超 season_id
curl -s "https://api.football-data-api.com/league-list?key=$API_KEY" | \
  jq '.data[] | select(.name | contains("Premier")) | .season[0].id'

# 2. 用获取的 ID 查询积分榜
curl -s "https://api.football-data-api.com/league-tables?key=$API_KEY&season_id=2012"
```

### 分析阿森纳近期表现

```bash
curl -s "https://api.football-data-api.com/team?key=$API_KEY&team_id=59"
curl -s "https://api.football-data-api.com/lastx?key=$API_KEY&team_id=59"
```

### 查看今日 BTTS 热门

```bash
curl -s "https://api.football-data-api.com/stats-data-btts?key=$API_KEY" | jq '.data.top_teams'
```

---

## 注意事项

1. API Key 必须有效才能调用
2. 每小时有请求限制（约 1800 次）
3. 返回数据量大的端点支持分页：`&page=1&max_per_page=500`
4. 球员/裁判 ID 可通过联赛数据获取
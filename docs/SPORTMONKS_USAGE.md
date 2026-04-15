# Sportmonks API v3 Football Provider 深度使用指南

`SportmonksProvider` 完整实现了 Sportmonks API v3 Football 的核心端点。本指南旨在详细说明每个功能模块的业务逻辑、核心指标（Type IDs）、包含选项（Includes）及订阅限制。

---

## 🏗️ 全局核心概念

在深入具体端点之前，理解 Sportmonks 3.0 的三个核心机制至关重要：

### 1. 灵活的包含机制 (Includes)
Sportmonks 采用“实体-关联”模型。大多数端点支持 `include` 参数，允许您在一次请求中获取关联数据（如比赛详情中包含球队、进球、阵容）。
- **用法**: `include=participants,goals,lineups`
- **嵌套包含**: 支持深度包含，如 `include=lineups.player`（获取阵容及每个球员的详细信息）。

### 2. 统一的类型系统 (Type System)
指标数据（统计、期望数据、事件等）通过 `type_id` 区分。每个 `type_id` 对应一个具体的业务含义。
- **查询**: 使用 `get_types()` 获取所有可用的类型定义。
- **过滤**: 许多端点支持通过类型 ID 过滤返回结果。

### 3. 分页处理 (Pagination)
所有返回列表的端点均支持分页。
- **参数**: `page` (页码), `per_page` (每页数量，通常上限 50)。
- **响应**: 包含 `pagination` 对象，指示 `has_more` 和 `current_page`。

---

## 🚀 功能模块详解

### 1. 比赛状态与实时数据 (Livescores & States)
监控比赛从“未开始”到“已结束”的全生命周期。

- **核心端点**: `get_livescores()`, `get_livescores_inplay()`, `get_states()`
- **关键状态码 (State IDs)**:
    - `1` (NS): 未开始 (Not Started)
    - `2` (LIVE): 第一半场 (1st Half)
    - `3` (HT): 中场休息 (Half Time)
    - `22` (LIVE): 第二半场 (2nd Half)
    - `5` (FT): 完场 (Full Time)
    - `10` (POSTP): 推迟 (Postponed)
- **推荐包含**: `include=scores,events,statistics`
- **计划限制**: 实时数据 (Inplay) 通常需要 Standard 或更高计划。

### 2. 期望数据 (Expected Data - xG) ⭐
基于统计模型评估进球质量和表现。

- **核心端点**: `get_expected_by_fixture()`, `get_expected_by_team()`, `get_expected_by_player()`
- **核心指标 (Type IDs)**:
    - `5304`: **Expected Goals (xG)** - 总进球期望。
    - `5305`: **xG On Target (xGOT)** - 射正进球期望。
    - `7943`: **Non-Penalty xG (npxG)** - 非点球期望进球。
    - `7939`: **Expected Points (xPTS)** - 期望积分。
    - `9685`: **Shooting Performance** - 射门表现（xGOT vs xG）。
- **业务价值**: 用于判断球队是“实至名归”还是“运气使然”。

### 3. 高级预期阵容 (Premium Expected Lineups) ⭐
在比赛开始前预测首发阵容及阵型。

- **核心端点**: `get_expected_lineup_by_team()`, `get_expected_lineups_by_player()`
- **数据层级**: 包含球员位置、预计阵型（Formation）及首发概率。
- **计划限制**: 属于高级插件，通常在赛前 24-48 小时开始提供更新。

### 4. 统计数据 (Statistics)
覆盖球队和球员的深度表现指标。

- **核心端点**: `get_season_statistics_by_participant()`, `get_round_statistics()`
- **常用指标 (Type IDs)**:
    - `34`: 角球 (Corners)
    - `42`: 总射门 (Shots Total)
    - `45`: 控球率 (Ball Possession %)
    - `80`: 传球总数 (Passes)
    - `86`: 射正次数 (Shots on Target)
    - `118`: 球员评分 (Rating)
- **推荐包含**: `include=type` (获取指标名称)

### 5. 赛程安排与赛程表 (Schedules & Fixtures) ⭐
这是追踪球队比赛计划、历史赛绩以及未来赛程的核心模块。

- **核心端点**: 
    - `get_fixtures(page=1, filters="leagues:8,501")`: 获取全量赛程，支持通过 `filters` 参数过滤特定联赛（多个 ID 用逗号分隔）。
    - `get_schedules_by_team(team_id)`: 获取特定球队的完整赛程安排。
    - `get_schedules_by_season(season_id)`: 获取特定赛季的完整赛程表。
    - `get_fixtures_between(start_date, end_date)`: 获取特定时间段内的所有比赛。
    - `get_fixtures_by_date(date)`: 获取特定日期的所有比赛。
- **业务场景**:
    - **双线作战分析**: 通过 `get_schedules_by_team` 检查球队是否在 7 天内有 3 场比赛（如周中欧冠 + 周末联赛），这通常意味着体能透支，是下注“冷门”或“小球”的重要参考。
    - **未来赛程难度 (SOS)**: 观察球队未来 5 场的对手排名。如果接连面对前 4 名，球队可能会在当前比赛中“战略性放弃”或保留实力。
- **推荐包含**: `include=league,participants,venue`

### 6. 赔率与市场 (Odds & Markets)
提供全球 100+ 博彩公司的实时和历史赔率。

- **核心端点**: `get_prematch_odds_by_fixture()`, `get_inplay_odds_by_fixture()`, `get_markets()`
- **博彩公司 (Bookmakers)**:
    - **获取 ID**: 使用 `get_bookmakers()` 获取全量列表，或 `get_bookmakers_by_search("bet365")` 搜索特定公司。
    - **常用博彩公司 ID**:
        - `2`: **Bet365** (最常用)
        - `18`: **Pinnacle** (平博，高胜率参考)
        - `1`: **Bwin**
        - `11`: **William Hill**
        - `15`: **Betfair** (必发)
        - `97`: **Unibet**
        - `14`: **Marathonbet**
    - **指定公司获取赔率**: 
        - 使用特定接口: `get_prematch_odds_by_fixture_and_bookmaker(fixture_id, 2)`
        - 使用过滤器 (Filters): 在请求比赛列表时，通过 `include=odds&filters=bookmakers:2,18` 仅获取指定公司的赔率。
- **主要盘口 (Market IDs)**:
    - `1`: 全场胜平负 (Fulltime Result / 1X2)
    - `12`: 进球大小球 (Over/Under)
    - `28`: 亚洲让球 (Asian Handicap)
    - `63`: 双重机会 (Double Chance)
- **计划限制**: 赔率数据通常作为独立扩展包订阅。

### 6. 高级赔率与初盘监控 (Premium Odds) ⭐
Premium Odds Feed 记录了赔率从开盘到结束的**完整变动历史**，是获取“初盘”的唯一官方途径。

- **核心端点**: `get_premium_odds_by_fixture()`, `get_premium_odds_updated_between()`
- **初盘获取逻辑**:
    - 调用 `get_premium_odds_by_fixture(fixture_id)` 获取该场比赛的所有赔率流水。
    - 针对每个 `market_id` 和 `bookmaker_id` 组合，时间戳 `created_at` 最早的那条记录即为该博彩公司的**初盘**。
- **数据保留**: 高级赔率数据在比赛结束后仍保留 **7 天**。
- **监控新开盘**: 使用 `get_premium_odds_updated_between(start_ts, end_ts)` 轮询过去 5 分钟内产生变动（含新开盘）的赔率。

### 7. 预测数据 (Predictions)
Sportmonks 基于历史数据和 xG 模型生成的概率预测。

- **核心端点**: `get_probabilities_by_fixture()`, `get_value_bets()`
- **常用预测类型 (Type IDs)**:
    - `231`: 全场胜平负概率 (1X2)
    - `235`: 2.5 进球大小概率 (O/U 2.5)
    - `231`: 双方进球概率 (BTTS)
    - `240`: 精确比分概率 (Correct Score)
- **业务逻辑**: `value_bets` 端点会自动筛选“模型概率 > 市场赔率暗示概率”的投注项。

### 7. 积分榜与排名 (Standings & Rankings)
详细的联赛排名、主客场表现及历史趋势。

- **核心端点**: `get_standings_by_season()`, `get_standings_live_by_league()`, `get_team_rankings()`
- **积分榜类型**:
    - `Total`: 总积分榜。
    - `Home/Away`: 主客场专项积分榜。
- **推荐包含**: `include=participant,form` (包含球队详情及近期 5 场走势)。

### 8. 联赛同步与本地过滤 (League Sync & Local Filtering) ⭐
为了提高查询效率并支持按名称过滤，系统支持将 Sportmonks 的全量联赛数据持久化到本地。

- **核心功能**:
    - **全量同步**: 使用 `goalcast_sportmonks_sync_leagues` 工具将 API 中的所有联赛（ID、名称、国家、简称等）保存到本地 `data/cache/sportmonks/leagues.json`。
    - **名称查找**: 使用 `goalcast_sportmonks_get_leagues_by_name(name="Premier League")` 在本地索引中进行模糊搜索。
- **业务场景**:
    - **动态过滤**: 在调用 `get_fixtures` 或 `get_todays_matches` 时，您可以直接传入联赛名称（如 `leagues=["Premier League", "Serie A"]`）。系统会自动匹配本地索引中的 ID 并进行过滤。
    - **ID 转换**: 如果您只有联赛名称，可以先通过同步后的索引找到对应的 `league_id`，再进行精确查询。
- **最佳实践**: 建议每周运行一次同步工具，以确保本地联赛列表（包括新赛季升降级联赛）是最新的。

---

## 💰 下注实战指南 (Betting Insights)

基于本 Provider 提供的数据，您可以构建以下下注策略：

### 1. 利用“主客场积分榜”发现冷门
**逻辑**：总积分榜往往掩盖了球队对主场的依赖。
- **策略**：对比 `Total` 和 `Home/Away` 积分榜。若强队客场排名极低（客场虫），而对手主场稳健，则是下注“主队不败”的良机。

### 2. 利用 `form` 识别战力拐点
**逻辑**：积分榜具有滞后性，近期 5 场走势更能反映真实战力。
- **策略**：监控顶级球队的连败。若处于低迷期且核心球员缺阵，其下场比赛的胜赔往往仍因“名气”被低估，适合下注其对面或大球。

### 3. 利用“实时积分榜”进行走地投注
**逻辑**：比赛后期的动力源于积分榜压力。
- **策略**：若实时积分为平局，且这一分足以让两队保级/夺冠，最后 15 分钟“小球”概率极大。反之，若某队必须赢球才能保级，80 分钟后必全线压上，适合追“绝杀”或“大球”。

### 4. 利用初盘变动 (Premium Odds) 洞察内幕
**逻辑**：初盘反映了博彩公司的原始信心，后续变动反映了资金流向和内幕消息。
- **策略**：通过 `get_premium_odds_by_fixture()` 追溯初盘。若某队初盘极低但临场赔率大幅升高（升水），通常意味着该队主力突然缺阵或信心不足。

---

## 🛠️ 代码调用示例

### 获取单场比赛的深度分析数据 (xG + 统计 + 赔率)
```python
from provider.sportmonks.client import SportmonksProvider

async def analyze_match(fixture_id):
    provider = SportmonksProvider()
    
    # 1. 获取比赛基础信息及统计
    match = await provider.get_fixture_by_id(
        fixture_id, 
        include="participants,statistics,scores"
    )
    
    # 2. 获取该场比赛的 xG 数据
    xg_data = await provider.get_expected_by_fixture(fixture_id)
    
    # 3. 获取主要博彩公司的赔率 (如 bet365, ID: 2)
    odds = await provider.get_prematch_odds_by_fixture_and_bookmaker(
        fixture_id, 
        bookmaker_id=2
    )
    
    return {
        "match": match,
        "xg": xg_data,
        "odds": odds
    }
```

---

## ⚠️ 常见问题与注意事项

1. **数据更新延迟**:
    - 免费/基础计划的 xG 数据通常延迟 12 小时提供。
    - 实时比分在基础计划中可能有 1-5 分钟延迟。
2. **Include 限制**:
    - 单次请求的 `include` 实体数量过多可能导致请求变慢或被系统截断（建议不超过 5-8 个）。
3. **空响应处理**:
    - 如果您的计划不包含某个端点，API 可能返回 `403 Forbidden` 或空的 `data` 数组。请务必检查响应中的 `subscription` 对象以确认权限。

---

## 📚 更多资源
- [官方详细文档](https://docs.sportmonks.com/v3/)
- [完整端点列表](https://docs.sportmonks.com/v3/endpoints-and-entities/endpoints)

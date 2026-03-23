# Goalcast Collectors 重构验证清单

**版本**: 1.0  
**创建日期**: 2026-03-22  
**参考规范**: [refactor_collectors_spec.md](./refactor_collectors_spec.md)

---

## Phase 1: 基础设施

### Task 1.1: Provider 基类

- [ ] 文件创建
  - [ ] `src/provider/__init__.py` 存在
  - [ ] `src/provider/base.py` 存在

- [ ] `BaseProvider` 类定义
  - [ ] `BASE_URL` 类属性
  - [ ] `DEFAULT_TIMEOUT` 类属性
  - [ ] `__init__(api_key, timeout)` 构造函数
  - [ ] `name` 抽象属性
  - [ ] `is_available()` 抽象方法
  - [ ] `_request(endpoint, params, headers)` 方法

- [ ] HTTP 请求功能
  - [ ] 使用 `httpx.AsyncClient`
  - [ ] 支持自定义超时
  - [ ] 支持自定义 headers
  - [ ] 返回 `Optional[Dict[str, Any]]`

- [ ] 重试逻辑
  - [ ] 最多重试 3 次
  - [ ] 指数退避等待
  - [ ] 429 状态码特殊处理
  - [ ] 5xx 状态码重试

- [ ] 单元测试
  - [ ] 测试正常请求
  - [ ] 测试超时处理
  - [ ] 测试重试逻辑
  - [ ] 测试错误处理

---

### Task 1.2: DataSource 基类

- [ ] 文件创建
  - [ ] `src/datasource/__init__.py` 存在
  - [ ] `src/datasource/base.py` 存在

- [ ] `DataCapability` 数据类
  - [ ] `type: DataSourceType` 字段
  - [ ] `name: str` 字段
  - [ ] `description: str` 字段
  - [ ] `providers: List[str]` 字段
  - [ ] `params: Dict[str, str]` 字段
  - [ ] `update_freq: float` 字段
  - [ ] `historical: bool` 字段
  - [ ] `realtime: bool` 字段

- [ ] `DataSource` 泛型类
  - [ ] `__init__(providers)` 构造函数
  - [ ] `data_type` 抽象属性
  - [ ] `capabilities()` 抽象方法
  - [ ] `fetch(**params)` 抽象方法
  - [ ] `parse(raw_data)` 抽象方法
  - [ ] `is_available()` 方法

- [ ] 缓存逻辑
  - [ ] `_cache` 字典存储
  - [ ] `_cache_ttl` 配置
  - [ ] `_cache_key(**params)` 方法
  - [ ] 缓存命中检查
  - [ ] 缓存更新

- [ ] Provider 回退逻辑
  - [ ] 遍历 `_providers` 列表
  - [ ] 捕获异常继续下一个
  - [ ] 返回第一个成功结果

- [ ] 单元测试
  - [ ] 测试缓存命中
  - [ ] 测试缓存过期
  - [ ] 测试 Provider 回退
  - [ ] 测试所有 Provider 失败

---

### Task 1.3: 标准数据类型

- [ ] 文件创建
  - [ ] `src/datasource/types.py` 存在

- [ ] 枚举类型
  - [ ] `DataSourceType` 枚举
    - [ ] `MATCH = "match"`
    - [ ] `TEAM = "team"`
    - [ ] `STANDINGS = "standings"`
    - [ ] `ODDS = "odds"`
    - [ ] `ELO = "elo"`
    - [ ] `WEATHER = "weather"`
  - [ ] `MatchType` 枚举
    - [ ] `LEAGUE = "A"`
    - [ ] `CUP = "B"`
    - [ ] `TWO_LEG = "C"`
    - [ ] `CRUCIAL = "D"`
  - [ ] `MatchStatus` 枚举
    - [ ] `SCHEDULED`, `LIVE`, `FINISHED`, `POSTPONED`, `CANCELLED`

- [ ] `Match` 数据类
  - [ ] `match_id: str` 必填
  - [ ] `home_team: str` 必填
  - [ ] `away_team: str` 必填
  - [ ] `competition: str`
  - [ ] `match_type: MatchType`
  - [ ] `status: MatchStatus`
  - [ ] `kickoff_time: Optional[datetime]`
  - [ ] `home_score`, `away_score`
  - [ ] `odds_home`, `odds_draw`, `odds_away`

- [ ] `Team` 数据类
  - [ ] `team_id: str` 必填
  - [ ] `name: str` 必填
  - [ ] `xg_home`, `xg_away`, `xga_home`, `xga_away`
  - [ ] `ppg`, `position`, `played`, `won`, `drawn`, `lost`
  - [ ] `recent_form: List[str]`
  - [ ] `possession`, `ppda`
  - [ ] `elo: Optional[float]`
  - [ ] `injuries: List[str]`

- [ ] `StandingsEntry` 数据类
  - [ ] `position`, `team_id`, `team_name` 必填
  - [ ] `played`, `won`, `drawn`, `lost`
  - [ ] `goals_for`, `goals_against`, `goal_difference`, `points`
  - [ ] `ppg: Optional[float]`

- [ ] `Odds` 数据类
  - [ ] `home`, `draw`, `away` 必填
  - [ ] `bookmaker`, `timestamp`
  - [ ] `home_prob`, `draw_prob`, `away_prob`

- [ ] `Elo` 数据类
  - [ ] `team_name`, `elo` 必填
  - [ ] `date`, `rank`

- [ ] `Weather` 数据类
  - [ ] `condition`, `wind_speed`, `rain_1h` 必填
  - [ ] `temperature`
  - [ ] `xg_adjustment`

- [ ] 单元测试
  - [ ] 测试所有数据类实例化
  - [ ] 测试枚举值
  - [ ] 测试默认值

---

### Task 1.4: 数据源注册表

- [ ] 文件创建
  - [ ] `src/datasource/registry.py` 存在

- [ ] `DataRegistry` 类
  - [ ] 单例模式实现
  - [ ] `_data_sources: Dict[DataSourceType, List[DataSource]]` 存储

- [ ] 方法实现
  - [ ] `register(datasource)` 方法
  - [ ] `get(dtype) -> Optional[DataSource]` 方法
  - [ ] `get_all(dtype) -> List[DataSource]` 方法
  - [ ] `capabilities() -> Dict[DataSourceType, DataCapability]` 方法

- [ ] 全局实例
  - [ ] `registry = DataRegistry()` 导出

- [ ] 单元测试
  - [ ] 测试单例模式
  - [ ] 测试注册功能
  - [ ] 测试获取功能
  - [ ] 测试能力查询

---

## Phase 2: Provider 迁移

### Task 2.1: FootyStats Provider

- [ ] 文件创建
  - [ ] `src/provider/footystats/__init__.py` 存在
  - [ ] `src/provider/footystats/client.py` 存在

- [ ] `FootyStatsProvider` 类
  - [ ] 继承 `BaseProvider`
  - [ ] `BASE_URL = "https://api.football-data-api.com"`
  - [ ] `name` 属性返回 `"footystats"`
  - [ ] `is_available()` 检查 API key

- [ ] API 方法
  - [ ] `get_team(team_id)` 返回原始 JSON
  - [ ] `get_match(match_id)` 返回原始 JSON
  - [ ] `get_league_matches(league_id, date)` 返回原始 JSON
  - [ ] `get_league_table(league_id, season_id)` 返回原始 JSON

- [ ] 移除内容
  - [ ] 无缓存逻辑
  - [ ] 无解析逻辑
  - [ ] 无 `rate_limiter` 调用（由 DataSource 负责）

- [ ] 测试文件
  - [ ] `tests/test_provider/test_footystats.py` 存在
  - [ ] 测试所有 API 方法
  - [ ] 使用 mock HTTP 响应

---

### Task 2.2: Football-Data Provider

- [ ] 文件创建
  - [ ] `src/provider/football_data/__init__.py` 存在
  - [ ] `src/provider/football_data/client.py` 存在

- [ ] `FootballDataProvider` 类
  - [ ] 继承 `BaseProvider`
  - [ ] `BASE_URL = "https://api.football-data.org/v4"`
  - [ ] `name` 属性返回 `"football_data"`
  - [ ] `is_available()` 检查 API key
  - [ ] `X-Auth-Token` header 认证

- [ ] API 方法
  - [ ] `get_matches(competition, date_from, date_to)` 返回原始 JSON
  - [ ] `get_standings(competition)` 返回原始 JSON
  - [ ] `get_team(team_id)` 返回原始 JSON

- [ ] 联赛映射
  - [ ] `COMPETITION_IDS` 字典定义

- [ ] 测试文件
  - [ ] `tests/test_provider/test_football_data.py` 存在
  - [ ] 测试所有 API 方法

---

### Task 2.3: Understat Provider

- [ ] 文件创建
  - [ ] `src/provider/understat/__init__.py` 存在
  - [ ] `src/provider/understat/client.py` 存在

- [ ] `UnderstatProvider` 类
  - [ ] 继承 `BaseProvider`
  - [ ] 使用 `understat` 包或直接 HTTP
  - [ ] `name` 属性返回 `"understat"`
  - [ ] `is_available()` 检查包是否安装

- [ ] API 方法
  - [ ] `get_team_stats(team_name, league, season)` 返回原始 JSON
  - [ ] `get_team_matches(team_name, league, season)` 返回原始 JSON
  - [ ] `get_league_matches(league, season)` 返回原始 JSON
  - [ ] `get_player_stats(player_name, league, season)` 返回原始 JSON

- [ ] 测试文件
  - [ ] `tests/test_provider/test_understat.py` 存在

---

### Task 2.4: ClubElo Provider

- [ ] 文件创建
  - [ ] `src/provider/clubelo/__init__.py` 存在
  - [ ] `src/provider/clubelo/client.py` 存在

- [ ] `ClubEloProvider` 类
  - [ ] 继承 `BaseProvider`
  - [ ] `BASE_URL = "http://api.clubelo.com"`
  - [ ] `name` 属性返回 `"clubelo"`
  - [ ] `is_available()` 返回 `True`（免费 API）

- [ ] API 方法
  - [ ] `get_elo(team_name, date)` 返回原始 CSV/JSON

- [ ] 球队名称映射
  - [ ] 加载 `config/team_name_map.json`
  - [ ] `_map_team_name()` 方法

- [ ] 测试文件
  - [ ] `tests/test_provider/test_clubelo.py` 存在

---

### Task 2.5: Odds API Provider

- [ ] 文件创建
  - [ ] `src/provider/odds/__init__.py` 存在
  - [ ] `src/provider/odds/client.py` 存在

- [ ] `OddsProvider` 类
  - [ ] 继承 `BaseProvider`
  - [ ] `BASE_URL = "https://api.the-odds-api.com"`
  - [ ] `name` 属性返回 `"odds_api"`
  - [ ] `is_available()` 检查 API key

- [ ] API 方法
  - [ ] `get_odds(sport, match_id, regions, markets)` 返回原始 JSON

- [ ] 测试文件
  - [ ] `tests/test_provider/test_odds.py` 存在

---

### Task 2.6: Weather Provider

- [ ] 文件创建
  - [ ] `src/provider/weather/__init__.py` 存在
  - [ ] `src/provider/weather/client.py` 存在

- [ ] `WeatherProvider` 类
  - [ ] 继承 `BaseProvider`
  - [ ] `BASE_URL = "https://api.openweathermap.org/data/2.5"`
  - [ ] `name` 属性返回 `"weather"`
  - [ ] `is_available()` 检查 API key

- [ ] API 方法
  - [ ] `get_weather(lat, lon)` 返回原始 JSON

- [ ] 测试文件
  - [ ] `tests/test_provider/test_weather.py` 存在

---

## Phase 3: DataSource 实现

### Task 3.1: MatchDataSource

- [ ] 文件创建
  - [ ] `src/datasource/match/__init__.py` 存在
  - [ ] `src/datasource/match/match_datasource.py` 存在

- [ ] `MatchDataSource` 类
  - [ ] 继承 `DataSource[Match]`
  - [ ] `data_type` 返回 `DataSourceType.MATCH`
  - [ ] `capabilities()` 返回正确描述

- [ ] 方法实现
  - [ ] `fetch(match_id)` 返回 `Optional[Match]`
  - [ ] `fetch_upcoming(competition, days)` 返回 `List[Match]`
  - [ ] `parse(raw_data)` 返回 `Match`

- [ ] Provider 回退
  - [ ] FootyStats Provider 优先
  - [ ] Football-Data Provider 回退
  - [ ] 日志记录回退事件

- [ ] 缓存
  - [ ] 缓存 TTL = 30 秒
  - [ ] 缓存键包含所有参数

- [ ] 测试文件
  - [ ] `tests/test_datasource/test_match.py` 存在
  - [ ] 测试正常获取
  - [ ] 测试 Provider 回退
  - [ ] 测试缓存行为

---

### Task 3.2: TeamDataSource

- [ ] 文件创建
  - [ ] `src/datasource/team/__init__.py` 存在
  - [ ] `src/datasource/team/team_datasource.py` 存在

- [ ] `TeamDataSource` 类
  - [ ] 继承 `DataSource[Team]`
  - [ ] `data_type` 返回 `DataSourceType.TEAM`
  - [ ] `capabilities()` 返回正确描述

- [ ] 方法实现
  - [ ] `fetch(team_id)` 返回 `Optional[Team]`
  - [ ] `parse(raw_data)` 返回 `Team`

- [ ] 数据聚合
  - [ ] FootyStats 提供基础数据
  - [ ] Understat 补充 xG/PPDA
  - [ ] ClubElo 补充 Elo

- [ ] 缓存
  - [ ] 缓存 TTL = 3600 秒（1小时）

- [ ] 测试文件
  - [ ] `tests/test_datasource/test_team.py` 存在

---

### Task 3.3: StandingsDataSource

- [ ] 文件创建
  - [ ] `src/datasource/standings/__init__.py` 存在
  - [ ] `src/datasource/standings/standings_datasource.py` 存在

- [ ] `StandingsDataSource` 类
  - [ ] 继承 `DataSource[List[StandingsEntry]]`
  - [ ] `data_type` 返回 `DataSourceType.STANDINGS`
  - [ ] `fetch(competition)` 返回 `List[StandingsEntry]`

- [ ] Provider 回退
  - [ ] FootyStats 优先
  - [ ] Football-Data 回退

- [ ] 测试文件
  - [ ] `tests/test_datasource/test_standings.py` 存在

---

### Task 3.4: OddsDataSource

- [ ] 文件创建
  - [ ] `src/datasource/odds/__init__.py` 存在
  - [ ] `src/datasource/odds/odds_datasource.py` 存在

- [ ] `OddsDataSource` 类
  - [ ] 继承 `DataSource[Odds]`
  - [ ] `fetch(competition, match_id)` 返回 `Odds`

- [ ] 计算方法
  - [ ] `calculate_implied_probability(odds)` 方法
  - [ ] `remove_vig(home, draw, away)` 方法

- [ ] 测试文件
  - [ ] `tests/test_datasource/test_odds.py` 存在

---

### Task 3.5: EloDataSource

- [ ] 文件创建
  - [ ] `src/datasource/elo/__init__.py` 存在
  - [ ] `src/datasource/elo/elo_datasource.py` 存在

- [ ] `EloDataSource` 类
  - [ ] 继承 `DataSource[Elo]`
  - [ ] `fetch(team_name)` 返回 `Elo`

- [ ] 球队名称映射
  - [ ] 使用 Provider 的映射

- [ ] 测试文件
  - [ ] `tests/test_datasource/test_elo.py` 存在

---

### Task 3.6: WeatherDataSource

- [ ] 文件创建
  - [ ] `src/datasource/weather/__init__.py` 存在
  - [ ] `src/datasource/weather/weather_datasource.py` 存在

- [ ] `WeatherDataSource` 类
  - [ ] 继承 `DataSource[Weather]`
  - [ ] `fetch(lat, lon)` 返回 `Weather`

- [ ] xG 调整计算
  - [ ] 风速 > 8m/s: -0.10
  - [ ] 降水 > 5mm: -0.10
  - [ ] 雪/雾/霭: -0.10

- [ ] 测试文件
  - [ ] `tests/test_datasource/test_weather.py` 存在

---

## Phase 4: 集成与测试

### Task 4.1: 更新 MatchBuilder

- [ ] 导入更新
  - [ ] 导入 `MatchDataSource`
  - [ ] 导入 `TeamDataSource`
  - [ ] 导入 `StandingsDataSource`
  - [ ] 导入 `OddsDataSource`
  - [ ] 导入 `EloDataSource`
  - [ ] 导入 `WeatherDataSource`

- [ ] 构造函数更新
  - [ ] 接受 DataSource 实例
  - [ ] 或从 registry 获取

- [ ] 方法更新
  - [ ] `build()` 使用 DataSource
  - [ ] `_fetch_team_stats()` 使用 TeamDataSource
  - [ ] `_fetch_league_table()` 使用 StandingsDataSource
  - [ ] `_fetch_odds()` 使用 OddsDataSource

- [ ] 功能验证
  - [ ] 所有现有功能正常
  - [ ] 返回数据格式一致
  - [ ] 错误处理正确

---

### Task 4.2: 向后兼容层

- [ ] 文件更新
  - [ ] `src/collectors/__init__.py` 更新

- [ ] 别名定义
  - [ ] `FootyStatsClient = FootyStatsProvider`
  - [ ] `FootballDataClient = FootballDataProvider`
  - [ ] `UnderstatClient = UnderstatProvider`
  - [ ] `ClubEloClient = ClubEloProvider`
  - [ ] `OddsAPIClient = OddsProvider`
  - [ ] `WeatherClient = WeatherProvider`

- [ ] 导出验证
  - [ ] `from src.collectors import FootyStatsClient` 可用
  - [ ] 所有旧导入路径可用

---

### Task 4.3: 集成测试

- [ ] 测试文件
  - [ ] `tests/integration/test_datasource_integration.py` 存在

- [ ] 测试场景
  - [ ] 完整数据获取流程
  - [ ] Provider 回退场景
  - [ ] 缓存命中/未命中
  - [ ] MatchBuilder 集成
  - [ ] 向后兼容验证

- [ ] 测试通过
  - [ ] 所有测试用例通过
  - [ ] 无回归问题

---

### Task 4.4: 文档更新

- [ ] 架构文档
  - [ ] `doc/architecture.md` 更新
  - [ ] 添加新架构图
  - [ ] 添加模块说明

- [ ] 开发指南
  - [ ] `doc/provider_guide.md` 创建
  - [ ] `doc/datasource_guide.md` 创建

- [ ] 使用示例
  - [ ] 添加代码示例
  - [ ] 添加 API 文档

---

## 最终验证

### 功能验证

- [ ] 所有 Provider 测试通过
- [ ] 所有 DataSource 测试通过
- [ ] MatchBuilder 功能正常
- [ ] 向后兼容验证通过
- [ ] 集成测试通过

### 代码质量

- [ ] 类型注解完整
- [ ] 文档字符串完整
- [ ] 无 lint 错误
- [ ] 无类型检查错误

### 性能验证

- [ ] 缓存正常工作
- [ ] 无性能退化
- [ ] 并发请求正常

### 文档验证

- [ ] 架构文档更新
- [ ] API 文档完整
- [ ] 使用示例清晰

---

*Goalcast Collectors Refactoring Checklist v1.0*

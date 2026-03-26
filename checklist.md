# FootyStats 数据解析与缓存 - 实施检查清单

## Phase 1: 数据模型定义

### Task 1.1: 创建基础模型文件
- [ ] 创建 `provider/footystats/models.py` 文件
- [ ] 导入必要的依赖（pydantic, datetime, typing 等）
- [ ] 实现 `FootyStatsMeta` 类
  - [ ] 字段：endpoint, timestamp, api_version, rate_limit_remaining
  - [ ] 默认值设置
  - [ ] 文档字符串
- [ ] 实现 `FootyStatsResponse[T]` 泛型类
  - [ ] 泛型类型参数 T
  - [ ] 字段：data, meta, raw_data
  - [ ] `from_api_response` 类方法
- [ ] 实现 `Pagination` 类
  - [ ] 字段：current_page, total_pages, per_page, total_items
- [ ] 实现枚举类型
  - [ ] `MatchStatus`: SCHEDULED, LIVE, HALFTIME, FINISHED, POSTPONED, CANCELLED
  - [ ] `LeagueType`: LEAGUE, CUP, INTERNATIONAL
- [ ] 运行基础测试验证模型创建成功

**验收标准**:
```bash
pytest tests/provider/footystats/test_models.py::test_base_models -v
```

---

### Task 1.2: 创建联赛数据模型
- [ ] 实现 `League` 类
  - [ ] 字段：id, name, country_id, country_name, is_cup, current_season_id
  - [ ] 字段类型和默认值
  - [ ] 添加字段验证器（is_cup 必须是 bool）
- [ ] 实现 `Season` 类
  - [ ] 字段：id, league_id, year, start_date, end_date, is_current
  - [ ] date 类型验证
- [ ] 实现 `LeagueListResponse` 类
  - [ ] 继承 `FootyStatsResponse[List[League]]`
- [ ] 添加 Pydantic 配置
  - [ ] `model_config = ConfigDict(frozen=True)` (可选，性能优化)
- [ ] 编写单元测试

**验收标准**:
```bash
pytest tests/provider/footystats/test_models.py::test_league_models -v
```

---

### Task 1.3: 创建比赛数据模型
- [ ] 实现 `MatchTeam` 类
  - [ ] 字段：id, name, short_name, logo_url
- [ ] 实现 `MatchScore` 类
  - [ ] 字段：home, away, halftime_home, halftime_away, fulltime_home, fulltime_away
  - [ ] 可选字段处理
- [ ] 实现 `MatchOdds` 类
  - [ ] 字段：opening_home, opening_draw, opening_away, current_home, current_draw, current_away
  - [ ] 赔率范围验证器（ge=1.0）
- [ ] 实现 `Match` 类（核心）
  - [ ] 基础字段：id, season_id, league_id, league_name, round, stage
  - [ ] 球队字段：home_team, away_team
  - [ ] 比分为：score
  - [ ] 赔率字段：odds (optional)
  - [ ] 时间字段：kickoff_time
  - [ ] 状态字段：status
  - [ ] 其他：venue, referee_id
  - [ ] 高级统计：home_xg, away_xg, home_possession, away_possession
  - [ ] `raw_data` 字段（保留原始数据）
  - [ ] datetime 字段验证器
- [ ] 实现 `MatchListResponse` 类
  - [ ] 字段：data (List[Match]), meta, raw_data, pagination
- [ ] 编写单元测试和边界测试

**验收标准**:
```bash
pytest tests/provider/footystats/test_models.py::test_match_models -v
```

---

### Task 1.4: 创建球队数据模型
- [ ] 实现 `TeamStats` 类
  - [ ] 基础统计：played, won, drawn, lost, goals_for, goals_against, points
  - [ ] xG 统计：xg_for, xg_against, xg_home, xg_away, xga_home, xga_away
  - [ ] 控球率：possession_home, possession_away
  - [ ] 射门统计：shots_home, shots_away, shots_on_target_home, shots_on_target_away
  - [ ] 转化率：conversion_rate_home, conversion_rate_away
  - [ ] 零封率：clean_sheet_home, clean_sheet_away
  - [ ] 角球：corners_for_home, corners_for_away, corners_against_home, corners_against_away
  - [ ] 场均数据：ppg_home, ppg_away, ppg_overall
  - [ ] 数值范围验证器（possession: 0-100, xg: 0-5 等）
- [ ] 实现 `TeamForm` 类
  - [ ] 字段：last_5, last_6, last_10 (List[str])
  - [ ] form_score: float (0-100)
  - [ ] 验证器：form 结果只能是 W/D/L
- [ ] 实现 `Team` 类
  - [ ] 基础信息：id, name, short_name, country, founded, venue, logo_url
  - [ ] 统计：stats (TeamStats)
  - [ ] 状态：form (TeamForm)
  - [ ] 排名：league_position
  - [ ] raw_data 字段
- [ ] 实现 `TeamResponse` 类
- [ ] 编写单元测试

**验收标准**:
```bash
pytest tests/provider/footystats/test_models.py::test_team_models -v
```

---

### Task 1.5: 创建球员和裁判数据模型
- [ ] 实现 `PlayerStats` 类
  - [ ] 字段：appearances, goals, assists, minutes_played
  - [ ] 卡片：yellow_cards, red_cards
  - [ ] 技术统计：shots_per_game, pass_accuracy, xg, xa
- [ ] 实现 `Player` 类
  - [ ] 基础信息：id, name, team_id, team_name, position, age, nationality
  - [ ] 统计：stats (PlayerStats)
  - [ ] raw_data 字段
- [ ] 实现 `PlayerListResponse` 类
- [ ] 实现 `RefereeStats` 类
  - [ ] 字段：matches_officiated, yellow_cards_per_match, red_cards_per_match, penalties_per_match
- [ ] 实现 `Referee` 类
  - [ ] 基础信息：id, name, country
  - [ ] 统计：stats (RefereeStats)
  - [ ] raw_data 字段
- [ ] 实现 `RefereeListResponse` 类
- [ ] 编写单元测试

**验收标准**:
```bash
pytest tests/provider/footystats/test_models.py::test_player_referee_models -v
```

---

### Task 1.6: 创建积分榜数据模型
- [ ] 实现 `StandingsEntry` 类
  - [ ] 字段：position, team_id, team_name, played, won, drawn, lost
  - [ ] 进球：goals_for, goals_against, goal_difference
  - [ ] 积分：points
  - [ ] 状态：form (List[str])
  - [ ] xG 统计：xg_for, xg_against
- [ ] 实现 `StandingsTable` 类
  - [ ] 字段：season_id, league_id, league_name, stage, type
  - [ ] 条目：entries (List[StandingsEntry])
  - [ ] 验证器：stage 只能是预定义值，type 只能是 total/home/away
- [ ] 实现 `StandingsResponse` 类
  - [ ] data: List[StandingsTable] (可能包含多个阶段/类型)
- [ ] 编写单元测试

**验收标准**:
```bash
pytest tests/provider/footystats/test_models.py::test_standings_models -v
```

---

### Task 1.7: 创建缓存数据模型
- [ ] 创建 `datasource/cache_models.py` 文件
- [ ] 实现 `CacheMetadata` 类
  - [ ] 字段：created_at, updated_at, source, version, checksum
  - [ ] datetime 字段处理
- [ ] 实现 `CachedMatch` 类
  - [ ] 字段：match (Match), cache_meta, access_count, last_accessed
- [ ] 实现 `CachedTeam` 类
  - [ ] 字段：team (Team), cache_meta, historical_stats (List[TeamStats])
- [ ] 实现 `CachedLeagueTable` 类
  - [ ] 字段：table (StandingsTable), cache_meta, snapshot_history
- [ ] 添加 checksum 计算工具函数
  - [ ] 使用 hashlib.md5
  - [ ] JSON 序列化字典
- [ ] 编写单元测试

**验收标准**:
```bash
pytest tests/datasource/test_cache_models.py -v
```

---

### Task 1.8: 编写模型单元测试
- [ ] 创建 `tests/provider/footystats/test_models.py` 文件
- [ ] 测试基础模型
  - [ ] FootyStatsMeta 创建和字段验证
  - [ ] FootyStatsResponse 泛型功能
  - [ ] from_api_response 类方法
- [ ] 测试比赛模型
  - [ ] MatchTeam, MatchScore, MatchOdds 创建
  - [ ] Match 完整创建流程
  - [ ] datetime 验证器测试
  - [ ] 边界值测试（None 值，空字符串）
- [ ] 测试球队模型
  - [ ] TeamStats 数值验证
  - [ ] TeamForm form_score 计算
  - [ ] Team 完整创建
- [ ] 测试其他模型
  - [ ] Player, Referee, Standings 模型
- [ ] 运行测试并检查覆盖率
  - [ ] 目标：模型测试覆盖率 > 90%

**验收标准**:
```bash
pytest tests/provider/footystats/test_models.py -v --cov=provider.footystats.models
# 覆盖率报告应显示 > 90%
```

---

## Phase 2: Parser 实现

### Task 2.1: 创建 Parser 基类
- [ ] 创建 `provider/footystats/parser.py` 文件
- [ ] 导入必要的依赖
- [ ] 实现 `FootyStatsParser` 类
- [ ] 实现 `_safe_get` 静态方法
  - [ ] 支持多级嵌套键访问
  - [ ] 支持默认值
  - [ ] 测试：`_safe_get({"a": {"b": 1}}, "a", "b") == 1`
- [ ] 实现 `_parse_datetime` 静态方法
  - [ ] 处理 date + time 组合
  - [ ] 处理单独 date
  - [ ] 处理 None 和空字符串
  - [ ] 异常处理
- [ ] 实现 `_parse_status` 方法
  - [ ] 字符串到 MatchStatus 的映射
  - [ ] 默认值处理
- [ ] 实现 `_calculate_form_score` 静态方法
  - [ ] W/D/L 到分数的映射（3/1/0）
  - [ ] 权重计算（近期权重更高）
  - [ ] 归一化到 0-100
- [ ] 编写单元测试

**验收标准**:
```bash
pytest tests/provider/footystats/test_parser.py::test_parser_utils -v
```

---

### Task 2.2: 实现联赛列表解析
- [ ] 实现 `parse_league_list` 方法
  - [ ] 从 raw dict 中提取数据列表
  - [ ] 处理 data/leagues 键
  - [ ] 列表和非列表情况处理
- [ ] 遍历数据项创建 League 对象
  - [ ] 字段映射（兼容不同 API 格式）
  - [ ] 类型转换（int, str, bool）
- [ ] 错误处理
  - [ ] try-except 包裹单个联赛解析
  - [ ] 记录警告日志
  - [ ] 跳过错误项继续处理
- [ ] 创建并返回 `LeagueListResponse`
  - [ ] 包含 meta 信息
  - [ ] 包含 raw_data
- [ ] 编写单元测试

**验收标准**:
```bash
pytest tests/provider/footystats/test_parser.py::test_parse_league_list -v
```

---

### Task 2.3: 实现比赛详情解析
- [ ] 实现 `parse_match_details` 方法
  - [ ] 从 raw dict 中提取 data 字段
- [ ] 解析球队信息
  - [ ] 创建 MatchTeam 对象（home 和 away）
  - [ ] 处理 home_id/homeTeam.id 等不同格式
- [ ] 解析比分信息
  - [ ] 创建 MatchScore 对象
  - [ ] 处理全场、半场比分
- [ ] 解析赔率信息（可选）
  - [ ] 检查赔率字段是否存在
  - [ ] 创建 MatchOdds 对象
- [ ] 解析高级统计
  - [ ] xG 数据
  - [ ] 控球率数据
- [ ] 解析时间和状态
  - [ ] 使用 _parse_datetime
  - [ ] 使用 _parse_status
- [ ] 创建 Match 对象
  - [ ] 包含 raw_data
- [ ] 创建并返回 `MatchResponse`
- [ ] 错误处理和日志记录
- [ ] 编写单元测试

**验收标准**:
```bash
pytest tests/provider/footystats/test_parser.py::test_parse_match_details -v
```

---

### Task 2.4: 实现球队数据解析
- [ ] 实现 `parse_team` 方法
- [ ] 解析统计数据
  - [ ] 创建 TeamStats 对象
  - [ ] 字段映射和类型转换
  - [ ] 处理缺失字段（使用默认值 0）
- [ ] 解析近期状态
  - [ ] 创建 TeamForm 对象
  - [ ] 提取 last_5, last_6, last_10
  - [ ] 计算 form_score
- [ ] 创建 Team 对象
  - [ ] 基础信息字段
  - [ ] 包含 stats 和 form
  - [ ] 包含 raw_data
- [ ] 创建并返回 `TeamResponse`
- [ ] 错误处理
- [ ] 编写单元测试

**验收标准**:
```bash
pytest tests/provider/footystats/test_parser.py::test_parse_team -v
```

---

### Task 2.5: 实现其他端点解析
- [ ] 实现 `parse_league_stats` 方法
- [ ] 实现 `parse_league_matches` 方法
  - [ ] 处理分页信息
- [ ] 实现 `parse_league_teams` 方法
- [ ] 实现 `parse_league_players` 方法
  - [ ] 处理 include_stats 参数
- [ ] 实现 `parse_league_tables` 方法
  - [ ] 处理多个阶段/类型的积分榜
- [ ] 实现 `parse_referees` 方法
- [ ] 实现 `parse_player_stats` 方法
- [ ] 为每个方法编写单元测试

**验收标准**:
```bash
pytest tests/provider/footystats/test_parser.py::test_parse_other_endpoints -v
```

---

### Task 2.6: 编写 Parser 单元测试
- [ ] 创建 `tests/provider/footystats/test_parser.py` 文件
- [ ] 准备测试数据
  - [ ] 收集真实 API 响应样本（或构造逼真的样本）
  - [ ] 为每个端点准备至少 3 个样本
  - [ ] 包括边界情况样本（空数据、缺失字段）
- [ ] 测试工具方法
  - [ ] _safe_get 各种情况
  - [ ] _parse_datetime 各种格式
  - [ ] _parse_status 各种状态
  - [ ] _calculate_form_score 计算逻辑
- [ ] 测试各端点解析方法
  - [ ] 正常情况测试
  - [ ] 缺失字段测试
  - [ ] 错误数据测试
- [ ] 运行测试并检查覆盖率
  - [ ] 目标：Parser 测试覆盖率 > 85%

**验收标准**:
```bash
pytest tests/provider/footystats/test_parser.py -v --cov=provider.footystats.parser
# 覆盖率 > 85%
```

---

## Phase 3: Provider 增强

### Task 3.1: 增强 FootyStatsProvider
- [ ] 编辑 `provider/footystats/client.py`
- [ ] 添加导入
  - [ ] `from .models import ...`
  - [ ] `from .parser import FootyStatsParser`
- [ ] 在 `__init__` 中添加
  - [ ] `self._parser = FootyStatsParser()`
- [ ] 实现类型化方法（为每个现有方法添加 typed 版本）
  - [ ] `get_league_list_typed` - 返回 `LeagueListResponse`
  - [ ] `get_country_list_typed` - 返回响应对象
  - [ ] `get_todays_matches_typed` - 返回 `MatchListResponse`
  - [ ] `get_league_stats_typed` - 返回响应对象
  - [ ] `get_league_matches_typed` - 返回 `MatchListResponse`
  - [ ] `get_league_teams_typed` - 返回响应对象
  - [ ] `get_league_players_typed` - 返回 `PlayerListResponse`
  - [ ] `get_league_referees_typed` - 返回 `RefereeListResponse`
  - [ ] `get_league_tables_typed` - 返回 `StandingsResponse`
  - [ ] `get_match_details_typed` - 返回 `MatchResponse`
  - [ ] `get_team_typed` - 返回 `TeamResponse`
  - [ ] `get_team_last_x_stats_typed` - 返回响应对象
  - [ ] `get_player_stats_typed` - 返回响应对象
  - [ ] `get_referee_stats_typed` - 返回响应对象
  - [ ] `get_btts_stats_typed` - 返回响应对象
  - [ ] `get_over_2_5_stats_typed` - 返回响应对象
- [ ] 每个 typed 方法实现模式
  - [ ] 调用对应的原始方法获取 raw_data
  - [ ] 检查 raw_data 是否为 None
  - [ ] 调用 parser 对应解析方法
  - [ ] 返回类型化响应对象
- [ ] 添加类型注解

**验收标准**:
```bash
pytest tests/provider/footystats/test_client.py::test_typed_methods -v
```

---

### Task 3.2: 保持向后兼容
- [ ] 确认所有现有方法签名未改变
  - [ ] 原始方法（如 `get_league_list`）保持不变
  - [ ] 返回类型仍为 `Optional[Dict[str, Any]]`
- [ ] 添加类型提示
  - [ ] 为现有方法添加返回类型注解
- [ ] 添加文档注释
  - [ ] 在 typed 方法中添加说明
  - [ ] 标注原始方法将在未来版本中废弃（可选）
- [ ] 更新 `__init__.py` 导出
  - [ ] 导出新的 Models 和 Parser

**验收标准**:
- 现有代码无需修改即可运行
- IDE 类型检查通过

---

### Task 3.3: Provider 集成测试
- [ ] 创建/编辑 `tests/provider/footystats/test_client.py`
- [ ] 设置测试夹具
  - [ ] Mock HTTP 客户端
  - [ ] Mock API 响应
- [ ] 测试 typed 方法
  - [ ] 验证返回类型正确
  - [ ] 验证解析后的数据结构正确
- [ ] 测试错误处理
  - [ ] API 返回 None 时的处理
  - [ ] 解析失败时的处理
- [ ] 测试限流逻辑（如已有）
- [ ] 测试重试逻辑（如已有）
- [ ] 运行集成测试

**验收标准**:
```bash
pytest tests/provider/footystats/test_client.py -v
```

---

## Phase 4: DataSource 增强

### Task 4.1: 创建缓存管理器
- [ ] 创建 `datasource/cache_manager.py` 文件
- [ ] 导入依赖
- [ ] 实现 `CacheManager` 单例类
  - [ ] `__new__` 方法实现单例
  - [ ] `__init__` 初始化
- [ ] 实现缓存存储
  - [ ] `_cache: Dict[str, Dict[str, Any]]`
  - [ ] `_access_times: Dict[str, datetime]`
- [ ] 实现统计计数器
  - [ ] `_hit_count`
  - [ ] `_miss_count`
- [ ] 实现 `get` 方法
  - [ ] 检查缓存是否存在
  - [ ] 检查 TTL 是否过期
  - [ ] 更新访问时间和计数
  - [ ] 返回缓存数据或 None
- [ ] 实现 `set` 方法
  - [ ] 存储数据和元数据
  - [ ] 记录时间戳
- [ ] 实现 `delete` 方法
- [ ] 实现 `clear` 方法
- [ ] 实现 `get_stats` 方法
  - [ ] 计算并返回命中率等统计
- [ ] 实现 `_get_ttl_for_key` 方法
  - [ ] 根据 key 类型返回不同 TTL
- [ ] 实现 `_periodic_clean` 协程
  - [ ] 定期清理过期缓存
- [ ] 实现 `_start_clean_task` 方法
- [ ] 实现 `clean_expired` 方法
- [ ] 添加日志记录
- [ ] 编写单元测试

**验收标准**:
```bash
pytest tests/datasource/test_cache_manager.py -v
```

---

### Task 4.2: 增强 MatchDataSource
- [ ] 编辑 `datasource/match/match_datasource.py`
- [ ] 添加导入
  - [ ] `from datasource.cache_models import ...`
  - [ ] `from datasource.cache_manager import cache_manager`
- [ ] 在 `__init__` 中添加
  - [ ] `self._history_cache: Dict[str, List[CachedMatch]] = {}`
- [ ] 增强 `fetch` 方法
  - [ ] 尝试从缓存获取
  - [ ] 缓存命中时更新访问记录并返回
  - [ ] 缓存未命中时调用 Provider
  - [ ] 解析并设置缓存
  - [ ] 添加到历史缓存
- [ ] 实现 `_add_to_history` 方法
  - [ ] 创建 `CachedMatch` 对象
  - [ ] 添加到历史列表
  - [ ] 限制历史版本数量（max 10）
- [ ] 实现 `_compute_checksum` 方法
  - [ ] 使用 hashlib.md5
  - [ ] JSON 序列化后计算
- [ ] 实现 `_update_cache_access` 方法
  - [ ] 更新访问时间和计数
- [ ] 实现 `get_history` 方法
  - [ ] 返回比赛历史数据列表
- [ ] 实现 `_convert_to_domain` 方法（如需要）
- [ ] 编写单元测试

**验收标准**:
```bash
pytest tests/datasource/match/test_match_datasource.py -v
```

---

### Task 4.3: 增强 TeamDataSource
- [ ] 编辑 `datasource/team/team_datasource.py`
- [ ] 添加导入
- [ ] 在 `__init__` 中添加
  - [ ] `self._historical_stats: Dict[str, List[Dict]] = {}`
- [ ] 增强 `fetch` 方法
  - [ ] 检查缓存
  - [ ] 获取数据
  - [ ] 调用 `_accumulate_stats`
  - [ ] enrich 数据
  - [ ] 设置缓存
- [ ] 实现 `_accumulate_stats` 方法
  - [ ] 添加时间戳
  - [ ] 添加到历史列表
  - [ ] 限制历史数量（max 50）
- [ ] 实现 `get_stats_history` 方法
  - [ ] 返回球队历史统计
- [ ] 实现 `get_stats_trend` 方法
  - [ ] 计算趋势（current, average, min, max, trend 方向）
- [ ] 编写单元测试

**验收标准**:
```bash
pytest tests/datasource/team/test_team_datasource.py -v
```

---

### Task 4.4: 增强其他 DataSource
- [ ] 增强 `StandingsDataSource`
  - [ ] 添加历史快照功能
  - [ ] 实现趋势分析
- [ ] 增强 `PlayerDataSource`（如存在）
- [ ] 增强 `RefereeDataSource`（如存在）
- [ ] 为每个增强的 DataSource 编写测试

---

### Task 4.5: DataSource 集成测试
- [ ] 创建/编辑相应的测试文件
- [ ] 测试 MatchDataSource 缓存功能
  - [ ] 首次 fetch 调用 Provider
  - [ ] 第二次 fetch 命中缓存
  - [ ] TTL 过期后重新获取
  - [ ] 历史数据积累
- [ ] 测试 TeamDataSource 统计积累
  - [ ] 多次 fetch 后历史统计增加
  - [ ] get_stats_history 返回正确数据
  - [ ] get_stats_trend 计算正确
- [ ] 测试历史数据查询
- [ ] 测试缓存失效逻辑
- [ ] 运行集成测试

**验收标准**:
```bash
pytest tests/datasource/ -v -k "cache or history"
```

---

## Phase 5: 配置和监控

### Task 5.1: 添加缓存配置
- [ ] 编辑 `config/settings.py`
- [ ] 创建 `CacheSettings` 类
  - [ ] 字段：MATCH_CACHE_TTL, TEAM_CACHE_TTL, LEAGUE_CACHE_TTL, PLAYER_CACHE_TTL
  - [ ] 字段：MAX_HISTORY_SIZE, ENABLE_HISTORY
  - [ ] 字段：AUTO_CLEAN_INTERVAL, CLEAN_THRESHOLD
  - [ ] 默认值设置
- [ ] 在 `Settings` 类中添加
  - [ ] `CACHE: CacheSettings = CacheSettings()`
- [ ] 更新 cache_manager 使用配置
  - [ ] 从 settings.CACHE 读取配置
- [ ] 编写配置测试

**验收标准**:
```bash
pytest tests/config/test_settings.py::test_cache_settings -v
```

---

### Task 5.2: 添加缓存监控
- [ ] 创建 `utils/cache_monitor.py` 文件
- [ ] 实现缓存命中率监控
  - [ ] 定期记录 hit_rate
- [ ] 实现缓存大小监控
  - [ ] 记录缓存条目数量
- [ ] 实现缓存清理日志
  - [ ] 记录每次清理的条目数
- [ ] （可选）添加 Prometheus 指标
  - [ ] gauge: cache_size
  - [ ] counter: cache_hits, cache_misses
  - [ ] histogram: cache_ttl_distribution
- [ ] 添加日志输出
- [ ] 编写测试

---

### Task 5.3: 性能测试
- [ ] 创建 `tests/performance/test_cache.py` 文件
- [ ] 测试缓存命中率
  - [ ] 模拟大量请求
  - [ ] 测量 hit_rate
- [ ] 测试解析性能
  - [ ] 测量解析耗时
  - [ ] 对比有无解析的性能差异
- [ ] 测试内存占用
  - [ ] 测量缓存内存使用
  - [ ] 测试不同缓存大小的影响
- [ ] 生成性能报告
  - [ ] 输出关键指标
  - [ ] 提出优化建议

**验收标准**:
```bash
pytest tests/performance/test_cache.py -v
# 查看性能报告
```

---

## Phase 6: 文档和迁移

### Task 6.1: 更新 API 文档
- [ ] 编辑 `provider/footystats/README.md`
- [ ] 更新数据类型说明
  - [ ] 说明新的类型化方法
  - [ ] 说明 Models 结构
- [ ] 添加使用示例
  - [ ] 基本使用示例
  - [ ] 类型化方法示例
  - [ ] 缓存使用示例
- [ ] 添加缓存机制说明
  - [ ] TTL 配置
  - [ ] 历史数据
- [ ] 更新端点文档
  - [ ] 列出所有 16 个端点
  - [ ] 说明返回类型

---

### Task 6.2: 编写迁移指南
- [ ] 创建 `docs/migration_guide.md` 文件
- [ ] 说明新旧 API 对比
  - [ ] 对照表：旧方法 vs 新方法
- [ ] 提供代码迁移示例
  - [ ] Before/After 代码对比
- [ ] 列出破坏性变更
  - [ ] 如有，详细说明
- [ ] 提供回滚方案
  - [ ] 如何禁用新功能
  - [ ] 如何恢复到旧版本

---

### Task 6.3: 编写使用文档
- [ ] 创建 `docs/usage_guide.md` 文件
- [ ] 基础使用示例
  - [ ] Provider 初始化
  - [ ] 调用 API
  - [ ] 处理响应
- [ ] 高级功能示例
  - [ ] 使用缓存
  - [ ] 访问历史数据
  - [ ] 趋势分析
- [ ] 最佳实践
  - [ ] 缓存配置建议
  - [ ] 错误处理
  - [ ] 性能优化
- [ ] 常见问题解答
  - [ ] FAQ

---

## 最终验收清单

### 功能验收
- [ ] 所有 16 个端点都有类型化方法
- [ ] 所有模型都有完整的字段定义
- [ ] Parser 能正确处理各种 API 响应
- [ ] 缓存机制正常工作
- [ ] 历史数据能正确积累和查询
- [ ] 配置系统正常工作

### 质量验收
- [ ] 单元测试覆盖率 > 85%
- [ ] 集成测试通过
- [ ] 性能测试达标
- [ ] 文档完整
- [ ] 代码审查通过

### 向后兼容性验收
- [ ] 现有代码无需修改即可运行
- [ ] 旧的 API 方法仍然可用
- [ ] 迁移指南清晰

### 部署验收
- [ ] 配置文件更新
- [ ] 依赖项更新（requirements.txt）
- [ ] 环境变量说明
- [ ] 监控和日志配置

---

## 快速检查命令

```bash
# 运行所有测试
pytest tests/provider/footystats/ tests/datasource/ -v

# 检查覆盖率
pytest --cov=provider.footystats --cov=datasource --cov-report=html

# 类型检查
mypy provider/footystats/ datasource/

# 代码风格检查
flake8 provider/footystats/ datasource/

# 查看覆盖率报告
open htmlcov/index.html
```

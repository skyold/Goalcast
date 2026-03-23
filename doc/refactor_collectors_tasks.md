# Goalcast Collectors 重构任务分解

**版本**: 1.0  
**创建日期**: 2026-03-22  
**参考规范**: [refactor_collectors_spec.md](./refactor_collectors_spec.md)

---

## Phase 1: 基础设施

### Task 1.1: 创建 Provider 基类
**优先级**: P0  
**预估时间**: 2h  
**依赖**: 无

**描述**:
创建 `src/provider/base.py`，定义 Provider 抽象基类。

**验收标准**:
- [ ] `BaseProvider` 抽象类定义完成
- [ ] 包含 `name`, `is_available()` 抽象方法
- [ ] 包含 `_request()` HTTP 请求方法
- [ ] 支持超时配置
- [ ] 包含重试逻辑

**文件**:
- `src/provider/__init__.py`
- `src/provider/base.py`

---

### Task 1.2: 创建 DataSource 基类
**优先级**: P0  
**预估时间**: 2h  
**依赖**: Task 1.1

**描述**:
创建 `src/datasource/base.py`，定义 DataSource 抽象基类。

**验收标准**:
- [ ] `DataSource` 泛型抽象类定义完成
- [ ] 包含 `data_type`, `capabilities()`, `fetch()`, `parse()` 抽象方法
- [ ] 包含缓存逻辑
- [ ] 包含多 Provider 回退逻辑
- [ ] `DataCapability` 数据类定义

**文件**:
- `src/datasource/__init__.py`
- `src/datasource/base.py`

---

### Task 1.3: 定义标准数据类型
**优先级**: P0  
**预估时间**: 3h  
**依赖**: 无

**描述**:
创建 `src/datasource/types.py`，定义所有标准数据类型。

**验收标准**:
- [ ] `Match` 数据类定义
- [ ] `Team` 数据类定义
- [ ] `StandingsEntry` 数据类定义
- [ ] `Odds` 数据类定义
- [ ] `Elo` 数据类定义
- [ ] `Weather` 数据类定义
- [ ] `MatchType`, `MatchStatus` 枚举定义
- [ ] `DataSourceType` 枚举定义

**文件**:
- `src/datasource/types.py`

---

### Task 1.4: 实现数据源注册表
**优先级**: P1  
**预估时间**: 2h  
**依赖**: Task 1.2, Task 1.3

**描述**:
创建 `src/datasource/registry.py`，实现数据源注册管理。

**验收标准**:
- [ ] `DataRegistry` 单例类实现
- [ ] `register()` 方法
- [ ] `get()` 方法
- [ ] `get_all()` 方法
- [ ] `capabilities()` 方法
- [ ] 全局 `registry` 实例

**文件**:
- `src/datasource/registry.py`

---

## Phase 2: Provider 迁移

### Task 2.1: 迁移 FootyStats Provider
**优先级**: P0  
**预估时间**: 3h  
**依赖**: Task 1.1

**描述**:
将 `src/collectors/footystats.py` 迁移为 Provider 模式。

**验收标准**:
- [ ] `FootyStatsProvider` 类实现
- [ ] `get_team()` 方法返回原始 JSON
- [ ] `get_match()` 方法返回原始 JSON
- [ ] `get_league_matches()` 方法返回原始 JSON
- [ ] `get_league_table()` 方法返回原始 JSON
- [ ] 移除缓存逻辑（由 DataSource 负责）
- [ ] 移除解析逻辑（由 DataSource 负责）
- [ ] 单元测试通过

**文件**:
- `src/provider/footystats/__init__.py`
- `src/provider/footystats/client.py`
- `tests/test_provider/test_footystats.py`

---

### Task 2.2: 迁移 Football-Data Provider
**优先级**: P0  
**预估时间**: 2h  
**依赖**: Task 1.1

**描述**:
将 `src/collectors/football_data.py` 迁移为 Provider 模式。

**验收标准**:
- [ ] `FootballDataProvider` 类实现
- [ ] `get_matches()` 方法返回原始 JSON
- [ ] `get_standings()` 方法返回原始 JSON
- [ ] `get_team()` 方法返回原始 JSON
- [ ] 移除缓存逻辑
- [ ] 移除解析逻辑
- [ ] 单元测试通过

**文件**:
- `src/provider/football_data/__init__.py`
- `src/provider/football_data/client.py`
- `tests/test_provider/test_football_data.py`

---

### Task 2.3: 迁移 Understat Provider
**优先级**: P1  
**预估时间**: 2h  
**依赖**: Task 1.1

**描述**:
将 `src/collectors/understat.py` 迁移为 Provider 模式。

**验收标准**:
- [ ] `UnderstatProvider` 类实现
- [ ] `get_team_stats()` 方法返回原始 JSON
- [ ] `get_team_matches()` 方法返回原始 JSON
- [ ] `get_league_matches()` 方法返回原始 JSON
- [ ] `get_player_stats()` 方法返回原始 JSON
- [ ] 移除缓存逻辑
- [ ] 移除解析逻辑
- [ ] 单元测试通过

**文件**:
- `src/provider/understat/__init__.py`
- `src/provider/understat/client.py`
- `tests/test_provider/test_understat.py`

---

### Task 2.4: 迁移 ClubElo Provider
**优先级**: P1  
**预估时间**: 1h  
**依赖**: Task 1.1

**描述**:
将 `src/collectors/clubelo.py` 迁移为 Provider 模式。

**验收标准**:
- [ ] `ClubEloProvider` 类实现
- [ ] `get_elo()` 方法返回原始 CSV/JSON
- [ ] 移除缓存逻辑
- [ ] 移除解析逻辑
- [ ] 单元测试通过

**文件**:
- `src/provider/clubelo/__init__.py`
- `src/provider/clubelo/client.py`
- `tests/test_provider/test_clubelo.py`

---

### Task 2.5: 迁移 Odds API Provider
**优先级**: P1  
**预估时间**: 1h  
**依赖**: Task 1.1

**描述**:
将 `src/collectors/odds_api.py` 迁移为 Provider 模式。

**验收标准**:
- [ ] `OddsProvider` 类实现
- [ ] `get_odds()` 方法返回原始 JSON
- [ ] 移除缓存逻辑
- [ ] 移除解析逻辑
- [ ] 单元测试通过

**文件**:
- `src/provider/odds/__init__.py`
- `src/provider/odds/client.py`
- `tests/test_provider/test_odds.py`

---

### Task 2.6: 迁移 Weather Provider
**优先级**: P2  
**预估时间**: 1h  
**依赖**: Task 1.1

**描述**:
将 `src/collectors/weather.py` 迁移为 Provider 模式。

**验收标准**:
- [ ] `WeatherProvider` 类实现
- [ ] `get_weather()` 方法返回原始 JSON
- [ ] 移除缓存逻辑
- [ ] 移除解析逻辑
- [ ] 单元测试通过

**文件**:
- `src/provider/weather/__init__.py`
- `src/provider/weather/client.py`
- `tests/test_provider/test_weather.py`

---

## Phase 3: DataSource 实现

### Task 3.1: 实现 MatchDataSource
**优先级**: P0  
**预估时间**: 4h  
**依赖**: Task 1.2, Task 1.3, Task 2.1, Task 2.2

**描述**:
创建 `MatchDataSource`，支持多 Provider 回退。

**验收标准**:
- [ ] `MatchDataSource` 类实现
- [ ] `fetch(match_id)` 返回 `Match` 类型
- [ ] `fetch_upcoming(competition, days)` 返回 `List[Match]`
- [ ] FootyStats Provider 优先
- [ ] Football-Data Provider 回退
- [ ] 缓存逻辑实现
- [ ] `parse()` 方法实现
- [ ] 单元测试通过

**文件**:
- `src/datasource/match/__init__.py`
- `src/datasource/match/match_datasource.py`
- `tests/test_datasource/test_match.py`

---

### Task 3.2: 实现 TeamDataSource
**优先级**: P0  
**预估时间**: 4h  
**依赖**: Task 1.2, Task 1.3, Task 2.1, Task 2.3

**描述**:
创建 `TeamDataSource`，聚合多个 Provider 数据。

**验收标准**:
- [ ] `TeamDataSource` 类实现
- [ ] `fetch(team_id)` 返回 `Team` 类型
- [ ] FootyStats 提供基础数据
- [ ] Understat 补充 xG/PPDA 数据
- [ ] ClubElo 补充 Elo 数据
- [ ] 缓存逻辑实现
- [ ] `parse()` 方法实现
- [ ] 单元测试通过

**文件**:
- `src/datasource/team/__init__.py`
- `src/datasource/team/team_datasource.py`
- `tests/test_datasource/test_team.py`

---

### Task 3.3: 实现 StandingsDataSource
**优先级**: P1  
**预估时间**: 2h  
**依赖**: Task 1.2, Task 1.3, Task 2.1, Task 2.2

**描述**:
创建 `StandingsDataSource`，支持多 Provider 回退。

**验收标准**:
- [ ] `StandingsDataSource` 类实现
- [ ] `fetch(competition)` 返回 `List[StandingsEntry]`
- [ ] FootyStats Provider 优先
- [ ] Football-Data Provider 回退
- [ ] 缓存逻辑实现
- [ ] `parse()` 方法实现
- [ ] 单元测试通过

**文件**:
- `src/datasource/standings/__init__.py`
- `src/datasource/standings/standings_datasource.py`
- `tests/test_datasource/test_standings.py`

---

### Task 3.4: 实现 OddsDataSource
**优先级**: P1  
**预估时间**: 2h  
**依赖**: Task 1.2, Task 1.3, Task 2.5

**描述**:
创建 `OddsDataSource`。

**验收标准**:
- [ ] `OddsDataSource` 类实现
- [ ] `fetch(competition, match_id)` 返回 `Odds` 类型
- [ ] 隐含概率计算
- [ ] Vig 去除计算
- [ ] 缓存逻辑实现
- [ ] 单元测试通过

**文件**:
- `src/datasource/odds/__init__.py`
- `src/datasource/odds/odds_datasource.py`
- `tests/test_datasource/test_odds.py`

---

### Task 3.5: 实现 EloDataSource
**优先级**: P2  
**预估时间**: 1h  
**依赖**: Task 1.2, Task 1.3, Task 2.4

**描述**:
创建 `EloDataSource`。

**验收标准**:
- [ ] `EloDataSource` 类实现
- [ ] `fetch(team_name)` 返回 `Elo` 类型
- [ ] 球队名称映射
- [ ] 缓存逻辑实现
- [ ] 单元测试通过

**文件**:
- `src/datasource/elo/__init__.py`
- `src/datasource/elo/elo_datasource.py`
- `tests/test_datasource/test_elo.py`

---

### Task 3.6: 实现 WeatherDataSource
**优先级**: P2  
**预估时间**: 1h  
**依赖**: Task 1.2, Task 1.3, Task 2.6

**描述**:
创建 `WeatherDataSource`。

**验收标准**:
- [ ] `WeatherDataSource` 类实现
- [ ] `fetch(lat, lon)` 返回 `Weather` 类型
- [ ] xG 调整计算
- [ ] 缓存逻辑实现
- [ ] 单元测试通过

**文件**:
- `src/datasource/weather/__init__.py`
- `src/datasource/weather/weather_datasource.py`
- `tests/test_datasource/test_weather.py`

---

## Phase 4: 集成与测试

### Task 4.1: 更新 MatchBuilder
**优先级**: P0  
**预估时间**: 3h  
**依赖**: Phase 3 完成

**描述**:
更新 `src/aggregator/match_builder.py` 使用新的 DataSource 接口。

**验收标准**:
- [ ] 使用 `MatchDataSource` 替代 `FootyStatsClient`
- [ ] 使用 `TeamDataSource` 替代多个 client 调用
- [ ] 使用 `StandingsDataSource` 替代 `FootyStatsClient.get_league_table`
- [ ] 使用 `OddsDataSource` 替代 `OddsAPIClient`
- [ ] 使用 `EloDataSource` 替代 `ClubEloClient`
- [ ] 使用 `WeatherDataSource` 替代 `WeatherClient`
- [ ] 所有现有功能正常工作

**文件**:
- `src/aggregator/match_builder.py`

---

### Task 4.2: 添加向后兼容层
**优先级**: P0  
**预估时间**: 1h  
**依赖**: Phase 3 完成

**描述**:
更新 `src/collectors/__init__.py` 提供向后兼容。

**验收标准**:
- [ ] 旧导入路径仍然可用
- [ ] `FootyStatsClient` 别名指向 `FootyStatsProvider`
- [ ] 所有旧名称都有别名
- [ ] 弃用警告（可选）

**文件**:
- `src/collectors/__init__.py`

---

### Task 4.3: 编写集成测试
**优先级**: P1  
**预估时间**: 3h  
**依赖**: Task 4.1, Task 4.2

**描述**:
编写端到端集成测试。

**验收标准**:
- [ ] 测试完整数据获取流程
- [ ] 测试 Provider 回退
- [ ] 测试缓存行为
- [ ] 测试 `MatchBuilder` 集成
- [ ] 测试向后兼容

**文件**:
- `tests/integration/test_datasource_integration.py`

---

### Task 4.4: 更新文档
**优先级**: P2  
**预估时间**: 2h  
**依赖**: Phase 3 完成

**描述**:
更新项目文档。

**验收标准**:
- [ ] 更新 `doc/architecture.md`
- [ ] 添加 Provider 开发指南
- [ ] 添加 DataSource 开发指南
- [ ] 更新 API 使用示例

**文件**:
- `doc/architecture.md`
- `doc/provider_guide.md`
- `doc/datasource_guide.md`

---

## 任务依赖图

```
Phase 1 (基础设施)
├── Task 1.1 (Provider 基类) ─────────────────────────────────────┐
├── Task 1.2 (DataSource 基类) ← Task 1.1 ────────────────────────┤
├── Task 1.3 (标准数据类型) ──────────────────────────────────────┤
└── Task 1.4 (注册表) ← Task 1.2, Task 1.3 ───────────────────────┤
                                                                   │
Phase 2 (Provider 迁移)                                            │
├── Task 2.1 (FootyStats) ← Task 1.1 ──────────────────────────────┤
├── Task 2.2 (Football-Data) ← Task 1.1 ───────────────────────────┤
├── Task 2.3 (Understat) ← Task 1.1 ───────────────────────────────┤
├── Task 2.4 (ClubElo) ← Task 1.1 ─────────────────────────────────┤
├── Task 2.5 (Odds) ← Task 1.1 ────────────────────────────────────┤
└── Task 2.6 (Weather) ← Task 1.1 ─────────────────────────────────┤
                                                                   │
Phase 3 (DataSource 实现)                                          │
├── Task 3.1 (Match) ← Task 1.2, Task 1.3, Task 2.1, Task 2.2 ─────┤
├── Task 3.2 (Team) ← Task 1.2, Task 1.3, Task 2.1, Task 2.3 ──────┤
├── Task 3.3 (Standings) ← Task 1.2, Task 1.3, Task 2.1, Task 2.2 ─┤
├── Task 3.4 (Odds) ← Task 1.2, Task 1.3, Task 2.5 ────────────────┤
├── Task 3.5 (Elo) ← Task 1.2, Task 1.3, Task 2.4 ─────────────────┤
└── Task 3.6 (Weather) ← Task 1.2, Task 1.3, Task 2.6 ─────────────┤
                                                                   │
Phase 4 (集成与测试)                                               │
├── Task 4.1 (MatchBuilder) ← Phase 3 ─────────────────────────────┤
├── Task 4.2 (向后兼容) ← Phase 3 ──────────────────────────────────┤
├── Task 4.3 (集成测试) ← Task 4.1, Task 4.2 ───────────────────────┤
└── Task 4.4 (文档) ← Phase 3 ─────────────────────────────────────┘
```

---

## 时间估算

| Phase | 任务数 | 预估时间 |
|-------|--------|----------|
| Phase 1 | 4 | 9h |
| Phase 2 | 6 | 10h |
| Phase 3 | 6 | 14h |
| Phase 4 | 4 | 9h |
| **总计** | **20** | **42h (~5-6 天)** |

---

## 里程碑

| 里程碑 | 完成标准 | 预计日期 |
|--------|----------|----------|
| M1: 基础设施完成 | Phase 1 所有任务完成 | Day 1-2 |
| M2: Provider 迁移完成 | Phase 2 所有任务完成 | Day 2-3 |
| M3: DataSource 实现完成 | Phase 3 所有任务完成 | Day 4-5 |
| M4: 集成测试通过 | Phase 4 所有任务完成 | Day 5-6 |

---

*Goalcast Collectors Refactoring Tasks v1.0*

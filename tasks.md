# FootyStats 数据解析与缓存 - 任务分解

## 任务概览

本文档将 spec.md 中的规范分解为可执行的具体任务，按照优先级和依赖关系组织。

---

## Phase 1: 数据模型定义

### Task 1.1: 创建基础模型文件
**文件**: `provider/footystats/models.py`  
**优先级**: P0  
**估计工时**: 4 小时

#### 子任务
- [ ] 1.1.1: 创建 `FootyStatsMeta` 类（API 元数据）
- [ ] 1.1.2: 创建 `FootyStatsResponse` 泛型基类
- [ ] 1.1.3: 创建 `Pagination` 类（分页信息）
- [ ] 1.1.4: 创建枚举类型（`MatchStatus`, `LeagueType` 等）

#### 验收标准
```python
# 测试用例
from provider.footystats.models import FootyStatsMeta, FootyStatsResponse

meta = FootyStatsMeta(endpoint="/match", timestamp=datetime.now())
assert meta.endpoint == "/match"

response = FootyStatsResponse(data={"test": "data"}, meta=meta, raw_data={})
assert response.data == {"test": "data"}
assert response.raw_data == {}
```

---

### Task 1.2: 创建联赛数据模型
**文件**: `provider/footystats/models.py`  
**优先级**: P0  
**估计工时**: 3 小时

#### 子任务
- [ ] 1.2.1: 创建 `League` 类
- [ ] 1.2.2: 创建 `Season` 类
- [ ] 1.2.3: 创建 `LeagueListResponse` 类
- [ ] 1.2.4: 添加字段验证器（validator）

#### 依赖
- Task 1.1 完成

---

### Task 1.3: 创建比赛数据模型
**文件**: `provider/footystats/models.py`  
**优先级**: P0  
**估计工时**: 6 小时

#### 子任务
- [ ] 1.3.1: 创建 `MatchTeam` 类
- [ ] 1.3.2: 创建 `MatchScore` 类
- [ ] 1.3.3: 创建 `MatchOdds` 类
- [ ] 1.3.4: 创建 `Match` 类（核心模型）
- [ ] 1.3.5: 创建 `MatchListResponse` 类
- [ ] 1.3.6: 添加 datetime 解析验证器

#### 依赖
- Task 1.1 完成

#### 验收标准
```python
match = Match(
    id="123",
    season_id="456",
    home_team=MatchTeam(id="1", name="Home FC"),
    away_team=MatchTeam(id="2", name="Away FC"),
    score=MatchScore(home=2, away=1),
    kickoff_time=datetime.now(),
    status=MatchStatus.FINISHED
)
assert match.id == "123"
assert match.score.home == 2
```

---

### Task 1.4: 创建球队数据模型
**文件**: `provider/footystats/models.py`  
**优先级**: P0  
**估计工时**: 6 小时

#### 子任务
- [ ] 1.4.1: 创建 `TeamStats` 类（完整统计字段）
- [ ] 1.4.2: 创建 `TeamForm` 类
- [ ] 1.4.3: 创建 `Team` 类
- [ ] 1.4.4: 创建 `TeamResponse` 类
- [ ] 1.4.5: 添加数值范围验证器

#### 依赖
- Task 1.1 完成

---

### Task 1.5: 创建球员和裁判数据模型
**文件**: `provider/footystats/models.py`  
**优先级**: P1  
**估计工时**: 4 小时

#### 子任务
- [ ] 1.5.1: 创建 `PlayerStats` 类
- [ ] 1.5.2: 创建 `Player` 类
- [ ] 1.5.3: 创建 `PlayerListResponse` 类
- [ ] 1.5.4: 创建 `RefereeStats` 类
- [ ] 1.5.5: 创建 `Referee` 类
- [ ] 1.5.6: 创建 `RefereeListResponse` 类

#### 依赖
- Task 1.1 完成

---

### Task 1.6: 创建积分榜数据模型
**文件**: `provider/footystats/models.py`  
**优先级**: P1  
**估计工时**: 3 小时

#### 子任务
- [ ] 1.6.1: 创建 `StandingsEntry` 类
- [ ] 1.6.2: 创建 `StandingsTable` 类
- [ ] 1.6.3: 创建 `StandingsResponse` 类

#### 依赖
- Task 1.1 完成

---

### Task 1.7: 创建缓存数据模型
**文件**: `datasource/cache_models.py`  
**优先级**: P1  
**估计工时**: 3 小时

#### 子任务
- [ ] 1.7.1: 创建 `CacheMetadata` 类
- [ ] 1.7.2: 创建 `CachedMatch` 类
- [ ] 1.7.3: 创建 `CachedTeam` 类
- [ ] 1.7.4: 创建 `CachedLeagueTable` 类
- [ ] 1.7.5: 添加 checksum 计算方法

#### 依赖
- Task 1.3, 1.4 完成

---

### Task 1.8: 编写模型单元测试
**文件**: `tests/provider/footystats/test_models.py`  
**优先级**: P1  
**估计工时**: 4 小时

#### 子任务
- [ ] 1.8.1: 测试基础模型
- [ ] 1.8.2: 测试比赛模型
- [ ] 1.8.3: 测试球队模型
- [ ] 1.8.4: 测试验证器
- [ ] 1.8.5: 测试边界情况

#### 验收标准
- 模型测试覆盖率 > 90%
- 所有验证器都有对应测试

---

## Phase 2: Parser 实现

### Task 2.1: 创建 Parser 基类
**文件**: `provider/footystats/parser.py`  
**优先级**: P0  
**估计工时**: 3 小时

#### 子任务
- [ ] 2.1.1: 创建 `FootyStatsParser` 类
- [ ] 2.1.2: 实现 `_safe_get` 工具方法
- [ ] 2.1.3: 实现 `_parse_datetime` 方法
- [ ] 2.1.4: 实现 `_parse_status` 方法
- [ ] 2.1.5: 实现 `_calculate_form_score` 方法

#### 验收标准
```python
parser = FootyStatsParser()
assert parser._safe_get({"a": {"b": 1}}, "a", "b") == 1
assert parser._safe_get({}, "a", "b", default=0) == 0
```

---

### Task 2.2: 实现联赛列表解析
**文件**: `provider/footystats/parser.py`  
**优先级**: P0  
**估计工时**: 2 小时

#### 子任务
- [ ] 2.2.1: 实现 `parse_league_list` 方法
- [ ] 2.2.2: 处理字段映射（兼容不同 API 响应格式）
- [ ] 2.2.3: 添加错误处理和日志记录

#### 依赖
- Task 1.2, 2.1 完成

---

### Task 2.3: 实现比赛详情解析
**文件**: `provider/footystats/parser.py`  
**优先级**: P0  
**估计工时**: 4 小时

#### 子任务
- [ ] 2.3.1: 实现 `parse_match_details` 方法
- [ ] 2.3.2: 解析球队信息
- [ ] 2.3.3: 解析比分信息
- [ ] 2.3.4: 解析赔率信息
- [ ] 2.3.5: 解析高级统计（xG, 控球率等）
- [ ] 2.3.6: 保留原始数据引用

#### 依赖
- Task 1.3, 2.1 完成

---

### Task 2.4: 实现球队数据解析
**文件**: `provider/footystats/parser.py`  
**优先级**: P0  
**估计工时**: 4 小时

#### 子任务
- [ ] 2.4.1: 实现 `parse_team` 方法
- [ ] 2.4.2: 解析统计数据
- [ ] 2.4.3: 解析近期状态
- [ ] 2.4.4: 计算状态评分

#### 依赖
- Task 1.4, 2.1 完成

---

### Task 2.5: 实现其他端点解析
**文件**: `provider/footystats/parser.py`  
**优先级**: P1  
**估计工时**: 6 小时

#### 子任务
- [ ] 2.5.1: 实现 `parse_league_stats` 方法
- [ ] 2.5.2: 实现 `parse_league_matches` 方法
- [ ] 2.5.3: 实现 `parse_league_teams` 方法
- [ ] 2.5.4: 实现 `parse_league_players` 方法
- [ ] 2.5.5: 实现 `parse_league_tables` 方法
- [ ] 2.5.6: 实现 `parse_referees` 方法
- [ ] 2.5.7: 实现 `parse_player_stats` 方法

#### 依赖
- Task 1.5, 1.6, 2.1 完成

---

### Task 2.6: 编写 Parser 单元测试
**文件**: `tests/provider/footystats/test_parser.py`  
**优先级**: P1  
**估计工时**: 6 小时

#### 子任务
- [ ] 2.6.1: 准备测试数据（真实 API 响应样本）
- [ ] 2.6.2: 测试联赛列表解析
- [ ] 2.6.3: 测试比赛详情解析
- [ ] 2.6.4: 测试球队数据解析
- [ ] 2.6.5: 测试边界情况和错误处理
- [ ] 2.6.6: 测试字段缺失情况

#### 验收标准
- Parser 测试覆盖率 > 85%
- 所有解析方法都有对应测试

---

## Phase 3: Provider 增强

### Task 3.1: 增强 FootyStatsProvider
**文件**: `provider/footystats/client.py`  
**优先级**: P0  
**估计工时**: 4 小时

#### 子任务
- [ ] 3.1.1: 导入 Parser 和 Models
- [ ] 3.1.2: 添加 `_parser` 属性
- [ ] 3.1.3: 实现 `get_league_list_typed` 方法
- [ ] 3.1.4: 实现 `get_match_details_typed` 方法
- [ ] 3.1.5: 实现 `get_team_typed` 方法
- [ ] 3.1.6: 实现其他端点的 typed 版本

#### 依赖
- Phase 1, Phase 2 完成

#### 验收标准
```python
provider = FootyStatsProvider()
response = await provider.get_match_details_typed(12345)
assert isinstance(response, MatchResponse)
assert isinstance(response.data, Match)
```

---

### Task 3.2: 保持向后兼容
**文件**: `provider/footystats/client.py`  
**优先级**: P0  
**估计工时**: 2 小时

#### 子任务
- [ ] 3.2.1: 确保现有方法签名不变
- [ ] 3.2.2: 添加类型提示
- [ ] 3.2.3: 添加迁移文档注释

#### 依赖
- Task 3.1 完成

---

### Task 3.3: Provider 集成测试
**文件**: `tests/provider/footystats/test_client.py`  
**优先级**: P1  
**估计工时**: 4 小时

#### 子任务
- [ ] 3.3.1: Mock API 响应
- [ ] 3.3.2: 测试 typed 方法
- [ ] 3.3.3: 测试错误处理
- [ ] 3.3.4: 测试限流逻辑
- [ ] 3.3.5: 测试重试逻辑

---

## Phase 4: DataSource 增强

### Task 4.1: 创建缓存管理器
**文件**: `datasource/cache_manager.py`  
**优先级**: P0  
**估计工时**: 6 小时

#### 子任务
- [ ] 4.1.1: 实现 `CacheManager` 单例类
- [ ] 4.1.2: 实现 `get`/`set`/`delete` 方法
- [ ] 4.1.3: 实现 TTL 管理
- [ ] 4.1.4: 实现定期清理任务
- [ ] 4.1.5: 实现缓存统计方法
- [ ] 4.1.6: 添加日志记录

#### 依赖
- Task 1.7 完成

#### 验收标准
```python
from datasource.cache_manager import cache_manager

cache_manager.set("test_key", {"data": 123}, ttl=60)
assert cache_manager.get("test_key") == {"data": 123}

stats = cache_manager.get_stats()
assert 'hit_rate' in stats
```

---

### Task 4.2: 增强 MatchDataSource
**文件**: `datasource/match/match_datasource.py`  
**优先级**: P0  
**估计工时**: 6 小时

#### 子任务
- [ ] 4.2.1: 导入缓存管理器和缓存模型
- [ ] 4.2.2: 添加 `_history_cache` 属性
- [ ] 4.2.3: 增强 `fetch` 方法支持历史缓存
- [ ] 4.2.4: 实现 `_add_to_history` 方法
- [ ] 4.2.5: 实现 `_update_cache_access` 方法
- [ ] 4.2.6: 实现 `get_history` 方法
- [ ] 4.2.7: 实现 `_compute_checksum` 方法

#### 依赖
- Task 4.1 完成

---

### Task 4.3: 增强 TeamDataSource
**文件**: `datasource/team/team_datasource.py`  
**优先级**: P0  
**估计工时**: 6 小时

#### 子任务
- [ ] 4.3.1: 添加 `_historical_stats` 属性
- [ ] 4.3.2: 增强 `fetch` 方法
- [ ] 4.3.3: 实现 `_accumulate_stats` 方法
- [ ] 4.3.4: 实现 `get_stats_history` 方法
- [ ] 4.3.5: 实现 `get_stats_trend` 方法

#### 依赖
- Task 4.1 完成

#### 验收标准
```python
team = await team_ds.fetch(team_id="123")
history = team_ds.get_stats_history("123")
assert len(history) > 0

trend = team_ds.get_stats_trend("123", "xg_for")
assert 'current' in trend
assert 'trend' in trend
```

---

### Task 4.4: 增强其他 DataSource
**文件**: `datasource/*/datasource.py`  
**优先级**: P1  
**估计工时**: 8 小时

#### 子任务
- [ ] 4.4.1: 增强 `StandingsDataSource`
- [ ] 4.4.2: 增强 `PlayerDataSource`（如存在）
- [ ] 4.4.3: 增强 `RefereeDataSource`（如存在）

---

### Task 4.5: DataSource 集成测试
**文件**: `tests/datasource/test_*.py`  
**优先级**: P1  
**估计工时**: 6 小时

#### 子任务
- [ ] 4.5.1: 测试 MatchDataSource 缓存
- [ ] 4.5.2: 测试 TeamDataSource 统计积累
- [ ] 4.5.3: 测试历史数据查询
- [ ] 4.5.4: 测试缓存失效逻辑

---

## Phase 5: 配置和监控

### Task 5.1: 添加缓存配置
**文件**: `config/settings.py`  
**优先级**: P0  
**估计工时**: 2 小时

#### 子任务
- [ ] 5.1.1: 创建 `CacheSettings` 类
- [ ] 5.1.2: 定义 TTL 配置项
- [ ] 5.1.3: 定义历史缓存配置
- [ ] 5.1.4: 定义清理策略配置
- [ ] 5.1.5: 在 `Settings` 中添加 `CACHE` 属性

---

### Task 5.2: 添加缓存监控
**文件**: `utils/cache_monitor.py`  
**优先级**: P2  
**估计工时**: 4 小时

#### 子任务
- [ ] 5.2.1: 实现缓存命中率监控
- [ ] 5.2.2: 实现缓存大小监控
- [ ] 5.2.3: 实现缓存清理日志
- [ ] 5.2.4: 添加 Prometheus 指标（如使用）

---

### Task 5.3: 性能测试
**文件**: `tests/performance/test_cache.py`  
**优先级**: P2  
**估计工时**: 4 小时

#### 子任务
- [ ] 5.3.1: 测试缓存命中率
- [ ] 5.3.2: 测试解析性能
- [ ] 5.3.3: 测试内存占用
- [ ] 5.3.4: 生成性能报告

---

## Phase 6: 文档和迁移

### Task 6.1: 更新 API 文档
**文件**: `provider/footystats/README.md`  
**优先级**: P1  
**估计工时**: 3 小时

#### 子任务
- [ ] 6.1.1: 更新数据类型说明
- [ ] 6.1.2: 添加使用示例
- [ ] 6.1.3: 添加缓存机制说明
- [ ] 6.1.4: 更新端点文档

---

### Task 6.2: 编写迁移指南
**文件**: `docs/migration_guide.md`  
**优先级**: P1  
**估计工时**: 2 小时

#### 子任务
- [ ] 6.2.1: 说明新旧 API 对比
- [ ] 6.2.2: 提供代码迁移示例
- [ ] 6.2.3: 列出破坏性变更
- [ ] 6.2.4: 提供回滚方案

---

### Task 6.3: 编写使用文档
**文件**: `docs/usage_guide.md`  
**优先级**: P2  
**估计工时**: 3 小时

#### 子任务
- [ ] 6.3.1: 基础使用示例
- [ ] 6.3.2: 高级功能示例
- [ ] 6.3.3: 最佳实践
- [ ] 6.3.4: 常见问题解答

---

## 任务依赖关系图

```
Phase 1 (数据模型)
├─ Task 1.1 → Task 1.2, 1.3, 1.4, 1.5, 1.6
└─ Task 1.3, 1.4 → Task 1.7

Phase 2 (Parser)
├─ Task 2.1 → Task 2.2, 2.3, 2.4, 2.5
├─ Task 1.2, 2.1 → Task 2.2
├─ Task 1.3, 2.1 → Task 2.3
├─ Task 1.4, 2.1 → Task 2.4
└─ Task 2.x → Task 2.6 (测试)

Phase 3 (Provider)
├─ Phase 1, Phase 2 → Task 3.1
└─ Task 3.1 → Task 3.2, 3.3

Phase 4 (DataSource)
├─ Task 1.7 → Task 4.1
├─ Task 4.1 → Task 4.2, 4.3, 4.4
└─ Task 4.x → Task 4.5 (测试)

Phase 5 (配置监控)
├─ Task 4.1 → Task 5.1
└─ Task 5.1 → Task 5.2, 5.3

Phase 6 (文档)
└─ Phase 1-5 → Task 6.x
```

---

## 总工时估算

| Phase | 工时（小时） | 工作日（按 8 小时/天） |
|-------|-------------|---------------------|
| Phase 1: 数据模型 | 33 | ~4 天 |
| Phase 2: Parser | 25 | ~3 天 |
| Phase 3: Provider | 10 | ~1.5 天 |
| Phase 4: DataSource | 30 | ~4 天 |
| Phase 5: 配置监控 | 10 | ~1.5 天 |
| Phase 6: 文档 | 8 | ~1 天 |
| **总计** | **116** | **~15 天** |

---

## 优先级建议

### Sprint 1 (Week 1-2): 核心功能
- Task 1.1, 1.3, 1.4 (基础模型)
- Task 2.1, 2.3, 2.4 (核心 Parser)
- Task 3.1, 3.2 (Provider 增强)
- Task 4.1 (缓存管理器)

### Sprint 2 (Week 3-4): 完整功能
- Task 1.2, 1.5, 1.6, 1.7 (剩余模型)
- Task 2.2, 2.5 (剩余 Parser)
- Task 4.2, 4.3 (DataSource 增强)
- Task 5.1 (配置)

### Sprint 3 (Week 5): 测试和文档
- Task 1.8, 2.6, 3.3, 4.5 (测试)
- Task 5.2, 5.3 (监控和性能)
- Task 6.x (文档)

---

## 风险和挑战

### 高风险
1. **API 响应格式不一致**: 不同端点可能返回不同格式的数据
   - 缓解：准备充足的测试数据样本
   - 缓解：Parser 设计要足够灵活

2. **性能开销**: Pydantic 模型解析可能影响性能
   - 缓解：性能测试验证
   - 缓解：考虑可选的跳过解析模式

### 中风险
1. **向后兼容性**: 现有代码可能依赖旧的数据格式
   - 缓解：保留原有方法，新增 typed 方法
   - 缓解：提供详细的迁移指南

2. **缓存一致性**: 多个 DataSource 可能缓存同一数据
   - 缓解：统一的缓存管理器
   - 缓解：checksum 验证

---

## 下一步行动

1. **立即开始**: Task 1.1 (基础模型定义)
2. **并行进行**: Task 1.3, 1.4 (比赛和球队模型)
3. **等待依赖**: Phase 2+ 的任务等待 Phase 1 完成

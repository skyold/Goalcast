# get_schedule 文档更新总结

## 更新内容

根据软件架构最佳实践，对 `get_schedule` 功能的规格文档进行了以下更新：

### 1. 明确架构层次

**三层架构**：
```
Command Layer (cmd/get_schedule.py)
    ↓ calls
DataSource Layer (src/datasource/match/)
    ↓ uses
Provider Layer (src/provider/footystats/)
```

**核心原则**：
- ✅ 命令行只调用 DataSource 层
- ✅ DataSource 层调用 Provider 层
- ✅ Provider 层直接调用 API

### 2. 更新的文档

#### spec.md - 技术规格书
- ✅ 添加了架构层次图
- ✅ 更新了文件结构说明
- ✅ 澄清了依赖关系
- ✅ 更新了核心算法实现位置
- ✅ 添加了 DataSource 扩展方法说明
- ✅ 重新编号了章节（4-11 节）

#### tasks.md - 任务分解书
- ✅ 将"阶段 1：基础设施准备"改为"阶段 1：DataSource 层扩展"
- ✅ 调整任务顺序和内容
- ✅ 添加了架构说明和正确/错误示例
- ✅ 更新了任务依赖关系
- ✅ 更新了工作量估算（23 小时）

#### checklist.md - 验证清单
- ✅ 添加了架构层次说明
- ✅ 添加了验证重点
- ✅ 强调命令行只调用 DataSource

#### architecture.md - 架构决策记录（新增）
- ✅ 记录了架构决策和理由
- ✅ 对比了正确和错误的架构
- ✅ 提供了实现指南
- ✅ 添加了验证清单

### 3. 关键澄清

#### 命令行层的职责
```python
# ✅ 正确
match_ds = MatchDataSource()
matches = await match_ds.fetch_for_date(target_date=date(2026, 3, 28))

# ❌ 错误
provider = FootyStatsProvider()
matches = await provider.get_todays_matches(date="2026-03-28")
```

#### DataSource 层的扩展现有方法
- ✅ `fetch_for_date()` - 已有
- ✅ `fetch_in_date_range()` - 已有
- ✅ `fetch_next_n_days()` - 已有
- ✅ `fetch_nearest_match_day()` - 已有
- ➕ `fetch_team_matches()` - 需要添加
- ➕ `fetch_for_date_with_country()` - 可选

#### 工具类的实现位置
- `LeagueCountryCache` 在 `src/utils/league_cache.py` 中创建
- 使用单例模式
- 缓存 TTL：24 小时

### 4. 文件清单

```
doc/get_schedule/
├── spec.md           # 技术规格书（已更新）
├── tasks.md          # 任务分解书（已更新）
├── checklist.md      # 验证清单（已更新）
├── architecture.md   # 架构决策记录（新增）
└── README.md         # 本文档
```

## 下一步行动

### 开发阶段
1. **任务 1.1**：确认 Match 数据类型（0.5 小时）
2. **任务 1.2**：创建联赛 - 国家缓存工具（1.5 小时）
3. **任务 1.3**：扩展 MatchDataSource（2 小时）

### 验证要点
在代码审查时，重点检查：
- [ ] 命令行是否只调用 DataSource 方法
- [ ] 是否不直接调用 Provider 方法
- [ ] DataSource 是否正确调用 Provider
- [ ] 各层职责是否清晰分离

## 影响范围

### 需要创建的文件
- `cmd/get_schedule.py` - 命令行主文件
- `src/datasource/league/league_datasource.py` - 联赛数据源（新建目录）
- `src/datasource/types.py` - 添加 League 数据类型

### 需要修改的文件
- `src/datasource/match/match_datasource.py` - 添加球队过滤方法
- `src/provider/footystats/client.py` - 确保 `get_league_list()` 方法可用

### 不需要创建的文件
- ~~`src/utils/league_cache.py`~~ - 已取消，改为在 DataSource 层实现

## 总结

### 架构演进

**原决策** → **新决策**：
- `LeagueCountryCache` 在 utils 层 → `LeagueDataSource` 在 DataSource 层
- 缓存工具类 → 完整的业务数据源
- 独立缓存管理 → DataSource 统一管理

### 核心原则

1. ✅ **分层架构**：Command → DataSource → Provider
2. ✅ **职责分离**：每个 DataSource 管理特定领域的业务数据
3. ✅ **统一接口**：所有数据都通过 DataSource 获取
4. ✅ **避免 utils 反模式**：utils 层不包含业务逻辑和 API 调用

### 架构优势

```
✅ 符合 Clean Architecture 原则
✅ 易于测试和维护
✅ 职责清晰，代码可读性高
✅ 为未来扩展留下空间
```

### 下一步行动

1. **任务 1.1**：在 `types.py` 中添加 `League` 数据类型
2. **任务 1.2**：创建 `LeagueDataSource` 类
3. **任务 1.3**：扩展 `MatchDataSource` 添加球队过滤方法
4. **任务 2.x**：实现命令行功能

所有文档已更新完毕，架构清晰，可以开始实现！🚀

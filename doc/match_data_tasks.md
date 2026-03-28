# Match Data Datasource 实现任务列表

## 任务分解

### Phase 1: 基础架构搭建 (预计 2-3 天)

#### Task 1.1: 创建数据实体类 - MatchBasicData
- [ ] 创建文件 `src/domain/entities/match_basic.py`
- [ ] 实现 `MatchBasicData` 数据类
- [ ] 添加 `__post_init__` 方法初始化 extra 字段
- [ ] 添加辅助属性 `is_finished`, `is_live`
- [ ] 编写单元测试
- **优先级**: High
- **预计时间**: 2 小时
- **依赖**: 无

#### Task 1.2: 创建数据实体类 - MatchStatsData
- [ ] 创建文件 `src/domain/entities/match_stats.py`
- [ ] 实现 `MatchStatsData` 数据类
- [ ] 实现所有统计字段（射门、控球、角球等）
- [ ] 添加 `has_valid_stats` 属性
- [ ] 编写单元测试
- **优先级**: High
- **预计时间**: 2 小时
- **依赖**: Task 1.1

#### Task 1.3: 创建数据实体类 - MatchAdvancedData
- [ ] 创建文件 `src/domain/entities/match_advanced.py`
- [ ] 实现 `LineupPlayer` 辅助类
- [ ] 实现 `MatchAdvancedData` 数据类
- [ ] 添加 xG、进攻等高级统计字段
- [ ] 添加 `has_xg`, `has_lineups` 属性
- [ ] 编写单元测试
- [ ] **注意**: 需要查看 Match Details API 的实际返回格式
- **优先级**: High
- **预计时间**: 3 小时
- **依赖**: Task 1.1

#### Task 1.4: 创建数据实体类 - MatchOddsData
- [ ] 创建文件 `src/domain/entities/match_odds.py`
- [ ] 实现 `MatchOddsData` 数据类
- [ ] 实现 `calculate_implied_probabilities` 方法
- [ ] 添加大小球、BTTS 等赔率字段
- [ ] 编写单元测试
- **优先级**: Medium
- **预计时间**: 2 小时
- **依赖**: Task 1.1

#### Task 1.5: 创建数据实体类 - MatchTeamsData
- [ ] 创建文件 `src/domain/entities/match_teams.py`
- [ ] 实现 `TeamForm` 类（球队状态）
- [ ] 实现 `TeamSeasonStats` 类（赛季统计）
- [ ] 实现 `MatchTeamsData` 主类
- [ ] 添加 `form_difference`, `strength_difference` 属性
- [ ] 编写单元测试
- **优先级**: High
- **预计时间**: 4 小时
- **依赖**: Task 1.1

#### Task 1.6: 创建数据实体类 - MatchOthersData
- [ ] 创建文件 `src/domain/entities/match_others.py`
- [ ] 实现 `MatchOthersData` 数据类
- [ ] 添加球员、裁判、联赛统计字段
- [ ] 编写单元测试
- **优先级**: Low
- **预计时间**: 2 小时
- **依赖**: Task 1.1

#### Task 1.7: 创建聚合数据类 - FullMatchData
- [ ] 创建文件 `src/domain/entities/full_match_data.py`
- [ ] 实现 `FullMatchData` 数据类
- [ ] 组合所有数据类别（basic, stats, advanced, odds, teams, others）
- [ ] 实现 `is_complete` 属性
- [ ] 预留 `to_feature_vector` 接口（TODO）
- [ ] 编写单元测试
- **优先级**: Medium
- **预计时间**: 2 小时
- **依赖**: Task 1.1-1.6

---

### Phase 2: Datasource 层实现 (预计 3-4 天)

#### Task 2.1: 创建 MatchDataDataSource 基础框架
- [ ] 创建文件 `src/datasource/footystats/match_datasource.py`
- [ ] 实现 `MatchDataDataSource` 类
- [ ] 实现类初始化和 Provider 注入
- [ ] 添加日志记录
- [ ] 实现错误处理框架
- [ ] 编写集成测试框架
- **优先级**: High
- **预计时间**: 2 小时
- **依赖**: Phase 1 完成

#### Task 2.2: 实现 get_match_basic 方法
- [ ] 实现 `get_match_basic(match_id)` 方法
- [ ] 调用 Provider 的 `get_match_details`
- [ ] 实现 `_parse_basic_data` 解析方法
- [ ] 处理日期转换和状态映射
- [ ] 编写单元测试（mock Provider）
- **优先级**: High
- **预计时间**: 3 小时
- **依赖**: Task 1.1, Task 2.1

#### Task 2.3: 实现 get_match_stats 方法
- [ ] 实现 `get_match_stats(match_id)` 方法
- [ ] 实现 `_parse_stats_data` 解析方法
- [ ] 处理默认值（-1 表示无效数据）
- [ ] 验证统计数据完整性
- [ ] 编写单元测试
- **优先级**: High
- **预计时间**: 3 小时
- **依赖**: Task 1.2, Task 2.2

#### Task 2.4: 实现 get_match_advanced 方法
- [ ] 实现 `get_match_advanced(match_id)` 方法
- [ ] 实现 `_parse_advanced_data` 解析方法
- [ ] 解析阵容数据（lineups）
- [ ] 解析交锋记录（h2h）
- [ ] 解析趋势分析（trends）
- [ ] 解析天气数据
- [ ] 编写单元测试
- **优先级**: High
- **预计时间**: 4 小时
- **依赖**: Task 1.3, Task 2.3

#### Task 2.5: 实现 get_match_odds 方法
- [ ] 实现 `get_match_odds(match_id)` 方法
- [ ] 实现 `_parse_odds_data` 解析方法
- [ ] 调用 `calculate_implied_probabilities`
- [ ] 处理赔率对比数据
- [ ] 编写单元测试
- **优先级**: Medium
- **预计时间**: 3 小时
- **依赖**: Task 1.4, Task 2.4

#### Task 2.6: 实现 get_match_teams 方法
- [ ] 实现 `get_match_teams(match_id)` 方法
- [ ] 实现 `_get_team_form` 方法（调用 LastX API）
- [ ] 实现 `_get_team_season_stats` 方法（调用 League Teams API）
- [ ] 实现 `_get_h2h_data` 方法
- [ ] 组装 `MatchTeamsData` 对象
- [ ] 编写单元测试
- **优先级**: High
- **预计时间**: 5 小时
- **依赖**: Task 1.5, Task 2.5

#### Task 2.7: 实现 get_match_others 方法
- [ ] 实现 `get_match_others(match_id)` 方法
- [ ] 根据需要获取其他数据
- [ ] 编写单元测试
- **优先级**: Low
- **预计时间**: 3 小时
- **依赖**: Task 1.6, Task 2.6

#### Task 2.8: 实现 get_full_match_data 方法
- [ ] 实现 `get_full_match_data(match_id)` 方法
- [ ] 按顺序调用各类数据方法
- [ ] 组装 `FullMatchData` 对象
- [ ] 添加数据完整性检查
- [ ] 编写集成测试
- **优先级**: Medium
- **预计时间**: 3 小时
- **依赖**: Task 2.2-2.7

#### Task 2.9: 实现 get_recent_matches 方法
- [ ] 实现 `get_recent_matches(days)` 方法
- [ ] 循环调用 `get_todays_matches`
- [ ] 解析并返回 `MatchBasicData` 列表
- [ ] 处理分页和日期边界
- [ ] 编写单元测试
- **优先级**: High
- **预计时间**: 3 小时
- **依赖**: Task 2.2

---

### Phase 3: Provider 层验证 (预计 1 天)

#### Task 3.1: 验证 Provider API 完整性
- [ ] 检查 `client.py` 是否覆盖所有 16 个端点
- [ ] 验证每个端点的参数和返回值
- [ ] 查看 API 文档确认字段映射
- [ ] 记录需要补充的端点（如有）
- **优先级**: High
- **预计时间**: 2 小时
- **依赖**: 无

#### Task 3.2: 添加 Provider 数据验证
- [ ] 为关键端点添加数据验证
- [ ] 添加字段类型检查
- [ ] 添加缺失字段日志
- [ ] 编写验证测试
- **优先级**: Medium
- **预计时间**: 3 小时
- **依赖**: Task 3.1

---

### Phase 4: CMD 层实现 (预计 2-3 天)

#### Task 4.1: 创建 CMD 基础框架
- [ ] 创建文件 `src/cmd/match_data_cmd.py`
- [ ] 实现 `MatchDataCMD` 类
- [ ] 注入 Datasource
- [ ] 实现所有独立命令方法
- [ ] 添加异常处理
- **优先级**: High
- **预计时间**: 2 小时
- **依赖**: Phase 2 完成

#### Task 4.2: 实现数据展示方法
- [ ] 实现 `_print_matches` 方法
- [ ] 实现 `_print_basic` 方法
- [ ] 实现 `_print_stats` 方法
- [ ] 实现 `_print_advanced` 方法
- [ ] 实现 `_print_odds` 方法
- [ ] 实现 `_print_teams` 方法
- [ ] 实现 `_print_others` 方法
- [ ] 实现 `_print_full` 方法
- **优先级**: High
- **预计时间**: 5 小时
- **依赖**: Task 4.1

#### Task 4.3: 实现 CLI 入口
- [ ] 实现 `main()` 函数
- [ ] 解析命令行参数
- [ ] 路由到对应命令
- [ ] 添加帮助信息
- [ ] 测试所有命令
- **优先级**: High
- **预计时间**: 3 小时
- **依赖**: Task 4.2

---

### Phase 5: 测试和优化 (预计 2-3 天)

#### Task 5.1: 编写单元测试
- [ ] 为所有实体类编写测试
- [ ] 为 Datasource 方法编写测试
- [ ] Mock Provider 响应
- [ ] 测试边界情况
- [ ] 达到 80%+ 覆盖率
- **优先级**: High
- **预计时间**: 6 小时
- **依赖**: Phase 2 完成

#### Task 5.2: 编写集成测试
- [ ] 测试完整数据获取流程
- [ ] 测试错误处理
- [ ] 测试 API 超时场景
- [ ] 测试数据一致性
- **优先级**: High
- **预计时间**: 4 小时
- **依赖**: Task 5.1

#### Task 5.3: 性能优化
- [ ] 分析数据获取耗时
- [ ] 实现并行数据获取（如适用）
- [ ] 添加缓存机制（可选）
- [ ] 优化解析逻辑
- **优先级**: Medium
- **预计时间**: 4 小时
- **依赖**: Task 5.2

#### Task 5.4: 错误处理增强
- [ ] 添加重试机制
- [ ] 完善错误日志
- [ ] 处理 API 限流
- [ ] 添加降级策略
- **优先级**: High
- **预计时间**: 3 小时
- **依赖**: Task 5.2

---

### Phase 6: 文档和交付 (预计 1 天)

#### Task 6.1: 编写使用文档
- [ ] 编写 Datasource 使用示例
- [ ] 编写 CMD 操作指南
- [ ] 添加 API 调用流程图
- [ ] 更新 README
- **优先级**: Medium
- **预计时间**: 3 小时
- **依赖**: Phase 5 完成

#### Task 6.2: 代码审查
- [ ] 自查代码规范
- [ ] 添加代码注释
- [ ] 类型注解检查
- [ ] 日志规范性检查
- **优先级**: High
- **预计时间**: 3 小时
- **依赖**: Phase 5 完成

#### Task 6.3: 交付演示
- [ ] 准备演示脚本
- [ ] 录制演示视频（可选）
- [ ] 收集反馈
- [ ] 迭代改进
- **优先级**: Medium
- **预计时间**: 2 小时
- **依赖**: Task 6.1

---

## 依赖关系说明

### 与现有代码的关系

```
现有代码:
  src/provider/footystats/client.py (FootyStatsProvider)
      ↓ 被依赖
新代码:
  src/datasource/footystats/match_datasource.py (MatchDataDataSource)
      ↓ 使用
  src/cmd/match_data_cmd.py (命令行入口)
```

### Datasource 依赖 Provider

- `MatchDataDataSource` 依赖 `FootyStatsProvider`
- Provider 层保持不变，不需要修改
- Datasource 层负责组合多个 Provider 调用

### 数据流向

```
用户命令 (CMD)
    ↓
MatchDataDataSource
    ↓
FootyStatsProvider (现有)
    ↓
FootyStats API
```

---

## 预估总工时

| Phase | 内容 | 时间 |
|-------|------|------|
| Phase 1 | 基础架构（7 个实体类） | 2 天 |
| Phase 2 | Datasource 实现（9 个方法） | 4 天 |
| Phase 3 | Provider 验证 | 0.5 天 |
| Phase 4 | CMD 实现 | 2 天 |
| Phase 5 | 测试优化 | 2 天 |
| Phase 6 | 文档交付 | 1 天 |
| **总计** | | **11.5 天** |

**最快 MVP**: 5-6 天（只实现基础数据 + 统计数据 + 高级数据 + CMD 基础）

---

## 下一步行动

1. **立即开始**: Task 1.1 - 创建 MatchBasicData
2. **并行进行**: Task 3.1 - 验证 Provider API 完整性
3. **完成后通知**: 每个 Task 完成后更新状态

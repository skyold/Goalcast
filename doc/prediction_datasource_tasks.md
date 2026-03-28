# Prediction Datasource 实现任务列表

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

#### Task 1.7: 创建聚合数据类 - FullPredictionData
- [ ] 创建文件 `src/domain/entities/full_prediction_data.py`
- [ ] 实现 `FullPredictionData` 数据类
- [ ] 组合所有 Layer 数据
- [ ] 实现 `is_complete` 属性
- [ ] 预留 `to_feature_vector` 接口（TODO）
- [ ] 编写单元测试
- **优先级**: Medium
- **预计时间**: 2 小时
- **依赖**: Task 1.1-1.6

---

### Phase 2: Datasource 层实现 (预计 3-4 天)

#### Task 2.1: 创建 PredictionMatchDataSource 基础框架
- [ ] 创建文件 `src/datasource/footystats/prediction_datasource.py`
- [ ] 实现类初始化和 Provider 注入
- [ ] 添加日志记录
- [ ] 实现错误处理框架
- [ ] 编写集成测试框架
- **优先级**: High
- **预计时间**: 2 小时
- **依赖**: Phase 1 完成

#### Task 2.2: 实现 get_layer1_basic 方法
- [ ] 实现 `get_layer1_basic(match_id)` 方法
- [ ] 调用 Provider 的 `get_match_details`
- [ ] 实现 `_parse_basic_data` 解析方法
- [ ] 处理日期转换和状态映射
- [ ] 编写单元测试（mock Provider）
- **优先级**: High
- **预计时间**: 3 小时
- **依赖**: Task 1.1, Task 2.1

#### Task 2.3: 实现 get_layer2_stats 方法
- [ ] 实现 `get_layer2_stats(match_id)` 方法
- [ ] 实现 `_parse_stats_data` 解析方法
- [ ] 处理默认值（-1 表示无效数据）
- [ ] 验证统计数据完整性
- [ ] 编写单元测试
- **优先级**: High
- **预计时间**: 3 小时
- **依赖**: Task 1.2, Task 2.2

#### Task 2.4: 实现 get_layer3_advanced 方法
- [ ] 实现 `get_layer3_advanced(match_id)` 方法
- [ ] 实现 `_parse_advanced_data` 解析方法
- [ ] 解析阵容数据（lineups）
- [ ] 解析交锋记录（h2h）
- [ ] 解析趋势分析（trends）
- [ ] 解析天气数据
- [ ] 编写单元测试
- **优先级**: High
- **预计时间**: 4 小时
- **依赖**: Task 1.3, Task 2.3

#### Task 2.5: 实现 get_layer4_odds 方法
- [ ] 实现 `get_layer4_odds(match_id)` 方法
- [ ] 实现 `_parse_odds_data` 解析方法
- [ ] 调用 `calculate_implied_probabilities`
- [ ] 处理赔率对比数据
- [ ] 编写单元测试
- **优先级**: Medium
- **预计时间**: 3 小时
- **依赖**: Task 1.4, Task 2.4

#### Task 2.6: 实现 get_layer5_teams 方法
- [ ] 实现 `get_layer5_teams(match_id)` 方法
- [ ] 实现 `_get_team_form` 方法（调用 LastX API）
- [ ] 实现 `_get_team_season_stats` 方法（调用 League Teams API）
- [ ] 实现 `_get_h2h_data` 方法
- [ ] 组装 `MatchTeamsData` 对象
- [ ] 编写单元测试
- **优先级**: High
- **预计时间**: 5 小时
- **依赖**: Task 1.5, Task 2.5

#### Task 2.7: 实现 get_layer6_others 方法
- [ ] 实现 `get_layer6_others(match_id)` 方法
- [ ] 根据需要获取球员数据
- [ ] 根据需要获取裁判数据
- [ ] 根据需要获取联赛统计
- [ ] 编写单元测试
- **优先级**: Low
- **预计时间**: 3 小时
- **依赖**: Task 1.6, Task 2.6

#### Task 2.8: 实现 get_full_prediction_data 方法
- [ ] 实现 `get_full_prediction_data(match_id)` 方法
- [ ] 按顺序调用各 Layer 方法
- [ ] 组装 `FullPredictionData` 对象
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
- [ ] 创建文件 `src/cmd/prediction_cmd.py`
- [ ] 实现 `PredictionCMD` 类
- [ ] 注入 Datasource
- [ ] 实现主循环框架
- [ ] 添加异常处理
- **优先级**: High
- **预计时间**: 2 小时
- **依赖**: Phase 2 完成

#### Task 4.2: 实现比赛列表展示
- [ ] 实现 `_display_matches` 方法
- [ ] 格式化比赛信息输出
- [ ] 添加时间、比分显示
- [ ] 实现 `_prompt_match_selection` 方法
- [ ] 测试用户交互
- **优先级**: High
- **预计时间**: 3 小时
- **依赖**: Task 4.1

#### Task 4.3: 实现渐进式数据加载菜单
- [ ] 实现 `_progressive_load` 方法
- [ ] 创建 Layer 选择菜单
- [ ] 实现各 Layer 的数据获取逻辑
- [ ] 添加返回和退出功能
- [ ] 测试完整流程
- **优先级**: High
- **预计时间**: 4 小时
- **依赖**: Task 4.2

#### Task 4.4: 实现各 Layer 数据展示方法
- [ ] 实现 `_display_basic` 方法
- [ ] 实现 `_display_stats` 方法
- [ ] 实现 `_display_advanced` 方法
- [ ] 实现 `_display_odds` 方法
- [ ] 实现 `_display_teams` 方法
- [ ] 实现 `_display_others` 方法
- [ ] 格式化输出，确保可读性
- **优先级**: High
- **预计时间**: 5 小时
- **依赖**: Task 4.3

#### Task 4.5: 实现全部数据展示
- [ ] 实现 `_display_all` 方法
- [ ] 分层展示所有数据
- [ ] 添加数据完整性提示
- [ ] 优化输出格式
- **优先级**: Medium
- **预计时间**: 3 小时
- **依赖**: Task 4.4

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

## 任务依赖图

```
Phase 1 (基础架构)
├─ Task 1.1 → Task 1.2, 1.3, 1.4, 1.5, 1.6
└─ Task 1.1-1.6 → Task 1.7

Phase 2 (Datasource)
├─ Phase 1 完成 → Task 2.1
├─ Task 2.1 → Task 2.2
├─ Task 2.2 → Task 2.3 → Task 2.4 → Task 2.5 → Task 2.6 → Task 2.7
└─ Task 2.2-2.7 → Task 2.8, Task 2.9

Phase 3 (Provider 验证)
└─ 独立进行

Phase 4 (CMD)
└─ Phase 2 完成 → Task 4.1 → Task 4.2 → Task 4.3 → Task 4.4 → Task 4.5

Phase 5 (测试优化)
└─ Phase 2 完成 → Task 5.1 → Task 5.2 → Task 5.3, Task 5.4

Phase 6 (交付)
└─ Phase 5 完成 → Task 6.1 → Task 6.2 → Task 6.3
```

---

## 优先级总结

### High Priority (必须完成)
- Phase 1: 所有实体类
- Phase 2: Task 2.1-2.6, 2.8-2.9（核心 Layer）
- Phase 4: 所有 CMD 功能
- Phase 5: 测试和错误处理

### Medium Priority (重要但可延后)
- Phase 1: FullPredictionData
- Phase 2: Layer 4 (赔率), Layer 6 (其他)
- Phase 4: 全部数据展示
- Phase 5: 性能优化

### Low Priority (可选)
- Phase 2: Layer 6 详细实现
- Phase 6: 演示和文档

---

## 预估总工时

| Phase | 预计时间 | 关键路径 |
|-------|----------|----------|
| Phase 1 | 17 小时 | 2 天 |
| Phase 2 | 29 小时 | 4 天 |
| Phase 3 | 5 小时 | 0.5 天 |
| Phase 4 | 17 小时 | 2 天 |
| Phase 5 | 17 小时 | 2 天 |
| Phase 6 | 8 小时 | 1 天 |
| **总计** | **93 小时** | **11.5 天** |

**关键路径**: Phase 1 → Phase 2 → Phase 4 → Phase 5

**最快交付**: 如果只实现核心功能（Layer 1-3 + 基础 CMD），预计 **5-6 天**

---

## 风险和挑战

### 高风险
1. **API 返回格式变化**: 需要验证实际 API 返回与文档一致
   - 缓解：Task 3.1 优先进行
   
2. **LastX API 数据解析**: 球队状态计算逻辑复杂
   - 缓解：查看实际 API 返回，简化初期实现

### 中风险
1. **数据一致性问题**: 不同 API 返回的数据可能冲突
   - 缓解：定义数据优先级规则

2. **性能问题**: 多次 API 调用耗时长
   - 缓解：Phase 5 实现并行获取

### 低风险
1. **字段映射错误**: 部分字段名称可能不匹配
   - 缓解：单元测试覆盖

---

## 验收标准

### Phase 1-2 验收
- [ ] 所有实体类创建完成
- [ ] Datasource 方法可正常调用
- [ ] 单元测试覆盖率 > 80%
- [ ] 能从真实 API 获取数据

### Phase 3-4 验收
- [ ] CMD 可运行
- [ ] 可展示近期比赛列表
- [ ] 可选择比赛并分层加载数据
- [ ] 各 Layer 数据正确显示

### Phase 5-6 验收
- [ ] 集成测试通过
- [ ] 错误处理完善
- [ ] 使用文档完整
- [ ] 代码审查通过

---

## 下一步行动

1. **立即开始**: Task 1.1 - 创建 MatchBasicData
2. **并行进行**: Task 3.1 - 验证 Provider API 完整性
3. **完成后通知**: 每个 Task 完成后更新状态

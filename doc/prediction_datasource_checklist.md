# Prediction Datasource 实现检查清单

## Phase 1: 基础架构检查清单

### Task 1.1: MatchBasicData 实体
- [ ] 文件已创建：`src/domain/entities/match_basic.py`
- [ ] 类定义使用 `@dataclass` 装饰器
- [ ] 所有必需字段已定义（match_id, home_team_id, away_team_id 等）
- [ ] 字段类型注解正确
- [ ] 默认值设置合理
- [ ] `__post_init__` 方法初始化 extra 字段
- [ ] `is_finished` 属性正确实现
- [ ] `is_live` 属性正确实现
- [ ] 单元测试通过
- [ ] 代码符合项目规范（lint 检查通过）

### Task 1.2: MatchStatsData 实体
- [ ] 文件已创建：`src/domain/entities/match_stats.py`
- [ ] 所有统计字段已定义（射门、控球、角球等）
- [ ] 默认值 -1 表示无效数据
- [ ] `has_valid_stats` 属性正确实现
- [ ] 字段命名与 API 返回一致
- [ ] 单元测试覆盖所有字段
- [ ] 代码符合项目规范

### Task 1.3: MatchAdvancedData 实体
- [ ] 文件已创建：`src/domain/entities/match_advanced.py`
- [ ] `LineupPlayer` 辅助类已实现
- [ ] 所有高级统计字段已定义（xG、进攻等）
- [ ] 阵容字段使用 List[LineupPlayer]
- [ ] `has_xg` 属性正确实现
- [ ] `has_lineups` 属性正确实现
- [ ] h2h_summary 字段类型为 Optional[Dict]
- [ ] trends 字段类型为 List[str]
- [ ] 单元测试覆盖
- [ ] 已验证 API 实际返回格式

### Task 1.4: MatchOddsData 实体
- [ ] 文件已创建：`src/domain/entities/match_odds.py`
- [ ] 基础赔率字段已定义（主胜、平局、客胜）
- [ ] 隐含概率字段已定义
- [ ] `calculate_implied_probabilities` 方法正确实现
- [ ] 大小球、BTTS 赔率字段已定义
- [ ] odds_comparison 字段支持嵌套字典
- [ ] 单元测试验证概率计算
- [ ] 代码符合项目规范

### Task 1.5: MatchTeamsData 实体
- [ ] 文件已创建：`src/domain/entities/match_teams.py`
- [ ] `TeamForm` 类已实现
- [ ] `TeamSeasonStats` 类已实现
- [ ] `MatchTeamsData` 主类已实现
- [ ] TeamForm 包含近 5 场统计字段
- [ ] TeamForm 包含 current_streak 字段
- [ ] TeamSeasonStats 包含赛季统计字段
- [ ] MatchTeamsData 包含主客队 form 和 stats
- [ ] `form_difference` 属性正确实现
- [ ] `strength_difference` 属性正确实现
- [ ] 单元测试覆盖所有场景
- [ ] 代码符合项目规范

### Task 1.6: MatchOthersData 实体
- [ ] 文件已创建：`src/domain/entities/match_others.py`
- [ ] 所有可选字段已定义
- [ ] 字段类型使用 Optional
- [ ] extra 字段用于未来扩展
- [ ] 单元测试覆盖
- [ ] 代码符合项目规范

### Task 1.7: FullPredictionData 实体
- [ ] 文件已创建：`src/domain/entities/full_prediction_data.py`
- [ ] 组合所有 6 个 Layer 数据
- [ ] 所有 Layer 字段类型为 Optional
- [ ] `is_complete` 属性检查所有 Layer
- [ ] `to_feature_vector` 方法框架已预留（TODO 注释）
- [ ] features 和 prediction 字典已初始化
- [ ] 单元测试验证组合逻辑
- [ ] 代码符合项目规范

---

## Phase 2: Datasource 层检查清单

### Task 2.1: PredictionMatchDataSource 框架
- [ ] 文件已创建：`src/datasource/footystats/prediction_datasource.py`
- [ ] 类定义正确
- [ ] `__init__` 方法注入 Provider
- [ ] Provider 赋值给 self.provider
- [ ] 导入所有需要的实体类
- [ ] 导入 logger
- [ ] 添加基本日志记录
- [ ] 异常处理框架已建立
- [ ] 代码符合项目规范

### Task 2.2: get_layer1_basic 方法
- [ ] 方法签名正确：`async def get_layer1_basic(self, match_id: int)`
- [ ] 返回类型：`Optional[MatchBasicData]`
- [ ] 调用 `provider.get_match_details`
- [ ] 检查 API 返回 success
- [ ] 错误处理：返回 None
- [ ] 调用 `_parse_basic_data` 解析
- [ ] `_parse_basic_data` 实现完整
- [ ] 日期转换正确（UNIX timestamp → datetime）
- [ ] 状态映射正确
- [ ] 日志记录完整
- [ ] 单元测试通过（mock Provider）

### Task 2.3: get_layer2_stats 方法
- [ ] 方法签名正确
- [ ] 返回类型：`Optional[MatchStatsData]`
- [ ] 调用 `provider.get_match_details`
- [ ] 调用 `_parse_stats_data` 解析
- [ ] 处理默认值 -1
- [ ] 验证统计数据完整性
- [ ] `has_valid_stats` 逻辑正确
- [ ] 日志记录完整
- [ ] 单元测试通过

### Task 2.4: get_layer3_advanced 方法
- [ ] 方法签名正确
- [ ] 返回类型：`Optional[MatchAdvancedData]`
- [ ] 调用 `provider.get_match_details`
- [ ] 调用 `_parse_advanced_data` 解析
- [ ] xG 数据解析正确
- [ ] 进攻数据解析正确
- [ ] 阵容数据解析（lineups）
- [ ] LineupPlayer 对象创建正确
- [ ] h2h 数据解析
- [ ] trends 数据解析
- [ ] weather 数据解析
- [ ] 日志记录完整
- [ ] 单元测试通过

### Task 2.5: get_layer4_odds 方法
- [ ] 方法签名正确
- [ ] 返回类型：`Optional[MatchOddsData]`
- [ ] 调用 `provider.get_match_details`
- [ ] 调用 `_parse_odds_data` 解析
- [ ] 调用 `calculate_implied_probabilities`
- [ ] 隐含概率计算正确
- [ ] 赔率对比数据处理
- [ ] 日志记录完整
- [ ] 单元测试验证概率计算

### Task 2.6: get_layer5_teams 方法
- [ ] 方法签名正确
- [ ] 返回类型：`Optional[MatchTeamsData]`
- [ ] 先获取 layer1 拿到球队 ID 和赛季 ID
- [ ] 调用 `_get_team_form` 获取主队状态
- [ ] 调用 `_get_team_form` 获取客队状态
- [ ] 调用 `_get_team_season_stats` 获取主队统计
- [ ] 调用 `_get_team_season_stats` 获取客队统计
- [ ] 调用 `_get_h2h_data` 获取交锋记录
- [ ] 组装 MatchTeamsData 对象
- [ ] 填充 h2h 字段
- [ ] `_get_team_form` 实现（调用 LastX API）
- [ ] `_get_team_season_stats` 实现（调用 League Teams API）
- [ ] `_get_h2h_data` 实现
- [ ] 日志记录完整
- [ ] 单元测试通过

### Task 2.7: get_layer6_others 方法
- [ ] 方法签名正确
- [ ] 返回类型：`Optional[MatchOthersData]`
- [ ] 先获取 layer1 基础信息
- [ ] 创建 MatchOthersData 对象
- [ ] 根据需要获取其他数据
- [ ] 日志记录完整
- [ ] 单元测试通过

### Task 2.8: get_full_prediction_data 方法
- [ ] 方法签名正确
- [ ] 返回类型：`Optional[FullPredictionData]`
- [ ] 创建 FullPredictionData 对象
- [ ] 按顺序调用各 Layer 方法
- [ ] layer1 失败时返回 None
- [ ] 其他 layer 失败时继续
- [ ] 返回完整对象
- [ ] 日志记录完整
- [ ] 集成测试验证完整流程

### Task 2.9: get_recent_matches 方法
- [ ] 方法签名正确：`async def get_recent_matches(self, days: int = 7)`
- [ ] 返回类型：`List[MatchBasicData]`
- [ ] 导入 datetime 和 timedelta
- [ ] 循环获取每天的比赛
- [ ] 日期格式正确（YYYY-MM-DD）
- [ ] 调用 `provider.get_todays_matches`
- [ ] 解析为 MatchBasicData
- [ ] 添加到列表
- [ ] 返回列表
- [ ] 处理分页（如有）
- [ ] 日志记录完整
- [ ] 单元测试通过

---

## Phase 3: Provider 层验证检查清单

### Task 3.1: 验证 Provider API 完整性
- [ ] 检查 `client.py` 文件
- [ ] 确认 16 个端点都已实现
- [ ] 端点列表：
  - [ ] get_league_list
  - [ ] get_country_list
  - [ ] get_todays_matches
  - [ ] get_league_stats
  - [ ] get_league_matches
  - [ ] get_league_teams
  - [ ] get_league_players
  - [ ] get_league_referees
  - [ ] get_league_tables
  - [ ] get_match_details
  - [ ] get_team
  - [ ] get_team_last_x_stats
  - [ ] get_player_stats
  - [ ] get_referee_stats
  - [ ] get_btts_stats
  - [ ] get_over_2_5_stats
- [ ] 验证每个方法的参数
- [ ] 验证每个方法的返回类型
- [ ] 查看 API 文档确认字段
- [ ] 记录字段映射关系
- [ ] 创建 API 映射文档

### Task 3.2: 添加 Provider 数据验证
- [ ] 为关键方法添加验证
- [ ] get_match_details 验证返回字段
- [ ] get_todays_matches 验证数据格式
- [ ] get_league_matches 验证分页
- [ ] 添加字段类型检查
- [ ] 添加缺失字段日志
- [ ] 不抛出异常，返回 None 或默认值
- [ ] 验证测试通过

---

## Phase 4: CMD 层检查清单

### Task 4.1: PredictionCMD 基础框架
- [ ] 文件已创建：`src/cmd/prediction_cmd.py`
- [ ] 导入必要的模块
- [ ] 导入 Datasource 和 Provider
- [ ] 定义 PredictionCMD 类
- [ ] `__init__` 方法创建 Provider 和 Datasource
- [ ] 实现 `run` 异步方法
- [ ] 打印欢迎信息
- [ ] 异常处理框架
- [ ] 代码符合项目规范

### Task 4.2: 比赛列表展示
- [ ] 实现 `_display_matches` 方法
- [ ] 参数：`List[MatchBasicData]`
- [ ] 遍历比赛列表
- [ ] 显示球队名称
- [ ] 显示比赛时间
- [ ] 显示比分
- [ ] 格式化输出（对齐）
- [ ] 实现 `_prompt_match_selection` 方法
- [ ] 使用 `input()` 获取用户选择
- [ ] 验证输入有效性
- [ ] 返回选中的 match_id
- [ ] 测试用户交互流程

### Task 4.3: 渐进式数据加载菜单
- [ ] 实现 `_progressive_load` 方法
- [ ] 参数：match_id
- [ ] while True 循环
- [ ] 打印菜单选项（1-7 + 0）
- [ ] Layer 1-6 选项
- [ ] 选项 7: 加载全部
- [ ] 选项 0: 返回
- [ ] 获取用户输入
- [ ] if-elif 分支处理
- [ ] 调用对应 datasource 方法
- [ ] 调用对应 display 方法
- [ ] break 退出循环
- [ ] 测试完整流程

### Task 4.4: 各 Layer 数据展示方法
- [ ] 实现 `_display_basic` 方法
  - [ ] 显示比赛信息
  - [ ] 显示比分
  - [ ] 显示时间
- [ ] 实现 `_display_stats` 方法
  - [ ] 显示控球率
  - [ ] 显示射门数据
  - [ ] 显示角球数据
  - [ ] 显示纪律数据
- [ ] 实现 `_display_advanced` 方法
  - [ ] 显示 xG 数据
  - [ ] 显示进攻数据
  - [ ] 显示阵容（如有）
- [ ] 实现 `_display_odds` 方法
  - [ ] 显示胜平负赔率
  - [ ] 显示隐含概率
  - [ ] 显示大小球赔率
- [ ] 实现 `_display_teams` 方法
  - [ ] 显示主队状态
  - [ ] 显示客队状态
  - [ ] 显示交锋记录
- [ ] 实现 `_display_others` 方法
  - [ ] 显示其他数据
- [ ] 所有方法格式化输出
- [ ] 所有方法处理 None 值
- [ ] 测试所有展示方法

### Task 4.5: 全部数据展示
- [ ] 实现 `_display_all` 方法
- [ ] 参数：FullPredictionData
- [ ] 检查数据完整性
- [ ] 分层调用 display 方法
- [ ] 添加分隔符
- [ ] 显示加载状态
- [ ] 优化输出格式
- [ ] 测试完整展示

---

## Phase 5: 测试和优化检查清单

### Task 5.1: 单元测试
- [ ] 所有实体类有测试
- [ ] 所有 datasource 方法有测试
- [ ] Mock Provider 响应
- [ ] 测试正常流程
- [ ] 测试错误流程
- [ ] 测试边界情况
- [ ] 测试 None 返回值
- [ ] 测试异常处理
- [ ] 代码覆盖率 > 80%
- [ ] 所有测试通过

### Task 5.2: 集成测试
- [ ] 测试完整数据获取流程
- [ ] 测试 get_recent_matches
- [ ] 测试 get_full_prediction_data
- [ ] 测试错误处理
- [ ] 测试 API 超时
- [ ] 测试数据一致性
- [ ] 所有集成测试通过

### Task 5.3: 性能优化
- [ ] 分析各方法耗时
- [ ] 识别慢查询
- [ ] 实现并行获取（如适用）
- [ ] 添加缓存机制
- [ ] 优化解析逻辑
- [ ] 减少重复调用
- [ ] 性能提升 > 20%

### Task 5.4: 错误处理增强
- [ ] 添加重试机制（decorator）
- [ ] 完善错误日志
- [ ] 区分错误类型
- [ ] 处理 API 限流
- [ ] 添加降级策略
- [ ] 用户友好错误提示
- [ ] 所有异常场景覆盖

---

## Phase 6: 文档和交付检查清单

### Task 6.1: 使用文档
- [ ] 编写 Datasource 使用示例
- [ ] 编写 CMD 操作指南
- [ ] 绘制 API 调用流程图
- [ ] 更新项目 README
- [ ] 添加快速开始指南
- [ ] 文档语言清晰
- [ ] 示例代码可运行

### Task 6.2: 代码审查
- [ ] 自查代码规范
- [ ] 运行 linter
- [ ] 修复所有 warning
- [ ] 添加缺失的 docstring
- [ ] 检查类型注解
- [ ] 日志格式规范
- [ ] 无硬编码字符串
- [ ] 无调试代码
- [ ] 审查通过

### Task 6.3: 交付演示
- [ ] 准备演示脚本
- [ ] 准备测试数据
- [ ] 录制演示视频
- [ ] 收集反馈
- [ ] 记录改进建议
- [ ] 迭代改进
- [ ] 最终验收通过

---

## 最终验收标准

### 功能完整性
- [ ] 所有 Layer 数据可正常获取
- [ ] CMD 可正常运行
- [ ] 渐进式加载工作正常
- [ ] 数据展示正确
- [ ] 错误处理完善

### 代码质量
- [ ] 单元测试覆盖率 > 80%
- [ ] 集成测试通过
- [ ] 代码符合项目规范
- [ ] 类型注解完整
- [ ] 文档齐全

### 性能要求
- [ ] Layer 1-3 加载时间 < 3 秒
- [ ] 完整数据加载 < 10 秒
- [ ] 无内存泄漏
- [ ] 并发处理合理

### 用户体验
- [ ] CMD 交互流畅
- [ ] 输出格式美观
- [ ] 错误提示友好
- [ ] 帮助信息清晰

---

## 签署验收

- [ ] 开发者自验通过
- [ ] 代码审查通过
- [ ] 测试团队验收通过
- [ ] 产品经理验收通过
- [ ] 可以上线发布

**验收日期**: _______________

**验收人员**: _______________

**备注**: _______________

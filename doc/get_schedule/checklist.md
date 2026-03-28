# get_schedule 验证清单

## 使用说明

本文档用于验证 `get_schedule` 功能的完整性和质量。在每个开发阶段完成后，勾选相应的复选框。

**图例**:
- [ ] 待验证
- [x] 已验证通过
- [-] 不适用/已跳过

## 架构层次说明

**重要**：命令行只调用 DataSource 层，不直接调用 Provider 层。

```
┌─────────────────────────────────────┐
│  Command Layer (cmd/get_schedule.py) │  ← 本功能的实现位置
│  - 参数解析                          │     只调用 DataSource
│  - 输出格式化                        │
├─────────────────────────────────────┤
│  DataSource Layer                    │  ← 业务逻辑层
│  (src/datasource/match/)             │     数据解析、缓存、聚合
│  - MatchDataSource                   │     已有方法：fetch_*
├─────────────────────────────────────┤
│  Provider Layer                      │  ← API 适配层
│  (src/provider/footystats/)          │     直接调用 FootyStats API
│  - FootyStatsProvider                │
└─────────────────────────────────────┘
```

**验证重点**:
1. 命令行是否正确调用 DataSource 方法
2. DataSource 是否正确调用 Provider 方法
3. 各层职责是否清晰分离

---

## 阶段 1：基础设施验证

### 1.1 FootyStatsProvider 扩展

- [ ] `get_league_country_mapping()` 方法已实现
- [ ] 方法正确调用 `/league-list` API
- [ ] 返回的映射格式正确 `{league_name: country}`
- [ ] 处理 API 错误（返回空字典或 None）
- [ ] 添加日志记录
- [ ] 单元测试通过

**测试用例**:
```python
# 测试 1: 正常情况
mapping = await provider.get_league_country_mapping()
assert "Premier League" in mapping
assert mapping["Premier League"] == "England"

# 测试 2: API 错误处理
# 模拟 API 错误，验证返回 None 或空字典
```

---

### 1.2 Match 数据类型确认

- [ ] Match 类包含 match_id 字段
- [ ] Match 类包含 home_team, away_team 字段
- [ ] Match 类包含 home_team_id, away_team_id 字段
- [ ] Match 类包含 competition 字段
- [ ] Match 类包含 kickoff_time 字段
- [ ] Match 类包含 status 字段
- [ ] 所有字段类型正确
- [ ] 添加了字段说明注释

**验证代码**:
```python
from datasource.types import Match
import inspect

# 检查字段是否存在
sig = inspect.signature(Match)
required_fields = ['match_id', 'home_team', 'away_team', 'home_team_id', 
                   'away_team_id', 'competition', 'kickoff_time', 'status']
for field in required_fields:
    assert field in sig.parameters, f"Missing field: {field}"
```

---

### 1.3 联赛 - 国家缓存工具类

- [ ] `LeagueCountryCache` 类已创建
- [ ] 单例模式实现正确
- [ ] `get_country(league_name)` 方法工作正常
- [ ] 缓存 TTL 机制有效（24 小时）
- [ ] 缓存过期后自动刷新
- [ ] 支持并发访问（无竞态条件）
- [ ] `refresh()` 方法强制刷新缓存
- [ ] 单元测试通过

**测试用例**:
```python
# 测试 1: 缓存命中
cache = LeagueCountryCache()
country1 = await cache.get_country("Premier League")
country2 = await cache.get_country("Premier League")
assert country1 == country2  # 第二次应该命中缓存

# 测试 2: 缓存过期
# 设置短 TTL（如 1 秒），验证过期后重新加载

# 测试 3: 并发访问
# 并发调用 get_country，验证无竞态条件
```

---

## 阶段 2：核心功能验证

### 2.1 命令行参数解析

- [ ] `--nearest` 参数工作正常
- [ ] `--next-days N` 参数工作正常
- [ ] `--date-range FROM TO` 参数工作正常
- [ ] `--team "球队名称"` 参数工作正常
- [ ] `--json` 参数工作正常
- [ ] `--compact` 参数工作正常
- [ ] `--debug` 参数工作正常
- [ ] `--no-cache` 参数工作正常
- [ ] 互斥组关系正确（查询模式互斥）
- [ ] `--help` 显示完整帮助信息
- [ ] 错误参数给出友好提示

**测试命令**:
```bash
# 测试帮助信息
python -m cmd.get_schedule --help

# 测试参数互斥（应该报错）
python -m cmd.get_schedule --nearest --next-days 7

# 测试有效参数组合
python -m cmd.get_schedule --next-days 7 --team "Manchester United" --compact
```

---

### 2.2 时间范围查询功能

#### 模式 1.1: 最近比赛日
- [ ] 正确找到第一个有比赛的日期
- [ ] 返回该日期的所有比赛
- [ ] 处理无比赛情况（返回空或提示）
- [ ] 球队过滤工作正常
- [ ] 查询未来 30 天内无比赛时给出友好提示

**测试命令**:
```bash
python -m cmd.get_schedule --nearest
python -m cmd.get_schedule --nearest --team "Liverpool"
```

#### 模式 1.2: 未来 N 天
- [ ] 正确获取未来 N 天的比赛
- [ ] N 值有效范围检查（1-365）
- [ ] 多天数据正确合并
- [ ] 球队过滤工作正常
- [ ] 按日期排序正确

**测试命令**:
```bash
python -m cmd.get_schedule --next-days 1
python -m cmd.get_schedule --next-days 7 --team "Arsenal"
python -m cmd.get_schedule --next-days 30
```

#### 模式 1.3: 日期范围
- [ ] 正确解析日期字符串
- [ ] 日期格式验证（YYYY-MM-DD）
- [ ] 起始日期 <= 结束日期检查
- [ ] 范围内所有比赛正确获取
- [ ] 球队过滤工作正常
- [ ] 跨月/跨年范围查询正确

**测试命令**:
```bash
# 有效日期范围
python -m cmd.get_schedule --date-range 2026-03-28 2026-04-05

# 无效日期格式（应该报错）
python -m cmd.get_schedule --date-range 2026/03/28 2026-04-05

# 起始日期 > 结束日期（应该报错）
python -m cmd.get_schedule --date-range 2026-04-05 2026-03-28
```

---

### 2.3 球队查询功能

- [ ] 精确匹配球队名称工作正常
- [ ] 模糊匹配工作正常（部分匹配）
- [ ] 大小写不敏感
- [ ] 匹配多支球队时返回所有结果
- [ ] 球队不存在时给出友好提示
- [ ] 可能拼写错误时给出建议

**测试命令**:
```bash
# 精确匹配
python -m cmd.get_schedule --team "Manchester United" --next-days 7

# 模糊匹配
python -m cmd.get_schedule --team "Man United" --next-days 7
python -m cmd.get_schedule --team "manchester" --next-days 7

# 不存在的球队（应该给出友好提示）
python -m cmd.get_schedule --team "NonExistentTeam" --nearest
```

---

### 2.4 输出格式化

#### 表格格式
- [ ] 表格边框正确绘制
- [ ] 所有 9 个字段都显示
- [ ] 列对齐正确
- [ ] 长文本处理（换行或截断）
- [ ] 中文显示正常
- [ ] 多场比赛分页或滚动显示

**验证截图**:
```
┌──────────────┬──────────┬─────────────────┬──────────────┬─────────────────────┬─────────┬─────────────────────┬─────────┬───────────┐
│ 比赛时间     │ 比赛 ID  │ 开赛联赛        │ 比赛国家     │ 主队名称            │ 主队 ID │ 客队名称            │ 客队 ID │ 比赛状态  │
├──────────────┼──────────┼─────────────────┼──────────────┼─────────────────────┼─────────┼─────────────────────┼─────────┼───────────┤
│ 2026-03-28   │ 579101   │ Premier League  │ England      │ Manchester City     │ 1       │ Liverpool           │ 14      │ SCHEDULED │
│ 15:00        │          │                 │              │                     │         │                     │         │           │
└──────────────┴──────────┴─────────────────┴──────────────┴─────────────────────┴─────────┴─────────────────────┴─────────┴───────────┘
```

#### JSON 格式
- [ ] JSON 格式有效（可解析）
- [ ] 包含所有 9 个字段
- [ ] 字段名称正确
- [ ] 数据类型正确（字符串、整数、null）
- [ ] 中文显示正常（ensure_ascii=False）
- [ ] 缩进格式美观（indent=2）

**验证代码**:
```python
import json
output = subprocess.check_output(["python", "-m", "cmd.get_schedule", "--next-days", "7", "--json"])
data = json.loads(output)
assert isinstance(data, list)
for match in data:
    assert "kickoff_time" in match
    assert "match_id" in match
    assert "league" in match
    # ... 检查所有字段
```

#### 简洁格式
- [ ] 每行显示一场比赛
- [ ] 格式统一：`时间 [联赛 - 国家] 主队 vs 客队 (状态)`
- [ ] 信息完整且简洁
- [ ] 易于阅读

**验证输出**:
```
2026-03-28 15:00 [Premier League - England] Manchester City vs Liverpool (SCHEDULED)
2026-03-28 17:30 [La Liga - Spain] Real Madrid vs Barcelona (SCHEDULED)
2026-03-29 20:00 [Serie A - Italy] Juventus vs AC Milan (FINISHED)
```

---

### 2.5 错误处理

- [ ] API Key 未配置：错误码 1001
- [ ] API 不可用：错误码 1002
- [ ] 日期格式错误：错误码 2001
- [ ] 球队未找到：错误码 3001
- [ ] 无比赛数据：错误码 4001
- [ ] 参数冲突：错误码 5001
- [ ] 所有错误都有友好提示
- [ ] 错误消息包含建议
- [ ] 使用 emoji 增强可读性

**测试命令**:
```bash
# 测试各种错误情况
# （根据实际实现验证错误消息）
```

---

## 阶段 3：辅助功能验证

### 3.1 调试模式

- [ ] `--debug` 参数启用调试输出
- [ ] 显示 API 请求参数
- [ ] 显示 API 原始响应
- [ ] 显示解析后的数据
- [ ] 显示缓存命中情况
- [ ] 调试信息使用 `[DEBUG]` 前缀
- [ ] 调试信息格式清晰
- [ ] 不影响正常输出

**测试命令**:
```bash
python -m cmd.get_schedule --nearest --debug
```

---

### 3.2 缓存控制

- [ ] `--no-cache` 参数工作正常
- [ ] 使用缓存时显示提示
- [ ] 刷新缓存时显示提示
- [ ] 缓存清理后重新从 API 加载
- [ ] 缓存机制提高性能（对比有/无缓存的时间）

**测试命令**:
```bash
# 第一次（无缓存）
time python -m cmd.get_schedule --next-days 7

# 第二次（有缓存）
time python -m cmd.get_schedule --next-days 7

# 强制刷新缓存
time python -m cmd.get_schedule --next-days 7 --no-cache
```

---

### 3.3 汇总统计

- [ ] 显示总比赛数量
- [ ] 显示有比赛的天数
- [ ] 显示涉及联赛数量
- [ ] 显示联赛列表（前 10 个）
- [ ] 汇总格式美观
- [ ] 在每种查询模式下都显示
- [ ] 统计数据准确

**验证输出**:
```
════════════════════════════════════════
汇总统计
════════════════════════════════════════
总比赛数：25
有比赛的天数：5
涉及联赛数：8
联赛列表：Premier League, La Liga, Serie A, ...
```

---

## 阶段 4：测试和文档验证

### 4.1 单元测试

- [ ] 测试文件已创建
- [ ] 参数解析测试通过
- [ ] 日期验证测试通过
- [ ] 球队过滤测试通过
- [ ] 输出格式化测试通过
- [ ] 错误处理测试通过
- [ ] 测试覆盖率 > 80%
- [ ] 所有测试用例通过

**运行测试**:
```bash
# 运行单元测试
python -m pytest tests/test_get_schedule.py -v

# 查看覆盖率
python -m pytest tests/test_get_schedule.py --cov=cmd.get_schedule --cov-report=html
```

---

### 4.2 集成测试

- [ ] 所有查询模式测试通过
- [ ] 所有输出格式测试通过
- [ ] 错误情况测试通过
- [ ] 性能测试通过（< 3 秒）
- [ ] 真实 API 测试通过
- [ ] 边界条件测试通过

**测试矩阵**:

| 查询模式 | 无球队 | 有球队 | JSON 输出 | 简洁输出 |
|----------|--------|--------|-----------|----------|
| --nearest | [ ] | [ ] | [ ] | [ ] |
| --next-days 7 | [ ] | [ ] | [ ] | [ ] |
| --date-range | [ ] | [ ] | [ ] | [ ] |

---

### 4.3 用户文档

- [ ] README 文件已创建
- [ ] 功能介绍清晰
- [ ] 安装配置说明完整
- [ ] 所有使用示例都提供
- [ ] 参数说明详细
- [ ] 常见问题解答
- [ ] 错误代码说明
- [ ] 中文书写
- [ ] 格式美观

**文档检查清单**:
- [ ] 目录结构清晰
- [ ] 代码示例可运行
- [ ] 截图清晰（如有）
- [ ] 链接有效
- [ ] 拼写和语法正确

---

### 4.4 代码质量

- [ ] 代码风格一致
- [ ] 命名规范（变量、函数、类）
- [ ] 注释完整
- [ ] docstring 完整
- [ ] 类型注解完整
- [ ] 通过 flake8 检查
- [ ] 通过 pylint 检查（> 8.0 分）
- [ ] 无重复代码
- [ ] 错误处理完善
- [ ] 日志记录适当

**运行检查**:
```bash
# 代码风格检查
python -m flake8 cmd/get_schedule.py --max-line-length=120

# 代码质量检查
python -m pylint cmd/get_schedule.py --disable=C0114,C0115,C0116

# 类型检查（如使用 mypy）
python -m mypy cmd/get_schedule.py
```

---

## 最终验收

### 功能完整性

- [ ] 所有 6 种查询模式都实现
- [ ] 所有 9 个显示字段都正确
- [ ] 所有 3 种输出格式都可用
- [ ] 错误处理完善
- [ ] 辅助功能完整

### 性能指标

- [ ] 单次查询响应时间 < 3 秒
- [ ] 缓存命中率 > 80%
- [ ] 内存使用合理
- [ ] 无内存泄漏
- [ ] 并发访问安全

### 用户体验

- [ ] 命令行界面友好
- [ ] 错误消息有帮助
- [ ] 输出格式美观
- [ ] 文档完整易懂
- [ ] 示例丰富实用

### 代码质量

- [ ] 代码结构清晰
- [ ] 易于维护和扩展
- [ ] 测试覆盖率高
- [ ] 符合项目规范
- [ ] 无安全漏洞

---

## 签署确认

**开发者**: _________________  **日期**: _______________

**审查者**: _________________  **日期**: _______________

**最终批准**: _________________  **日期**: _______________

---

## 备注

在此记录任何特殊情况、已知问题或未来改进建议：

1. 
2. 
3. 

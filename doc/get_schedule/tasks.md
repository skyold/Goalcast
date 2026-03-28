# get_schedule 开发任务分解

## 任务概览

本文档将 `get_schedule` 功能开发分解为具体可执行的任务，每个任务都有明确的验收标准。

---

## 阶段 1：DataSource 层扩展

**架构说明**：命令行只调用 DataSource 层，不直接调用 Provider 层。

```
Command Layer (cmd/get_schedule.py)
    ↓ calls
DataSource Layer (src/datasource/match/match_datasource.py)
    ↓ uses
Provider Layer (src/provider/footystats/client.py)
```

### 任务 1.1：确认 Match 数据类型

**文件**: `/Users/zhengningdai/workspace/skyold/Goalcast/src/datasource/types.py`

**任务描述**:
确认 Match 类包含所有需要的字段

**具体工作**:
1. 检查现有字段：
   - ✅ match_id, home_team, away_team
   - ✅ home_team_id, away_team_id
   - ✅ competition
   - ✅ status, kickoff_time
   
2. 确认所有必需字段都已存在，无需添加

**验收标准**:
- [ ] 确认数据类型完整
- [ ] 添加字段说明注释

**预计工时**: 0.5 小时

---

### 任务 1.2：创建 LeagueDataSource

**文件**: `/Users/zhengningdai/workspace/skyold/Goalcast/src/datasource/league/league_datasource.py`（新建目录和文件）

**任务描述**:
创建联赛数据源，管理联赛和国家数据

**具体工作**:
1. 创建 `LeagueDataSource` 类，继承自 `DataSource`
2. 实现方法：
   - `async def get_country(league_name: str) -> str`: 获取联赛国家
   - `async def get_league_list()`: 获取联赛列表（调用 Provider）
   - `_load_league_list()`: 从 API 加载并缓存联赛 - 国家映射
3. 内部缓存：`_league_country_cache: Dict[str, str]`
4. 缓存 TTL：24 小时（可选，使用 DataSource 基类的缓存机制）

**数据结构**（在 `types.py` 中添加）:
```python
@dataclass
class League:
    """联赛实体"""
    league_id: str
    name: str
    country: str
    season: Optional[str] = None
    season_id: Optional[int] = None
```

**验收标准**:
- [ ] DataSource 类工作正常
- [ ] 正确调用 Provider 的 `get_league_list()`
- [ ] 缓存机制有效
- [ ] 支持并发访问
- [ ] 添加单元测试

**预计工时**: 2 小时

---

### 任务 1.3：扩展 MatchDataSource

**文件**: `/Users/zhengningdai/workspace/skyold/Goalcast/src/datasource/match/match_datasource.py`

**任务描述**:
在 MatchDataSource 中添加球队过滤和带国家信息的查询方法

**具体工作**:
1. 添加 `fetch_team_matches()` 方法：
   - 调用 `fetch_in_date_range()` 获取日期范围内所有比赛
   - 过滤包含指定球队的比赛（主队或客队）
   - 支持模糊匹配（不区分大小写）
   - 返回过滤后的比赛列表

2. 添加 `_matches_team()` 辅助方法：
   - 判断比赛是否包含指定球队
   - 支持模糊匹配

3. 添加 `fetch_for_date_with_country()` 方法（可选）：
   - 获取指定日期比赛
   - 为每场比赛添加国家信息

**验收标准**:
- [ ] 球队过滤逻辑正确
- [ ] 模糊匹配有效
- [ ] 返回格式正确
- [ ] 添加单元测试

**预计工时**: 2 小时

---

## 阶段 2：核心功能开发

### 任务 2.1：创建 get_schedule.py 主文件

**文件**: `/Users/zhengningdai/workspace/skyold/Goalcast/cmd/get_schedule.py`

**任务描述**:
创建命令行工具的主文件，只调用 DataSource 层

**具体工作**:
1. 创建文件并添加模块级 docstring
2. 导入必要的模块：
   - asyncio, argparse, sys, json
   - datetime, date, timedelta
   - **MatchDataSource** (from datasource.match)
   - **LeagueCountryCache** (from utils)
   - Match, MatchStatus

3. 实现参数解析器 `create_parser()`:
   - 查询模式互斥组（--nearest, --next-days, --date-range）
   - 球队过滤（--team）
   - 输出格式（--json, --compact）
   - 其他选项（--debug, --no-cache）

4. 实现主函数 `main()`:
   - 解析参数
   - 初始化 DataSource（会自动初始化 Provider）
   - 根据参数调用 DataSource 的方法
   - 格式化输出结果

**架构说明**:
```python
# ❌ 错误：直接调用 Provider
provider = FootyStatsProvider()
matches = await provider.get_todays_matches(date="2026-03-28")

# ✅ 正确：调用 DataSource
match_ds = MatchDataSource()
matches = await match_ds.fetch_for_date(target_date=date(2026, 3, 28))
```

**验收标准**:
- [ ] 参数解析正确
- [ ] 参数互斥关系正确
- [ ] 只调用 DataSource 层
- [ ] 帮助信息完整
- [ ] 主流程逻辑清晰

**预计工时**: 2 小时

---

### 任务 2.2：实现时间范围查询功能

**文件**: `/Users/zhengningdai/workspace/skyold/Goalcast/cmd/get_schedule.py`

**任务描述**:
实现三种时间范围查询模式（通过 DataSource）

**具体工作**:
1. `async def query_nearest(match_ds, team=None, league_cache=None, debug=False)`:
   - 调用 `match_ds.fetch_nearest_match_day()`
   - 如果指定球队：使用 `match_ds.fetch_team_matches()` 过滤
   - 使用 `league_cache.get_country()` 获取国家信息
   - 返回查询结果

2. `async def query_next_days(match_ds, days, team=None, league_cache=None, debug=False)`:
   - 调用 `match_ds.fetch_next_n_days(days)`
   - 如果指定球队：使用 `match_ds.fetch_team_matches()` 过滤
   - 使用 `league_cache.get_country()` 获取国家信息
   - 合并所有结果

3. `async def query_date_range(match_ds, start_date, end_date, team=None, league_cache=None, debug=False)`:
   - 调用 `match_ds.fetch_in_date_range(start_date, end_date)`
   - 如果指定球队：使用 `match_ds.fetch_team_matches()` 过滤
   - 使用 `league_cache.get_country()` 获取国家信息
   - 合并所有结果

**注意**: 球队过滤逻辑已在 `MatchDataSource.fetch_team_matches()` 中实现，命令行层只需调用该方法。

**验收标准**:
- [ ] 三种模式都正常工作
- [ ] 正确调用 DataSource 方法
- [ ] 球队过滤有效
- [ ] 国家信息显示正确
- [ ] 错误处理完善

**预计工时**: 2.5 小时

---

### 任务 2.3：实现输出格式化功能

**文件**: `/Users/zhengningdai/workspace/skyold/Goalcast/cmd/get_schedule.py`

**任务描述**:
实现三种输出格式：表格、JSON、简洁

**具体工作**:
1. `def format_table(matches: List[Match], league_cache: LeagueCountryCache) -> str`:
   - 使用 prettytable 或手动构建表格
   - 包含所有 9 个字段：比赛时间、比赛 ID、开赛联赛、比赛国家、主队名称、主队 ID、客队名称、客队 ID、比赛状态
   - 处理长文本换行
   - 添加边框和分隔线

2. `def format_json(matches: List[Match], league_cache: LeagueCountryCache) -> str`:
   - 构建字典列表
   - 包含所有字段
   - 使用 json.dumps 格式化（indent=2, ensure_ascii=False）

3. `def format_compact(matches: List[Match], league_cache: LeagueCountryCache) -> str`:
   - 每行显示一场比赛
   - 格式：`时间 [联赛 - 国家] 主队 vs 客队 (状态)`
   - 示例：`2026-03-28 15:00 [Premier League - England] Man City vs Liverpool (SCHEDULED)`

4. 辅助函数 `get_country_for_match(match: Match, league_cache: LeagueCountryCache) -> str`:
   - 从缓存获取联赛国家

**数据结构**:
```python
# 命令行层需要构建包含国家信息的完整数据结构
match_with_country = {
    "match": match,  # Match 对象
    "country": await league_cache.get_country(match.competition)
}
```

**验收标准**:
- [ ] 表格格式美观对齐
- [ ] JSON 格式正确且包含所有字段
- [ ] 简洁格式清晰易读
- [ ] 中文显示正常
- [ ] 国家信息正确显示

**预计工时**: 2 小时

---

### 任务 2.4：实现错误处理和提示

**文件**: `/Users/zhengningdai/workspace/skyold/Goalcast/cmd/get_schedule.py`

**任务描述**:
实现完善的错误处理和用户提示

**具体工作**:
1. 创建错误码常量：
   ```python
   class ErrorCode:
       API_KEY_MISSING = 1001
       API_UNAVAILABLE = 1002
       DATE_FORMAT_INVALID = 2001
       TEAM_NOT_FOUND = 3001
       NO_MATCHES = 4001
       PARAM_CONFLICT = 5001
   ```

2. 创建错误类 `ScheduleError(Exception)`:
   - 包含 error_code 和 message
   - 包含 suggestion（可选建议）

3. 实现验证函数：
   - `validate_date_format(date_str: str) -> date`: 验证并解析日期字符串
   - `validate_team_name(team_name: str) -> str`: 验证球队名称

4. 实现错误显示函数 `show_error(error: ScheduleError)`:
   - 使用 emoji 和颜色（如果终端支持）
   - 显示错误类型、消息和建议

**验收标准**:
- [ ] 所有错误类型都有对应处理
- [ ] 错误消息友好且有帮助
- [ ] 建议具体且可操作
- [ ] 不影响正常流程

**预计工时**: 1.5 小时

---

## 阶段 3：辅助功能开发

### 任务 3.1：添加调试模式

**文件**: `/Users/zhengningdai/workspace/skyold/Goalcast/cmd/get_schedule.py`

**任务描述**:
实现调试模式，显示 API 原始数据

**具体工作**:
1. 在查询函数中添加 debug 参数
2. 当 debug=True 时：
   - 打印 API 请求参数
   - 打印 API 原始响应
   - 打印解析后的数据结构
   - 打印缓存命中情况

3. 使用 `[DEBUG]` 前缀标识调试信息
4. 使用 json.dumps 格式化输出

**验收标准**:
- [ ] 调试信息完整
- [ ] 输出格式清晰
- [ ] 不影响正常输出
- [ ] 只在 debug=True 时显示

**预计工时**: 1 小时

---

### 任务 3.2：添加缓存控制

**文件**: `/Users/zhengningdai/workspace/skyold/Goalcast/cmd/get_schedule.py`

**任务描述**:
实现缓存控制功能

**具体工作**:
1. 实现 `--no-cache` 参数处理
2. 当使用 --no-cache 时：
   - 清除 MatchDataSource 缓存
   - 清除 LeagueCountryCache 缓存
   - 强制从 API 重新加载数据

3. 显示缓存状态提示：
   - 使用缓存时显示 "ℹ️ 使用缓存数据"
   - 刷新缓存时显示 "🔄 刷新缓存..."

**验收标准**:
- [ ] --no-cache 参数有效
- [ ] 缓存刷新正常
- [ ] 状态提示清晰

**预计工时**: 0.5 小时

---

### 任务 3.3：添加汇总统计

**文件**: `/Users/zhengningdai/workspace/skyold/Goalcast/cmd/get_schedule.py`

**任务描述**:
在输出末尾添加汇总统计信息

**具体工作**:
1. 创建汇总函数 `print_summary(matches: List[Match], days: int)`:
   - 总比赛数量
   - 有比赛的天数
   - 涉及联赛数量
   - 联赛列表（前 10 个）

2. 在每种查询模式的输出末尾调用汇总函数

3. 汇总格式：
   ```
   ════════════════════════════════════════
   汇总统计
   ════════════════════════════════════════
   总比赛数：25
   有比赛的天数：5
   涉及联赛数：8
   联赛列表：Premier League, La Liga, Serie A, ...
   ```

**验收标准**:
- [ ] 统计信息准确
- [ ] 格式美观
- [ ] 在每种模式下都显示

**预计工时**: 1 小时

---

## 阶段 4：测试和文档

### 任务 4.1：编写单元测试

**文件**: `/Users/zhengningdai/workspace/skyold/Goalcast/tests/test_get_schedule.py`（新建）

**任务描述**:
为 get_schedule 功能编写单元测试

**具体工作**:
1. 测试参数解析：
   - 测试各种参数组合
   - 测试互斥关系
   - 测试错误参数

2. 测试日期验证：
   - 测试有效日期格式
   - 测试无效日期格式

3. 测试球队过滤：
   - 测试精确匹配
   - 测试模糊匹配
   - 测试大小写不敏感

4. 测试输出格式化：
   - 测试表格格式
   - 测试 JSON 格式
   - 测试简洁格式

5. 测试错误处理：
   - 测试各种错误情况
   - 测试错误消息内容

**验收标准**:
- [ ] 测试覆盖率 > 80%
- [ ] 所有测试通过
- [ ] 测试用例完整

**预计工时**: 3 小时

---

### 任务 4.2：集成测试

**文件**: 手动测试

**任务描述**:
使用真实 API 进行集成测试

**具体工作**:
1. 测试所有查询模式：
   ```bash
   # 模式 1.1：最近比赛日
   python -m cmd.get_schedule --nearest
   
   # 模式 1.2：未来 N 天
   python -m cmd.get_schedule --next-days 7
   
   # 模式 1.3：日期范围
   python -m cmd.get_schedule --date-range 2026-03-28 2026-04-05
   
   # 模式 2.1：球队最近比赛
   python -m cmd.get_schedule --team "Manchester United" --nearest
   
   # 模式 2.2：球队未来比赛
   python -m cmd.get_schedule --team "Liverpool" --next-days 14
   
   # 模式 2.3：球队日期范围
   python -m cmd.get_schedule --team "Arsenal" --date-range 2026-03-28 2026-04-30
   ```

2. 测试所有输出格式：
   ```bash
   # JSON 格式
   python -m cmd.get_schedule --next-days 7 --json
   
   # 简洁格式
   python -m cmd.get_schedule --next-days 7 --compact
   ```

3. 测试错误情况：
   ```bash
   # 无效日期
   python -m cmd.get_schedule --date-range 2026/03/28 2026-04-05
   
   # 球队不存在
   python -m cmd.get_schedule --team "NonExistentTeam" --nearest
   
   # 参数冲突
   python -m cmd.get_schedule --nearest --next-days 7
   ```

**验收标准**:
- [ ] 所有命令正常执行
- [ ] 输出格式正确
- [ ] 错误处理友好
- [ ] 性能可接受（< 3 秒）

**预计工时**: 2 小时

---

### 任务 4.3：编写用户文档

**文件**: `/Users/zhengningdai/workspace/skyold/Goalcast/doc/get_schedule/README.md`（新建）

**任务描述**:
编写用户使用文档

**具体工作**:
1. 创建 README 文件
2. 包含以下章节：
   - 功能简介
   - 安装和配置
   - 使用方法（包含所有示例）
   - 参数说明
   - 输出格式说明
   - 常见问题
   - 错误代码说明

3. 添加使用示例截图（可选）

**验收标准**:
- [ ] 文档结构清晰
- [ ] 示例完整
- [ ] 语言简洁
- [ ] 中文书写

**预计工时**: 2 小时

---

### 任务 4.4：代码审查和优化

**文件**: 所有相关文件

**任务描述**:
进行代码审查和优化

**具体工作**:
1. 代码审查清单：
   - 代码风格一致性
   - 命名规范
   - 注释完整性
   - 错误处理
   - 性能优化

2. 运行 lint 工具：
   ```bash
   # 使用项目配置的 lint 工具
   python -m flake8 cmd/get_schedule.py
   python -m pylint cmd/get_schedule.py
   ```

3. 优化建议：
   - 简化复杂逻辑
   - 提取重复代码
   - 改进错误消息
   - 添加类型注解

**验收标准**:
- [ ] 通过 lint 检查
- [ ] 代码质量高
- [ ] 无警告信息

**预计工时**: 1.5 小时

---

## 任务总结

### 工作量估算

| 阶段 | 任务数 | 总工时 |
|------|--------|--------|
| 阶段 1：DataSource 层扩展 | 3 | 4 小时 |
| 阶段 2：核心功能开发 | 4 | 8 小时 |
| 阶段 3：辅助功能开发 | 3 | 2.5 小时 |
| 阶段 4：测试和文档 | 4 | 8.5 小时 |
| **总计** | **14** | **23 小时** |

### 任务依赖关系

```
任务 1.1 (数据类型确认) ──┬──> 任务 2.1 ──> 任务 2.2 ──┬──> 任务 2.3 ──> 任务 2.4
任务 1.2 (缓存工具) ──────┤                           │
任务 1.3 (DataSource 扩展) ─┘                           │
                                       ↓
任务 2.1 ─────────────────────────> 任务 3.1
                                       │
                                       ↓
                                    任务 3.2 ──> 任务 3.3
                                                   │
                                                   ↓
                                                任务 4.1 ──> 任务 4.2 ──> 任务 4.3 ──> 任务 4.4
```

### 推荐执行顺序

1. **第 1 天**（4 小时）: 任务 1.1（确认数据类型）, 任务 1.2（创建缓存工具）, 任务 1.3（扩展 DataSource）
2. **第 2 天**（6 小时）: 任务 2.1（创建命令行主文件）, 任务 2.2（实现查询功能）, 任务 2.3（实现输出格式化）
3. **第 3 天**（4 小时）: 任务 2.4（错误处理）, 任务 3.1（调试模式）, 任务 3.2（缓存控制）, 任务 3.3（汇总统计）
4. **第 4 天**（8 小时）: 任务 4.1（单元测试）, 任务 4.2（集成测试）, 任务 4.3（用户文档）, 任务 4.4（代码审查）

---

## 注意事项

1. **API Key 配置**: 确保测试环境配置了有效的 FootyStats API Key
2. **速率限制**: 测试时注意 API 速率限制，避免触发限制
3. **缓存清理**: 开发过程中定期清理缓存，确保测试最新数据
4. **错误恢复**: 实现优雅的错误恢复机制，避免程序崩溃
5. **文档同步**: 代码变更及时更新文档

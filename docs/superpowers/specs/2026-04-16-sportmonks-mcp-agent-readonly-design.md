# Sportmonks MCP Agent 只读化改造设计文档

**日期**：2026-04-16
**状态**：待开发
**范围**：`mcp_server/tools/sportmonks.py`、`datasource/sportmonks/service.py`、相关调用方与测试

---

## 背景

当前 Sportmonks MCP 既暴露读取能力，也暴露缓存预热、刷新、状态查询等能力。  
这导致 Agent 承担了不应承担的缓存编排职责，典型问题包括：

- Agent 需要决定是否 `prefetch`
- Agent 需要决定是否 `refresh`
- Agent 需要解释 `stale/partial` 并作流程分支
- `get_todays_matches` 与 `get_fixtures` 语义重复，调用心智复杂

本设计将边界收敛为：**缓存管理属于数据层内部职责，不属于 Agent 职责**。

---

## 目标

- MCP 对 Agent 仅暴露只读查询能力
- 预热与刷新改为数据层自动行为，不再由 Agent 决策
- 列表接口统一，减少 today/date 双入口重复
- 单场接口不再要求 Agent 传入大量上下文字段
- 调用方（analyzer/daily）不再显式调用缓存管理工具

---

## 非目标

- 不重构 FootyStats/Quant 工具链
- 不替换现有 Sportmonks 存储介质
- 不新增复杂调度系统
- 不在首期引入新的外部依赖

---

## 核心决策

### 1. Agent 仅可见两类能力

- `goalcast_sportmonks_get_matches`
- `goalcast_sportmonks_get_match`

### 2. 缓存策略完全内聚到数据层

- 自动预热：列表查询缺数据时自动执行
- 自动刷新：单场查询遇到过期或关键层缺失时自动执行
- 自动兜底：刷新失败时尽量返回可用数据并标记缺失

### 3. MCP 不暴露缓存控制参数

从 Agent-facing 接口中移除：

- `warm_if_missing`
- `refresh_if_stale`
- `layers`
- `cache_status` 查询入口

### 4. 只读语义优先于实现细节

MCP 只表达“查询意图”，不表达“缓存操作意图”。  
缓存是否命中、是否刷新、刷新哪些层，均由 service 内部策略决定。

---

## 对外接口设计（Agent-facing）

## 1) `goalcast_sportmonks_get_matches`

```python
async def goalcast_sportmonks_get_matches(
    date: str | None = None,
    leagues: list[str] | None = None,
) -> dict[str, Any]:
    ...
```

语义：

- 查询指定日期（默认今天）比赛列表
- 可按联赛过滤
- 无缓存时由数据层自动预热

返回要求：

- `ok: bool`
- `count: int`
- `data: list[dict]`

每场至少包含：

- `fixture_id`
- `match_date`
- `kickoff_time`
- `league_name`
- `home_team_name`
- `away_team_name`

## 2) `goalcast_sportmonks_get_match`

```python
async def goalcast_sportmonks_get_match(
    fixture_id: int,
    match_date: str | None = None,
) -> dict[str, Any]:
    ...
```

语义：

- 查询单场标准化详情
- 缓存缺失/过期/关键层缺失时由数据层自动补抓或刷新
- Agent 不关心缓存控制参数

返回要求：

- `ok: bool`
- `data: dict`
- 可选 `availability` 或 `data_gaps` 表达数据缺失事实

禁止返回对 Agent 可见的缓存控制建议（例如“请调用 refresh”）。

---

## 内部接口与职责（Service 层）

`datasource/sportmonks/service.py` 推荐收敛为以下核心方法：

```python
class SportmonksDataService:
    async def get_matches(
        self,
        date: str | None = None,
        leagues: list[str] | None = None,
    ) -> list[SportmonksFixtureSummary]:
        ...

    async def get_match_for_analysis(
        self,
        fixture_id: int,
        match_date: str | None = None,
    ) -> dict[str, Any]:
        ...
```

内部 helper（不暴露给 Agent）：

- `ensure_date_ready(date, leagues)`：保证日期级数据可读
- `ensure_match_ready(fixture_id, match_date)`：保证单场关键层可读
- `refresh_match_internal(...)`：内部刷新实现
- `prefetch_internal(...)`：内部预热实现

说明：

- 允许保留现有 `prefetch/refresh/get_cache_status` 作为内部方法
- 但 MCP 不再直接注册这些能力为 Agent-facing 工具

---

## 现有工具改造映射

| 现有工具 | 处理方式 | 目标 |
| ---- | ---- | ---- |
| `goalcast_sportmonks_get_todays_matches` | 删除或兼容转调 | 合并进 `get_matches(date=None)` |
| `goalcast_sportmonks_get_fixtures` | 重命名/兼容 | 统一为 `goalcast_sportmonks_get_matches` |
| `goalcast_sportmonks_get_match` | 保留并收敛入参 | 改为仅 `fixture_id (+ match_date)` |
| `goalcast_sportmonks_get_raw_match` | 内部化（默认） | 调试用途，不对 Agent 暴露 |
| `goalcast_sportmonks_prefetch_today` | 下线 Agent-facing | 改为内部自动行为 |
| `goalcast_sportmonks_prefetch` | 下线 Agent-facing | 改为内部自动行为 |
| `goalcast_sportmonks_refresh_match` | 下线 Agent-facing | 改为内部自动行为 |
| `goalcast_sportmonks_get_cache_status` | 下线 Agent-facing | 改为内部观测用途 |

---

## 逐文件开发清单

## A. `mcp_server/tools/sportmonks.py`

变更项：

- 新增 `goalcast_sportmonks_get_matches`
- 改造 `goalcast_sportmonks_get_match` 入参
- 移除 Agent-facing 的 prefetch/refresh/cache-status/raw 工具注册
- 更新 tool description 为“只读查询语义”

验收点：

- MCP 注册清单仅包含 Agent 所需只读工具
- 工具签名中不出现 `warm_if_missing`、`refresh_if_stale`、`layers`

## B. `datasource/sportmonks/service.py`

变更项：

- 新增或重命名为 `get_matches(date=None, leagues=None)`
- 新增 `get_match_for_analysis(fixture_id, match_date=None)`
- 在上述方法内部接管自动预热、自动刷新与关键层兜底
- 将缓存状态判断封装到内部函数，不外溢到 MCP 入参

验收点：

- 读取路径只需“查询意图”即可完成
- 无需调用方显式触发预热/刷新

## C. 调用方（skills/workflow）

变更项：

- analyzer 与 daily 流程只调用 `get_matches` + `get_match`
- 删除缓存管理分支逻辑（prefetch/refresh/cache_status）

验收点：

- 调用方不再出现缓存操作工具名
- 调用方不再传缓存控制参数

## D. 测试文件

建议改造：

- `tests/datasource/test_sportmonks_mcp_tools.py`
- `tests/datasource/*service*`（如已有）

新增断言重点：

- 工具注册收敛
- `get_matches` 自动预热路径
- `get_match` 自动刷新路径
- 单场接口入参收敛

---

## 数据与错误语义

## 数据可用性表达

允许在 `get_match` 返回中保留：

- `data_gaps`
- `overall_quality`
- `missing_layers`（作为数据质量信息）

不允许将以下能力外露为 Agent 需决策事项：

- 是否执行 refresh
- 是否执行 prefetch
- 刷新哪个 layer

## 错误处理原则

- 若自动补抓失败但仍有旧数据，返回可用数据并携带缺失说明
- 若完全无数据，返回明确错误与可读原因
- 错误信息聚焦“数据不可得”，避免暴露“你应该调用某缓存接口”

---

## 迁移计划

## 阶段 1：接口并存

- 增加新接口 `goalcast_sportmonks_get_matches`
- 旧接口保留但标记 deprecated

## 阶段 2：调用方切换

- analyzer/daily 全量切换到新只读接口
- 文档与技能提示移除缓存管理调用示例

## 阶段 3：边界收口

- 移除旧 Agent-facing 缓存工具注册
- 只保留内部 service 方法与观测能力

---

## 测试矩阵

## 单元测试

- `tools`：
  - 只注册只读工具
  - 接口签名符合新约束
- `service`：
  - 日期数据缺失 -> 自动预热 -> 列表可读
  - 单场数据过期 -> 自动刷新 -> 返回标准化详情
  - 单层失败 -> 兜底返回 + 缺失标记

## 集成测试

- 批量查询路径：
  - `get_matches` 返回 fixtures
  - 遍历 fixture 调 `get_match` 全程无需显式 prefetch/refresh
- 回归测试：
  - 不引入联赛过滤行为退化
  - 不破坏既有序列化结构的关键字段

---

## 验收标准（DoD）

- Agent-facing MCP 工具只剩只读查询能力
- Agent 调用链中不再出现 prefetch/refresh/cache-status
- `goalcast_sportmonks_get_match` 不再要求球队/联赛/赛季上下文参数
- 自动预热与自动刷新在 service 内部可观测并稳定执行
- 测试覆盖新的默认路径和失败兜底路径

---

## 实施顺序建议

1. 先改 `service` 能力边界（实现自动预热/刷新内聚）
2. 再改 `tools` 对外签名（只读化）
3. 然后切调用方（analyzer/daily）
4. 最后删旧工具与补测试

---

## 开发注意事项

- 兼容期内避免一次性删除全部旧方法，先转调再清理
- 保持 `fixture_id` 作为单场主键，不增加调用方心智成本
- 对“自动刷新失败”的兜底路径必须有测试
- 文档、示例、技能提示必须同步更新，否则容易回退到旧用法

---

## 一句话结论

对 Agent，Sportmonks MCP 必须呈现为“只读查询服务”；  
对系统内部，预热与刷新必须自动化并封装在数据层，调用方无感知。

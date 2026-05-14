# 后端架构重构 — 设计规范

**日期**: 2026-05-10  
**状态**: 设计中  
**目标**: 从多 Agent 异步流水线架构简化为按需触发的单一路径架构

---

## 1. 问题背景

当前后端存在三个核心问题：

### 1.1 数据获取过度复杂

数据获取路径为 **6 层调用链**：

```
Orchestrator → DataCollector → ToolExecutor → MCP工具 → SportmonksDataService → Provider → API
```

实际需求仅为：**联赛 + 日期 → 并行拉取数据**。MCP 协议和 ToolExecutor 的介入是不必要的复杂度。

### 1.2 多余 Agent 角色

当前有 4 个 Agent 角色参与流水线：

| 角色 | 价值评估 |
|------|----------|
| **Analyst** | ✅ 核心价值：xG/方向/置信度/亚盘建议 |
| **Trader** | 🔴 功能可并入 Analyst 输出 |
| **Reviewer** | 🔴 审核逻辑可在 Analyst 内部完成 |
| **Reporter** | 🔴 纯格式化输出，不需要 LLM |

### 1.3 数据源接入方式不统一

4 个 Provider 接入方式各不相同：

| Provider | 接入方式 |
|----------|----------|
| Sportmonks | MCP/ToolExecutor（最复杂） |
| OddAlerts | 半独立 DataCollector |
| FootyStats | 仅 discover，无数据采集 |
| Understat | 按联赛名查询 |

期望：每个数据源有统一接口，通过开关随时激活/关闭。

---

## 2. 设计目标

1. **按需触发** — 用户选择联赛 + 日期 → API 直接拉取数据并返回结果，无后台循环
2. **单一路径** — 一次请求一个生命周期：Request → Fetch → Persist → Optional Analyze → Response
3. **只保留 Analyst** — 唯一 LLM Agent，输出含投注建议
4. **数据源平等可开关** — 统一 `collect_fixture_data()` 接口，`config/sources.json` 配置，API 运行时切换
5. **数据持久化完整保留** — `data/matches/` 目录、JSON 格式、MatchStore 核心函数保留
6. **现有路由最大保留** — 只删除 `trigger` 端点，其余保留并内部精简

---

## 3. 新架构蓝图

### 3.1 新旧对比

```
旧架构（4 层 + 5 路循环）:
  Agent Layer: Orchestrator(5路) → Pipeline(5状态) → ClaudeAdapter
  Data Service Layer: DataFusion(8路) → DataCollector(MCP)
  Provider Layer: SM/OA/FS/US（接入各不同）
  API Layer: 5 路由 + 3 WebSocket

新架构（3 层 + 单一路径）:
  Service Layer: MatchService → DataSourceRegistry → Analyst
  Provider Layer: SM/OA/FS/US（统一接口）
  API Layer: 5 路由 + 3 WebSocket（保留并精简）
```

### 3.2 简化后的数据流

```
POST /api/matches/fetch {league, date, analyze?}
  → MatchService.fetch_and_save()
    → DataSourceRegistry.discover_all()    // 并行发现比赛
    → merge_fixtures()                     // 合并
    → DataSourceRegistry.collect_all()     // 并行拉取数据
    → MatchStore.save() + append_layer()   // 持久化
    → [可选] Analyst.analyze()             // LLM 分析
    → append_layer("analysis")
  → 返回 JSON 结果
```

### 3.3 新目录结构

```
backend/
├── main.py                    ← 简化 CLI
├── server/                    ← API 层（精简）
│   ├── server.py              ← 修改：注册新路由
│   ├── routes/
│   │   ├── match.py           ← 新增
│   │   ├── source.py          ← 新增
│   │   ├── board.py           ← 保留（refresh 内部改造）
│   │   ├── config.py          ← 保留不动
│   │   ├── chat.py            ← 保留不动
│   │   ├── agents.py          ← 精简（去 Trader/Reviewer/Reporter）
│   │   └── pipeline.py        ← 精简（去 trigger）
│   └── ws/
│       └── manager.py         ← 精简
├── services/                  ← 新增：核心服务层
│   ├── __init__.py
│   ├── data_source_registry.py
│   ├── match_service.py
│   ├── analyst.py
│   ├── match_store.py         ← 从 agents/core/ 迁移
│   └── fixture_merger.py      ← 从 agents/core/ 迁移
├── provider/                  ← 保留，新增 collect_fixture_data()
│   ├── base.py                ← 修改：新增抽象方法
│   ├── models.py
│   ├── sportmonks/client.py   ← 修改：新增 collect
│   ├── oddalerts/client.py    ← 修改：新增 collect（迁移自 DataCollector）
│   ├── footystats/client.py   ← 修改：新增 collect
│   └── understat/client.py    ← 修改：新增 collect
├── agents/                    ← 大幅精简
│   ├── adapters/
│   │   ├── adapter.py         ← 保留（ClaudeAdapter）
│   │   └── tool_executor.py   ← 保留（Analyst 需要）
│   ├── core/
│   │   ├── base.py            ← 保留
│   │   ├── directory_agent.py ← 保留（Analyst 需要）
│   │   ├── blackboard.py      ← 保留
│   │   └── events.py          ← 保留（WS 需要）
│   └── roles/
│       └── analyst/           ← 完整保留
├── config/
│   ├── settings.py            ← 保留
│   └── sources.json           ← 新增
├── analytics/                 ← 保留
├── utils/                     ← 保留
└── data/
    └── matches/               ← 保留（格式不变）
```

---

## 4. 数据持久化

### 4.1 保留内容

- 目录：`data/matches/`
- 文件命名：`MC-YYYYMMDD-HHMMSS-UUID.json`
- MatchStore 核心函数：`save / load / append_layer / update_status / list_all / count_by_status / generate_match_id`

### 4.2 移除的函数

- `claim_oldest()` — 不再需要 worker 认领机制
- `abandon_active()` — 不再需要重启清理
- `finalize()` — 不再需要最终化
- `_STATUS_MAP` — 不再需要自动状态映射

### 4.3 状态流转简化

```
旧: pending → analyzing → analyzed → trading → traded → reviewing → reviewed (→ feedback → analyzing, → rejected) → reported
    10 个状态

新: pending → analyzing → analyzed
    3 个状态
```

### 4.4 JSON Schema（简化后 7 个顶级字段）

```json
{
  "match_id": "MC-YYYYMMDD-HHMMSS-UUID",
  "status": "pending | analyzing | analyzed",
  "orchestrator": {prepared_at, fixture_id, home_team, away_team, league, kickoff_time},
  "metadata": {match_id, fixture_id, oa_fixture_id, provider_ids, home_team, away_team, league, kickoff_time, requested_models, prepared_at},
  "state": {"orchestrator": "done", "analyst": "done"},
  "raw_data": {"sportmonks": {...11 keys...}, "oddalerts": {...8 keys...}},
  "analysis": {home_xg, away_xg, ev, kelly_fraction, recommendation, raw_output, analyzed_at, "v4.0": {...}}
}
```

**移除字段**: `trading` / `review` / `report_ref` — Trader/Reviewer/Reporter 已去掉，这 3 个段不再产生。

### 4.5 代码迁移

```
agents/core/match_store.py  →  services/match_store.py
  - 删除: claim_oldest / abandon_active / finalize / _STATUS_MAP
  - 保留: save / load / append_layer / update_status / list_all / count_by_status / generate_match_id
```

---

## 5. DataSource Registry

### 5.1 设计目标

所有数据源平等对待，通过统一接口管理，支持运行时开关。

### 5.2 统一接口

每个 Provider 实现 3 个方法：

1. `async def is_available() -> bool` — 检查 API 是否可用（已有）
2. `async def discover_fixtures(league_ids, dates) -> list[ProviderFixture]` — 发现比赛（已有）
3. `async def collect_fixture_data(fixture_id) -> dict` — **新增**：为单场比赛拉取全部详细数据

### 5.3 DataSourceRegistry

```python
class DataSourceConfig:
    name: str       # "sportmonks" / "oddalerts" / "footystats" / "understat"
    enabled: bool    # 运行时开关
    provider: BaseProvider

class DataSourceRegistry:
    def __init__(self, config_path: str = "config/sources.json")
    def get_enabled() -> list[DataSourceConfig]
    def enable(name: str) / disable(name: str)   # 内存操作
    def status() -> dict                          # {name: {enabled, available, ...}}
    async def discover_all(league_ids, dates) -> dict[str, list]
    async def collect_all(provider_ids: dict) -> dict[str, dict]
```

### 5.4 配置文件: `config/sources.json`

```json
{
  "sportmonks": {"enabled": true,  "label": "SportMonks", "description": "...", "priority": 1},
  "oddalerts":  {"enabled": true,  "label": "OddAlerts",  "description": "...", "priority": 2},
  "footystats": {"enabled": false, "label": "FootyStats", "description": "...", "priority": 3},
  "understat":  {"enabled": false, "label": "Understat",  "description": "...", "priority": 4}
}
```

### 5.5 API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/sources | 查看所有数据源状态 |
| POST | /api/sources/{name}/enable | 激活 |
| POST | /api/sources/{name}/disable | 关闭 |

---

## 6. MatchService & API

### 6.1 MatchService

新增文件 `services/match_service.py`，替代旧 Orchestrator 的全部数据拉取逻辑。

```python
class MatchService:
    def __init__(self, registry: DataSourceRegistry)
    
    async def fetch_and_save(
        self, league: str, date: str,
        models: list[str] = None,
        analyze: bool = False
    ) -> dict:
        # 1. 解析联赛ID + 生成日期范围
        # 2. registry.discover_all() → 并行发现
        # 3. merge_fixtures(all_fixtures) → 合并
        # 4. 每场比赛: save() → registry.collect_all() → append_layer("raw_data")
        # 5. 可选: Analyst.analyze() → append_layer("analysis")
        # 6. 返回完整结果
```

### 6.2 新增 API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| **POST** | `/api/matches/fetch` | **核心入口**：联赛+日期 → 拉数据+持久化+可选分析 |
| POST | `/api/matches/{id}/analyze` | 对已有比赛执行分析 |

**请求示例**：

```json
POST /api/matches/fetch
{
  "league": "La Liga",
  "date": "2026-05-10",
  "models": ["v4.0"],
  "analyze": true
}
```

**响应示例**：

```json
{
  "matches": [{
    "match_id": "MC-20260510-002042-0D49DD21",
    "status": "analyzed",
    "orchestrator": {"home_team": "Real Madrid", ...},
    "analysis": {"home_xg": 2.24, "away_xg": 0.43, "ev": 0.12, ...}
  }],
  "sources_used": ["sportmonks", "oddalerts"],
  "total": 1
}
```

### 6.3 保留并内部改造的端点

| 端点 | 改造内容 |
|------|----------|
| `POST /api/board/matches/{id}/refresh/{source}` | 内部改为走新 Registry 而非旧 DataCollector |
| `GET /api/agents/status` | 去掉 Trader/Reviewer/Reporter 状态计数 |
| `GET /api/pipelines/status` | 精简为只显示 Analyst 相关状态 |
| `/ws/chat` | 内部改为走 MatchService 而非 Orchestrator |
| `/ws/status` | EventEmitter 保留，事件类型精简 |

### 6.4 删除的端点

| 端点 | 原因 |
|------|------|
| `POST /api/pipeline/trigger` | 旧 trigger 写入文件 → Orchestrator 轮询 → 间接拉取。新架构无后台进程，改用 POST /api/matches/fetch 直接执行并返回结果 |

### 6.5 保留不动的端点

`GET /api/board/*` / `GET /api/config/*` / `GET /api/chat/` / `GET /api/health` / `WS /ws/logs`

---

## 7. 简化版 Analyst

### 7.1 保留内容

- 所有角色定义文件：`agents/roles/analyst/*`（IDENTITY.md / AGENTS.md / SOUL.md / TOOLS.md / skills/* / ...）
- DirectoryAgentLoader — 角色定义加载
- ClaudeAdapter — 多轮 tool_use 循环（支持 Anthropic / OpenAI 双后端）
- ToolExecutor — 工具调用执行

### 7.2 新增 Analyst 类

文件：`services/analyst.py`

```python
class Analyst:
    ROLE_DIR = "backend/agents/roles/analyst"
    
    def __init__(self):
        self.adapter = ClaudeAdapter()
        self.agent_def = DirectoryAgentLoader.load_agent(self.ROLE_DIR)
    
    async def analyze(match_record: dict, models: list[str] = None) -> dict:
        # 1. _build_prompt() — 构建数据摘要（不直接 dump 450KB raw_data）
        # 2. adapter.run_agent() — 调用 LLM
        # 3. _parse_result() — 解析结构化 JSON
        # 返回 analysis 段内容
```

### 7.3 输出 Schema（含投注建议）

```json
{
  "home_xg": 2.24,                    // 主队预期进球
  "away_xg": 0.43,                    // 客队预期进球
  "total_xg": 2.67,                   // 总预期进球（新增）
  "xg_difference": 1.81,              // xG 差（新增）
  "direction": "home",                // 方向
  "confidence": 85,                   // 置信度 0-100
  "fulltime_result_probabilities": {
    "home": 0.756, "draw": 0.163, "away": 0.081
  },
  "ah_recommendation": {"side": "home", "line": -1.5, "rationale": "..."},
  "ev": 0.12,                         // 期望值（合并自旧 Trader）
  "kelly_fraction": 0.25,             // 凯利比例（合并自旧 Trader）
  "recommendation": "bet",            // bet | caution | pass（合并自旧 Trader）
  "v4.0": {"home_xg": 2.24, ...},     // 按模型分组
  "raw_output": "...",                // LLM 原始输出（截断）
  "analyzed_at": "2026-05-10T12:39:29+08:00"
}
```

### 7.4 数据摘要策略

raw_data 约 450KB，不能全量送入 LLM。摘要规则：

| 数据类型 | 处理方式 |
|----------|----------|
| predictive_xg | 直接传入（2 个 float） |
| predictions_summary | 直接传入（已汇总） |
| oddalerts.predictions 概率分布 | 直接传入（胜平负/BTTS/盘口覆盖/HT-FT） |
| stats 每队摘要 | 提取关键字段（场均进球/失球/BTTS%/零封%） |
| recent_stats (近5主场/客场) | 提取关键字段 |
| h2h | 直接传入 |
| odds_history (196条 × 7博彩公司) | **不传入**（数据量过大，LLM 无法有效利用） |
| predictions 原始列表 (28条) | 可省略（summary 已涵盖） |

### 7.5 调用链简化

```
旧: Orchestrator.analyst_loop()
       → match_store.claim_oldest("pending")
       → pipeline.run_analyst_step()
         → blackboard.load_partial(metadata+raw_data)
         → ClaudeAdapter.run_agent()
         → blackboard.merge_update(analysis)
       → match_store.append_layer("analysis")

新: MatchService._run_analysis(matches)
       → update_status(id, "analyzing")
       → Analyst.analyze(record)
         → build_prompt(metadata+raw_data_summary)
         → ClaudeAdapter.run_agent()
         → parse_result()
       → append_layer(id, "analysis", result)
       → update_status(id, "analyzed")
```

---

## 8. 文件变更地图

### 8.1 整体删除（2 个目录）

| 目录 | 原因 |
|------|------|
| `backend/datasource/` | DataFusion + Resolver 体系不再需要 |
| `backend/agents/roles/{trader,reviewer,reporter,orchestrator}/` | 只保留 Analyst |

### 8.2 单独删除

| 文件 | 原因 |
|------|------|
| `agents/core/orchestrator.py` | 5路异步循环 |
| `agents/core/pipeline.py` | 多 Agent 步骤编排 |
| `agents/core/coordinator.py` | 备用线性编排器 |
| `agents/core/data_collector.py` | MCP 数据收集 |
| `agents/core/state.py` | WorkflowState dataclass |
| `agents/scheduler.py` | APScheduler 定时任务 |
| `agents/llm_router.py` | 已被 ClaudeAdapter 替代 |
| `data/trigger.json` | 不再需要触发器文件 |

### 8.3 迁移

| 旧路径 | 新路径 | 变更 |
|--------|--------|------|
| `agents/core/match_store.py` | `services/match_store.py` | 精简 |
| `agents/core/fixture_merger.py` | `services/fixture_merger.py` | 精简 |
| `agents/core/league_config.py` | 合并到 `services/match_service.py` | 融合 |

### 8.4 新增

| 文件 | 说明 |
|------|------|
| `services/__init__.py` | 包初始化 |
| `services/data_source_registry.py` | 数据源注册管理 |
| `services/match_service.py` | 核心编排服务 |
| `services/analyst.py` | 简化版分析师 |
| `config/sources.json` | 数据源配置文件 |
| `server/routes/match.py` | 比赛相关端点 |
| `server/routes/source.py` | 数据源管理端点 |

### 8.5 修改

| 文件 | 变更 |
|------|------|
| `server/server.py` | 注册新路由，/ws/chat 内部改造 |
| `server/routes/agents.py` | 去 Trader/Reviewer/Reporter |
| `server/routes/pipeline.py` | 去 trigger 端点 |
| `server/routes/board.py` | refresh 内部走新 Registry |
| `server/ws/manager.py` | 精简事件类型 |
| `provider/base.py` | 新增 collect_fixture_data() 抽象方法 |
| `provider/sportmonks/client.py` | 新增 collect 实现 |
| `provider/oddalerts/client.py` | 新增 collect 实现（迁移自 DataCollector） |
| `provider/footystats/client.py` | 新增 collect 实现 |
| `provider/understat/client.py` | 新增 collect 实现 |
| `main.py` | 精简 CLI 命令 |

### 8.6 保留不动

| 文件 | 说明 |
|------|------|
| `agents/core/directory_agent.py` | Analyst 需要 |
| `agents/core/base.py` | Analyst 需要 |
| `agents/core/blackboard.py` | load_partial 仍有价值 |
| `agents/core/events.py` | WebSocket 需要 |
| `agents/adapters/adapter.py` | ClaudeAdapter |
| `agents/adapters/tool_executor.py` | Analyst 工具调用 |
| `agents/roles/analyst/*` | 角色定义完整保留 |
| `config/settings.py` | 系统配置 |
| `server/routes/board.py` | 文件浏览器 |
| `server/routes/config.py` | 配置管理 |
| `server/routes/chat.py` | Chat 空壳 |
| `utils/rate_limiter.py` | 速率限制 |
| `utils/config_parser.py` | JSONC/MD 解析 |
| `analytics/confidence.py` | 置信度计算 |
| `data/matches/*.json` | 已有比赛数据不变 |

### 8.7 数量汇总

| 类别 | 数量 |
|------|------|
| 文件删除 | 12+（含 2 个目录） |
| 文件修改 | ~12 |
| 文件迁移 | 3 |
| 文件新增 | 7 |
| 文件不动 | ~15 |

---

## 9. 风险评估

| 风险 | 等级 | 缓解措施 |
|------|------|----------|
| Provider 接口统一化可能引入回归 | 🟡 中 | 保持现有 client.py 不变，仅新增 collect_fixture_data() 方法 |
| raw_data 结构变化导致旧文件不兼容 | 🟢 低 | raw_data 段格式完全不变，只新增 provider key |
| ClaudeAdapter 移除对 Orchestrator 的依赖 | 🟢 低 | ClaudeAdapter 本身是独立的，不依赖 Orchestrator |
| WebSocket 流精简可能影响前端 | 🟡 中 | 保留 EventEmitter 和 ws/manager.py，只精简事件类型 |
| MatchStore 迁移遗漏依赖 | 🟢 低 | 所有导入集中管理，迁移后统一检查 |

---

## 10. 与当前架构的关键差异总结

| 维度 | 旧架构 | 新架构 |
|------|--------|--------|
| 触发方式 | 定时 + trigger 文件轮询 | API 直接调用 |
| 核心引擎 | Orchestrator 5路异步循环 | MatchService 同步请求 |
| Agent 数量 | 4 (Analyst/Trader/Reviewer/Reporter) | 1 (Analyst，含投注建议) |
| 数据获取 | DataCollector → MCP → ToolExecutor | Provider 直接 httpx 调用 |
| 状态存储 | match_store (文件系统) + claim_oldest 认领 | match_store (保留核心函数) |
| 数据源管理 | 分散在各处 | DataSourceRegistry 统一管理 |
| 路由数量 | 5 模块 + 3 WS | 5 模块 + 3 WS（保留并精简） |
| 被删端点 | — | 仅 POST /api/pipeline/trigger |
| status 状态 | 10 个 | 3 个 |
| JSON 字段 | 10 个顶级字段 | 7 个顶级字段 |

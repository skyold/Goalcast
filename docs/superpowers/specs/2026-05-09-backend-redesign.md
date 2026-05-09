# 后端架构重设计规范

**日期：** 2026-05-09  
**状态：** 已批准  

---

## 概述

将 Goalcast 从 5 个常驻异步 loop 的多 agent 系统，简化为清晰的三层 Pipeline 架构。唯一的 LLM agent 是 Analyst（分析 + 投注推荐）。数据获取改为普通异步函数，不再走 agent 调用。所有数据源平等对待，支持运行时开关。

---

## 目标

1. 删除 Trader / Reviewer / Reporter agent，价值有限
2. 数据获取改为普通 async 函数，不再是 agent 调用
3. 所有激活的 provider 平等参与 fixture 发现和数据收集
4. Provider（含 Analyst）可在运行时开关，无需重启
5. 前端精简为单页 Pipeline 页面，替代现有 5 个页面
6. Match Store 统一为单一 JSON 格式，消除双写

---

## 删除内容

| 组件 | 原因 |
|------|------|
| `agents/core/orchestrator.py` | 由 `pipeline/runner.py` 替代 |
| `agents/core/pipeline.py` | Trader/Reviewer/Reporter 步骤全部删除 |
| `agents/roles/trader/` | 功能合并进 Analyst |
| `agents/roles/reviewer/` | 删除 |
| `agents/roles/reporter/` | 删除 |
| `agents/core/blackboard.py` | 双写机制消除 |
| `agents/core/data_collector.py` | 移入 `pipeline/collector.py` |
| `datasource/` | 与 `provider/` 功能重叠 |
| `mcp_server/` | 不再需要 |
| 前端：`BoardPage`、`ChatPanel`、`DashboardPage`、`TokenStatsPage` | 由单页 Pipeline 替代 |

---

## 目录结构

```
backend/
├── pipeline/
│   ├── runner.py          # 核心：发现 → 收集 → 分析（顺序执行）
│   ├── discovery.py       # 并行从各 provider 发现赛程，合并去重
│   ├── collector.py       # 并行从各 provider 收集单场比赛数据
│   └── scheduler.py       # 定时 + 手动触发
├── provider/
│   ├── registry.py        # Provider 注册表，开关的唯一入口（新增）
│   ├── base.py            # ProviderBase 接口（保留）
│   ├── oddalerts/         # 保留现有 client
│   ├── sportmonks/        # 保留现有 client
│   ├── footystats/        # 保留现有 client
│   └── understat/         # 保留现有 client
├── store/
│   └── match_store.py     # 统一文件存储，单一 JSON 格式，单一写入路径（重写）
├── agents/
│   ├── analyst.py         # 唯一 agent：分析 + 投注推荐
│   └── roles/
│       └── analyst/       # Analyst role 定义（保留现有）
├── server/
│   └── routes/            # 精简后的 API 路由
└── config/
    └── providers.json     # 激活数据源 + analyst 开关配置（新增）
```

---

## Provider Registry

`config/providers.json` 是所有数据源开关的唯一数据源：

```json
{
  "analyst": { "enabled": true },
  "schedule": { "interval_hours": 1 },
  "providers": {
    "oddalerts":  { "enabled": true },
    "sportmonks": { "enabled": true },
    "footystats":  { "enabled": false },
    "understat":   { "enabled": false }
  }
}
```

`provider/registry.py` 职责：
- `get_active_providers()` → 返回所有 enabled=true 的 provider 实例列表
- `set_enabled(name: str, enabled: bool)` → 运行时开关，写回 JSON，无需重启
- Pipeline 所有地方只通过 Registry 获取 provider，不直接 import 具体 client

每个 provider 必须实现 `ProviderBase` 的两个方法：
- `discover_fixtures(dates: list[str]) -> list[ProviderFixture]`
- `collect_match(fixture_id: int) -> dict | None`

---

## Pipeline Runner

`pipeline/runner.py` 将现有 5-loop Orchestrator 替换为一个顺序执行的函数：

```
run_pipeline(leagues, dates, models)
    │
    ├─ 1. discovery.py
    │      并行：所有激活 provider → discover_fixtures(dates)
    │      合并去重（按队名 + 开球时间）→ UnifiedFixture 列表
    │      按联赛过滤（如有指定）
    │
    ├─ 2. 过滤已处理比赛（读 match_store）
    │      跳过状态为 analyzed 或 error 的比赛（force=True 时强制重跑）
    │
    ├─ 3. 对每场比赛：collector.py
    │      并行：所有激活 provider → collect_match(fixture_id)
    │      写入 match_store → 状态：collected
    │
    └─ 4. 若 analyst.enabled：
              analyst.py → 调用 Claude agent
              输入：所有激活 provider 收集的 raw_data
              输出：xG、亚盘方向、置信度、Kelly 注额
              写入 match_store → 状态：analyzed
           否则：
              跳过 → 状态保持：collected
```

**相比现有架构的关键简化：**
- 无常驻 asyncio loop，pipeline 运行一次后退出
- 无跨 loop 状态机（pending→analyzing→analyzed→trading→…）
- 只有 4 个比赛状态：`pending` → `collected` → `analyzed` / `error`
- Scheduler 按间隔调用 `run_pipeline()`，不再有 trigger 文件机制

---

## Analyst Agent

`agents/analyst.py` 合并现有 Analyst + Trader 的职责：

- **输入：** 单场比赛所有激活 provider 的 raw_data（合并后传给 Claude）
- **输出（JSON）：**
  ```json
  {
    "home_xg": 1.8,
    "away_xg": 1.2,
    "ah_recommendation": "主队 -0.5",
    "confidence": 0.72,
    "kelly_fraction": 0.08,
    "reasoning": "...",
    "analyzed_at": "2025-05-09T10:30:00+08:00"
  }
  ```
- 使用现有 `agents/roles/analyst/` role 定义
- 解析失败时：该比赛状态 → `error`，下次 pipeline 运行时重试

---

## Match Store（统一文件格式）

每场比赛一个 JSON 文件，路径：`data/matches/MC-YYYYMMDD-NNN.json`

```json
{
  "match_id": "MC-20250510-001",
  "status": "analyzed",
  "metadata": {
    "home_team": "Arsenal",
    "away_team": "Chelsea",
    "league": "Premier League",
    "kickoff_time": "2025-05-10 20:00:00",
    "provider_ids": {
      "sportmonks": 18329,
      "oddalerts": 54201
    },
    "collected_at": "2025-05-09T10:00:00+08:00"
  },
  "raw_data": {
    "oddalerts": { ... },
    "sportmonks": { ... }
  },
  "analysis": {
    "home_xg": 1.8,
    "away_xg": 1.2,
    "ah_recommendation": "主队 -0.5",
    "confidence": 0.72,
    "kelly_fraction": 0.08,
    "analyzed_at": "2025-05-09T10:30:00+08:00"
  }
}
```

`store/match_store.py` 职责：
- `save(match)` — 单一写入路径（无双写）
- `update(match_id, fields)` — 局部更新
- `list_matches(league=None, date=None, status=None)` — 带过滤的全量扫描
- `get(match_id)` — 读取单场比赛

---

## API Server

精简现有 5 个 route 文件，替换为：

```
GET  /api/matches                  比赛列表（支持 ?league=&date=&status= 过滤）
GET  /api/matches/:id              单场比赛完整数据
POST /api/pipeline/run             手动触发 pipeline
GET  /api/pipeline/status          当前 pipeline 状态（idle/running/error）
GET  /api/config/providers         获取所有 provider + analyst 开关状态
POST /api/config/providers         更新 provider / analyst 开关
GET  /api/config/schedule          获取定时间隔配置
POST /api/config/schedule          更新定时间隔

WS   /ws/events                    实时推送 pipeline 事件（发现/收集/分析进度）
```

删除：`/api/agents`、`/api/board`、`/api/chat`

---

## 前端（单页 Pipeline）

单页替代现有的 BoardPage、ChatPanel、DashboardPage、TokenStatsPage、PipelineMonitor。

**页面布局：**

```
┌──────────────────────────────────────────────────────────┐
│  Goalcast                          [立即运行]  ● 运行中  │  顶栏：手动触发 + 状态指示
├──────────────────────────────────────────────────────────┤
│  联赛: [全部 ▾]   日期: [2025-05-10 ▾]                  │  过滤栏
├──────────────────────────────────────────────────────────┤
│  Arsenal vs Chelsea  · 英超 · 20:00                      │
│  状态：数据获取完成 · 分析未激活                          │  (analyst 关闭)
│  ┌──────────────┐  ┌──────────────┐                     │
│  │  OddAlerts   │  │  Sportmonks  │                     │  数据源卡片（内容和样式同现在）
│  └──────────────┘  └──────────────┘                     │
├──────────────────────────────────────────────────────────┤
│  Barcelona vs Real Madrid  · 西甲 · 22:00                │
│  状态：已分析                                             │  (analyst 开启)
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  OddAlerts   │  │  Sportmonks  │  │   分析结果     │  │  分析卡片（额外展示）
│  └──────────────┘  └──────────────┘  └───────────────┘  │
├──────────────────────────────────────────────────────────┤
│  Provider 开关：OddAlerts ● Sportmonks ● Analyst ○       │  底部配置面板
│  定时运行：每 [1] 小时                                    │
└──────────────────────────────────────────────────────────┘
```

**比赛状态标签：**
- `pending` — 等待处理
- `collected`（analyst 开启）— 数据已收集，等待分析
- `collected`（analyst 关闭）— 数据获取完成 · 分析未激活
- `analyzed` — 已分析
- `error` — 处理失败（下次自动重试）

**数据源卡片：** 复用现有 `MatchSourcePanel.tsx` 的内容与样式  
**分析卡片：** 展示 xG、亚盘推荐、置信度、Kelly 注额

---

## 迁移说明

- 现有 `data/matches/MC-*.json` 文件格式混乱（legacy + blackboard 双写）。首次运行时需执行迁移脚本，将旧文件规范化为新格式。
- `config/sportmonks_leagues.json` 和 `config/oddalerts_leagues.json` 保持不变。联赛名称匹配从 LLM 解析改为 fuzzy 字符串匹配（使用 `thefuzz` 库）。
- `analytics/`（poisson、ev_calculator、confidence）保留为工具模块，Analyst role 可按需调用。

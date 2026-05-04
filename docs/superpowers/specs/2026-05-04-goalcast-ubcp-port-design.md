# Goalcast UBCP Port — yclake Frontend Migration Design

## Summary

将 [yclake](file:///Users/zhengningdai/workspace/skyold/yclake) 前端（含 UBCP 通用 Board 查看平台）完整移植到 Goalcast，同时将所有 Web 相关后端代码统一收敛到 `backend/server/` 目录下，与 yclake 的 `quant_system/server/` 结构对齐。Goalcast 独有的流水线监控能力通过 Extension 机制注入 yclake 框架，不修改 UBCP 协议核心。

## Goals

- **前端全量替换**：用 yclake frontend 覆盖 Goalcast frontend，保留 yclake 全部功能（Dashboard、Board、Chat、Token Stats、Logs）
- **UBCP 协议完整落地**：yclake 的 BoardPage 作为通用数据查看/管理平台，配置驱动，后端实现协议即可接入
- **Goalcast 扩展注入**：流水线监控（比赛卡片 Grid）通过新页面 `PipelineMonitor.tsx` + appStore 扩展实现
- **后端收敛对齐**：所有 Web 相关代码统一放在 `backend/server/` 下，删除 `backend/agents/web/`
- **品牌适配**：品牌名从 FAFETS → Goalcast，导航项微调，去除 Hypothesis

## Non-Goals

- 不修改 UBCP 协议设计（[design](file:///Users/zhengningdai/workspace/skyold/yclake/docs/superpowers/specs/2026-05-03-universal-board-connector-design.md) / [protocol](file:///Users/zhengningdai/workspace/skyold/yclake/docs/superpowers/specs/2026-05-03-universal-board-connector-protocol.md)）
- 不修改 `backend/agents/`、`backend/main.py` CLI、`backend/config/`、`backend/datasource/`、`backend/analytics/`
- 不对原 Goalcast 前端做任何兼容保留——全量替换

## Architecture

```text
Goalcast (移植后)
├── frontend/                          # = yclake frontend + Goalcast 扩展
│   ├── src/
│   │   ├── pages/
│   │   │   ├── DashboardPage.tsx      # 🔧 复制 + 加 DashboardExtras 渲染点
│   │   │   ├── BoardPage.tsx          # ⬜ 复制（UBCP 核心，零改动）
│   │   │   ├── ChatPanel.tsx          # ⬜ 复制
│   │   │   ├── TokenStatsPage.tsx     # ⬜ 复制
│   │   │   └── PipelineMonitor.tsx    # 🆕 Goalcast 流水线监控
│   │   ├── components/
│   │   │   ├── AgentDetailDrawer.tsx  # ⬜ 复制
│   │   │   ├── LogViewer.tsx          # ⬜ 复制
│   │   │   └── SideNav.tsx            # 🔧 品牌名 + 导航项
│   │   ├── extensions/
│   │   │   └── DashboardExtras.tsx    # 🔧 Goalcast Pipeline 状态摘要
│   │   ├── hooks/useWebSocket.ts      # ⬜ 复制
│   │   ├── services/
│   │   │   ├── api.ts                 # ⬜ 复制
│   │   │   ├── extensions.ts         # ⬜ 复制
│   │   │   └── ws.ts                  # ⬜ 复制
│   │   ├── store/appStore.ts          # 🔧 扩展 Goalcast WS 事件
│   │   ├── types/
│   │   │   ├── index.ts              # ⬜ 复制（UBCP 类型）
│   │   │   └── extensions.ts         # ⬜ 复制
│   │   ├── App.tsx                    # 🔧 路由调整
│   │   ├── config.ts                 # ⬜ 复制
│   │   ├── index.css                 # ⬜ 复制
│   │   └── main.tsx                  # ⬜ 复制
│   └── public/config.json            # 🔧 Goalcast 配置
├── backend/
│   ├── server/                        # 🆕 所有 Web 代码（对齐 yclake）
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── config.py             # GET /api/config
│   │   │   ├── board.py              # GET /api/board/{dir}[/{filename}]
│   │   │   └── chat.py               # POST /api/chat/
│   │   ├── ws/
│   │   │   ├── __init__.py
│   │   │   └── manager.py            # WebSocket 连接管理
│   │   ├── __init__.py
│   │   ├── config.json               # 服务端静态配置
│   │   ├── requirements.txt
│   │   └── server.py                 # FastAPI 入口
│   ├── agents/                        # ✅ 不动（纯 Agent 逻辑）
│   ├── main.py                        # ✅ 不动（CLI）
│   └── ...                            # ✅ 其余不动
└── docs/superpowers/specs/
    └── 2026-05-04-goalcast-ubcp-port-design.md
```

### 关键符号

| 符号 | 含义 |
|---|---|
| ⬜ | 从 yclake 直接复制，零改动 |
| 🔧 | 从 yclake 复制后需微调 |
| 🆕 | Goalcast 新建 |
| ✅ | 现有文件，不动 |
| 🗑️ | 现有文件，删除 |

---

## Component Breakdown

### 1. 前端：文件复制策略

#### 1.1 零改动复制（⬜）

以下文件从 `yclake/frontend/src/` 直接复制到 `Goalcast/frontend/src/`，不做任何修改：

| 文件 | 说明 |
|---|---|
| `pages/BoardPage.tsx` | UBCP 核心——列渲染、详情渲染、Actions、Provider 分流 |
| `pages/ChatPanel.tsx` | AI 对话面板 |
| `pages/DashboardPage.tsx` | Agent 状态面板（需加 DashboardExtras 渲染点，见 §1.2） |
| `pages/TokenStatsPage.tsx` | Token 统计页面 |
| `components/AgentDetailDrawer.tsx` | Agent 详情抽屉 |
| `components/LogViewer.tsx` | 日志查看器 |
| `hooks/useWebSocket.ts` | WebSocket 连接 hook |
| `services/api.ts` | REST API 客户端（/api 前缀拼接） |
| `services/ws.ts` | WebSocket 客户端类（含断线重连） |
| `services/extensions.ts` | Extension 注册机制 |
| `types/index.ts` | UBCP 类型定义 + AppConfig 类型 |
| `types/extensions.ts` | Extension 类型定义 |
| `config.ts` | 双层配置加载（静态 + 后端 merge） |
| `index.css` | 设计 Token + antd 暗色覆盖 + 动画 |
| `main.tsx` | 入口（loadConfig → render） |

以下文件从 yclake 根目录复制：

| 文件 | 说明 |
|---|---|
| `tsconfig.json`、`tsconfig.app.json`、`tsconfig.node.json` | TypeScript 配置 |
| `vite.config.ts` | Vite 构建配置 |
| `eslint.config.js` | ESLint 配置 |

#### 1.2 微调文件（🔧）

##### `components/SideNav.tsx`

- 品牌名：`FAFETS` → `Goalcast`
- 导航项：
  - 去掉 `{ label: "Hypothesis", path: "/hypothesis" }`
  - 新增 `{ label: "Pipeline", path: "/pipeline", icon: <PlayCircleOutlined /> }`

##### `layouts/AppLayout.tsx`

- 品牌名：`FAFETS` → `Goalcast`，副标题 `Console` → `Orchestrator`

##### `App.tsx`

- 去掉 `import HypothesisPage from "./extensions/HypothesisPage"`
- 去掉 `<Route path="/hypothesis" element={<HypothesisPage />} />`
- 新增 `import PipelineMonitor from "./pages/PipelineMonitor"`
- 新增 `<Route path="/pipeline" element={<PipelineMonitor />} />`

##### `pages/DashboardPage.tsx`

- 新增 `import DashboardExtras from "../extensions/DashboardExtras"`
- 在 `AlertBar` 之后（stat cards 之前）插入 `<DashboardExtras />` 渲染点
- 原有 yclake 的 `DashboardExtras` 是 "Cluster Controls"（R&D/Battle 按钮），Goalcast 重写为 Pipeline 状态摘要

##### `public/config.json`

完全重写为 Goalcast 配置（见 §3）。

##### `package.json`

从 yclake 复制，额外加上 Goalcast 原有的 `lucide-react`（PipelineMonitor 用）。

#### 1.3 删除文件（🗑️）

Goalcast 现有前端全部删除，仅保留 `public/favicon.svg`、`public/icons.svg`：

| 删除 | 原因 |
|---|---|
| `src/App.tsx`、`src/App.css` | yclake 版本替换 |
| `src/ws.ts` | 用 yclake `services/ws.ts` 替换 |
| `src/main.tsx`、`src/index.css` | yclake 版本替换 |
| `src/assets/` | 用不上 |

---

### 2. Goalcast 扩展：PipelineMonitor

#### 2.1 `pages/PipelineMonitor.tsx`

Goalcast 项目独有的流水线监控页面，路由 `/pipeline`。

**组件结构**：

```text
PipelineMonitor
├── 页面 Header：Pipeline Status + 活跃联赛 + WS 指示
├── 比赛卡片 Grid（antd Card，3 列响应式）
│   ├── 卡片 Header：
│   │   ├── match_id（截断显示）
│   │   ├── home_team vs away_team
│   │   └── 状态图标（Clock / Loader / CheckCircle / XCircle）
│   └── 卡片 Body：
│       ├── analyzing → antd Progress 动画
│       ├── done → 预测概率条 + EV 值 + Recommendation
│       └── error → 错误信息
└── 空状态：antd Empty（无活跃 Pipeline）
```

**复用 yclake 基础设施**：
- 用 `useAppStore` 读取 `pipelineMatches`、`pipelineStatus`、`activeLeagues`、`wsConnected`
- 用 antd `Card`、`Tag`、`Progress`、`Empty` 组件（与 yclake UI 一致）
- WebSocket 事件在 store 层统一处理，页面只做展示

#### 2.2 `extensions/DashboardExtras.tsx`

注入到 DashboardPage 中的 Goalcast Pipeline 状态摘要。

**实现方式**：DashboardPage.tsx 在 `AlertBar` 之后插入 `<DashboardExtras />` 渲染点。Goalcast 的 `DashboardExtras` 组件展示：

- 当前活跃联赛列表
- Pipeline 进度（analyzed / total）
- 最近完成比赛结果摘要

> **注**：yclake 原有的 `DashboardExtras.tsx` 是 "Cluster Controls"（R&D/Battle 启停按钮），且当前 DashboardPage.tsx 并未实际引用它。Goalcast 将其完全重写为 Pipeline 状态摘要组件。

#### 2.3 状态管理扩展

在 `store/appStore.ts` 中新增字段（**在现有一切字段之后追加**，不修改 yclake 原有逻辑）：

```ts
interface MatchCard {
  match_id: string;
  home_team: string;
  away_team: string;
  kickoff_time: string;
  status: "pending" | "analyzing" | "trading" | "done" | "error";
  predictions?: { home_win?: number; draw?: number; away_win?: number };
  ev?: number;
  recommendation?: string;
  error?: string;
}

// AppState 新增字段
pipelineMatches: Record<string, MatchCard>;
pipelineStatus: string;     // "Idle" | "Running..." | "Completed"
activeLeagues: string[];
```

在 `handleWsMessage` 的 `switch` 的 `default` 之前插入 Goalcast 扩展事件处理（不修改现有 case 分支）：

```ts
case "pipeline_start":
  set({ pipelineMatches: {}, pipelineStatus: "Running...", activeLeagues: (msg.payload as {leagues:string[]}).leagues ?? [] });
  break;
case "matches_found":
  // 初始化比赛卡片列表
  break;
case "match_step_start":
  // 更新单场比赛状态
  break;
case "match_result_ready":
  // 填充预测结果
  break;
case "match_step_error":
  // 标记错误
  break;
case "pipeline_complete":
  set({ pipelineStatus: "Completed" });
  break;
```

---

### 3. 配置文件

#### 3.1 `public/config.json`（前端静态配置）

```json
{
  "app": { "name": "Goalcast", "subtitle": "Football Quant System" },
  "modules": {
    "agents": true,
    "board": true,
    "tokens": true,
    "chat": true,
    "logs": true
  },
  "agents": {
    "clusters": [
      { "key": "orchestrator", "label": "Orchestrator", "color": "#00FF9D", "desc": "Pipeline coordinator" },
      { "key": "analyst",      "label": "Analyst",      "color": "#4ade80", "desc": "Match analysis" },
      { "key": "trader",       "label": "Trader",       "color": "#ff9500", "desc": "Trade execution" },
      { "key": "reviewer",     "label": "Reviewer",     "color": "#ef4444", "desc": "Quality review" },
      { "key": "reporter",     "label": "Reporter",     "color": "#3b82f6", "desc": "Report generation" }
    ]
  },
  "board": {
    "tabs": [
      {
        "dir": "matches",
        "label": "Matches",
        "columns": [
          { "key": "match_id",     "label": "ID",       "render": "text" },
          { "key": "home_team",    "label": "Home",     "render": "text" },
          { "key": "away_team",    "label": "Away",     "render": "text" },
          { "key": "kickoff_time", "label": "Kickoff",  "render": "date_time" },
          { "key": "status",       "label": "Status",   "render": "status_badge",
            "status_map": {
              "pending":   { "color": "default",    "text": "Pending" },
              "analyzing": { "color": "processing", "text": "Analyzing" },
              "traded":    { "color": "orange",     "text": "Traded" },
              "reviewed":  { "color": "green",      "text": "Reviewed" },
              "rejected":  { "color": "red",        "text": "Rejected" },
              "reported":  { "color": "blue",       "text": "Reported" }
            }
          }
        ]
      }
    ]
  }
}
```

#### 3.2 配置加载流程

对齐 yclake 的双层 merge（`config.ts` 已有此逻辑）：

```
1. fetch("/config.json")           → 静态配置
2. deepMerge(DEFAULT_CONFIG, static)
3. fetch("/api/config")            → 后端动态配置
4. deepMerge(static, backend)
5. useConfig() 返回最终配置
```

---

### 4. 后端：server/ 目录

#### 4.1 对齐结构

| yclake | Goalcast |
|---|---|
| `quant_system/server/server.py` | `backend/server/server.py` |
| `quant_system/server/routes/config.py` | `backend/server/routes/config.py` |
| `quant_system/server/routes/board.py` | `backend/server/routes/board.py` |
| `quant_system/server/routes/chat.py` | `backend/server/routes/chat.py` |
| `quant_system/server/ws/manager.py` | `backend/server/ws/manager.py` |

#### 4.2 `server/server.py` — FastAPI 入口

- 从 `agents/web/server.py` 迁移 WebSocket `/ws/chat` 逻辑
- 新增 `/ws/status` WebSocket 端点（yclake 标准，推送 `agent_status`、`pipeline_progress`、`board_update` 等）
- 新增 `/ws/chat` WebSocket 端点（Goalcast 独有，用户意图 → orchestrator 调度 + 事件回调）
- 挂载 REST 路由：`config`、`board`、`chat`

#### 4.3 `server/routes/config.py` — GET /api/config

返回 `AppConfig`，包含 `board.tabs` 和 `agents.clusters`。当前阶段可静态返回 `config.json` 的内容；后续可动态注入活跃联赛、运行中 Pipeline 状态。

#### 4.3.1 额外需要的 Stub 端点

yclake 的 `DashboardPage.tsx` 在挂载时会调用以下 API，这些需要后端提供（至少返回空数据以免报错）：

| 端点 | 方法 | 用途 | MVP 行为 |
|---|---|---|---|
| `/api/agents/status` | GET | Agent 状态列表 | 返回 `[]`（Goalcast 暂不用 Agent 状态，后续从 orchestrator 注入） |
| `/api/pipelines/status` | GET | Pipeline 状态列表 | 返回 `[]` 或从 WS 状态推导 |
| `/api/tokens/summary` | GET | Token 用量汇总 | 返回 `{total_tokens:0, total_cost:0, ...}`（Goalcast 暂未接入 Token 追踪） |
| `/api/tokens/records` | GET | Token 明细列表 | 返回 `{items:[], total:0, ...}` |
| `/api/tokens/agents/{id}` | GET | 单 Agent Token 统计 | 返回空对象 |

这些 stub 端点放在 `server/routes/` 下对应路由文件中。

#### 4.4 `server/routes/board.py` — GET /api/board/{dir}[/{filename}]

实现 UBCP default provider 的列表 + 详情端点：

- `GET /api/board/{dir}?page=1&page_size=20` → `{items, total, page, page_size}`
- `GET /api/board/{dir}/{filename}` → 单条 JSON（含 `_filename`）

数据源：扫描 `backend/data/{dir}/` 下的 JSON 文件。

#### 4.5 `server/routes/chat.py` — POST /api/chat/

实现 AI 对话端点。内部复用 `backend/agents/web/intent.py` 的 `parse_intent` 逻辑（迁移到 `server/routes/chat.py` 中内联）。

#### 4.6 `server/ws/manager.py` — WebSocket 连接管理

管理多个 WebSocket 客户端的连接、订阅和广播，对齐 yclake `ws/manager.py`。

#### 4.7 删除：`backend/agents/web/`

整个目录删除，内容迁移到 `backend/server/`。

---

### 5. WebSocket 事件系统

#### 5.1 端点设计

| 端点 | 协议 | 用途 | 来源 |
|---|---|---|---|
| `/ws/status` | JSON 单向推送 | 系统事件广播（yclake 标准） | yclake |
| `/ws/chat` | 文本双向 | 用户输入 → Orchestrator 调度 + 事件回调 | Goalcast 现有 |

#### 5.2 事件分类

**yclake 标准事件**（`/ws/status` 推送，appStore 已有处理）：

| 事件类型 | payload | 用途 |
|---|---|---|
| `agent_status` | `AgentStatus` | Agent 状态 → Dashboard |
| `pipeline_progress` | `PipelineState` | Pipeline 进度 → Dashboard |
| `board_update` | `BoardUpdatePayload` | 文件落盘 → BoardPage 刷新 |
| `result_created` | `ResultCreated` | 新结果入库 → Toast 通知 |

**Goalcast 扩展事件**（`/ws/status` 或 `/ws/chat` 回调推送，appStore 新增处理）：

| 事件类型 | payload | 用途 |
|---|---|---|
| `pipeline_start` | `{leagues, date?}` | Pipeline 启动 → PipelineMonitor |
| `matches_found` | `{total, matches[]}` | 发现比赛 → PipelineMonitor |
| `match_step_start` | `{match_id, step}` | 分析步骤开始 → PipelineMonitor |
| `match_result_ready` | `{match_id, predictions, ev, recommendation}` | 分析完成 → PipelineMonitor |
| `match_step_error` | `{match_id, message}` | 分析错误 → PipelineMonitor |
| `pipeline_complete` | `{message, reviewed}` | Pipeline 完成 → PipelineMonitor |

---

### 6. 错误处理

| 场景 | 策略 |
|---|---|
| `/api/config` 不可达 | 降级到静态 `config.json`（`config.ts` 已有） |
| Board list/detail 请求失败 | 空列表/空抽屉 + 可见错误提示（`BoardPage.tsx` 已有） |
| WS `/ws/status` 断连 | 自动重连 3s 间隔（`WebSocketClient` 已有） |
| Pipeline 后台异常 | `match_step_error` → 卡片变红，错误信息可见 |
| 无 WebSocket（非 Pipeline 场景） | 页面显示 "Disconnected"，数据加载走 REST fallback |

---

### 7. 测试策略

| 层 | 内容 | 来源 |
|---|---|---|
| 前端单元测试 | `tests/BoardPage.test.tsx`、`tests/config.test.ts` | yclake 直接复制 |
| 后端集成测试 | `/api/config` 响应格式、`/api/board/{dir}` 分页 | 新增 |
| WebSocket 测试 | `/ws/status` 事件推送、`/ws/chat` 对话往返 | 复用 `test_server.py` |

---

### 8. 实施顺序

```
Step 1: 前端基础设施就位
  ├── 删除 Goalcast 旧前端文件（保留 public/ 静态资源）
  ├── 复制 yclake frontend 全部 src/ + config 文件 + vite/tsconfig
  ├── 合并 package.json（yclake 为基础 + lucide-react）
  └── 验证 npm install && npm run dev 可启动

Step 2: 品牌 + 配置适配
  ├── SideNav / AppLayout 品牌名修改
  ├── App.tsx 路由调整（去 /hypothesis，加 /pipeline）
  ├── public/config.json 写入 Goalcast 配置
  ├── DashboardPage.tsx 加 DashboardExtras 渲染点
  └── 验证 Dashboard / Board / Chat / TokenStats 页面正常渲染

Step 3: Goalcast 扩展开发
  ├── appStore 扩展（pipelineMatches、pipelineStatus 等 + WS 事件处理）
  ├── PipelineMonitor.tsx 页面（比赛卡片 Grid）
  ├── DashboardExtras.tsx 扩展（Pipeline 状态摘要）
  └── 验证 /pipeline 路由可独立访问，空状态正常

Step 4: 后端 server/ 重构
  ├── 创建 backend/server/ 目录结构
  ├── 迁移 agents/web/server.py → server/server.py（/ws/chat）
  ├── 新增 routes/config.py、board.py、chat.py
  ├── 新增 ws/manager.py + /ws/status
  ├── 删除 backend/agents/web/
  └── 验证 GET /api/config、Board list API、/ws/status

Step 5: 联调验证
  ├── 前端 /api/config 拉取成功
  ├── BoardPage matches Tab 加载正常
  ├── /ws/status 推送前端接收
  ├── /ws/chat → orchestrator → 事件 → PipelineMonitor 端到端
  └── ChatPanel 对话正常
```

---

### 9. 不动部分

| 目录 / 文件 | 状态 |
|---|---|
| `backend/agents/` 全部 | 不动 |
| `backend/main.py` | 不动 |
| `backend/config/` | 不动 |
| `backend/datasource/` | 不动 |
| `backend/analytics/` | 不动 |
| `backend/scripts/` | 不动 |
| `backend/mcp_server/` | 不动 |
| `backend/skills/` | 不动 |
| `docker/` | 不动 |
| `docs/`（除本 spec 新增） | 不动 |
| `tests/` | 不动 |

# Universal Board Connector Protocol（UBCP）v1 — Goalcast 适配版

**日期**: 2026-05-05  
**状态**: 已适配  
**目标**: 让前端 BoardPage 成为"Goalcast 足球量化分析系统的通用比赛观察平台"。任何后端只要实现本协议，即可接入并获得一致的列表、详情、语义化渲染与动作能力。

---

## 1. 约束与术语

### 1.1 协议作用域

- 协议覆盖范围：Board 的 Tab 配置、数据源 Provider、列表/详情契约、列/详情渲染声明、Actions 行为、实时推送（Streaming）。
- 不覆盖范围：鉴权/权限模型、审计/风控策略、跨域访问（默认同域 `/api`）。

### 1.2 路径与模板

- **API Base**：前端固定将所有请求拼接到 `/api` 下（见 [api.ts](file:///Users/zhengningdai/workspace/skyold/Goalcast/frontend/src/services/api.ts#L19-L31)）。
- 因此本协议中所有 `endpoint` / `endpoints.*` 必须满足：
  - 以 `/` 开头
  - **不得**以 `/api/` 开头（否则会变成 `/api/api/...`）
- **URL Path 模板**：统一使用 `{id}`、`{dir}`、`{filename}` 等占位符，替换时必须对值做 URL 编码。
- **Body 模板**：统一使用 `{{...}}` 占位符（见 §7）。

---

## 2. 配置模型（BoardTab）

Board 由若干 Tab 组成。每个 Tab 配置决定：

- 使用哪个 Provider 拉取/订阅数据（`source`）
- 列如何渲染（`columns`）
- 详情如何渲染（`source.detail`）
- 用户可触发哪些动作（`actions`）

```ts
export interface BoardTab {
  dir: string;
  label: string;
  columns: ColumnDef[];
  source?: BoardTabSource; // 缺省则为 default provider
  actions?: TabAction[];
}
```

---

## 3. Provider 总览

`source.provider` 决定连接方式与接口契约。

| provider | 典型场景 | 数据获取方式 |
| :-- | :-- | :-- |
| `default` | 扫描 JSON 文件目录（Goalcast matches） | REST（仓库内置） |
| `rest` | 自定义 REST 列表/详情 | REST |
| `streaming` | 实盘/实时截面（预留） | WebSocket |
| `analytical` | 海量数据分页/筛选/排序（预留） | REST |
| `langgraph` | Agent 检查点/轨迹（预留） | REST |

---

## 3.1 服务端 API 实现清单（Required/Optional） — Goalcast 现状

### 3.1.1 平台启动（Required）

| 能力 | 方法 | 路径 | 说明 |
| :-- | :-- | :-- | :-- |
| 前端配置拉取 | GET | `/api/config` | 返回 `AppConfig`，包含 `board.tabs`（见 [config.py](file:///Users/zhengningdai/workspace/skyold/Goalcast/backend/server/routes/config.py#L5-L23)） |

### 3.1.2 default provider（Required）

| 能力 | 方法 | 路径 | 说明 |
| :-- | :-- | :-- | :-- |
| 列表 | GET | `/api/board/{dir}` | query：`page`、`page_size`；response：`{items,total,page,page_size}` |
| 详情 | GET | `/api/board/{dir}/{filename}` | response：单条 JSON（注入 `_filename`） |

Goalcast 当前 Matches Tab 即使用 default provider，读取 `backend/data/matches/*.json`。

### 3.1.3 rest provider（可选）

如果未来 Goalcast 添加独立 REST 端点（如分析师数据、回测结果），可使用 rest provider。

| 能力 | 方法 | 路径 | 说明 |
| :-- | :-- | :-- | :-- |
| 列表 | GET | `{endpoints.list}` | query：`page`、`page_size`；response：默认 `{items,total,page,page_size}`（支持 `list_response` 映射） |
| 详情 | GET | `{endpoints.detail}` | `{id}` 由 `id_field` 替换 |

### 3.1.4 全局事件通道（已实现）

用于在文件落盘/分析完成后，通知前端刷新 default 列表。

| 能力 | 方法 | 路径 | 说明 |
| :-- | :-- | :-- | :-- |
| 全局事件 WS | WS | `/ws/status` | 包含 `board_update` 事件（见 [server.py](file:///Users/zhengningdai/workspace/skyold/Goalcast/backend/server/server.py#L36-L44)） |

`board_update` 事件结构：

```json
{ "type": "board_update", "payload": { "dir": "matches", "filename": "MC-xxx.json", "action": "created" } }
```

### 3.1.5 MVP 约束

Goalcast 当前仅使用 default provider。MVP 最小可用集合为：

- Required：
  - `GET /api/config`
  - default provider：`GET /api/board/{dir}`、`GET /api/board/{dir}/{filename}`
- Strongly Recommended：
  - `WS /ws/status` + `board_update`（已实现，用于触发列表刷新）
- Not Required（MVP 不阻塞）：
  - streaming/analytical/langgraph providers
  - `endpoints.history`、`endpoints.export`
  - `detail.format` 的 `diff/chart_timeseries/agent_trace`（先保留 `markdown/code/json`）

---

## 4. Source（BoardTabSource）

### 4.1 通用字段

```ts
export type BoardTabProvider = "default" | "rest" | "streaming" | "analytical" | "langgraph";

export interface BoardTabSourceBase {
  provider: BoardTabProvider;
  id_field: string;
  detail?: BoardTabDetail;
}
```

### 4.2 default provider（Goalcast 当前使用）

缺省 `source` 等价于：

```json
{ "provider": "default", "id_field": "match_id" }
```

端点：

- 列表：`GET /api/board/{dir}?page=&page_size=`
- 详情：`GET /api/board/{dir}/{filename}`

列表响应（含 metadata 扁平化）：

```json
{
  "items": [
    {
      "_filename": "MC-xxx.json",
      "match_id": "MC-xxx",
      "home_team": "Chelsea",
      "away_team": "Nottingham Forest",
      "league_name": "Premier League",
      "kickoff_time": "2026-05-04 14:00:00",
      "status": "reported",
      "analysis": { ... },
      "trading": { ... },
      "review": { ... }
    }
  ],
  "total": 5,
  "page": 1,
  "page_size": 20
}
```

> `home_team`、`away_team`、`kickoff_time`、`league_name` 由 `_flatten_metadata()` 从 `metadata` 对象中提升到顶层（见 [board.py](file:///Users/zhengningdai/workspace/skyold/Goalcast/backend/server/routes/board.py#L60-L70)）。

### 4.3 rest provider

```ts
export interface BoardTabEndpoints {
  list: string;
  detail: string;
  history?: string;
}

export interface RestSource extends BoardTabSourceBase {
  provider: "rest";
  endpoints: BoardTabEndpoints;
  list_response?: {
    items?: string;
    total?: string;
    page?: string;
    page_size?: string;
  };
}
```

请求约定：

- list：`GET {endpoints.list}?page=&page_size=`（可扩展额外 query 参数）
- detail：`GET {endpoints.detail}`，其中 `{id}` 替换为行 `id_field` 的值

### 4.4 streaming provider（预留）

```ts
export interface StreamingSource extends BoardTabSourceBase {
  provider: "streaming";
  ws_topic: string;
  buffer_size?: number;
  update_mode?: "upsert" | "append_only";
}
```

### 4.5 analytical provider（预留）

### 4.6 langgraph provider（预留）

---

## 5. Columns（列渲染协议）

### 5.1 ColumnDef

```ts
export type ColumnRenderer =
  | "text"
  | "status_badge"
  | "direction_badge"
  | "percentage_color"
  | "number_precision"
  | "heatmap"
  | "relative_time"
  | "date_time"
  | "code_snippet"
  | "link"
  | "boolean";

export interface ColumnDef {
  key: string;
  label: string;
  render?: ColumnRenderer;
  precision?: number;
  status_map?: Record<string, { color: string; text: string }>;
  direction_map?: Record<string, { color: string; label: string }>;
  domain?: [number, number];
  format?: string;
  link_template?: string;
  language?: string;
}
```

### 5.2 Goalcast 列配置

```json
{
  "columns": [
    { "key": "match_id",     "label": "ID",       "render": "text" },
    { "key": "home_team",    "label": "Home",     "render": "text" },
    { "key": "away_team",    "label": "Away",     "render": "text" },
    { "key": "league_name",  "label": "League",   "render": "text" },
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
```

Goalcast pipeline 状态流转：`pending → analyzing → traded → reviewed → reported`（或 `rejected`）。

### 5.3 回退规则

- 未配置 `render` 或 `render` 不支持 → `text`
- `status_badge` 若 `status_map` 不包含当前值 → 灰色显示原始值

---

## 6. Detail（详情渲染协议）

### 6.1 模式

```ts
export type DetailMode = "json" | "tabs";
export type DetailFormat = "markdown" | "code" | "json" | "diff" | "chart_timeseries" | "agent_trace";

export interface DetailTab {
  label: string;
  field: string;
  format: DetailFormat;
  language?: string;
}

export interface BoardTabDetail {
  mode: DetailMode;
  tabs?: DetailTab[];
}
```

### 6.2 Goalcast 详情配置

```json
{
  "detail": {
    "mode": "tabs",
    "tabs": [
      { "label": "分析摘要", "field": "analysis", "format": "json" },
      { "label": "交易决策", "field": "trading.results", "format": "json" },
      { "label": "质量审查", "field": "review.verdict", "format": "markdown" },
      { "label": "原始数据", "field": "", "format": "json" }
    ]
  }
}
```

各 tab 的数据源：

| tab | field 路径 | 数据内容 |
| :-- | :-- | :-- |
| 分析摘要 | `analysis` | Analyst 输出：xG、概率、推荐、置信度等 |
| 交易决策 | `trading.results` | Trader 输出：交易信号、赔率、建议 |
| 质量审查 | `review.verdict` | Reviewer 文本审查意见（Markdown） |
| 原始数据 | 空字符串 | 完整 JSON 原始比赛数据 |

### 6.3 字段取值规则

前端通过 `getByPath(data, tab.field)` 按点路径取值（见 [BoardPage.tsx](file:///Users/zhengningdai/workspace/skyold/Goalcast/frontend/src/pages/BoardPage.tsx#L92-L99)）。当 `field` 为空字符串时，取整个 `data` 对象。

---

## 7. Actions（动作协议）

### 7.1 模型

```ts
export type ActionScope = "row" | "selection" | "global";
export type ActionKind = "api_call" | "ws_send" | "navigate" | "inject_chat";
export type ActionColor = "default" | "blue" | "green" | "orange" | "red";

export interface ActionCondition {
  field: string;
  equals?: any;
  not_equals?: any;
}

export interface TabAction {
  label: string;
  tooltip?: string;
  scope: ActionScope;
  kind: ActionKind;
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  endpoint?: string;
  body_template?: Record<string, any>;
  target_tab?: string;
  condition?: ActionCondition;
  color?: ActionColor;
  require_confirm?: boolean;
}
```

### 7.2 模板变量

`body_template` 支持以下占位符：

- `{{row.<field>}}`：当前行字段值
- `{{selected_ids}}`：selection scope 下，选中行的 `id_field` 数组
- `{{tab.dir}}`：当前 tab 的 dir

### 7.3 Goalcast 典型动作

| label | kind | scope | 说明 |
| :-- | :-- | :-- | :-- |
| 助手解读 | `inject_chat` | row | 将比赛数据注入 Chat 面板（已硬编码实现） |
| 重新分析 | `api_call` | row | 触发对该比赛重新运行 pipeline（需后端支持） |

---

## 8. Goalcast 当前后端覆盖检查

| 能力 | 方法 | 路径 | 状态 |
| :-- | :-- | :-- | :-- |
| 配置拉取 | GET | `/api/config` | ✅ 已实现（[config.py](file:///Users/zhengningdai/workspace/skyold/Goalcast/backend/server/routes/config.py)） |
| default 列表 | GET | `/api/board/{dir}` | ✅ 已实现（[board.py](file:///Users/zhengningdai/workspace/skyold/Goalcast/backend/server/routes/board.py#L18-L44)） |
| default 详情 | GET | `/api/board/{dir}/{filename}` | ✅ 已实现（[board.py](file:///Users/zhengningdai/workspace/skyold/Goalcast/backend/server/routes/board.py#L47-L59)） |
| WS 全局事件 | WS | `/ws/status` | ✅ 已实现（[server.py](file:///Users/zhengningdai/workspace/skyold/Goalcast/backend/server/server.py#L36-L44)） |
| metadata 扁平化 | — | board.py `_flatten_metadata()` | ✅ 已实现（[board.py](file:///Users/zhengningdai/workspace/skyold/Goalcast/backend/server/routes/board.py#L62-L72)） |
| WS board topic | WS | `/ws/board/{topic}` | ❌ 未实现（预留） |
| streaming provider | — | — | ❌ 未实现（预留） |

---

## 9. Goalcast 字段映射表

| 原始 JSON 路径 | 扁平化字段 | 列表显示 | 详情 tab | 渲染器 |
| :--- | :--- | :---: | :---: | :--- |
| `metadata.match_id` | `match_id` | ✅ | — | `text` |
| `metadata.home_team` | `home_team` | ✅ | — | `text` |
| `metadata.away_team` | `away_team` | ✅ | — | `text` |
| `metadata.league.name` | `league_name` | ✅ | — | `text` |
| `metadata.kickoff_time` | `kickoff_time` | ✅ | — | `date_time` |
| `status` | `status` | ✅ | — | `status_badge` |
| `match_id` | `match_id` | — | ✅ 原始数据 | `json` |
| `analysis` | `analysis` | — | ✅ 分析摘要 | `json` |
| `trading.results` | `trading.results` | — | ✅ 交易决策 | `json` |
| `review.verdict` | `review.verdict` | — | ✅ 质量审查 | `markdown` |
| `review.notes` | `review.notes` | — | ❌ | — |
| `state` | `state` | — | ❌ | — |
| `raw_data` | `raw_data` | — | ❌ | — |
| `report_ref` | `report_ref` | — | ❌ | — |

---

## 10. 兼容性与迁移

### 10.1 旧配置兼容

当前 Goalcast 无旧配置需要迁移。`source.provider` 字段直接使用协议规范。

### 10.2 现有后端覆盖点

- default provider：已实现 `/api/board/{dir}` 与 `/api/board/{dir}/{filename}`（见 [board.py](file:///Users/zhengningdai/workspace/skyold/Goalcast/backend/server/routes/board.py)）
- rest provider：预留，配置示例见 §4.3
- streaming provider：需要新增 `/ws/board/{topic}`（当前只有 `/ws/status`，见 [server.py](file:///Users/zhengningdai/workspace/skyold/Goalcast/backend/server/server.py#L36-L44)）

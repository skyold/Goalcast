# Universal Board Connector — 设计规范（Goalcast 适配版）

**日期**: 2026-05-05
**状态**: 已适配
**基于**: Agent Dashboard Framework 设计规范（`2026-05-02-agent-dashboard-framework-design.md`）、BoardPage 多数据源适配（`2026-05-02-board-multisource-design.md`）
**先行讨论**: 方案对比（2026-05-03 对话记录）
**适配项目**: Goalcast 足球量化分析系统

---

## 1. 问题背景

当前 `BoardPage` 已通过 `BoardTabSource` 初步支持了"默认模式"（JSON 文件扫描）和"rest 模式"（自定义 API），但存在以下局限：

1. **Provider 类型单一**：仅支持默认模式（JSON 文件扫描），无法覆盖自定义 REST API 等场景。
2. **列渲染无语义**：所有列按纯文本渲染，无法自动识别百分比、状态徽章、相对时间等语义。
3. **详情渲染固定**：Markdown / Code / JSON 之外缺少图表、Diff 对比等模式。
4. **无动作协议**：用户在截面上无法触发操作（如"重新分析""助手解读"），只能手动跳转。

这些问题导致每次新项目接入时都需要修改前端代码，违背了"配置即 UI"的目标。

---

## 2. 设计目标

1. **标准化**：定义一套 Protocol，任何后端只要实现该协议，即可无缝接入 BoardPage。
2. **多 Provider 支持**：从文件目录延伸到自定义 REST API。
3. **语义化渲染**：前端根据列级 `render` 声明自动选择组件。
4. **可操作截面**：通过 `actions` 协议让用户直接在截面上触发操作。
5. **向后兼容**：所有现有 Tab 不做任何配置修改即可正常工作。

---

## 3. 架构方案：Provider 分类模式（Hybrid）

### 3.1 方案对比

| 维度 | 方案 A: 协议先行 | 方案 B: 灵活映射 | 方案 C: Provider 分类（推荐）|
| :--- | :--- | :--- | :--- |
| 前端复杂度 | 极低 | 高（需解析器） | 中（Provider 模式匹配）|
| 后端适配成本 | 高（必须适配协议）| 极低 | 低（按类别实现接口）|
| 实盘 WebSocket 支持 | 需额外约定 | 难处理 | 原生支持（Streaming Provider）|
| 海量数据分页 | 需额外约定 | 难处理 | 原生支持（Analytical Provider）|
| 跨项目复用 | 强 | 最强 | 强 |

**选择方案 C**。Goalcast 当前以"比赛 JSON 文件扫描"为主，预留扩展 REST/Streaming 的可能性。

### 3.2 Provider 分类

```
BoardTabSource
├── provider: "default"       → 现有逻辑（/api/board/{dir}）
├── provider: "rest"          → 自定义 REST API
├── provider: "streaming"     → WebSocket 实时推送（预留）
├── provider: "analytical"    → 数据库分页 / 查询（预留）
└── provider: "langgraph"     → LangGraph 检查点（预留）
```

---

## 4. Source Provider 详细规范

### 4.1 `default` — 默认模式（向后兼容）

不配置 `source` 的 Tab 自动使用此模式。行为完全不变。

| 操作 | 端点 |
| :--- | :--- |
| 列表 | `GET /api/board/{dir}` |
| 详情 | `GET /api/board/{dir}/{filename}` |
| 行 ID | `_filename` |

**何时用**：平铺 JSON 文件的简单场景。Goalcast 的 matches 目录即使用此模式。

---

### 4.2 `rest` — 自定义 REST API

适用于已有独立 REST 端点的数据源。

```json
{
  "source": {
    "provider": "rest",
    "id_field": "match_id",
    "endpoints": {
      "list": "/board/matches",
      "detail": "/board/matches/{id}"
    },
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
}
```

**新增字段说明**：

| 字段 | 类型 | 必填 | 说明 |
| :--- | :--- | :--- | :--- |
| `provider` | `string` | 是 | 固定为 `"rest"` |
| `endpoints.list` | `string` | 是 | 列表端点，以 `/` 开头 |
| `endpoints.detail` | `string` | 是 | 详情端点，支持 `{id}` 占位符 |
| `endpoints.history` | `string` | 否 | 用于版本回溯的端点 |
| `detail` | `object` | 否 | 详情渲染配置 |

---

### 4.3 `streaming` — WebSocket 实时推送（预留）

Goalcast 当前无实时推送场景，协议定义供后续扩展。

---

### 4.4 `analytical` — 数据库分页 / 查询（预留）

---

### 4.5 `langgraph` — 智能体执行检查点（预留）

---

## 5. 列渲染器（Column Renderer）协议

每个 `column` 增加可选的 `render` 字段。前端据此选择渲染组件。

### 5.1 渲染器清单

| `render` 值 | 适用范围 | 渲染行为 | 额外字段 |
| :--- | :--- | :--- | :--- |
| `text` | 所有 | 纯文本（默认） | — |
| `status_badge` | 枚举值 | 带颜色的文本徽章 | `status_map`（必填） |
| `direction_badge` | 方向枚举 | `↑`/`↓`/`—` 带颜色 | `direction_map`（必填） |
| `percentage_color` | 数值 | 绿涨红跌自动染色 | `precision`（可选，默认 4） |
| `number_precision` | 数值 | 固定小数位 | `precision`（必填） |
| `heatmap` | 数值 | 单元格背景热力图 | `domain`（可选，`[min, max]`） |
| `relative_time` | 时间字符串 | 相对时间（如 "3 分钟前"） | — |
| `date_time` | 时间字符串 | 绝对时间格式化 | `format`（可选，如 `"YYYY-MM-DD HH:mm"`） |
| `code_snippet` | 短文本 | 等宽字体 + 截断 | `language`（可选） |
| `link` | 字符串 | 可点击跳转 | `link_template`（可选） |
| `boolean` | 布尔值 | `✓` / `✗` 图标 | — |

### 5.2 配置示例（Goalcast Matches Tab）

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

### 5.3 渲染回退规则

若 `render` 字段为空或值不在清单中，前端回退为 `"text"`。若 `status_map` 中不包含当前值，使用默认灰色显示原始值。

---

## 6. 详情渲染器（Detail Renderer）协议

### 6.1 详情模式

| `mode` 值 | 行为 |
| :--- | :--- |
| `json`（默认）| `<pre>JSON.stringify</pre>` |
| `tabs` | 多标签页，每个 tab 按 `format` 渲染 |

### 6.2 详情 `format` 清单

| `format` 值 | 渲染组件 | 适用场景 |
| :--- | :--- | :--- |
| `markdown` | `ReactMarkdown` + `remark-gfm` | review 审查意见、分析摘要文本 |
| `code` | `PrismJS` | 交易策略代码 |
| `json` | JSON Tree Viewer | 原始数据探查 |
| `diff` | Monaco Diff Editor | 两个截面的差异对比（预留） |
| `chart_timeseries` | Lightweight Charts | 净值曲线、xG 走势（预留） |
| `agent_trace` | 自定义 Agent 思考链组件 | Agent 节点日志（预留） |

### 6.3 Goalcast 详情配置示例（matches tab）

```json
{
  "source": {
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
}
```

---

## 7. 动作协议（Actions Protocol）（预留）

Goalcast 当前暂不启用 Action 引擎。未来可以配置以下典型动作：

| label | kind | 说明 |
| :--- | :--- | :--- |
| 助手解读 | `inject_chat` | 将比赛数据注入 Chat 面板 |
| 重新分析 | `api_call` | 触发对指定比赛的重新分析 |

---

## 8. 类型定义（TypeScript）

实现见 [frontend/src/types/index.ts](../../../frontend/src/types/index.ts)

```typescript
// ── Source ──────────────────────────────────────────────────

type BoardTabProvider = "default" | "rest" | "streaming" | "analytical" | "langgraph";

interface BoardTabEndpoints {
  list: string;
  detail: string;
  history?: string;
  export?: string;
}

interface BoardTabSource {
  provider: BoardTabProvider;
  id_field: string;
  endpoints?: BoardTabEndpoints;
  list_response?: {
    items?: string;
    total?: string;
    page?: string;
    page_size?: string;
  };
  detail?: BoardTabDetail;
}

// ── Detail ──────────────────────────────────────────────────

type DetailMode = "json" | "tabs";
type DetailFormat = "markdown" | "code" | "json" | "diff" | "chart_timeseries" | "agent_trace";

interface DetailTab {
  label: string;
  field: string;
  format: DetailFormat;
  language?: string;
}

interface BoardTabDetail {
  mode: DetailMode;
  tabs?: DetailTab[];
}

// ── Columns ─────────────────────────────────────────────────

type ColumnRenderer =
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

interface ColumnDef {
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

// ── BoardTab ────────────────────────────────────────────────

interface BoardTab {
  dir: string;
  label: string;
  columns: ColumnDef[];
  source?: BoardTabSource;
}
```

---

## 9. 当前数据覆盖率验证（Goalcast）

基于 2026-05-05 对 `config.json` 和赛事 JSON 文件的逐项验证：

### 9.1 Tab 覆盖

| Tab | 当前模式 | `provider` | 列渲染覆盖 | 详情渲染覆盖 |
| :--- | :--- | :--- | :--- | :--- |
| matches | default | `"default"` | `status_badge` + `date_time` + `text` 全覆盖 | `json` + `markdown` 多 tab 渲染 |

### 9.2 赛事 JSON 数据字段（展开后）

| 字段路径 | 扁平化后 | 说明 |
| :--- | :--- | :--- |
| `metadata.match_id` | `match_id` | 比赛 ID |
| `metadata.home_team` | `home_team` | 主队 |
| `metadata.away_team` | `away_team` | 客队 |
| `metadata.kickoff_time` | `kickoff_time` | 开赛时间 |
| `metadata.league.name` | `league_name` | 联赛名称 |
| `metadata.fixture_id` | `fixture_id` | SportMonks fixture ID |
| `match_id` | `match_id` | 顶层比赛 ID |
| `status` | `status` | 分析状态流转 |
| `analysis` | `analysis` | Analyst 分析结果（xG、概率等） |
| `trading.results` | `trading.results` | Trader 交易执行结果 |
| `review.verdict` | `review.verdict` | Reviewer 审查意见 |
| `review.notes` | `review.notes` | 审查备注 |
| `report_ref` | `report_ref` | 报告文件引用 |

### 9.3 WebSocket 事件

| 事件类型 | 协议映射 | 实现状态 |
| :--- | :--- | :--- |
| `agent_status` | agent 状态面板 | 已实现 `/ws/status` |
| `pipeline_progress` | 可选 poll 覆盖 | 已通过 `/ws/status` 推送 |
| `board_update` | 触发列表刷新 | 已通过 `/ws/status` 推送 |
| `match_result_ready` | 可选 poll 覆盖 | 已通过 `/ws/status` 推送 |

### 9.4 发现的可增强点

1. **metadata 扁平化**：赛事 JSON 的 `home_team`、`away_team`、`kickoff_time` 等字段嵌套在 `metadata` 内，需在 [board.py](../../../backend/server/routes/board.py) 中做 `_flatten_metadata()` 才能被前端 `record[col.key]` 直接访问（已实现）。
2. **`status_map` 已补齐**：Matches Tab 的 `status` 列已配置完整的 pipeline 状态颜色映射。
3. **`report_ref` 引用**：未来可扩展 Reports Tab 以 `.md` 格式展示生成的赛事报告。

---

## 10. 改动清单（分阶段）

### Phase 1：核心协议落地（已完成）

| 文件 | 改动 | 状态 |
| :--- | :--- | :--- |
| [frontend/src/types/index.ts](../../../frontend/src/types/index.ts) | 新增 `BoardTabSource`、`ColumnDef`、`DetailTab` 等类型 | ✅ 已完成 |
| [backend/server/config.json](../../../backend/server/config.json) | 配置 Matches Tab，含 `source`、`columns`、`detail` | ✅ 已完成 |
| [frontend/public/config.json](../../../frontend/public/config.json) | 同步配置 | ✅ 已完成 |
| [backend/server/routes/board.py](../../../backend/server/routes/board.py) | 修复 path 计算，增加 `_flatten_metadata` | ✅ 已完成 |

### Phase 2：渲染引擎（可选项）

| 文件 | 改动 |
| :--- | :--- |
| `frontend/src/components/board/ColumnRenderer.tsx` | 统一列渲染入口 |
| `frontend/src/components/board/DetailRenderer.tsx` | 扩展详情渲染 |

### Phase 3：动作引擎（可选项）

| 文件 | 改动 |
| :--- | :--- |
| `frontend/src/components/board/ActionBar.tsx` | 动作按钮渲染 |
| `frontend/src/services/boardActions.ts` | 动作分发逻辑 |

### 已有依赖

- `react-markdown` + `remark-gfm` — 已在 `package.json`
- `prismjs` — 已在 `package.json`
- `dayjs` — 已在 `package.json`（`relative_time` / `date_time` 渲染器依赖）

---

## 11. 向后兼容

- 不配 `source` 的 Tab 行为与当前完全一致（Provider 自动设为 `"default"`）
- 不配 `render` 的 column 回退为 `"text"`
- 不配 `actions` 的 Tab 不显示任何操作按钮
- 已有的 `type` 字段（`"directory"`）已在解析层映射为 `"rest"`

---

## 12. 数据流示例（Goalcast）

### 12.1 比赛列表（default provider）

```
1. BoardPage 挂载 → 读取 config.board.tabs[0].source
2. provider === "default" → 调用 api.getBoardList("matches", {page, page_size})
3. GET /api/board/matches?page=1&page_size=20 → {items, total, page, page_size}
   - board.py 读取 backend/data/matches/*.json
   - 调用 _flatten_metadata() 将 metadata.* 提升到顶层
   - 注入 _filename 字段
4. 渲染表格：
   - "match_id"      → render: "text"          → 纯文本
   - "home_team"     → render: "text"          → 纯文本
   - "away_team"     → render: "text"          → 纯文本
   - "league_name"   → render: "text"          → 纯文本
   - "kickoff_time"  → render: "date_time"     → "2026-05-04 17:00:00"
   - "status"        → render: "status_badge"  → 彩色徽章（如 "Reported" 蓝色）
5. 用户点击行 → api.getBoardItem("matches", record._filename)
6. 抽屉渲染 → detail.mode === "tabs"
   - "分析摘要" tab → format: "json" → analysis 对象
   - "交易决策" tab → format: "json" → trading.results 对象
   - "质量审查" tab → format: "markdown" → review.verdict 文本
   - "原始数据" tab → format: "json" → 完整 JSON
7. 用户点击"助手解读"按钮 → 注入 Chat Panel
```

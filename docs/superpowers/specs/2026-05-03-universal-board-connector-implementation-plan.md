# Universal Board Connector — 落地开发计划（Goalcast 适配版）

**日期**: 2026-05-05  
**目标**: 在不破坏现有 BoardPage 的前提下，逐步落地 UBCP v1，让 BoardPage 成为 Goalcast 足球量化分析系统的通用比赛观察平台。  
**协议基线**: [2026-05-03-universal-board-connector-protocol.md](file:///Users/zhengningdai/workspace/skyold/Goalcast/docs/superpowers/specs/2026-05-03-universal-board-connector-protocol.md)

---

## 0. 当前基线（已存在能力）

### 0.1 前端

- Board 入口：[BoardPage.tsx](file:///Users/zhengningdai/workspace/skyold/Goalcast/frontend/src/pages/BoardPage.tsx#L66-L353)
- Source 协议（`provider/endpoints/id_field/detail`）：[types/index.ts](file:///Users/zhengningdai/workspace/skyold/Goalcast/frontend/src/types/index.ts#L195-L210)
- 配置加载（静态 `config.json` + `/api/config` merge）：[config.ts](file:///Users/zhengningdai/workspace/skyold/Goalcast/frontend/src/config.ts#L39-L61)
- WS 事件（用于 board_update 刷新）：[server.py](file:///Users/zhengningdai/workspace/skyold/Goalcast/backend/server/server.py#L36-L44)

### 0.2 后端

- default provider：`GET /api/board/{dir}`、`GET /api/board/{dir}/{filename}`：[board.py](file:///Users/zhengningdai/workspace/skyold/Goalcast/backend/server/routes/board.py#L18-L44)
- WS：`/ws/status`：[server.py](file:///Users/zhengningdai/workspace/skyold/Goalcast/backend/server/server.py#L36-L44)

### 0.3 已有 Goalcast 配置

- Matches Tab（default provider），含赛事元数据扁平化：
  - 文件：[config.json](file:///Users/zhengningdai/workspace/skyold/Goalcast/backend/server/config.json#L19-L42)
  - 列：`match_id`、`home_team`、`away_team`、`league_name`、`kickoff_time`、`status`
  - 详情 tabs：分析摘要（json）、交易决策（json）、质量审查（markdown）、原始数据（json）

### 0.4 赛事数据字段映射

Goalcast 赛事 JSON 文件存储在 `backend/data/matches/*.json`，嵌套结构如下：

| 原始路径 | 扁平化后 | 列表可见 |
| :--- | :--- | :--- |
| `metadata.home_team` | `home_team` | ✅ |
| `metadata.away_team` | `away_team` | ✅ |
| `metadata.kickoff_time` | `kickoff_time` | ✅ |
| `metadata.league.name` | `league_name` | ✅ |
| `metadata.fixture_id` | `fixture_id` | ❌ （detail 中可见）|
| `match_id` | `match_id` | ✅ |
| `status` | `status` | ✅ |
| `analysis` | `analysis` | detail tab |
| `trading.results` | `trading.results` | detail tab |
| `review.verdict` | `review.verdict` | detail tab |
| `state` | `state` | detail tab |

---

## 1. 里程碑与 Phase 拆分

### Phase 1：协议"骨架"落地（已完成）

**目标**：前端可以读取新协议字段并兼容旧配置；Provider 只跑通 `default + rest`，修复赛事 JSON 的 metadata 嵌套问题。

已完成的改动：

| 前端文件 | 改动 |
| :--- | :--- |
| `frontend/src/types/index.ts` | 新增 `BoardTabSource`、`BoardTabDetail`、`ColumnDef`、`DetailTab` 等类型 |
| `frontend/src/pages/BoardPage.tsx` | `fetchList` 按 `source.provider` 分流；支持 `detail.mode === "tabs"` 的多 tab 详情渲染 |

| 后端文件 | 改动 |
| :--- | :--- |
| `backend/server/routes/board.py` | 修复 path 计算（`parents[3]` → `parents[2]`）；新增 `_flatten_metadata()` 将 `metadata.*` 提升到顶层 |
| `backend/server/config.json` | 重新配置 Matches Tab，含 `source`、`columns`、`detail` 完整协议 |
| `frontend/public/config.json` | 同步配置 |

交付验收：

- Matches Tab 可以正确显示赛事列表（含主客队、联赛、开赛时间、状态）
- 点击行后 Drawer 可显示详情的多 tab 渲染（分析/交易/审查/原始数据）
- `home_team`、`away_team`、`kickoff_time` 等字段从 metadata 中正确扁平化

---

### Phase 2：列渲染引擎（ColumnRenderer）

**目标**：让 `columns.render` 真正生效，并做到完全回退。

前端改动：

- 新增统一入口 `ColumnRenderer`
  - 文件：`frontend/src/components/board/ColumnRenderer.tsx`
  - BoardPage 渲染表格 cell 改为调用 ColumnRenderer（替换现有 CellRenderer，见 [BoardPage.tsx](file:///Users/zhengningdai/workspace/skyold/Goalcast/frontend/src/pages/BoardPage.tsx#L15-L51)）
- 分 renderer 组件实现（按优先级）
  - `text`（默认）
  - `status_badge`、`direction_badge`
  - `percentage_color`、`number_precision`
  - `relative_time`、`date_time`
  - `heatmap`（可后置）

交付验收：

- 未配置 `render` 的列保持旧表现
- 配置了 `render` 的列具备可读性提升且无报错

---

### Phase 3：详情渲染扩展（diff / chart_timeseries）

**目标**：扩展 detail.tabs 的 format 能力，且不引入强依赖绑定。

前端改动：

- 新增 `DetailRenderer`（替换 BoardPage 内部 detail 渲染分支）
  - `markdown`/`code`/`json`：迁移现有能力
  - `diff`：对比分析前后版本
  - `chart_timeseries`：xG 走势图（需要确认是否引入 lightweight-charts）

后端改动（按需）：

- 为现有 detail 返回补齐 `diff/chart` 字段（如果要演示能力）

交付验收：

- 在 matches tab 上不回归（现有 markdown/json 仍正常）
- 新 format 出错时可以回退到 json（不影响页面）

---

### Phase 4：Actions 引擎（ActionBar + 执行器）

**目标**：把"可操作截面"从硬编码按钮升级为协议驱动。

Goalcast 的典型 Action：

| label | kind | 说明 |
| :--- | :--- | :--- |
| 助手解读 | `inject_chat` | 将比赛数据注入 Chat 面板（已实现） |
| 重新分析 | `api_call` | 触发对指定比赛的重新分析（需后端 `/api/pipelines/start` 支持） |

前端改动：

- 新增 `ActionBar`（根据 `actions` 渲染按钮，含 condition/scope）
- 新增 action 执行器
  - `inject_chat`：复用现有逻辑（见 [BoardPage.tsx](file:///Users/zhengningdai/workspace/skyold/Goalcast/frontend/src/pages/BoardPage.tsx#L218-L232)）
  - `api_call`：用现有 `api.request` 风格调用
- 二次确认：`require_confirm=true` 弹框确认

后端改动（建议项）：

- 可选：增加 API 路由用于重新分析比赛

交付验收：

- 不配置 actions 时页面无变化
- 配置 actions 后可触发 `inject_chat` 与 `api_call`

---

### Phase 5：Streaming Provider（WebSocket board topic）（可选项）

**目标**：让实时比赛推送通过 WebSocket 实现无刷新更新。

后端改动：

- 新增 `WS /ws/board/{topic}`，支持：
  - 连接建立与断线处理
  - 服务端推送消息：`{type:"upsert"|"append", payload:{...}}`

前端改动：

- 新增 `StreamingProvider`：维护 buffer、支持 `upsert/append_only`、断线状态展示

---

### Phase 6：Reports Tab（可选项）

**目标**：在 Board 中新增 Reports Tab，展示生成的 `.md` 赛事报告。

后端改动：

- 扩展 board.py 支持 `.md` 文件的扫描（当前仅 `.json`）
- 或新增 reports 专用路由 `/api/board/reports`

前端改动：

- 在 config 中新增 reports tab 配置
- detail 使用 `format: "markdown"` 展示报告全文

---

## 2. 配置迁移策略

- 兼容期：支持 `source.provider` 字段，无 source 的 Tab 自动使用 default provider
- 收敛期：Goalcast 当前仅一个 Matches Tab，使用 default provider
- 退出期：无旧字段需要迁移

---

## 3. 质量与验证清单（贯穿所有 Phase）

- 配置容错：错误配置必须"可见地失败"（UI 给出提示），避免静默空列表
- 回退规则：render/format 任一不支持时必须降级为 text/json
- URL 安全：严禁配置 `/api/...` 前缀；模板替换必须做 URL 编码
- 性能边界：default provider 明确仅适用于小目录（Goalcast 赛事文件数通常 < 50）

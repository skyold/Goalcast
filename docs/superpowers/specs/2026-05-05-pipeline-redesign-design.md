# Pipeline 页面重构 — 设计规范

**日期**: 2026-05-05  
**状态**: 设计中  
**目标**: 让 Pipeline 页面成为比赛分析的主入口 — 选择联赛、筛选日期、查看比赛分析结果，并通过 WebSocket 实时跟踪分析进度。

---

## 1. 问题背景

当前 `PipelineMonitor.tsx` 存在以下问题：

1. **无联赛选择** — 只有被动显示当前激活的联赛，用户无法自行增删
2. **数据仅在 push 时有** — 依赖 WebSocket 事件，刷新页面后数据全部丢失
3. **比赛卡片是半成品** — 信息密度低，缺少 xG、概率条、EV、信心度等核心输出
4. **无日期筛选** — 默认按照接收到的 push 展示所有比赛，无法按时间范围过滤

---

## 2. 设计目标

1. **联赛管理融入 UI** — 用户可以直接从页面上勾选/取消联赛，即时生效
2. **日期范围选择** — 默认展示未来 3 天的比赛，可自由调整
3. **REST + WebSocket 混合** — 首屏用 REST 拉取全量，WebSocket 做实时增量
4. **完整的分析结果展示** — 表格行内展示 xG、概率条、推荐、信心、EV
5. **未分析比赛的进度感知** — Pending / Analyzing 状态可视化

---

## 3. 架构方案：REST 初始 + WebSocket 增量

```
首屏加载:
  GET /api/pipeline/leagues  → 联赛列表 + 激活状态
  GET /api/pipeline/matches?date_from=&date_to=  → 完整比赛列表
  
实时增量:
  WS /ws/status 事件:
    matches_found    → 新增 pending 比赛到列表
    match_step_start → 更新状态为 analyzing/trading
    match_result_ready → 填充分析结果 (xG, 概率, EV, 推荐)
    match_step_error → 标记为 error

用户操作:
  POST /api/pipeline/leagues  → 写入 active_leagues.json → 返回新状态
  POST /api/pipeline/trigger  → 写入 trigger.json → orchestrator 立即拉取
```

---

## 4. 后端 API 设计

### 新增路由文件: `backend/server/routes/pipeline.py`

#### 4.1 GET /api/pipeline/leagues

读取 `config/sportmonks_leagues.json` + `data/active_leagues.json`，返回合并后的联赛列表。

```json
{
  "available": [
    { "id": 8,   "chinese_name": "英超", "name": "Premier League", "active": true  },
    { "id": 564, "chinese_name": "西甲", "name": "La Liga",        "active": false },
    ...
  ],
  "active_count": 1
}
```

实现要点：
- 读取 `config/sportmonks_leagues.json` 获取全部 30 个联赛
- 读取 `data/active_leagues.json` 获取当前激活的联赛名称列表
- 合并时标记 `active: true/false`
- 按 `chinese_name` 排序

#### 4.2 POST /api/pipeline/leagues

请求体：
```json
{ "leagues": ["英超", "西甲", "意甲"] }
```

后端行为：
1. 调用 `league_config._write(leagues)` 写入 `data/active_leagues.json`
2. 返回 `{ "active": ["英超", "西甲", "意甲"], "message": "已更新活跃联赛" }`

注意：不在此处触发 orchestrator 立即拉取——orchestrator 每小时自取一次新的联赛配置。用户如需立即拉取，使用单独的 trigger 端点。

#### 4.3 POST /api/pipeline/trigger

无请求体。行为：
1. 在 `data/` 目录下创建空文件 `trigger.json`
2. orchestrator loop 检测到该文件存在时，跳过正常 3600s 的睡眠，立即执行下一轮 `_fetch_and_prepare`
3. 拉取完成 → orchestrator 删除 `trigger.json` → 恢复 3600s 周期

返回 `{ "message": "已触发比赛拉取" }`。

#### 4.4 GET /api/pipeline/matches

聚合 `data/matches/*.json`，展开关键分析字段。支持 query 参数：

| 参数 | 类型 | 默认 | 说明 |
| :--- | :--- | :--- | :--- |
| `date_from` | string | 今天 | YYYY-MM-DD |
| `date_to` | string | 今天+3天 | YYYY-MM-DD |

响应示例：
```json
{
  "items": [
    {
      "match_id": "MC-20260503-190011-ADD85761",
      "home_team": "Chelsea",
      "away_team": "Nottingham Forest",
      "league_name": "Premier League",
      "kickoff_time": "2026-05-04 14:00:00",
      "status": "reported",
      "state": { "analyst": "done", "trader": "done", "reviewer": "done", "reporter": "done" },
      "home_xg": 1.63,
      "away_xg": 1.23,
      "total_xg": 2.86,
      "result_probs": { "home_win": 0.476, "draw": 0.243, "away_win": 0.282 },
      "ev": 0.081,
      "recommendation": "Home -0.75",
      "confidence": 0.72,
      "verdict": "approved"
    }
  ],
  "total": 5,
  "date_range": { "from": "2026-05-05", "to": "2026-05-08" }
}
```

实现要点：
- 扫描 `data/matches/*.json`，读 `metadata.kickoff_time` 做日期过滤
- 提取 `metadata` 的 `home_team` / `away_team` / `league_name` / `kickoff_time`
- 提取 `state` 的 agent 进度
- 如果 `analysis` 存在 → 提取 `home_xg`, `away_xg`, `total_xg`, `result_probs`, `confidence`, `recommendation`
- 如果 `trading` 存在 → 提取 `ev`
- 如果 `review` 存在 → 提取 `verdict`
- 按 `kickoff_time` 排序
- 已分析完成的比赛保留完整字段；未完成的（status=pending/analyzing）字段为 null

---

## 5. Orchestrator 改造

### 5.1 日期范围扩展

当前 `_resolve_date_range` 只拉取今天+明天（2天）：

```python
# orchestrator.py L282-289 - 当前
return [today, tomorrow]  # 2 天

# 改为
return [today, tomorrow, day_after_tomorrow]  # 3 天
```

### 5.2 Trigger 文件检测

在 `_orchestrator_loop` 中新增 trigger 检测逻辑：

```python
# orchestrator.py _orchestrator_loop 中
trigger_file = Path("data/trigger.json")
while not self.stop_event.is_set():
    active_leagues = lc.get_active()
    ...
    fetched = await self._fetch_and_prepare(active_leagues, date, models=models)
    
    # 拉取完成，清除 trigger
    if trigger_file.exists():
        trigger_file.unlink()
    
    # 正常等待 3600s；有 trigger 则等 5s
    sleep_time = 5 if trigger_file.exists() else fetch_interval
    await asyncio.wait_for(self.stop_event.wait(), timeout=sleep_time)
```

### 5.3 已存在比赛的更新

Orchestrator 通过 `_load_existing_fixture_ids()` 跳过已存在的 fixture_id。当 trigger 触发时，应该**更新**已存在比赛的数据而非跳过。改动方案：

- 正常 3600s 循环：跳过已存在 fixture，不重复创建
- 收到 trigger 时：不跳过，覆盖更新已有比赛的 `raw_data`（通过 `merge_update` 或直接重写）

可通过 `trigger.json` 的内容来区分行为（空文件=不更新已有；含 `{"force": true}` = 强制覆盖）：

```python
trigger_force = False
if trigger_file.exists():
    try:
        data = json.loads(trigger_file.read_text())
        trigger_force = data.get("force", False)
    except Exception:
        pass

if not trigger_force and fixture_id in existing_fixture_ids:
    skipped += 1
    continue
```

---

## 6. 数据流 & WebSocket 事件映射

### 6.1 首屏加载

```
PipelinePage mount
  → GET /api/pipeline/leagues
  → GET /api/pipeline/matches?date_from=today&date_to=today+3
  → 渲染表格
```

### 6.2 WebSocket 实时更新

复用现有 `/ws/status`，前端 store 的 `handleWsMessage` 处理以下事件：

| WS 事件 | store action | 表格效果 |
| :--- | :--- | :--- |
| `matches_found` | 向 `pipelineMatches` 追加新比赛 | 表格新增行（Pending 状态） |
| `match_step_start` | 更新 `pipelineMatches[id].status` | 行状态变为 Analyzing / Trading |
| `match_result_ready` | 填充 `predictions` / `ev` / `recommendation` | 行显示 xG、概率、EV |
| `match_step_error` | 标记 `status=error` | 行变红，显示错误信息 |
| `pipeline_complete` | 设置 `pipelineStatus = "Completed"` | 顶部状态栏更新 |

### 6.3 REST 刷新

当触发以下操作时，重新调用 `GET /api/pipeline/matches` 刷新表格：
- 联赛变更（POST /api/pipeline/leagues 成功回调）
- 强制刷新（POST /api/pipeline/trigger 成功回调）
- 轮询：每 10s 自动刷新一次（简单可靠，无需改造 WS）

### 6.4 已知缺口：orchestrator 事件不经过 /ws/status

当前 orchestrator 的 `EventEmitter` 仅通过 `/ws/chat` 推送事件，`/ws/status` 只是保持连接而不转发业务事件。因此本节中的 WS 实时增量（`matches_found` 等事件）在 `PipelineMonitor` 页面上暂时不可用。**替代方案**：使用 10s 轮询 `GET /api/pipeline/matches` 作为主要刷新机制，WebSocket 事件做辅助（由 store 的 `handleWsMessage` 处理，一旦 orchestrator 接入 `/ws/status` 即自动生效）。

---

## 7. 前端 UI 布局

```
┌──────────────────────────────────────────────────────────────────┐
│  联赛选择栏                                                        │
│  [●英超] [○西甲] [○德甲] [○意甲] [○法甲] [○荷甲] [○葡超] [▼更多]   │
│                                                                   │
│  激活: 英超   📅 [2026-05-05 → 2026-05-08]  · 5 场比赛  [🔄强制刷新] │
├──────────────────────────────────────────────────────────────────┤
│  比赛表格 (复用 CellRenderer 渲染体系)                               │
│  ┌──────┬────────┬────────┬──────┬────────┬──────┬──────┬────────┐ │
│  │联赛   │主队     │客队    │开赛   │状态     │xG(主:客)│胜率  │推荐/EV  │ │
│  ├──────┼────────┼────────┼──────┼────────┼──────┼──────┼────────┤ │
│  │英超   │Chelsea │Nott'm  │05-04 │Reported│1.6:1.2│▓▓▓░░ │-0.75 +.08│ │
│  │英超   │Everton │ManCity │05-04 │Reported│0.8:2.2│░▓▓▓▓ │-0.5 +.04│ │
│  │英超   │Arsenal │Liverpl │05-07 │Analyzing│  —   │  —   │    —    │ │
│  └──────┴────────┴────────┴──────┴────────┴──────┴──────┴────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

### 7.1 联赛选择栏

- **Tag 多选**：用 `antd Tag.CheckableTag` 渲染 30 个联赛，已激活亮绿色高亮
- 变更后即时调用 `POST /api/pipeline/leagues`
- 默认展示前 8 个常用联赛，其余通过「▼ 更多」展开
- 「强制刷新」按钮调用 `POST /api/pipeline/trigger`，按钮进入 loading 态直到 WS 返回 `pipeline_complete`

### 7.2 日期选择器

- 两个 `<input type="date">` 或 `antd DatePicker`
- 默认 from=today, to=today+3days
- 变更后重新调用 `GET /api/pipeline/matches?date_from=&date_to=` 刷新表格

### 7.3 比赛表格

| 列 | key | render | 数据来源 |
| :--- | :--- | :--- | :--- |
| 联赛 | `league_name` | `text` | pipeline matches API |
| 主队 | `home_team` | `text`（加粗） | pipeline matches API |
| 客队 | `away_team` | `text` | pipeline matches API |
| 开赛 | `kickoff_time` | `date_time` | pipeline matches API |
| 状态 | `status` | `status_badge` | 映射到 pipeline 状态颜色 |
| xG (主:客) | — | 自定义（两位小数，xG 高方绿色） | 已有分析时渲染，否则 `—` |
| 胜率 | `result_probs` | 自定义（概率条） | 三段色条 (绿/灰/蓝) |
| 推荐 / EV | — | 自定义 | `rec-badge` + 绿/黄/红 EV 数字 |

- status 的映射：`pending`→灰色, `analyzing`→绿色动画, `trading`→橙色动画, `reviewed`→绿色, `reported`→蓝色, `error`→红色
- 未分析完成的行：xG、胜率、推荐、EV 列显示 `—`
- 点击行 → 弹出 Drawer，用已有 `DetailTabRenderer` 渲染 analysis / trading / review 的详情 tabs

---

## 8. 改动清单

### 后端

| 文件 | 改动 | 优先级 |
| :--- | :--- | :--- |
| `backend/server/routes/pipeline.py` | **新建** — 4 个 REST 端点 (leagues CRUD, trigger, matches list) | P0 |
| `backend/server/server.py` | 注册 pipeline router | P0 |
| `backend/agents/core/orchestrator.py` | 日期范围 2→3 天；trigger.json 检测；强制更新逻辑 | P1 |
| `backend/server/routes/config.py` | 无需改动（config.json 的 board tabs 不受影响） | — |

### 前端

| 文件 | 改动 | 优先级 |
| :--- | :--- | :--- |
| `frontend/src/pages/PipelineMonitor.tsx` | **重写** — 联赛栏、日期选择、REST 表格 | P0 |
| `frontend/src/services/api.ts` | 新增 `getPipelineLeagues`, `updatePipelineLeagues`, `triggerPipeline`, `getPipelineMatches` | P0 |
| `frontend/src/store/appStore.ts` | 无需改动（已有 pipelineMatches, handleWsMessage 处理 matches_found 等事件） | — |
| `frontend/src/types/index.ts` | 新增 `PipelineMatch`, `PipelineLeaguesResponse` 类型 | P1 |

### 不新增依赖

- `antd` Tag, Table, DatePicker — 已安装
- `dayjs` — 已安装
- WebSocket — 浏览器原生 + 已有 `ws.ts` 封装

---

## 9. 向后兼容

- 现有 Dashboard 上的 `DashboardExtras`（Pipeline Status 摘要条）不受影响
- Board 页面的 matches tab 不受影响
- orchestrator 的联赛管理逻辑不变（`active_leagues.json` 仍然是唯一真源）
- 旧的 PipelineMonitor 的 MatchCard 组件将被替换，不影响其他页面

---

## 10. 验收标准

1. 联赛选择：勾选「西甲」后，`active_leagues.json` 同步更新，orchestrator 在 ≤1h 内自动拉取
2. 日期筛选：选择日期范围后表格按 `kickoff_time` 过滤
3. 强制刷新：点击后后台立即拉取，卡片状态实时推进
4. 数据完整性：已分析比赛显示 xG / 概率 / EV / 推荐；未分析比赛显示 `—`
5. 实时更新：WebSocket 事件到达时，对应行状态与数据即时更新
6. 页面刷新后数据不丢失：REST API 重新拉取全量

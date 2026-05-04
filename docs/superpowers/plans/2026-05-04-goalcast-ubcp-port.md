# Goalcast UBCP Port — yclake Frontend Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 yclake 前端全量移植到 Goalcast（含 UBCP BoardPage），品牌适配，新增 PipelineMonitor 扩展页面，后端收敛到 `backend/server/` 并对齐 yclake 的 REST API 结构，删除 `backend/agents/web/`。

**Architecture:** 前端以 yclake 为主——全部 src/ 直接复制，仅微调 6 个文件 + 新增 2 个文件 + 1 个 config.json。后端新建 `backend/server/` 目录（对齐 yclake `quant_system/server/`），迁移并扩展 FastAPI，删除旧 `agents/web/`。Goalcast 独家流水线监控作为扩展页面注入。

**Tech Stack:** React 19 + TypeScript + Vite + antd + zustand + react-router-dom, FastAPI + WebSocket + asyncio

---

### Task 1: 删除 Goalcast 旧前端文件

**Files:**
- Delete: `frontend/src/App.tsx`
- Delete: `frontend/src/App.css`
- Delete: `frontend/src/ws.ts`
- Delete: `frontend/src/main.tsx`
- Delete: `frontend/src/index.css`
- Delete: `frontend/src/assets/` (entire directory)

- [ ] **Step 1: 删除所有不再需要的文件**

```bash
rm -f /Users/zhengningdai/workspace/skyold/Goalcast/frontend/src/App.tsx
rm -f /Users/zhengningdai/workspace/skyold/Goalcast/frontend/src/App.css
rm -f /Users/zhengningdai/workspace/skyold/Goalcast/frontend/src/ws.ts
rm -f /Users/zhengningdai/workspace/skyold/Goalcast/frontend/src/main.tsx
rm -f /Users/zhengningdai/workspace/skyold/Goalcast/frontend/src/index.css
rm -rf /Users/zhengningdai/workspace/skyold/Goalcast/frontend/src/assets/
```

- [ ] **Step 2: 验证文件已删除**

```bash
ls /Users/zhengningdai/workspace/skyold/Goalcast/frontend/src/
```
Expected: src 目录下为空。

- [ ] **Step 3: Commit**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast
git add frontend/src/
git commit -m "chore: remove old Goalcast frontend source files"
```

---

### Task 2: 从 yclake 复制前端 src/ 目录

**Files:**
- Copy: `yclake/frontend/src/` → `Goalcast/frontend/src/` (entire directory)

- [ ] **Step 1: 复制整个 src/ 目录**

```bash
cp -r /Users/zhengningdai/workspace/skyold/yclake/frontend/src/* /Users/zhengningdai/workspace/skyold/Goalcast/frontend/src/
```

- [ ] **Step 2: 验证关键文件存在**

```bash
ls /Users/zhengningdai/workspace/skyold/Goalcast/frontend/src/pages/BoardPage.tsx
ls /Users/zhengningdai/workspace/skyold/Goalcast/frontend/src/pages/DashboardPage.tsx
ls /Users/zhengningdai/workspace/skyold/Goalcast/frontend/src/pages/ChatPanel.tsx
ls /Users/zhengningdai/workspace/skyold/Goalcast/frontend/src/store/appStore.ts
ls /Users/zhengningdai/workspace/skyold/Goalcast/frontend/src/types/index.ts
ls /Users/zhengningdai/workspace/skyold/Goalcast/frontend/src/services/api.ts
```
Expected: 全部文件存在。

- [ ] **Step 3: Commit**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast
git add frontend/src/
git commit -m "feat: copy yclake frontend src/ to Goalcast"
```

---

### Task 3: 替换配置文件（tsconfig、vite、eslint、package.json）

**Files:**
- Overwrite: `Goalcast/frontend/tsconfig.json`
- Overwrite: `Goalcast/frontend/tsconfig.app.json`
- Overwrite: `Goalcast/frontend/tsconfig.node.json`
- Overwrite: `Goalcast/frontend/vite.config.ts`
- Overwrite: `Goalcast/frontend/eslint.config.js`
- Modify: `Goalcast/frontend/package.json`
- Delete: `Goalcast/frontend/Dockerfile`
- Delete: `Goalcast/frontend/nginx.conf`

- [ ] **Step 1: 复制 yclake 的 tsconfig / vite / eslint**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast
cp /Users/zhengningdai/workspace/skyold/yclake/frontend/tsconfig.json frontend/tsconfig.json
cp /Users/zhengningdai/workspace/skyold/yclake/frontend/tsconfig.app.json frontend/tsconfig.app.json
cp /Users/zhengningdai/workspace/skyold/yclake/frontend/tsconfig.node.json frontend/tsconfig.node.json
cp /Users/zhengningdai/workspace/skyold/yclake/frontend/vite.config.ts frontend/vite.config.ts
cp /Users/zhengningdai/workspace/skyold/yclake/frontend/eslint.config.js frontend/eslint.config.js
```

- [ ] **Step 2: 删除前端专属的 Docker/nginx（Goalcast 用后端 Docker）**

```bash
rm -f /Users/zhengningdai/workspace/skyold/Goalcast/frontend/Dockerfile
rm -f /Users/zhengningdai/workspace/skyold/Goalcast/frontend/nginx.conf
```

- [ ] **Step 3: 用 yclake 的 package.json 替换，追加 lucide-react**

```bash
cp /Users/zhengningdai/workspace/skyold/yclake/frontend/package.json /Users/zhengningdai/workspace/skyold/Goalcast/frontend/package.json
```

Then edit to add `"lucide-react": "^1.14.0"` to dependencies.

- [ ] **Step 4: 复制 yclake 的测试文件**

```bash
cp -r /Users/zhengningdai/workspace/skyold/yclake/frontend/tests /Users/zhengningdai/workspace/skyold/Goalcast/frontend/tests
```

- [ ] **Step 5: 安装依赖并验证 dev server 可启动**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast/frontend
npm install
npx vite --port 5174 &
sleep 3
curl -s http://localhost:5174 | head -5
kill %1 2>/dev/null
```
Expected: `curl` 返回 HTML 内容。

- [ ] **Step 6: Commit**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast
git add frontend/
git commit -m "feat: replace frontend configs with yclake versions, add lucide-react"
```

---

### Task 4: SideNav + AppLayout 品牌名修改

**Files:**
- Modify: `Goalcast/frontend/src/components/SideNav.tsx`
- Modify: `Goalcast/frontend/src/layouts/AppLayout.tsx`

- [ ] **Step 1: 修改 SideNav.tsx — 添加 Pipeline 导航项**

In `ALL_NAV_ITEMS` array, after the board item (line ~31), insert:

```tsx
  {
    key: "pipeline",
    path: "/pipeline",
    label: "Pipeline",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
      </svg>
    ),
  },
```

Also update the `navItems` filter to allow `pipeline` key:

```tsx
const navItems = ALL_NAV_ITEMS.filter(
  (item) => item.key === "pipeline" || config.modules[item.key as keyof typeof config.modules] !== false
);
```

- [ ] **Step 2: 修改 AppLayout.tsx — 品牌名**

```tsx
// 品牌名
<span style={{ fontSize: 13, fontWeight: 700, color: "var(--accent)", letterSpacing: "0.08em" }}>
  Goalcast
</span>
// 副标题
<span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>
  Orchestrator
</span>
```

- [ ] **Step 3: 验证编译通过**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast/frontend
npx tsc --noEmit
```
Expected: 允许有类型错误（后续步骤修），无语法错误即可。

- [ ] **Step 4: Commit**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast
git add frontend/src/components/SideNav.tsx frontend/src/layouts/AppLayout.tsx
git commit -m "feat: rebrand to Goalcast, add Pipeline nav item"
```

---

### Task 5: App.tsx 路由调整 + public/config.json

**Files:**
- Modify: `Goalcast/frontend/src/App.tsx`
- Overwrite: `Goalcast/frontend/public/config.json`

- [ ] **Step 1: 修改 App.tsx**

- Remove `import HypothesisPage from "./extensions/HypothesisPage"`
- Remove `<Route path="/hypothesis" element={<HypothesisPage />} />`
- Add `import PipelineMonitor from "./pages/PipelineMonitor"`
- Add `<Route path="/pipeline" element={<PipelineMonitor />} />`
- Change `colorPrimary` from `#ff9500` to `#00FF9D` (Goalcast green)

- [ ] **Step 2: 写入 Goalcast 版 public/config.json**

```json
{
  "app": { "name": "Goalcast", "subtitle": "Football Quant System" },
  "modules": { "agents": true, "board": true, "tokens": true, "chat": true, "logs": true },
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

- [ ] **Step 3: Commit**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast
git add frontend/src/App.tsx frontend/public/config.json
git commit -m "feat: update routes for Goalcast, add Goalcast config.json"
```

---

### Task 6: DashboardPage.tsx 添加 DashboardExtras 渲染点

**Files:**
- Modify: `Goalcast/frontend/src/pages/DashboardPage.tsx`

- [ ] **Step 1: 添加 import 和渲染点**

At top of file, add: `import DashboardExtras from "../extensions/DashboardExtras";`

After `<AlertBar/>` (approximately line 266), insert:

```tsx
<DashboardExtras />
```

- [ ] **Step 2: Commit**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast
git add frontend/src/pages/DashboardPage.tsx
git commit -m "feat: add DashboardExtras render point to DashboardPage"
```

---

### Task 7: 新建 PipelineMonitor.tsx 页面

**Files:**
- Create: `Goalcast/frontend/src/pages/PipelineMonitor.tsx`

- [ ] **Step 1: 创建 PipelineMonitor.tsx**

Full component that renders a pipeline monitoring page with:
- Header bar showing Pipeline Status tag, active leagues, WS connection indicator
- Match card grid (antd `Card`, 3-col responsive) driven by `useAppStore.pipelineMatches`
- Each card shows: match ID, teams, status icon, progress bar / predictions bar / error
- Empty state when `pipelineMatches` is empty

(Full code provided inline in plan — uses antd `Card`, `Tag`, `Progress`, `Empty`, `@ant-design/icons`)

- [ ] **Step 2: Commit**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast
git add frontend/src/pages/PipelineMonitor.tsx
git commit -m "feat: add PipelineMonitor page for Goalcast"
```

---

### Task 8: 扩展 appStore 支持 Goalcast 事件

**Files:**
- Modify: `Goalcast/frontend/src/store/appStore.ts`

- [ ] **Step 1: 追加 MatchCard 接口和 AppState 字段**

After existing interfaces, add:
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
```

In `AppState` interface, append:
```ts
pipelineMatches: Record<string, MatchCard>;
pipelineStatus: string;
activeLeagues: string[];
```

In initial state, add:
```ts
pipelineMatches: {},
pipelineStatus: "Idle",
activeLeagues: [],
```

- [ ] **Step 2: 在 handleWsMessage switch 中追加 Goalcast 事件处理**

Before `default:`, add cases for: `pipeline_start`, `matches_found`, `match_step_start`, `match_result_ready`, `match_step_error`, `pipeline_complete`.

Each event updates `pipelineMatches`, `pipelineStatus`, or `activeLeagues` via `set()`.

- [ ] **Step 3: 验证编译 0 errors**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast/frontend
npx tsc --noEmit 2>&1 | grep -c "error"
```

- [ ] **Step 4: Commit**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast
git add frontend/src/store/appStore.ts
git commit -m "feat: extend appStore with Goalcast pipeline events and state"
```

---

### Task 9: 重写 DashboardExtras.tsx

**Files:**
- Overwrite: `Goalcast/frontend/src/extensions/DashboardExtras.tsx`

- [ ] **Step 1: 重写为 Goalcast Pipeline 状态摘要**

Replace yclake's "Cluster Controls" with a component that reads `pipelineStatus`, `pipelineMatches`, and `activeLeagues` from `useAppStore` and renders a compact status bar with: Pipeline status Tag, active leagues, and match progress (doneCount/total, errorCount).

- [ ] **Step 2: Commit**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast
git add frontend/src/extensions/DashboardExtras.tsx
git commit -m "feat: rewrite DashboardExtras for Goalcast pipeline status summary"
```

---

### Task 10: 删除旧 `backend/agents/web/` 并创建 `backend/server/` 目录结构

**Files:**
- Delete: `Goalcast/backend/agents/web/` (entire directory)
- Create: `Goalcast/backend/server/__init__.py`
- Create: `Goalcast/backend/server/routes/__init__.py`
- Create: `Goalcast/backend/server/ws/__init__.py`

- [ ] **Step 1: 删除 agents/web/ + 创建 server/ 目录**

```bash
rm -rf /Users/zhengningdai/workspace/skyold/Goalcast/backend/agents/web/
mkdir -p /Users/zhengningdai/workspace/skyold/Goalcast/backend/server/routes
mkdir -p /Users/zhengningdai/workspace/skyold/Goalcast/backend/server/ws
touch /Users/zhengningdai/workspace/skyold/Goalcast/backend/server/__init__.py
touch /Users/zhengningdai/workspace/skyold/Goalcast/backend/server/routes/__init__.py
touch /Users/zhengningdai/workspace/skyold/Goalcast/backend/server/ws/__init__.py
```

- [ ] **Step 2: Commit**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast
git add backend/server/ backend/agents/web/
git commit -m "chore: reorganize web code to backend/server/, delete agents/web/"
```

---

### Task 11: 创建 `server/ws/manager.py`

**Files:**
- Create: `Goalcast/backend/server/ws/manager.py`

- [ ] **Step 1: 创建 WS 连接管理器**

```python
from fastapi import WebSocket
from typing import Any
import json
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self._connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._connections.append(ws)
        logger.info("WebSocket connected (%d total)", len(self._connections))

    def disconnect(self, ws: WebSocket):
        if ws in self._connections:
            self._connections.remove(ws)
            logger.info("WebSocket disconnected (%d remaining)", len(self._connections))

    async def broadcast(self, message: dict[str, Any]):
        dead: list[WebSocket] = []
        data = json.dumps(message)
        for ws in self._connections:
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()
```

- [ ] **Step 2: Commit**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast
git add backend/server/ws/manager.py
git commit -m "feat: add WebSocket ConnectionManager"
```

---

### Task 12: 创建 `server/routes/config.py`

**Files:**
- Create: `Goalcast/backend/server/routes/config.py`

- [ ] **Step 1: 创建 /api/config 路由**

```python
from pathlib import Path
import json
from fastapi import APIRouter

router = APIRouter(prefix="/api/config", tags=["config"])

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"


@router.get("")
async def get_config() -> dict:
    if _CONFIG_PATH.exists():
        try:
            return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "app": {"name": "Goalcast", "subtitle": "Football Quant System"},
        "modules": {"agents": True, "board": True, "tokens": True, "chat": True, "logs": True},
        "agents": {"clusters": []},
        "board": {"tabs": []},
    }
```

- [ ] **Step 2: Commit**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast
git add backend/server/routes/config.py
git commit -m "feat: add /api/config route"
```

---

### Task 13: 创建 `server/routes/board.py`

**Files:**
- Create: `Goalcast/backend/server/routes/board.py`

- [ ] **Step 1: 创建 /api/board 路由**

```python
from pathlib import Path
import json
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api/board", tags=["board"])

_BOARD_BASE = Path(__file__).resolve().parents[3] / "data"


def _safe_subpath(base: Path, *parts: str) -> Path:
    resolved_base = base.resolve()
    candidate = (base / Path(*parts)).resolve()
    if not str(candidate).startswith(str(resolved_base)):
        raise HTTPException(status_code=400, detail="Invalid path: traversal not allowed")
    return candidate


@router.get("/{dir}")
async def get_board_list(
    dir: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict:
    dir_path = _safe_subpath(_BOARD_BASE, dir)
    if not dir_path.exists() or not dir_path.is_dir():
        return {"items": [], "total": 0, "page": page, "page_size": page_size}

    items: list[dict] = []
    for f in sorted(dir_path.glob("*.json")):
        try:
            data: dict = json.loads(f.read_text(encoding="utf-8"))
            data["_filename"] = f.name
            items.append(data)
        except Exception:
            pass

    total = len(items)
    start = (page - 1) * page_size
    return {
        "items": items[start : start + page_size],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{dir}/{filename}")
async def get_board_item(dir: str, filename: str) -> dict:
    file_path = _safe_subpath(_BOARD_BASE, dir, filename)
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail=f"{dir}/{filename} not found")
    try:
        data: dict = json.loads(file_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        raise HTTPException(status_code=500, detail=f"Failed to read {filename}: {e}") from e
    data["_filename"] = file_path.name
    return data
```

- [ ] **Step 2: Commit**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast
git add backend/server/routes/board.py
git commit -m "feat: add /api/board routes"
```

---

### Task 14: 创建 `server/routes/chat.py` + `server/config.json`

**Files:**
- Create: `Goalcast/backend/server/routes/chat.py`
- Create: `Goalcast/backend/server/config.json`

- [ ] **Step 1: 创建 chat.py（POST /api/chat/ + stub endpoints）**

File includes:
- `POST /api/chat/` — placeholder response
- `GET /api/agents/status` — returns `[]`
- `GET /api/pipelines/status` — returns `[]`
- `GET /api/tokens/summary` — returns zeroed summary
- `GET /api/tokens/records` — returns `{items:[], total:0, ...}`
- `GET /api/tokens/agents/{agent_id}` — returns zeroed stats

- [ ] **Step 2: 创建 server/config.json** (Copy of `public/config.json`)

- [ ] **Step 3: Commit**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast
git add backend/server/routes/chat.py backend/server/config.json
git commit -m "feat: add /api/chat + stub endpoints + server config.json"
```

---

### Task 15: 创建 `server/server.py` — FastAPI 入口

**Files:**
- Create: `Goalcast/backend/server/server.py`
- Create: `Goalcast/backend/server/requirements.txt`

- [ ] **Step 1: 创建 server.py**

FastAPI entry point with:
- `/api/health` healthcheck
- `/ws/status` — broadcasts to connected clients (ConnectionManager)
- `/ws/chat` — Goalcast orchestrator chat (migrated from agents/web/server.py, with intent parsing + orchestrator.run())
- CORS middleware for dev (5173, 5174)
- Mounts: config_router, board_router, chat_router

- [ ] **Step 2: 创建 requirements.txt**

```txt
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
websockets>=12.0
python-dotenv>=1.0.0
```

- [ ] **Step 3: 验证 Python 语法**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast
python -c "import ast; ast.parse(open('backend/server/server.py').read()); print('OK')"
```

- [ ] **Step 4: Commit**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast
git add backend/server/server.py backend/server/requirements.txt
git commit -m "feat: add FastAPI entry point with /ws/status and /ws/chat"
```

---

### Task 16: 最终联调验证

- [ ] **Step 1: 前端 TypeScript 编译 0 errors**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast/frontend
npx tsc --noEmit 2>&1 | grep "error" | grep -v "node_modules" | wc -l
```

- [ ] **Step 2: 前端测试通过**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast/frontend
npx vitest run 2>&1 | tail -10
```

- [ ] **Step 3: 后端 server 模块可加载**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast
python -c "
import sys; sys.path.insert(0, 'backend')
from server import server as srv
print('FastAPI app:', srv.app.title)
"
```
Expected: `FastAPI app: Goalcast API`

- [ ] **Step 4: 前端 dev server 可启动**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast/frontend
npx vite --port 5174 &
sleep 3
curl -s http://localhost:5174 | head -3
kill %1 2>/dev/null
```

- [ ] **Step 5: Final commit**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast
git commit -m "chore: final integration verification"
```

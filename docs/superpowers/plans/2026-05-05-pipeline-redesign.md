# Pipeline 页面重构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重构 PipelineMonitor 页面为比赛分析主入口 — 联赛 Tag 多选、日期范围筛选、REST 表格展示完整分析结果，Orchestrator 增加 trigger.json 即时触发和 3 天日期范围。

**Architecture:** 后端新增 `routes/pipeline.py`（4 个 REST 端点），Orchestrator 新增 trigger 文件检测 + 日期扩展。前端 PipelineMonitor 全量重写为联赛栏 + 日期选择器 + REST 表格 + 10s 轮询。store 和 WebSocket 层不改动。

**Tech Stack:** Python/FastAPI (backend), React/TypeScript/antd (frontend), 复用现有 CellRenderer + DetailTabRenderer

---

## File Structure

| 文件 | 职责 |
| :--- | :--- |
| `backend/server/routes/pipeline.py` | **新建** — 4 个端点的 REST 路由：leagues GET/POST、trigger POST、matches GET |
| `backend/server/server.py` | 注册 pipeline router（+4 行） |
| `backend/agents/core/orchestrator.py` | trigger.json 文件检测 + `_resolve_date_range` 2→3天 |
| `frontend/src/types/index.ts` | 新增 `PipelineMatch` 和 `PipelineLeaguesResponse` 类型 |
| `frontend/src/services/api.ts` | 新增 4 个 API 函数 |
| `frontend/src/pages/PipelineMonitor.tsx` | **全量重写** — 联赛栏、日期选择、REST 表格 |

---

### Task 1: 新建 backend/server/routes/pipeline.py

**Files:**
- Create: `backend/server/routes/pipeline.py`

- [ ] **Step 1: 创建文件并实现 4 个端点**

```python
from pathlib import Path
import json
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])

_CST = timezone(timedelta(hours=8))
_MATCHES_DIR = Path(__file__).resolve().parents[2] / "data" / "matches"
_LEAGUES_FILE = Path(__file__).resolve().parents[2] / "config" / "sportmonks_leagues.json"
_ACTIVE_FILE = Path(__file__).resolve().parents[2] / "data" / "active_leagues.json"
_TRIGGER_FILE = Path(__file__).resolve().parents[2] / "data" / "trigger.json"


def _read_active_leagues() -> list[str]:
    if not _ACTIVE_FILE.exists():
        return []
    try:
        data = json.loads(_ACTIVE_FILE.read_text(encoding="utf-8"))
        return data.get("leagues", [])
    except Exception:
        return []


@router.get("/leagues")
async def get_leagues() -> dict:
    active = _read_active_leagues()
    active_set = set(active)
    available = []
    if _LEAGUES_FILE.exists():
        try:
            all_leagues = json.loads(_LEAGUES_FILE.read_text(encoding="utf-8"))
            seen = set()
            for lid, info in all_leagues.items():
                cn = info.get("chinese_name", info.get("name", ""))
                key = (cn, info.get("id"))
                if key in seen:
                    continue
                seen.add(key)
                available.append({
                    "id": info.get("id"),
                    "chinese_name": cn,
                    "name": info.get("name", ""),
                    "active": cn in active_set,
                })
        except Exception:
            pass
    available.sort(key=lambda x: x["chinese_name"])
    return {"available": available, "active_count": len(active)}


@router.post("/leagues")
async def update_leagues(body: dict) -> dict:
    leagues = body.get("leagues", [])
    if not isinstance(leagues, list):
        leagues = []
    _ACTIVE_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "leagues": leagues,
        "updated_at": datetime.now(_CST).isoformat(),
    }
    _ACTIVE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"active": leagues, "message": "已更新活跃联赛"}


@router.post("/trigger")
async def trigger_pipeline(body: dict = None) -> dict:
    _TRIGGER_FILE.parent.mkdir(parents=True, exist_ok=True)
    force = False
    if body and body.get("force"):
        force = True
    payload = {"force": force}
    _TRIGGER_FILE.write_text(json.dumps(payload), encoding="utf-8")
    return {"message": "已触发比赛拉取"}


@router.get("/matches")
async def get_matches(
    date_from: str = Query(default=None),
    date_to: str = Query(default=None),
) -> dict:
    now = datetime.now(_CST)
    if not date_from:
        date_from = now.strftime("%Y-%m-%d")
    if not date_to:
        date_to = (now + timedelta(days=3)).strftime("%Y-%m-%d")

    items = []
    if _MATCHES_DIR.exists():
        for fp in sorted(_MATCHES_DIR.glob("*.json")):
            try:
                record = json.loads(fp.read_text(encoding="utf-8"))
            except Exception:
                continue
            md = record.get("metadata", {})
            if isinstance(md, dict):
                league = md.get("league", {})
                league_name = league.get("name", "") if isinstance(league, dict) else str(league) if league else ""
                home_team = md.get("home_team", "")
                away_team = md.get("away_team", "")
                kickoff_time = md.get("kickoff_time", "")
            else:
                league_name = ""
                home_team = ""
                away_team = ""
                kickoff_time = ""
            status = record.get("status", "unknown")
            state = record.get("state", {})
            analysis = record.get("analysis", {}) or {}
            trading = record.get("trading", {}) or {}
            review = record.get("review", {}) or {}

            kt_str = str(kickoff_time) if kickoff_time else ""
            if kt_str:
                kt_date = kt_str[:10]
                if kt_date < date_from or kt_date > date_to:
                    continue

            item = {
                "match_id": record.get("match_id", fp.stem),
                "home_team": home_team,
                "away_team": away_team,
                "league_name": league_name,
                "kickoff_time": kt_str,
                "status": status,
                "state": state,
            }
            if isinstance(analysis, dict) and analysis:
                item["home_xg"] = analysis.get("home_xg")
                item["away_xg"] = analysis.get("away_xg")
                item["total_xg"] = analysis.get("total_xg")
                item["result_probs"] = analysis.get("fulltime_result_probabilities")
                item["confidence"] = analysis.get("confidence")
                item["recommendation"] = analysis.get("ah_recommendation")
            if isinstance(trading, dict) and trading:
                item["ev"] = trading.get("ev", trading.get("results", {}).get("ev") if isinstance(trading.get("results"), dict) else None)
            if isinstance(review, dict) and review:
                item["verdict"] = review.get("verdict")
            items.append(item)

    items.sort(key=lambda x: x.get("kickoff_time", ""))
    return {
        "items": items,
        "total": len(items),
        "date_range": {"from": date_from, "to": date_to},
    }
```

- [ ] **Step 2: 验证文件语法正确**

Run: `cd /Users/zhengningdai/workspace/skyold/Goalcast && python3 -c "import sys; sys.path.insert(0, 'backend'); from server.routes import pipeline; print('OK')"`

Expected: `OK`

---

### Task 2: 注册 pipeline router 到 server.py

**Files:**
- Modify: `backend/server/server.py:23-28`

- [ ] **Step 1: 添加 router 导入和注册**

将第 23-28 行的导入和注册代码改为：

```python
from .routes.config import router as config_router
from .routes.board import router as board_router
from .routes.chat import router as chat_router
from .routes.agents import router as agents_router
from .routes.pipeline import router as pipeline_router

app.include_router(config_router)
app.include_router(board_router)
app.include_router(chat_router)
app.include_router(agents_router)
app.include_router(pipeline_router)
```

- [ ] **Step 2: 验证路由注册**

Run: `cd /Users/zhengningdai/workspace/skyold/Goalcast && python3 -c "import sys; sys.path.insert(0, 'backend'); from server.server import app; routes = [r.path for r in app.routes]; print('pipeline/leagues' if any('pipeline/leagues' in p for p in routes) else 'MISSING')"`

Expected: `pipeline/leagues`

---

### Task 3: Orchestrator 改造 — 日期范围扩展 + trigger 检测

**Files:**
- Modify: `backend/agents/core/orchestrator.py:22-25`
- Modify: `backend/agents/core/orchestrator.py:90-116`
- Modify: `backend/agents/core/orchestrator.py:158-167`
- Modify: `backend/agents/core/orchestrator.py:282-289`

- [ ] **Step 1: 在文件顶部增加 trigger 文件路径常量**

在第 24-25 行之后添加：

```python
TRIGGER_FILE = Path(__file__).parent.parent.parent / "data" / "trigger.json"
```

- [ ] **Step 2: 修改 _resolve_date_range 从 2 天扩展到 3 天**

将第 282-289 行改为：

```python
    def _resolve_date_range(self, date: str | None) -> list[str]:
        if date:
            return [date]
        tz = _CST
        now = datetime.now(tz)
        today = now.strftime("%Y-%m-%d")
        tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")
        day_after = (now + timedelta(days=2)).strftime("%Y-%m-%d")
        return [today, tomorrow, day_after]
```

- [ ] **Step 3: 在 _orchestrator_loop 中添加 trigger 检测逻辑**

将第 97-116 行改为：

```python
    async def _orchestrator_loop(
        self,
        leagues: list[str] | None,
        date: str | None,
        models: list[str] | None,
        fetch_interval: int,
    ) -> None:
        while not self.stop_event.is_set():
            active_leagues = lc.get_active()
            if not active_leagues:
                print("[Orchestrator] 当前无活跃联赛，跳过拉取（使用 leagues add <联赛名> 添加）")
                try:
                    await asyncio.wait_for(self.stop_event.wait(), timeout=fetch_interval)
                except asyncio.TimeoutError:
                    pass
                continue
            print(f"[Orchestrator] 正在拉取比赛数据... 当前联赛: {active_leagues}")
            fetched = await self._fetch_and_prepare(active_leagues, date, models=models)
            print(f"[Orchestrator] 已准备 {fetched} 场比赛")

            # 清除 trigger
            if TRIGGER_FILE.exists():
                TRIGGER_FILE.unlink()
                print("[Orchestrator] Trigger 完成，恢复 3600s 等待")

            if self.stop_event.is_set():
                break

            try:
                await asyncio.wait_for(self.stop_event.wait(), timeout=fetch_interval)
            except asyncio.TimeoutError:
                pass
```

- [ ] **Step 4: 在 _fetch_and_prepare 中添加 trigger 强制更新逻辑**

在第 158-167 行的 fixture 跳过逻辑处添加 trigger_force 判断（`_fetch_and_prepare` 方法中）：

将：

```python
        existing_fixture_ids = self._load_existing_fixture_ids()
        skipped = 0
        for fixture in fixtures:
            fixture_id = fixture.get("fixture_id", fixture.get("id"))
            if fixture_id in existing_fixture_ids:
                skipped += 1
                continue
```

改为：

```python
        trigger_force = False
        if TRIGGER_FILE.exists():
            try:
                tdata = json.loads(TRIGGER_FILE.read_text(encoding="utf-8"))
                trigger_force = tdata.get("force", False)
            except Exception:
                pass

        existing_fixture_ids = self._load_existing_fixture_ids()
        skipped = 0
        for fixture in fixtures:
            fixture_id = fixture.get("fixture_id", fixture.get("id"))
            if not trigger_force and fixture_id in existing_fixture_ids:
                skipped += 1
                continue
```

- [ ] **Step 5: 验证语法**

Run: `cd /Users/zhengningdai/workspace/skyold/Goalcast && python3 -c "import sys; sys.path.insert(0, 'backend'); from agents.core import orchestrator; print('OK')"`

Expected: `OK`

---

### Task 4: 新增前端类型定义

**Files:**
- Modify: `frontend/src/types/index.ts:245-end`

- [ ] **Step 1: 添加类型定义到 index.ts 末尾（第 251 行之前）**

```typescript
export interface PipelineLeague {
  id: number;
  chinese_name: string;
  name: string;
  active: boolean;
}

export interface PipelineLeaguesResponse {
  available: PipelineLeague[];
  active_count: number;
}

export interface PipelineMatch {
  match_id: string;
  home_team: string;
  away_team: string;
  league_name: string;
  kickoff_time: string;
  status: string;
  state: Record<string, string>;
  home_xg?: number;
  away_xg?: number;
  total_xg?: number;
  result_probs?: { home_win: number; draw: number; away_win: number };
  ev?: number;
  recommendation?: Record<string, unknown> | string;
  confidence?: number;
  verdict?: string;
}

export interface PipelineMatchesResponse {
  items: PipelineMatch[];
  total: number;
  date_range: { from: string; to: string };
}
```

---

### Task 5: 新增前端 API 函数

**Files:**
- Modify: `frontend/src/services/api.ts:1-18` (imports)
- Modify: `frontend/src/services/api.ts:130-end` (add new functions)

- [ ] **Step 1: 在 import 声明中追加新类型**

在 `api.ts` 第 1-17 行的 import 语句末尾添加：

```typescript
import type {
  ...
  JsonRecord,
  PipelineLeaguesResponse,
  PipelineMatchesResponse,
} from "../types";
```

- [ ] **Step 2: 在 api object 末尾（第 130 行之前）追加 4 个新方法**

在 `getBoardItemCustom` 方法之后、`};` 之前添加：

```typescript
  getPipelineLeagues: () => request<PipelineLeaguesResponse>("/pipeline/leagues"),

  updatePipelineLeagues: (leagues: string[]) =>
    request<{ active: string[]; message: string }>("/pipeline/leagues", {
      method: "POST",
      body: JSON.stringify({ leagues }),
    }),

  triggerPipeline: () =>
    request<{ message: string }>("/pipeline/trigger", {
      method: "POST",
      body: JSON.stringify({ force: true }),
    }),

  getPipelineMatches: (params?: { date_from?: string; date_to?: string }) => {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return request<PipelineMatchesResponse>(`/pipeline/matches${qs}`);
  },
```

---

### Task 6: 重写 PipelineMonitor.tsx

**Files:**
- Rewrite: `frontend/src/pages/PipelineMonitor.tsx`

- [ ] **Step 1: 写入完整文件**

```tsx
import { useEffect, useState, useCallback } from "react";
import { Tag, Button, Empty, Spin, Drawer, Tabs } from "antd";
import { ReloadOutlined, PlayCircleOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import { useAppStore } from "../store/appStore";
import { api } from "../services/api";
import type { PipelineLeague, PipelineMatch } from "../types";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const POLL_INTERVAL = 10000;

function getStatusColor(status: string): string {
  switch (status) {
    case "pending": return "default";
    case "analyzing": return "processing";
    case "trading": return "orange";
    case "reviewed": return "green";
    case "reported": return "blue";
    case "error": return "red";
    case "rejected": return "red";
    default: return "default";
  }
}

function XGCell({ homeXg, awayXg }: { homeXg?: number; awayXg?: number }) {
  if (homeXg == null || awayXg == null) return <span>—</span>;
  const homeColor = homeXg >= awayXg ? "var(--accent)" : "var(--text-secondary)";
  const awayColor = awayXg > homeXg ? "var(--accent)" : "var(--text-secondary)";
  return (
    <span style={{ fontFamily: "var(--font-mono)", fontSize: 12 }}>
      <span style={{ color: homeColor, fontWeight: 600 }}>{homeXg.toFixed(2)}</span>
      {" : "}
      <span style={{ color: awayColor, fontWeight: 600 }}>{awayXg.toFixed(2)}</span>
    </span>
  );
}

function ProbBar({ probs }: { probs?: { home_win: number; draw: number; away_win: number } }) {
  if (!probs) return <span>—</span>;
  const h = Math.round(probs.home_win * 100);
  const d = Math.round(probs.draw * 100);
  const a = Math.round(probs.away_win * 100);
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <div style={{ display: "flex", height: 8, borderRadius: 2, overflow: "hidden", width: 100, gap: 1 }}>
        <div style={{ flex: h, background: "var(--accent)" }} />
        <div style={{ flex: d, background: "var(--text-muted)" }} />
        <div style={{ flex: a, background: "#3b82f6" }} />
      </div>
      <span style={{ fontSize: 10, fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>
        {h}/{d}/{a}
      </span>
    </div>
  );
}

function RecEVCell({ rec, ev }: { rec?: Record<string, unknown> | string; ev?: number }) {
  const recLabel = typeof rec === "object" && rec
    ? `${(rec as Record<string, unknown>).side ?? ""} ${(rec as Record<string, unknown>).line ?? ""}`.trim()
    : typeof rec === "string" ? rec : "";
  const evColor = ev == null ? "var(--text-muted)" : ev > 0.05 ? "var(--accent)" : ev > 0 ? "var(--orange)" : "var(--red)";
  const evLabel = ev != null ? `${ev >= 0 ? "+" : ""}${ev.toFixed(3)}` : "—";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      {recLabel ? (
        <span style={{ fontSize: 11, padding: "1px 6px", borderRadius: 3, background: "var(--accent-bg)", color: "var(--accent)", border: "1px solid var(--accent-border)", fontFamily: "var(--font-mono)" }}>
          {recLabel}
        </span>
      ) : <span style={{ color: "var(--text-muted)", fontSize: 11 }}>—</span>}
      <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, fontWeight: 600, color: evColor }}>
        {evLabel}
      </span>
    </div>
  );
}

function MatchDetailDrawer({ match, onClose }: { match: PipelineMatch | null; onClose: () => void }) {
  if (!match) return null;
  return (
    <Drawer
      title={`${match.home_team} vs ${match.away_team}`}
      placement="right"
      width={500}
      onClose={onClose}
      open={!!match}
    >
      <pre style={{ background: "#0a0a12", color: "var(--green)", padding: 16, borderRadius: 8, fontSize: 12, overflowX: "auto", whiteSpace: "pre-wrap", border: "1px solid var(--border)" }}>
        {JSON.stringify(match, null, 2)}
      </pre>
    </Drawer>
  );
}

export default function PipelineMonitor() {
  const wsConnected = useAppStore((s) => s.wsConnected);
  const pipelineMatches = useAppStore((s) => s.pipelineMatches);
  const pipelineStatus = useAppStore((s) => s.pipelineStatus);
  const activeLeagues = useAppStore((s) => s.activeLeagues);

  const [leagues, setLeagues] = useState<PipelineLeague[]>([]);
  const [matches, setMatches] = useState<PipelineMatch[]>([]);
  const [loading, setLoading] = useState(false);
  const [triggering, setTriggering] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [selectedMatch, setSelectedMatch] = useState<PipelineMatch | null>(null);

  const today = dayjs().format("YYYY-MM-DD");
  const threeDaysLater = dayjs().add(3, "day").format("YYYY-MM-DD");
  const [dateFrom, setDateFrom] = useState(today);
  const [dateTo, setDateTo] = useState(threeDaysLater);

  const activeLeagueNames = leagues.filter((l) => l.active).map((l) => l.chinese_name);
  const visibleLeagues = expanded ? leagues : leagues.slice(0, 8);

  const fetchLeagues = useCallback(async () => {
    try {
      const res = await api.getPipelineLeagues();
      setLeagues(res.available);
    } catch {}
  }, []);

  const fetchMatches = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.getPipelineMatches({ date_from: dateFrom, date_to: dateTo });
      setMatches(res.items);
    } catch {
      setMatches([]);
    } finally {
      setLoading(false);
    }
  }, [dateFrom, dateTo]);

  useEffect(() => { fetchLeagues(); }, [fetchLeagues]);
  useEffect(() => { fetchMatches(); }, [fetchMatches]);

  // 10s polling for match updates
  useEffect(() => {
    const timer = setInterval(fetchMatches, POLL_INTERVAL);
    return () => clearInterval(timer);
  }, [fetchMatches]);

  const handleLeagueToggle = async (cn: string) => {
    const newActive = activeLeagueNames.includes(cn)
      ? activeLeagueNames.filter((l) => l !== cn)
      : [...activeLeagueNames, cn];
    try {
      await api.updatePipelineLeagues(newActive);
      setLeagues((prev) =>
        prev.map((l) => ({ ...l, active: newActive.includes(l.chinese_name) }))
      );
    } catch {}
  };

  const handleTrigger = async () => {
    setTriggering(true);
    try {
      await api.triggerPipeline();
    } catch {}
    setTimeout(() => setTriggering(false), 2000);
  };

  const handleDateFromChange = (val: string) => {
    setDateFrom(val);
    if (val > dateTo) setDateTo(val);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      {/* League Bar */}
      <div style={{
        background: "var(--card-bg)", border: "1px solid var(--border)",
        borderRadius: "var(--radius-md)", padding: "14px 18px",
      }}>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 12 }}>
          {visibleLeagues.map((l) => (
            <Tag.CheckableTag
              key={l.id}
              checked={l.active}
              onChange={() => handleLeagueToggle(l.chinese_name)}
              style={{
                border: l.active ? "1px solid var(--accent-border)" : "1px solid var(--border)",
                background: l.active ? "var(--accent-bg)" : "var(--nav-bg)",
                color: l.active ? "var(--accent)" : "var(--text-muted)",
                fontSize: 12, fontWeight: 500,
              }}
            >
              {l.chinese_name}
            </Tag.CheckableTag>
          ))}
          {!expanded && leagues.length > 8 && (
            <Tag
              onClick={() => setExpanded(true)}
              style={{ cursor: "pointer", opacity: 0.5, fontSize: 12 }}
            >
              ▼ 更多 ({leagues.length - 8})
            </Tag>
          )}
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 12, color: "var(--text-secondary)" }}>
          <span>激活: <strong style={{ color: "var(--accent)" }}>{activeLeagueNames.join(", ") || "无"}</strong></span>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => handleDateFromChange(e.target.value)}
              style={{
                background: "var(--nav-bg)", border: "1px solid var(--border)", borderRadius: 6,
                color: "var(--text)", padding: "4px 8px", fontSize: 12, fontFamily: "var(--font-mono)",
                outline: "none",
              }}
            />
            <span style={{ color: "var(--text-muted)" }}>→</span>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              style={{
                background: "var(--nav-bg)", border: "1px solid var(--border)", borderRadius: 6,
                color: "var(--text)", padding: "4px 8px", fontSize: 12, fontFamily: "var(--font-mono)",
                outline: "none",
              }}
            />
            <span>· <strong style={{ color: "var(--accent)" }}>{matches.length}</strong> 场比赛</span>
          </div>
          <Button
            size="small"
            icon={<ReloadOutlined spin={triggering} />}
            onClick={handleTrigger}
            loading={triggering}
            style={{ borderColor: "var(--accent-border)", color: "var(--accent)" }}
          >
            强制刷新
          </Button>
        </div>
      </div>

      {/* Pipeline status bar */}
      <div style={{
        display: "flex", alignItems: "center", gap: 6,
        padding: "4px 0", fontSize: 11, color: "var(--text-muted)",
      }}>
        <div style={{
          width: 6, height: 6, borderRadius: "50%",
          background: wsConnected ? "var(--green)" : "#ef4444",
          boxShadow: wsConnected ? "0 0 6px var(--green)" : "none",
        }} />
        <span>{wsConnected ? "Connected" : "Disconnected"}</span>
        {activeLeagues.length > 0 && (
          <span>· <Tag color="processing" style={{ fontSize: 10 }}>{pipelineStatus || "Idle"}</Tag></span>
        )}
      </div>

      {/* Table */}
      {loading && matches.length === 0 ? (
        <Spin style={{ display: "block", margin: "40px auto" }} />
      ) : matches.length === 0 ? (
        <Empty description="暂无比赛数据。请选择联赛后等待 Orchestrator 拉取，或点击强制刷新。" style={{ padding: 40 }} />
      ) : (
        <div style={{
          background: "var(--card-bg)", border: "1px solid var(--border)",
          borderRadius: "var(--radius-md)", overflow: "hidden",
        }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ background: "var(--nav-bg)" }}>
                {["联赛", "主队", "客队", "开赛", "状态", "xG (主:客)", "胜率", "推荐 / EV"].map((h) => (
                  <th key={h} style={{ padding: "8px 14px", textAlign: "left", fontSize: 11, fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", borderBottom: "1px solid var(--border)", whiteSpace: "nowrap" }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {matches.map((m, i) => (
                <tr
                  key={m.match_id}
                  style={{ borderBottom: i < matches.length - 1 ? "1px solid var(--border-subtle)" : "none", cursor: "pointer" }}
                  onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.background = "var(--hover-bg)")}
                  onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.background = "transparent")}
                  onClick={() => setSelectedMatch(m)}
                >
                  <td style={{ padding: "9px 14px", color: "var(--text)" }}>{m.league_name}</td>
                  <td style={{ padding: "9px 14px", color: "var(--text)", fontWeight: 600 }}>{m.home_team}</td>
                  <td style={{ padding: "9px 14px", color: "var(--text-secondary)" }}>{m.away_team}</td>
                  <td style={{ padding: "9px 14px", fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--text-secondary)" }}>
                    {m.kickoff_time ? dayjs(m.kickoff_time).format("MM-DD HH:mm") : "—"}
                  </td>
                  <td style={{ padding: "9px 14px" }}>
                    <Tag color={getStatusColor(m.status)} style={{ fontSize: 10, fontWeight: 600 }}>{m.status}</Tag>
                  </td>
                  <td style={{ padding: "9px 14px" }}>
                    <XGCell homeXg={m.home_xg} awayXg={m.away_xg} />
                  </td>
                  <td style={{ padding: "9px 14px" }}>
                    <ProbBar probs={m.result_probs} />
                  </td>
                  <td style={{ padding: "9px 14px" }}>
                    <RecEVCell rec={m.recommendation} ev={m.ev} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <MatchDetailDrawer match={selectedMatch} onClose={() => setSelectedMatch(null)} />
    </div>
  );
}
```

- [ ] **Step 2: 验证 TypeScript 编译**

Run: `cd /Users/zhengningdai/workspace/skyold/Goalcast/frontend && npx tsc --noEmit 2>&1 | head -20`

Expected: No errors (or only pre-existing errors from other files)

---

### Task 7: 构建 & 部署验证

- [ ] **Step 1: 构建后端镜像并重启**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast
docker build --no-cache -t goalcast/backend:latest -f Dockerfile .
docker compose -f docker/docker-compose.yml up -d --force-recreate backend
sleep 12
```

- [ ] **Step 2: 验证 4 个 API 端点**

```bash
docker exec goalcast-backend python3 -c "
import urllib.request, json

# GET leagues
r = urllib.request.urlopen('http://localhost:8000/api/pipeline/leagues')
d = json.loads(r.read())
print(f'GET leagues: {len(d[\"available\"])} available, {d[\"active_count\"]} active')

# POST leagues
req = urllib.request.Request('http://localhost:8000/api/pipeline/leagues', data=json.dumps({'leagues': ['英超','意甲']}).encode(), headers={'Content-Type': 'application/json'})
r2 = urllib.request.urlopen(req)
print(f'POST leagues: {json.loads(r2.read())[\"message\"]}')

# POST trigger
req3 = urllib.request.Request('http://localhost:8000/api/pipeline/trigger', data=json.dumps({'force': True}).encode(), headers={'Content-Type': 'application/json'})
r3 = urllib.request.urlopen(req3)
print(f'POST trigger: {json.loads(r3.read())[\"message\"]}')

# GET matches
r4 = urllib.request.urlopen('http://localhost:8000/api/pipeline/matches')
d4 = json.loads(r4.read())
print(f'GET matches: {d4[\"total\"]} matches, date_range={d4[\"date_range\"]}')
"
```

Expected: All 4 endpoints return 200 with valid JSON

- [ ] **Step 3: 构建前端镜像并重启**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast
docker build --no-cache -t goalcast/frontend:latest -f frontend/Dockerfile frontend/
docker compose -f docker/docker-compose.yml up -d --force-recreate frontend
sleep 6
```

- [ ] **Step 4: 通过 nginx 验证 API**

```bash
curl -s http://localhost/api/pipeline/leagues | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'OK: {len(d[\"available\"])} leagues')"
curl -s http://localhost/api/pipeline/matches | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'OK: {d[\"total\"]} matches')"
```

Expected: both return OK with valid counts

- [ ] **Step 5: 打开浏览器验证**

Visit `http://localhost/pipeline` and verify:
1. 联赛 Tag 列表显示，英超高亮
2. 日期选择器默认为今天 → 3天后
3. 表格显示已有比赛数据（5 场 reported）
4. 「强制刷新」按钮可点击
5. 点击比赛行弹出 Drawer 显示详情

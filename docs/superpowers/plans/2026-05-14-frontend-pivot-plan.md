# Frontend OddAlert-Only Pivot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 Plan 1 后端 API 就绪的前提下，构建全新浏览优先 UI — 主页 + 详情页 + 跌水/趋势榜 + 联赛/球队/分析/我的/设置共 10+ 页面，移动端响应式，并把旧 agent UI 归档到 `pages/legacy/`。

**Architecture:** React 19 + Ant Design 6（暗色主题，主色 `#00FF9D`）+ react-router-dom 7 + zustand。新 `services/browse.ts` 端点对接 Plan 1 后端；新 `pages/*` 与 `components/*` 按 mockup（`.superpowers/brainstorm/.../content/*.html`）实现；旧重组件移到 `pages/legacy/`。

**Tech Stack:** React 19 · TypeScript 6 · Vite · Ant Design 6 · react-router-dom 7 · zustand · dayjs · vitest + @testing-library/react · lucide-react · @ant-design/icons

**Spec:** `docs/superpowers/specs/2026-05-14-oddalert-only-pivot-design.md`
**Predecessor Plan:** `docs/superpowers/plans/2026-05-14-backend-pivot-plan.md` (must be complete)

---

## File Structure

### Create — Types
- `frontend/src/types/browse.ts`

### Create — Services
- `frontend/src/services/browse.ts`

### Create — Stores
- `frontend/src/store/favorites.ts`

### Create — Components
- `frontend/src/components/LeagueTree.tsx`
- `frontend/src/components/FixtureCard.tsx`
- `frontend/src/components/FixtureDetailDrawer.tsx`
- `frontend/src/components/OddsCurveChart.tsx`
- `frontend/src/components/MarketDepthTable.tsx`
- `frontend/src/components/StatsCompare.tsx`
- `frontend/src/components/H2HTable.tsx`
- `frontend/src/components/AnalysisBadge.tsx`
- `frontend/src/components/MobileTabBar.tsx`

### Create — Pages
- `frontend/src/pages/BettingPage.tsx`
- `frontend/src/pages/FixtureDetailPage.tsx`
- `frontend/src/pages/DroppingOddsPage.tsx`
- `frontend/src/pages/TrendsPage.tsx`
- `frontend/src/pages/LeaguePage.tsx`
- `frontend/src/pages/TeamPage.tsx`
- `frontend/src/pages/AnalysisReportsPage.tsx`
- `frontend/src/pages/FavoritesPage.tsx`
- `frontend/src/pages/BetHistoryPage.tsx`
- `frontend/src/pages/SettingsPage.tsx`

### Modify
- `frontend/src/App.tsx`
- `frontend/src/layouts/AppLayout.tsx`
- `frontend/src/components/SideNav.tsx`
- `frontend/src/index.css`

### Move (Task 19)
- `pages/{BoardPage,DashboardPage,ChatPanel,TokenStatsPage}.tsx` → `pages/legacy/`
- `components/{MatchSourcePanel,AgentDetailDrawer}.tsx` → `pages/legacy/`

---

## Task 1: Browse types + API client

**Files:**
- Create: `frontend/src/types/browse.ts`
- Create: `frontend/src/services/browse.ts`
- Test: `frontend/src/services/__tests__/browse.test.ts`

- [ ] **Step 1: Write failing test**

Create `frontend/src/services/__tests__/browse.test.ts`:
```typescript
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { browseApi } from "../browse";

beforeEach(() => { global.fetch = vi.fn(); });
afterEach(() => vi.restoreAllMocks());

describe("browseApi", () => {
  it("getCompetitions returns parsed list", async () => {
    (global.fetch as any).mockResolvedValue({
      ok: true, json: async () => [{ id: 8, name: "Premier League", country: "England" }],
    });
    const out = await browseApi.getCompetitions();
    expect(out[0].name).toBe("Premier League");
    expect(global.fetch).toHaveBeenCalledWith("/api/competitions", expect.any(Object));
  });

  it("getFixtures forwards date and competition_id", async () => {
    (global.fetch as any).mockResolvedValue({ ok: true, json: async () => [] });
    await browseApi.getFixtures({ date: "2026-05-14", competitionId: 8 });
    const url = (global.fetch as any).mock.calls[0][0];
    expect(url).toBe("/api/fixtures?date=2026-05-14&competition_id=8");
  });

  it("getFixtureDetail returns 404 as null", async () => {
    (global.fetch as any).mockResolvedValue({ ok: false, status: 404, text: async () => "nf" });
    const out = await browseApi.getFixtureDetail(999);
    expect(out).toBeNull();
  });

  it("runAnalysis posts", async () => {
    (global.fetch as any).mockResolvedValue({
      ok: true, json: async () => ({ run_id: "0099", status: "started" })
    });
    const out = await browseApi.runAnalysis();
    expect(out.run_id).toBe("0099");
    expect((global.fetch as any).mock.calls[0][1].method).toBe("POST");
  });
});
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd frontend && npm test -- src/services/__tests__/browse.test.ts
```

- [ ] **Step 3: Create `frontend/src/types/browse.ts`**

```typescript
export interface Competition { id: number; name: string; country?: string; }
export interface League { id: number; name?: string; country?: string; }
export interface Team { id: number; name: string; }

export interface Fixture {
  fixture_id: number;
  name?: string;
  kickoff_utc?: string;
  league?: League;
  closing?: number;
  opening?: number;
  drop_percentage?: number;
}

export interface OddsLine { closing?: number; opening?: number; peak?: number; }
export interface OddsByDirection { home: OddsLine; draw: OddsLine; away: OddsLine; }
export interface OddsHistory { markets: Record<string, Record<string, OddsByDirection>>; }

export interface AnalysisRecord {
  model_prob: { H: number; D: number; A: number };
  market_prob: { H: number | null; D: number | null; A: number | null };
  pick: "H" | "D" | "A";
  odds?: number;
  ev?: number;
  kelly?: number;
  confidence_stars: number;
  analyst_summary?: string | null;
  reviewer_verdict?: "pass" | "fail" | "skip" | null;
  run_id?: string | null;
  analyzed_at: string;
}

export interface FixtureDetail {
  fixture_id: number;
  name?: string;
  kickoff_utc?: string;
  league?: League;
  home_team?: Team;
  away_team?: Team;
  odds_history?: OddsHistory;
  h2h?: any[];
  stats_home?: Record<string, any>;
  stats_away?: Record<string, any>;
  trends?: Record<string, number>;
  analysis?: AnalysisRecord | null;
}

export type TrendType = "home_win" | "away_win" | "btts" | "over25";

export interface TrendItem {
  fixture_id: number;
  fixture_name?: string;
  probability: number;
  odds?: number;
  league?: League;
  kickoff_utc?: string;
}

export interface DroppingOdd {
  fixture_id: number;
  fixture_name?: string;
  starting_at?: string;
  league?: League;
  market_key?: string;
  opening?: number;
  closing?: number;
  drop_percentage?: number;
  bookmaker?: string;
}

export interface TeamStats {
  team_id: number;
  name: string;
  goals_for_avg?: number;
  goals_against_avg?: number;
  xg_for?: number;
  xg_against?: number;
}

export interface AnalysisRunResult { run_id: string; status: string; }
```

- [ ] **Step 4: Create `frontend/src/services/browse.ts`**

```typescript
import type {
  Competition, Fixture, FixtureDetail, TrendItem, TrendType,
  DroppingOdd, TeamStats, AnalysisRunResult, AnalysisRecord,
} from "../types/browse";

const BASE = "/api";

async function get<T>(url: string): Promise<T> {
  const res = await fetch(`${BASE}${url}`, { headers: { "Content-Type": "application/json" } });
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`);
  return res.json();
}

async function getOrNull<T>(url: string): Promise<T | null> {
  const res = await fetch(`${BASE}${url}`, { headers: { "Content-Type": "application/json" } });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`);
  return res.json();
}

async function post<T>(url: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`);
  return res.json();
}

export const browseApi = {
  getCompetitions: () => get<Competition[]>("/competitions"),
  getFixtures: (params: { date: string; competitionId?: number }) => {
    const q = new URLSearchParams({ date: params.date });
    if (params.competitionId) q.set("competition_id", String(params.competitionId));
    return get<Fixture[]>(`/fixtures?${q.toString()}`);
  },
  getFixtureDetail: (id: number) => getOrNull<FixtureDetail>(`/fixtures/${id}`),
  getTrends: (type: TrendType) => get<TrendItem[]>(`/trends/${type}`),
  getDropping: (opts: { market?: string; minDrop?: number; window?: "1h" | "6h" | "24h" } = {}) => {
    const q = new URLSearchParams();
    if (opts.market) q.set("market", opts.market);
    if (opts.minDrop != null) q.set("min_drop", String(opts.minDrop));
    if (opts.window) q.set("window", opts.window);
    const qs = q.toString();
    return get<DroppingOdd[]>(`/odds/dropping${qs ? "?" + qs : ""}`);
  },
  getTeam: (id: number) => getOrNull<TeamStats>(`/teams/${id}`),
  getStandings: (leagueId: number) => getOrNull<any[]>(`/leagues/${leagueId}/standings`),
  getAnalysisRecent: (limit = 20) =>
    get<Array<{ fixture_id: number; name?: string; analysis: AnalysisRecord | null }>>(
      `/analysis/recent?limit=${limit}`,
    ),
  runAnalysis: () => post<AnalysisRunResult>("/analysis/run"),
};
```

- [ ] **Step 5: Run — expect PASS**

```bash
cd frontend && npm test -- src/services/__tests__/browse.test.ts
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/types/browse.ts frontend/src/services/browse.ts frontend/src/services/__tests__/
git commit -m "feat(frontend): browse API types + typed client"
```

---

## Task 2: Routes rewrite + page stubs

**Files:**
- Modify: `frontend/src/App.tsx`
- Create: 10 stub pages under `frontend/src/pages/`

- [ ] **Step 1: Create stub pages**

For each new page below, create a one-line file:
- `frontend/src/pages/BettingPage.tsx`
- `frontend/src/pages/FixtureDetailPage.tsx`
- `frontend/src/pages/DroppingOddsPage.tsx`
- `frontend/src/pages/TrendsPage.tsx`
- `frontend/src/pages/LeaguePage.tsx`
- `frontend/src/pages/TeamPage.tsx`
- `frontend/src/pages/AnalysisReportsPage.tsx`
- `frontend/src/pages/FavoritesPage.tsx`
- `frontend/src/pages/BetHistoryPage.tsx`
- `frontend/src/pages/SettingsPage.tsx`

Each contains the stub (rename the component to match the file):
```tsx
export default function BettingPage() { return <div>BettingPage (stub)</div>; }
```

- [ ] **Step 2: Rewrite `frontend/src/App.tsx`**

```tsx
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ConfigProvider, theme } from "antd";
import AppLayout from "./layouts/AppLayout";
import BettingPage from "./pages/BettingPage";
import FixtureDetailPage from "./pages/FixtureDetailPage";
import DroppingOddsPage from "./pages/DroppingOddsPage";
import TrendsPage from "./pages/TrendsPage";
import LeaguePage from "./pages/LeaguePage";
import TeamPage from "./pages/TeamPage";
import AnalysisReportsPage from "./pages/AnalysisReportsPage";
import FavoritesPage from "./pages/FavoritesPage";
import BetHistoryPage from "./pages/BetHistoryPage";
import SettingsPage from "./pages/SettingsPage";
import PipelineMonitor from "./pages/PipelineMonitor";
import ChatPanel from "./pages/ChatPanel";
import BoardPage from "./pages/BoardPage";
import DashboardPage from "./pages/DashboardPage";
import TokenStatsPage from "./pages/TokenStatsPage";
import "./index.css";

function App() {
  return (
    <ConfigProvider
      theme={{
        algorithm: theme.darkAlgorithm,
        token: {
          colorPrimary: "#00FF9D",
          colorPrimaryBg: "rgba(0,255,157,0.08)",
          colorPrimaryBorder: "rgba(0,255,157,0.28)",
          colorBgContainer: "#0f1220",
          colorBgElevated: "#0b0d17",
          colorBgLayout: "#060810",
          colorText: "#e8eaf0",
          colorTextSecondary: "#9ba3b8",
          colorTextTertiary: "#555d72",
          colorSuccess: "#4ade80",
          colorWarning: "#ff9500",
          colorError: "#ef4444",
          borderRadius: 8,
          fontFamily: "'Space Grotesk', sans-serif",
          fontFamilyCode: "'JetBrains Mono', monospace",
        },
      }}
    >
      <BrowserRouter>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="/" element={<BettingPage />} />
            <Route path="/fixture/:id" element={<FixtureDetailPage />} />
            <Route path="/dropping" element={<DroppingOddsPage />} />
            <Route path="/trends" element={<Navigate to="/trends/home_win" replace />} />
            <Route path="/trends/:type" element={<TrendsPage />} />
            <Route path="/league/:id" element={<LeaguePage />} />
            <Route path="/team/:id" element={<TeamPage />} />
            <Route path="/analysis" element={<AnalysisReportsPage />} />
            <Route path="/analysis/pipeline" element={<PipelineMonitor />} />
            <Route path="/analysis/chat" element={<ChatPanel />} />
            <Route path="/my" element={<FavoritesPage />} />
            <Route path="/my/bets" element={<BetHistoryPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/legacy/dashboard" element={<DashboardPage />} />
            <Route path="/legacy/board" element={<BoardPage />} />
            <Route path="/legacy/token-stats" element={<TokenStatsPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  );
}

export default App;
```

- [ ] **Step 3: TypeScript check**

```bash
cd frontend && npx tsc -b --noEmit
```
Expected: no errors.

- [ ] **Step 4: Smoke run dev server**

```bash
cd frontend && timeout 15 npm run dev 2>&1 | head -10
```
Expected: Vite starts cleanly. Kill after ~5s.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.tsx frontend/src/pages/
git commit -m "feat(frontend): rewrite routes + stub new pages"
```

---

## Task 3: SideNav grouped + AppLayout

**Files:**
- Modify: `frontend/src/components/SideNav.tsx`
- Modify: `frontend/src/layouts/AppLayout.tsx`
- Test: `frontend/src/components/__tests__/SideNav.test.tsx`

- [ ] **Step 1: Write failing test**

Create `frontend/src/components/__tests__/SideNav.test.tsx`:
```tsx
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect } from "vitest";
import SideNav from "../SideNav";

describe("SideNav", () => {
  it("renders Browse, Analysis, My groups", () => {
    render(<MemoryRouter><SideNav /></MemoryRouter>);
    expect(screen.getByText(/浏览/)).toBeInTheDocument();
    expect(screen.getByText(/分析/)).toBeInTheDocument();
    expect(screen.getByText(/我的/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd frontend && npm test -- src/components/__tests__/SideNav.test.tsx
```

- [ ] **Step 3: Rewrite `frontend/src/components/SideNav.tsx`**

```tsx
import { Link, useLocation } from "react-router-dom";
import { Menu } from "antd";
import {
  HomeOutlined, FireOutlined, LineChartOutlined,
  BarChartOutlined, ApiOutlined, MessageOutlined,
  StarOutlined, SettingOutlined,
} from "@ant-design/icons";

export default function SideNav() {
  const location = useLocation();
  const items = [
    {
      key: "browse", label: "浏览", type: "group" as const,
      children: [
        { key: "/", icon: <HomeOutlined />, label: <Link to="/">主页</Link> },
        { key: "/dropping", icon: <FireOutlined />, label: <Link to="/dropping">跌水榜</Link> },
        { key: "/trends/home_win", icon: <LineChartOutlined />,
          label: <Link to="/trends/home_win">趋势榜</Link> },
      ],
    },
    {
      key: "analysis", label: "分析", type: "group" as const,
      children: [
        { key: "/analysis", icon: <BarChartOutlined />, label: <Link to="/analysis">分析报告</Link> },
        { key: "/analysis/pipeline", icon: <ApiOutlined />,
          label: <Link to="/analysis/pipeline">Pipeline</Link> },
        { key: "/analysis/chat", icon: <MessageOutlined />,
          label: <Link to="/analysis/chat">对话</Link> },
      ],
    },
    {
      key: "my", label: "我的", type: "group" as const,
      children: [
        { key: "/my", icon: <StarOutlined />, label: <Link to="/my">收藏</Link> },
        { key: "/settings", icon: <SettingOutlined />, label: <Link to="/settings">设置</Link> },
      ],
    },
  ];
  return (
    <Menu
      mode="inline"
      theme="dark"
      selectedKeys={[location.pathname]}
      style={{ height: "100%", borderRight: 0, background: "transparent" }}
      items={items}
    />
  );
}
```

- [ ] **Step 4: Update `frontend/src/layouts/AppLayout.tsx`**

```tsx
import { Layout } from "antd";
import { Outlet } from "react-router-dom";
import SideNav from "../components/SideNav";
import MobileTabBar from "../components/MobileTabBar";

export default function AppLayout() {
  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Layout.Sider width={240} className="goalcast-sider" breakpoint="md" collapsedWidth={0}>
        <div className="goalcast-logo">⚽ GOALCAST</div>
        <SideNav />
      </Layout.Sider>
      <Layout>
        <Layout.Content className="goalcast-content">
          <Outlet />
        </Layout.Content>
      </Layout>
      <MobileTabBar />
    </Layout>
  );
}
```

If `MobileTabBar` does not yet exist, create a temporary stub at `frontend/src/components/MobileTabBar.tsx`:
```tsx
export default function MobileTabBar() { return null; }
```
Task 18 replaces it.

- [ ] **Step 5: Run — expect PASS**

```bash
cd frontend && npm test -- src/components/__tests__/SideNav.test.tsx
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/SideNav.tsx frontend/src/layouts/AppLayout.tsx frontend/src/components/MobileTabBar.tsx frontend/src/components/__tests__/SideNav.test.tsx
git commit -m "feat(frontend): SideNav grouped (Browse/Analysis/My) + MobileTabBar stub"
```

---

## Task 4: LeagueTree component

**Files:**
- Create: `frontend/src/components/LeagueTree.tsx`
- Test: `frontend/src/components/__tests__/LeagueTree.test.tsx`

- [ ] **Step 1: Write failing test**

```tsx
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import LeagueTree from "../LeagueTree";
import type { Competition } from "../../types/browse";

const comps: Competition[] = [
  { id: 8, name: "Premier League", country: "England" },
  { id: 9, name: "Championship", country: "England" },
  { id: 564, name: "La Liga", country: "Spain" },
];

describe("LeagueTree", () => {
  it("groups by country", () => {
    render(<LeagueTree competitions={comps} onSelect={() => {}} />);
    expect(screen.getByText("England")).toBeInTheDocument();
    expect(screen.getByText("Spain")).toBeInTheDocument();
  });

  it("filters by search query", () => {
    render(<LeagueTree competitions={comps} onSelect={() => {}} />);
    fireEvent.change(screen.getByPlaceholderText(/搜索/), { target: { value: "Liga" } });
    expect(screen.queryByText("Premier League")).toBeNull();
    expect(screen.getByText("La Liga")).toBeInTheDocument();
  });

  it("fires onSelect when a league is clicked", () => {
    const onSelect = vi.fn();
    render(<LeagueTree competitions={comps} onSelect={onSelect} />);
    fireEvent.click(screen.getByText("Premier League"));
    expect(onSelect).toHaveBeenCalledWith(8);
  });
});
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd frontend && npm test -- src/components/__tests__/LeagueTree.test.tsx
```

- [ ] **Step 3: Implement `frontend/src/components/LeagueTree.tsx`**

```tsx
import { useMemo, useState } from "react";
import { Input } from "antd";
import { SearchOutlined } from "@ant-design/icons";
import type { Competition } from "../types/browse";

interface Props {
  competitions: Competition[];
  selectedId?: number;
  onSelect: (competitionId: number | undefined) => void;
}

export default function LeagueTree({ competitions, selectedId, onSelect }: Props) {
  const [query, setQuery] = useState("");
  const groups = useMemo(() => {
    const q = query.trim().toLowerCase();
    const grouped: Record<string, Competition[]> = {};
    for (const c of competitions) {
      if (q && !`${c.name} ${c.country ?? ""}`.toLowerCase().includes(q)) continue;
      const key = c.country || "其他";
      (grouped[key] ||= []).push(c);
    }
    return Object.entries(grouped).sort(([a], [b]) => a.localeCompare(b));
  }, [competitions, query]);

  return (
    <div className="league-tree">
      <Input
        prefix={<SearchOutlined />}
        placeholder="搜索联赛 / 国家"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        size="small"
      />
      <div className="league-tree-shortcut">
        <div className={`shortcut ${selectedId === undefined ? "on" : ""}`}
             onClick={() => onSelect(undefined)}>📅 今日比赛</div>
      </div>
      {groups.map(([country, items]) => (
        <div key={country} className="league-tree-group">
          <div className="league-tree-country">{country}</div>
          {items.map((c) => (
            <div key={c.id}
                 className={`league-tree-item ${selectedId === c.id ? "on" : ""}`}
                 onClick={() => onSelect(c.id)}>
              {c.name}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 4: Append CSS to `frontend/src/index.css`**

```css
.league-tree { display:flex; flex-direction:column; gap:8px; padding:8px; }
.league-tree-shortcut .shortcut { padding:5px 8px; border-radius:5px; cursor:pointer; color:#9ba3b8; font-size:12px; }
.league-tree-shortcut .shortcut.on { background:rgba(0,255,157,0.10); color:#00FF9D; }
.league-tree-country { font-size:10px; color:#555d72; text-transform:uppercase; letter-spacing:1px; padding:6px 8px 2px; }
.league-tree-item { padding:5px 8px; border-radius:5px; cursor:pointer; color:#9ba3b8; font-size:12px; }
.league-tree-item:hover { color:#e8eaf0; background:#0f1220; }
.league-tree-item.on { background:rgba(0,255,157,0.10); color:#00FF9D; }
```

- [ ] **Step 5: Run — expect PASS**

```bash
cd frontend && npm test -- src/components/__tests__/LeagueTree.test.tsx
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/LeagueTree.tsx frontend/src/components/__tests__/LeagueTree.test.tsx frontend/src/index.css
git commit -m "feat(frontend): LeagueTree with country grouping + search"
```

---

## Task 5: AnalysisBadge component

**Files:**
- Create: `frontend/src/components/AnalysisBadge.tsx`
- Test: `frontend/src/components/__tests__/AnalysisBadge.test.tsx`

- [ ] **Step 1: Write failing test**

```tsx
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import AnalysisBadge from "../AnalysisBadge";

describe("AnalysisBadge", () => {
  it("renders EV positive", () => {
    render(<AnalysisBadge ev={0.064} stars={4} pick="H" />);
    expect(screen.getByText(/\+6\.4%/)).toBeInTheDocument();
    expect(screen.getByText(/主胜/)).toBeInTheDocument();
  });

  it("renders stars count", () => {
    const { container } = render(<AnalysisBadge ev={0.03} stars={3} pick="A" />);
    expect(container.querySelectorAll(".star.on")).toHaveLength(3);
  });

  it("renders placeholder when no analysis", () => {
    render(<AnalysisBadge />);
    expect(screen.getByText(/观望/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd frontend && npm test -- src/components/__tests__/AnalysisBadge.test.tsx
```

- [ ] **Step 3: Implement `frontend/src/components/AnalysisBadge.tsx`**

```tsx
const PICK_LABEL: Record<string, string> = { H: "主胜", D: "平", A: "客胜" };

interface Props {
  ev?: number;
  stars?: number;
  pick?: "H" | "D" | "A";
}

export default function AnalysisBadge({ ev, stars = 0, pick }: Props) {
  if (ev === undefined || pick === undefined) {
    return <span className="analysis-badge muted">观望</span>;
  }
  const evPct = (ev * 100).toFixed(1);
  return (
    <span className="analysis-badge">
      <span className="ev">{ev >= 0 ? "+" : ""}{evPct}%</span>
      <span className="pick">{PICK_LABEL[pick]}</span>
      <span className="stars">
        {[1, 2, 3, 4, 5].map((i) => (
          <span key={i} className={`star ${i <= stars ? "on" : ""}`}>★</span>
        ))}
      </span>
    </span>
  );
}
```

Append CSS:
```css
.analysis-badge { display:inline-flex; align-items:center; gap:6px; font-size:11px; }
.analysis-badge .ev { color:#00FF9D; font-weight:600; }
.analysis-badge .pick { color:#e8eaf0; font-weight:500; }
.analysis-badge .star { color:#3a3f52; font-size:10px; }
.analysis-badge .star.on { color:#facc15; }
.analysis-badge.muted { color:#555d72; }
```

- [ ] **Step 4: Run — expect PASS**

```bash
cd frontend && npm test -- src/components/__tests__/AnalysisBadge.test.tsx
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/AnalysisBadge.tsx frontend/src/components/__tests__/AnalysisBadge.test.tsx frontend/src/index.css
git commit -m "feat(frontend): AnalysisBadge reusable component"
```

---

## Task 6: FixtureCard component

**Files:**
- Create: `frontend/src/components/FixtureCard.tsx`
- Test: `frontend/src/components/__tests__/FixtureCard.test.tsx`

- [ ] **Step 1: Write failing test**

```tsx
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import FixtureCard from "../FixtureCard";
import type { Fixture } from "../../types/browse";

const f: Fixture = {
  fixture_id: 1,
  name: "Arsenal vs Chelsea",
  kickoff_utc: "2026-05-14T20:00:00Z",
  league: { id: 8, name: "Premier League", country: "England" },
  closing: 1.72,
  opening: 1.87,
  drop_percentage: -8.0,
};

describe("FixtureCard", () => {
  it("renders teams and odds", () => {
    render(<FixtureCard fixture={f} onClick={() => {}} />);
    expect(screen.getByText(/Arsenal/)).toBeInTheDocument();
    expect(screen.getByText(/Chelsea/)).toBeInTheDocument();
    expect(screen.getByText("1.72")).toBeInTheDocument();
  });

  it("shows drop percentage", () => {
    render(<FixtureCard fixture={f} onClick={() => {}} />);
    expect(screen.getByText(/-8/)).toBeInTheDocument();
  });

  it("fires onClick with fixture id", () => {
    const onClick = vi.fn();
    const { container } = render(<FixtureCard fixture={f} onClick={onClick} />);
    fireEvent.click(container.querySelector(".fixture-card")!);
    expect(onClick).toHaveBeenCalledWith(1);
  });
});
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd frontend && npm test -- src/components/__tests__/FixtureCard.test.tsx
```

- [ ] **Step 3: Implement `frontend/src/components/FixtureCard.tsx`**

```tsx
import dayjs from "dayjs";
import type { Fixture } from "../types/browse";
import AnalysisBadge from "./AnalysisBadge";

interface Props {
  fixture: Fixture;
  analysis?: { ev?: number; stars?: number; pick?: "H" | "D" | "A" };
  onClick: (fixtureId: number) => void;
}

function splitName(name?: string): [string, string] {
  if (!name) return ["", ""];
  const parts = name.split(/\s+vs\s+/i);
  return [parts[0] ?? "", parts[1] ?? ""];
}

export default function FixtureCard({ fixture, analysis, onClick }: Props) {
  const [home, away] = splitName(fixture.name);
  const ko = fixture.kickoff_utc ? dayjs(fixture.kickoff_utc).format("HH:mm") : "—";
  const drop = fixture.drop_percentage ?? 0;

  return (
    <div className="fixture-card" onClick={() => onClick(fixture.fixture_id)}>
      <div className="fc-head">
        <span>⚽ {fixture.league?.name ?? "—"}</span>
        <span>{ko} KO</span>
      </div>
      <div className="fc-teams">
        <div className="fc-team">{home}</div>
        <div className="fc-team">{away}</div>
      </div>
      <div className="fc-odds">
        {fixture.closing != null && (
          <div className="fc-odd best">
            <div className="lbl">当前</div>
            <div className="val">{fixture.closing.toFixed(2)}</div>
          </div>
        )}
        {fixture.opening != null && (
          <div className="fc-odd">
            <div className="lbl">开盘</div>
            <div className="val">{fixture.opening.toFixed(2)}</div>
          </div>
        )}
        {drop !== 0 && (
          <div className="fc-odd drop">
            <div className="lbl">跌水</div>
            <div className="val">{drop.toFixed(1)}%</div>
          </div>
        )}
      </div>
      <div className="fc-footer">
        <AnalysisBadge ev={analysis?.ev} stars={analysis?.stars} pick={analysis?.pick} />
      </div>
    </div>
  );
}
```

Append CSS:
```css
.fixture-card { background:#0f1220; border:1px solid rgba(255,255,255,0.07); border-radius:10px; padding:12px 14px; cursor:pointer; transition:all .15s; }
.fixture-card:hover { border-color:rgba(0,255,157,0.28); transform:translateY(-1px); }
.fc-head { display:flex; justify-content:space-between; font-size:11px; color:#555d72; margin-bottom:8px; }
.fc-teams { display:flex; flex-direction:column; gap:4px; margin-bottom:10px; }
.fc-team { font-size:13px; color:#e8eaf0; font-weight:500; }
.fc-odds { display:grid; grid-template-columns:repeat(3,1fr); gap:6px; margin-bottom:10px; }
.fc-odd { background:#161a2e; border-radius:6px; padding:6px 8px; text-align:center; }
.fc-odd .lbl { font-size:10px; color:#555d72; }
.fc-odd .val { font-size:14px; font-weight:600; color:#e8eaf0; font-family:"JetBrains Mono",monospace; }
.fc-odd.best .val { color:#00FF9D; }
.fc-odd.drop .val { color:#ef4444; }
.fc-footer { display:flex; justify-content:flex-end; padding-top:8px; border-top:1px dashed rgba(255,255,255,0.07); }
```

- [ ] **Step 4: Run — expect PASS**

```bash
cd frontend && npm test -- src/components/__tests__/FixtureCard.test.tsx
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/FixtureCard.tsx frontend/src/components/__tests__/FixtureCard.test.tsx frontend/src/index.css
git commit -m "feat(frontend): FixtureCard component"
```

---

## Task 7: BettingPage skeleton (route `/`)

**Files:**
- Modify: `frontend/src/pages/BettingPage.tsx`
- Test: `frontend/src/pages/__tests__/BettingPage.test.tsx`

- [ ] **Step 1: Write failing test**

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import BettingPage from "../BettingPage";
import { browseApi } from "../../services/browse";

vi.mock("../../services/browse");

describe("BettingPage", () => {
  beforeEach(() => {
    (browseApi.getCompetitions as any).mockResolvedValue([
      { id: 8, name: "Premier League", country: "England" },
    ]);
    (browseApi.getFixtures as any).mockResolvedValue([
      { fixture_id: 1, name: "Arsenal vs Chelsea",
        kickoff_utc: "2026-05-14T20:00:00Z",
        league: { id: 8, name: "Premier League" }, closing: 1.72 },
    ]);
  });

  it("loads competitions and fixtures on mount", async () => {
    render(<MemoryRouter><BettingPage /></MemoryRouter>);
    await waitFor(() => expect(browseApi.getFixtures).toHaveBeenCalled());
    expect(screen.getByText(/Arsenal/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd frontend && npm test -- src/pages/__tests__/BettingPage.test.tsx
```

- [ ] **Step 3: Implement `frontend/src/pages/BettingPage.tsx`**

```tsx
import { useEffect, useState, useMemo } from "react";
import { Layout, Segmented, DatePicker, Empty, Spin } from "antd";
import dayjs, { Dayjs } from "dayjs";
import { browseApi } from "../services/browse";
import type { Competition, Fixture } from "../types/browse";
import LeagueTree from "../components/LeagueTree";
import FixtureCard from "../components/FixtureCard";
import FixtureDetailDrawer from "../components/FixtureDetailDrawer";

const { Sider, Content } = Layout;

export default function BettingPage() {
  const [competitions, setCompetitions] = useState<Competition[]>([]);
  const [date, setDate] = useState<Dayjs>(dayjs());
  const [selectedLeague, setSelectedLeague] = useState<number | undefined>();
  const [fixtures, setFixtures] = useState<Fixture[]>([]);
  const [loading, setLoading] = useState(false);
  const [drawerFixtureId, setDrawerFixtureId] = useState<number | null>(null);

  useEffect(() => {
    browseApi.getCompetitions().then(setCompetitions).catch(console.error);
  }, []);

  useEffect(() => {
    setLoading(true);
    browseApi.getFixtures({
      date: date.format("YYYY-MM-DD"),
      competitionId: selectedLeague,
    })
      .then(setFixtures)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [date, selectedLeague]);

  const grouped = useMemo(() => {
    const g: Record<string, Fixture[]> = {};
    for (const f of fixtures) {
      const key = f.league?.name ?? "其他";
      (g[key] ||= []).push(f);
    }
    return Object.entries(g);
  }, [fixtures]);

  return (
    <Layout style={{ background: "transparent" }}>
      <Sider width={240} className="goalcast-aside" theme="dark">
        <LeagueTree
          competitions={competitions}
          selectedId={selectedLeague}
          onSelect={setSelectedLeague}
        />
      </Sider>
      <Content style={{ padding: "16px 22px" }}>
        <div className="filters">
          <DatePicker value={date} onChange={(d) => d && setDate(d)} allowClear={false} format="YYYY-MM-DD" />
          <Segmented
            options={[
              { label: "今天", value: 0 },
              { label: "明天", value: 1 },
              { label: "本周", value: 7 },
            ]}
            onChange={(v) => setDate(dayjs().add(Number(v), "day"))}
          />
        </div>

        {loading ? (
          <div style={{ textAlign: "center", padding: 40 }}><Spin /></div>
        ) : fixtures.length === 0 ? (
          <Empty description="无赛事" />
        ) : (
          grouped.map(([league, items]) => (
            <div key={league} className="league-section">
              <h3 className="league-title">{league} <span>{items.length} 场</span></h3>
              <div className="fixture-grid">
                {items.map((f) => (
                  <FixtureCard
                    key={f.fixture_id}
                    fixture={f}
                    onClick={(id) => setDrawerFixtureId(id)}
                  />
                ))}
              </div>
            </div>
          ))
        )}

        <FixtureDetailDrawer
          fixtureId={drawerFixtureId}
          open={drawerFixtureId !== null}
          onClose={() => setDrawerFixtureId(null)}
        />
      </Content>
    </Layout>
  );
}
```

Append CSS:
```css
.filters { display:flex; gap:10px; align-items:center; margin-bottom:16px; flex-wrap:wrap; }
.league-section { margin-bottom:24px; }
.league-title { font-size:13px; font-weight:600; margin:18px 0 10px; }
.league-title span { color:#555d72; font-size:11px; font-weight:400; margin-left:8px; }
.fixture-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(340px,1fr)); gap:12px; }
.goalcast-aside { background:#0b0d17 !important; border-right:1px solid rgba(255,255,255,0.07); }
```

- [ ] **Step 4: Note — `FixtureDetailDrawer` is created in Task 8**

If the import fails, create a temporary stub at `frontend/src/components/FixtureDetailDrawer.tsx`:
```tsx
export default function FixtureDetailDrawer(_: { fixtureId: number | null; open: boolean; onClose: () => void }) { return null; }
```

- [ ] **Step 5: Run — expect PASS**

```bash
cd frontend && npm test -- src/pages/__tests__/BettingPage.test.tsx
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/BettingPage.tsx frontend/src/pages/__tests__/ frontend/src/index.css frontend/src/components/FixtureDetailDrawer.tsx
git commit -m "feat(frontend): BettingPage skeleton with league tree + filters"
```

---

## Task 8: FixtureDetailDrawer

**Files:**
- Modify: `frontend/src/components/FixtureDetailDrawer.tsx`
- Test: `frontend/src/components/__tests__/FixtureDetailDrawer.test.tsx`

- [ ] **Step 1: Write failing test**

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import FixtureDetailDrawer from "../FixtureDetailDrawer";
import { browseApi } from "../../services/browse";

vi.mock("../../services/browse");

describe("FixtureDetailDrawer", () => {
  beforeEach(() => {
    (browseApi.getFixtureDetail as any).mockResolvedValue({
      fixture_id: 1,
      home_team: { id: 11, name: "Arsenal" },
      away_team: { id: 22, name: "Chelsea" },
      kickoff_utc: "2026-05-14T20:00:00Z",
      analysis: {
        pick: "H", ev: 0.064, confidence_stars: 4,
        model_prob: { H: 0.62, D: 0.2, A: 0.18 },
        market_prob: { H: null, D: null, A: null }, analyzed_at: "",
      },
    });
  });

  it("renders fixture name and analysis when open", async () => {
    render(<MemoryRouter><FixtureDetailDrawer fixtureId={1} open onClose={() => {}} /></MemoryRouter>);
    await waitFor(() => expect(screen.getByText(/Arsenal/)).toBeInTheDocument());
    expect(screen.getByText(/Chelsea/)).toBeInTheDocument();
    expect(screen.getByText(/主胜/)).toBeInTheDocument();
  });

  it("does not fetch when closed", () => {
    render(<MemoryRouter><FixtureDetailDrawer fixtureId={1} open={false} onClose={() => {}} /></MemoryRouter>);
    expect(browseApi.getFixtureDetail).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd frontend && npm test -- src/components/__tests__/FixtureDetailDrawer.test.tsx
```

- [ ] **Step 3: Implement `frontend/src/components/FixtureDetailDrawer.tsx`**

```tsx
import { useEffect, useState } from "react";
import { Drawer, Tabs, Button, Spin } from "antd";
import { useNavigate } from "react-router-dom";
import dayjs from "dayjs";
import { browseApi } from "../services/browse";
import type { FixtureDetail } from "../types/browse";
import AnalysisBadge from "./AnalysisBadge";

interface Props {
  fixtureId: number | null;
  open: boolean;
  onClose: () => void;
}

export default function FixtureDetailDrawer({ fixtureId, open, onClose }: Props) {
  const navigate = useNavigate();
  const [data, setData] = useState<FixtureDetail | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open || fixtureId == null) return;
    setLoading(true);
    browseApi.getFixtureDetail(fixtureId)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [open, fixtureId]);

  const title = data
    ? `${data.home_team?.name ?? ""} vs ${data.away_team?.name ?? ""}`
    : "加载中...";

  return (
    <Drawer
      title={title}
      placement="right"
      width={560}
      onClose={onClose}
      open={open}
      extra={
        data && (
          <Button type="primary" onClick={() => { onClose(); navigate(`/fixture/${data.fixture_id}`); }}>
            查看完整页面 →
          </Button>
        )
      }
    >
      {loading || !data ? (
        <Spin />
      ) : (
        <Tabs
          items={[
            {
              key: "overview", label: "概览",
              children: (
                <div>
                  <div style={{ color: "#555d72", fontSize: 11, marginBottom: 8 }}>
                    {data.league?.name} · {dayjs(data.kickoff_utc).format("YYYY-MM-DD HH:mm")}
                  </div>
                  {data.analysis && (
                    <div className="analysis-card" style={{ padding: 12, background: "#0f1220", border: "1px solid rgba(0,255,157,0.28)", borderRadius: 8 }}>
                      <h4 style={{ marginTop: 0 }}>🎯 自研分析</h4>
                      <AnalysisBadge
                        ev={data.analysis.ev}
                        stars={data.analysis.confidence_stars}
                        pick={data.analysis.pick}
                      />
                      {data.analysis.analyst_summary && (
                        <div style={{ marginTop: 8, fontSize: 12, color: "#9ba3b8" }}>
                          {data.analysis.analyst_summary}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ),
            },
            { key: "odds", label: "赔率曲线", children: <div>(Task 9 接入 OddsCurveChart)</div> },
            { key: "h2h", label: "H2H", children: <div>(Task 10 接入 H2HTable)</div> },
          ]}
        />
      )}
    </Drawer>
  );
}
```

- [ ] **Step 4: Run — expect PASS**

```bash
cd frontend && npm test -- src/components/__tests__/FixtureDetailDrawer.test.tsx
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/FixtureDetailDrawer.tsx frontend/src/components/__tests__/FixtureDetailDrawer.test.tsx
git commit -m "feat(frontend): FixtureDetailDrawer with overview + analysis"
```

---

## Task 9: OddsCurveChart (SVG)

**Files:**
- Create: `frontend/src/components/OddsCurveChart.tsx`
- Test: `frontend/src/components/__tests__/OddsCurveChart.test.tsx`

- [ ] **Step 1: Write failing test**

```tsx
import { render } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import OddsCurveChart from "../OddsCurveChart";

describe("OddsCurveChart", () => {
  it("renders three polylines for H/D/A", () => {
    const data = {
      home: [1.87, 1.85, 1.80, 1.75, 1.72],
      draw: [3.80, 3.82, 3.85, 3.85, 3.85],
      away: [4.40, 4.45, 4.50, 4.55, 4.60],
    };
    const { container } = render(<OddsCurveChart data={data} />);
    expect(container.querySelectorAll("polyline")).toHaveLength(3);
  });

  it("renders placeholder when no data", () => {
    const { container } = render(<OddsCurveChart data={null} />);
    expect(container.textContent).toMatch(/无数据/);
  });
});
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd frontend && npm test -- src/components/__tests__/OddsCurveChart.test.tsx
```

- [ ] **Step 3: Implement `frontend/src/components/OddsCurveChart.tsx`**

```tsx
interface Series { home: number[]; draw: number[]; away: number[]; }

interface Props {
  data: Series | null;
  width?: number;
  height?: number;
}

export default function OddsCurveChart({ data, width = 480, height = 140 }: Props) {
  if (!data || data.home.length === 0) {
    return <div style={{ color: "#555d72", padding: 20 }}>无数据</div>;
  }
  const all = [...data.home, ...data.draw, ...data.away];
  const min = Math.min(...all);
  const max = Math.max(...all);
  const padding = { x: 20, y: 20 };

  function points(arr: number[]): string {
    const stepX = (width - padding.x * 2) / (arr.length - 1 || 1);
    return arr.map((v, i) => {
      const x = padding.x + i * stepX;
      const y = padding.y + (1 - (v - min) / (max - min || 1)) * (height - padding.y * 2);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(" ");
  }

  return (
    <div className="chart-wrap">
      <div className="chart-legend">
        <span><span className="dot" style={{ background: "#00FF9D" }} />主胜</span>
        <span><span className="dot" style={{ background: "#555d72" }} />平</span>
        <span><span className="dot" style={{ background: "#60a5fa" }} />客胜</span>
      </div>
      <svg viewBox={`0 0 ${width} ${height}`} width="100%" height={height}>
        <polyline points={points(data.home)} fill="none" stroke="#00FF9D" strokeWidth="2" />
        <polyline points={points(data.draw)} fill="none" stroke="#555d72" strokeWidth="2" strokeDasharray="3,3" />
        <polyline points={points(data.away)} fill="none" stroke="#60a5fa" strokeWidth="2" />
      </svg>
    </div>
  );
}
```

Append CSS:
```css
.chart-wrap { background:#0f1220; border:1px solid rgba(255,255,255,0.07); border-radius:8px; padding:10px; }
.chart-legend { display:flex; gap:14px; font-size:10px; color:#9ba3b8; margin-bottom:6px; }
.chart-legend .dot { display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:4px; vertical-align:middle; }
```

- [ ] **Step 4: Run — expect PASS**

```bash
cd frontend && npm test -- src/components/__tests__/OddsCurveChart.test.tsx
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/OddsCurveChart.tsx frontend/src/components/__tests__/OddsCurveChart.test.tsx frontend/src/index.css
git commit -m "feat(frontend): OddsCurveChart SVG component"
```

---

## Task 10: FixtureDetailPage (full) + sub-tables

**Files:**
- Modify: `frontend/src/pages/FixtureDetailPage.tsx`
- Create: `frontend/src/components/MarketDepthTable.tsx`
- Create: `frontend/src/components/StatsCompare.tsx`
- Create: `frontend/src/components/H2HTable.tsx`
- Test: `frontend/src/pages/__tests__/FixtureDetailPage.test.tsx`

- [ ] **Step 1: Write failing test**

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import FixtureDetailPage from "../FixtureDetailPage";
import { browseApi } from "../../services/browse";

vi.mock("../../services/browse");

describe("FixtureDetailPage", () => {
  beforeEach(() => {
    (browseApi.getFixtureDetail as any).mockResolvedValue({
      fixture_id: 1,
      home_team: { id: 11, name: "Arsenal" },
      away_team: { id: 22, name: "Chelsea" },
      kickoff_utc: "2026-05-14T20:00:00Z",
      league: { id: 8, name: "Premier League" },
      odds_history: { markets: { ft_result: { Bet365: {
        home: { closing: 1.72 }, draw: { closing: 3.85 }, away: { closing: 4.60 }
      }}}},
      analysis: { pick: "H", ev: 0.064, confidence_stars: 4,
                  model_prob: { H: 0.62, D: 0.2, A: 0.18 },
                  market_prob: { H: 0.581, D: 0.26, A: 0.159 },
                  analyzed_at: "" },
    });
  });

  it("renders Hero with team names and KPI row", async () => {
    render(
      <MemoryRouter initialEntries={["/fixture/1"]}>
        <Routes><Route path="/fixture/:id" element={<FixtureDetailPage />} /></Routes>
      </MemoryRouter>
    );
    await waitFor(() => expect(screen.getByText(/Arsenal/)).toBeInTheDocument());
    expect(screen.getByText(/Chelsea/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd frontend && npm test -- src/pages/__tests__/FixtureDetailPage.test.tsx
```

- [ ] **Step 3: Implement `frontend/src/components/MarketDepthTable.tsx`**

```tsx
import { Table } from "antd";
import type { OddsHistory } from "../types/browse";

interface Props { history?: OddsHistory; }

export default function MarketDepthTable({ history }: Props) {
  if (!history) return <div style={{ color: "#555d72" }}>无赔率数据</div>;
  const market = history.markets?.ft_result || {};
  const rows = Object.entries(market).map(([book, lines]) => ({
    key: book, book,
    home: lines.home?.closing?.toFixed(2),
    draw: lines.draw?.closing?.toFixed(2),
    away: lines.away?.closing?.toFixed(2),
  }));
  return (
    <Table
      size="small" pagination={false} dataSource={rows}
      columns={[
        { title: "博彩", dataIndex: "book" },
        { title: "主胜", dataIndex: "home", align: "right" },
        { title: "平", dataIndex: "draw", align: "right" },
        { title: "客胜", dataIndex: "away", align: "right" },
      ]}
    />
  );
}
```

- [ ] **Step 4: Implement `frontend/src/components/StatsCompare.tsx`**

```tsx
interface Props { homeStats?: Record<string, any>; awayStats?: Record<string, any>; }

const FIELDS: Array<[string, string]> = [
  ["xg_for", "xG (for)"],
  ["xg_against", "xG (against)"],
  ["goals_for_avg", "场均进球"],
  ["goals_against_avg", "场均失球"],
];

export default function StatsCompare({ homeStats = {}, awayStats = {} }: Props) {
  return (
    <div className="stats-compare">
      {FIELDS.map(([k, label]) => {
        const h = homeStats[k]; const a = awayStats[k];
        if (h == null && a == null) return null;
        return (
          <div key={k} className="row">
            <span className="left">{h ?? "—"}</span>
            <span className="label">{label}</span>
            <span className="right">{a ?? "—"}</span>
          </div>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 5: Implement `frontend/src/components/H2HTable.tsx`**

```tsx
import { Table } from "antd";
interface Props { h2h?: any[]; }
export default function H2HTable({ h2h = [] }: Props) {
  return (
    <Table
      size="small" pagination={false}
      dataSource={h2h.map((r, i) => ({ key: i, ...r }))}
      columns={[
        { title: "日期", dataIndex: "date" },
        { title: "主场", dataIndex: "home" },
        { title: "比分", dataIndex: "score" },
        { title: "客场", dataIndex: "away" },
      ]}
      locale={{ emptyText: "无 H2H 数据" }}
    />
  );
}
```

- [ ] **Step 6: Implement `frontend/src/pages/FixtureDetailPage.tsx`**

```tsx
import { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { Tabs, Statistic, Row, Col, Button, Spin } from "antd";
import dayjs from "dayjs";
import { browseApi } from "../services/browse";
import type { FixtureDetail } from "../types/browse";
import MarketDepthTable from "../components/MarketDepthTable";
import StatsCompare from "../components/StatsCompare";
import H2HTable from "../components/H2HTable";
import AnalysisBadge from "../components/AnalysisBadge";

export default function FixtureDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<FixtureDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    browseApi.getFixtureDetail(Number(id))
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <Spin />;
  if (!data) return <div>赛事未找到</div>;

  const a = data.analysis;
  const modelHpct = a ? (a.model_prob.H * 100).toFixed(1) : "—";
  const evPct = a?.ev != null ? (a.ev * 100).toFixed(1) : "—";
  const kellyPct = a?.kelly != null ? (a.kelly * 100).toFixed(2) : "—";

  return (
    <div className="fixture-detail">
      <div className="fdp-breadcrumb">
        <Link to="/">浏览</Link>
        {data.league?.id && <> ▸ <Link to={`/league/${data.league.id}`}>{data.league.name}</Link></>}
        {" ▸ "}{data.home_team?.name} vs {data.away_team?.name}
      </div>
      <div className="fdp-hero">
        <div className="fdp-team">
          <div className="logo">{data.home_team?.name?.slice(0, 3)}</div>
          <div>{data.home_team?.name}</div>
        </div>
        <div className="fdp-vs">
          <div className="ko">{dayjs(data.kickoff_utc).format("YYYY-MM-DD HH:mm")}</div>
          <div className="meta">{data.league?.name}</div>
        </div>
        <div className="fdp-team">
          <div className="logo">{data.away_team?.name?.slice(0, 3)}</div>
          <div>{data.away_team?.name}</div>
        </div>
        <div className="fdp-actions">
          <Button onClick={() => navigate(-1)}>← 返回</Button>
          <Button type="primary">🔄 重新分析</Button>
        </div>
      </div>
      <Row gutter={12} className="fdp-kpi">
        <Col span={6}><Statistic title="模型 P(H)" value={modelHpct} suffix="%" /></Col>
        <Col span={6}><Statistic title="EV (主胜)" value={evPct} suffix="%" /></Col>
        <Col span={6}><Statistic title="Kelly" value={kellyPct} suffix="%" /></Col>
        <Col span={6}>
          <div style={{ color: "#9ba3b8", fontSize: 12 }}>置信</div>
          <AnalysisBadge ev={a?.ev} stars={a?.confidence_stars} pick={a?.pick} />
        </Col>
      </Row>
      <Tabs
        items={[
          { key: "depth", label: "赔率深度",
            children: <MarketDepthTable history={data.odds_history} /> },
          { key: "stats", label: "统计对比",
            children: <StatsCompare homeStats={data.stats_home} awayStats={data.stats_away} /> },
          { key: "h2h", label: "H2H", children: <H2HTable h2h={data.h2h} /> },
          { key: "json", label: "JSON 原始",
            children: <pre style={{ maxHeight: 400, overflow: "auto" }}>{JSON.stringify(data, null, 2)}</pre> },
        ]}
      />
    </div>
  );
}
```

Append CSS:
```css
.fixture-detail { padding:0 0 40px; }
.fdp-breadcrumb { color:#555d72; font-size:11px; padding:14px 32px 8px; }
.fdp-breadcrumb a { color:#555d72; }
.fdp-hero { display:flex; align-items:center; gap:24px; padding:0 32px 20px; border-bottom:1px solid rgba(255,255,255,0.07); }
.fdp-team { display:flex; flex-direction:column; align-items:center; gap:6px; }
.fdp-team .logo { width:64px; height:64px; border-radius:50%; background:#161a2e; display:flex; align-items:center; justify-content:center; font-weight:800; font-size:18px; }
.fdp-vs { flex:1; text-align:center; }
.fdp-vs .ko { font-size:22px; font-weight:700; color:#00FF9D; font-family:"JetBrains Mono",monospace; }
.fdp-vs .meta { color:#555d72; font-size:11px; }
.fdp-actions { display:flex; gap:8px; }
.fdp-kpi { padding:16px 32px; background:#0b0d17; border-bottom:1px solid rgba(255,255,255,0.07); }
.stats-compare .row { display:grid; grid-template-columns:1fr 80px 1fr; gap:8px; padding:6px 0; align-items:center; }
.stats-compare .left { text-align:right; color:#00FF9D; font-family:"JetBrains Mono",monospace; }
.stats-compare .right { color:#60a5fa; font-family:"JetBrains Mono",monospace; }
.stats-compare .label { color:#555d72; font-size:10px; text-align:center; }
```

- [ ] **Step 7: Run — expect PASS**

```bash
cd frontend && npm test -- src/pages/__tests__/FixtureDetailPage.test.tsx
```

- [ ] **Step 8: Commit**

```bash
git add frontend/src/pages/FixtureDetailPage.tsx frontend/src/components/MarketDepthTable.tsx frontend/src/components/StatsCompare.tsx frontend/src/components/H2HTable.tsx frontend/src/pages/__tests__/ frontend/src/index.css
git commit -m "feat(frontend): FixtureDetailPage with KPI, market depth, stats, H2H"
```

---

## Task 11: DroppingOddsPage

**Files:**
- Modify: `frontend/src/pages/DroppingOddsPage.tsx`
- Test: `frontend/src/pages/__tests__/DroppingOddsPage.test.tsx`

- [ ] **Step 1: Write failing test**

```tsx
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import DroppingOddsPage from "../DroppingOddsPage";
import { browseApi } from "../../services/browse";

vi.mock("../../services/browse");

describe("DroppingOddsPage", () => {
  beforeEach(() => {
    (browseApi.getDropping as any).mockResolvedValue([
      { fixture_id: 1, fixture_name: "Arsenal vs Chelsea",
        starting_at: "2026-05-14T20:00:00Z",
        league: { name: "PL" }, bookmaker: "Bet365",
        opening: 1.87, closing: 1.72, drop_percentage: -8.0 },
    ]);
  });

  it("loads dropping odds and renders row", async () => {
    render(<MemoryRouter><DroppingOddsPage /></MemoryRouter>);
    await waitFor(() => expect(screen.getByText(/Arsenal/)).toBeInTheDocument());
    expect(screen.getByText(/-8/)).toBeInTheDocument();
  });

  it("changes min_drop when chip clicked", async () => {
    render(<MemoryRouter><DroppingOddsPage /></MemoryRouter>);
    await waitFor(() => expect(browseApi.getDropping).toHaveBeenCalled());
    fireEvent.click(screen.getByText("≥12%"));
    await waitFor(() => {
      const last = (browseApi.getDropping as any).mock.calls.at(-1)[0];
      expect(last.minDrop).toBe(12);
    });
  });
});
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd frontend && npm test -- src/pages/__tests__/DroppingOddsPage.test.tsx
```

- [ ] **Step 3: Implement `frontend/src/pages/DroppingOddsPage.tsx`**

```tsx
import { useEffect, useState } from "react";
import { Table, Tag, Space, Typography } from "antd";
import { useNavigate } from "react-router-dom";
import dayjs from "dayjs";
import { browseApi } from "../services/browse";
import type { DroppingOdd } from "../types/browse";

const DROP_OPTIONS = [5, 8, 12];
const WINDOW_OPTIONS = ["1h", "6h", "24h"] as const;

export default function DroppingOddsPage() {
  const navigate = useNavigate();
  const [items, setItems] = useState<DroppingOdd[]>([]);
  const [minDrop, setMinDrop] = useState(8);
  const [windowSel, setWindowSel] = useState<"1h" | "6h" | "24h">("24h");

  useEffect(() => {
    browseApi.getDropping({ minDrop, window: windowSel })
      .then(setItems)
      .catch(console.error);
  }, [minDrop, windowSel]);

  return (
    <div style={{ padding: 24 }}>
      <Typography.Title level={3}>🔥 跌水赔率榜</Typography.Title>
      <Space style={{ marginBottom: 16 }} wrap>
        <span style={{ color: "#555d72" }}>跌幅：</span>
        {DROP_OPTIONS.map((d) => (
          <Tag.CheckableTag key={d} checked={minDrop === d} onChange={() => setMinDrop(d)}>
            ≥{d}%
          </Tag.CheckableTag>
        ))}
        <span style={{ color: "#555d72", marginLeft: 14 }}>时间：</span>
        {WINDOW_OPTIONS.map((w) => (
          <Tag.CheckableTag key={w} checked={windowSel === w} onChange={() => setWindowSel(w)}>
            {w}
          </Tag.CheckableTag>
        ))}
      </Space>
      <Table
        size="small"
        rowKey={(r) => `${r.fixture_id}-${r.bookmaker ?? ""}`}
        dataSource={items}
        onRow={(r) => ({ onClick: () => navigate(`/fixture/${r.fixture_id}`), style: { cursor: "pointer" } })}
        pagination={{ pageSize: 30 }}
        columns={[
          { title: "KO", dataIndex: "starting_at",
            render: (v?: string) => v ? dayjs(v).format("MM-DD HH:mm") : "—" },
          { title: "联赛", dataIndex: ["league", "name"] },
          { title: "对阵", dataIndex: "fixture_name" },
          { title: "开盘", dataIndex: "opening", align: "right",
            render: (v?: number) => v?.toFixed(2) ?? "—" },
          { title: "当前", dataIndex: "closing", align: "right",
            render: (v?: number) => v != null ? <span style={{ color: "#00FF9D" }}>{v.toFixed(2)}</span> : "—" },
          { title: "跌幅", dataIndex: "drop_percentage", align: "right",
            render: (v?: number) => v != null ? <span style={{ color: "#ef4444" }}>{v.toFixed(1)}%</span> : "—" },
          { title: "博彩", dataIndex: "bookmaker" },
        ]}
      />
    </div>
  );
}
```

- [ ] **Step 4: Run — expect PASS**

```bash
cd frontend && npm test -- src/pages/__tests__/DroppingOddsPage.test.tsx
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/DroppingOddsPage.tsx frontend/src/pages/__tests__/DroppingOddsPage.test.tsx
git commit -m "feat(frontend): DroppingOddsPage with min_drop + window filters"
```

---

## Task 12: TrendsPage (4 tabs)

**Files:**
- Modify: `frontend/src/pages/TrendsPage.tsx`
- Test: `frontend/src/pages/__tests__/TrendsPage.test.tsx`

- [ ] **Step 1: Write failing test**

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import TrendsPage from "../TrendsPage";
import { browseApi } from "../../services/browse";

vi.mock("../../services/browse");

describe("TrendsPage", () => {
  beforeEach(() => {
    (browseApi.getTrends as any).mockResolvedValue([
      { fixture_id: 1, fixture_name: "Man City vs Newcastle", probability: 0.72, odds: 1.45 },
    ]);
  });

  it("renders trend cards", async () => {
    render(
      <MemoryRouter initialEntries={["/trends/home_win"]}>
        <Routes><Route path="/trends/:type" element={<TrendsPage />} /></Routes>
      </MemoryRouter>
    );
    await waitFor(() => expect(screen.getByText(/Man City/)).toBeInTheDocument());
    expect(screen.getByText(/72/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd frontend && npm test -- src/pages/__tests__/TrendsPage.test.tsx
```

- [ ] **Step 3: Implement `frontend/src/pages/TrendsPage.tsx`**

```tsx
import { useEffect, useState } from "react";
import { Tabs, Typography, Empty } from "antd";
import { useNavigate, useParams } from "react-router-dom";
import { browseApi } from "../services/browse";
import type { TrendItem, TrendType } from "../types/browse";

const TYPES: { key: TrendType; label: string }[] = [
  { key: "home_win", label: "主胜趋势" },
  { key: "away_win", label: "客胜趋势" },
  { key: "btts", label: "BTTS 趋势" },
  { key: "over25", label: "大球趋势" },
];

export default function TrendsPage() {
  const { type } = useParams<{ type: TrendType }>();
  const navigate = useNavigate();
  const active = (type ?? "home_win") as TrendType;
  const [items, setItems] = useState<TrendItem[]>([]);

  useEffect(() => {
    browseApi.getTrends(active).then(setItems).catch(console.error);
  }, [active]);

  return (
    <div style={{ padding: 24 }}>
      <Typography.Title level={3}>📈 OddAlerts 趋势榜</Typography.Title>
      <Tabs
        activeKey={active}
        onChange={(k) => navigate(`/trends/${k}`)}
        items={TYPES.map(({ key, label }) => ({ key, label }))}
      />
      {items.length === 0 ? (
        <Empty />
      ) : (
        <div className="trend-grid">
          {items.map((t, i) => (
            <div key={t.fixture_id} className="trend-card" onClick={() => navigate(`/fixture/${t.fixture_id}`)}>
              <div className="rank">#{i + 1}</div>
              <div className="pair">{t.fixture_name ?? `Fixture ${t.fixture_id}`}</div>
              <div className="prob">{(t.probability * 100).toFixed(1)}%</div>
              <div className="meta">赔率 {t.odds?.toFixed(2) ?? "—"}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

Append CSS:
```css
.trend-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(300px,1fr)); gap:12px; }
.trend-card { background:#0f1220; border:1px solid rgba(255,255,255,0.07); border-radius:10px; padding:12px 14px; cursor:pointer; position:relative; }
.trend-card:hover { border-color:rgba(0,255,157,0.28); }
.trend-card .rank { position:absolute; top:10px; right:12px; color:#555d72; font-family:"JetBrains Mono",monospace; font-size:11px; }
.trend-card .pair { font-size:13px; font-weight:600; margin-bottom:8px; }
.trend-card .prob { font-size:24px; font-weight:700; color:#00FF9D; font-family:"JetBrains Mono",monospace; }
.trend-card .meta { color:#9ba3b8; font-size:11px; margin-top:8px; }
```

- [ ] **Step 4: Run — expect PASS**

```bash
cd frontend && npm test -- src/pages/__tests__/TrendsPage.test.tsx
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/TrendsPage.tsx frontend/src/pages/__tests__/TrendsPage.test.tsx frontend/src/index.css
git commit -m "feat(frontend): TrendsPage with 4 trend tabs"
```

---

## Task 13: LeaguePage

**Files:**
- Modify: `frontend/src/pages/LeaguePage.tsx`
- Test: `frontend/src/pages/__tests__/LeaguePage.test.tsx`

- [ ] **Step 1: Write failing test**

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import LeaguePage from "../LeaguePage";
import { browseApi } from "../../services/browse";

vi.mock("../../services/browse");

describe("LeaguePage", () => {
  beforeEach(() => {
    (browseApi.getCompetitions as any).mockResolvedValue([
      { id: 8, name: "Premier League", country: "England" },
    ]);
    (browseApi.getFixtures as any).mockResolvedValue([
      { fixture_id: 1, name: "Arsenal vs Chelsea",
        kickoff_utc: "2026-05-14T20:00:00Z", league: { id: 8, name: "PL" }, closing: 1.72 },
    ]);
    (browseApi.getStandings as any).mockResolvedValue(null);
  });

  it("renders league name and upcoming fixtures", async () => {
    render(
      <MemoryRouter initialEntries={["/league/8"]}>
        <Routes><Route path="/league/:id" element={<LeaguePage />} /></Routes>
      </MemoryRouter>
    );
    await waitFor(() => expect(screen.getByText(/Premier League/)).toBeInTheDocument());
    expect(screen.getByText(/Arsenal/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd frontend && npm test -- src/pages/__tests__/LeaguePage.test.tsx
```

- [ ] **Step 3: Implement `frontend/src/pages/LeaguePage.tsx`**

```tsx
import { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { Typography, Tabs, Table, Alert } from "antd";
import dayjs from "dayjs";
import { browseApi } from "../services/browse";
import type { Competition, Fixture } from "../types/browse";

export default function LeaguePage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const compId = Number(id);
  const [league, setLeague] = useState<Competition | null>(null);
  const [fixtures, setFixtures] = useState<Fixture[]>([]);
  const [standingsUnavailable, setStandingsUnavailable] = useState(false);

  useEffect(() => {
    browseApi.getCompetitions().then((items) => {
      setLeague(items.find((c) => c.id === compId) ?? null);
    });
    const today = dayjs().format("YYYY-MM-DD");
    browseApi.getFixtures({ date: today, competitionId: compId }).then(setFixtures);
    browseApi.getStandings(compId).then((v) => setStandingsUnavailable(v === null));
  }, [compId]);

  return (
    <div style={{ padding: 24 }}>
      <div style={{ color: "#555d72", fontSize: 11, marginBottom: 6 }}>
        <Link to="/">浏览</Link> ▸ {league?.country} ▸ {league?.name}
      </div>
      <Typography.Title level={3}>{league?.name ?? `League ${compId}`}</Typography.Title>
      <Tabs
        items={[
          {
            key: "fixtures", label: "赛程",
            children: (
              <Table
                size="small" rowKey="fixture_id" dataSource={fixtures}
                onRow={(r) => ({ onClick: () => navigate(`/fixture/${r.fixture_id}`), style: { cursor: "pointer" } })}
                pagination={false}
                columns={[
                  { title: "KO", dataIndex: "kickoff_utc",
                    render: (v?: string) => v ? dayjs(v).format("MM-DD HH:mm") : "—" },
                  { title: "对阵", dataIndex: "name" },
                  { title: "赔率", dataIndex: "closing", align: "right",
                    render: (v?: number) => v?.toFixed(2) ?? "—" },
                  { title: "跌水", dataIndex: "drop_percentage", align: "right",
                    render: (v?: number) => v != null ? `${v.toFixed(1)}%` : "—" },
                ]}
              />
            ),
          },
          {
            key: "standings", label: "积分榜",
            children: standingsUnavailable
              ? <Alert type="info" message="此联赛暂无积分榜数据" />
              : <div>加载中...</div>,
          },
        ]}
      />
    </div>
  );
}
```

- [ ] **Step 4: Run — expect PASS**

```bash
cd frontend && npm test -- src/pages/__tests__/LeaguePage.test.tsx
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/LeaguePage.tsx frontend/src/pages/__tests__/LeaguePage.test.tsx
git commit -m "feat(frontend): LeaguePage with fixtures + standings stub"
```

---

## Task 14: TeamPage

**Files:**
- Modify: `frontend/src/pages/TeamPage.tsx`
- Test: `frontend/src/pages/__tests__/TeamPage.test.tsx`

- [ ] **Step 1: Write failing test**

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import TeamPage from "../TeamPage";
import { browseApi } from "../../services/browse";

vi.mock("../../services/browse");

describe("TeamPage", () => {
  beforeEach(() => {
    (browseApi.getTeam as any).mockResolvedValue({
      team_id: 11, name: "Arsenal", goals_for_avg: 2.1, xg_for: 2.24,
    });
  });

  it("renders team header and stats", async () => {
    render(
      <MemoryRouter initialEntries={["/team/11"]}>
        <Routes><Route path="/team/:id" element={<TeamPage />} /></Routes>
      </MemoryRouter>
    );
    await waitFor(() => expect(screen.getByText(/Arsenal/)).toBeInTheDocument());
    expect(screen.getByText(/2\.1/)).toBeInTheDocument();
  });

  it("shows not-found alert when team is null", async () => {
    (browseApi.getTeam as any).mockResolvedValue(null);
    render(
      <MemoryRouter initialEntries={["/team/999"]}>
        <Routes><Route path="/team/:id" element={<TeamPage />} /></Routes>
      </MemoryRouter>
    );
    await waitFor(() => expect(screen.getByText(/未找到/)).toBeInTheDocument());
  });
});
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd frontend && npm test -- src/pages/__tests__/TeamPage.test.tsx
```

- [ ] **Step 3: Implement `frontend/src/pages/TeamPage.tsx`**

```tsx
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Typography, Descriptions, Alert, Spin } from "antd";
import { browseApi } from "../services/browse";
import type { TeamStats } from "../types/browse";

export default function TeamPage() {
  const { id } = useParams<{ id: string }>();
  const [team, setTeam] = useState<TeamStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    browseApi.getTeam(Number(id))
      .then(setTeam)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <Spin />;
  if (!team) return <Alert type="warning" message="球队未找到" />;

  return (
    <div style={{ padding: 24 }}>
      <Typography.Title level={3}>{team.name}</Typography.Title>
      <Descriptions bordered column={2} size="small">
        <Descriptions.Item label="场均进球">{team.goals_for_avg ?? "—"}</Descriptions.Item>
        <Descriptions.Item label="场均失球">{team.goals_against_avg ?? "—"}</Descriptions.Item>
        <Descriptions.Item label="xG (for)">{team.xg_for ?? "—"}</Descriptions.Item>
        <Descriptions.Item label="xG (against)">{team.xg_against ?? "—"}</Descriptions.Item>
      </Descriptions>
    </div>
  );
}
```

- [ ] **Step 4: Run — expect PASS**

```bash
cd frontend && npm test -- src/pages/__tests__/TeamPage.test.tsx
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/TeamPage.tsx frontend/src/pages/__tests__/TeamPage.test.tsx
git commit -m "feat(frontend): TeamPage with stats"
```

---

## Task 15: AnalysisReportsPage

**Files:**
- Modify: `frontend/src/pages/AnalysisReportsPage.tsx`
- Test: `frontend/src/pages/__tests__/AnalysisReportsPage.test.tsx`

- [ ] **Step 1: Write failing test**

```tsx
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import AnalysisReportsPage from "../AnalysisReportsPage";
import { browseApi } from "../../services/browse";

vi.mock("../../services/browse");

describe("AnalysisReportsPage", () => {
  beforeEach(() => {
    (browseApi.getAnalysisRecent as any).mockResolvedValue([
      { fixture_id: 1, name: "Arsenal vs Chelsea",
        analysis: { pick: "H", ev: 0.064, confidence_stars: 4,
                    model_prob: { H: 0.62, D: 0.2, A: 0.18 },
                    market_prob: { H: null, D: null, A: null }, analyzed_at: "" } },
    ]);
    (browseApi.runAnalysis as any).mockResolvedValue({ run_id: "0099", status: "started" });
  });

  it("loads recent analyses", async () => {
    render(<MemoryRouter><AnalysisReportsPage /></MemoryRouter>);
    await waitFor(() => expect(screen.getByText(/Arsenal/)).toBeInTheDocument());
  });

  it("triggers run on button click", async () => {
    render(<MemoryRouter><AnalysisReportsPage /></MemoryRouter>);
    fireEvent.click(screen.getByText(/触发新一轮/));
    await waitFor(() => expect(browseApi.runAnalysis).toHaveBeenCalled());
  });
});
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd frontend && npm test -- src/pages/__tests__/AnalysisReportsPage.test.tsx
```

- [ ] **Step 3: Implement `frontend/src/pages/AnalysisReportsPage.tsx`**

```tsx
import { useEffect, useState } from "react";
import { Button, Table, Typography, message } from "antd";
import { useNavigate } from "react-router-dom";
import { browseApi } from "../services/browse";
import AnalysisBadge from "../components/AnalysisBadge";

interface Row {
  fixture_id: number;
  name?: string;
  analysis: any;
}

export default function AnalysisReportsPage() {
  const navigate = useNavigate();
  const [rows, setRows] = useState<Row[]>([]);
  const [running, setRunning] = useState(false);

  const load = () => browseApi.getAnalysisRecent(50).then((items) => setRows(items as Row[]));
  useEffect(() => { load(); }, []);

  const trigger = async () => {
    setRunning(true);
    try {
      const r = await browseApi.runAnalysis();
      message.success(`分析已触发 (run_id=${r.run_id})`);
      setTimeout(load, 2000);
    } catch (e) {
      message.error(`触发失败: ${e}`);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <Typography.Title level={3}>📊 自研分析报告</Typography.Title>
        <Button type="primary" onClick={trigger} loading={running}>▶ 触发新一轮</Button>
      </div>
      <Table
        size="small" rowKey="fixture_id" dataSource={rows}
        onRow={(r) => ({ onClick: () => navigate(`/fixture/${r.fixture_id}`), style: { cursor: "pointer" } })}
        columns={[
          { title: "比赛", dataIndex: "name", render: (v?: string, r) => v ?? `Fixture ${r.fixture_id}` },
          { title: "推荐", dataIndex: ["analysis", "pick"] },
          { title: "EV", dataIndex: ["analysis", "ev"],
            render: (v?: number) => v != null ? `${(v * 100).toFixed(1)}%` : "—" },
          { title: "置信",
            render: (_, r) => <AnalysisBadge ev={r.analysis?.ev} stars={r.analysis?.confidence_stars} pick={r.analysis?.pick} /> },
        ]}
      />
    </div>
  );
}
```

- [ ] **Step 4: Run — expect PASS**

```bash
cd frontend && npm test -- src/pages/__tests__/AnalysisReportsPage.test.tsx
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/AnalysisReportsPage.tsx frontend/src/pages/__tests__/AnalysisReportsPage.test.tsx
git commit -m "feat(frontend): AnalysisReportsPage with trigger button"
```

---

## Task 16: Favorites store + FavoritesPage + BetHistoryPage

**Files:**
- Create: `frontend/src/store/favorites.ts`
- Modify: `frontend/src/pages/FavoritesPage.tsx`
- Modify: `frontend/src/pages/BetHistoryPage.tsx`
- Test: `frontend/src/store/__tests__/favorites.test.ts`

- [ ] **Step 1: Write failing test**

```typescript
import { describe, it, expect, beforeEach } from "vitest";
import { useFavorites } from "../favorites";

describe("favorites store", () => {
  beforeEach(() => {
    localStorage.clear();
    useFavorites.setState({ fixtures: [], leagues: [], teams: [] });
  });

  it("adds and removes fixture favorite", () => {
    useFavorites.getState().toggleFixture(1);
    expect(useFavorites.getState().fixtures).toContain(1);
    useFavorites.getState().toggleFixture(1);
    expect(useFavorites.getState().fixtures).not.toContain(1);
  });

  it("persists to localStorage", () => {
    useFavorites.getState().toggleLeague(8);
    const raw = localStorage.getItem("goalcast.favorites");
    expect(raw).toContain("8");
  });
});
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd frontend && npm test -- src/store/__tests__/favorites.test.ts
```

- [ ] **Step 3: Implement `frontend/src/store/favorites.ts`**

```typescript
import { create } from "zustand";
import { persist } from "zustand/middleware";

interface FavoritesState {
  fixtures: number[];
  leagues: number[];
  teams: number[];
  toggleFixture: (id: number) => void;
  toggleLeague: (id: number) => void;
  toggleTeam: (id: number) => void;
}

function toggle(arr: number[], id: number): number[] {
  return arr.includes(id) ? arr.filter((v) => v !== id) : [...arr, id];
}

export const useFavorites = create<FavoritesState>()(
  persist(
    (set) => ({
      fixtures: [],
      leagues: [],
      teams: [],
      toggleFixture: (id) => set((s) => ({ fixtures: toggle(s.fixtures, id) })),
      toggleLeague: (id) => set((s) => ({ leagues: toggle(s.leagues, id) })),
      toggleTeam: (id) => set((s) => ({ teams: toggle(s.teams, id) })),
    }),
    { name: "goalcast.favorites" },
  ),
);
```

- [ ] **Step 4: Implement `frontend/src/pages/FavoritesPage.tsx`**

```tsx
import { Tabs, Empty, Typography } from "antd";
import { Link } from "react-router-dom";
import { useFavorites } from "../store/favorites";

export default function FavoritesPage() {
  const { fixtures, leagues, teams } = useFavorites();
  return (
    <div style={{ padding: 24 }}>
      <Typography.Title level={3}>⭐ 我的关注</Typography.Title>
      <Tabs
        items={[
          {
            key: "fixtures", label: `关注比赛 (${fixtures.length})`,
            children: fixtures.length === 0 ? <Empty /> : (
              <ul>{fixtures.map((id) => <li key={id}><Link to={`/fixture/${id}`}>Fixture #{id}</Link></li>)}</ul>
            ),
          },
          {
            key: "leagues", label: `关注联赛 (${leagues.length})`,
            children: leagues.length === 0 ? <Empty /> : (
              <ul>{leagues.map((id) => <li key={id}><Link to={`/league/${id}`}>League #{id}</Link></li>)}</ul>
            ),
          },
          {
            key: "teams", label: `关注球队 (${teams.length})`,
            children: teams.length === 0 ? <Empty /> : (
              <ul>{teams.map((id) => <li key={id}><Link to={`/team/${id}`}>Team #{id}</Link></li>)}</ul>
            ),
          },
          { key: "bets", label: "下注记录", children: <Link to="/my/bets">查看下注记录 →</Link> },
        ]}
      />
    </div>
  );
}
```

- [ ] **Step 5: Implement `frontend/src/pages/BetHistoryPage.tsx`**

```tsx
import { Typography, Alert, Table } from "antd";

export default function BetHistoryPage() {
  return (
    <div style={{ padding: 24 }}>
      <Typography.Title level={3}>📒 下注记录</Typography.Title>
      <Alert type="info" message="下注记录持久化将在后续版本接入；当前为占位。" />
      <Table
        size="small" style={{ marginTop: 12 }} dataSource={[]} rowKey="id"
        locale={{ emptyText: "暂无下注" }}
        columns={[
          { title: "日期", dataIndex: "date" },
          { title: "比赛", dataIndex: "match" },
          { title: "市场", dataIndex: "market" },
          { title: "赔率", dataIndex: "odds" },
          { title: "盈亏", dataIndex: "pnl" },
        ]}
      />
    </div>
  );
}
```

- [ ] **Step 6: Run — expect PASS**

```bash
cd frontend && npm test -- src/store/__tests__/favorites.test.ts
```

- [ ] **Step 7: Commit**

```bash
git add frontend/src/store/favorites.ts frontend/src/store/__tests__/ frontend/src/pages/FavoritesPage.tsx frontend/src/pages/BetHistoryPage.tsx
git commit -m "feat(frontend): favorites store + FavoritesPage + BetHistoryPage stub"
```

---

## Task 17: SettingsPage

**Files:**
- Modify: `frontend/src/pages/SettingsPage.tsx`
- Test: `frontend/src/pages/__tests__/SettingsPage.test.tsx`

- [ ] **Step 1: Write failing test**

```tsx
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { MemoryRouter } from "react-router-dom";
import SettingsPage from "../SettingsPage";

describe("SettingsPage", () => {
  it("renders settings sections", () => {
    render(<MemoryRouter><SettingsPage /></MemoryRouter>);
    expect(screen.getByText(/OddAlerts API/)).toBeInTheDocument();
    expect(screen.getByText(/分析参数/)).toBeInTheDocument();
    expect(screen.getByText(/Kelly/i)).toBeInTheDocument();
  });

  it("legacy section shows deletion label", () => {
    render(<MemoryRouter><SettingsPage /></MemoryRouter>);
    expect(screen.getByText(/FootyStats/)).toBeInTheDocument();
    expect(screen.getAllByText(/已删除/).length).toBeGreaterThan(0);
  });
});
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd frontend && npm test -- src/pages/__tests__/SettingsPage.test.tsx
```

- [ ] **Step 3: Implement `frontend/src/pages/SettingsPage.tsx`**

```tsx
import { Typography, Card, Form, Input, InputNumber, Alert, Tag, Space } from "antd";

export default function SettingsPage() {
  return (
    <div style={{ padding: 24, maxWidth: 900 }}>
      <Typography.Title level={3}>⚙️ 设置</Typography.Title>

      <Card title="🔌 OddAlerts API" style={{ marginBottom: 14 }}>
        <Form layout="vertical">
          <Form.Item label="API Token" extra="从 OddAlerts 控制台获取，单点配额 300 req/min">
            <Input.Password placeholder="oa_xxxxxxxxxxxxxxxx" />
          </Form.Item>
          <Form.Item label="速率上限 (req/min)">
            <InputNumber defaultValue={280} min={1} max={300} />
          </Form.Item>
        </Form>
      </Card>

      <Card title="🎯 分析参数" style={{ marginBottom: 14 }}>
        <Form layout="vertical">
          <Form.Item label="概率混合权重 (Poisson / OddAlerts trends / 市场, 和=1)">
            <Space>
              <InputNumber defaultValue={0.5} min={0} max={1} step={0.1} />
              <InputNumber defaultValue={0.4} min={0} max={1} step={0.1} />
              <InputNumber defaultValue={0.1} min={0} max={1} step={0.1} />
            </Space>
          </Form.Item>
          <Form.Item label="最低 EV 阈值 (%)">
            <InputNumber defaultValue={2.0} min={0} step={0.5} />
          </Form.Item>
          <Form.Item label="最低置信度 (星)">
            <InputNumber defaultValue={3} min={0} max={5} />
          </Form.Item>
        </Form>
      </Card>

      <Card title="💰 资金 / Kelly" style={{ marginBottom: 14 }}>
        <Form layout="vertical">
          <Form.Item label="基准 Bankroll (u)">
            <InputNumber defaultValue={100} min={1} />
          </Form.Item>
          <Form.Item label="Kelly 分数">
            <InputNumber defaultValue={0.25} min={0.05} max={1} step={0.05} />
          </Form.Item>
          <Form.Item label="单注上限 (u)">
            <InputNumber defaultValue={3.0} min={0.1} step={0.5} />
          </Form.Item>
        </Form>
      </Card>

      <Card title="⚠ Legacy 数据源 (只读)" style={{ marginBottom: 14 }}>
        <Alert type="warning" showIcon
               message="以下数据源已在 2026-05-14 架构升级中删除，不可重新启用。" />
        <div style={{ marginTop: 12 }}>
          <Tag>FootyStats</Tag><Tag>Sportmonks</Tag><Tag>Understat</Tag>
          <span style={{ marginLeft: 10, color: "#555d72" }}>已删除 · 已删除 · 已删除</span>
        </div>
      </Card>
    </div>
  );
}
```

- [ ] **Step 4: Run — expect PASS**

```bash
cd frontend && npm test -- src/pages/__tests__/SettingsPage.test.tsx
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/SettingsPage.tsx frontend/src/pages/__tests__/SettingsPage.test.tsx
git commit -m "feat(frontend): SettingsPage with API/analytics/Kelly/legacy sections"
```

---

## Task 18: MobileTabBar + responsive breakpoints

**Files:**
- Modify: `frontend/src/components/MobileTabBar.tsx`
- Modify: `frontend/src/index.css`
- Test: `frontend/src/components/__tests__/MobileTabBar.test.tsx`

- [ ] **Step 1: Write failing test**

```tsx
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect } from "vitest";
import MobileTabBar from "../MobileTabBar";

describe("MobileTabBar", () => {
  it("renders 5 tabs", () => {
    render(<MemoryRouter><MobileTabBar /></MemoryRouter>);
    expect(screen.getByText(/浏览/)).toBeInTheDocument();
    expect(screen.getByText(/跌水/)).toBeInTheDocument();
    expect(screen.getByText(/趋势/)).toBeInTheDocument();
    expect(screen.getByText(/推荐/)).toBeInTheDocument();
    expect(screen.getByText(/我的/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd frontend && npm test -- src/components/__tests__/MobileTabBar.test.tsx
```

- [ ] **Step 3: Implement `frontend/src/components/MobileTabBar.tsx`**

```tsx
import { NavLink } from "react-router-dom";
import {
  HomeOutlined, FireOutlined, LineChartOutlined,
  BarChartOutlined, UserOutlined,
} from "@ant-design/icons";

const tabs = [
  { to: "/", label: "浏览", icon: <HomeOutlined /> },
  { to: "/dropping", label: "跌水", icon: <FireOutlined /> },
  { to: "/trends/home_win", label: "趋势", icon: <LineChartOutlined /> },
  { to: "/analysis", label: "推荐", icon: <BarChartOutlined /> },
  { to: "/my", label: "我的", icon: <UserOutlined /> },
];

export default function MobileTabBar() {
  return (
    <div className="mobile-tabbar">
      {tabs.map((t) => (
        <NavLink key={t.to} to={t.to} end={t.to === "/"}
                 className={({ isActive }) => `tab ${isActive ? "on" : ""}`}>
          <div className="ico">{t.icon}</div>
          <div className="label">{t.label}</div>
        </NavLink>
      ))}
    </div>
  );
}
```

- [ ] **Step 4: Append responsive CSS to `frontend/src/index.css`**

```css
.mobile-tabbar { display:none; }
@media (max-width: 768px) {
  .goalcast-sider, .goalcast-aside { display:none; }
  .fixture-grid { grid-template-columns:1fr; }
  .filters { gap:6px; }
  .mobile-tabbar {
    display:flex; position:fixed; bottom:0; left:0; right:0;
    background:#0b0d17; border-top:1px solid rgba(255,255,255,0.07);
    padding:8px 0 14px; z-index:50;
  }
  .mobile-tabbar .tab {
    flex:1; text-align:center; color:#555d72; font-size:10px; text-decoration:none;
  }
  .mobile-tabbar .tab.on { color:#00FF9D; }
  .mobile-tabbar .tab .ico { font-size:18px; display:block; margin-bottom:2px; }
  .goalcast-content { padding-bottom:72px; }
  .fdp-hero { flex-direction:column; }
}
```

- [ ] **Step 5: Run — expect PASS**

```bash
cd frontend && npm test -- src/components/__tests__/MobileTabBar.test.tsx
```

- [ ] **Step 6: Manual mobile preview**

```bash
cd frontend && npm run dev
```
Open browser DevTools, switch to mobile 390×844. Verify:
- Sider hides; MobileTabBar appears
- Fixture cards single-column
- Hero stacks vertically on `/fixture/:id`

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/MobileTabBar.tsx frontend/src/components/__tests__/MobileTabBar.test.tsx frontend/src/index.css
git commit -m "feat(frontend): MobileTabBar + responsive breakpoints"
```

---

## Task 19: Legacy cleanup (move + delete)

**Files:**
- Move legacy files into `pages/legacy/`
- Modify: `frontend/src/App.tsx` (update legacy import paths)

- [ ] **Step 1: Create legacy directory + move files**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast/frontend/src
mkdir -p pages/legacy
git mv pages/DashboardPage.tsx pages/legacy/DashboardPage.tsx
git mv pages/BoardPage.tsx pages/legacy/BoardPage.tsx
git mv pages/TokenStatsPage.tsx pages/legacy/TokenStatsPage.tsx
git mv pages/ChatPanel.tsx pages/legacy/ChatPanel.tsx
git mv components/MatchSourcePanel.tsx pages/legacy/MatchSourcePanel.tsx
git mv components/AgentDetailDrawer.tsx pages/legacy/AgentDetailDrawer.tsx
```

`PipelineMonitor.tsx` stays in `pages/` (still reachable at `/analysis/pipeline`).

- [ ] **Step 2: Update import paths in `App.tsx`**

Change in `frontend/src/App.tsx`:
```tsx
import BoardPage from "./pages/BoardPage";
import DashboardPage from "./pages/DashboardPage";
import TokenStatsPage from "./pages/TokenStatsPage";
import ChatPanel from "./pages/ChatPanel";
```
to:
```tsx
import BoardPage from "./pages/legacy/BoardPage";
import DashboardPage from "./pages/legacy/DashboardPage";
import TokenStatsPage from "./pages/legacy/TokenStatsPage";
import ChatPanel from "./pages/legacy/ChatPanel";
```

- [ ] **Step 3: Find lingering references**

```bash
cd frontend && grep -rn "components/MatchSourcePanel\|components/AgentDetailDrawer\|pages/BoardPage\|pages/DashboardPage\|pages/ChatPanel\|pages/TokenStatsPage" src
```
For each hit (excluding `pages/legacy/...`), update to `pages/legacy/<file>` or delete the dead import.

- [ ] **Step 4: TypeScript + tests + lint + build**

```bash
cd frontend
npx tsc -b --noEmit
npm test
npm run lint
npm run build
```
All four must succeed.

- [ ] **Step 5: Commit**

```bash
git add -A frontend
git commit -m "refactor(frontend): move legacy pages to pages/legacy/"
```

---

## Task 20: README + final E2E verification

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update root `README.md`**

Open `README.md`. Replace the "Multi-provider data sources" feature bullet with:
```markdown
- **OddAlerts data source** — single-provider design with sqlite cache + token-bucket rate limit
- **Browse-first UI** — fixtures, dropping odds, trends, league/team pages; responsive web + mobile
- **In-house analysis preserved** — Poisson + EV + confidence, fed by OddAlerts stats/trends; agent RD loop continues to write `match_store`
```
Adjust the "Quick start" / install section so the only API key needed is `ODDALERTS_API_KEY`. Remove any FootyStats / Sportmonks / Understat env vars.

- [ ] **Step 2: Backend + frontend smoke tests**

```bash
cd backend && python -m pytest 2>&1 | tail -5
cd ../frontend && npm test 2>&1 | tail -5
```
Both must show 0 failures.

- [ ] **Step 3: Dev-stack E2E walkthrough**

Terminal 1:
```bash
cd backend && python main.py --provider anthropic --base-url <BASE_URL> --api-key <KEY> run
```
Terminal 2:
```bash
cd frontend && npm run dev
```
Open the printed URL. Verify each route:
- `/` shows competitions in the left tree, today's fixture cards in the main area
- Click a fixture → drawer opens with analysis badge
- "查看完整页面" → `/fixture/:id` renders Hero + KPI + tabs
- `/dropping` shows table with drop badges
- `/trends/home_win` shows top fixtures
- `/league/8` shows fixtures + standings stub
- `/team/11` shows stats
- `/analysis` shows recent runs; triggering "▶ 触发新一轮" fires `POST /api/analysis/run`
- `/my` and `/settings` render
- `/legacy/board` still renders (smoke backwards-compatibility)
- Resize to 390 px wide → MobileTabBar appears at bottom; layout stacks

- [ ] **Step 4: Commit README**

```bash
git add README.md
git commit -m "docs: update README for OddAlert-only architecture"
```

- [ ] **Step 5: (Optional) Tag the milestone**

```bash
git tag v2.0.0-pivot-complete
```

---

## Self-Review

**Spec coverage (§4 pages → tasks):**
- §4.1 BettingPage — Tasks 4, 6, 7, 8
- §4.2 FixtureDetailPage — Task 10 (Hero + KPI + market depth + stats + H2H)
- §4.3 DroppingOddsPage — Task 11
- §4.4 TrendsPage — Task 12
- §4.5 LeaguePage — Task 13
- §4.6 TeamPage — Task 14
- §4.7 AnalysisReportsPage — Task 15
- §4.8 PipelineMonitor — preserved as-is (no task)
- §4.9 FavoritesPage + BetHistoryPage — Task 16
- §4.10 SettingsPage — Task 17
- §4.11 Mobile responsive — Task 18

**Spec §5 component inventory:**
- LeagueTree=Task 4, FixtureCard=Task 6, FixtureDetailDrawer=Task 8, OddsCurveChart=Task 9, MarketDepthTable/StatsCompare/H2HTable=Task 10, AnalysisBadge=Task 5, MobileTabBar=Task 18.
- `StandingsTable.tsx` from spec is currently inlined into `LeaguePage`; if a second consumer appears, extract then. Acceptance criteria explicitly only require the standings stub, so this is acceptable for MVP.

**Spec §6 Phase mapping:**
- Phase 5 (骨架) — Tasks 1-3, 7
- Phase 6 (主流程) — Tasks 4-10
- Phase 7 (列表与榜单) — Tasks 11, 12. Card vs list toggle is currently single-state (cards); to add a real list view, extend Task 7's `Segmented` and split the render block — note above for follow-up.
- Phase 8 (联赛/球队/分析/我的/设置) — Tasks 13-17
- Phase 9 (移动端) — Task 18
- Phase 10 (清理) — Tasks 19-20

**Type consistency:**
- `Competition`, `Fixture`, `FixtureDetail`, `AnalysisRecord`, `TrendItem`, `DroppingOdd`, `TeamStats` (Task 1) are referenced unchanged in Tasks 4, 6, 8, 10, 11-15.
- `browseApi` method names (`getCompetitions`, `getFixtures`, `getFixtureDetail`, `getTrends`, `getDropping`, `getTeam`, `getStandings`, `getAnalysisRecent`, `runAnalysis`) appear identically in Task 1 service + every page test mock.
- `AnalysisBadge` props (`ev`, `stars`, `pick`) identical across Tasks 5, 6, 8, 10, 15.

**Caveats fixed inline:**
- `MobileTabBar` stub introduced in Task 3 so `AppLayout` compiles; real implementation in Task 18.
- `FixtureDetailDrawer` stub introduced in Task 7 so `BettingPage` compiles; real implementation in Task 8.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-14-frontend-pivot-plan.md`. Two execution options:

**1. Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks. Suits this plan's 20 isolated tasks.

**2. Inline Execution** — execute tasks in this session using `superpowers:executing-plans`, batch with checkpoints.

**Prerequisite:** Plan 1 (`2026-05-14-backend-pivot-plan.md`) must be merged before Task 1 of this plan runs (the `/api/*` endpoints must exist for integration to pass).

**Which approach?**

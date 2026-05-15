# Goalcast UI Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace all inline-style React components with the approved v6 CSS design system across all 6 pages.

**Architecture:** Extract the full design system CSS from the mockup HTML into `index.css`. All components switch from `style={{}}` to `className`. No new npm deps; Tailwind remains installed but is not used for the new classes. TypeScript type-check (`npm run typecheck`) is the validation gate after each task.

**Tech Stack:** React 18, TypeScript, React Router v6, TanStack Query v5, TanStack Virtual v3, Zustand v4, Vite

---

## File Map

| File | Action | Responsible for |
|------|--------|-----------------|
| `frontend/src/index.css` | Overwrite | Full design system CSS |
| `frontend/src/components/layout/Sidebar.tsx` | Overwrite | Gradient logo, icon nav, sync status |
| `frontend/src/components/layout/Layout.tsx` | Minor edit | Remove inline style, add `className="layout"` |
| `frontend/src/components/match/ProbBar.tsx` | Overwrite | className-based prob bar |
| `frontend/src/components/match/MatchCard.tsx` | Overwrite | Full v6 card structure |
| `frontend/src/pages/Matches.tsx` | Overwrite | Inline filters + league grouping |
| `frontend/src/pages/Dashboard.tsx` | Overwrite | Stat cards + alert cards + featured matches |
| `frontend/src/pages/MatchDetail.tsx` | Overwrite | Hero + 2-col detail grid |
| `frontend/src/pages/ValueBets.tsx` | Overwrite | Ranked vb-card list |
| `frontend/src/pages/DroppingOdds.tsx` | Overwrite | do-card list with odds track |
| `frontend/src/pages/History.tsx` | Overwrite | hist-table + filter chips |
| `frontend/src/components/filters/DateFilter.tsx` | Delete | Inlined into Matches.tsx |
| `frontend/src/components/filters/LeagueFilter.tsx` | Delete | Inlined into Matches.tsx |
| `frontend/src/components/match/MatchCardGrid.tsx` | Delete | Replaced by league-grouped grid in Matches.tsx |

---

## Task 1: Design System CSS

**Files:**
- Overwrite: `frontend/src/index.css`

- [ ] **Step 1: Replace index.css with full design system**

```css
/* frontend/src/index.css */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #060d1a; color: #e2e8f0; font-family: -apple-system, 'Inter', sans-serif; font-size: 13px; }

/* ── Layout ── */
.layout { display: flex; min-height: 100vh; }
.main { flex: 1; overflow: auto; background: #070e1c; }
.page-header { padding: 18px 24px 14px; border-bottom: 1px solid #1e293b; display: flex; align-items: center; justify-content: space-between; }
.page-title { font-size: 18px; font-weight: 700; color: #f1f5f9; }
.page-subtitle { font-size: 12px; color: #475569; margin-top: 2px; }

/* ── Sidebar ── */
.sidebar { width: 180px; min-width: 180px; background: #0a1628; border-right: 1px solid #1e3a5f; padding: 20px 0; display: flex; flex-direction: column; }
.sidebar-logo { padding: 0 16px 20px; display: flex; align-items: center; gap: 10px; border-bottom: 1px solid #1e293b; margin-bottom: 12px; }
.logo-icon { width: 28px; height: 28px; background: linear-gradient(135deg, #3b82f6, #22c55e); border-radius: 7px; display: flex; align-items: center; justify-content: center; font-size: 14px; }
.logo-text { font-size: 15px; font-weight: 700; color: #f1f5f9; }
.nav-item { display: flex; align-items: center; gap: 10px; padding: 9px 16px; font-size: 13px; color: #64748b; margin: 1px 8px; border-radius: 6px; cursor: pointer; text-decoration: none; }
.nav-item.active { background: #22c55e15; color: #22c55e; }
.nav-item:hover:not(.active) { background: #1e293b; color: #94a3b8; }
.nav-section { padding: 8px 16px 4px; font-size: 10px; color: #334155; text-transform: uppercase; letter-spacing: 1px; margin-top: 8px; }
.nav-spacer { flex: 1; }
.sync-status { padding: 10px 16px; font-size: 11px; color: #334155; display: flex; align-items: center; gap: 6px; }
.sync-dot { width: 6px; height: 6px; border-radius: 50%; background: #22c55e; }

/* ── Buttons / Controls ── */
.btn { padding: 5px 12px; border-radius: 6px; font-size: 12px; cursor: pointer; }
.btn-primary { background: #3b82f622; color: #3b82f6; border: 1px solid #3b82f633; }
.btn-secondary { background: #1e293b; color: #94a3b8; border: 1px solid #1a2d47; }

/* ── Chips & Pills ── */
.chip { padding: 4px 13px; border-radius: 6px; font-size: 12px; font-weight: 500; cursor: pointer; border: 1px solid #1e3a5f; background: #0f1d30; color: #64748b; transition: all .15s; white-space: nowrap; }
.chip.active { background: #22c55e22; border-color: #22c55e55; color: #22c55e; font-weight: 700; }
.pill { padding: 3px 11px; border-radius: 20px; font-size: 11px; cursor: pointer; border: 1px solid #1e3a5f; background: #0f1d30; color: #64748b; transition: all .12s; white-space: nowrap; }
.pill.sel { background: #3b82f622; border-color: #3b82f655; color: #60a5fa; }
.pill.all-pill { background: #22c55e22; border-color: #22c55e55; color: #22c55e; font-weight: 600; }
.sort-select { background: #0f1d30; border: 1px solid #1e3a5f; border-radius: 6px; padding: 4px 10px; color: #94a3b8; font-size: 12px; outline: none; }

/* ── Badges ── */
.badge { display: inline-flex; align-items: center; padding: 2px 6px; border-radius: 4px; font-size: 9px; font-weight: 600; white-space: nowrap; }
.bg { background: #22c55e1a; color: #22c55e; border: 1px solid #22c55e33; }
.ba { background: #f59e0b1a; color: #f59e0b; border: 1px solid #f59e0b33; }
.bb { background: #3b82f61a; color: #3b82f6; border: 1px solid #3b82f633; }
.bp { background: #a855f71a; color: #a855f7; border: 1px solid #a855f733; }
.br { background: #ef44441a; color: #ef4444; border: 1px solid #ef444433; }

/* ── Filters ── */
.filter-section { padding: 12px 24px; border-bottom: 1px solid #1e293b; display: flex; flex-direction: column; gap: 10px; }
.filter-row { display: flex; align-items: flex-start; gap: 10px; flex-wrap: wrap; }
.filter-lbl { font-size: 10px; color: #475569; text-transform: uppercase; letter-spacing: .5px; width: 36px; flex-shrink: 0; padding-top: 6px; }
.date-native { background: #0f1d30; border: 1px solid #3b82f655; border-radius: 6px; padding: 4px 10px; color: #3b82f6; font-size: 12px; outline: none; font-weight: 600; }
.continent-block { margin-bottom: 6px; }
.continent-label { font-size: 10px; color: #475569; text-transform: uppercase; letter-spacing: .8px; margin-bottom: 5px; }
.league-pills { display: flex; gap: 5px; flex-wrap: wrap; }
.sort-row { display: flex; align-items: center; gap: 8px; }
.result-info { margin-left: auto; font-size: 12px; color: #475569; }
.result-info em { color: #22c55e; font-style: normal; font-weight: 700; }

/* ── Match Grid ── */
.matches-area { padding: 16px 24px; }
.league-group { margin-bottom: 24px; }
.league-title { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.league-name { font-size: 13px; font-weight: 700; color: #94a3b8; }
.league-count { font-size: 11px; color: #334155; background: #1e293b; padding: 1px 8px; border-radius: 10px; }
.match-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }

/* ── Match Card v6 ── */
.mcard { background: #0d1626; border: 1px solid #1a2d47; border-radius: 10px; overflow: hidden; cursor: pointer; transition: border-color .15s, box-shadow .15s; }
.mcard:hover { border-color: #3b82f644; box-shadow: 0 4px 20px #3b82f60d; }
.mcard.live { border-color: #22c55e44; }

.mc-hdr { display: flex; align-items: center; justify-content: space-between; padding: 6px 12px; background: #09111f; border-bottom: 1px solid #1e293b; }
.mc-hdr-lname { font-size: 11px; color: #64748b; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 120px; }
.mc-hdr-time { font-size: 14px; font-weight: 700; color: #e2e8f0; }
.mc-status { font-size: 9px; padding: 2px 6px; border-radius: 4px; font-weight: 700; letter-spacing: .5px; }
.st-pre  { background: #1e293b; color: #475569; }
.st-live { background: #22c55e25; color: #22c55e; border: 1px solid #22c55e44; animation: pulse 2s infinite; }
.st-ft   { background: #0f1d30; color: #334155; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.65} }
@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }

.mc-body { display: flex; align-items: stretch; padding: 10px 12px 8px; }
.mc-team { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 5px; }
.mc-team.home { align-items: flex-end; padding-right: 8px; border-right: 1px solid #1a2d47; }
.mc-team.away { align-items: flex-start; padding-left: 8px; }

.t-namerow { display: flex; align-items: center; gap: 7px; }
.mc-team.home .t-namerow { flex-direction: row-reverse; }
.t-abbr { width: 28px; height: 28px; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 9px; font-weight: 800; color: #fff; flex-shrink: 0; letter-spacing: -.5px; }
.t-fullname { font-size: 13px; font-weight: 700; color: #f1f5f9; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 95px; }

.t-record { display: flex; align-items: center; gap: 4px; }
.mc-team.home .t-record { justify-content: flex-end; }
.t-pos { font-size: 10px; color: #60a5fa; font-weight: 700; }
.t-wdl { font-size: 10px; color: #334155; }
.t-wdl .w { color: #22c55e; } .t-wdl .d { color: #64748b; } .t-wdl .l { color: #ef4444; }

.t-goals { display: flex; align-items: center; gap: 5px; font-size: 11px; }
.mc-team.home .t-goals { justify-content: flex-end; }
.g-for { color: #22c55e; font-weight: 700; }
.g-sep { color: #2d4a6e; font-size: 9px; }
.g-ag  { color: #ef444488; font-weight: 700; }
.g-avg { font-size: 9px; color: #2d4a6e; }

.t-form { display: flex; gap: 2px; }
.mc-team.home .t-form { justify-content: flex-end; }
.fp { width: 16px; height: 16px; border-radius: 3px; font-size: 8px; font-weight: 800; display: flex; align-items: center; justify-content: center; }
.fp.W { background: #22c55e22; color: #22c55e; border: 1px solid #22c55e44; }
.fp.D { background: #47556922; color: #64748b; border: 1px solid #47556944; }
.fp.L { background: #ef444422; color: #ef4444; border: 1px solid #ef444444; }

.t-winpct { font-size: 19px; font-weight: 900; line-height: 1; }
.t-winpct.h { color: #22c55e; }
.t-winpct.a { color: #f59e0b; }
.t-winlbl { font-size: 9px; color: #334155; }

.mc-center { width: 54px; flex-shrink: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 3px; padding: 0 4px; }
.mc-vs-txt { font-size: 9px; color: #1e3a5f; letter-spacing: 3px; font-weight: 700; }
.mc-score { font-size: 22px; font-weight: 900; color: #f1f5f9; line-height: 1; }
.mc-draw { font-size: 12px; font-weight: 700; color: #64748b; line-height: 1; }
.mc-drawlbl { font-size: 9px; color: #334155; }
.mc-divider { width: 100%; height: 1px; background: #1a2d47; margin: 4px 0; }
.mc-h2h { font-size: 9px; color: #475569; text-align: center; line-height: 1.5; }
.mc-h2h span { color: #64748b; }

.mc-probbar { padding: 0 12px 8px; }
.pb-wrap { height: 4px; border-radius: 2px; background: #1e293b; overflow: hidden; display: flex; }
.pb-home { background: #22c55e; border-radius: 2px 0 0 2px; }
.pb-draw { background: #475569; }
.pb-away { background: #f59e0b; border-radius: 0 2px 2px 0; flex: 1; }
.pb-labels { display: flex; justify-content: space-between; margin-top: 4px; }
.pbl { font-size: 9px; color: #334155; }
.pbl .h { color: #22c55e; } .pbl .a { color: #f59e0b; }

.mc-ftr { border-top: 1px solid #1e293b; padding: 7px 12px; display: flex; align-items: center; gap: 5px; background: #09111f; }
.odds-box { display: flex; gap: 3px; flex-shrink: 0; }
.ob { background: #1a2d47; border-radius: 5px; padding: 4px 7px; text-align: center; min-width: 42px; }
.ob.hot { background: #22c55e18; border: 1px solid #22c55e44; }
.ob .ol { font-size: 9px; color: #334155; margin-bottom: 1px; }
.ob .ov { font-size: 12px; font-weight: 700; color: #e2e8f0; }
.ob.hot .ov { color: #22c55e; }
.ftr-sep { width: 1px; height: 28px; background: #1a2d47; margin: 0 3px; flex-shrink: 0; }
.drop-col { text-align: center; flex-shrink: 0; min-width: 46px; }
.drop-val { font-size: 15px; font-weight: 800; color: #22c55e; line-height: 1; }
.drop-mkt { font-size: 9px; color: #475569; }
.badges { display: flex; flex-wrap: wrap; gap: 3px; margin-left: auto; justify-content: flex-end; align-items: center; }

/* ── Dashboard ── */
.stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; padding: 20px 28px; }
.stat-card { background: #0d1626; border: 1px solid #1a2d47; border-radius: 10px; padding: 16px 20px; }
.stat-label { font-size: 11px; color: #475569; text-transform: uppercase; letter-spacing: .5px; }
.stat-value { font-size: 28px; font-weight: 900; color: #f1f5f9; line-height: 1; margin: 6px 0 2px; }
.stat-sub { font-size: 11px; }
.dash-section { padding: 0 28px 24px; }
.dash-section-title { font-size: 13px; font-weight: 700; color: #64748b; margin-bottom: 10px; padding: 12px 0 0; }
.dash-2col { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 4px; }
.alert-card { background: #0d1626; border: 1px solid #1a2d47; border-radius: 10px; padding: 14px 16px; display: flex; align-items: flex-start; gap: 12px; }
.alert-icon { width: 34px; height: 34px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 14px; flex-shrink: 0; }
.alert-match { font-size: 13px; font-weight: 700; color: #f1f5f9; }
.alert-detail { font-size: 11px; color: #475569; margin-top: 2px; }
.alert-tags { display: flex; gap: 4px; flex-wrap: wrap; margin-top: 6px; }

/* ── Match Detail ── */
.detail-area { padding: 20px 28px; }
.detail-hero { background: #0d1626; border: 1px solid #1a2d47; border-radius: 12px; padding: 24px; margin-bottom: 16px; }
.detail-teams-row { display: flex; align-items: center; margin-bottom: 20px; }
.detail-team { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 8px; }
.detail-abbr { width: 52px; height: 52px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 16px; font-weight: 900; color: #fff; }
.detail-tname { font-size: 15px; font-weight: 700; color: #f1f5f9; }
.detail-record { font-size: 11px; color: #475569; }
.detail-center { width: 100px; display: flex; flex-direction: column; align-items: center; gap: 4px; flex-shrink: 0; }
.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.detail-card { background: #0d1626; border: 1px solid #1a2d47; border-radius: 10px; padding: 14px 16px; }
.detail-card-title { font-size: 10px; color: #475569; text-transform: uppercase; letter-spacing: .5px; margin-bottom: 10px; }
.oh-row { display: flex; align-items: center; gap: 8px; margin-bottom: 5px; }
.oh-time { font-size: 10px; color: #475569; width: 52px; }
.oh-bar-wrap { flex: 1; height: 5px; background: #1e293b; border-radius: 3px; overflow: hidden; }
.oh-bar { height: 100%; border-radius: 3px; background: #22c55e; }
.oh-val { font-size: 11px; font-weight: 700; color: #f1f5f9; width: 36px; text-align: right; }
.h2h-row { display: flex; align-items: center; gap: 8px; font-size: 11px; margin-bottom: 5px; }
.h2h-date { color: #334155; width: 54px; flex-shrink: 0; }
.h2h-match { flex: 1; color: #94a3b8; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.h2h-score { font-weight: 700; color: #f1f5f9; width: 36px; text-align: center; }
.h2h-res { font-size: 9px; padding: 1px 5px; border-radius: 3px; font-weight: 700; flex-shrink: 0; }
.res-h { background: #22c55e22; color: #22c55e; }
.res-a { background: #f59e0b22; color: #f59e0b; }
.res-d { background: #47556922; color: #64748b; }
.sc-row { display: flex; align-items: center; gap: 8px; margin-bottom: 7px; }
.sc-lbl { font-size: 10px; color: #475569; width: 70px; text-align: right; }
.sc-bars { flex: 1; display: flex; height: 5px; }
.sc-h { background: #22c55e; border-radius: 2px 0 0 2px; }
.sc-a { background: #f59e0b; border-radius: 0 2px 2px 0; flex: 1; }
.sc-vl { font-size: 10px; color: #22c55e; font-weight: 700; width: 30px; text-align: right; }
.sc-vr { font-size: 10px; color: #f59e0b; font-weight: 700; width: 30px; }

/* ── Value Bets ── */
.vb-list { padding: 12px 28px; display: flex; flex-direction: column; gap: 10px; }
.vb-card { background: #0d1626; border: 1px solid #1a2d47; border-radius: 10px; padding: 14px 18px; display: flex; align-items: center; gap: 14px; cursor: pointer; transition: border-color .15s; }
.vb-card:hover { border-color: #a855f744; }
.vb-rank { width: 28px; height: 28px; border-radius: 50%; background: #a855f722; border: 1px solid #a855f744; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 800; color: #a855f7; flex-shrink: 0; }
.vb-match { flex: 1; min-width: 0; }
.vb-teams { font-size: 14px; font-weight: 700; color: #f1f5f9; }
.vb-meta { font-size: 11px; color: #475569; margin-top: 2px; }
.vb-stat { text-align: center; flex-shrink: 0; min-width: 58px; }
.vb-stat-val { font-size: 18px; font-weight: 900; line-height: 1; }
.vb-stat-lbl { font-size: 9px; color: #334155; margin-top: 1px; }

/* ── Dropping Odds ── */
.do-list { padding: 12px 28px; display: flex; flex-direction: column; gap: 10px; }
.do-card { background: #0d1626; border: 1px solid #1a2d47; border-radius: 10px; overflow: hidden; cursor: pointer; transition: border-color .15s; }
.do-card:hover { border-color: #22c55e44; }
.do-hdr { display: flex; align-items: center; justify-content: space-between; padding: 7px 14px; background: #09111f; border-bottom: 1px solid #1e293b; }
.do-body { display: flex; align-items: center; gap: 14px; padding: 12px 14px; }
.do-teams { flex: 1; min-width: 0; }
.do-matchname { font-size: 14px; font-weight: 700; color: #f1f5f9; }
.do-league { font-size: 11px; color: #475569; margin-top: 2px; }
.do-track { flex-shrink: 0; min-width: 160px; }
.do-track-lbl { font-size: 9px; color: #475569; margin-bottom: 4px; text-transform: uppercase; letter-spacing: .5px; }
.do-track-row { display: flex; align-items: center; gap: 8px; }
.do-old { font-size: 13px; font-weight: 700; color: #475569; text-decoration: line-through; }
.do-new { font-size: 20px; font-weight: 900; color: #22c55e; }
.do-pct { text-align: center; flex-shrink: 0; min-width: 70px; }
.do-pct-val { font-size: 22px; font-weight: 900; color: #22c55e; line-height: 1; }
.do-pct-mkt { font-size: 10px; color: #475569; }

/* ── History ── */
.hist-table { padding: 0 28px 28px; }
.hist-filters { padding: 12px 0; display: flex; gap: 8px; flex-wrap: wrap; }
.hist-table table { width: 100%; border-collapse: collapse; }
.hist-table thead th { padding: 10px 12px; text-align: left; font-size: 10px; color: #475569; text-transform: uppercase; letter-spacing: .5px; border-bottom: 1px solid #1e293b; background: #09111f; }
.hist-table tbody tr { border-bottom: 1px solid #0d1a2e; cursor: pointer; transition: background .1s; }
.hist-table tbody tr:hover { background: #0f1d30; }
.hist-table td { padding: 10px 12px; font-size: 12px; color: #94a3b8; }
.td-match { color: #f1f5f9; font-weight: 600; }
.td-score { font-weight: 700; color: #f1f5f9; text-align: center; }
.td-drop { color: #22c55e; font-weight: 700; }
.rw { color: #22c55e; font-weight: 700; }
.rd { color: #64748b; }
.rl { color: #ef4444; font-weight: 700; }

/* ── Skeleton ── */
.skeleton { border-radius: 4px; background: linear-gradient(90deg, #1a2d47 25%, #243a57 50%, #1a2d47 75%); background-size: 200% 100%; animation: shimmer 1.5s infinite; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: #070e1c; }
::-webkit-scrollbar-thumb { background: #1e3a5f; border-radius: 3px; }
```

- [ ] **Step 2: Run typecheck**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast/frontend && npm run typecheck
```
Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/index.css
git commit -m "feat: add design system CSS from v6 mockups"
```

---

## Task 2: Layout + Sidebar

**Files:**
- Overwrite: `frontend/src/components/layout/Sidebar.tsx`
- Modify: `frontend/src/components/layout/Layout.tsx`

**Context:** Sidebar needs gradient logo, NavLink for active state (already uses NavLink — just update classNames), sync status from Zustand store (`useStore().syncStatus.synced_at`). Layout switches inline style to className.

- [ ] **Step 1: Rewrite Sidebar.tsx**

```tsx
import { NavLink } from 'react-router-dom'
import { useStore } from '../../lib/store'
import { useEffect, useState } from 'react'

const NAV = [
  { to: '/', label: 'Dashboard', icon: '⊞' },
  { to: '/matches', label: '比赛列表', icon: '📋' },
  { to: '/value-bets', label: 'Value Bets', icon: '💎' },
  { to: '/dropping', label: '跌水监控', icon: '📉' },
]
const NAV_DATA = [
  { to: '/history', label: '历史记录', icon: '🕒' },
]

function timeAgo(isoStr: string | null): string {
  if (!isoStr) return '从未同步'
  const diff = Math.floor((Date.now() - new Date(isoStr).getTime()) / 60000)
  if (diff < 1) return '刚刚'
  if (diff < 60) return `${diff} 分钟前`
  return `${Math.floor(diff / 60)} 小时前`
}

export default function Sidebar() {
  const { syncStatus } = useStore()
  const [, setTick] = useState(0)

  useEffect(() => {
    const t = setInterval(() => setTick(n => n + 1), 30_000)
    return () => clearInterval(t)
  }, [])

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="logo-icon">⚽</div>
        <div className="logo-text">Goalcast</div>
      </div>
      <nav>
        {NAV.map(({ to, label, icon }) => (
          <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}>
            <span>{icon}</span><span>{label}</span>
          </NavLink>
        ))}
        <div className="nav-section">数据</div>
        {NAV_DATA.map(({ to, label, icon }) => (
          <NavLink key={to} to={to} className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}>
            <span>{icon}</span><span>{label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="nav-spacer" />
      <div className="sync-status">
        <div className="sync-dot" />
        <span>同步于 {timeAgo(syncStatus.synced_at)}</span>
      </div>
    </aside>
  )
}
```

- [ ] **Step 2: Rewrite Layout.tsx**

```tsx
import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'

export default function Layout() {
  return (
    <div className="layout">
      <Sidebar />
      <main className="main"><Outlet /></main>
    </div>
  )
}
```

- [ ] **Step 3: Run typecheck**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast/frontend && npm run typecheck
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/layout/Sidebar.tsx frontend/src/components/layout/Layout.tsx
git commit -m "feat: redesign sidebar with gradient logo and sync status"
```

---

## Task 3: ProbBar

**Files:**
- Overwrite: `frontend/src/components/match/ProbBar.tsx`

- [ ] **Step 1: Rewrite ProbBar.tsx**

```tsx
export default function ProbBar({ home, draw, away }: { home: number | null; draw: number | null; away: number | null }) {
  if (home == null) return null
  const h = Math.round((home ?? 0) * 100)
  const d = Math.round((draw ?? 0) * 100)
  const a = Math.round((away ?? 0) * 100)
  return (
    <div className="mc-probbar">
      <div className="pb-wrap">
        <div className="pb-home" style={{ flex: h }} />
        <div className="pb-draw" style={{ flex: d }} />
        <div className="pb-away" style={{ flex: a }} />
      </div>
      <div className="pb-labels">
        <span className="pbl"><span className="h">{h}%</span> 主</span>
        <span className="pbl">{d}% 平</span>
        <span className="pbl">客 <span className="a">{a}%</span></span>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Run typecheck and commit**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast/frontend && npm run typecheck
git add frontend/src/components/match/ProbBar.tsx
git commit -m "feat: migrate ProbBar to CSS className system"
```

---

## Task 4: MatchCard v6

**Files:**
- Overwrite: `frontend/src/components/match/MatchCard.tsx`

**Context:** `FixtureSummary` from `lib/api.ts` has `home_stats: TeamStats | null` with fields `wins, draws, losses, gf, ga, goals_avg, win_pct_home, win_pct_away, form5: string[]`. `form5` is currently always `[]` (T-DATA-1 deferred) — render only if `form5.length > 0`. No h2h data on the card (only available in detail). Team color: BRAND map for known abbreviations, hash-based HSL for unknowns.

- [ ] **Step 1: Rewrite MatchCard.tsx**

```tsx
import { useNavigate } from 'react-router-dom'
import type { FixtureSummary } from '../../lib/api'
import ProbBar from './ProbBar'

const BRAND: Record<string, string> = {
  ARS:'#ef0107', LIV:'#c8102e', MCI:'#6cabdd', MUN:'#da291c',
  CHE:'#034694', TOT:'#132257', BAR:'#004d98', REA:'#febe10',
  BAY:'#dc052d', BVB:'#fde100', JUV:'#000000', MIL:'#fb090b',
}

function abbrev(name: string) { return name.slice(0, 3).toUpperCase() }

function teamColor(name: string): string {
  const key = abbrev(name)
  if (BRAND[key]) return BRAND[key]
  let h = 0
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) & 0xffff
  return `hsl(${h % 360}, 55%, 40%)`
}

export default function MatchCard({ fixture: f }: { fixture: FixtureSummary }) {
  const navigate = useNavigate()
  const isLive = f.status === 'live'
  const isFT = f.status === 'ft'
  const time = new Date(f.kickoff_utc).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  const statusClass = isLive ? 'st-live' : isFT ? 'st-ft' : 'st-pre'
  const statusLabel = isLive ? '● 进行中' : isFT ? '已结束' : '未开赛'

  return (
    <div className={`mcard${isLive ? ' live' : ''}`} onClick={() => navigate(`/matches/${f.id}`)}>
      <div className="mc-hdr">
        <span className="mc-hdr-lname">{f.competition_name}</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
          <span className="mc-hdr-time">{time}</span>
          <span className={`mc-status ${statusClass}`}>{statusLabel}</span>
        </div>
      </div>

      <div className="mc-body">
        <div className="mc-team home">
          <div className="t-namerow">
            <div className="t-abbr" style={{ background: teamColor(f.home_team) }}>{abbrev(f.home_team)}</div>
            <span className="t-fullname">{f.home_team}</span>
          </div>
          {f.home_stats && <>
            <div className="t-record">
              <span className="t-wdl">
                <span className="w">{f.home_stats.wins}W</span>{' '}
                <span className="d">{f.home_stats.draws}D</span>{' '}
                <span className="l">{f.home_stats.losses}L</span>
              </span>
            </div>
            <div className="t-goals">
              <span className="g-for">{f.home_stats.gf}</span>
              <span className="g-sep">/</span>
              <span className="g-ag">{f.home_stats.ga}</span>
              <span className="g-avg">·{f.home_stats.goals_avg.toFixed(1)}/场</span>
            </div>
            {f.home_stats.form5.length > 0 && (
              <div className="t-form">
                {f.home_stats.form5.map((r, i) => <span key={i} className={`fp ${r}`}>{r}</span>)}
              </div>
            )}
            <div className="t-winpct h">{f.home_stats.win_pct_home}%</div>
            <div className="t-winlbl">主场胜率</div>
          </>}
        </div>

        <div className="mc-center">
          {(isLive || isFT)
            ? <span className="mc-score">{f.score_home ?? 0}–{f.score_away ?? 0}</span>
            : <span className="mc-vs-txt">VS</span>
          }
          {f.prob_draw !== null && <>
            <span className="mc-draw">{Math.round(f.prob_draw * 100)}%</span>
            <span className="mc-drawlbl">平局</span>
          </>}
        </div>

        <div className="mc-team away">
          <div className="t-namerow">
            <div className="t-abbr" style={{ background: teamColor(f.away_team) }}>{abbrev(f.away_team)}</div>
            <span className="t-fullname">{f.away_team}</span>
          </div>
          {f.away_stats && <>
            <div className="t-record">
              <span className="t-wdl">
                <span className="w">{f.away_stats.wins}W</span>{' '}
                <span className="d">{f.away_stats.draws}D</span>{' '}
                <span className="l">{f.away_stats.losses}L</span>
              </span>
            </div>
            <div className="t-goals">
              <span className="g-for">{f.away_stats.gf}</span>
              <span className="g-sep">/</span>
              <span className="g-ag">{f.away_stats.ga}</span>
              <span className="g-avg">·{f.away_stats.goals_avg.toFixed(1)}/场</span>
            </div>
            {f.away_stats.form5.length > 0 && (
              <div className="t-form">
                {f.away_stats.form5.map((r, i) => <span key={i} className={`fp ${r}`}>{r}</span>)}
              </div>
            )}
            <div className="t-winpct a">{f.away_stats.win_pct_away}%</div>
            <div className="t-winlbl">客场胜率</div>
          </>}
        </div>
      </div>

      <ProbBar home={f.prob_home_win} draw={f.prob_draw} away={f.prob_away_win} />

      <div className="mc-ftr">
        <div className="odds-box">
          <div className={`ob${f.trend_home_win ? ' hot' : ''}`}>
            <div className="ol">主</div>
            <div className="ov">{f.odds_home?.toFixed(2) ?? '—'}</div>
          </div>
          <div className="ob">
            <div className="ol">平</div>
            <div className="ov">{f.odds_draw?.toFixed(2) ?? '—'}</div>
          </div>
          <div className={`ob${f.trend_away_win ? ' hot' : ''}`}>
            <div className="ol">客</div>
            <div className="ov">{f.odds_away?.toFixed(2) ?? '—'}</div>
          </div>
        </div>
        <div className="ftr-sep" />
        <div className="drop-col">
          <div className="drop-val">{f.drop_pct !== null ? `↓${Math.abs(f.drop_pct).toFixed(0)}%` : '—'}</div>
          <div className="drop-mkt">{f.drop_market ?? ''}</div>
        </div>
        <div className="badges">
          {!!f.trend_home_win && <span className="badge bg">主胜↑</span>}
          {!!f.trend_away_win && <span className="badge ba">客胜↑</span>}
          {!!f.trend_btts && <span className="badge bb">BTTS</span>}
          {f.drop_pct !== null && f.drop_pct <= -10 && <span className="badge br">跌水</span>}
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Run typecheck and commit**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast/frontend && npm run typecheck
git add frontend/src/components/match/MatchCard.tsx
git commit -m "feat: rewrite MatchCard to v6 design"
```

---

## Task 5: Matches Page

**Files:**
- Overwrite: `frontend/src/pages/Matches.tsx`
- Delete: `frontend/src/components/filters/DateFilter.tsx`
- Delete: `frontend/src/components/filters/LeagueFilter.tsx`
- Delete: `frontend/src/components/match/MatchCardGrid.tsx`

**Context:** All filter logic is inlined. The continent/league classification from `LeagueFilter.tsx` is copied into Matches. Virtual scrolling (`MatchCardGrid`) is removed — 600 fixtures grouped into leagues renders fine without it. `Skeleton` component from `shared/Skeleton.tsx` stays.

- [ ] **Step 1: Rewrite Matches.tsx**

```tsx
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useStore } from '../lib/store'
import { api, type FixtureSummary } from '../lib/api'
import MatchCard from '../components/match/MatchCard'
import Skeleton from '../components/shared/Skeleton'

const CONTINENT: Record<string, string> = {
  'Premier':'Europe','La Liga':'Europe','Bundesliga':'Europe','Serie A':'Europe',
  'Ligue 1':'Europe','Champions':'Europe','Europa':'Europe','Championship':'Europe',
  'Eredivisie':'Europe','Primeira':'Europe','Super Lig':'Europe','Scottish':'Europe',
  'MLS':'Americas','Liga MX':'Americas','Brasileirao':'Americas','Copa':'Americas',
  'J1':'Asia','K League':'Asia','CSL':'Asia','A-League':'Asia','AFC':'Asia','Saudi':'Asia',
  'CAF':'Africa','AFCON':'Africa',
}
const CONT_FLAG: Record<string, string> = { Europe:'🌍', Americas:'🌎', Asia:'🌏', Africa:'🌍', Other:'🌐' }

function getContinent(name: string): string {
  for (const [key, val] of Object.entries(CONTINENT)) { if (name.includes(key)) return val }
  return 'Other'
}

function offsetDay(n: number): string {
  const d = new Date(); d.setDate(d.getDate() + n); return d.toISOString().split('T')[0]
}
const DATE_PRESETS = [
  { label: '今天', fn: () => offsetDay(0) },
  { label: '明天', fn: () => offsetDay(1) },
  { label: '后天', fn: () => offsetDay(2) },
]

type SortKey = 'time' | 'drop' | 'prob'

function sortFixtures(fixtures: FixtureSummary[], key: SortKey): FixtureSummary[] {
  return [...fixtures].sort((a, b) => {
    if (key === 'drop') return (a.drop_pct ?? 0) - (b.drop_pct ?? 0)
    if (key === 'prob') return (b.prob_home_win ?? 0) - (a.prob_home_win ?? 0)
    return new Date(a.kickoff_utc).getTime() - new Date(b.kickoff_utc).getTime()
  })
}

export default function Matches() {
  const { selectedLeagues, toggleLeague, selectedDate, setDate } = useStore()
  const [sort, setSort] = useState<SortKey>('time')
  const presetValues = DATE_PRESETS.map(p => p.fn())
  const isPreset = presetValues.includes(selectedDate)

  const { data: compData } = useQuery({ queryKey: ['competitions'], queryFn: api.competitions, staleTime: 5 * 60_000 })
  const competitions = compData?.competitions ?? []

  const { data, isLoading } = useQuery({
    queryKey: ['fixtures', selectedDate, selectedLeagues.join(',')],
    queryFn: () => api.fixtures({ date: selectedDate, leagues: selectedLeagues.join(',') }),
    enabled: selectedLeagues.length > 0,
  })

  const fixtures = sortFixtures(data?.fixtures ?? [], sort)
  const groups = fixtures.reduce<Record<string, FixtureSummary[]>>((acc, f) => {
    (acc[f.competition_name] ??= []).push(f); return acc
  }, {})

  const allIds = competitions.map(c => c.id)
  function selectAll() { allIds.forEach(id => { if (!selectedLeagues.includes(id)) toggleLeague(id) }) }
  function selectNone() { allIds.forEach(id => { if (selectedLeagues.includes(id)) toggleLeague(id) }) }

  const byContinent = competitions.reduce<Record<string, typeof competitions>>((acc, c) => {
    const cont = getContinent(c.name);(acc[cont] ??= []).push(c); return acc
  }, {})
  const ORDER = ['Europe', 'Americas', 'Asia', 'Africa', 'Other']
  const sorted = Object.entries(byContinent).sort(([a], [b]) => ORDER.indexOf(a) - ORDER.indexOf(b))

  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-title">比赛列表</div>
          <div className="page-subtitle">
            {selectedLeagues.length > 0 ? `共 ${fixtures.length} 场 · 已选 ${selectedLeagues.length} 个联赛` : '请选择联赛'}
          </div>
        </div>
        <button className="btn btn-secondary" onClick={() => window.location.reload()}>↻ 刷新</button>
      </div>

      <div className="filter-section">
        <div className="filter-row">
          <span className="filter-lbl">日期</span>
          {DATE_PRESETS.map(({ label, fn }) => {
            const v = fn()
            return (
              <button key={label} className={`chip${selectedDate === v ? ' active' : ''}`} onClick={() => setDate(v)}>{label}</button>
            )
          })}
          <input type="date" value={!isPreset ? selectedDate : ''} onChange={e => e.target.value && setDate(e.target.value)} className="date-native" />
        </div>

        <div className="filter-row" style={{ alignItems: 'flex-start' }}>
          <span className="filter-lbl" style={{ paddingTop: 2 }}>联赛</span>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, flex: 1 }}>
            <div style={{ display: 'flex', gap: 5 }}>
              <button className="pill all-pill" onClick={selectAll}>全选</button>
              <button className="pill" onClick={selectNone}>全不选</button>
            </div>
            {sorted.map(([continent, leagues]) => (
              <div key={continent} className="continent-block">
                <div className="continent-label">{CONT_FLAG[continent] ?? '🌐'} {continent}</div>
                <div className="league-pills">
                  {leagues.map(l => (
                    <button key={l.id} className={`pill${selectedLeagues.includes(l.id) ? ' sel' : ''}`} onClick={() => toggleLeague(l.id)}>
                      {l.name}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="sort-row">
          <span style={{ fontSize: 11, color: '#475569' }}>排序</span>
          <select className="sort-select" value={sort} onChange={e => setSort(e.target.value as SortKey)}>
            <option value="time">开赛时间</option>
            <option value="drop">跌水幅度</option>
            <option value="prob">主胜概率</option>
          </select>
          <span className="result-info"><em>{fixtures.length}</em> 场 · <em>{selectedLeagues.length}</em> 联赛</span>
        </div>
      </div>

      <div className="matches-area">
        {selectedLeagues.length === 0 && (
          <div style={{ textAlign: 'center', color: '#475569', padding: 60 }}>请先选择联赛以加载比赛数据</div>
        )}
        {isLoading && selectedLeagues.length > 0 && (
          <div className="match-grid">
            {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} height={260} style={{ borderRadius: 10 }} />)}
          </div>
        )}
        {!isLoading && selectedLeagues.length > 0 && fixtures.length === 0 && (
          <div style={{ textAlign: 'center', color: '#475569', padding: 60 }}>当天所选联赛无比赛</div>
        )}
        {!isLoading && Object.entries(groups).map(([league, fxs]) => (
          <div key={league} className="league-group">
            <div className="league-title">
              <span>{CONT_FLAG[getContinent(league)] ?? '🌐'}</span>
              <span className="league-name">{league}</span>
              <span className="league-count">{fxs.length}场</span>
            </div>
            <div className="match-grid">
              {fxs.map(f => <MatchCard key={f.id} fixture={f} />)}
            </div>
          </div>
        ))}
      </div>
    </>
  )
}
```

- [ ] **Step 2: Delete unused components**

```bash
rm /Users/zhengningdai/workspace/skyold/Goalcast/frontend/src/components/filters/DateFilter.tsx
rm /Users/zhengningdai/workspace/skyold/Goalcast/frontend/src/components/filters/LeagueFilter.tsx
rm /Users/zhengningdai/workspace/skyold/Goalcast/frontend/src/components/match/MatchCardGrid.tsx
```

- [ ] **Step 3: Run typecheck**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast/frontend && npm run typecheck
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/Matches.tsx
git rm frontend/src/components/filters/DateFilter.tsx frontend/src/components/filters/LeagueFilter.tsx frontend/src/components/match/MatchCardGrid.tsx
git commit -m "feat: rewrite Matches page with inline filters and league grouping"
```

---

## Task 6: Dashboard

**Files:**
- Overwrite: `frontend/src/pages/Dashboard.tsx`

**Context:** 4 stat cards. `api.history({ limit: 0 })` is called with `limit: 0` — the backend returns `total` correctly even with limit=0 because the history router uses `SELECT COUNT(*)` separately. Alert cards use className `.alert-card` with inline `style={{ borderColor }}` override for color variation. Featured match grid shows up to 4 cards.

- [ ] **Step 1: Rewrite Dashboard.tsx**

```tsx
import { useQuery } from '@tanstack/react-query'
import { useStore } from '../lib/store'
import { api } from '../lib/api'
import MatchCard from '../components/match/MatchCard'

export default function Dashboard() {
  const { selectedLeagues, selectedDate } = useStore()
  const today = new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' })

  const { data: fixturesData } = useQuery({
    queryKey: ['fixtures', selectedDate, selectedLeagues.join(','), 4],
    queryFn: () => api.fixtures({ date: selectedDate, leagues: selectedLeagues.join(','), limit: 4 }),
    enabled: selectedLeagues.length > 0,
  })
  const { data: vbData } = useQuery({ queryKey: ['value-bets', 5], queryFn: () => api.valueBets({ min_edge: 5 }) })
  const { data: dropData } = useQuery({ queryKey: ['dropping-odds', 10], queryFn: () => api.droppingOdds({ min_drop: 10 }) })
  const { data: histData } = useQuery({ queryKey: ['history-total'], queryFn: () => api.history({ limit: 0 }) })

  const liveCount = fixturesData?.fixtures.filter(f => f.status === 'live').length ?? 0
  const vbItems = (vbData?.items ?? []).slice(0, 4)
  const dropItems = (dropData?.items ?? []).slice(0, 4)
  const featured = fixturesData?.fixtures ?? []

  const STATS = [
    { label: '今日比赛', value: fixturesData?.total ?? '—', color: '#22c55e', sub: liveCount > 0 ? `● ${liveCount} 场进行中` : undefined, subColor: '#22c55e' },
    { label: 'Value Bets', value: vbData?.items.length ?? '—', color: '#a855f7', sub: undefined, subColor: undefined },
    { label: '跌水警报', value: dropData?.items.length ?? '—', color: '#22c55e', sub: undefined, subColor: undefined },
    { label: '已存储比赛', value: histData?.total ?? '—', color: '#3b82f6', sub: undefined, subColor: undefined },
  ]

  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-title">Dashboard</div>
          <div className="page-subtitle">今日数据概览 · {today}</div>
        </div>
        <button className="btn btn-secondary" onClick={() => window.location.reload()}>↻ 刷新</button>
      </div>

      <div className="stats-grid">
        {STATS.map(({ label, value, color, sub, subColor }) => (
          <div key={label} className="stat-card">
            <div className="stat-label">{label}</div>
            <div className="stat-value" style={{ color }}>{value}</div>
            {sub && <div className="stat-sub" style={{ color: subColor }}>{sub}</div>}
          </div>
        ))}
      </div>

      <div className="dash-section">
        <div className="dash-section-title">💎 今日 Value Bets</div>
        {vbItems.length === 0
          ? <div style={{ color: '#475569', fontSize: 13 }}>暂无 Value Bets</div>
          : (
            <div className="dash-2col">
              {vbItems.map((item, i) => {
                const dir = item.selection === 'home' ? '主胜' : item.selection === 'away' ? '客胜' : '平局'
                const time = new Date(item.kickoff_utc).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
                return (
                  <div key={i} className="alert-card" style={{ borderColor: '#a855f733' }}>
                    <div className="alert-icon" style={{ background: '#a855f722' }}>💎</div>
                    <div>
                      <div className="alert-match">{item.home_team} vs {item.away_team}</div>
                      <div className="alert-detail">{item.competition_name} · {time} · {dir}</div>
                      <div className="alert-tags">
                        <span className="badge bp">边际+{item.edge_pct.toFixed(1)}%</span>
                        <span className="badge bb">赔率{item.odds.toFixed(2)}</span>
                        <span className="badge bp">概率{Math.round(item.prob * 100)}%</span>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )
        }
      </div>

      <div className="dash-section">
        <div className="dash-section-title">📉 最新跌水警报</div>
        {dropItems.length === 0
          ? <div style={{ color: '#475569', fontSize: 13 }}>暂无跌水警报</div>
          : (
            <div className="dash-2col">
              {dropItems.map((item, i) => {
                const time = new Date(item.kickoff_utc).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
                return (
                  <div key={i} className="alert-card" style={{ borderColor: '#22c55e33' }}>
                    <div className="alert-icon" style={{ background: '#22c55e22' }}>↓</div>
                    <div>
                      <div className="alert-match">{item.home_team} vs {item.away_team}</div>
                      <div className="alert-detail">{item.competition_name} · {time}</div>
                      <div className="alert-tags">
                        <span className="badge bg">{item.market} ↓{Math.abs(item.drop_pct ?? 0).toFixed(1)}%</span>
                        <span className="badge bb">{item.odds_home?.toFixed(2) ?? '—'} / {item.odds_draw?.toFixed(2) ?? '—'} / {item.odds_away?.toFixed(2) ?? '—'}</span>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )
        }
      </div>

      <div className="dash-section">
        <div className="dash-section-title">📋 今日精选比赛</div>
        {selectedLeagues.length === 0
          ? <div style={{ color: '#475569', fontSize: 13 }}>请先在比赛列表中选择关注联赛</div>
          : featured.length === 0
          ? <div style={{ color: '#475569', fontSize: 13 }}>今日无精选比赛</div>
          : <div className="match-grid">{featured.map(f => <MatchCard key={f.id} fixture={f} />)}</div>
        }
      </div>
    </>
  )
}
```

- [ ] **Step 2: Run typecheck and commit**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast/frontend && npm run typecheck
git add frontend/src/pages/Dashboard.tsx
git commit -m "feat: rewrite Dashboard with stat cards and alert sections"
```

---

## Task 7: MatchDetail

**Files:**
- Overwrite: `frontend/src/pages/MatchDetail.tsx`

**Context:** Uses `api.fixture(id)` → `{ fixture, odds_history, h2h, stats }`. Also fetches `api.valueBets()` and filters client-side by `fixture_id`. Odds history bar: scale relative to `max(odds_home)` in the last-10 slice. Stats comparison: bar width = `hv / (hv + av) * 100%`. `teamColor` helper is duplicated here (same as MatchCard — not extracted to avoid creating a new shared file).

- [ ] **Step 1: Rewrite MatchDetail.tsx**

```tsx
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'

const BRAND: Record<string, string> = {
  ARS:'#ef0107', LIV:'#c8102e', MCI:'#6cabdd', MUN:'#da291c',
  CHE:'#034694', TOT:'#132257', BAR:'#004d98', REA:'#febe10',
  BAY:'#dc052d', BVB:'#fde100', JUV:'#000000', MIL:'#fb090b',
}
function abbrev(name: string) { return name.slice(0, 3).toUpperCase() }
function teamColor(name: string): string {
  const key = abbrev(name)
  if (BRAND[key]) return BRAND[key]
  let h = 0
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) & 0xffff
  return `hsl(${h % 360}, 55%, 40%)`
}

export default function MatchDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const { data, isLoading } = useQuery({
    queryKey: ['fixture', id],
    queryFn: () => api.fixture(Number(id)),
    enabled: !!id,
  })
  const { data: vbAll } = useQuery({ queryKey: ['value-bets', 0], queryFn: () => api.valueBets() })

  if (isLoading) return <div style={{ padding: 24, color: '#64748b' }}>加载中...</div>
  if (!data) return <div style={{ padding: 24, color: '#64748b' }}>比赛不存在</div>

  const { fixture: f, odds_history, h2h, stats } = data
  const vbMatch = (vbAll?.items ?? []).filter(v => v.fixture_id === f.id)
  const kickoffStr = new Date(f.kickoff_utc).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
  const ohSlice = odds_history.slice(-10)
  const maxOdds = Math.max(...ohSlice.map(s => s.odds_home ?? 0), 1)

  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-title">比赛详情</div>
          <div className="page-subtitle">{f.competition_name} · {kickoffStr}</div>
        </div>
        <button className="btn btn-secondary" onClick={() => navigate(-1)}>← 返回列表</button>
      </div>

      <div className="detail-area">
        <div className="detail-hero">
          <div className="detail-teams-row">
            <div className="detail-team">
              <div className="detail-abbr" style={{ background: teamColor(f.home_team) }}>{abbrev(f.home_team)}</div>
              <div className="detail-tname">{f.home_team}</div>
              {stats.home && (
                <div className="detail-record">
                  {stats.home.wins}W {stats.home.draws}D {stats.home.losses}L · 进{stats.home.gf} 失{stats.home.ga}
                </div>
              )}
            </div>
            <div className="detail-center">
              <div style={{ fontSize: 11, color: '#475569' }}>{new Date(f.kickoff_utc).toLocaleDateString('zh-CN')}</div>
              <div style={{ fontSize: 26, fontWeight: 900, color: '#f1f5f9' }}>
                {f.status !== 'pre' ? `${f.score_home ?? 0} – ${f.score_away ?? 0}` : 'VS'}
              </div>
              <div style={{ fontSize: 11, color: '#475569' }}>{f.competition_name}</div>
              <div style={{ display: 'flex', gap: 4, marginTop: 4 }}>
                {f.status === 'live' && <span className="mc-status st-live">● 进行中</span>}
                {f.status === 'ft' && <span className="mc-status st-ft">已结束</span>}
                {vbMatch.length > 0 && <span className="badge bp">Value</span>}
                {!!f.trend_btts && <span className="badge bb">BTTS</span>}
              </div>
            </div>
            <div className="detail-team">
              <div className="detail-abbr" style={{ background: teamColor(f.away_team) }}>{abbrev(f.away_team)}</div>
              <div className="detail-tname">{f.away_team}</div>
              {stats.away && (
                <div className="detail-record">
                  {stats.away.wins}W {stats.away.draws}D {stats.away.losses}L · 进{stats.away.gf} 失{stats.away.ga}
                </div>
              )}
            </div>
          </div>

          {f.prob_home_win !== null && (
            <>
              <div style={{ height: 8, borderRadius: 4, overflow: 'hidden', display: 'flex', marginBottom: 8 }}>
                <div style={{ flex: Math.round((f.prob_home_win ?? 0) * 100), background: '#22c55e' }} />
                <div style={{ flex: Math.round((f.prob_draw ?? 0) * 100), background: '#475569' }} />
                <div style={{ flex: Math.round((f.prob_away_win ?? 0) * 100), background: '#f59e0b' }} />
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#64748b', marginBottom: 12 }}>
                <span style={{ color: '#22c55e' }}>主胜 {Math.round((f.prob_home_win ?? 0) * 100)}%</span>
                <span>平 {Math.round((f.prob_draw ?? 0) * 100)}%</span>
                <span style={{ color: '#f59e0b' }}>客胜 {Math.round((f.prob_away_win ?? 0) * 100)}%</span>
              </div>
            </>
          )}

          <div className="odds-box">
            <div className={`ob${f.trend_home_win ? ' hot' : ''}`} style={{ minWidth: 64 }}>
              <div className="ol">主胜</div>
              <div className="ov">{f.odds_home?.toFixed(2) ?? '—'}</div>
            </div>
            <div className="ob" style={{ minWidth: 64 }}>
              <div className="ol">平局</div>
              <div className="ov">{f.odds_draw?.toFixed(2) ?? '—'}</div>
            </div>
            <div className={`ob${f.trend_away_win ? ' hot' : ''}`} style={{ minWidth: 64 }}>
              <div className="ol">客胜</div>
              <div className="ov">{f.odds_away?.toFixed(2) ?? '—'}</div>
            </div>
            {f.drop_pct !== null && (
              <div className="ob" style={{ minWidth: 64, background: '#22c55e22', border: '1px solid #22c55e44' }}>
                <div className="ol">跌水</div>
                <div className="ov" style={{ color: '#22c55e' }}>↓{Math.abs(f.drop_pct).toFixed(1)}%</div>
              </div>
            )}
          </div>
        </div>

        <div className="detail-grid">
          <div className="detail-card">
            <div className="detail-card-title">赔率历史 — 主胜走势</div>
            {ohSlice.length === 0
              ? <div style={{ color: '#475569', fontSize: 12 }}>暂无赔率历史记录</div>
              : ohSlice.map((snap, i) => {
                const pct = ((snap.odds_home ?? 0) / maxOdds) * 100
                const t = new Date(snap.recorded_at).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
                return (
                  <div key={i} className="oh-row">
                    <span className="oh-time">{t}</span>
                    <div className="oh-bar-wrap"><div className="oh-bar" style={{ width: `${pct}%` }} /></div>
                    <span className="oh-val">{snap.odds_home?.toFixed(2) ?? '—'}</span>
                  </div>
                )
              })
            }
          </div>

          <div className="detail-card">
            <div className="detail-card-title">近期 H2H 交锋记录</div>
            {(!h2h || h2h.length === 0)
              ? <div style={{ color: '#475569', fontSize: 12 }}>暂无 H2H 交锋记录</div>
              : h2h.map((m, i) => {
                const homeWon = m.score_h > m.score_a
                const draw = m.score_h === m.score_a
                return (
                  <div key={i} className="h2h-row">
                    <span className="h2h-date">{String(m.date).slice(0, 10)}</span>
                    <span className="h2h-match">{m.home} vs {m.away}</span>
                    <span className="h2h-score">{m.score_h}–{m.score_a}</span>
                    <span className={`h2h-res ${homeWon ? 'res-h' : draw ? 'res-d' : 'res-a'}`}>
                      {homeWon ? '主胜' : draw ? '平' : '客胜'}
                    </span>
                  </div>
                )
              })
            }
          </div>

          <div className="detail-card">
            <div className="detail-card-title">赛季数据对比</div>
            {(!stats.home && !stats.away)
              ? <div style={{ color: '#475569', fontSize: 12 }}>暂无赛季数据</div>
              : ([
                ['进球', stats.home?.gf ?? 0, stats.away?.gf ?? 0],
                ['失球', stats.home?.ga ?? 0, stats.away?.ga ?? 0],
                ['主场胜率%', stats.home?.win_pct_home ?? 0, stats.away?.win_pct_home ?? 0],
                ['场均进球', +(stats.home?.goals_avg ?? 0).toFixed(1), +(stats.away?.goals_avg ?? 0).toFixed(1)],
                ['客场胜率%', stats.home?.win_pct_away ?? 0, stats.away?.win_pct_away ?? 0],
              ] as [string, number, number][]).map(([lbl, hv, av]) => {
                const total = (hv + av) || 1
                return (
                  <div key={lbl} className="sc-row">
                    <span className="sc-vl">{hv}</span>
                    <span className="sc-lbl">{lbl}</span>
                    <div className="sc-bars">
                      <div className="sc-h" style={{ width: `${(hv / total) * 100}%` }} />
                      <div className="sc-a" />
                    </div>
                    <span className="sc-vr">{av}</span>
                  </div>
                )
              })
            }
          </div>

          <div className="detail-card">
            <div className="detail-card-title">趋势分析</div>
            {!f.drop_pct && !f.trend_home_win && !f.trend_away_win && !f.trend_btts && vbMatch.length === 0
              ? <div style={{ color: '#475569', fontSize: 12 }}>暂无分析数据</div>
              : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 12, color: '#94a3b8', lineHeight: 1.6 }}>
                  {f.drop_pct !== null && f.drop_pct <= -10 && (
                    <p>📉 <strong style={{ color: '#22c55e' }}>跌水警报：</strong>{f.drop_market ?? ''}赔率下跌 {Math.abs(f.drop_pct).toFixed(1)}%。</p>
                  )}
                  {!!f.trend_home_win && <p>🏠 <strong style={{ color: '#22c55e' }}>主胜趋势：</strong>主队近期主场表现强势。</p>}
                  {!!f.trend_away_win && <p>✈️ <strong style={{ color: '#f59e0b' }}>客胜趋势：</strong>客队近期客场表现出色。</p>}
                  {!!f.trend_btts && <p>⚽ <strong style={{ color: '#3b82f6' }}>双进球趋势：</strong>两队近期均有进球，BTTS 概率较高。</p>}
                  {vbMatch.map((v, i) => (
                    <p key={i}>💎 <strong style={{ color: '#a855f7' }}>Value Bet：</strong>
                      {v.selection === 'home' ? '主胜' : v.selection === 'away' ? '客胜' : '平局'} · 
                      赔率 {v.odds.toFixed(2)} · 边际优势 <strong style={{ color: '#22c55e' }}>+{v.edge_pct.toFixed(1)}%</strong>
                    </p>
                  ))}
                </div>
              )
            }
          </div>
        </div>
      </div>
    </>
  )
}
```

- [ ] **Step 2: Run typecheck and commit**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast/frontend && npm run typecheck
git add frontend/src/pages/MatchDetail.tsx
git commit -m "feat: rewrite MatchDetail with hero section and 2-col detail grid"
```

---

## Task 8: ValueBets

**Files:**
- Overwrite: `frontend/src/pages/ValueBets.tsx`

- [ ] **Step 1: Rewrite ValueBets.tsx**

```tsx
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'

type Dir = 'all' | 'home' | 'draw' | 'away'
const DIR_LABELS: Record<Dir, string> = { all: '全部', home: '主胜', draw: '平局', away: '客胜' }

export default function ValueBets() {
  const navigate = useNavigate()
  const [minEdge, setMinEdge] = useState(5)
  const [dir, setDir] = useState<Dir>('all')

  const { data, isLoading } = useQuery({
    queryKey: ['value-bets', minEdge],
    queryFn: () => api.valueBets({ min_edge: minEdge }),
  })

  const items = (data?.items ?? [])
    .filter(item => dir === 'all' || item.selection === dir)
    .sort((a, b) => b.edge_pct - a.edge_pct)

  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-title">Value Bets</div>
          <div className="page-subtitle">边际优势 ≥ {minEdge}% 的投注机会 · 今日 {data?.items.length ?? '—'} 个</div>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          {(['all', 'home', 'draw', 'away'] as Dir[]).map(d => (
            <button key={d} className={`chip${dir === d ? ' active' : ''}`} onClick={() => setDir(d)}>{DIR_LABELS[d]}</button>
          ))}
        </div>
      </div>

      <div style={{ padding: '10px 28px', display: 'flex', alignItems: 'center', gap: 8, borderBottom: '1px solid #1e293b' }}>
        <span style={{ fontSize: 11, color: '#475569' }}>最小优势</span>
        <select className="sort-select" value={minEdge} onChange={e => setMinEdge(Number(e.target.value))}>
          {[3, 5, 8, 10, 15].map(v => <option key={v} value={v}>{v}%</option>)}
        </select>
      </div>

      {isLoading
        ? <div style={{ padding: 24, color: '#64748b' }}>加载中...</div>
        : items.length === 0
        ? <div style={{ textAlign: 'center', color: '#475569', padding: 60 }}>当前无符合条件的 Value Bets</div>
        : (
          <div className="vb-list">
            {items.map((item, i) => {
              const dirLabel = item.selection === 'home' ? '主胜' : item.selection === 'away' ? '客胜' : '平局'
              const time = new Date(item.kickoff_utc).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
              return (
                <div key={i} className="vb-card" onClick={() => navigate(`/matches/${item.fixture_id}`)}>
                  <div className="vb-rank">{i + 1}</div>
                  <div className="vb-match">
                    <div className="vb-teams">{item.home_team} vs {item.away_team}</div>
                    <div className="vb-meta">{item.competition_name} · {time}</div>
                  </div>
                  <div className="vb-stat">
                    <div className="vb-stat-val" style={{ color: '#f1f5f9' }}>{dirLabel}</div>
                    <div className="vb-stat-lbl">投注方向</div>
                  </div>
                  <div className="ob hot" style={{ minWidth: 54 }}>
                    <div className="ol">赔率</div>
                    <div className="ov">{item.odds.toFixed(2)}</div>
                  </div>
                  <div className="vb-stat">
                    <div className="vb-stat-val" style={{ color: '#a855f7' }}>{Math.round(item.prob * 100)}%</div>
                    <div className="vb-stat-lbl">模型概率</div>
                  </div>
                  <div className="vb-stat">
                    <div className="vb-stat-val" style={{ color: '#22c55e' }}>+{item.edge_pct.toFixed(1)}%</div>
                    <div className="vb-stat-lbl">边际优势</div>
                  </div>
                </div>
              )
            })}
          </div>
        )
      }
    </>
  )
}
```

- [ ] **Step 2: Run typecheck and commit**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast/frontend && npm run typecheck
git add frontend/src/pages/ValueBets.tsx
git commit -m "feat: rewrite ValueBets as ranked vb-card list"
```

---

## Task 9: DroppingOdds

**Files:**
- Overwrite: `frontend/src/pages/DroppingOdds.tsx`

**Context:** `DroppingOddsItem` has `odds_home | odds_draw | odds_away | drop_pct | drop_market | market | recorded_at`. Opening price not yet stored (T-DATA-3) — show current odds only. Market filter matches `drop_market` string loosely.

- [ ] **Step 1: Rewrite DroppingOdds.tsx**

```tsx
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'

type MktFilter = 'all' | 'home' | 'over' | 'away'
const MKT_LABELS: Record<MktFilter, string> = { all: '所有市场', home: '主胜', over: '大球', away: '客胜' }

function timeAgoShort(isoStr: string): string {
  const diff = Math.floor((Date.now() - new Date(isoStr).getTime()) / 60000)
  if (diff < 1) return '刚刚'
  if (diff < 60) return `${diff}分钟前`
  return new Date(isoStr).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

export default function DroppingOdds() {
  const navigate = useNavigate()
  const [minDrop, setMinDrop] = useState(10)
  const [mkt, setMkt] = useState<MktFilter>('all')

  const { data, isLoading } = useQuery({
    queryKey: ['dropping-odds', minDrop],
    queryFn: () => api.droppingOdds({ min_drop: minDrop }),
    refetchInterval: 30_000,
  })

  const items = (data?.items ?? [])
    .filter(item => {
      if (mkt === 'all') return true
      const m = (item.drop_market ?? item.market ?? '').toLowerCase()
      if (mkt === 'home') return m.includes('主') || m.includes('home')
      if (mkt === 'away') return m.includes('客') || m.includes('away')
      if (mkt === 'over') return m.includes('大') || m.includes('over')
      return true
    })
    .sort((a, b) => (a.drop_pct ?? 0) - (b.drop_pct ?? 0))

  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-title">跌水监控</div>
          <div className="page-subtitle">赔率显著下跌的比赛</div>
        </div>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          {(['all', 'home', 'over', 'away'] as MktFilter[]).map(m => (
            <button key={m} className={`chip${mkt === m ? ' active' : ''}`} onClick={() => setMkt(m)}>{MKT_LABELS[m]}</button>
          ))}
          <select className="sort-select" value={minDrop} onChange={e => setMinDrop(Number(e.target.value))}>
            {[5, 10, 15, 20].map(v => <option key={v} value={v}>≥{v}%</option>)}
          </select>
        </div>
      </div>

      {isLoading
        ? <div style={{ padding: 24, color: '#64748b' }}>加载中...</div>
        : items.length === 0
        ? <div style={{ textAlign: 'center', color: '#475569', padding: 60 }}>暂无跌水数据</div>
        : (
          <div className="do-list">
            {items.map((item, i) => {
              const currentOdds = item.odds_home ?? item.odds_away ?? item.odds_draw
              const mktLabel = item.drop_market ?? item.market ?? '赔率'
              return (
                <div key={i} className="do-card" onClick={() => navigate(`/matches/${item.fixture_id}`)}>
                  <div className="do-hdr">
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ fontSize: 11, color: '#64748b' }}>{item.competition_name}</span>
                    </div>
                    <span style={{ fontSize: 11, color: '#334155' }}>{timeAgoShort(item.recorded_at)}</span>
                  </div>
                  <div className="do-body">
                    <div className="do-teams">
                      <div className="do-matchname">{item.home_team} vs {item.away_team}</div>
                      <div className="do-league">{item.competition_name}</div>
                    </div>
                    <div className="do-track">
                      <div className="do-track-lbl">{mktLabel}赔率变动</div>
                      <div className="do-track-row">
                        <div className="do-new">{currentOdds?.toFixed(2) ?? '—'}</div>
                        <span style={{ fontSize: 10, color: '#334155' }}>当前</span>
                      </div>
                    </div>
                    <div className="do-pct">
                      <div className="do-pct-val">↓{Math.abs(item.drop_pct ?? 0).toFixed(0)}%</div>
                      <div className="do-pct-mkt">{mktLabel}</div>
                    </div>
                    <div className="badges" style={{ flexDirection: 'column' }}>
                      {(item.drop_pct ?? 0) <= -20 && <span className="badge br">大幅跌水</span>}
                      <span className="badge bg">↓{Math.abs(item.drop_pct ?? 0).toFixed(1)}%</span>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )
      }
    </>
  )
}
```

- [ ] **Step 2: Run typecheck and commit**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast/frontend && npm run typecheck
git add frontend/src/pages/DroppingOdds.tsx
git commit -m "feat: rewrite DroppingOdds as do-card list with odds track"
```

---

## Task 10: History

**Files:**
- Overwrite: `frontend/src/pages/History.tsx`

**Context:** `api.history({ limit, offset, league })` — `league` is `number | undefined` (competition id). Filter chips: `全部` / `有跌水` are local state (not persisted). Top-8 league pills come from `api.competitions()`. When `leagueFilter` changes, reset `offset` to 0.

- [ ] **Step 1: Rewrite History.tsx**

```tsx
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'

type DropFilter = 'all' | 'drop'

export default function History() {
  const navigate = useNavigate()
  const [offset, setOffset] = useState(0)
  const [dropFilter, setDropFilter] = useState<DropFilter>('all')
  const [leagueFilter, setLeagueFilter] = useState<number | null>(null)
  const limit = 50

  const { data: compData } = useQuery({ queryKey: ['competitions'], queryFn: api.competitions, staleTime: 5 * 60_000 })
  const topLeagues = (compData?.competitions ?? []).slice(0, 8)

  const { data, isLoading } = useQuery({
    queryKey: ['history', offset, leagueFilter],
    queryFn: () => api.history({ limit, offset, league: leagueFilter ?? undefined }),
  })

  const rawItems = data?.items ?? []
  const items = dropFilter === 'drop' ? rawItems.filter(f => f.drop_pct !== null) : rawItems
  const total = data?.total ?? 0

  function resultClass(f: typeof items[0]): string {
    if (f.status !== 'ft' || f.score_home == null || f.score_away == null) return ''
    if (f.score_home > f.score_away) return 'rw'
    if (f.score_home === f.score_away) return 'rd'
    return 'rl'
  }

  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-title">历史记录</div>
          <div className="page-subtitle">已存储比赛数据 · 共 {total} 场</div>
        </div>
      </div>

      <div className="hist-table">
        <div className="hist-filters">
          <button className={`chip${dropFilter === 'all' ? ' active' : ''}`} onClick={() => setDropFilter('all')}>全部</button>
          <button className={`chip${dropFilter === 'drop' ? ' active' : ''}`} onClick={() => setDropFilter('drop')}>有跌水</button>
          <span style={{ width: 1, alignSelf: 'stretch', background: '#1e293b', margin: '0 4px' }} />
          <button className={`chip${leagueFilter === null ? ' active' : ''}`} onClick={() => { setLeagueFilter(null); setOffset(0) }}>所有联赛</button>
          {topLeagues.map(l => (
            <button key={l.id} className={`chip${leagueFilter === l.id ? ' active' : ''}`} onClick={() => { setLeagueFilter(l.id); setOffset(0) }}>
              {l.name}
            </button>
          ))}
        </div>

        {isLoading
          ? <div style={{ color: '#64748b', padding: 20 }}>加载中...</div>
          : items.length === 0
          ? <div style={{ textAlign: 'center', color: '#475569', padding: 60 }}>暂无已完成比赛记录</div>
          : (
            <table>
              <thead>
                <tr>
                  <th>日期</th>
                  <th>比赛</th>
                  <th>联赛</th>
                  <th>比分</th>
                  <th>趋势</th>
                  <th>跌水</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {items.map(f => {
                  const res = resultClass(f)
                  return (
                    <tr key={f.id} onClick={() => navigate(`/matches/${f.id}`)}>
                      <td>{new Date(f.kickoff_utc).toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })}</td>
                      <td className="td-match">{f.home_team} vs {f.away_team}</td>
                      <td style={{ maxWidth: 130, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{f.competition_name}</td>
                      <td className={`td-score${res ? ' ' + res : ''}`}>
                        {f.status === 'ft' && f.score_home != null ? `${f.score_home}–${f.score_away}` : '—'}
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: 3 }}>
                          {!!f.trend_home_win && <span className="badge bg">主胜↑</span>}
                          {!!f.trend_away_win && <span className="badge ba">客胜↑</span>}
                          {!!f.trend_btts && <span className="badge bb">BTTS</span>}
                        </div>
                      </td>
                      <td className="td-drop">{f.drop_pct !== null ? `↓${Math.abs(f.drop_pct).toFixed(0)}%` : ''}</td>
                      <td style={{ color: '#334155', fontSize: 11 }}>→</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )
        }

        {total > limit && (
          <div style={{ display: 'flex', justifyContent: 'center', gap: 8, marginTop: 16 }}>
            <button disabled={offset === 0} className="btn btn-secondary" onClick={() => setOffset(Math.max(0, offset - limit))}>上一页</button>
            <span style={{ padding: '6px 12px', color: '#64748b', fontSize: 13 }}>{Math.floor(offset / limit) + 1} / {Math.ceil(total / limit)}</span>
            <button disabled={offset + limit >= total} className="btn btn-secondary" onClick={() => setOffset(offset + limit)}>下一页</button>
          </div>
        )}
      </div>
    </>
  )
}
```

- [ ] **Step 2: Run typecheck and commit**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast/frontend && npm run typecheck
git add frontend/src/pages/History.tsx
git commit -m "feat: rewrite History with filter chips and full table"
```

---

## Task 11: Deferred Data Tasks (Record Only — No Implementation)

These are NOT implemented in this plan. Recorded so they appear in git history for future planning.

| ID | Title | What to investigate |
|----|-------|---------------------|
| T-DATA-1 | form5 近5场 | OddAlerts endpoint for recent form — try `/teams/{id}` or fixture detail `?include=form` |
| T-DATA-2 | H2H 交锋记录 | Test `/fixtures/{id}?include=h2h` — check if OddAlerts returns H2H in fixture detail |
| T-DATA-3 | Opening 开盘价 | Check `/odds` or `/odds-movements` for opening price field; store in new `odds_snapshots` columns |
| T-DATA-4 | 1x2 赔率来源 | Investigate `/odds?market=1x2` for real-time home/draw/away odds |

- [ ] **Step 1: Commit empty with data task notes**

```bash
git commit --allow-empty -m "docs: record deferred data tasks T-DATA-1 through T-DATA-4 for future sprints"
```

---

## Final Verification

- [ ] `cd /Users/zhengningdai/workspace/skyold/Goalcast/frontend && npm run typecheck` — 0 errors
- [ ] `cd /Users/zhengningdai/workspace/skyold/Goalcast/frontend && npm run build` — succeeds
- [ ] Browser Dashboard: 4 stat cards visible, alert card sections present
- [ ] Browser Matches: inline filter rows visible, league groups with emoji and count badges
- [ ] Browser MatchDetail: hero section with team abbr badges + 2-col grid
- [ ] Browser ValueBets: ranked numbered cards with vb-rank circle
- [ ] Browser DroppingOdds: do-card list with header row + body
- [ ] Browser History: table with filter chips
- [ ] Browser Sidebar: gradient ⚽ logo, green active nav item, sync status at bottom

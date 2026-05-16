# 亚盘押注决策 MVP — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 OddAlerts API 实测能力落到 v2 分支，让 Goalcast 在 ≤200ms 内呈现一场比赛的亚盘押注决策面板（双家盘口 + 模型 + 比分热力图 + form + 跌幅 + predictability）。

**Architecture:** 纯增量加表（`predictions`、`team_form`、`bookmaker_odds`），扩展现有 `GET /fixtures` 和 `GET /fixtures/{id}` 响应；前端新增 7 个组件，重写 MatchCard / MatchDetail / Matches。M1→M4 顺序依赖。

**Tech Stack:** Python 3.12 + FastAPI + aiosqlite + httpx + APScheduler；React 18 + TypeScript + Vite；pytest + pytest-asyncio + pytest-httpx。

**Spec:** `docs/superpowers/specs/2026-05-16-asian-handicap-mvp-design.md`

**Note vs. spec:** spec 里提到的 `migrations/0002_*.sql` 在本项目不存在——既有惯例是 `backend/database.py` 用 `CREATE TABLE IF NOT EXISTS`，本计划遵循该惯例。

---

## File Structure

### 新建（Create）

| 路径 | 责任 |
|---|---|
| `backend/scripts/backfill.py` | 首次启动按序跑 4 个 sync job |
| `backend/services/ah.py` | 主 AH 档推导（`derive_main_ah_line`） |
| `backend/tests/test_oddalerts_client.py` | OddAlerts 客户端新增方法单测 |
| `backend/tests/test_sync_jobs.py` | sync_* 4 个新 job 单测（mock httpx） |
| `backend/tests/test_services_ah.py` | 主 AH 档推导单测 |
| `frontend/src/components/shared/PredictabilityBadge.tsx` | predictability pill 标签 |
| `frontend/src/components/match/FormStrip.tsx` | "WWLDW" 彩色方块 |
| `frontend/src/components/match/OddsPair.tsx` | Pinnacle vs Bet365 赔率对比 |
| `frontend/src/components/match/AhLineSelector.tsx` | 详情页 AH 档下拉 |
| `frontend/src/components/match/AhLineTable.tsx` | 所有 AH 档表格 |
| `frontend/src/components/match/PredictionBars.tsx` | 模型概率条形图 |
| `frontend/src/components/match/ScorelineHeatmap.tsx` | 7×7 比分热力图 + AH 切片 |
| `frontend/src/lib/ahMath.ts` | AH 档 ↔ 比分映射工具函数 |

### 修改（Modify）

| 路径 | 改动 |
|---|---|
| `backend/database.py` | 加 3 张表 + ALTER fixtures.predictability + ALTER fixtures.season_id |
| `backend/services/oddalerts.py` | 加 5 个新方法 |
| `backend/services/sync.py` | 加 5 个新 sync 函数 + 注册到 scheduler |
| `backend/routers/fixtures.py` | `/fixtures` + `/fixtures/{id}` 响应/查询参数扩展 |
| `frontend/src/lib/api.ts` | 新类型 + 现有类型扩展 |
| `frontend/src/components/match/MatchCard.tsx` | 大改：双家盘口 + AI 行 + form + predictability |
| `frontend/src/pages/Matches.tsx` | filter chips + 默认 limit + 加载更多 |
| `frontend/src/pages/MatchDetail.tsx` | 5-block 重排，删 H2H block |
| `frontend/src/pages/Dashboard.tsx` | 3 栏 tile + top 5 跌赔 list |
| `frontend/src/index.css` | 新 design token |

### 不动（Untouched）

`backend/services/value_bets.py`、`backend/routers/odds.py`、`backend/routers/history.py`、`frontend/src/pages/ValueBets.tsx`、`frontend/src/pages/DroppingOdds.tsx`、`frontend/src/pages/History.tsx`。

---

# M1 — 后端地基

## Task 1.1：建库表

**Files:**
- Modify: `backend/database.py`
- Test: `backend/tests/test_database.py`

- [ ] **Step 1: Write the failing test**

在 `backend/tests/test_database.py` 末尾追加：

```python
import aiosqlite
import pytest

@pytest.mark.asyncio
async def test_new_tables_exist(tmp_path, monkeypatch):
    monkeypatch.setenv("GOALCAST_DB_PATH", str(tmp_path / "test.db"))
    import importlib, database
    importlib.reload(database)
    await database.init_db()
    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        cur = await db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        names = {row[0] for row in await cur.fetchall()}
    assert {"predictions", "team_form", "bookmaker_odds"}.issubset(names)

@pytest.mark.asyncio
async def test_fixtures_has_new_columns(tmp_path, monkeypatch):
    monkeypatch.setenv("GOALCAST_DB_PATH", str(tmp_path / "test.db"))
    import importlib, database
    importlib.reload(database)
    await database.init_db()
    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        cur = await db.execute("PRAGMA table_info(fixtures)")
        col_names = {row[1] for row in await cur.fetchall()}
    assert "predictability" in col_names
    assert "season_id" in col_names
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && .venv/bin/pytest tests/test_database.py -v
```

Expected: FAIL（新表 / 新列不存在）。

- [ ] **Step 3: Add DDLs to `backend/database.py`**

在现有 `CREATE_SYNC_LOG` 之后追加新表 DDL：

```python
CREATE_PREDICTIONS = """
CREATE TABLE IF NOT EXISTS predictions (
    fixture_id   INTEGER PRIMARY KEY REFERENCES fixtures(id),
    simulations  INTEGER NOT NULL DEFAULT 0,
    home_win     INTEGER, draw INTEGER, away_win INTEGER,
    btts         INTEGER,
    o15_goals    INTEGER, o25_goals INTEGER, o35_goals INTEGER, o45_goals INTEGER,
    scorelines   TEXT,
    updated_at   DATETIME NOT NULL
)
"""

CREATE_TEAM_FORM = """
CREATE TABLE IF NOT EXISTS team_form (
    team_id        INTEGER NOT NULL,
    season_id      INTEGER NOT NULL,
    form5_str      TEXT NOT NULL DEFAULT '',
    played         INTEGER, won INTEGER, drawn INTEGER, lost INTEGER,
    goals_for      INTEGER, goals_against INTEGER, goals_avg REAL,
    updated_at     DATETIME NOT NULL,
    PRIMARY KEY (team_id, season_id)
)
"""

CREATE_BOOKMAKER_ODDS = """
CREATE TABLE IF NOT EXISTS bookmaker_odds (
    fixture_id    INTEGER NOT NULL REFERENCES fixtures(id),
    bookmaker_id  INTEGER NOT NULL,
    market_id     INTEGER NOT NULL,
    outcome       TEXT NOT NULL,
    opening       REAL,
    current       REAL,
    peak          REAL,
    opening_at    DATETIME,
    current_at    DATETIME,
    PRIMARY KEY (fixture_id, bookmaker_id, market_id, outcome)
)
"""
CREATE_BO_IDX1 = "CREATE INDEX IF NOT EXISTS idx_bo_fix ON bookmaker_odds(fixture_id)"
CREATE_BO_IDX2 = "CREATE INDEX IF NOT EXISTS idx_bo_fix_market ON bookmaker_odds(fixture_id, market_id)"

ALTER_FIXTURES_PRED = "ALTER TABLE fixtures ADD COLUMN predictability TEXT"
ALTER_FIXTURES_SEASON = "ALTER TABLE fixtures ADD COLUMN season_id INTEGER"
```

修改 `init_db()` 函数：

```python
async def init_db() -> None:
    async with aiosqlite.connect(_db_path()) as db:
        for ddl in (
            CREATE_FIXTURES, CREATE_FIXTURES_IDX1, CREATE_FIXTURES_IDX2,
            CREATE_ODDS, CREATE_ODDS_IDX1, CREATE_ODDS_IDX2,
            CREATE_SYNC_LOG,
            CREATE_PREDICTIONS,
            CREATE_TEAM_FORM,
            CREATE_BOOKMAKER_ODDS, CREATE_BO_IDX1, CREATE_BO_IDX2,
        ):
            await db.execute(ddl)
        cur = await db.execute("PRAGMA table_info(fixtures)")
        existing = {row[1] for row in await cur.fetchall()}
        if "predictability" not in existing:
            await db.execute(ALTER_FIXTURES_PRED)
        if "season_id" not in existing:
            await db.execute(ALTER_FIXTURES_SEASON)
        await db.commit()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
.venv/bin/pytest tests/test_database.py -v
```

Expected: PASS（全部测试通过）。

- [ ] **Step 5: Commit**

```bash
git add backend/database.py backend/tests/test_database.py
git commit -m "feat(db): add predictions, team_form, bookmaker_odds tables + predictability/season_id columns"
```

---

## Task 1.2：OddAlerts 客户端新方法

**Files:**
- Modify: `backend/services/oddalerts.py`
- Test: `backend/tests/test_oddalerts_client.py` (new)

- [ ] **Step 1: Write failing tests**

创建 `backend/tests/test_oddalerts_client.py`：

```python
import pytest
from pytest_httpx import HTTPXMock

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("ODDALERTS_API_KEY", "TESTKEY")
    import importlib, config, services.oddalerts as oa
    importlib.reload(config); importlib.reload(oa)
    return oa.OddAlertClient()

@pytest.mark.asyncio
async def test_get_upcoming_fixtures(client, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://data.oddalerts.com/api/fixtures/upcoming?api_token=TESTKEY&page=1&per_page=250",
        json={"info": {"total": 2}, "data": [{"id": 1, "home_name": "A"}, {"id": 2, "home_name": "B"}]})
    items = await client.get_upcoming_fixtures(page=1, per_page=250)
    assert len(items) == 2 and items[0]["id"] == 1
    await client.aclose()

@pytest.mark.asyncio
async def test_get_season_stats_last_x(client, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://data.oddalerts.com/api/stats/season/999?api_token=TESTKEY&last_x=5_overall",
        json={"info": {"total": 1}, "data": [{"team_id": 11, "played": {"total": 5}, "won": {"total": 3}}]})
    rows = await client.get_season_stats_last_x(999, n=5)
    assert rows[0]["team_id"] == 11
    await client.aclose()

@pytest.mark.asyncio
async def test_get_odds_history_by_path(client, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://data.oddalerts.com/api/odds/history/77?api_token=TESTKEY",
        json={"info": {"count": 1}, "data": [{"fixture_id": 77, "market_id": 51, "outcome": "home_m05",
                                                "opening": "1.90", "closing": "1.85", "peak": "1.95",
                                                "bookmaker_id": 1, "bookmaker_name": "Pinnacle"}]})
    rows = await client.get_odds_history_by_path(77)
    assert rows[0]["outcome"] == "home_m05"
    await client.aclose()

@pytest.mark.asyncio
async def test_get_odds_history_handles_false_body(client, httpx_mock: HTTPXMock):
    # API quirk: returns plain `false` (boolean) when no data
    httpx_mock.add_response(
        url="https://data.oddalerts.com/api/odds/history/77?api_token=TESTKEY",
        json=False)
    rows = await client.get_odds_history_by_path(77)
    assert rows == []
    await client.aclose()

@pytest.mark.asyncio
async def test_get_odds_latest(client, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://data.oddalerts.com/api/odds/latest?api_token=TESTKEY&bookmakers=1%2C2&markets=6%2C51&per_page=500&page=1",
        json={"info": {"page": 1}, "data": [{"fixture_id": 77, "market_id": 6, "outcome": "home",
                                              "odds": 1.95, "unix": 1779000000, "bookmaker_id": 1,
                                              "bookmaker_name": "Pinnacle"}]})
    rows = await client.get_odds_latest(bookmakers="1,2", markets="6,51", per_page=500, page=1)
    assert rows[0]["fixture_id"] == 77
    await client.aclose()

@pytest.mark.asyncio
async def test_get_predictions_multiple(client, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://data.oddalerts.com/api/predictions/generate/multiple?api_token=TESTKEY&ids=1%2C2",
        json={"info": {"results": 2}, "data": [{"fixture_id": 1, "simulations": 50000, "home_win": 28000},
                                                 {"fixture_id": 2, "simulations": 50000, "home_win": 18000}]})
    rows = await client.get_predictions_multiple([1, 2])
    assert len(rows) == 2
    await client.aclose()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/pytest tests/test_oddalerts_client.py -v
```

Expected: FAIL（5 个新方法不存在）。

- [ ] **Step 3: Add methods to `backend/services/oddalerts.py`**

在 `OddAlertClient` 类内追加（保留现有 5 个方法）：

```python
async def get_upcoming_fixtures(self, page: int = 1, per_page: int = 250) -> list[dict]:
    r = await self._client.get("/fixtures/upcoming", params={"page": page, "per_page": per_page})
    r.raise_for_status()
    raw = r.json()
    return raw.get("data", []) if isinstance(raw, dict) else []

async def get_season_stats_last_x(self, season_id: int, n: int = 5, location: str = "overall") -> list[dict]:
    r = await self._client.get(f"/stats/season/{season_id}", params={"last_x": f"{n}_{location}"})
    r.raise_for_status()
    raw = r.json()
    return raw.get("data", []) if isinstance(raw, dict) else []

async def get_odds_history_by_path(self, fixture_id: int) -> list[dict]:
    r = await self._client.get(f"/odds/history/{fixture_id}")
    r.raise_for_status()
    raw = r.json()
    if isinstance(raw, bool):
        return []
    return raw.get("data", []) if isinstance(raw, dict) else []

async def get_odds_latest(self, bookmakers: str = "1,2", markets: str = "6,51",
                          per_page: int = 500, page: int = 1) -> list[dict]:
    r = await self._client.get("/odds/latest", params={"bookmakers": bookmakers,
                                                         "markets": markets,
                                                         "per_page": per_page,
                                                         "page": page})
    r.raise_for_status()
    raw = r.json()
    return raw.get("data", []) if isinstance(raw, dict) else []

async def get_predictions_multiple(self, fixture_ids: list[int]) -> list[dict]:
    ids = ",".join(str(i) for i in fixture_ids)
    r = await self._client.get("/predictions/generate/multiple", params={"ids": ids})
    r.raise_for_status()
    raw = r.json()
    return raw.get("data", []) if isinstance(raw, dict) else []
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest tests/test_oddalerts_client.py -v
```

Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/services/oddalerts.py backend/tests/test_oddalerts_client.py
git commit -m "feat(client): add OddAlerts methods for upcoming, season_stats, odds_history/latest, predictions"
```

---

## Task 1.3：`sync_fixtures_upcoming` 主源同步

**Files:**
- Modify: `backend/services/sync.py`
- Test: `backend/tests/test_sync_jobs.py` (new)

- [ ] **Step 1: Write failing test**

新建 `backend/tests/test_sync_jobs.py`：

```python
import json
import aiosqlite
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_sync_fixtures_upcoming_inserts(tmp_path, monkeypatch):
    monkeypatch.setenv("GOALCAST_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("ODDALERTS_API_KEY", "K")
    import importlib, config, database, services.oddalerts as oa, services.sync as sync
    for m in (config, database, oa, sync): importlib.reload(m)
    await database.init_db()

    fake = [
        {"id": 100, "home_name": "A", "away_name": "B", "home_id": 11, "away_id": 22,
         "competition_id": 1, "competition_name": "L1", "competition_predictability": "medium",
         "season_id": 5, "unix": 1779000000, "status": "NS"},
        {"id": 101, "home_name": "C", "away_name": "D", "home_id": 33, "away_id": 44,
         "competition_id": 1, "competition_name": "L1", "competition_predictability": "high",
         "season_id": 5, "unix": 1779001000, "status": "NS"},
    ]
    with patch.object(oa.oddalerts_client, "get_upcoming_fixtures",
                       new=AsyncMock(side_effect=[fake, []])):
        await sync.sync_fixtures_upcoming()

    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        cur = await db.execute(
            "SELECT id, home_team, predictability, home_team_id, season_id FROM fixtures ORDER BY id"
        )
        rows = await cur.fetchall()
    assert len(rows) == 2
    assert rows[0] == (100, "A", "medium", 11, 5)
    assert rows[1] == (101, "C", "high", 33, 5)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/bin/pytest tests/test_sync_jobs.py::test_sync_fixtures_upcoming_inserts -v
```

Expected: FAIL (`sync_fixtures_upcoming` 不存在).

- [ ] **Step 3: Implement `sync_fixtures_upcoming`**

在 `backend/services/sync.py` 末尾（在既有函数下方、`scheduler.add_job` 之前）添加：

```python
async def sync_fixtures_upcoming() -> None:
    started = _now()
    async with aiosqlite.connect(_db_path()) as db:
        try:
            page = 1
            upserted = 0
            while True:
                items = await oddalerts_client.get_upcoming_fixtures(page=page, per_page=250)
                if not items:
                    break
                now = _now()
                for it in items:
                    fid = it.get("id")
                    if not fid:
                        continue
                    kickoff = _from_unix(it.get("unix"))
                    await db.execute(
                        """INSERT INTO fixtures
                           (id,competition_id,competition_name,home_team,away_team,
                            home_team_id,away_team_id,season_id,kickoff_utc,status,
                            predictability,fetched_at,updated_at)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
                           ON CONFLICT(id) DO UPDATE SET
                             kickoff_utc=excluded.kickoff_utc,
                             status=excluded.status,
                             predictability=excluded.predictability,
                             home_team_id=excluded.home_team_id,
                             away_team_id=excluded.away_team_id,
                             season_id=excluded.season_id,
                             updated_at=excluded.updated_at""",
                        (fid,
                         it.get("competition_id", 0),
                         it.get("competition_name", ""),
                         it.get("home_name", ""),
                         it.get("away_name", ""),
                         it.get("home_id"), it.get("away_id"),
                         it.get("season_id"),
                         kickoff, it.get("status", "NS"),
                         it.get("competition_predictability"),
                         now, now),
                    )
                    upserted += 1
                page += 1
                if len(items) < 250:
                    break
            await db.commit()
            await _log(db, "fixtures_upcoming", "ok", upserted, started_at=started)
            await db.commit()
        except Exception as exc:
            await _log(db, "fixtures_upcoming", "error", error_msg=str(exc), started_at=started)
            await db.commit()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
.venv/bin/pytest tests/test_sync_jobs.py::test_sync_fixtures_upcoming_inserts -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/services/sync.py backend/tests/test_sync_jobs.py
git commit -m "feat(sync): add sync_fixtures_upcoming as primary fixture source"
```

---

## Task 1.4：`sync_team_form` 近 5 场

**Files:**
- Modify: `backend/services/sync.py`
- Test: `backend/tests/test_sync_jobs.py`

- [ ] **Step 1: Write failing test**

在 `tests/test_sync_jobs.py` 末尾追加：

```python
@pytest.mark.asyncio
async def test_sync_team_form_inserts(tmp_path, monkeypatch):
    monkeypatch.setenv("GOALCAST_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("ODDALERTS_API_KEY", "K")
    import importlib, config, database, services.oddalerts as oa, services.sync as sync
    for m in (config, database, oa, sync): importlib.reload(m)
    await database.init_db()
    now = "2026-05-16T00:00:00"
    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        await db.execute(
            """INSERT INTO fixtures
               (id,competition_id,competition_name,home_team,away_team,home_team_id,away_team_id,
                season_id,kickoff_utc,status,fetched_at,updated_at)
               VALUES(100,1,'L1','A','B',11,22,5,'2026-05-20T00:00:00','NS',?,?)""",
            (now, now),
        )
        await db.commit()

    fake_rows = [{
        "team_id": 11, "season_id": 5, "name": "A",
        "played": {"total": 5}, "won": {"total": 3}, "drawn": {"total": 1}, "lost": {"total": 1},
        "goals_for": {"total": 8}, "goals_against": {"total": 4},
        "goals_total": {"total_avg": 2.4},
        "form_overall": "WDWLW"
    }]
    with patch.object(oa.oddalerts_client, "get_season_stats_last_x",
                       new=AsyncMock(return_value=fake_rows)):
        await sync.sync_team_form(season_ids=[5])

    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        cur = await db.execute(
            "SELECT team_id, season_id, form5_str, played, won, goals_for FROM team_form"
        )
        rows = await cur.fetchall()
    assert rows[0] == (11, 5, "WDWLW", 5, 3, 8)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/bin/pytest tests/test_sync_jobs.py::test_sync_team_form_inserts -v
```

Expected: FAIL.

- [ ] **Step 3: Implement `sync_team_form`**

在 `backend/services/sync.py` 添加：

```python
def _build_form5(raw: dict) -> str:
    """Prefer API-provided form string; fallback to empty."""
    s = raw.get("form_overall") or raw.get("form") or ""
    if isinstance(s, str) and s:
        return s[:5].upper()
    return ""

async def sync_team_form(season_ids: list[int] | None = None) -> None:
    started = _now()
    async with aiosqlite.connect(_db_path()) as db:
        try:
            if season_ids is None:
                cur = await db.execute(
                    """SELECT DISTINCT season_id FROM fixtures
                       WHERE kickoff_utc >= datetime('now') AND season_id IS NOT NULL"""
                )
                season_ids = [int(r[0]) for r in await cur.fetchall()]
            now = _now()
            count = 0
            for sid in season_ids:
                rows = await oddalerts_client.get_season_stats_last_x(sid, n=5)
                for r in rows:
                    tid = r.get("team_id")
                    if not tid:
                        continue
                    played = (r.get("played") or {}).get("total")
                    won = (r.get("won") or {}).get("total")
                    drawn = (r.get("drawn") or {}).get("total")
                    lost = (r.get("lost") or {}).get("total")
                    gf = (r.get("goals_for") or {}).get("total")
                    ga = (r.get("goals_against") or {}).get("total")
                    g_avg = (r.get("goals_total") or {}).get("total_avg")
                    await db.execute(
                        """INSERT INTO team_form
                           (team_id,season_id,form5_str,played,won,drawn,lost,
                            goals_for,goals_against,goals_avg,updated_at)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?)
                           ON CONFLICT(team_id, season_id) DO UPDATE SET
                             form5_str=excluded.form5_str, played=excluded.played,
                             won=excluded.won, drawn=excluded.drawn, lost=excluded.lost,
                             goals_for=excluded.goals_for, goals_against=excluded.goals_against,
                             goals_avg=excluded.goals_avg, updated_at=excluded.updated_at""",
                        (tid, sid, _build_form5(r), played, won, drawn, lost,
                         gf, ga, g_avg, now),
                    )
                    count += 1
            await db.commit()
            await _log(db, "team_form", "ok", count, started_at=started)
            await db.commit()
        except Exception as exc:
            await _log(db, "team_form", "error", error_msg=str(exc), started_at=started)
            await db.commit()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
.venv/bin/pytest tests/test_sync_jobs.py::test_sync_team_form_inserts -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/services/sync.py backend/tests/test_sync_jobs.py
git commit -m "feat(sync): add sync_team_form for last-5 form"
```

---

## Task 1.5：`sync_ah_odds_seed` AH 赔率 seed

**Files:**
- Modify: `backend/services/sync.py`
- Test: `backend/tests/test_sync_jobs.py`

- [ ] **Step 1: Write failing test**

追加到 `tests/test_sync_jobs.py`：

```python
@pytest.mark.asyncio
async def test_sync_ah_odds_seed_filters_bookmakers(tmp_path, monkeypatch):
    monkeypatch.setenv("GOALCAST_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("ODDALERTS_API_KEY", "K")
    import importlib, config, database, services.oddalerts as oa, services.sync as sync
    for m in (config, database, oa, sync): importlib.reload(m)
    await database.init_db()
    now = "2026-05-16T00:00:00"
    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        await db.execute(
            """INSERT INTO fixtures
               (id,competition_id,competition_name,home_team,away_team,home_team_id,away_team_id,
                kickoff_utc,status,fetched_at,updated_at)
               VALUES(200,1,'L','A','B',11,22,'2026-05-20T00:00:00','NS',?,?)""",
            (now, now),
        )
        await db.commit()

    history = [
        {"fixture_id": 200, "market_id": 51, "outcome": "home_m05",
         "opening": "1.92", "closing": "1.85", "peak": "1.95",
         "bookmaker_id": 1, "bookmaker_name": "Pinnacle"},
        {"fixture_id": 200, "market_id": 6, "outcome": "home",
         "opening": "2.05", "closing": "1.95", "peak": "2.10",
         "bookmaker_id": 2, "bookmaker_name": "Bet365"},
        {"fixture_id": 200, "market_id": 6, "outcome": "home",
         "opening": "2.00", "closing": "1.92", "peak": "2.00",
         "bookmaker_id": 7, "bookmaker_name": "Betano"},
    ]
    with patch.object(oa.oddalerts_client, "get_odds_history_by_path",
                       new=AsyncMock(return_value=history)):
        await sync.sync_ah_odds_seed(fixture_ids=[200])

    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        cur = await db.execute(
            "SELECT bookmaker_id, market_id, outcome, opening, current FROM bookmaker_odds ORDER BY bookmaker_id"
        )
        rows = await cur.fetchall()
    assert len(rows) == 2   # Betano dropped
    assert (rows[0][0], rows[0][1], rows[0][2]) == (1, 51, "home_m05")
    assert rows[0][3] == 1.92 and rows[0][4] == 1.85
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/bin/pytest tests/test_sync_jobs.py::test_sync_ah_odds_seed_filters_bookmakers -v
```

Expected: FAIL.

- [ ] **Step 3: Implement `sync_ah_odds_seed`**

在 `backend/services/sync.py` 添加：

```python
TARGET_BOOKMAKERS = {1, 2}    # Pinnacle, Bet365
TARGET_MARKETS = {6, 51}      # ft_result, asian_handicap

async def sync_ah_odds_seed(fixture_ids: list[int] | None = None) -> None:
    started = _now()
    async with aiosqlite.connect(_db_path()) as db:
        try:
            if fixture_ids is None:
                cur = await db.execute(
                    """SELECT f.id FROM fixtures f
                       LEFT JOIN bookmaker_odds bo ON bo.fixture_id=f.id
                       WHERE f.kickoff_utc >= datetime('now') AND bo.fixture_id IS NULL"""
                )
                fixture_ids = [int(r[0]) for r in await cur.fetchall()]
            now = _now()
            count = 0
            for fid in fixture_ids:
                rows = await oddalerts_client.get_odds_history_by_path(fid)
                for r in rows:
                    bk = r.get("bookmaker_id"); mk = r.get("market_id")
                    if bk not in TARGET_BOOKMAKERS or mk not in TARGET_MARKETS:
                        continue
                    opening = float(r["opening"]) if r.get("opening") else None
                    closing = float(r["closing"]) if r.get("closing") else None
                    peak = float(r["peak"]) if r.get("peak") else None
                    await db.execute(
                        """INSERT INTO bookmaker_odds
                           (fixture_id,bookmaker_id,market_id,outcome,
                            opening,current,peak,opening_at,current_at)
                           VALUES(?,?,?,?,?,?,?,?,?)
                           ON CONFLICT(fixture_id,bookmaker_id,market_id,outcome) DO UPDATE SET
                             opening=COALESCE(bookmaker_odds.opening, excluded.opening),
                             current=excluded.current,
                             peak=MAX(IFNULL(bookmaker_odds.peak,0), IFNULL(excluded.peak,0)),
                             opening_at=COALESCE(bookmaker_odds.opening_at, excluded.opening_at),
                             current_at=excluded.current_at""",
                        (fid, bk, mk, r.get("outcome", ""),
                         opening, closing, peak, now, now),
                    )
                    count += 1
            await db.commit()
            await _log(db, "ah_odds_seed", "ok", count, started_at=started)
            await db.commit()
        except Exception as exc:
            await _log(db, "ah_odds_seed", "error", error_msg=str(exc), started_at=started)
            await db.commit()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
.venv/bin/pytest tests/test_sync_jobs.py::test_sync_ah_odds_seed_filters_bookmakers -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/services/sync.py backend/tests/test_sync_jobs.py
git commit -m "feat(sync): add sync_ah_odds_seed with bookmaker/market filtering"
```

---

## Task 1.6：`sync_ah_odds_latest` 流式更新

**Files:**
- Modify: `backend/services/sync.py`
- Test: `backend/tests/test_sync_jobs.py`

- [ ] **Step 1: Write failing test**

追加：

```python
@pytest.mark.asyncio
async def test_sync_ah_odds_latest_preserves_opening(tmp_path, monkeypatch):
    monkeypatch.setenv("GOALCAST_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("ODDALERTS_API_KEY", "K")
    import importlib, config, database, services.oddalerts as oa, services.sync as sync
    for m in (config, database, oa, sync): importlib.reload(m)
    await database.init_db()
    now = "2026-05-16T00:00:00"
    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        await db.execute(
            """INSERT INTO fixtures
               (id,competition_id,competition_name,home_team,away_team,
                kickoff_utc,status,fetched_at,updated_at)
               VALUES(300,1,'L','A','B','2026-05-20T00:00:00','NS',?,?)""",
            (now, now),
        )
        await db.execute(
            """INSERT INTO bookmaker_odds
               (fixture_id,bookmaker_id,market_id,outcome,opening,current,peak,opening_at,current_at)
               VALUES(300,1,6,'home',2.10,2.10,2.10,?,?)""",
            (now, now),
        )
        await db.commit()

    latest = [{"fixture_id": 300, "market_id": 6, "outcome": "home", "odds": 1.95,
               "unix": 1779000000, "bookmaker_id": 1, "bookmaker_name": "Pinnacle"}]
    with patch.object(oa.oddalerts_client, "get_odds_latest",
                       new=AsyncMock(side_effect=[latest, []])):
        await sync.sync_ah_odds_latest()

    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        cur = await db.execute(
            "SELECT current, opening FROM bookmaker_odds WHERE fixture_id=300 AND bookmaker_id=1 AND market_id=6 AND outcome='home'"
        )
        rows = await cur.fetchall()
    assert rows[0] == (1.95, 2.10)   # current updated, opening preserved
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/bin/pytest tests/test_sync_jobs.py::test_sync_ah_odds_latest_preserves_opening -v
```

Expected: FAIL.

- [ ] **Step 3: Implement `sync_ah_odds_latest`**

```python
async def sync_ah_odds_latest(max_pages: int = 20) -> None:
    started = _now()
    async with aiosqlite.connect(_db_path()) as db:
        try:
            now = _now()
            count = 0
            for page in range(1, max_pages + 1):
                items = await oddalerts_client.get_odds_latest(
                    bookmakers="1,2", markets="6,51", per_page=500, page=page
                )
                if not items:
                    break
                for r in items:
                    bk = r.get("bookmaker_id"); mk = r.get("market_id")
                    if bk not in TARGET_BOOKMAKERS or mk not in TARGET_MARKETS:
                        continue
                    fid = r.get("fixture_id"); odds = r.get("odds")
                    if not fid or odds is None:
                        continue
                    o = float(odds)
                    await db.execute(
                        """INSERT INTO bookmaker_odds
                           (fixture_id,bookmaker_id,market_id,outcome,
                            opening,current,peak,opening_at,current_at)
                           VALUES(?,?,?,?,?,?,?,?,?)
                           ON CONFLICT(fixture_id,bookmaker_id,market_id,outcome) DO UPDATE SET
                             current=excluded.current,
                             peak=MAX(IFNULL(bookmaker_odds.peak,0), excluded.current),
                             current_at=excluded.current_at""",
                        (fid, bk, mk, r.get("outcome", ""),
                         o, o, o, now, now),
                    )
                    count += 1
                if len(items) < 500:
                    break
            await db.commit()
            await _log(db, "ah_odds_latest", "ok", count, started_at=started)
            await db.commit()
        except Exception as exc:
            await _log(db, "ah_odds_latest", "error", error_msg=str(exc), started_at=started)
            await db.commit()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
.venv/bin/pytest tests/test_sync_jobs.py -v
```

Expected: 全 PASS。

- [ ] **Step 5: Commit**

```bash
git add backend/services/sync.py backend/tests/test_sync_jobs.py
git commit -m "feat(sync): add sync_ah_odds_latest for 5-min current odds refresh"
```

---

## Task 1.7：注册新 sync job 到 scheduler

**Files:**
- Modify: `backend/services/sync.py`（末尾）

- [ ] **Step 1: Add jobs to scheduler**

在文件末尾的 `scheduler.add_job` 区域追加：

```python
scheduler.add_job(sync_fixtures_upcoming, "interval", hours=1, id="fixtures_upcoming")
scheduler.add_job(sync_ah_odds_latest, "interval", minutes=5, id="ah_odds_latest")
scheduler.add_job(sync_team_form, "interval", hours=6, id="team_form")
scheduler.add_job(sync_ah_odds_seed, "interval", hours=12, id="ah_odds_seed")
```

修改 `sync_fixtures_upcoming` 末尾在 `_log` 之后追加链式触发：

```python
            await _log(db, "fixtures_upcoming", "ok", upserted, started_at=started)
            await db.commit()
            # chain: seed odds for fixtures that have no bookmaker_odds rows yet
            cur = await db.execute(
                """SELECT f.id FROM fixtures f
                   LEFT JOIN bookmaker_odds bo ON bo.fixture_id=f.id
                   WHERE f.kickoff_utc >= datetime('now') AND bo.fixture_id IS NULL
                   LIMIT 200"""
            )
            new_fids = [int(r[0]) for r in await cur.fetchall()]
        except Exception as exc:
            await _log(db, "fixtures_upcoming", "error", error_msg=str(exc), started_at=started)
            await db.commit()
            return
    if new_fids:
        await sync_ah_odds_seed(fixture_ids=new_fids)
```

注意：上面把 chain 放在 `try` 末尾，`db.commit()` 之后；`return` 在 except 内确保失败不连锁；`sync_ah_odds_seed` 在 `with` 块外调用（用独立连接）。

- [ ] **Step 2: Run regression test**

```bash
.venv/bin/pytest tests/test_sync_jobs.py tests/test_database.py -v
```

Expected: 全 PASS。

- [ ] **Step 3: Commit**

```bash
git add backend/services/sync.py
git commit -m "feat(sync): register new jobs and chain seed after fixtures_upcoming"
```

---

## Task 1.8：首次启动 backfill 脚本

**Files:**
- Create: `backend/scripts/backfill.py`
- Create: `backend/scripts/__init__.py`（空文件）

- [ ] **Step 1: Create scripts dir + backfill**

```bash
mkdir -p backend/scripts && touch backend/scripts/__init__.py
```

写入 `backend/scripts/backfill.py`：

```python
"""One-shot backfill on first deployment: runs jobs in dependency order
so prepopulated tables exist when later jobs read them.

Usage:
    cd backend && .venv/bin/python -m scripts.backfill
"""
import asyncio
from database import init_db
from services.sync import (
    sync_fixtures_upcoming, sync_team_form, sync_ah_odds_seed,
)

async def main() -> None:
    await init_db()
    print("[1/3] fixtures_upcoming…")
    await sync_fixtures_upcoming()
    print("[2/3] team_form…")
    await sync_team_form()
    print("[3/3] ah_odds_seed…")
    await sync_ah_odds_seed()
    print("done.")

if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Import smoke test**

```bash
cd backend && .venv/bin/python -c "import scripts.backfill"
```

Expected: 无 import 错误。

- [ ] **Step 3: Commit**

```bash
git add backend/scripts/
git commit -m "feat(scripts): add first-deploy backfill script"
```

---

# M2 — Predictions + Backend API

## Task 2.1：`/predictions/generate/multiple` 最大批次 spike

**Files:** 临时脚本 `backend/scripts/spike_predictions_batch.py`（**不 commit**）

- [ ] **Step 1: Write spike script**

```python
"""Run once to discover the practical batch size limit. Not committed."""
import asyncio
from services.oddalerts import oddalerts_client

async def main():
    items = await oddalerts_client.get_trends("homeWin")
    ids = [x["id"] for x in items[:100]]
    for n in (10, 25, 50, 100):
        try:
            r = await oddalerts_client.get_predictions_multiple(ids[:n])
            print(f"batch={n}  got={len(r)}  ok")
        except Exception as e:
            print(f"batch={n}  FAIL: {e!r}")
    await oddalerts_client.aclose()

asyncio.run(main())
```

- [ ] **Step 2: Run spike**

```bash
cd backend && .venv/bin/python -m scripts.spike_predictions_batch
```

记录每个批量级别的成败。

- [ ] **Step 3: Adjust BATCH_SIZE in Task 2.2**

把实测可用最大值除以 2 作为安全默认（譬如能跑通 50 → 用 25）。

- [ ] **Step 4: Delete spike script**

```bash
rm backend/scripts/spike_predictions_batch.py
```

不进 git。

---

## Task 2.2：`sync_predictions` 同步

**Files:**
- Modify: `backend/services/sync.py`
- Modify: `backend/scripts/backfill.py`
- Test: `backend/tests/test_sync_jobs.py`

- [ ] **Step 1: Write failing test**

```python
@pytest.mark.asyncio
async def test_sync_predictions_filters_poor(tmp_path, monkeypatch):
    monkeypatch.setenv("GOALCAST_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("ODDALERTS_API_KEY", "K")
    import importlib, config, database, services.oddalerts as oa, services.sync as sync
    for m in (config, database, oa, sync): importlib.reload(m)
    await database.init_db()
    now = "2026-05-16T00:00:00"
    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        for fid, pred in [(401, "poor"), (402, "medium")]:
            await db.execute(
                """INSERT INTO fixtures
                   (id,competition_id,competition_name,home_team,away_team,
                    kickoff_utc,status,predictability,fetched_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (fid, 1, "L", "A", "B", "2026-05-20T00:00:00", "NS", pred, now, now),
            )
        await db.commit()

    fake = [{"fixture_id": 402, "simulations": 50000,
             "home_win": 28000, "draw": 12000, "away_win": 10000,
             "btts": 22000, "o15_goals": 35000, "o25_goals": 22000,
             "o35_goals": 11000, "o45_goals": 5000,
             "scorelines": {"1-0": 13.44, "2-0": 11.87}}]
    with patch.object(oa.oddalerts_client, "get_predictions_multiple",
                       new=AsyncMock(return_value=fake)):
        await sync.sync_predictions()

    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        cur = await db.execute("SELECT fixture_id, home_win, scorelines FROM predictions")
        rows = await cur.fetchall()
    assert len(rows) == 1   # poor was filtered
    assert rows[0][0] == 402
    assert rows[0][1] == 28000
    assert json.loads(rows[0][2])["1-0"] == 13.44
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/bin/pytest tests/test_sync_jobs.py::test_sync_predictions_filters_poor -v
```

Expected: FAIL.

- [ ] **Step 3: Implement `sync_predictions`**

在 `backend/services/sync.py` 添加：

```python
BATCH_SIZE = 25   # set after Task 2.1 spike result

async def sync_predictions() -> None:
    started = _now()
    async with aiosqlite.connect(_db_path()) as db:
        try:
            cur = await db.execute(
                """SELECT id FROM fixtures
                   WHERE kickoff_utc >= datetime('now')
                     AND (predictability IS NULL OR predictability != 'poor')"""
            )
            fids = [int(r[0]) for r in await cur.fetchall()]
            now = _now()
            count = 0
            for i in range(0, len(fids), BATCH_SIZE):
                batch = fids[i:i+BATCH_SIZE]
                items = await oddalerts_client.get_predictions_multiple(batch)
                for r in items:
                    fid = r.get("fixture_id")
                    if not fid:
                        continue
                    await db.execute(
                        """INSERT INTO predictions
                           (fixture_id,simulations,home_win,draw,away_win,btts,
                            o15_goals,o25_goals,o35_goals,o45_goals,
                            scorelines,updated_at)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                           ON CONFLICT(fixture_id) DO UPDATE SET
                             simulations=excluded.simulations,
                             home_win=excluded.home_win, draw=excluded.draw,
                             away_win=excluded.away_win, btts=excluded.btts,
                             o15_goals=excluded.o15_goals, o25_goals=excluded.o25_goals,
                             o35_goals=excluded.o35_goals, o45_goals=excluded.o45_goals,
                             scorelines=excluded.scorelines, updated_at=excluded.updated_at""",
                        (fid, r.get("simulations", 0),
                         r.get("home_win"), r.get("draw"), r.get("away_win"),
                         r.get("btts"),
                         r.get("o15_goals"), r.get("o25_goals"),
                         r.get("o35_goals"), r.get("o45_goals"),
                         json.dumps(r.get("scorelines") or {}), now),
                    )
                    count += 1
            await db.commit()
            await _log(db, "predictions", "ok", count, started_at=started)
            await db.commit()
        except Exception as exc:
            await _log(db, "predictions", "error", error_msg=str(exc), started_at=started)
            await db.commit()
```

注册到 scheduler：

```python
scheduler.add_job(sync_predictions, "interval", hours=6, id="predictions")
```

更新 `backend/scripts/backfill.py`（在 ah_odds_seed 之后追加）：

```python
from services.sync import (
    sync_fixtures_upcoming, sync_team_form, sync_ah_odds_seed, sync_predictions,
)

async def main() -> None:
    await init_db()
    print("[1/4] fixtures_upcoming…");  await sync_fixtures_upcoming()
    print("[2/4] team_form…");          await sync_team_form()
    print("[3/4] ah_odds_seed…");       await sync_ah_odds_seed()
    print("[4/4] predictions…");        await sync_predictions()
    print("done.")
```

- [ ] **Step 4: Run test to verify it passes**

```bash
.venv/bin/pytest tests/test_sync_jobs.py::test_sync_predictions_filters_poor -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/services/sync.py backend/tests/test_sync_jobs.py backend/scripts/backfill.py
git commit -m "feat(sync): add sync_predictions with predictability filter + scheduler reg"
```

---

## Task 2.3：`derive_main_ah_line` 推导函数

**Files:**
- Create: `backend/services/ah.py`
- Test: `backend/tests/test_services_ah.py`

- [ ] **Step 1: Write failing tests**

新建 `backend/tests/test_services_ah.py`：

```python
import pytest
from services.ah import derive_main_ah_line, parse_ah_outcome_line

def test_parse_home_minus_05():
    assert parse_ah_outcome_line("home_m05") == ("home", -0.5)

def test_parse_away_plus_075():
    assert parse_ah_outcome_line("away_p075") == ("away", 0.75)

def test_parse_away_plus_125():
    assert parse_ah_outcome_line("away_p125") == ("away", 1.25)

def test_parse_home_zero():
    assert parse_ah_outcome_line("home_0") == ("home", 0.0)

def test_parse_invalid():
    assert parse_ah_outcome_line("home") is None
    assert parse_ah_outcome_line("draw") is None

def test_derive_picks_closest_to_even():
    rows = [
        {"market_id": 51, "outcome": "home_m05",  "current": 2.30, "bookmaker_id": 1},
        {"market_id": 51, "outcome": "away_p05",  "current": 1.65, "bookmaker_id": 1},
        {"market_id": 51, "outcome": "home_m025", "current": 1.95, "bookmaker_id": 1},
        {"market_id": 51, "outcome": "away_p025", "current": 1.90, "bookmaker_id": 1},  # closest
    ]
    line, h, a = derive_main_ah_line(rows, bookmaker_id=1)
    assert line == -0.25
    assert h == 1.95 and a == 1.90

def test_derive_returns_none_when_no_data():
    assert derive_main_ah_line([], bookmaker_id=1) is None

def test_derive_skips_other_bookmakers():
    rows = [
        {"market_id": 51, "outcome": "home_m05", "current": 1.85, "bookmaker_id": 2},
        {"market_id": 51, "outcome": "away_p05", "current": 1.95, "bookmaker_id": 2},
    ]
    assert derive_main_ah_line(rows, bookmaker_id=1) is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/pytest tests/test_services_ah.py -v
```

Expected: FAIL（模块不存在）。

- [ ] **Step 3: Implement `backend/services/ah.py`**

```python
"""Asian Handicap outcome parsing + main-line derivation."""
import re

_RE = re.compile(r"^(home|away)_(?:(m|p)?(\d+))$")

def parse_ah_outcome_line(outcome: str) -> tuple[str, float] | None:
    """'home_m05' -> ('home', -0.5);  'away_p075' -> ('away', 0.75);
       'home_0'   -> ('home', 0.0);   anything else -> None."""
    m = _RE.match(outcome)
    if not m:
        return None
    side, sign, digits = m.group(1), m.group(2), m.group(3)
    if digits == "0":
        return side, 0.0
    if len(digits) == 1:
        raw = float(digits)
    elif len(digits) == 2:
        raw = float(digits[0]) + (0.5 if digits[1] == "5" else 0.0)
    elif len(digits) == 3:
        # '075' -> 0.75;  '125' -> 1.25
        raw = float(digits[0]) + float(digits[1:]) / 100
    else:
        return None
    sign_val = -1 if sign == "m" else 1
    return side, sign_val * raw

def derive_main_ah_line(rows: list[dict], bookmaker_id: int) -> tuple[float, float, float] | None:
    """Return (line, home_odds, away_odds) for the AH line whose two-side odds are
    closest to each other for the given bookmaker. `line` is from home perspective."""
    buckets: dict[float, dict[str, float]] = {}
    for r in rows:
        if r.get("bookmaker_id") != bookmaker_id or r.get("market_id") != 51:
            continue
        parsed = parse_ah_outcome_line(r.get("outcome", ""))
        if parsed is None:
            continue
        side, line = parsed
        home_line = line if side == "home" else -line
        b = buckets.setdefault(home_line, {})
        odds = r.get("current") or 0
        try:
            o = float(odds)
        except (TypeError, ValueError):
            continue
        b[side] = o
    candidates = [(ln, b["home"], b["away"]) for ln, b in buckets.items()
                  if "home" in b and "away" in b and b["home"] > 0 and b["away"] > 0]
    if not candidates:
        return None
    return min(candidates, key=lambda t: abs(t[1] - t[2]))
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest tests/test_services_ah.py -v
```

Expected: PASS (8 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/services/ah.py backend/tests/test_services_ah.py
git commit -m "feat(ah): outcome parser + main-line derivation by closest-to-even odds"
```

---

## Task 2.4：`GET /fixtures` 列表响应扩展

**Files:**
- Modify: `backend/routers/fixtures.py`
- Test: `backend/tests/test_routers_fixtures.py`

- [ ] **Step 1: Write failing test**

追加到 `tests/test_routers_fixtures.py`：

```python
@pytest.mark.asyncio
async def test_list_fixtures_returns_predictability_form_odds(tmp_path, monkeypatch):
    monkeypatch.setenv("GOALCAST_DB_PATH", str(tmp_path / "test.db"))
    import importlib, database, main
    importlib.reload(database)
    await database.init_db()
    now = "2026-05-15T15:00:00"
    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        await db.execute(
            """INSERT INTO fixtures
               (id,competition_id,competition_name,home_team,away_team,
                home_team_id,away_team_id,season_id,kickoff_utc,status,predictability,
                fetched_at,updated_at)
               VALUES(1,101,'Premier League','Arsenal','Chelsea',11,22,55,
                      '2026-05-15T15:00:00','pre','high',?,?)""",
            (now, now),
        )
        await db.execute(
            """INSERT INTO team_form
               (team_id,season_id,form5_str,played,won,drawn,lost,
                goals_for,goals_against,goals_avg,updated_at)
               VALUES(11,55,'WWLDW',5,3,1,1,8,4,2.4,?)""",
            (now,),
        )
        await db.execute(
            """INSERT INTO predictions
               (fixture_id,simulations,home_win,draw,away_win,btts,o25_goals,updated_at)
               VALUES(1,50000,28000,12000,10000,22000,22000,?)""",
            (now,),
        )
        await db.execute(
            """INSERT INTO bookmaker_odds
               (fixture_id,bookmaker_id,market_id,outcome,opening,current,peak,opening_at,current_at)
               VALUES(1,1,6,'home',2.05,1.95,2.10,?,?),
                     (1,1,6,'draw',3.40,3.40,3.40,?,?),
                     (1,1,6,'away',4.20,4.20,4.20,?,?),
                     (1,2,6,'home',2.00,1.91,2.00,?,?),
                     (1,2,6,'draw',3.50,3.50,3.50,?,?),
                     (1,2,6,'away',4.00,4.00,4.00,?,?),
                     (1,1,51,'home_m05',1.85,1.85,1.95,?,?),
                     (1,1,51,'away_p05',1.95,1.95,1.95,?,?)""",
            tuple([now] * 16),
        )
        await db.commit()
    importlib.reload(main)
    async with AsyncClient(transport=ASGITransport(app=main.app), base_url="http://test") as c:
        r = await c.get("/api/fixtures", params={"date": "2026-05-15", "leagues": "101"})
    assert r.status_code == 200
    f = r.json()["fixtures"][0]
    assert f["predictability"] == "high"
    assert f["home_form"]["form5"] == "WWLDW"
    assert f["prediction_summary"]["home_win_pct"] == pytest.approx(56.0, abs=0.1)
    assert f["odds"]["ft_result"]["pinnacle"]["home"] == 1.95
    assert f["odds"]["ft_result"]["bet365"]["home"] == 1.91
    assert f["odds"]["asian_handicap"]["line"] == -0.5
    assert f["odds"]["asian_handicap"]["pinnacle"]["home_odds"] == 1.85
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/bin/pytest tests/test_routers_fixtures.py::test_list_fixtures_returns_predictability_form_odds -v
```

Expected: FAIL.

- [ ] **Step 3: Extend `list_fixtures`**

把 `backend/routers/fixtures.py` 中 `list_fixtures` 函数与辅助函数整体替换为：

```python
from services.ah import derive_main_ah_line

def _pct(numer, denom):
    if not numer or not denom:
        return None
    return round(numer * 100 / denom, 2)

def _build_form(row: dict | None) -> dict | None:
    if not row or row.get("form5_str") is None:
        return None
    return {
        "form5": row.get("form5_str") or "",
        "won": row.get("won"), "drawn": row.get("drawn"), "lost": row.get("lost"),
        "gf": row.get("goals_for"), "ga": row.get("goals_against"),
    }

def _build_prediction_summary(p: dict | None) -> dict | None:
    if not p or not p.get("simulations"):
        return None
    s = p["simulations"]
    return {
        "home_win_pct": _pct(p["home_win"], s),
        "draw_pct":     _pct(p["draw"], s),
        "away_win_pct": _pct(p["away_win"], s),
        "btts_pct":     _pct(p["btts"], s),
        "o25_pct":      _pct(p["o25_goals"], s),
    }

def _format_ah_outcome(side: str, line: float) -> str:
    if line == 0:
        return f"{side}_0"
    sign = "m" if (side == "home" and line < 0) or (side == "away" and line > 0) else "p"
    abs_line = abs(line)
    if abs_line == int(abs_line):
        digits = f"{int(abs_line)}"
    elif abs_line * 2 == int(abs_line * 2):
        digits = f"{int(abs_line)}5" if abs_line >= 1 else "05"
    else:
        digits = f"{abs_line:.2f}".replace("0.", "0").replace(".", "")
    return f"{side}_{sign}{digits}"

def _bookmaker_1x2(rows: list[dict], bk: int) -> dict | None:
    pick = {r["outcome"]: r for r in rows if r["market_id"] == 6 and r["bookmaker_id"] == bk}
    if not pick:
        return None
    def _v(o):
        r = pick.get(o)
        return float(r["current"]) if r and r["current"] is not None else None
    home = _v("home"); draw = _v("draw"); away = _v("away")
    if home is None or away is None:
        return None
    at = pick.get("home", {}).get("current_at")
    return {"home": home, "draw": draw, "away": away, "current_at": at}

def _build_odds_summary(rows: list[dict]) -> dict | None:
    if not rows:
        return None
    ft = {"pinnacle": _bookmaker_1x2(rows, 1), "bet365": _bookmaker_1x2(rows, 2)}
    ah = None
    pin = derive_main_ah_line(rows, bookmaker_id=1)
    b365 = derive_main_ah_line(rows, bookmaker_id=2)
    if pin:
        line, ph, pa = pin
        ah = {
            "line": line,
            "pinnacle": {
                "home_outcome": _format_ah_outcome("home", line),
                "home_odds": ph,
                "away_outcome": _format_ah_outcome("away", -line),
                "away_odds": pa,
            },
            "bet365": ({"home_odds": b365[1], "away_odds": b365[2]}
                        if b365 and b365[0] == line else None),
        }
    if not ft["pinnacle"] and not ft["bet365"] and ah is None:
        return None
    return {"ft_result": ft, "asian_handicap": ah}

@router.get("/fixtures")
async def list_fixtures(
    date: Annotated[str | None, Query()] = None,
    leagues: Annotated[str | None, Query()] = None,
    predictability: Annotated[str | None, Query()] = None,
    min_drop: Annotated[float | None, Query()] = None,
    has_ai: Annotated[bool, Query()] = False,
    limit: Annotated[int, Query()] = 200,
    status: Annotated[str | None, Query()] = None,
    db: aiosqlite.Connection = Depends(get_db),
):
    target = date or str(date_type.today())
    sql = (
        "SELECT f.*, "
        "  hf.form5_str AS h_form5, hf.won AS h_won, hf.drawn AS h_drawn, hf.lost AS h_lost,"
        "  hf.goals_for AS h_gf, hf.goals_against AS h_ga,"
        "  af.form5_str AS a_form5, af.won AS a_won, af.drawn AS a_drawn, af.lost AS a_lost,"
        "  af.goals_for AS a_gf, af.goals_against AS a_ga,"
        "  p.simulations, p.home_win, p.draw, p.away_win, p.btts, p.o25_goals,"
        "  ds.drop_pct AS d_drop_pct, ds.drop_market AS d_drop_market"
        " FROM fixtures f"
        " LEFT JOIN team_form hf ON hf.team_id=f.home_team_id AND hf.season_id=f.season_id"
        " LEFT JOIN team_form af ON af.team_id=f.away_team_id AND af.season_id=f.season_id"
        " LEFT JOIN predictions p ON p.fixture_id=f.id"
        " LEFT JOIN ("
        "   SELECT fixture_id, drop_pct, drop_market FROM odds_snapshots"
        "   WHERE (fixture_id, recorded_at) IN ("
        "     SELECT fixture_id, MAX(recorded_at) FROM odds_snapshots GROUP BY fixture_id)"
        " ) ds ON ds.fixture_id=f.id"
        " WHERE date(f.kickoff_utc)=?"
    )
    params: list = [target]
    if leagues:
        ids = [int(x) for x in leagues.split(",") if x.strip()]
        if ids:
            sql += f" AND f.competition_id IN ({','.join('?'*len(ids))})"
            params.extend(ids)
    if predictability:
        levels = [s.strip() for s in predictability.split(",") if s.strip()]
        if levels:
            sql += f" AND f.predictability IN ({','.join('?'*len(levels))})"
            params.extend(levels)
    if has_ai:
        sql += " AND p.simulations IS NOT NULL AND p.simulations > 0"
    if min_drop is not None:
        sql += " AND ds.drop_pct <= ?"
        params.append(-abs(min_drop))
    if status:
        sql += " AND f.status=?"
        params.append(status)
    sql += f" ORDER BY f.kickoff_utc LIMIT {int(limit)}"

    async with db.execute(sql, params) as cur:
        rows = await cur.fetchall()

    fixtures = []
    for row in rows:
        d = _parse(row)
        async with db.execute(
            "SELECT * FROM bookmaker_odds WHERE fixture_id=?", (row["id"],)
        ) as ocur:
            odds_rows = [dict(r) for r in await ocur.fetchall()]
        home_form = _build_form({"form5_str": row["h_form5"], "won": row["h_won"],
                                   "drawn": row["h_drawn"], "lost": row["h_lost"],
                                   "goals_for": row["h_gf"], "goals_against": row["h_ga"]})
        away_form = _build_form({"form5_str": row["a_form5"], "won": row["a_won"],
                                   "drawn": row["a_drawn"], "lost": row["a_lost"],
                                   "goals_for": row["a_gf"], "goals_against": row["a_ga"]})
        d.update({
            "predictability": row["predictability"],
            "home_form": home_form, "away_form": away_form,
            "prediction_summary": _build_prediction_summary({
                "simulations": row["simulations"], "home_win": row["home_win"],
                "draw": row["draw"], "away_win": row["away_win"],
                "btts": row["btts"], "o25_goals": row["o25_goals"],
            }),
            "odds": _build_odds_summary(odds_rows),
            "drop_flag": ({"market_key": row["d_drop_market"],
                            "drop_percentage": abs(row["d_drop_pct"]) if row["d_drop_pct"] else 0}
                           if row["d_drop_pct"] is not None else None),
        })
        fixtures.append(d)
    return {"fixtures": fixtures, "total": len(fixtures), "cached_at": None}
```

把既有 `test_list_fixtures_requires_leagues` 重命名为 `test_list_fixtures_without_leagues_returns_all_in_date` 并改断言为：返回 `total == 1`（前提：测试数据是当天 kickoff）。

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest tests/test_routers_fixtures.py -v
```

Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add backend/routers/fixtures.py backend/tests/test_routers_fixtures.py
git commit -m "feat(api): /fixtures returns predictability, form, prediction, odds, drop_flag"
```

---

## Task 2.5：`GET /fixtures/{id}` 详情响应扩展

**Files:**
- Modify: `backend/routers/fixtures.py`
- Test: `backend/tests/test_routers_fixtures.py`

- [ ] **Step 1: Write failing test**

```python
@pytest.mark.asyncio
async def test_get_fixture_detail_returns_prediction_and_ah_lines(tmp_path, monkeypatch):
    monkeypatch.setenv("GOALCAST_DB_PATH", str(tmp_path / "test.db"))
    import importlib, database, main, json
    importlib.reload(database); await database.init_db()
    now = "2026-05-15T15:00:00"
    async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
        await db.execute(
            """INSERT INTO fixtures(id,competition_id,competition_name,home_team,away_team,
                home_team_id,away_team_id,season_id,kickoff_utc,status,predictability,
                fetched_at,updated_at)
               VALUES(1,101,'PL','A','B',11,22,55,'2026-05-15T15:00:00','pre','medium',?,?)""",
            (now, now),
        )
        await db.execute(
            """INSERT INTO predictions(fixture_id,simulations,home_win,draw,away_win,btts,
                o15_goals,o25_goals,o35_goals,o45_goals,scorelines,updated_at)
               VALUES(1,50000,28000,12000,10000,22000,35000,22000,11000,5000,?,?)""",
            (json.dumps({"1-0": 13.44, "2-0": 11.87, "1-1": 11.5}), now),
        )
        await db.execute(
            """INSERT INTO bookmaker_odds
               (fixture_id,bookmaker_id,market_id,outcome,opening,current,peak,opening_at,current_at)
               VALUES(1,1,51,'home_m05',1.92,1.85,1.95,?,?),
                     (1,1,51,'away_p05',1.95,1.95,1.95,?,?),
                     (1,1,51,'home_m075',2.10,2.10,2.10,?,?),
                     (1,1,51,'away_p075',1.75,1.75,1.75,?,?)""",
            tuple([now] * 8),
        )
        await db.commit()
    importlib.reload(main)
    async with AsyncClient(transport=ASGITransport(app=main.app), base_url="http://test") as c:
        r = await c.get("/api/fixtures/1")
    j = r.json()
    assert j["prediction"]["home_win_pct"] == pytest.approx(56.0, abs=0.1)
    assert j["prediction"]["scorelines"]["1-0"] == 13.44
    ah_lines = j["odds"]["asian_handicap_lines"]
    lines = sorted([l["line"] for l in ah_lines])
    assert -0.75 in lines and -0.5 in lines
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/bin/pytest tests/test_routers_fixtures.py::test_get_fixture_detail_returns_prediction_and_ah_lines -v
```

Expected: FAIL.

- [ ] **Step 3: Extend `get_fixture`**

在 `backend/routers/fixtures.py` 替换 `get_fixture` 与新增辅助：

```python
def _bookmaker_1x2_detail(rows: list[dict], bk: int) -> dict | None:
    pick = {r["outcome"]: r for r in rows if r["market_id"] == 6 and r["bookmaker_id"] == bk}
    if not pick:
        return None
    def _entry(o):
        r = pick.get(o)
        if not r:
            return None
        return {"current": float(r["current"]) if r["current"] is not None else None,
                "opening": float(r["opening"]) if r["opening"] is not None else None,
                "current_at": r["current_at"]}
    return {"home": _entry("home"), "draw": _entry("draw"), "away": _entry("away")}

def _all_ah_lines(rows: list[dict]) -> list[dict]:
    from services.ah import parse_ah_outcome_line
    by_bm: dict[int, dict[float, dict[str, dict]]] = {}
    for r in rows:
        if r["market_id"] != 51:
            continue
        parsed = parse_ah_outcome_line(r["outcome"])
        if not parsed:
            continue
        side, line = parsed
        home_line = line if side == "home" else -line
        b = by_bm.setdefault(r["bookmaker_id"], {}).setdefault(home_line, {})
        b[side] = {"current": float(r["current"]) if r["current"] is not None else None,
                    "opening": float(r["opening"]) if r["opening"] is not None else None}
    all_lines = sorted(set().union(*(b.keys() for b in by_bm.values())) if by_bm else [])
    out = []
    for ln in all_lines:
        item = {"line": ln}
        for bk_name, bk_id in (("pinnacle", 1), ("bet365", 2)):
            d = by_bm.get(bk_id, {}).get(ln, {})
            home, away = d.get("home", {}), d.get("away", {})
            if home or away:
                item[bk_name] = {
                    "home": home.get("current"), "away": away.get("current"),
                    "opening_home": home.get("opening"), "opening_away": away.get("opening"),
                }
            else:
                item[bk_name] = None
        out.append(item)
    return out

def _build_detail_odds(rows: list[dict]) -> dict | None:
    if not rows:
        return None
    ft = {"pinnacle": _bookmaker_1x2_detail(rows, 1), "bet365": _bookmaker_1x2_detail(rows, 2)}
    return {"ft_result": ft, "asian_handicap_lines": _all_ah_lines(rows)}

@router.get("/fixtures/{fixture_id}")
async def get_fixture(fixture_id: int, db: aiosqlite.Connection = Depends(get_db)):
    async with db.execute("SELECT * FROM fixtures WHERE id=?", (fixture_id,)) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(404, "Fixture not found")
    fixture = _parse(row, with_h2h=False)
    fixture["predictability"] = row["predictability"]

    async with db.execute("SELECT * FROM predictions WHERE fixture_id=?", (fixture_id,)) as cur:
        p = await cur.fetchone()
    prediction = None
    if p and p["simulations"]:
        s = p["simulations"]
        prediction = {
            "simulations": s,
            "home_win_pct": _pct(p["home_win"], s),
            "draw_pct":     _pct(p["draw"], s),
            "away_win_pct": _pct(p["away_win"], s),
            "btts_pct":     _pct(p["btts"], s),
            "o25_pct":      _pct(p["o25_goals"], s),
            "o35_pct":      _pct(p["o35_goals"], s),
            "scorelines":   json.loads(p["scorelines"] or "{}"),
            "updated_at":   p["updated_at"],
        }

    async with db.execute("SELECT * FROM bookmaker_odds WHERE fixture_id=?", (fixture_id,)) as cur:
        odds_rows = [dict(r) for r in await cur.fetchall()]
    odds = _build_detail_odds(odds_rows)

    async with db.execute(
        """SELECT tf.* FROM fixtures f
           LEFT JOIN team_form tf ON tf.team_id=f.home_team_id AND tf.season_id=f.season_id
           WHERE f.id=?""", (fixture_id,)) as cur:
        hf_row = await cur.fetchone()
    async with db.execute(
        """SELECT tf.* FROM fixtures f
           LEFT JOIN team_form tf ON tf.team_id=f.away_team_id AND tf.season_id=f.season_id
           WHERE f.id=?""", (fixture_id,)) as cur:
        af_row = await cur.fetchone()
    home_form = _build_form(dict(hf_row) if hf_row else None)
    away_form = _build_form(dict(af_row) if af_row else None)

    home_team_obj = {"id": row["home_team_id"], "name": row["home_team"],
                       "stats": fixture.get("home_stats"), "form": home_form}
    away_team_obj = {"id": row["away_team_id"], "name": row["away_team"],
                       "stats": fixture.get("away_stats"), "form": away_form}

    async with db.execute(
        """SELECT market AS market_key, drop_market, drop_pct,
                  odds_home, odds_draw, odds_away, bookmaker, recorded_at
           FROM odds_snapshots
           WHERE fixture_id=?
           ORDER BY recorded_at DESC LIMIT 50""",
        (fixture_id,)) as cur:
        drops = [dict(r) for r in await cur.fetchall()]

    # 注意：键名用 *_obj 后缀以免与 fixture 内的字符串字段 home_team / away_team 冲突。
    return {"fixture": fixture, "home_team_obj": home_team_obj, "away_team_obj": away_team_obj,
            "prediction": prediction, "odds": odds, "dropping_records": drops}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest tests/test_routers_fixtures.py -v
```

Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add backend/routers/fixtures.py backend/tests/test_routers_fixtures.py
git commit -m "feat(api): /fixtures/{id} returns prediction + all AH lines + form + dropping_records"
```

---

# M3 — 前端类型 + MatchCard + Matches

## Task 3.1：`lib/api.ts` 类型

**Files:**
- Modify: `frontend/src/lib/api.ts`

- [ ] **Step 1: Add / update types**

把以下类型加入文件顶部（保留现有 fetch 函数）：

```ts
export type Predictability = 'high' | 'good' | 'medium' | 'poor' | null

export type TeamForm = {
  form5: string
  won: number; drawn: number; lost: number
  gf: number; ga: number
}

export type BookmakerOdds = {
  home: number | null; draw?: number | null; away: number | null
  opening?: number | null
  current_at?: string | null
}

export type AsianHandicapLine = {
  line: number
  pinnacle?: { home: number | null; away: number | null
               opening_home?: number | null; opening_away?: number | null } | null
  bet365?:   { home: number | null; away: number | null } | null
}

export type Prediction = {
  simulations: number
  home_win_pct: number; draw_pct: number; away_win_pct: number
  btts_pct: number; o25_pct: number; o35_pct: number
  scorelines: Record<string, number>
  updated_at: string
}

export type FixtureSummary = {
  id: number
  home_team: string; away_team: string
  competition_name: string; competition_country?: string
  kickoff_utc: string
  status: 'pre' | 'live' | 'ft'
  predictability: Predictability
  home_form: TeamForm | null
  away_form: TeamForm | null
  prediction_summary: {
    home_win_pct: number; draw_pct: number; away_win_pct: number
    btts_pct: number; o25_pct: number
  } | null
  odds: {
    ft_result: { pinnacle: BookmakerOdds | null; bet365: BookmakerOdds | null }
    asian_handicap: {
      line: number
      pinnacle: { home_outcome: string; home_odds: number; away_outcome: string; away_odds: number }
      bet365: { home_odds: number | null; away_odds: number | null } | null
    } | null
  } | null
  drop_flag: { market_key: string; drop_percentage: number } | null
}

export type FixtureDetail = Omit<FixtureSummary, 'odds'> & {
  prediction: Prediction | null
  odds: {
    ft_result: { pinnacle: BookmakerOdds | null; bet365: BookmakerOdds | null }
    asian_handicap_lines: AsianHandicapLine[]
  } | null
  home_team_obj: { id: number; name: string; stats: unknown; form: TeamForm | null }
  away_team_obj: { id: number; name: string; stats: unknown; form: TeamForm | null }
  dropping_records: Array<{
    market_key: string; drop_pct: number; bookmaker: string; recorded_at: string
  }>
}
```

- [ ] **Step 2: TypeScript compile**

```bash
cd frontend && npx tsc --noEmit
```

Expected: 可能有 downstream 报错（MatchCard 等还没改），**但本文件自身必须无错**。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/api.ts
git commit -m "feat(types): add Predictability, TeamForm, Prediction, FixtureSummary/Detail types"
```

---

## Task 3.2：`PredictabilityBadge` 组件

**Files:**
- Create: `frontend/src/components/shared/PredictabilityBadge.tsx`
- Modify: `frontend/src/index.css`

- [ ] **Step 1: Write component**

```tsx
import type { Predictability } from '../../lib/api'

const LABELS: Record<NonNullable<Predictability>, string> = {
  high: '高可预测', good: '良好', medium: '一般', poor: '低可信'
}

export function PredictabilityBadge({ level }: { level: Predictability }) {
  if (!level) return null
  return (
    <span className={`pb pb-${level}`} title={`predictability: ${level}`}>
      {LABELS[level]}
    </span>
  )
}
```

- [ ] **Step 2: Add CSS**

加到 `frontend/src/index.css` 末尾：

```css
.pb { display: inline-block; padding: 2px 8px; border-radius: 9999px;
      font-size: 11px; font-weight: 600; line-height: 1; }
.pb-high   { background: #c7f0d2; color: #075c2b; }
.pb-good   { background: #defae9; color: #1a7a3f; }
.pb-medium { background: #fff2cc; color: #8a6d10; }
.pb-poor   { background: #f4d6d6; color: #8c1f1f; }
```

- [ ] **Step 3: Visual smoke**

在 Dashboard 临时挂一行 `<PredictabilityBadge level="high"/>`，跑 `npm run dev`，确认 4 档颜色对，再删掉临时挂载。

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/shared/PredictabilityBadge.tsx frontend/src/index.css
git commit -m "feat(ui): PredictabilityBadge with 4-level color tokens"
```

---

## Task 3.3：`FormStrip` 组件

**Files:**
- Create: `frontend/src/components/match/FormStrip.tsx`
- Modify: `frontend/src/index.css`

- [ ] **Step 1: Write component**

```tsx
const CLS: Record<string, string> = { W: 'form-w', D: 'form-d', L: 'form-l' }

export function FormStrip({ form5 }: { form5: string }) {
  if (!form5) return <span className="form-empty">—</span>
  return (
    <span className="form-strip">
      {form5.split('').slice(0, 5).map((c, i) => (
        <span key={i} className={`form-letter ${CLS[c] ?? ''}`}>{c}</span>
      ))}
    </span>
  )
}
```

- [ ] **Step 2: Add CSS**

```css
.form-strip { display: inline-flex; gap: 2px; }
.form-letter { display: inline-flex; align-items: center; justify-content: center;
               width: 18px; height: 18px; border-radius: 4px;
               font-size: 11px; font-weight: 700; color: #fff; }
.form-w { background: #22a85d; }
.form-d { background: #d4a017; }
.form-l { background: #d24a4a; }
.form-empty { color: #888; }
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/match/FormStrip.tsx frontend/src/index.css
git commit -m "feat(ui): FormStrip colored last-5 letter blocks"
```

---

## Task 3.4：`OddsPair` 组件

**Files:**
- Create: `frontend/src/components/match/OddsPair.tsx`
- Modify: `frontend/src/index.css`

- [ ] **Step 1: Write component**

```tsx
type OddsValues = { home: number | null; draw?: number | null; away: number | null }

type Props = {
  label?: string
  pinnacle: OddsValues | null
  bet365: OddsValues | null
  showDraw?: boolean
}

const fmt = (n: number | null | undefined) => (n == null ? '—' : n.toFixed(2))

function highlight(a: number | null, b: number | null): [string, string] {
  if (a == null || b == null || !a || !b) return ['', '']
  const diff = (a - b) / Math.min(a, b)
  if (Math.abs(diff) < 0.05) return ['', '']
  return diff > 0 ? ['odds-better', 'odds-worse'] : ['odds-worse', 'odds-better']
}

export function OddsPair({ label, pinnacle, bet365, showDraw = true }: Props) {
  const [hP, hB] = highlight(pinnacle?.home ?? null, bet365?.home ?? null)
  const [aP, aB] = highlight(pinnacle?.away ?? null, bet365?.away ?? null)
  return (
    <div className="odds-pair">
      {label && <div className="odds-label">{label}</div>}
      <div className="odds-row">
        <div className="odds-book">Pinnacle</div>
        <span className={`odds-cell ${hP}`}>{fmt(pinnacle?.home)}</span>
        {showDraw && <span className="odds-cell">{fmt(pinnacle?.draw)}</span>}
        <span className={`odds-cell ${aP}`}>{fmt(pinnacle?.away)}</span>
      </div>
      <div className="odds-row">
        <div className="odds-book">Bet365</div>
        <span className={`odds-cell ${hB}`}>{fmt(bet365?.home)}</span>
        {showDraw && <span className="odds-cell">{fmt(bet365?.draw)}</span>}
        <span className={`odds-cell ${aB}`}>{fmt(bet365?.away)}</span>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Add CSS**

```css
.odds-pair { display: flex; flex-direction: column; gap: 2px; font-size: 12px; }
.odds-label { font-weight: 600; color: #666; }
.odds-row { display: flex; gap: 6px; align-items: center; }
.odds-book { width: 56px; font-weight: 500; color: #888; font-size: 11px; }
.odds-cell { padding: 2px 6px; border-radius: 4px; background: #f5f5f5;
              min-width: 44px; text-align: center; }
.odds-better { background: #defae9; }
.odds-worse  { background: #f7d8d8; }
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/match/OddsPair.tsx frontend/src/index.css
git commit -m "feat(ui): OddsPair with two-bookmaker compare + 5%-diff highlight"
```

---

## Task 3.5：`MatchCard` 重写

**Files:**
- Modify: `frontend/src/components/match/MatchCard.tsx`
- Modify: `frontend/src/index.css`

- [ ] **Step 1: Read existing MatchCard to record current props/usage**

```bash
cat frontend/src/components/match/MatchCard.tsx
```

记下调用方（Matches.tsx 中如何用），保证新版兼容。

- [ ] **Step 2: Replace component body**

```tsx
import type { FixtureSummary } from '../../lib/api'
import { PredictabilityBadge } from '../shared/PredictabilityBadge'
import { FormStrip } from './FormStrip'
import { OddsPair } from './OddsPair'

type Props = { fixture: FixtureSummary; onClick?: () => void }

const fmtKO = (iso: string) => {
  const d = new Date(iso)
  return d.toLocaleString('zh-CN', { weekday: 'short', month: 'numeric', day: 'numeric',
                                       hour: '2-digit', minute: '2-digit' })
}

export function MatchCard({ fixture, onClick }: Props) {
  const ps = fixture.prediction_summary
  const ah = fixture.odds?.asian_handicap
  const ft = fixture.odds?.ft_result
  return (
    <div className="mc" role="button" tabIndex={0} onClick={onClick}
         onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onClick?.() }}>
      <div className="mc-head">
        <PredictabilityBadge level={fixture.predictability} />
        <span className="mc-teams">
          <strong>{fixture.home_team}</strong> vs <strong>{fixture.away_team}</strong>
        </span>
        {fixture.drop_flag && (
          <span className={`mc-drop ${fixture.drop_flag.drop_percentage >= 50 ? 'mc-drop-alert' : ''}`}>
            跌 {-Math.round(fixture.drop_flag.drop_percentage)}%
          </span>
        )}
      </div>
      <div className="mc-meta">
        {fixture.competition_name} · {fixture.competition_country ?? ''} · {fmtKO(fixture.kickoff_utc)}
      </div>

      <div className="mc-form">
        <span className="mc-form-label">FORM</span>
        <FormStrip form5={fixture.home_form?.form5 ?? ''} />
        <span className="mc-form-sep">·</span>
        <FormStrip form5={fixture.away_form?.form5 ?? ''} />
      </div>

      {ps && (
        <div className="mc-ai">
          <span className="mc-ai-label">AI</span>
          <span>主 {ps.home_win_pct.toFixed(1)}%</span>
          <span>平 {ps.draw_pct.toFixed(1)}%</span>
          <span>客 {ps.away_win_pct.toFixed(1)}%</span>
          <span className="mc-ai-extra">o2.5: {ps.o25_pct.toFixed(1)}%</span>
        </div>
      )}

      <div className="mc-odds">
        <OddsPair
          label="1x2"
          pinnacle={ft?.pinnacle ? { home: ft.pinnacle.home, draw: ft.pinnacle.draw ?? null, away: ft.pinnacle.away } : null}
          bet365={ft?.bet365 ? { home: ft.bet365.home, draw: ft.bet365.draw ?? null, away: ft.bet365.away } : null}
        />
        {ah ? (
          <OddsPair
            label={`AH ${ah.line > 0 ? '+' : ''}${ah.line}`}
            pinnacle={{ home: ah.pinnacle.home_odds, away: ah.pinnacle.away_odds }}
            bet365={ah.bet365 ? { home: ah.bet365.home_odds, away: ah.bet365.away_odds } : null}
            showDraw={false}
          />
        ) : (
          <div className="mc-no-ah">— 无亚盘 —</div>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Add CSS**

```css
.mc { padding: 12px; border: 1px solid #e0e0e0; border-radius: 8px; cursor: pointer;
       display: flex; flex-direction: column; gap: 8px; background: #fff; }
.mc:hover { background: #fafafa; }
.mc-head { display: flex; gap: 8px; align-items: center; }
.mc-teams { flex: 1; font-size: 15px; }
.mc-drop { font-size: 11px; padding: 2px 6px; border-radius: 4px;
            background: #ffe9e9; color: #8c1f1f; }
.mc-drop-alert { background: #ff6b6b; color: #fff; }
.mc-meta { color: #888; font-size: 12px; }
.mc-form { display: flex; gap: 6px; align-items: center; font-size: 12px; }
.mc-form-label { color: #888; font-weight: 600; }
.mc-form-sep { color: #ccc; }
.mc-ai { display: flex; gap: 12px; font-size: 12px; align-items: center; }
.mc-ai-label { color: #888; font-weight: 600; }
.mc-ai-extra { color: #888; margin-left: auto; }
.mc-odds { display: flex; gap: 16px; flex-wrap: wrap; }
.mc-no-ah { color: #aaa; font-size: 12px; align-self: center; }
```

- [ ] **Step 4: Build + visual check**

```bash
cd frontend && npm run build
```

Expected: build 成功。`npm run dev` 后打开 Matches 页，验证至少一张 MatchCard 完整呈现 8 项信息。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/match/MatchCard.tsx frontend/src/index.css
git commit -m "feat(ui): MatchCard rewrite with dual-bookmaker AH/1x2, form, AI summary"
```

---

## Task 3.6：`Matches.tsx` filter chips + 加载更多

**Files:**
- Modify: `frontend/src/pages/Matches.tsx`
- Modify: `frontend/src/index.css`

- [ ] **Step 1: Read current Matches.tsx**

记录现有 state、leagues filter 实现位置、fetch 调用形态。

- [ ] **Step 2: Add new filter state**

在组件顶部 useState 区追加：

```tsx
const [predictability, setPredictability] = useState<string[]>([])
const [minDrop, setMinDrop] = useState<number | null>(null)
const [hasAi, setHasAi] = useState(false)
const [limit, setLimit] = useState(200)
```

- [ ] **Step 3: Update fetch query**

把 fetch URL 改成携带新参数：

```tsx
const params = new URLSearchParams({ date, limit: String(limit) })
if (leagues.length) params.set('leagues', leagues.join(','))
if (predictability.length) params.set('predictability', predictability.join(','))
if (minDrop !== null) params.set('min_drop', String(minDrop))
if (hasAi) params.set('has_ai', 'true')
const res = await fetch(`/api/fixtures?${params.toString()}`)
```

依赖列表里加 `predictability, minDrop, hasAi, limit`。

- [ ] **Step 4: Render filter chips**

在 leagues filter 区下方追加：

```tsx
<div className="filter-chips">
  <button
    className={`chip ${!predictability.includes('poor') ? 'chip-active' : ''}`}
    onClick={() => setPredictability(p =>
      p.includes('poor') ? p.filter(x => x !== 'poor') : [...p, 'poor'])}>
    排除 poor
  </button>
  <button
    className={`chip ${predictability.length === 2
                        && predictability.includes('high')
                        && predictability.includes('good') ? 'chip-active' : ''}`}
    onClick={() => setPredictability(['high', 'good'])}>
    只看 high + good
  </button>
  <button
    className={`chip ${minDrop !== null ? 'chip-active' : ''}`}
    onClick={() => setMinDrop(d => d === null ? 50 : null)}>
    跌幅 ≥ 50%
  </button>
  <button
    className={`chip ${hasAi ? 'chip-active' : ''}`}
    onClick={() => setHasAi(v => !v)}>
    只看 有 AI
  </button>
  <button className="chip chip-reset"
    onClick={() => { setPredictability([]); setMinDrop(null); setHasAi(false) }}>
    清空
  </button>
</div>
```

- [ ] **Step 5: Add "加载更多" + CSS**

在列表末尾：

```tsx
{fixtures.length >= limit && (
  <button className="load-more" onClick={() => setLimit(l => l + 200)}>
    加载更多
  </button>
)}
```

CSS：

```css
.filter-chips { display: flex; gap: 8px; flex-wrap: wrap; margin: 12px 0; }
.chip { padding: 6px 12px; border-radius: 9999px; border: 1px solid #ddd;
        background: #fff; cursor: pointer; font-size: 12px; }
.chip-active { background: #007aff; color: #fff; border-color: #007aff; }
.chip-reset { color: #888; }
.load-more { margin: 16px auto; padding: 8px 20px; display: block; cursor: pointer;
              border: 1px solid #ddd; background: #fff; border-radius: 6px; }
```

- [ ] **Step 6: Build + smoke**

```bash
cd frontend && npm run build && npm run dev
```

打开 Matches，点每个 chip 验证 URL 参数与结果集变化；点「加载更多」验证 limit 增加。

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/Matches.tsx frontend/src/index.css
git commit -m "feat(ui): Matches page filter chips for predictability/drop/AI + load more"
```

---

## Task 3.7：M3 验收截图

**Files:**
- Create: `docs/screenshots/m3-matches-filters.png`
- Create: `docs/screenshots/m3-matchcard-detail.png`

- [ ] **Step 1: Run dev server**

```bash
cd frontend && npm run dev
```

- [ ] **Step 2: Take screenshots**

1. Matches 页带 filter chips 全启 → `docs/screenshots/m3-matches-filters.png`
2. 一张完整 MatchCard 放大（双家盘口 + form + AI + drop flag）→ `docs/screenshots/m3-matchcard-detail.png`

- [ ] **Step 3: Commit**

```bash
mkdir -p docs/screenshots
git add docs/screenshots/m3-*.png
git commit -m "docs: M3 acceptance screenshots"
```

---

# M4 — MatchDetail + ScorelineHeatmap + Dashboard

## Task 4.1：`PredictionBars` 组件

**Files:**
- Create: `frontend/src/components/match/PredictionBars.tsx`
- Modify: `frontend/src/index.css`

- [ ] **Step 1: Write component**

```tsx
import type { Prediction } from '../../lib/api'

type Row = { label: string; pct: number; color?: string }

function bar(r: Row, key: number) {
  return (
    <div key={key} className="pbar-row">
      <div className="pbar-label">{r.label}</div>
      <div className="pbar-track">
        <div className="pbar-fill" style={{ width: `${r.pct}%`, background: r.color ?? '#007aff' }} />
        <span className="pbar-val">{r.pct.toFixed(1)}%</span>
      </div>
    </div>
  )
}

export function PredictionBars({ prediction }: { prediction: Prediction | null }) {
  if (!prediction) {
    return <div className="pbar-empty">该场暂无 AI 模型</div>
  }
  const rows: Row[] = [
    { label: '主胜', pct: prediction.home_win_pct, color: '#22a85d' },
    { label: '平',   pct: prediction.draw_pct,     color: '#d4a017' },
    { label: '客胜', pct: prediction.away_win_pct, color: '#d24a4a' },
    { label: 'BTTS', pct: prediction.btts_pct,     color: '#7e57c2' },
    { label: 'o2.5', pct: prediction.o25_pct,      color: '#0277bd' },
    { label: 'o3.5', pct: prediction.o35_pct,      color: '#01579b' },
  ]
  return <div className="pbar">{rows.map(bar)}</div>
}
```

- [ ] **Step 2: Add CSS**

```css
.pbar { display: flex; flex-direction: column; gap: 6px; }
.pbar-empty { color: #888; padding: 16px; text-align: center; background: #f9f9f9; border-radius: 6px; }
.pbar-row { display: grid; grid-template-columns: 60px 1fr; gap: 8px; align-items: center; font-size: 13px; }
.pbar-label { color: #555; }
.pbar-track { position: relative; height: 22px; background: #f0f0f0; border-radius: 4px; overflow: hidden; }
.pbar-fill { height: 100%; transition: width 0.3s; }
.pbar-val { position: absolute; right: 8px; top: 50%; transform: translateY(-50%);
             font-size: 11px; color: #333; font-weight: 600; }
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/match/PredictionBars.tsx frontend/src/index.css
git commit -m "feat(ui): PredictionBars for 6 model metrics"
```

---

## Task 4.2：`lib/ahMath.ts` 工具函数

**Files:**
- Create: `frontend/src/lib/ahMath.ts`

- [ ] **Step 1: Write util**

```ts
export function ahProbabilities(
  scorelines: Record<string, number>,
  line: number,
  side: 'home' | 'away' = 'home',
): { win: number; push: number; lose: number } {
  let win = 0, push = 0, lose = 0
  for (const [k, pct] of Object.entries(scorelines)) {
    const [hStr, aStr] = k.split('-')
    const h = parseInt(hStr, 10), a = parseInt(aStr, 10)
    if (isNaN(h) || isNaN(a)) continue
    const margin = side === 'home' ? (h - a) : (a - h)
    const effective = margin + line
    const nearestInt = Math.round(effective)
    if (Math.abs(effective - nearestInt) < 1e-9) {
      if (nearestInt > 0) win += pct
      else if (nearestInt === 0) push += pct
      else lose += pct
    } else {
      // .25 / .75 -> half-bet semantics
      if (effective >= 0.5) win += pct
      else if (effective <= -0.5) lose += pct
      else if (effective > 0) { win += pct * 0.5; push += pct * 0.5 }
      else                     { lose += pct * 0.5; push += pct * 0.5 }
    }
  }
  return { win, push, lose }
}

export const AH_LINES_DEFAULT = [-1.25, -1, -0.75, -0.5, -0.25, 0, 0.25, 0.5, 0.75, 1, 1.25]
```

- [ ] **Step 2: TypeScript check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: 无新错误。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/ahMath.ts
git commit -m "feat(lib): ahMath — compute win/push/lose probabilities from scorelines"
```

---

## Task 4.3：`AhLineSelector` 组件

**Files:**
- Create: `frontend/src/components/match/AhLineSelector.tsx`
- Modify: `frontend/src/index.css`

- [ ] **Step 1: Write component**

```tsx
import { AH_LINES_DEFAULT } from '../../lib/ahMath'

type Props = {
  value: number
  options?: number[]
  onChange: (v: number) => void
}

export function AhLineSelector({ value, options = AH_LINES_DEFAULT, onChange }: Props) {
  return (
    <select className="ah-line-select" value={value}
            onChange={e => onChange(parseFloat(e.target.value))}>
      {options.map(o => (
        <option key={o} value={o}>{`AH ${o > 0 ? '+' : ''}${o}`}</option>
      ))}
    </select>
  )
}
```

- [ ] **Step 2: CSS**

```css
.ah-line-select { padding: 6px 12px; border-radius: 6px; border: 1px solid #ddd;
                   font-size: 14px; background: #fff; }
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/match/AhLineSelector.tsx frontend/src/index.css
git commit -m "feat(ui): AhLineSelector dropdown"
```

---

## Task 4.4：`ScorelineHeatmap` 组件（killer feature）

**Files:**
- Create: `frontend/src/components/match/ScorelineHeatmap.tsx`
- Modify: `frontend/src/index.css`

- [ ] **Step 1: Write component**

```tsx
import { useMemo } from 'react'
import { ahProbabilities } from '../../lib/ahMath'

type Props = {
  scorelines: Record<string, number>
  ahLine: number
  size?: number
}

const MAX_GOALS = 6

function cellColor(pct: number, max: number): string {
  const r = max ? Math.min(1, pct / max) : 0
  const v = Math.round(255 - r * 180)
  return `rgb(${v}, ${v}, ${v})`
}

function cellOverlay(h: number, a: number, line: number): 'win' | 'push' | 'lose' {
  const margin = h - a
  const eff = margin + line
  const nearestInt = Math.round(eff)
  if (Math.abs(eff - nearestInt) < 1e-9) {
    if (nearestInt > 0) return 'win'
    if (nearestInt === 0) return 'push'
    return 'lose'
  }
  return eff > 0 ? 'win' : 'lose'
}

export function ScorelineHeatmap({ scorelines, ahLine, size = 36 }: Props) {
  const cells = useMemo(() => {
    const m: number[][] = Array.from({ length: MAX_GOALS + 1 }, () => Array(MAX_GOALS + 1).fill(0))
    for (const [k, p] of Object.entries(scorelines)) {
      const [hs, as] = k.split('-').map(s => parseInt(s, 10))
      if (isNaN(hs) || isNaN(as)) continue
      const h = Math.min(hs, MAX_GOALS), a = Math.min(as, MAX_GOALS)
      m[a][h] += p
    }
    return m
  }, [scorelines])

  const max = useMemo(() => Math.max(...cells.flat()), [cells])
  const probs = useMemo(() => ahProbabilities(scorelines, ahLine), [scorelines, ahLine])

  return (
    <div className="hm-wrap">
      <table className="hm" style={{ ['--cell' as string]: `${size}px` } as React.CSSProperties}>
        <thead>
          <tr>
            <th></th>
            {Array.from({ length: MAX_GOALS + 1 }, (_, h) => (
              <th key={h}>{h === MAX_GOALS ? `${h}+` : h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {cells.map((row, a) => (
            <tr key={a}>
              <th>{a === MAX_GOALS ? `${a}+` : a}</th>
              {row.map((p, h) => {
                const o = cellOverlay(h, a, ahLine)
                return (
                  <td key={h}
                      className={`hm-cell hm-${o}`}
                      style={{ background: cellColor(p, max) }}
                      title={`${h}-${a} = ${p.toFixed(2)}%`}>
                    {p >= 0.5 ? p.toFixed(0) : ''}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <div className="hm-summary">
        <div className="hm-stat hm-win">赢: {probs.win.toFixed(1)}%</div>
        <div className="hm-stat hm-push">和: {probs.push.toFixed(1)}%</div>
        <div className="hm-stat hm-lose">输: {probs.lose.toFixed(1)}%</div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: CSS**

```css
.hm-wrap { display: flex; flex-direction: column; align-items: center; gap: 12px; }
.hm { border-collapse: collapse; font-size: 11px; }
.hm th, .hm td { width: var(--cell); height: var(--cell); text-align: center; vertical-align: middle; }
.hm th { color: #888; font-weight: 500; }
.hm-cell { position: relative; cursor: default; border: 1px solid #fff; }
.hm-cell::after { content: ''; position: absolute; inset: 0; pointer-events: none; }
.hm-win::after  { box-shadow: inset 0 0 0 2px rgba(34, 168, 93, 0.4); }
.hm-push::after { box-shadow: inset 0 0 0 2px rgba(212, 160, 23, 0.4); }
.hm-lose::after { box-shadow: inset 0 0 0 2px rgba(210, 74, 74, 0.4); }
.hm-summary { display: flex; gap: 16px; }
.hm-stat { padding: 6px 12px; border-radius: 6px; font-weight: 600; font-size: 13px; }
.hm-win { background: #defae9; color: #075c2b; }
.hm-push { background: #fff2cc; color: #8a6d10; }
.hm-lose { background: #f7d8d8; color: #8c1f1f; }
```

- [ ] **Step 3: Performance smoke test**

在 MatchDetail 临时挂载该组件，传入 ~30 个 scoreline 项，用 React DevTools Profiler：
1. 首渲染 < 200ms
2. 切 ahLine 重画 < 50ms

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/match/ScorelineHeatmap.tsx frontend/src/index.css
git commit -m "feat(ui): ScorelineHeatmap 7x7 with AH win/push/lose overlay"
```

---

## Task 4.5：`AhLineTable` 组件

**Files:**
- Create: `frontend/src/components/match/AhLineTable.tsx`
- Modify: `frontend/src/index.css`

- [ ] **Step 1: Write component**

```tsx
import type { AsianHandicapLine } from '../../lib/api'

const fmt = (n: number | null | undefined) => (n == null ? '—' : n.toFixed(2))

export function AhLineTable({ lines }: { lines: AsianHandicapLine[] }) {
  if (lines.length === 0) return <div className="aht-empty">— 无亚盘 —</div>
  return (
    <table className="aht">
      <thead>
        <tr>
          <th>档</th>
          <th colSpan={2}>Pinnacle</th>
          <th colSpan={2}>Bet365</th>
        </tr>
        <tr>
          <th></th>
          <th>主</th><th>客</th>
          <th>主</th><th>客</th>
        </tr>
      </thead>
      <tbody>
        {lines.map(l => (
          <tr key={l.line}>
            <td className="aht-line">{l.line > 0 ? '+' : ''}{l.line}</td>
            <td>{fmt(l.pinnacle?.home)}</td>
            <td>{fmt(l.pinnacle?.away)}</td>
            <td>{fmt(l.bet365?.home)}</td>
            <td>{fmt(l.bet365?.away)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
```

- [ ] **Step 2: CSS**

```css
.aht { width: 100%; font-size: 13px; border-collapse: collapse; }
.aht th, .aht td { padding: 6px 8px; text-align: center; border-bottom: 1px solid #eee; }
.aht th { background: #f9f9f9; font-weight: 600; }
.aht-line { font-weight: 700; }
.aht-empty { padding: 16px; text-align: center; color: #888; }
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/match/AhLineTable.tsx frontend/src/index.css
git commit -m "feat(ui): AhLineTable for detail page"
```

---

## Task 4.6：`MatchDetail` 重写

**Files:**
- Modify: `frontend/src/pages/MatchDetail.tsx`
- Modify: `frontend/src/index.css`

- [ ] **Step 1: Read current MatchDetail to record routing param + fetch usage**

```bash
cat frontend/src/pages/MatchDetail.tsx
```

- [ ] **Step 2: Replace component body**

```tsx
import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import type { FixtureDetail } from '../lib/api'
import { PredictabilityBadge } from '../components/shared/PredictabilityBadge'
import { PredictionBars } from '../components/match/PredictionBars'
import { ScorelineHeatmap } from '../components/match/ScorelineHeatmap'
import { AhLineSelector } from '../components/match/AhLineSelector'
import { AhLineTable } from '../components/match/AhLineTable'
import { FormStrip } from '../components/match/FormStrip'

export default function MatchDetail() {
  const { id } = useParams()
  const [data, setData] = useState<FixtureDetail | null>(null)
  const [ahLine, setAhLine] = useState<number>(-0.5)
  useEffect(() => {
    fetch(`/api/fixtures/${id}`).then(r => r.json()).then((d: FixtureDetail) => {
      setData(d)
      const lines = d.odds?.asian_handicap_lines ?? []
      if (lines.length) setAhLine(lines[0].line)
    })
  }, [id])

  if (!data) return <div className="loading">加载中…</div>
  const f = data
  const ah_lines = data.odds?.asian_handicap_lines ?? []

  return (
    <div className="md">
      <section className="md-hero">
        <div className="md-hero-top">
          <PredictabilityBadge level={f.predictability} />
          <h1>{f.home_team} vs {f.away_team}</h1>
        </div>
        <div className="md-hero-meta">
          {f.competition_name} · {new Date(f.kickoff_utc).toLocaleString('zh-CN')}
        </div>
      </section>

      <section className="md-section">
        <h2>模型概率</h2>
        <PredictionBars prediction={data.prediction} />
      </section>

      <section className="md-section">
        <div className="md-section-head">
          <h2>比分概率 × 亚盘切片</h2>
          {ah_lines.length > 0 && (
            <AhLineSelector value={ahLine}
                             options={ah_lines.map(l => l.line)}
                             onChange={setAhLine} />
          )}
        </div>
        {data.prediction
          ? <ScorelineHeatmap scorelines={data.prediction.scorelines} ahLine={ahLine} />
          : <div className="md-empty">无模型数据</div>}
      </section>

      <section className="md-section">
        <h2>赔率全表</h2>
        <AhLineTable lines={ah_lines} />
      </section>

      <section className="md-section">
        <h2>两队状态</h2>
        <div className="md-stats">
          <div className="md-stat-col">
            <h3>{f.home_team}</h3>
            <FormStrip form5={data.home_team_obj?.form?.form5 ?? ''} />
          </div>
          <div className="md-stat-col">
            <h3>{f.away_team}</h3>
            <FormStrip form5={data.away_team_obj?.form?.form5 ?? ''} />
          </div>
        </div>
      </section>

      <section className="md-section">
        <h2>跌赔记录</h2>
        {data.dropping_records.length === 0 ? (
          <div className="md-empty">无跌赔</div>
        ) : (
          <ul className="md-drops">
            {data.dropping_records.slice(0, 20).map((d, i) => (
              <li key={i}>
                <span className="md-drop-mkt">{d.market_key}</span>
                <span className="md-drop-pct">{Math.round(d.drop_pct)}%</span>
                <span className="md-drop-bm">{d.bookmaker}</span>
                <span className="md-drop-at">{new Date(d.recorded_at).toLocaleString()}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
```

注意：后端 Task 2.5 已经把 nested 对象键命名为 `home_team_obj` / `away_team_obj`（避免与 `fixture.home_team` 字符串字段冲突）。前端 `FixtureDetail` 类型也用同名键，无需 patch。

- [ ] **Step 3: CSS**

```css
.md { max-width: 980px; margin: 0 auto; padding: 16px; }
.md-hero-top { display: flex; gap: 12px; align-items: center; }
.md-hero-top h1 { font-size: 24px; margin: 0; }
.md-hero-meta { color: #888; font-size: 13px; margin-top: 4px; }
.md-section { margin-top: 20px; padding: 16px; background: #fff;
               border-radius: 8px; border: 1px solid #eee; }
.md-section h2 { margin: 0 0 12px 0; font-size: 16px; }
.md-section-head { display: flex; justify-content: space-between; align-items: center; }
.md-empty { color: #888; text-align: center; padding: 16px; }
.md-stats { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.md-stat-col h3 { margin: 0 0 8px 0; font-size: 14px; }
.md-drops { list-style: none; padding: 0; margin: 0; }
.md-drops li { display: grid; grid-template-columns: 1fr 60px 100px 120px; gap: 8px;
                padding: 8px 0; border-bottom: 1px solid #f0f0f0; font-size: 13px; }
.md-drop-pct { color: #c30; text-align: right; font-weight: 600; }
```

- [ ] **Step 4: Build frontend + smoke**

```bash
cd frontend && npm run build && npm run dev
```

打开一场有 AI 模型的 MatchDetail，验证 5 个 block 顺序正确、AH 切档热力图重画、跌赔记录显示。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/MatchDetail.tsx frontend/src/index.css
git commit -m "feat(ui): MatchDetail 5-block layout with heatmap + AH selector"
```

---

## Task 4.7：`Dashboard.tsx` 升级

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx`
- Modify: `backend/routers/fixtures.py`（让 `/fixtures` 的 `total` 返回真实总数）
- Modify: `backend/tests/test_routers_fixtures.py`

- [ ] **Step 1: Make backend `/fixtures` return real total**

在 `list_fixtures` 末尾，return 前替换：

```python
# 真实总数（不受 limit 影响）
count_sql = sql.replace("ORDER BY f.kickoff_utc LIMIT " + str(int(limit)), "")
count_sql = "SELECT COUNT(*) FROM (" + count_sql.replace("SELECT f.*, ", "SELECT f.id ", 1) + ")"
# 但 count_sql 还有 LEFT JOIN 衍生列，简化：用子查询包裹原 SQL 不带 LIMIT
async with db.execute(count_sql, params) as ccur:
    total_row = await ccur.fetchone()
total = total_row[0] if total_row else len(fixtures)
return {"fixtures": fixtures, "total": total, "cached_at": None}
```

注：上面的 string replace 易碎，更稳健的做法是把构造 SQL 时**分离 base 与 LIMIT**，COUNT 时只跑 base 包裹：

```python
base_sql = ... # WHERE 之前 + 全部 WHERE 条件，不带 ORDER BY/LIMIT
sql = base_sql + f" ORDER BY f.kickoff_utc LIMIT {int(limit)}"
count_sql = "SELECT COUNT(*) FROM (" + base_sql.replace("SELECT f.*,", "SELECT f.id,", 1) + ")"
```

实施时按此模式重构。

- [ ] **Step 2: Update existing tests that assume `total = len(fixtures)`**

把 `test_list_fixtures_returns_match` 等保留：单条数据 total 仍然 = 1。无需改。

- [ ] **Step 3: Run backend tests**

```bash
cd backend && .venv/bin/pytest tests/test_routers_fixtures.py -v
```

Expected: 全 PASS。

- [ ] **Step 4: Update Dashboard**

`frontend/src/pages/Dashboard.tsx`：

```tsx
import { useEffect, useState } from 'react'

type Counts = { total: number; withAi: number; predMid: number }

export default function Dashboard() {
  const [counts, setCounts] = useState<Counts>({ total: 0, withAi: 0, predMid: 0 })
  const [topDrops, setTopDrops] = useState<any[]>([])

  useEffect(() => {
    Promise.all([
      fetch('/api/fixtures?limit=1').then(r => r.json()),
      fetch('/api/fixtures?limit=1&has_ai=true').then(r => r.json()),
      fetch('/api/fixtures?limit=1&predictability=high,good,medium').then(r => r.json()),
    ]).then(([a, b, c]) => setCounts({ total: a.total, withAi: b.total, predMid: c.total }))
    fetch('/api/dropping-odds?min_drop=50').then(r => r.json())
      .then(d => setTopDrops((d.items ?? []).slice(0, 5)))
  }, [])

  return (
    <div className="dash">
      <div className="dash-tiles">
        <div className="tile"><span className="tile-num">{counts.total}</span><span>未来 7 天候选</span></div>
        <div className="tile"><span className="tile-num">{counts.withAi}</span><span>有 AI 模型</span></div>
        <div className="tile"><span className="tile-num">{counts.predMid}</span><span>预测度 ≥ 一般</span></div>
      </div>
      <section className="dash-section">
        <h2>今日 Top 5 跌赔</h2>
        <ul className="top-drops">
          {topDrops.map((d, i) => (
            <li key={i}>
              <span>{d.home_team} vs {d.away_team}</span>
              <span className="drop-pct">{Math.round(d.drop_pct)}%</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
```

- [ ] **Step 5: CSS**

```css
.dash { padding: 16px; }
.dash-tiles { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.tile { padding: 16px; background: #fff; border-radius: 8px; border: 1px solid #eee;
        display: flex; flex-direction: column; gap: 4px; }
.tile-num { font-size: 28px; font-weight: 700; }
.dash-section { margin-top: 20px; padding: 16px; background: #fff; border-radius: 8px;
                 border: 1px solid #eee; }
.top-drops { list-style: none; padding: 0; margin: 0; }
.top-drops li { display: flex; justify-content: space-between; padding: 8px 0;
                 border-bottom: 1px solid #f0f0f0; font-size: 13px; }
.drop-pct { color: #c30; font-weight: 600; }
```

- [ ] **Step 6: Build + smoke**

```bash
cd backend && .venv/bin/pytest -v && cd ../frontend && npm run build
```

Expected: 全 PASS, build 成功。

- [ ] **Step 7: Commit**

```bash
git add backend/routers/fixtures.py backend/tests/test_routers_fixtures.py \
        frontend/src/pages/Dashboard.tsx frontend/src/index.css
git commit -m "feat(ui): Dashboard 3-tile + top 5 drops; backend returns real total count"
```

---

## Task 4.8：M4 验收截图

**Files:**
- Create: `docs/screenshots/m4-matchdetail-heatmap.png`
- Create: `docs/screenshots/m4-matchdetail-odds-table.png`

- [ ] **Step 1: Take screenshots**

跑 `npm run dev`，进 MatchDetail（一场有 AI 模型的），分别截：
1. 比分热力图 block，切到 -0.75 档显示赢/和/输 % → `m4-matchdetail-heatmap.png`
2. 赔率全表 + 模型概率两 block 一屏 → `m4-matchdetail-odds-table.png`

- [ ] **Step 2: Commit**

```bash
git add docs/screenshots/m4-*.png
git commit -m "docs: M4 acceptance screenshots"
```

---

## Task 4.9：MVP DoD 验证

**Files:**
- Create: `docs/superpowers/dod/2026-05-16-asian-handicap-mvp.md`

- [ ] **Step 1: Run full backend test suite**

```bash
cd backend && .venv/bin/pytest -v
```

Expected: 全 PASS。

- [ ] **Step 2: Run backfill on clean DB**

```bash
rm -f goalcast.db
.venv/bin/python -m scripts.backfill
```

记录耗时与行数：

```bash
sqlite3 goalcast.db <<'SQL'
SELECT 'fixtures',       COUNT(*) FROM fixtures;
SELECT 'predictions',    COUNT(*) FROM predictions;
SELECT 'team_form',      COUNT(*) FROM team_form;
SELECT 'bookmaker_odds', COUNT(*) FROM bookmaker_odds;
SQL
```

- [ ] **Step 3: DoD checklist**

写入 `docs/superpowers/dod/2026-05-16-asian-handicap-mvp.md`：

```markdown
# MVP DoD 验证 — 2026-XX-XX

## 行数
- fixtures: <N>
- predictions: <N>
- team_form: <N>
- bookmaker_odds: <N>

## 验收
- [ ] fixtures ≥ 5,000
- [ ] predictions ≥ 3,000
- [ ] team_form ≥ 1,500
- [ ] bookmaker_odds ≥ 50,000
- [ ] 抽查 5 张 MatchCard：≥ 3 张显示「Pinnacle + Bet365」双家
- [ ] 抽查 5 张 MatchCard：≥ 4 张显示 form5
- [ ] MatchDetail 比分热力图首渲染 < 200ms
- [ ] MatchDetail AH 切档重画 < 50ms
- [ ] 4 张截图已入 docs/screenshots/

## 备注
<填异常发现 / 跳过项 / 后续工单>
```

- [ ] **Step 4: Commit**

```bash
mkdir -p docs/superpowers/dod
git add docs/superpowers/dod/
git commit -m "docs: MVP DoD verification log"
```

---

# 自审清单

| Spec 章节 / 要求 | 对应任务 |
|---|---|
| §2 `predictions` 表 | Task 1.1 |
| §2 `team_form` 表 | Task 1.1 |
| §2 `bookmaker_odds` 表 | Task 1.1 |
| §2 `fixtures.predictability` | Task 1.1 |
| §2 `fixtures.season_id`（隐含） | Task 1.1 |
| §3 sync_fixtures_upcoming | Task 1.3 |
| §3 sync_team_form | Task 1.4 |
| §3 sync_ah_odds_seed | Task 1.5 |
| §3 sync_ah_odds_latest | Task 1.6 |
| §3 sync_predictions | Task 2.2 |
| §3 backfill 脚本 | Task 1.8 + Task 2.2 |
| §3 错误隔离 (`_log`) | 每个 sync try/except |
| §3 scheduler 注册 | Task 1.7 + Task 2.2 |
| §4 GET /fixtures 响应字段 | Task 2.4 |
| §4 GET /fixtures 新 query | Task 2.4 |
| §4 GET /fixtures/{id} 响应 | Task 2.5 |
| §4 主 AH 档推导 | Task 2.3 |
| §5 Matches filter chips | Task 3.6 |
| §5 MatchCard 重写 | Task 3.5 |
| §5 MatchDetail 5 block | Task 4.6 |
| §5 Dashboard 升级 | Task 4.7 |
| §5 7 个新组件 | Tasks 3.2 / 3.3 / 3.4 / 4.1 / 4.3 / 4.4 / 4.5 |
| §5 lib/api.ts 类型 | Task 3.1 |
| §5 4 张截图 | Tasks 3.7 / 4.8 |
| §6 M1–M4 顺序 | 任务编号 1.x / 2.x / 3.x / 4.x |
| §6 DoD | Task 4.9 |
| 附录 A T-DATA-1 form5 | Task 1.4 + Task 3.5 |
| 附录 A T-DATA-3 opening | Task 1.5 + Task 2.4 / 2.5 |
| 附录 A T-DATA-4 1x2 三路 | Task 1.5 + Task 3.5 |
| 附录 A T-DATA-2 H2H | 永久搁置（spec 已说明） |

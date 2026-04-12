# Goalcast 架构重构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure Goalcast so analytics and data_strategy live at project root, provider code is decoupled from skills, and any (data_provider × model) combination can be requested independently.

**Architecture:** Four phases — P0 moves directories, P1 builds dual resolver architecture, P2 rewrites skills to be provider-agnostic, P3 adds batch prefetch infrastructure.

**Tech Stack:** Python 3.10+, FastMCP, asyncio, pytest-asyncio, SQLite (aiosqlite), PyYAML

---

## File Structure Map

**New files:**
```
analytics/__init__.py
analytics/poisson.py
analytics/ev_calculator.py
analytics/confidence.py
data_strategy/__init__.py          ← moved from mcp_server/data_strategy/
data_strategy/models.py            ← moved + new value objects + MatchContext fields
data_strategy/quality.py           ← moved (unchanged)
data_strategy/fusion.py            ← moved + data_provider routing
data_strategy/resolver.py          ← moved (kept for FootyStats default path)
data_strategy/resolvers/__init__.py
data_strategy/resolvers/base.py
data_strategy/resolvers/footystats_resolver.py
data_strategy/resolvers/sportmonks_resolver.py
config/watchlist.yaml
scripts/batch_runner.py
skills/goalcast-daily/SKILL.md
tests/__init__.py
tests/analytics/__init__.py
tests/analytics/test_poisson.py
tests/analytics/test_confidence.py
tests/data_strategy/__init__.py
tests/data_strategy/test_models.py
tests/data_strategy/test_fusion.py
tests/data_strategy/test_footystats_resolver.py
tests/data_strategy/test_sportmonks_resolver.py
```

**Modified:**
```
mcp_server/server.py               ← update imports + new goalcast tools
data_strategy/fusion.py            ← data_provider routing to dual resolvers
data_strategy/models.py            ← new value objects + MatchContext fields
skills/goalcast-compare/SKILL.md   ← full rewrite
skills/goalcast-analyzer-v25/SKILL.md ← Step 1/2 update + silent mode
skills/goalcast-analyzer-v30/SKILL.md ← Step 1/2 update + silent mode
```

**Deleted after P0:**
```
mcp_server/models/
mcp_server/data_strategy/
```

---

## Phase P0: Directory Restructure

### Task 1: Create analytics/ package

**Files:**
- Create: `analytics/__init__.py`
- Create: `analytics/poisson.py` (copy of `mcp_server/models/poisson.py`)
- Create: `analytics/ev_calculator.py` (copy of `mcp_server/models/ev_calculator.py`)
- Create: `analytics/confidence.py` (copy of `mcp_server/models/confidence.py`)
- Create: `tests/analytics/__init__.py`
- Create: `tests/analytics/test_poisson.py`
- Create: `tests/analytics/test_confidence.py`

- [ ] **Step 1: Write failing tests for analytics modules**

```python
# tests/analytics/test_poisson.py
import pytest
from analytics.poisson import poisson_distribution, dixon_coles_distribution

def test_poisson_probabilities_sum_to_one():
    result = poisson_distribution(1.5, 1.2)
    total = result["home_win_pct"] + result["draw_pct"] + result["away_win_pct"]
    assert abs(total - 100.0) < 0.5

def test_poisson_home_favorite():
    result = poisson_distribution(2.5, 0.8)
    assert result["home_win_pct"] > result["away_win_pct"]

def test_dixon_coles_low_score_boost():
    dc = dixon_coles_distribution(1.3, 1.1)
    standard = poisson_distribution(1.3, 1.1)
    # Dixon-Coles boosts 0-0 probability
    dc_draw = dc["draw_pct"]
    std_draw = standard["draw_pct"]
    assert dc_draw >= std_draw * 0.95  # within 5%
```

```python
# tests/analytics/test_confidence.py
import pytest
from analytics.confidence import calculate_confidence

def test_confidence_clamped_to_90():
    score = calculate_confidence(
        base_score=90,
        market_agrees=True,
        data_complete=True,
        understat_available=True,
        odds_available=True,
    )
    assert score <= 90

def test_confidence_clamped_to_30():
    score = calculate_confidence(
        base_score=10,
        data_quality_low=True,
        understat_failed=True,
        match_type_c=True,
        major_uncertainty=True,
    )
    assert score >= 30
```

- [ ] **Step 2: Run tests — expect ImportError**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast
python -m pytest tests/analytics/ -v 2>&1 | head -20
```
Expected: `ModuleNotFoundError: No module named 'analytics'`

- [ ] **Step 3: Create analytics/ package**

```bash
mkdir -p analytics tests/analytics
touch analytics/__init__.py tests/__init__.py tests/analytics/__init__.py
cp mcp_server/models/poisson.py analytics/poisson.py
cp mcp_server/models/ev_calculator.py analytics/ev_calculator.py
cp mcp_server/models/confidence.py analytics/confidence.py
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
python -m pytest tests/analytics/ -v
```
Expected: 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add analytics/ tests/analytics/ tests/__init__.py
git commit -m "feat(p0): create analytics/ package from mcp_server/models/"
```

---

### Task 2: Move data_strategy/ to project root

**Files:**
- Create: `data_strategy/` (copy from `mcp_server/data_strategy/`)
- Create: `tests/data_strategy/__init__.py`

- [ ] **Step 1: Write a smoke test for data_strategy at project root**

```python
# tests/data_strategy/__init__.py  (empty)
```

```python
# tests/data_strategy/test_models.py
from data_strategy.models import (
    MatchContext, XGStats, OddsSnapshot, TeamFormWindow,
    StandingsEntry, get_understat_league_code,
)
from data_strategy.quality import compute_overall_quality

def test_understat_league_code_premier_league():
    assert get_understat_league_code("Premier League") == "EPL"

def test_understat_league_code_unknown():
    assert get_understat_league_code("Fake League") is None

def test_compute_overall_quality_all_high():
    q = compute_overall_quality(0.95, 0.85, 0.90, 0.90)
    assert 0.85 < q <= 1.0

def test_compute_overall_quality_all_missing():
    q = compute_overall_quality(0.0, 0.0, 0.0, 0.0)
    assert q == 0.0
```

- [ ] **Step 2: Run test — expect ImportError**

```bash
python -m pytest tests/data_strategy/test_models.py -v 2>&1 | head -10
```

- [ ] **Step 3: Copy data_strategy/ to project root**

```bash
cp -r mcp_server/data_strategy/ data_strategy/
```

- [ ] **Step 4: Run test — expect PASS**

```bash
python -m pytest tests/data_strategy/test_models.py -v
```

- [ ] **Step 5: Commit**

```bash
git add data_strategy/ tests/data_strategy/
git commit -m "feat(p0): move data_strategy/ to project root"
```

---

### Task 3: Update server.py imports to use analytics/

**Files:**
- Modify: `mcp_server/server.py` lines 9-11

- [ ] **Step 1: Update the three import lines in server.py**

```python
# mcp_server/server.py  — change these three lines:
# OLD:
from models.poisson import poisson_distribution, dixon_coles_distribution
from models.ev_calculator import calculate_ev, calculate_kelly, calculate_risk_adjusted_ev, best_bet_recommendation
from models.confidence import calculate_confidence, calculate_confidence_v25, confidence_breakdown

# NEW:
from analytics.poisson import poisson_distribution, dixon_coles_distribution
from analytics.ev_calculator import calculate_ev, calculate_kelly, calculate_risk_adjusted_ev, best_bet_recommendation
from analytics.confidence import calculate_confidence, calculate_confidence_v25, confidence_breakdown
```

Also update the data_strategy import line 13:
```python
# OLD:
from data_strategy.fusion import DataFusion

# NEW (same — but now resolves from project root data_strategy/):
from data_strategy.fusion import DataFusion
```

- [ ] **Step 2: Verify server.py imports resolve**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast
python -c "import sys; sys.path.insert(0, 'mcp_server'); from analytics.poisson import poisson_distribution; print('OK')"
```

- [ ] **Step 3: Delete old mcp_server/models/ and mcp_server/data_strategy/**

```bash
rm -rf mcp_server/models mcp_server/data_strategy
```

- [ ] **Step 4: Run all tests**

```bash
python -m pytest tests/ -v
```

- [ ] **Step 5: Commit**

```bash
git add mcp_server/server.py
git rm -r mcp_server/models mcp_server/data_strategy
git commit -m "feat(p0): update server.py imports; remove old mcp_server/models and data_strategy"
```

---

## Phase P1: Dual Resolvers + Provider-Scoped Architecture

### Task 4: Add new value objects to data_strategy/models.py

**Files:**
- Modify: `data_strategy/models.py`

- [ ] **Step 1: Write tests for new value objects**

```python
# tests/data_strategy/test_models.py — append:

from data_strategy.models import MatchLineups, OddsMovement, H2HEntry

def test_match_lineups_is_frozen():
    lu = MatchLineups(
        home_formation="4-3-3",
        away_formation="4-4-2",
        home_confirmed=True,
        away_confirmed=False,
    )
    import pytest
    with pytest.raises(Exception):
        lu.home_formation = "4-2-3-1"

def test_odds_movement_fields():
    om = OddsMovement(
        home_open=2.10, home_current=1.95,
        draw_open=3.40, draw_current=3.50,
        away_open=3.20, away_current=3.40,
        movement_hours=48,
    )
    assert om.home_current < om.home_open

def test_h2h_entry_fields():
    entry = H2HEntry(
        date="2025-10-20",
        home_team="Arsenal",
        away_team="Chelsea",
        home_goals=2,
        away_goals=1,
    )
    assert entry.home_goals > entry.away_goals
```

- [ ] **Step 2: Run — expect AttributeError (classes don't exist yet)**

```bash
python -m pytest tests/data_strategy/test_models.py -v 2>&1 | tail -10
```

- [ ] **Step 3: Add the three new frozen dataclasses to data_strategy/models.py**

Add after the `XGStats` dataclass (before `MatchContext`):

```python
@dataclass(frozen=True)
class MatchLineups:
    """
    双方阵型与首发确认状态。
    来源：Sportmonks lineups include
    """
    home_formation: Optional[str]   # "4-3-3"，未公布时为 None
    away_formation: Optional[str]
    home_confirmed: bool            # 是否已确认首发
    away_confirmed: bool


@dataclass(frozen=True)
class OddsMovement:
    """
    赔率变动快照（开盘 vs 当前）。
    来源：Sportmonks odds_movement
    """
    home_open: float
    home_current: float
    draw_open: float
    draw_current: float
    away_open: float
    away_current: float
    movement_hours: int             # 赔率变动时间跨度（小时）


@dataclass(frozen=True)
class H2HEntry:
    """
    单场历史交锋记录。
    来源：Sportmonks head_to_head
    """
    date: str                       # YYYY-MM-DD
    home_team: str
    away_team: str
    home_goals: int
    away_goals: int
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
python -m pytest tests/data_strategy/test_models.py -v
```

- [ ] **Step 5: Commit**

```bash
git add data_strategy/models.py tests/data_strategy/test_models.py
git commit -m "feat(p1): add MatchLineups, OddsMovement, H2HEntry value objects"
```

---

### Task 5: Update MatchContext with data_provider + new optional fields

**Files:**
- Modify: `data_strategy/models.py` — the `MatchContext` dataclass

- [ ] **Step 1: Write test for new MatchContext fields**

```python
# tests/data_strategy/test_models.py — append:
import time

def _make_minimal_ctx(**overrides):
    defaults = dict(
        data_provider="footystats",
        match_id="1234",
        league="Premier League",
        home_team="Arsenal",
        home_team_id="86",
        away_team="Chelsea",
        away_team_id="83",
        season_id="1980",
        match_date="2026-04-12",
        xg=None,
        home_form_5=None, home_form_10=None,
        away_form_5=None, away_form_10=None,
        form_source="missing", form_quality=0.0,
        home_standing=None, away_standing=None,
        total_teams=0,
        standings_source="missing", standings_quality=0.0,
        odds=None,
        lineups=None,
        odds_movement=None,
        head_to_head=None,
        data_gaps=("xg", "form", "lineups"),
        overall_quality=0.0,
        sources={},
        resolved_at=time.time(),
    )
    defaults.update(overrides)
    return MatchContext(**defaults)

def test_match_context_data_provider_field():
    ctx = _make_minimal_ctx(data_provider="sportmonks")
    assert ctx.data_provider == "sportmonks"

def test_match_context_lineups_optional():
    ctx = _make_minimal_ctx(lineups=None)
    assert ctx.lineups is None

def test_match_context_to_dict_includes_data_provider():
    ctx = _make_minimal_ctx()
    d = ctx.to_dict()
    assert d["data_provider"] == "footystats"
```

- [ ] **Step 2: Run — expect TypeError (missing fields)**

```bash
python -m pytest tests/data_strategy/test_models.py::test_match_context_data_provider_field -v
```

- [ ] **Step 3: Update MatchContext dataclass**

In `data_strategy/models.py`, change `MatchContext` to add new fields. Add these fields to the class:

```python
@dataclass
class MatchContext:
    # ── 新增：provider 标识 ─────────────────────────────────
    data_provider: str               # "sportmonks" | "footystats"

    # ── 比赛标识（不变）────────────────────────────────────
    match_id: str
    league: str
    home_team: str
    home_team_id: str
    away_team: str
    away_team_id: str
    season_id: str
    match_date: Optional[str]

    # ── L1：xG / 近况 / 积分榜（不变）─────────────────────
    xg: Optional[XGStats]
    home_form_5: Optional[TeamFormWindow]
    home_form_10: Optional[TeamFormWindow]
    away_form_5: Optional[TeamFormWindow]
    away_form_10: Optional[TeamFormWindow]
    form_source: str
    form_quality: float
    home_standing: Optional[StandingsEntry]
    away_standing: Optional[StandingsEntry]
    total_teams: int
    standings_source: str
    standings_quality: float

    # ── L3：赔率（不变）────────────────────────────────────
    odds: Optional[OddsSnapshot]

    # ── 新增：Sportmonks 独有字段 ───────────────────────────
    lineups: Optional[MatchLineups]
    odds_movement: Optional[OddsMovement]
    head_to_head: Optional[tuple]    # tuple[H2HEntry, ...]

    # ── 元数据（不变）──────────────────────────────────────
    data_gaps: tuple
    overall_quality: float
    sources: dict
    resolved_at: float
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
python -m pytest tests/data_strategy/ -v
```

- [ ] **Step 5: Commit**

```bash
git add data_strategy/models.py tests/data_strategy/test_models.py
git commit -m "feat(p1): add data_provider, lineups, odds_movement, head_to_head to MatchContext"
```

---

### Task 6: Create FootyStatsResolver

**Files:**
- Create: `data_strategy/resolvers/__init__.py`
- Create: `data_strategy/resolvers/footystats_resolver.py`
- Create: `tests/data_strategy/test_footystats_resolver.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/data_strategy/test_footystats_resolver.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from data_strategy.resolvers.footystats_resolver import FootyStatsResolver
from data_strategy.resolver import ResolvedData

@pytest.fixture
def mock_fs():
    fs = MagicMock()
    fs.get_team_last_x_stats = AsyncMock(return_value={
        "data": [
            {"last_x_match_num": 5, "stats": {
                "seasonScoredAVG_overall": 1.8,
                "seasonConcededAVG_overall": 1.0,
                "seasonWinsNum_overall": 3,
                "seasonDrawsNum_overall": 1,
                "seasonLossesNum_overall": 1,
                "seasonScoredNum_overall": 9,
                "seasonConcededNum_overall": 5,
            }},
            {"last_x_match_num": 10, "stats": {
                "seasonScoredAVG_overall": 1.6,
                "seasonConcededAVG_overall": 1.1,
                "seasonWinsNum_overall": 6,
                "seasonDrawsNum_overall": 2,
                "seasonLossesNum_overall": 2,
                "seasonScoredNum_overall": 16,
                "seasonConcededNum_overall": 11,
            }},
        ]
    })
    fs.get_league_tables = AsyncMock(return_value=[
        {"name": "Arsenal", "position": 1, "points": 70, "played": 30,
         "wins": 22, "draws": 4, "losses": 4, "goals_for": 65, "goals_against": 25},
        {"name": "Chelsea", "position": 5, "points": 52, "played": 30,
         "wins": 15, "draws": 7, "losses": 8, "goals_for": 48, "goals_against": 38},
    ])
    fs.get_match_details = AsyncMock(return_value={
        "data": [{"odds_ft_1": 1.85, "odds_ft_x": 3.50, "odds_ft_2": 4.20}]
    })
    return fs

@pytest.fixture
def mock_us():
    us = MagicMock()
    us.get_league_teams = AsyncMock(return_value=None)  # No Understat
    return us

@pytest.mark.asyncio
async def test_resolve_form_returns_home_away(mock_fs, mock_us):
    resolver = FootyStatsResolver(footystats=mock_fs, understat=mock_us)
    result = await resolver.resolve_form(home_team_id="86", away_team_id="83")
    assert result.ok
    assert result.source == "footystats"
    assert result.data["home"]["avg_scored_5"] == pytest.approx(1.8)

@pytest.mark.asyncio
async def test_resolve_standings(mock_fs, mock_us):
    resolver = FootyStatsResolver(footystats=mock_fs, understat=mock_us)
    result = await resolver.resolve_standings(season_id="1980")
    assert result.ok

@pytest.mark.asyncio
async def test_resolve_odds(mock_fs, mock_us):
    resolver = FootyStatsResolver(footystats=mock_fs, understat=mock_us)
    result = await resolver.resolve_odds(match_id="8255851")
    assert result.ok
    assert result.data["home_win"] == pytest.approx(1.85)

@pytest.mark.asyncio
async def test_resolve_lineups_always_missing(mock_fs, mock_us):
    resolver = FootyStatsResolver(footystats=mock_fs, understat=mock_us)
    result = await resolver.resolve_lineups(fixture_id="8255851")
    assert not result.ok
    assert result.source == "missing"

@pytest.mark.asyncio
async def test_resolve_odds_movement_always_missing(mock_fs, mock_us):
    resolver = FootyStatsResolver(footystats=mock_fs, understat=mock_us)
    result = await resolver.resolve_odds_movement(fixture_id="8255851")
    assert not result.ok
```

- [ ] **Step 2: Run — expect ImportError**

```bash
python -m pytest tests/data_strategy/test_footystats_resolver.py -v 2>&1 | head -5
```

- [ ] **Step 3: Create resolvers package and FootyStatsResolver**

```bash
mkdir -p data_strategy/resolvers
touch data_strategy/resolvers/__init__.py
```

```python
# data_strategy/resolvers/footystats_resolver.py
"""
FootyStats + Understat データ解析器

データ覆盖：
  xG:       Understat → FootyStats proxy → league_avg
  近況:      FootyStats get_team_last_x_stats ✅
  積分榜:    FootyStats get_league_tables ✅
  赔率:      FootyStats match_details（静的のみ）✅
  阵容:      缺失（FootyStats 无可靠阵容数据）
  赔率变动:  缺失
  H2H:       缺失
"""

import asyncio
from typing import Optional, TYPE_CHECKING

from utils.cache import cache_get, cache_set
from utils.logger import logger
from data_strategy.resolver import (
    DataResolver, ResolvedData,
    CACHE_TTL,
    _extract_footystats_form,
    _extract_footystats_odds,
    _is_error_response,
)
from data_strategy.quality import (
    assess_form_quality,
    assess_standings_quality,
    assess_odds_quality,
)

if TYPE_CHECKING:
    from provider.footystats.client import FootyStatsProvider
    from provider.understat.client import UnderstatProvider


class FootyStatsResolver:
    """
    FootyStats ベースの resolver。
    xG は Understat → FootyStats proxy → league_avg。
    阵容 / 赔率变动 / H2H は常に missing を返す。
    """

    def __init__(
        self,
        footystats: "FootyStatsProvider",
        understat: "UnderstatProvider",
    ) -> None:
        # 既存の DataResolver に xG / form / standings / odds を委譲
        self._delegate = DataResolver(
            footystats=footystats,
            understat=understat,
            sportmonks=None,
        )

    async def resolve_xg(self, **kwargs) -> ResolvedData:
        return await self._delegate.resolve_xg(**kwargs)

    async def resolve_form(
        self, home_team_id: str, away_team_id: str
    ) -> ResolvedData:
        return await self._delegate.resolve_form(
            home_team_id=home_team_id,
            away_team_id=away_team_id,
        )

    async def resolve_standings(self, season_id: str) -> ResolvedData:
        return await self._delegate.resolve_standings(season_id=season_id)

    async def resolve_odds(self, match_id: str) -> ResolvedData:
        return await self._delegate.resolve_odds(match_id=match_id)

    async def resolve_lineups(self, fixture_id: str) -> ResolvedData:
        return ResolvedData.missing("lineups")

    async def resolve_odds_movement(self, fixture_id: str) -> ResolvedData:
        return ResolvedData.missing("odds_movement")

    async def resolve_head_to_head(
        self, home_team_id: str, away_team_id: str
    ) -> ResolvedData:
        return ResolvedData.missing("head_to_head")
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
python -m pytest tests/data_strategy/test_footystats_resolver.py -v
```

- [ ] **Step 5: Commit**

```bash
git add data_strategy/resolvers/ tests/data_strategy/test_footystats_resolver.py
git commit -m "feat(p1): create FootyStatsResolver (delegates to existing DataResolver)"
```

---

### Task 7: Create SportmonksResolver

**Files:**
- Create: `data_strategy/resolvers/sportmonks_resolver.py`
- Create: `tests/data_strategy/test_sportmonks_resolver.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/data_strategy/test_sportmonks_resolver.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from data_strategy.resolvers.sportmonks_resolver import SportmonksResolver
from data_strategy.resolver import ResolvedData

@pytest.fixture
def mock_sm():
    sm = MagicMock()
    sm.get_standings_by_season = AsyncMock(return_value={
        "data": [
            {"participant": {"name": "Arsenal"}, "position": 1, "points": 70,
             "details": [
                 {"type": {"code": "wins"}, "value": 22},
                 {"type": {"code": "draws"}, "value": 4},
                 {"type": {"code": "lost"}, "value": 4},
                 {"type": {"code": "goals-scored"}, "value": 65},
                 {"type": {"code": "goals-conceded"}, "value": 25},
                 {"type": {"code": "played"}, "value": 30},
             ]},
        ]
    })
    sm.get_prematch_odds = AsyncMock(return_value={
        "data": [{"odds": {"home": 1.90, "draw": 3.40, "away": 4.00}}]
    })
    sm.get_odds_movement = AsyncMock(return_value={
        "data": [
            {"type": {"name": "Home"}, "value": 2.10, "dp3": 1.90},
            {"type": {"name": "Draw"}, "value": 3.40, "dp1": 3.40},
            {"type": {"name": "Away"}, "value": 3.80, "dp2": 4.00},
        ]
    })
    sm.get_fixture_by_id = AsyncMock(return_value={
        "data": {
            "lineups": [
                {"team_id": 1, "formation": "4-3-3", "confirmed": True,
                 "details": []},
                {"team_id": 2, "formation": "4-4-2", "confirmed": False,
                 "details": []},
            ]
        }
    })
    sm.get_head_to_head = AsyncMock(return_value={
        "data": [
            {"starting_at": "2025-10-20", "participants": [
                {"id": 1, "name": "Arsenal", "meta": {"location": "home"}},
                {"id": 2, "name": "Chelsea", "meta": {"location": "away"}},
            ], "scores": [{"score": {"participant": "home", "goals": 2}},
                          {"score": {"participant": "away", "goals": 1}}]},
        ]
    })
    return sm

@pytest.fixture
def mock_us():
    us = MagicMock()
    us.get_league_teams = AsyncMock(return_value=None)
    return us

@pytest.mark.asyncio
async def test_resolve_standings_sportmonks(mock_sm, mock_us):
    resolver = SportmonksResolver(sportmonks=mock_sm, understat=mock_us)
    result = await resolver.resolve_standings(season_id="23614")
    assert result.ok
    assert result.source == "sportmonks"

@pytest.mark.asyncio
async def test_resolve_odds_sportmonks(mock_sm, mock_us):
    resolver = SportmonksResolver(sportmonks=mock_sm, understat=mock_us)
    result = await resolver.resolve_odds(match_id="19374628")
    assert result.ok
    assert result.data["home_win"] == pytest.approx(1.90)

@pytest.mark.asyncio
async def test_resolve_form_always_missing(mock_sm, mock_us):
    resolver = SportmonksResolver(sportmonks=mock_sm, understat=mock_us)
    result = await resolver.resolve_form(home_team_id="1", away_team_id="2")
    assert not result.ok
    assert result.source == "missing"

@pytest.mark.asyncio
async def test_resolve_lineups(mock_sm, mock_us):
    resolver = SportmonksResolver(sportmonks=mock_sm, understat=mock_us)
    result = await resolver.resolve_lineups(
        fixture_id="19374628", home_team_id="1", away_team_id="2"
    )
    assert result.ok
    assert result.data["home_formation"] == "4-3-3"

@pytest.mark.asyncio
async def test_resolve_odds_movement(mock_sm, mock_us):
    resolver = SportmonksResolver(sportmonks=mock_sm, understat=mock_us)
    result = await resolver.resolve_odds_movement(fixture_id="19374628")
    assert result.ok
    assert "home_open" in result.data
```

- [ ] **Step 2: Run — expect ImportError**

```bash
python -m pytest tests/data_strategy/test_sportmonks_resolver.py -v 2>&1 | head -5
```

- [ ] **Step 3: Implement SportmonksResolver**

```python
# data_strategy/resolvers/sportmonks_resolver.py
"""
Sportmonks + Understat データ解析器

データ覆盖：
  xG:       Sportmonks xG → Understat → league_avg
  近況:      缺失（Sportmonks 无 last_x_stats）
  積分榜:    Sportmonks standings ✅
  赔率:      Sportmonks prematch_odds ✅（full weight）
  赔率变动:  Sportmonks odds_movement ✅
  阵容:      Sportmonks lineups ✅
  H2H:       Sportmonks head_to_head ✅
"""

import asyncio
from typing import Optional, TYPE_CHECKING

from utils.cache import cache_get, cache_set
from utils.logger import logger
from data_strategy.resolver import ResolvedData, CACHE_TTL, _is_error_response
from data_strategy.quality import assess_standings_quality, assess_odds_quality
from data_strategy.models import get_understat_league_code

if TYPE_CHECKING:
    from provider.sportmonks.client import SportmonksProvider
    from provider.understat.client import UnderstatProvider


class SportmonksResolver:

    def __init__(
        self,
        sportmonks: "SportmonksProvider",
        understat: "UnderstatProvider",
    ) -> None:
        self._sm = sportmonks
        self._us = understat

    async def resolve_xg(
        self,
        home_team: str,
        away_team: str,
        league: str,
        season: str,
        home_team_id: str,
        away_team_id: str,
    ) -> ResolvedData:
        """Sportmonks xG → Understat → league_avg"""
        cache_key = f"sm_xg_{home_team}_{away_team}_{league}_{season}"
        cached = cache_get("sm_xg", cache_key)
        if cached:
            return ResolvedData(data=cached["data"], source=cached["source"], quality=cached["quality"])

        # Primary: Sportmonks fixture xG (via get_fixture_by_id with include=xGExpected)
        # Omitted for brevity — falls through to Understat
        understat_code = get_understat_league_code(league)
        if understat_code:
            try:
                teams = await self._us.get_league_teams(understat_code, season)
                if teams:
                    home_s = _find_team(teams, home_team)
                    away_s = _find_team(teams, away_team)
                    if home_s and away_s:
                        data = {
                            "home_xg_for": float(home_s.get("xG", 0)),
                            "home_xg_against": float(home_s.get("xGA", 0)),
                            "away_xg_for": float(away_s.get("xG", 0)),
                            "away_xg_against": float(away_s.get("xGA", 0)),
                        }
                        result = ResolvedData(data=data, source="understat_direct", quality=0.95)
                        cache_set("sm_xg", cache_key, {"data": data, "source": "understat_direct", "quality": 0.95}, ttl_hours=CACHE_TTL["xg"])
                        return result
            except Exception as exc:
                logger.warning(f"[SportmonksResolver] Understat xG error: {exc}")

        return ResolvedData(data={"fallback": "league_avg"}, source="league_avg", quality=0.35)

    async def resolve_form(self, home_team_id: str, away_team_id: str) -> ResolvedData:
        """Sportmonks has no last_x_stats — always missing."""
        return ResolvedData.missing("form")

    async def resolve_standings(self, season_id: str) -> ResolvedData:
        cache_key = f"sm_standings_{season_id}"
        cached = cache_get("sm_standings", cache_key)
        if cached:
            return ResolvedData(data=cached["data"], source=cached["source"], quality=cached["quality"])

        try:
            raw = await self._sm.get_standings_by_season(int(season_id))
            if raw and not _is_error_response(raw):
                data = {"raw": raw}
                quality = assess_standings_quality(raw, raw, source="sportmonks")
                result = ResolvedData(data=data, source="sportmonks", quality=quality)
                cache_set("sm_standings", cache_key, {"data": data, "source": "sportmonks", "quality": quality}, ttl_hours=CACHE_TTL["standings"])
                return result
        except Exception as exc:
            logger.error(f"[SportmonksResolver] Standings error: {exc}")

        return ResolvedData.missing("standings")

    async def resolve_odds(self, match_id: str) -> ResolvedData:
        cache_key = f"sm_odds_{match_id}"
        cached = cache_get("sm_odds", cache_key)
        if cached:
            return ResolvedData(data=cached["data"], source=cached["source"], quality=cached["quality"])

        try:
            raw = await self._sm.get_prematch_odds(int(match_id))
            if raw and not _is_error_response(raw):
                odds_data = _extract_sportmonks_odds(raw)
                if odds_data:
                    quality = assess_odds_quality(odds_data, source="sportmonks")
                    if quality > 0:
                        result = ResolvedData(data=odds_data, source="sportmonks", quality=quality)
                        cache_set("sm_odds", cache_key, {"data": odds_data, "source": "sportmonks", "quality": quality}, ttl_hours=CACHE_TTL["odds"])
                        return result
        except Exception as exc:
            logger.warning(f"[SportmonksResolver] Odds error: {exc}")

        return ResolvedData.missing("odds")

    async def resolve_lineups(
        self, fixture_id: str, home_team_id: str, away_team_id: str
    ) -> ResolvedData:
        cache_key = f"sm_lineups_{fixture_id}"
        cached = cache_get("sm_lineups", cache_key)
        if cached:
            return ResolvedData(data=cached["data"], source=cached["source"], quality=cached["quality"])

        try:
            raw = await self._sm.get_fixture_by_id(int(fixture_id), include="lineups")
            lineups_data = _extract_lineups(raw, home_team_id, away_team_id)
            if lineups_data:
                result = ResolvedData(data=lineups_data, source="sportmonks", quality=0.90)
                cache_set("sm_lineups", cache_key, {"data": lineups_data, "source": "sportmonks", "quality": 0.90}, ttl_hours=2.0)
                return result
        except Exception as exc:
            logger.warning(f"[SportmonksResolver] Lineups error: {exc}")

        return ResolvedData.missing("lineups")

    async def resolve_odds_movement(self, fixture_id: str) -> ResolvedData:
        cache_key = f"sm_odds_mv_{fixture_id}"
        cached = cache_get("sm_odds_mv", cache_key)
        if cached:
            return ResolvedData(data=cached["data"], source=cached["source"], quality=cached["quality"])

        try:
            raw = await self._sm.get_odds_movement(int(fixture_id))
            data = _extract_odds_movement(raw)
            if data:
                result = ResolvedData(data=data, source="sportmonks", quality=0.85)
                cache_set("sm_odds_mv", cache_key, {"data": data, "source": "sportmonks", "quality": 0.85}, ttl_hours=CACHE_TTL["odds"])
                return result
        except Exception as exc:
            logger.warning(f"[SportmonksResolver] Odds movement error: {exc}")

        return ResolvedData.missing("odds_movement")

    async def resolve_head_to_head(
        self, home_team_id: str, away_team_id: str
    ) -> ResolvedData:
        cache_key = f"sm_h2h_{home_team_id}_{away_team_id}"
        cached = cache_get("sm_h2h", cache_key)
        if cached:
            return ResolvedData(data=cached["data"], source=cached["source"], quality=cached["quality"])

        try:
            raw = await self._sm.get_head_to_head(int(home_team_id), int(away_team_id))
            entries = _extract_h2h(raw)
            if entries:
                data = {"entries": entries}
                result = ResolvedData(data=data, source="sportmonks", quality=0.80)
                cache_set("sm_h2h", cache_key, {"data": data, "source": "sportmonks", "quality": 0.80}, ttl_hours=24.0)
                return result
        except Exception as exc:
            logger.warning(f"[SportmonksResolver] H2H error: {exc}")

        return ResolvedData.missing("head_to_head")


# ── Private helpers ───────────────────────────────────────────

def _find_team(teams, name: str):
    name_l = name.lower().strip()
    keywords = [w for w in name_l.split() if len(w) > 3]
    for t in teams:
        title = (t.get("title") or t.get("name") or "").lower()
        if title == name_l or any(kw in title for kw in keywords):
            return t
    return None


def _extract_sportmonks_odds(raw) -> Optional[dict]:
    data = raw.get("data", []) if isinstance(raw, dict) else (raw if isinstance(raw, list) else [])
    for item in data:
        if not isinstance(item, dict):
            continue
        odds = item.get("odds") or item
        home = float(odds.get("home") or odds.get("dp3") or 0)
        draw = float(odds.get("draw") or odds.get("dp1") or 0)
        away = float(odds.get("away") or odds.get("dp2") or 0)
        if home > 1.0 and draw > 1.0 and away > 1.0:
            return {"home_win": home, "draw": draw, "away_win": away}
    return None


def _extract_lineups(raw, home_team_id: str, away_team_id: str) -> Optional[dict]:
    if not raw or not isinstance(raw, dict):
        return None
    fixture = raw.get("data", {}) if isinstance(raw.get("data"), dict) else {}
    lineups = fixture.get("lineups", [])
    if not lineups:
        return None

    result = {"home_formation": None, "away_formation": None,
              "home_confirmed": False, "away_confirmed": False}
    for lu in lineups:
        tid = str(lu.get("team_id", ""))
        if tid == str(home_team_id):
            result["home_formation"] = lu.get("formation")
            result["home_confirmed"] = bool(lu.get("confirmed", False))
        elif tid == str(away_team_id):
            result["away_formation"] = lu.get("formation")
            result["away_confirmed"] = bool(lu.get("confirmed", False))
    return result


def _extract_odds_movement(raw) -> Optional[dict]:
    data = raw.get("data", []) if isinstance(raw, dict) else []
    if not data:
        return None
    # Expect a list of odds history entries; take first/last for open/current
    home_vals = [float(e.get("value", 0) or e.get("dp3", 0)) for e in data if "Home" in str(e.get("type", {}).get("name", ""))]
    draw_vals = [float(e.get("value", 0) or e.get("dp1", 0)) for e in data if "Draw" in str(e.get("type", {}).get("name", ""))]
    away_vals = [float(e.get("value", 0) or e.get("dp2", 0)) for e in data if "Away" in str(e.get("type", {}).get("name", ""))]
    if not home_vals or not draw_vals or not away_vals:
        return None
    return {
        "home_open": home_vals[0], "home_current": home_vals[-1],
        "draw_open": draw_vals[0], "draw_current": draw_vals[-1],
        "away_open": away_vals[0], "away_current": away_vals[-1],
        "movement_hours": 48,
    }


def _extract_h2h(raw) -> list:
    data = raw.get("data", []) if isinstance(raw, dict) else []
    entries = []
    for match in data[:5]:  # last 5 meetings
        if not isinstance(match, dict):
            continue
        date = match.get("starting_at", "")[:10]
        participants = match.get("participants", [])
        home_team = next((p["name"] for p in participants if p.get("meta", {}).get("location") == "home"), "")
        away_team = next((p["name"] for p in participants if p.get("meta", {}).get("location") == "away"), "")
        scores = match.get("scores", [])
        home_goals = sum(s["score"]["goals"] for s in scores if isinstance(s.get("score"), dict) and s["score"].get("participant") == "home")
        away_goals = sum(s["score"]["goals"] for s in scores if isinstance(s.get("score"), dict) and s["score"].get("participant") == "away")
        if home_team and away_team:
            entries.append({"date": date, "home_team": home_team, "away_team": away_team,
                            "home_goals": home_goals, "away_goals": away_goals})
    return entries
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
python -m pytest tests/data_strategy/test_sportmonks_resolver.py -v
```

- [ ] **Step 5: Commit**

```bash
git add data_strategy/resolvers/sportmonks_resolver.py tests/data_strategy/test_sportmonks_resolver.py
git commit -m "feat(p1): implement SportmonksResolver with lineups/odds_movement/H2H"
```

---

### Task 8: Refactor DataFusion to use provider-scoped resolvers

**Files:**
- Modify: `data_strategy/fusion.py`
- Create: `tests/data_strategy/test_fusion.py`

- [ ] **Step 1: Write tests for provider-scoped DataFusion**

```python
# tests/data_strategy/test_fusion.py
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch
from data_strategy.fusion import DataFusion
from data_strategy.resolver import ResolvedData


def _make_ok(data, source="footystats", quality=0.85):
    return ResolvedData(data=data, source=source, quality=quality)

def _make_missing(name):
    return ResolvedData.missing(name)


@pytest.fixture
def mock_fs_resolver():
    r = MagicMock()
    r.resolve_xg = AsyncMock(return_value=_make_ok({
        "home_xg_for": 1.8, "home_xg_against": 1.0,
        "away_xg_for": 1.2, "away_xg_against": 1.4,
    }))
    r.resolve_form = AsyncMock(return_value=_make_ok({"home": {"avg_scored_5": 1.8}, "away": {"avg_scored_5": 1.2}}))
    r.resolve_standings = AsyncMock(return_value=_make_ok({"raw": []}))
    r.resolve_odds = AsyncMock(return_value=_make_ok({"home_win": 1.85, "draw": 3.50, "away_win": 4.20}))
    r.resolve_lineups = AsyncMock(return_value=_make_missing("lineups"))
    r.resolve_odds_movement = AsyncMock(return_value=_make_missing("odds_movement"))
    r.resolve_head_to_head = AsyncMock(return_value=_make_missing("head_to_head"))
    return r


@pytest.mark.asyncio
async def test_footystats_provider_sets_data_provider_field(mock_fs_resolver):
    with patch("data_strategy.fusion.FootyStatsResolver", return_value=mock_fs_resolver):
        fusion = DataFusion(
            data_provider="footystats",
            footystats=MagicMock(),
            understat=MagicMock(),
        )
        ctx = await fusion.build(
            fixture_id="8255851",
            match_id="8255851",
            home_team="Arsenal", home_team_id="86",
            away_team="Chelsea", away_team_id="83",
            season_id="1980",
            league="Premier League",
            match_date="2026-04-12",
        )
    assert ctx.data_provider == "footystats"
    assert "lineups" in ctx.data_gaps
    assert "form" not in ctx.data_gaps


@pytest.mark.asyncio
async def test_sportmonks_provider_form_in_gaps():
    sm_resolver = MagicMock()
    sm_resolver.resolve_xg = AsyncMock(return_value=_make_ok({"home_xg_for": 1.8, "home_xg_against": 1.0, "away_xg_for": 1.2, "away_xg_against": 1.4}))
    sm_resolver.resolve_form = AsyncMock(return_value=_make_missing("form"))
    sm_resolver.resolve_standings = AsyncMock(return_value=_make_ok({"raw": []}))
    sm_resolver.resolve_odds = AsyncMock(return_value=_make_ok({"home_win": 1.90, "draw": 3.40, "away_win": 4.00}))
    sm_resolver.resolve_lineups = AsyncMock(return_value=_make_ok({"home_formation": "4-3-3", "away_formation": "4-4-2", "home_confirmed": True, "away_confirmed": False}))
    sm_resolver.resolve_odds_movement = AsyncMock(return_value=_make_ok({"home_open": 2.10, "home_current": 1.90, "draw_open": 3.40, "draw_current": 3.40, "away_open": 3.80, "away_current": 4.00, "movement_hours": 48}))
    sm_resolver.resolve_head_to_head = AsyncMock(return_value=_make_missing("head_to_head"))

    with patch("data_strategy.fusion.SportmonksResolver", return_value=sm_resolver):
        fusion = DataFusion(
            data_provider="sportmonks",
            footystats=MagicMock(),
            understat=MagicMock(),
            sportmonks=MagicMock(),
        )
        ctx = await fusion.build(
            fixture_id="19374628",
            match_id="19374628",
            home_team="Arsenal", home_team_id="1",
            away_team="Chelsea", away_team_id="2",
            season_id="23614",
            league="Premier League",
            match_date="2026-04-12",
        )
    assert ctx.data_provider == "sportmonks"
    assert "form" in ctx.data_gaps
    assert ctx.lineups is not None
    assert ctx.lineups.home_formation == "4-3-3"
    assert ctx.odds_movement is not None
```

- [ ] **Step 2: Run — expect failures**

```bash
python -m pytest tests/data_strategy/test_fusion.py -v 2>&1 | head -15
```

- [ ] **Step 3: Rewrite DataFusion.\_\_init\_\_ and build() in data_strategy/fusion.py**

Replace the `__init__` and `build` methods:

```python
# data_strategy/fusion.py — updated sections

from data_strategy.resolvers.footystats_resolver import FootyStatsResolver
from data_strategy.resolvers.sportmonks_resolver import SportmonksResolver
from data_strategy.models import (
    MatchContext, TeamFormWindow, StandingsEntry, OddsSnapshot, XGStats,
    MatchLineups, OddsMovement, H2HEntry,
)


class DataFusion:

    def __init__(
        self,
        data_provider: str,          # "sportmonks" | "footystats"
        footystats,
        understat,
        sportmonks=None,
    ) -> None:
        self._data_provider = data_provider
        if data_provider == "sportmonks":
            if sportmonks is None:
                raise ValueError("SportmonksProvider required when data_provider='sportmonks'")
            self._resolver = SportmonksResolver(sportmonks=sportmonks, understat=understat)
        else:
            self._resolver = FootyStatsResolver(footystats=footystats, understat=understat)

    async def build(
        self,
        fixture_id: str,
        match_id: str,
        home_team: str,
        home_team_id: str,
        away_team: str,
        away_team_id: str,
        season_id: str,
        league: str,
        match_date: Optional[str] = None,
        season: Optional[str] = None,
    ) -> MatchContext:
        resolved_season = season or _infer_season(match_date)

        xg_task = self._resolver.resolve_xg(
            home_team=home_team, away_team=away_team, league=league, season=resolved_season,
            home_team_id=home_team_id, away_team_id=away_team_id,
        )
        form_task = self._resolver.resolve_form(home_team_id=home_team_id, away_team_id=away_team_id)
        standings_task = self._resolver.resolve_standings(season_id=season_id)
        odds_task = self._resolver.resolve_odds(match_id=match_id)
        lineups_task = self._resolver.resolve_lineups(fixture_id=fixture_id, home_team_id=home_team_id, away_team_id=away_team_id)
        odds_mv_task = self._resolver.resolve_odds_movement(fixture_id=fixture_id)
        h2h_task = self._resolver.resolve_head_to_head(home_team_id=home_team_id, away_team_id=away_team_id)

        (xg_res, form_res, standings_res, odds_res,
         lineups_res, odds_mv_res, h2h_res) = await asyncio.gather(
            xg_task, form_task, standings_task, odds_task,
            lineups_task, odds_mv_task, h2h_task,
            return_exceptions=True,
        )

        xg_res = _safe_result(xg_res, "xg")
        form_res = _safe_result(form_res, "form")
        standings_res = _safe_result(standings_res, "standings")
        odds_res = _safe_result(odds_res, "odds")
        lineups_res = _safe_result(lineups_res, "lineups")
        odds_mv_res = _safe_result(odds_mv_res, "odds_movement")
        h2h_res = _safe_result(h2h_res, "head_to_head")

        xg = self._map_xg(xg_res, home_team, away_team, league)
        home_form_5, home_form_10, away_form_5, away_form_10 = self._map_form(form_res)
        home_standing, away_standing, total_teams = self._map_standings(standings_res, home_team, away_team)
        odds = self._map_odds(odds_res)
        lineups = self._map_lineups(lineups_res)
        odds_movement = self._map_odds_movement(odds_mv_res)
        head_to_head = self._map_h2h(h2h_res)

        data_gaps: list[str] = []
        if xg is None: data_gaps.append("xg")
        if home_form_5 is None and home_form_10 is None: data_gaps.append("form")
        if home_standing is None or away_standing is None: data_gaps.append("standings")
        if odds is None: data_gaps.append("odds")
        if lineups is None: data_gaps.append("lineups")
        if odds_movement is None: data_gaps.append("odds_movement")
        if head_to_head is None: data_gaps.append("head_to_head")
        data_gaps.append("injuries")  # always missing in v1

        xg_quality = xg_res.quality if xg_res.ok else 0.0
        form_quality = form_res.quality if form_res.ok else 0.0
        standings_quality = standings_res.quality if standings_res.ok else 0.0
        odds_quality = odds_res.quality if odds_res.ok else 0.0
        overall_quality = compute_overall_quality(xg_quality, form_quality, standings_quality, odds_quality)

        sources = {
            "xg": xg_res.source, "form": form_res.source,
            "standings": standings_res.source, "odds": odds_res.source,
        }

        return MatchContext(
            data_provider=self._data_provider,
            match_id=match_id,
            league=league,
            home_team=home_team, home_team_id=home_team_id,
            away_team=away_team, away_team_id=away_team_id,
            season_id=season_id, match_date=match_date,
            xg=xg,
            home_form_5=home_form_5, home_form_10=home_form_10,
            away_form_5=away_form_5, away_form_10=away_form_10,
            form_source=form_res.source, form_quality=form_quality,
            home_standing=home_standing, away_standing=away_standing,
            total_teams=total_teams,
            standings_source=standings_res.source, standings_quality=standings_quality,
            odds=odds,
            lineups=lineups,
            odds_movement=odds_movement,
            head_to_head=head_to_head,
            data_gaps=tuple(data_gaps),
            overall_quality=overall_quality,
            sources=sources,
            resolved_at=time.time(),
        )

    # Add new mapping methods alongside existing ones:

    def _map_lineups(self, res: ResolvedData) -> Optional[MatchLineups]:
        if not res.ok or not res.data:
            return None
        d = res.data
        return MatchLineups(
            home_formation=d.get("home_formation"),
            away_formation=d.get("away_formation"),
            home_confirmed=bool(d.get("home_confirmed", False)),
            away_confirmed=bool(d.get("away_confirmed", False)),
        )

    def _map_odds_movement(self, res: ResolvedData) -> Optional[OddsMovement]:
        if not res.ok or not res.data:
            return None
        d = res.data
        try:
            return OddsMovement(
                home_open=float(d["home_open"]), home_current=float(d["home_current"]),
                draw_open=float(d["draw_open"]), draw_current=float(d["draw_current"]),
                away_open=float(d["away_open"]), away_current=float(d["away_current"]),
                movement_hours=int(d.get("movement_hours", 48)),
            )
        except (KeyError, TypeError, ValueError):
            return None

    def _map_h2h(self, res: ResolvedData) -> Optional[tuple]:
        if not res.ok or not res.data:
            return None
        entries = res.data.get("entries", [])
        return tuple(
            H2HEntry(
                date=e["date"], home_team=e["home_team"], away_team=e["away_team"],
                home_goals=e["home_goals"], away_goals=e["away_goals"],
            )
            for e in entries if isinstance(e, dict)
        ) or None
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
python -m pytest tests/data_strategy/ -v
```

- [ ] **Step 5: Commit**

```bash
git add data_strategy/fusion.py tests/data_strategy/test_fusion.py
git commit -m "feat(p1): refactor DataFusion to route by data_provider (FootyStatsResolver/SportmonksResolver)"
```

---

### Task 9: Add goalcast_get_todays_matches + update goalcast_resolve_match

**Files:**
- Modify: `mcp_server/server.py`

- [ ] **Step 1: Add `goalcast_get_todays_matches` tool after the existing goalcast tools**

```python
# mcp_server/server.py — add after line ~1095

@mcp.tool()
async def goalcast_get_todays_matches(
    data_provider: str,
    date: Optional[str] = None,
    league_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    通过指定 data_provider 获取今日/指定日期的比赛列表。
    返回标准化 MatchSummary 列表，字段与 provider 无关。

    Args:
        data_provider: "sportmonks" | "footystats"
        date:          YYYY-MM-DD，默认今天
        league_filter: 联赛名过滤（子字符串匹配，不区分大小写）

    Returns:
        [{ home_team, away_team, competition, kickoff_time,
           match_id, home_team_id, away_team_id, season_id }, ...]
    """
    import datetime
    target_date = date or datetime.date.today().isoformat()

    try:
        if data_provider == "sportmonks":
            raw = await handle_api_call(
                "Sportmonks",
                get_sportmonks().get_fixtures_by_date(
                    target_date,
                    include="participants;scores;league;season",
                ),
            )
            return _normalize_sportmonks_fixtures(raw, league_filter)

        elif data_provider == "footystats":
            raw = await handle_api_call(
                "FootyStats",
                get_footystats().get_todays_matches(target_date, timezone=None),
            )
            return _normalize_footystats_fixtures(raw, league_filter)

        else:
            return [{"error": f"Unknown data_provider: {data_provider}"}]

    except Exception as exc:
        logger.error(f"[goalcast_get_todays_matches] {exc}")
        return [{"error": str(exc)}]


def _normalize_sportmonks_fixtures(raw, league_filter: Optional[str]) -> List[Dict]:
    data = raw.get("data", []) if isinstance(raw, dict) else []
    result = []
    for fix in data:
        if not isinstance(fix, dict):
            continue
        league_name = fix.get("league", {}).get("name", "") if isinstance(fix.get("league"), dict) else ""
        if league_filter and league_filter.lower() not in league_name.lower():
            continue
        participants = fix.get("participants", [])
        home = next((p for p in participants if p.get("meta", {}).get("location") == "home"), {})
        away = next((p for p in participants if p.get("meta", {}).get("location") == "away"), {})
        result.append({
            "home_team": home.get("name", ""),
            "away_team": away.get("name", ""),
            "competition": league_name,
            "kickoff_time": fix.get("starting_at", ""),
            "match_id": str(fix.get("id", "")),
            "home_team_id": str(home.get("id", "")),
            "away_team_id": str(away.get("id", "")),
            "season_id": str(fix.get("season_id", "")),
        })
    return result


def _normalize_footystats_fixtures(raw, league_filter: Optional[str]) -> List[Dict]:
    matches = raw.get("data", []) if isinstance(raw, dict) else []
    result = []
    for m in matches:
        if not isinstance(m, dict):
            continue
        comp_name = m.get("competition_name", "")
        if league_filter and league_filter.lower() not in comp_name.lower():
            continue
        result.append({
            "home_team": m.get("home_name", ""),
            "away_team": m.get("away_name", ""),
            "competition": comp_name,
            "kickoff_time": m.get("date_unix", ""),
            "match_id": str(m.get("id", "")),
            "home_team_id": str(m.get("homeID", "")),
            "away_team_id": str(m.get("awayID", "")),
            "season_id": str(m.get("competition_id", "")),
        })
    return result
```

- [ ] **Step 2: Update `goalcast_resolve_match` to add `data_provider` + `fixture_id` params**

```python
# mcp_server/server.py — update goalcast_resolve_match signature and body

@mcp.tool()
async def goalcast_resolve_match(
    match_id: str,
    home_team: str,
    home_team_id: str,
    away_team: str,
    away_team_id: str,
    season_id: str,
    league: str,
    data_provider: str = "footystats",   # NEW: required (default for backcompat)
    fixture_id: Optional[str] = None,     # NEW: same as match_id for Sportmonks
    match_date: Optional[str] = None,
    season: Optional[str] = None,
) -> Dict[str, Any]:
    """
    数据策略层核心工具：并行采集并融合单场比赛所需的全部数据。

    Args:
        data_provider: "sportmonks" | "footystats"（必填，影响 resolver 选择）
        fixture_id:    Sportmonks fixture ID（Sportmonks provider 时必填，否则同 match_id）
        match_id:      FootyStats 比赛 ID（footystats provider）/ Sportmonks fixture ID
        ...（其余参数同原版）

    Returns:
        MatchContext 序列化字典，新增字段：
        - data_provider: 本次解析使用的 provider
        - lineups:       阵容（仅 sportmonks provider 可能有值）
        - odds_movement: 赔率变动（仅 sportmonks provider 可能有值）
        - head_to_head:  历史交锋（仅 sportmonks provider 可能有值）
    """
    try:
        effective_fixture_id = fixture_id or match_id
        sportmonks = get_sportmonks() if data_provider == "sportmonks" else None

        fusion = DataFusion(
            data_provider=data_provider,
            footystats=get_footystats(),
            understat=get_understat(),
            sportmonks=sportmonks,
        )
        ctx = await fusion.build(
            fixture_id=str(effective_fixture_id),
            match_id=str(match_id),
            home_team=home_team,
            home_team_id=str(home_team_id),
            away_team=away_team,
            away_team_id=str(away_team_id),
            season_id=str(season_id),
            league=league,
            match_date=match_date,
            season=season,
        )
        return ctx.to_dict()
    except Exception as exc:
        logger.error(f"[goalcast_resolve_match] {exc}")
        return {"error": "RESOLVE_ERROR", "message": str(exc),
                "match_id": match_id, "home_team": home_team, "away_team": away_team}
```

- [ ] **Step 3: Verify server.py parses without errors**

```bash
python -c "import sys; sys.path.insert(0, 'mcp_server'); import server; print('server.py OK')"
```

- [ ] **Step 4: Commit**

```bash
git add mcp_server/server.py
git commit -m "feat(p1): add goalcast_get_todays_matches; update goalcast_resolve_match with data_provider param"
```

---

## Phase P2: Skill Rewrites

### Task 10: Update goalcast-analyzer-v25 and v30 for provider-agnostic Step 1/2 + silent mode

**Files:**
- Modify: `skills/goalcast-analyzer-v25/SKILL.md`
- Modify: `skills/goalcast-analyzer-v30/SKILL.md`

- [ ] **Step 1: Update Step 1 and Step 2 in goalcast-analyzer-v30/SKILL.md**

Replace the Step 1 block with:

```markdown
### Step 1：定位比赛

**注**：通过 `goalcast_get_todays_matches` 获取比赛 ID，无需直接调用 provider 工具。

调用 `goalcast_get_todays_matches`：
- 参数 `data_provider`：由调用方传入（如 "sportmonks" / "footystats"）
- 参数 `date`：用户指定日期（YYYY-MM-DD），默认今天
- 参数 `league_filter`：从用户意图提取，如 "Premier League"

按队名模糊匹配提取目标比赛，获取：
- `match_id` / `fixture_id` → provider 内部 ID
- `home_team_id` / `away_team_id`
- `competition` → 联赛名
- `season_id`

如未找到：回复"未找到符合条件的比赛"，停止。

**被 goalcast-compare 作为子 agent 调用时**：
接收参数包含 `home_team`, `away_team`, `competition`, `date`, `data_provider`, `model`, `match_type`。
此时跳过用户交互，直接以队名在 `goalcast_get_todays_matches` 结果中定位比赛。
```

Replace the Step 2 block with:

```markdown
### Step 2：数据采集（统一接口）

调用 `goalcast_resolve_match` 工具：

```
goalcast_resolve_match(
    match_id=<match_id>,
    fixture_id=<fixture_id>,      ← Sportmonks provider 时传入
    home_team=<home_team>,
    home_team_id=<home_team_id>,
    away_team=<away_team>,
    away_team_id=<away_team_id>,
    season_id=<season_id>,
    league=<competition>,
    data_provider=<data_provider>,  ← 必填，来自 Step 1 参数
    match_date=<date>
)
```

**该工具自动处理**：数据源选择、resolver 路由、缓存、质量评分。

**Sportmonks provider 新增字段**（v3.0 分析层可使用）：
- `ctx.lineups` → L6 贝叶斯调整启用条件
- `ctx.odds_movement` → L3 市场行为权重提升至 20%
- `ctx.head_to_head` → 交锋记录参考

**子 agent 静默规则**：收到 `match_type` 参数时，零层检查直接采用该值，不询问用户。
```

- [ ] **Step 2: Apply same changes to goalcast-analyzer-v25/SKILL.md** (same pattern for Step 1/2)

- [ ] **Step 3: Commit**

```bash
git add skills/goalcast-analyzer-v25/SKILL.md skills/goalcast-analyzer-v30/SKILL.md
git commit -m "feat(p2): update analyzer skills to use goalcast_get_todays_matches + silent sub-agent mode"
```

---

### Task 11: Rewrite goalcast-compare/SKILL.md

**Files:**
- Modify: `skills/goalcast-compare/SKILL.md`

- [ ] **Step 1: Replace SKILL.md with the new provider×model dispatcher**

```markdown
---
name: goalcast-compare
description: Use this skill to analyze a football match with one or more (data_provider × model) combinations, or to compare results across multiple combinations. Accepts any combination of sportmonks/footystats × v2.5/v3.0.
---

# Goalcast Compare — 统一分析调度器

版本：2.0 | 职责：解析组合列表 → 并行调度子 agent → 输出对比报告

## 重要约束

**本 skill 不包含任何分析逻辑。** 分析由子 agent 完成。
本 skill 只负责：解析请求 → 批量调度 → 收集结果 → 输出报告。

## 触发条件

- 用户指定"用 sportmonks+v3.0 分析"→ 单组合，直接输出结果
- 用户指定"分别用 sportmonks+v3.0 和 footystats+v3.0 分析"→ 多组合，输出对比
- 用户未指定 provider → 默认 `sportmonks+v3.0`
- 被 `goalcast-daily` 调用时，所有参数均由调用方传入

## 执行步骤

### Step 1：解析分析请求

从用户输入或调用方参数中提取：

```
matches: [{home_team, away_team, competition, date}, ...]   ← 比赛列表
combinations: [(data_provider, model), ...]                 ← 组合列表
match_type: "A"  ← 默认 A，可由用户指定
```

**默认组合**：未指定时使用 `[("sportmonks", "v3.0")]`

**合法的 data_provider 值**：`"sportmonks"` | `"footystats"`
**合法的 model 值**：`"v2.5"` | `"v3.0"`

### Step 2：批量规模检查

```
总子 agent 数 = len(matches) × len(combinations)
```

超过 10 个时：展示规模并等待用户确认后再继续。
10 个以内：直接执行，不打扰用户。

### Step 3：并行启动所有子 agent

**每个子 agent 收到以下参数（纯文本，不含 provider ID）：**

```
home_team:     "Arsenal"
away_team:     "Chelsea"
competition:   "Premier League"
date:          "2026-04-12"
data_provider: "sportmonks"          ← 每个 agent 独立
model:         "v3.0"                ← 每个 agent 独立
match_type:    "A"
```

**子 agent 映射**：
- model="v2.5" → 使用 goalcast-analyzer-v25 skill
- model="v3.0" → 使用 goalcast-analyzer-v30 skill

**并行启动所有子 agent，等待全部完成后继续。**

子 agent 内部流程（固定，不与用户交互）：
1. `goalcast_get_todays_matches(data_provider=X, date, league_filter=competition)` → 定位比赛
2. `goalcast_resolve_match(..., data_provider=X)` → 获取 MatchContext（极大概率缓存命中）
3. 执行指定模型分析层
4. 返回 `AnalysisResult` JSON

### Step 4：收集结果并输出

**单组合单场**：直接输出完整分析结果，无需对比表。

**多组合**（任意场数）：

```markdown
## [主队] vs [客队] — 多方案分析对比
日期：YYYY-MM-DD | 联赛：[联赛名] | 比赛类型：A

### 结论对比

| 维度 | sportmonks+v3.0 | footystats+v3.0 | 差异 |
|------|----------------|----------------|------|
| 数据质量 | 0.82 | 0.74 | — |
| 已启用层 | L3完整+L6阵容 | L2近况 | — |
| 主队胜率 | 52% | 49% | ±3% |
| 平局概率 | 25% | 27% | ±2% |
| 客队胜率 | 23% | 24% | ±1% |
| 最佳投注 | 主胜 | 主胜 | ✓一致 |
| EV（风险调整后）| +0.09 | +0.06 | ±0.03 |
| 置信度 | 73 | 67 | ±6 |

### 各方案完整结果

[各方案 AnalysisResult JSON，按组合顺序排列]
```

**单组合批量**：每场一个卡片，末尾附汇总表（高 EV 比赛优先）。

**多组合批量**：每场展示对比，末尾附全场汇总（各方案置信度 ≥ 60 的推荐汇总）。

### 结果失败处理

某子 agent 失败时：
- 在报告中注明 `[组合名] 分析失败`
- 展示可用结果
- 不重试，不估算缺失数据
```

- [ ] **Step 2: Commit**

```bash
git add skills/goalcast-compare/SKILL.md
git commit -m "feat(p2): rewrite goalcast-compare as provider×model dispatcher"
```

---

## Phase P3: Batch Infrastructure

### Task 12: Create config/watchlist.yaml

**Files:**
- Create: `config/watchlist.yaml`

- [ ] **Step 1: Create watchlist config**

```yaml
# config/watchlist.yaml
# 联赛监控列表，按 provider 分别配置
# batch_runner.py 读取此文件确定每日分析范围

sportmonks:
  leagues:
    - name: "Premier League"
      country: "England"
      season_id: 23614
    - name: "La Liga"
      country: "Spain"
      season_id: 23599
    - name: "Bundesliga"
      country: "Germany"
      season_id: 23584
    - name: "Serie A"
      country: "Italy"
      season_id: 23605
    - name: "Ligue 1"
      country: "France"
      season_id: 23610

footystats:
  leagues:
    - name: "Premier League"
      country: "England"
      league_id: 2
    - name: "La Liga"
      country: "Spain"
      league_id: 3
    - name: "Bundesliga"
      country: "Germany"
      league_id: 4
    - name: "Serie A"
      country: "Italy"
      league_id: 5
    - name: "Ligue 1"
      country: "France"
      league_id: 6
```

- [ ] **Step 2: Commit**

```bash
git add config/watchlist.yaml
git commit -m "feat(p3): add config/watchlist.yaml for batch runner league watchlist"
```

---

### Task 13: Add goalcast_prefetch_today MCP tool

**Files:**
- Modify: `mcp_server/server.py`

- [ ] **Step 1: Add the prefetch tool to server.py**

```python
# mcp_server/server.py — add after goalcast_get_todays_matches

@mcp.tool()
async def goalcast_prefetch_today(
    data_provider: str,
    leagues: Optional[List[str]] = None,
    date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    预热今日/指定日期比赛的数据缓存。

    适合在批量分析前调用：Python 并发拉取所有比赛的原始数据，
    写入 data/cache/，后续 goalcast_resolve_match 调用均为缓存命中。

    Args:
        data_provider: "sportmonks" | "footystats"
        leagues:       联赛名列表。为 None 时读取 config/watchlist.yaml。
        date:          YYYY-MM-DD，默认今天

    Returns:
        { matches_found, matches_cached, provider, date, match_list }
    """
    import datetime
    import yaml

    target_date = date or datetime.date.today().isoformat()

    # 读取 watchlist（未指定 leagues 时使用）
    if leagues is None:
        watchlist_path = Path(__file__).resolve().parent.parent / "config" / "watchlist.yaml"
        if watchlist_path.exists():
            with open(watchlist_path) as f:
                wl = yaml.safe_load(f)
            provider_cfg = wl.get(data_provider, {})
            leagues = [lg["name"] for lg in provider_cfg.get("leagues", [])]
        else:
            leagues = []

    all_matches = []
    for league in (leagues or [None]):
        try:
            matches = await goalcast_get_todays_matches(
                data_provider=data_provider,
                date=target_date,
                league_filter=league,
            )
            all_matches.extend(m for m in matches if "error" not in m)
        except Exception as exc:
            logger.warning(f"[prefetch] Failed to list {league}: {exc}")

    # 并发预热每场比赛
    cached_count = 0
    async def _prefetch_one(match: Dict) -> bool:
        try:
            await goalcast_resolve_match(
                match_id=match["match_id"],
                fixture_id=match.get("fixture_id") or match["match_id"],
                home_team=match["home_team"],
                home_team_id=match["home_team_id"],
                away_team=match["away_team"],
                away_team_id=match["away_team_id"],
                season_id=match["season_id"],
                league=match["competition"],
                data_provider=data_provider,
                match_date=target_date,
            )
            return True
        except Exception as exc:
            logger.warning(f"[prefetch] Failed to resolve {match.get('home_team')} vs {match.get('away_team')}: {exc}")
            return False

    results = await asyncio.gather(*(_prefetch_one(m) for m in all_matches), return_exceptions=True)
    cached_count = sum(1 for r in results if r is True)

    return {
        "matches_found": len(all_matches),
        "matches_cached": cached_count,
        "provider": data_provider,
        "date": target_date,
        "leagues": leagues or [],
        "match_list": [
            {"home_team": m["home_team"], "away_team": m["away_team"],
             "competition": m["competition"], "kickoff_time": m.get("kickoff_time", "")}
            for m in all_matches
        ],
    }
```

- [ ] **Step 2: Verify server.py imports yaml (add to requirements if needed)**

```bash
python -c "import yaml; print('yaml OK')"
# If fails: pip install pyyaml
```

- [ ] **Step 3: Commit**

```bash
git add mcp_server/server.py
git commit -m "feat(p3): add goalcast_prefetch_today MCP tool for batch cache warming"
```

---

### Task 14: Create scripts/batch_runner.py

**Files:**
- Create: `scripts/batch_runner.py`

- [ ] **Step 1: Create the batch runner script**

```python
#!/usr/bin/env python3
"""
batch_runner.py — Goalcast 数据预热批处理脚本

无 LLM 参与，仅拉取并缓存比赛数据。
适用于定时任务（cron）和大批量预热场景。

用法：
  python scripts/batch_runner.py --provider sportmonks
  python scripts/batch_runner.py --provider footystats --date 2026-04-12
  python scripts/batch_runner.py --provider sportmonks --league "Premier League"
"""
import sys
import asyncio
import argparse
import datetime
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "mcp_server"))

from utils.logger import logger
from config.settings import settings


async def _load_watchlist(provider: str, league_filter: str | None) -> list[str]:
    """Load league list from config/watchlist.yaml."""
    try:
        import yaml
        wl_path = Path(__file__).resolve().parent.parent / "config" / "watchlist.yaml"
        if not wl_path.exists():
            logger.warning("config/watchlist.yaml not found — fetching all leagues")
            return [None]
        with open(wl_path) as f:
            wl = yaml.safe_load(f)
        leagues = [lg["name"] for lg in wl.get(provider, {}).get("leagues", [])]
        if league_filter:
            leagues = [l for l in leagues if league_filter.lower() in l.lower()]
        return leagues or [None]
    except Exception as exc:
        logger.error(f"Failed to load watchlist: {exc}")
        return [None]


async def run_prefetch(provider: str, date: str, league_filter: str | None) -> dict:
    from provider.footystats.client import FootyStatsProvider
    from provider.sportmonks.client import SportmonksProvider
    from provider.understat.client import UnderstatProvider
    from data_strategy.fusion import DataFusion

    fs = FootyStatsProvider()
    us = UnderstatProvider(use_library=True)
    sm = SportmonksProvider() if provider == "sportmonks" else None

    leagues = await _load_watchlist(provider, league_filter)
    logger.info(f"Prefetching {provider} data for {date} | leagues: {leagues}")

    # Step 1: List all matches
    all_matches: list[dict] = []
    for league in leagues:
        if provider == "sportmonks" and sm:
            raw = await sm.get_fixtures_by_date(date, include="participants;scores;league;season")
        elif provider == "footystats":
            raw = await fs.get_todays_matches(date, timezone=None)
        else:
            continue

        data = raw.get("data", []) if isinstance(raw, dict) else []
        for item in data:
            if not isinstance(item, dict):
                continue
            if provider == "sportmonks":
                lg_name = item.get("league", {}).get("name", "") if isinstance(item.get("league"), dict) else ""
                if league and league.lower() not in lg_name.lower():
                    continue
                participants = item.get("participants", [])
                home = next((p for p in participants if p.get("meta", {}).get("location") == "home"), {})
                away = next((p for p in participants if p.get("meta", {}).get("location") == "away"), {})
                all_matches.append({
                    "home_team": home.get("name", ""),
                    "away_team": away.get("name", ""),
                    "competition": lg_name,
                    "match_id": str(item.get("id", "")),
                    "home_team_id": str(home.get("id", "")),
                    "away_team_id": str(away.get("id", "")),
                    "season_id": str(item.get("season_id", "")),
                })
            else:  # footystats
                comp_name = item.get("competition_name", "")
                if league and league.lower() not in comp_name.lower():
                    continue
                all_matches.append({
                    "home_team": item.get("home_name", ""),
                    "away_team": item.get("away_name", ""),
                    "competition": comp_name,
                    "match_id": str(item.get("id", "")),
                    "home_team_id": str(item.get("homeID", "")),
                    "away_team_id": str(item.get("awayID", "")),
                    "season_id": str(item.get("competition_id", "")),
                })

    logger.info(f"Found {len(all_matches)} matches")

    # Step 2: Warm cache for each match
    cached = 0
    errors = 0

    async def _warm_one(match: dict) -> bool:
        try:
            fusion = DataFusion(
                data_provider=provider,
                footystats=fs,
                understat=us,
                sportmonks=sm,
            )
            await fusion.build(
                fixture_id=match["match_id"],
                match_id=match["match_id"],
                home_team=match["home_team"],
                home_team_id=match["home_team_id"],
                away_team=match["away_team"],
                away_team_id=match["away_team_id"],
                season_id=match["season_id"],
                league=match["competition"],
                match_date=date,
            )
            return True
        except Exception as exc:
            logger.warning(f"  Failed: {match.get('home_team')} vs {match.get('away_team')}: {exc}")
            return False

    results = await asyncio.gather(*(_warm_one(m) for m in all_matches), return_exceptions=True)
    cached = sum(1 for r in results if r is True)
    errors = len(results) - cached

    # Save match list for agent consumption
    output_dir = Path(__file__).resolve().parent.parent / "data" / "cache"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"today_matches_{provider}.json"
    with open(output_path, "w") as f:
        json.dump({"date": date, "provider": provider, "matches": all_matches}, f, ensure_ascii=False, indent=2)

    summary = {
        "date": date,
        "provider": provider,
        "matches_found": len(all_matches),
        "matches_cached": cached,
        "errors": errors,
        "output": str(output_path),
    }
    logger.info(f"Prefetch complete: {summary}")
    return summary


def main():
    parser = argparse.ArgumentParser(description="Goalcast batch data prefetcher")
    parser.add_argument("--provider", choices=["sportmonks", "footystats"], required=True)
    parser.add_argument("--date", default=datetime.date.today().isoformat(), help="YYYY-MM-DD")
    parser.add_argument("--league", default=None, help="League name filter")
    args = parser.parse_args()

    result = asyncio.run(run_prefetch(args.provider, args.date, args.league))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Test the script parses without error**

```bash
python scripts/batch_runner.py --help
```
Expected: Prints usage without error.

- [ ] **Step 3: Commit**

```bash
git add scripts/batch_runner.py
git commit -m "feat(p3): add scripts/batch_runner.py for headless batch data prefetch"
```

---

### Task 15: Create data storage module for analysis results

**Files:**
- Create: `data_strategy/storage.py`
- Create: `tests/data_strategy/test_storage.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/data_strategy/test_storage.py
import pytest
import tempfile
from pathlib import Path
from data_strategy.storage import AnalysisStorage

@pytest.fixture
def tmp_storage(tmp_path):
    return AnalysisStorage(db_path=tmp_path / "test.db", reports_dir=tmp_path / "reports")

def test_storage_creates_tables(tmp_storage):
    tmp_storage.init()
    # Should not raise
    tmp_storage.init()  # idempotent

def test_save_analysis_result(tmp_storage):
    tmp_storage.init()
    row_id = tmp_storage.save_analysis(
        match_date="2026-04-12",
        home_team="Arsenal",
        away_team="Chelsea",
        competition="Premier League",
        data_provider="sportmonks",
        model_version="v3.0",
        home_win_prob=0.52,
        draw_prob=0.25,
        away_win_prob=0.23,
        confidence=73,
        best_bet="home_win",
        ev_adjusted=0.09,
        result_json={"decision": {"bet_rating": "推荐"}},
    )
    assert row_id is not None

def test_save_creates_json_report(tmp_storage):
    tmp_storage.init()
    tmp_storage.save_analysis(
        match_date="2026-04-12",
        home_team="Arsenal",
        away_team="Chelsea",
        competition="Premier League",
        data_provider="footystats",
        model_version="v3.0",
        home_win_prob=0.49,
        draw_prob=0.27,
        away_win_prob=0.24,
        confidence=67,
        best_bet="home_win",
        ev_adjusted=0.06,
        result_json={"method": "v3.0"},
    )
    report_path = tmp_storage.reports_dir / "2026-04-12" / "Arsenal_vs_Chelsea_footystats_v30.json"
    assert report_path.exists()
```

- [ ] **Step 2: Run — expect ImportError**

```bash
python -m pytest tests/data_strategy/test_storage.py -v 2>&1 | head -5
```

- [ ] **Step 3: Implement data_strategy/storage.py**

```python
# data_strategy/storage.py
"""
分析结果存储层

持久化分析结果到：
1. data/reports/YYYY-MM-DD/Match_Name_provider_model.json（供其他 agent 读取）
2. data/analysis.db SQLite（供回测和历史查询）
"""
import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Optional
from config.settings import BASE_DIR


class AnalysisStorage:

    def __init__(
        self,
        db_path: Optional[Path] = None,
        reports_dir: Optional[Path] = None,
    ) -> None:
        self.db_path = db_path or (BASE_DIR / "data" / "analysis.db")
        self.reports_dir = reports_dir or (BASE_DIR / "data" / "reports")
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def init(self) -> None:
        """Create tables if not exist (idempotent)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    match_date TEXT NOT NULL,
                    home_team TEXT NOT NULL,
                    away_team TEXT NOT NULL,
                    competition TEXT NOT NULL,
                    data_provider TEXT NOT NULL,
                    model_version TEXT NOT NULL,
                    home_win_prob REAL,
                    draw_prob REAL,
                    away_win_prob REAL,
                    confidence INTEGER,
                    best_bet TEXT,
                    ev_adjusted REAL,
                    result_json TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS match_results (
                    match_date TEXT NOT NULL,
                    home_team TEXT NOT NULL,
                    away_team TEXT NOT NULL,
                    home_goals INTEGER,
                    away_goals INTEGER,
                    PRIMARY KEY (match_date, home_team, away_team)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_analyses_date
                ON analyses (match_date, home_team, away_team)
            """)
            conn.commit()

    def save_analysis(
        self,
        match_date: str,
        home_team: str,
        away_team: str,
        competition: str,
        data_provider: str,
        model_version: str,
        home_win_prob: float,
        draw_prob: float,
        away_win_prob: float,
        confidence: int,
        best_bet: str,
        ev_adjusted: float,
        result_json: Any,
    ) -> int:
        """Save analysis to SQLite and write JSON report. Returns row id."""
        created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        result_str = json.dumps(result_json, ensure_ascii=False)

        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                """INSERT INTO analyses
                   (match_date, home_team, away_team, competition,
                    data_provider, model_version, home_win_prob, draw_prob, away_win_prob,
                    confidence, best_bet, ev_adjusted, result_json, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (match_date, home_team, away_team, competition,
                 data_provider, model_version, home_win_prob, draw_prob, away_win_prob,
                 confidence, best_bet, ev_adjusted, result_str, created_at),
            )
            conn.commit()
            row_id = cur.lastrowid

        # Write JSON report
        date_dir = self.reports_dir / match_date
        date_dir.mkdir(parents=True, exist_ok=True)
        model_slug = model_version.replace(".", "")
        fname = f"{home_team}_vs_{away_team}_{data_provider}_{model_slug}.json"
        report_path = date_dir / fname
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(result_json, f, ensure_ascii=False, indent=2)

        return row_id
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
python -m pytest tests/data_strategy/test_storage.py -v
```

- [ ] **Step 5: Commit**

```bash
git add data_strategy/storage.py tests/data_strategy/test_storage.py
git commit -m "feat(p3): add AnalysisStorage for SQLite + JSON report persistence"
```

---

### Task 16: Create goalcast-daily skill

**Files:**
- Create: `skills/goalcast-daily/SKILL.md`

- [ ] **Step 1: Create the skill file**

```markdown
---
name: goalcast-daily
description: Use this skill when the user wants to run today's daily analysis workflow, get a list of today's matches for a specific provider, or run batch analysis across all watchlist leagues.
---

# Goalcast Daily — 每日工作流入口

版本：1.0 | 职责：解析今日赛程 → 数据预热（可选）→ 转交 goalcast-compare 分析

## 触发条件

- "分析今天的比赛"
- "用 sportmonks+v3.0 跑今天英超的分析"
- "今天有哪些比赛？"
- 定时任务调用（批量模式）

## 执行步骤

### Step 0（批量时推荐）：数据预热

当分析场数 > 3 或用户明确要求批量时，先预热数据：

```
goalcast_prefetch_today(
    data_provider=<provider>,
    leagues=<watchlist 中的联赛列表 或 用户指定>,
    date=今天
)
```

输出：`已预热 N 场比赛数据，缓存写入 data/cache/`

**单场分析跳过此步骤**，直接从 Step 1 开始。

### Step 1：解析分析组合

从用户输入中提取：

| 参数 | 提取方式 | 默认值 |
|------|---------|-------|
| data_provider | "sportmonks"/"footystats" in 输入 | "sportmonks" |
| model | "v2.5"/"v3.0" in 输入 | "v3.0" |
| league_filter | 联赛名 in 输入 | None（全部） |
| date | YYYY-MM-DD in 输入 | 今天 |

如提取不到 data_provider，询问（单次，不重复）：
> "请问使用哪个数据源？A) sportmonks  B) footystats"

### Step 2：获取今日赛程

```
goalcast_get_todays_matches(
    data_provider=<data_provider>,
    date=<date>,
    league_filter=<league_filter>
)
```

展示赛程（时间升序）：
```
今日比赛（Premier League | sportmonks）

 1. Arsenal vs Chelsea           20:00
 2. Liverpool vs Man City        17:30
 3. Tottenham vs Newcastle       15:00
 ...
```

无比赛时：回复"今日 [联赛名] 暂无比赛安排"，停止。

### Step 3：用户选场（交互模式）或自动批量（无人值守模式）

**交互模式**（用户在线）：
- "分析第 2 场" → 单场
- "分析所有比赛" → 全部
- "分析前 3 场" → 指定数量

**无人值守模式**（定时任务调用，参数中含 `batch=true`）：
- 自动选择全部比赛
- 跳过交互，直接进入 Step 4

### Step 4：转交 goalcast-compare

调用 goalcast-compare，传入：

```
matches: [
  {home_team, away_team, competition, date},
  ...
]
combinations: [(data_provider, model)]   ← 本次组合
match_type: "A"                          ← 默认，可由用户指定
```

goalcast-compare 负责：
- 批量规模检查（>10 子 agent 时确认）
- 并行调度子 agent
- 收集结果 + 输出报告

### Step 5（可选）：保存结果

如用户要求持久化（或在 .env 中设置 `GOALCAST_PERSIST_RESULTS=true`）：
- 从各子 agent 的 AnalysisResult JSON 中提取关键字段
- 调用内部存储层写入 `data/reports/` 和 `data/analysis.db`
```

- [ ] **Step 2: Commit**

```bash
mkdir -p skills/goalcast-daily
git add skills/goalcast-daily/SKILL.md
git commit -m "feat(p3): create goalcast-daily skill for daily workflow entry point"
```

---

## Phase P4: Server Refactor (Optional, separate session)

### Task 17: Split mcp_server/server.py into tools/ submodules

> **Note:** This task is purely organizational. The MCP server continues to work before this task. Complete P0–P3 first, confirm everything works, then do this cleanup.

**Files:**
- Create: `mcp_server/tools/__init__.py`
- Create: `mcp_server/tools/footystats.py` (~300 lines)
- Create: `mcp_server/tools/understat.py` (~300 lines)
- Create: `mcp_server/tools/sportmonks.py` (~300 lines)
- Create: `mcp_server/tools/goalcast.py` (~200 lines)
- Modify: `mcp_server/server.py` (~100 lines, init + imports only)

- [ ] **Step 1: Create tools/ directory and empty files**

```bash
mkdir -p mcp_server/tools
touch mcp_server/tools/__init__.py
```

- [ ] **Step 2: Extract FootyStats tool registrations into mcp_server/tools/footystats.py**

Move all `@mcp.tool()` functions prefixed `footystats_*` from `server.py` into `footystats.py`. Keep the same function signatures. Add `from mcp.server.fastmcp import FastMCP` import at top. Function receives `mcp` instance via `register_tools(mcp)` pattern:

```python
# mcp_server/tools/footystats.py
from typing import Optional, Any
from mcp.server.fastmcp import FastMCP


def register_footystats_tools(mcp: FastMCP, get_footystats, handle_api_call) -> None:
    """Register all footystats_* MCP tools onto the given FastMCP instance."""

    @mcp.tool()
    async def footystats_get_league_list(chosen_leagues_only: bool = False, country: Optional[int] = None) -> Any:
        """Get list of available leagues from FootyStats."""
        return await handle_api_call("FootyStats", get_footystats().get_league_list(chosen_leagues_only, country))

    # ... (all other footystats_ tools, same pattern)
```

- [ ] **Step 3: Do same for understat.py, sportmonks.py, goalcast.py**

- [ ] **Step 4: Reduce server.py to ~100 lines**

```python
# mcp_server/server.py (final form)
import os
from mcp.server.fastmcp import FastMCP
from provider.footystats.client import FootyStatsProvider
from provider.sportmonks.client import SportmonksProvider
from provider.understat.client import UnderstatProvider
from utils.logger import logger

mcp = FastMCP(
    "Goalcast Data Providers",
    host=os.environ.get("FASTMCP_HOST", "127.0.0.1"),
    port=int(os.environ.get("FASTMCP_PORT", "8000")),
)

_footystats = _sportmonks = _understat = None

def get_footystats(): ...
def get_sportmonks(): ...
def get_understat(): ...

async def handle_api_call(provider_name, coro): ...

from mcp_server.tools.footystats import register_footystats_tools
from mcp_server.tools.understat import register_understat_tools
from mcp_server.tools.sportmonks import register_sportmonks_tools
from mcp_server.tools.goalcast import register_goalcast_tools

register_footystats_tools(mcp, get_footystats, handle_api_call)
register_understat_tools(mcp, get_understat, handle_api_call)
register_sportmonks_tools(mcp, get_sportmonks, handle_api_call)
register_goalcast_tools(mcp, get_footystats, get_sportmonks, get_understat)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "sse":
        mcp.run(transport="sse")
    else:
        mcp.run(transport="stdio")
```

- [ ] **Step 5: Verify MCP server starts**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast
python mcp_server/server.py --help 2>&1 | head -5
```

- [ ] **Step 6: Commit**

```bash
git add mcp_server/tools/ mcp_server/server.py
git commit -m "refactor(p4): split mcp_server/server.py into tools/ submodules"
```

---

## Final Validation

- [ ] **Run full test suite**

```bash
python -m pytest tests/ -v --tb=short
```
Expected: All tests PASS

- [ ] **Verify MCP tools registered correctly**

```bash
python -c "
import sys
sys.path.insert(0, 'mcp_server')
import server
tools = [t for t in dir(server.mcp) if not t.startswith('_')]
print('goalcast_get_todays_matches' in str(server.mcp))
print('goalcast_prefetch_today' in str(server.mcp))
print('goalcast_resolve_match' in str(server.mcp))
"
```

- [ ] **Verify skills reference goalcast_get_todays_matches (not footystats_get_todays_matches)**

```bash
grep -r "footystats_get_todays_matches" skills/ && echo "FAIL: provider-specific tool still in skills" || echo "OK: no provider-specific tools in skills"
```
Expected: `OK: no provider-specific tools in skills`

- [ ] **Final commit**

```bash
git tag v2.0-refactor
```

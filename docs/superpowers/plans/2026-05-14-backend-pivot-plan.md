# Backend OddAlert-Only Pivot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 删除 FootyStats / Sportmonks / Understat 三个 provider 及其融合层，让 analytics 与 RD agent 循环仅消费 OddAlerts 数据；新增 `/api/*` 浏览层 HTTP 端点（含缓存与速率限制）。

**Architecture:** 单源数据流：OddAlerts API → `OddAlertsProvider` → 两条消费支线 — (a) 新 HTTP API 层（带 sqlite 缓存 + token-bucket 速率限制）供前端读取；(b) `data_collector` 喂给 `analytics`（poisson/ev/confidence）→ agent RD 循环 → `match_store` 回写。

**Tech Stack:** Python 3.12 · FastAPI · httpx · pytest · sqlite3 (stdlib) · ruff

**Spec:** `docs/superpowers/specs/2026-05-14-oddalert-only-pivot-design.md`

---

## File Structure

### Delete
- `backend/provider/footystats/`
- `backend/provider/sportmonks/`
- `backend/provider/understat/`
- `backend/services/datafusion/`
- `backend/services/sportmonks/`

### Create
- `backend/provider/oddalerts/feature_extractor.py`
- `backend/utils/cache.py`
- `backend/utils/rate_limit.py`
- `backend/server/routes/browse.py`
- `tests/provider/oddalerts/test_feature_extractor.py`
- `tests/utils/test_cache.py`
- `tests/utils/test_rate_limit.py`
- `tests/server/routes/test_browse.py`

### Modify
- `backend/provider/__init__.py`
- `backend/provider/base.py`
- `backend/agents/core/fixture_merger.py`
- `backend/agents/core/data_collector.py`
- `backend/agents/core/match_store.py`
- `backend/analytics/poisson.py`
- `backend/analytics/ev_calculator.py`
- `backend/analytics/confidence.py`
- `backend/server/__init__.py` 或主 router 装配处
- `backend/server/routes/board.py`（若引用已删 provider）

---

## Task 1: Audit doomed-module imports

**Files:** Read-only audit, no edits.

- [ ] **Step 1: List every reference to doomed packages**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast
grep -rn --include='*.py' -E 'from provider\.(footystats|sportmonks|understat)|import provider\.(footystats|sportmonks|understat)|from services\.(datafusion|sportmonks)|import services\.(datafusion|sportmonks)' backend tests 2>/dev/null > /tmp/goalcast_doomed_imports.txt
wc -l /tmp/goalcast_doomed_imports.txt
cat /tmp/goalcast_doomed_imports.txt
```
Expected: a file listing every doomed import site. Use this as the worklist for Tasks 2-4.

- [ ] **Step 2: Snapshot test baseline**

```bash
cd backend
python -m pytest -q --collect-only 2>&1 | tail -5
```
Note current test count; we must not regress.

---

## Task 2: Delete doomed providers + DataFusion service

**Files:**
- Delete: `backend/provider/footystats/`
- Delete: `backend/provider/sportmonks/`
- Delete: `backend/provider/understat/`
- Delete: `backend/services/datafusion/`
- Delete: `backend/services/sportmonks/`
- Modify: `backend/provider/__init__.py`
- Modify: `backend/services/__init__.py`

- [ ] **Step 1: Write failing test that confirms doomed modules are gone**

Create `tests/test_doomed_providers_removed.py`:
```python
import importlib
import pytest


@pytest.mark.parametrize("mod", [
    "provider.footystats",
    "provider.sportmonks",
    "provider.understat",
    "services.datafusion",
    "services.sportmonks",
])
def test_doomed_modules_absent(mod):
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(mod)
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
cd backend && python -m pytest ../tests/test_doomed_providers_removed.py -v
```
Expected: 5 failures (modules currently exist).

- [ ] **Step 3: Delete directories**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast
rm -rf backend/provider/footystats backend/provider/sportmonks backend/provider/understat
rm -rf backend/services/datafusion backend/services/sportmonks
```

- [ ] **Step 4: Strip imports from `backend/provider/__init__.py`**

Open the file. Remove any line referencing `footystats`, `sportmonks`, or `understat`. Keep only `oddalerts` registration and the `BaseProvider` re-export.

- [ ] **Step 5: Strip imports from `backend/services/__init__.py`**

Open the file. Remove any line referencing `datafusion` or `sportmonks`.

- [ ] **Step 6: Run the doomed-modules test — expect PASS**

```bash
cd backend && python -m pytest ../tests/test_doomed_providers_removed.py -v
```
Expected: 5 passed.

- [ ] **Step 7: Run full test suite to find broken imports**

```bash
cd backend && python -m pytest -x 2>&1 | tail -30
```
Each `ImportError` points to a remaining caller. Track each — fix in this Step 8 or defer to Tasks 3, 4, 9.

- [ ] **Step 8: For each remaining caller, replace doomed import**

For every file flagged in Step 7, either:
- Delete the offending import + code path that used it, OR
- If the path is referenced elsewhere, raise `NotImplementedError("Provider removed — see 2026-05-14 pivot")` and leave a comment for later replacement.

Verify imports resolve cleanly:
```bash
cd backend && python -c "import provider; import services; import agents.core.data_collector; import agents.core.fixture_merger; print('OK')"
```
Expected: `OK`

- [ ] **Step 9: Commit**

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast
git add -A backend tests
git commit -m "refactor(backend): remove footystats/sportmonks/understat providers + datafusion service"
```

---

## Task 3: Simplify `provider/base.py` to oddalerts-only shim

**Files:**
- Modify: `backend/provider/base.py`
- Test: `tests/provider/test_base.py`

- [ ] **Step 1: Read current `base.py`**

```bash
cat backend/provider/base.py
```

- [ ] **Step 2: Write failing test**

Create `tests/provider/test_base.py`:
```python
from provider.base import BaseProvider, get_provider
from provider.oddalerts.client import OddAlertsProvider


def test_get_provider_returns_oddalerts_instance():
    p = get_provider()
    assert isinstance(p, OddAlertsProvider)
    assert p.name() == "oddalerts"


def test_base_provider_abstract_methods_minimal():
    required = {"name", "is_available"}
    impl = set(dir(BaseProvider))
    assert required.issubset(impl)
```

- [ ] **Step 3: Run — expect FAIL**

```bash
cd backend && python -m pytest ../tests/provider/test_base.py -v
```

- [ ] **Step 4: Rewrite `backend/provider/base.py`**

```python
"""Provider abstraction — single-source (OddAlerts) shim."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional


class BaseProvider(ABC):
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    async def is_available(self) -> bool:
        ...


_singleton: Optional["BaseProvider"] = None


def get_provider() -> BaseProvider:
    global _singleton
    if _singleton is None:
        from provider.oddalerts.client import OddAlertsProvider
        from config.settings import settings
        _singleton = OddAlertsProvider(api_key=settings.oddalerts_api_key)
    return _singleton


def reset_provider() -> None:
    global _singleton
    _singleton = None
```

- [ ] **Step 5: Run — expect PASS**

```bash
cd backend && python -m pytest ../tests/provider/test_base.py -v
```

- [ ] **Step 6: Commit**

```bash
git add backend/provider/base.py tests/provider/test_base.py
git commit -m "refactor(provider): simplify base.py to oddalerts-only shim"
```

---

## Task 4: Simplify `fixture_merger.py` to oddalerts normalization

**Files:**
- Modify: `backend/agents/core/fixture_merger.py`
- Test: `tests/agents/core/test_fixture_merger.py`

- [ ] **Step 1: Read current file**

```bash
cat backend/agents/core/fixture_merger.py
```

- [ ] **Step 2: Write failing test**

Create `tests/agents/core/test_fixture_merger.py`:
```python
from agents.core.fixture_merger import normalize_oddalerts_fixture


def test_normalize_basic_fixture():
    raw = {
        "id": 12345,
        "name": "Arsenal vs Chelsea",
        "starting_at": "2026-05-14T20:00:00Z",
        "league": {"id": 8, "name": "Premier League", "country": "England"},
        "participants": [
            {"id": 1, "name": "Arsenal", "meta": {"location": "home"}},
            {"id": 2, "name": "Chelsea", "meta": {"location": "away"}},
        ],
    }
    out = normalize_oddalerts_fixture(raw)
    assert out["fixture_id"] == 12345
    assert out["home_team"]["name"] == "Arsenal"
    assert out["away_team"]["name"] == "Chelsea"
    assert out["league"]["name"] == "Premier League"
    assert out["kickoff_utc"] == "2026-05-14T20:00:00Z"


def test_normalize_missing_participants_returns_none():
    raw = {"id": 999, "name": "Unknown", "starting_at": "2026-05-14T20:00:00Z"}
    assert normalize_oddalerts_fixture(raw) is None
```

- [ ] **Step 3: Run — expect FAIL**

```bash
cd backend && python -m pytest ../tests/agents/core/test_fixture_merger.py -v
```

- [ ] **Step 4: Rewrite `backend/agents/core/fixture_merger.py`**

```python
"""Normalize OddAlerts fixture responses into a canonical internal shape."""
from __future__ import annotations
from typing import Any, Optional


def normalize_oddalerts_fixture(raw: dict[str, Any]) -> Optional[dict[str, Any]]:
    participants = raw.get("participants") or []
    home = next((p for p in participants if (p.get("meta") or {}).get("location") == "home"), None)
    away = next((p for p in participants if (p.get("meta") or {}).get("location") == "away"), None)
    if not home or not away:
        return None
    league = raw.get("league") or {}
    return {
        "fixture_id": raw.get("id"),
        "name": raw.get("name"),
        "kickoff_utc": raw.get("starting_at"),
        "league": {
            "id": league.get("id"),
            "name": league.get("name"),
            "country": league.get("country"),
        },
        "home_team": {"id": home.get("id"), "name": home.get("name")},
        "away_team": {"id": away.get("id"), "name": away.get("name")},
        "raw": raw,
    }
```

- [ ] **Step 5: Run — expect PASS**

```bash
cd backend && python -m pytest ../tests/agents/core/test_fixture_merger.py -v
```

- [ ] **Step 6: Commit**

```bash
git add backend/agents/core/fixture_merger.py tests/agents/core/test_fixture_merger.py
git commit -m "refactor(agents): simplify fixture_merger to oddalerts normalizer"
```

---

## Task 5: OddAlerts → analytics feature extractor

**Files:**
- Create: `backend/provider/oddalerts/feature_extractor.py`
- Test: `tests/provider/oddalerts/test_feature_extractor.py`

- [ ] **Step 1: Write failing test**

Create `tests/provider/oddalerts/test_feature_extractor.py`:
```python
from provider.oddalerts.feature_extractor import (
    extract_team_lambdas,
    extract_market_odds,
    extract_trend_priors,
)


def test_extract_team_lambdas_from_season_stats():
    home_stats = {"goals_for_avg": 2.1, "goals_against_avg": 0.8, "xg_for": 2.24}
    away_stats = {"goals_for_avg": 1.4, "goals_against_avg": 1.3, "xg_for": 1.05}
    out = extract_team_lambdas(home_stats, away_stats)
    assert 1.0 < out["home_lambda"] < 3.0
    assert 0.5 < out["away_lambda"] < 2.0
    assert out["source"] == "oddalerts_stats"


def test_extract_team_lambdas_missing_data_returns_none():
    assert extract_team_lambdas({}, {}) is None


def test_extract_market_odds_picks_closing_1x2():
    odds_history = {
        "markets": {
            "ft_result": {
                "Bet365": {
                    "home": {"closing": 1.72, "opening": 1.87, "peak": 1.90},
                    "draw": {"closing": 3.85},
                    "away": {"closing": 4.60},
                }
            }
        }
    }
    out = extract_market_odds(odds_history, market="ft_result", bookmaker="Bet365")
    assert out == {"H": 1.72, "D": 3.85, "A": 4.60}


def test_extract_trend_priors():
    trends = {"homeWin": 0.621, "awayWin": 0.182, "btts": 0.554}
    out = extract_trend_priors(trends)
    assert out["H"] == 0.621
    assert out["A"] == 0.182
    assert abs(out["D"] - (1 - 0.621 - 0.182)) < 1e-9
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd backend && python -m pytest ../tests/provider/oddalerts/test_feature_extractor.py -v
```

- [ ] **Step 3: Implement `backend/provider/oddalerts/feature_extractor.py`**

```python
"""Extract analytics-ready features from OddAlerts raw API responses."""
from __future__ import annotations
from typing import Any, Optional


def extract_team_lambdas(
    home_stats: dict[str, Any],
    away_stats: dict[str, Any],
) -> Optional[dict[str, Any]]:
    """Compute λ_home / λ_away from OddAlerts /api/stats season responses.

    Signal preference: xg_for > goals_for_avg. Returns None if any side has no signal.
    """
    def _team_lambda(team_for: dict, opp_against: dict) -> Optional[float]:
        for_signal = team_for.get("xg_for") or team_for.get("goals_for_avg")
        against_signal = opp_against.get("xg_against") or opp_against.get("goals_against_avg")
        if for_signal is None or against_signal is None:
            return None
        return float(for_signal) * 0.6 + float(against_signal) * 0.4

    lam_h = _team_lambda(home_stats, away_stats)
    lam_a = _team_lambda(away_stats, home_stats)
    if lam_h is None or lam_a is None:
        return None
    return {
        "home_lambda": round(lam_h, 4),
        "away_lambda": round(lam_a, 4),
        "source": "oddalerts_stats",
    }


def extract_market_odds(
    odds_history: dict[str, Any],
    market: str = "ft_result",
    bookmaker: str = "Bet365",
) -> Optional[dict[str, float]]:
    try:
        block = odds_history["markets"][market][bookmaker]
        return {
            "H": float(block["home"]["closing"]),
            "D": float(block["draw"]["closing"]),
            "A": float(block["away"]["closing"]),
        }
    except (KeyError, TypeError, ValueError):
        return None


def extract_trend_priors(trends: dict[str, Any]) -> dict[str, float]:
    """Convert trends.{homeWin,awayWin,btts} into 1X2 prior probs. D implied."""
    h = float(trends.get("homeWin") or 0.0)
    a = float(trends.get("awayWin") or 0.0)
    d = max(0.0, 1.0 - h - a)
    return {"H": h, "D": d, "A": a}
```

- [ ] **Step 4: Run — expect PASS**

```bash
cd backend && python -m pytest ../tests/provider/oddalerts/test_feature_extractor.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/provider/oddalerts/feature_extractor.py tests/provider/oddalerts/
git commit -m "feat(oddalerts): add feature extractor for analytics inputs"
```

---

## Task 6: Adapt `poisson.py` — `poisson_from_oddalerts` wrapper

**Files:**
- Modify: `backend/analytics/poisson.py`
- Test: `tests/analytics/test_poisson_oddalerts.py`

- [ ] **Step 1: Inspect existing signature**

```bash
grep -n "^def " backend/analytics/poisson.py
```
Existing `poisson_distribution(home_lambda, away_lambda, max_goals=6)` is reused.

- [ ] **Step 2: Write failing test**

Create `tests/analytics/test_poisson_oddalerts.py`:
```python
from analytics.poisson import poisson_from_oddalerts


def test_poisson_from_oddalerts_returns_full_distribution():
    home_stats = {"xg_for": 2.0, "goals_against_avg": 1.0}
    away_stats = {"xg_for": 1.0, "goals_against_avg": 1.0}
    result = poisson_from_oddalerts(home_stats, away_stats)
    assert "home_win_pct" in result
    assert "draw_pct" in result
    assert "away_win_pct" in result
    total = result["home_win_pct"] + result["draw_pct"] + result["away_win_pct"]
    assert abs(total - 100.0) < 0.5


def test_poisson_from_oddalerts_missing_data_returns_none():
    assert poisson_from_oddalerts({}, {}) is None
```

- [ ] **Step 3: Run — expect FAIL**

```bash
cd backend && python -m pytest ../tests/analytics/test_poisson_oddalerts.py -v
```

- [ ] **Step 4: Append wrapper to `backend/analytics/poisson.py`**

```python
def poisson_from_oddalerts(home_stats: dict, away_stats: dict, max_goals: int = 6):
    """High-level: OddAlerts stats → Poisson distribution. Returns None if signals missing."""
    from provider.oddalerts.feature_extractor import extract_team_lambdas
    feats = extract_team_lambdas(home_stats, away_stats)
    if feats is None:
        return None
    return poisson_distribution(
        home_lambda=feats["home_lambda"],
        away_lambda=feats["away_lambda"],
        max_goals=max_goals,
    )
```

- [ ] **Step 5: Run — expect PASS**

```bash
cd backend && python -m pytest ../tests/analytics/test_poisson_oddalerts.py -v
```

- [ ] **Step 6: Commit**

```bash
git add backend/analytics/poisson.py tests/analytics/test_poisson_oddalerts.py
git commit -m "feat(analytics): add poisson_from_oddalerts wrapper"
```

---

## Task 7: Adapt `ev_calculator.py` — `ev_from_oddalerts` wrapper

**Files:**
- Modify: `backend/analytics/ev_calculator.py`
- Test: `tests/analytics/test_ev_oddalerts.py`

- [ ] **Step 1: Inspect existing signatures**

```bash
grep -n "^def " backend/analytics/ev_calculator.py
```
Inspect what `calculate_ev` and `calculate_kelly` return (dict vs float) — pin the right unwrap in Step 4.

- [ ] **Step 2: Write failing test**

Create `tests/analytics/test_ev_oddalerts.py`:
```python
from analytics.ev_calculator import ev_from_oddalerts


def test_ev_from_oddalerts_positive_when_model_outperforms_market():
    model_probs = {"H": 0.62, "D": 0.20, "A": 0.18}
    odds_history = {"markets": {"ft_result": {"Bet365": {
        "home": {"closing": 1.72}, "draw": {"closing": 3.85}, "away": {"closing": 4.60},
    }}}}
    result = ev_from_oddalerts(model_probs, odds_history)
    assert result["H"]["ev"] > 0
    assert "kelly" in result["H"]


def test_ev_from_oddalerts_missing_odds_returns_none():
    assert ev_from_oddalerts({"H": 0.5, "D": 0.25, "A": 0.25}, {}) is None
```

- [ ] **Step 3: Run — expect FAIL**

```bash
cd backend && python -m pytest ../tests/analytics/test_ev_oddalerts.py -v
```

- [ ] **Step 4: Append wrapper to `backend/analytics/ev_calculator.py`**

```python
def ev_from_oddalerts(model_probs: dict, odds_history: dict, bookmaker: str = "Bet365"):
    """Combine model 1X2 probs with OddAlerts closing odds → EV+Kelly per direction."""
    from provider.oddalerts.feature_extractor import extract_market_odds
    odds = extract_market_odds(odds_history, market="ft_result", bookmaker=bookmaker)
    if odds is None:
        return None
    out = {}
    for direction in ("H", "D", "A"):
        ev_raw = calculate_ev(model_probs[direction], odds[direction])
        kelly_raw = calculate_kelly(model_probs[direction], odds[direction])
        ev_val = ev_raw["ev"] if isinstance(ev_raw, dict) else float(ev_raw)
        kelly_val = (
            kelly_raw["kelly_fraction"] if isinstance(kelly_raw, dict) else float(kelly_raw)
        )
        out[direction] = {
            "model_prob": model_probs[direction],
            "odds": odds[direction],
            "ev": ev_val,
            "kelly": kelly_val,
        }
    return out
```

If Step 1 confirmed `calculate_ev` returns a plain float, simplify the unwrap accordingly.

- [ ] **Step 5: Run — expect PASS**

```bash
cd backend && python -m pytest ../tests/analytics/test_ev_oddalerts.py -v
```

- [ ] **Step 6: Commit**

```bash
git add backend/analytics/ev_calculator.py tests/analytics/test_ev_oddalerts.py
git commit -m "feat(analytics): add ev_from_oddalerts wrapper"
```

---

## Task 8: Adapt `confidence.py` — `confidence_from_oddalerts` wrapper

**Files:**
- Modify: `backend/analytics/confidence.py`
- Test: `tests/analytics/test_confidence_oddalerts.py`

- [ ] **Step 1: Write failing test**

Create `tests/analytics/test_confidence_oddalerts.py`:
```python
from analytics.confidence import confidence_from_oddalerts


def test_confidence_high_when_model_and_trends_agree():
    model_probs = {"H": 0.62, "D": 0.20, "A": 0.18}
    trends = {"homeWin": 0.621, "awayWin": 0.182}
    out = confidence_from_oddalerts(model_probs, trends, odds_history_present=True)
    assert out["stars"] >= 4
    assert out["agreement"] is True


def test_confidence_low_when_model_disagrees_with_trends():
    model_probs = {"H": 0.30, "D": 0.20, "A": 0.50}
    trends = {"homeWin": 0.621, "awayWin": 0.182}
    out = confidence_from_oddalerts(model_probs, trends, odds_history_present=True)
    assert out["stars"] <= 3
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd backend && python -m pytest ../tests/analytics/test_confidence_oddalerts.py -v
```

- [ ] **Step 3: Append wrapper to `backend/analytics/confidence.py`**

```python
def confidence_from_oddalerts(model_probs: dict, trends: dict, odds_history_present: bool = True):
    """Compute confidence with OddAlerts trends as the agreement signal.

    Returns {"score": 0-100, "stars": 0-5, "agreement": bool}.
    """
    from provider.oddalerts.feature_extractor import extract_trend_priors
    priors = extract_trend_priors(trends)
    pick = max(model_probs, key=lambda k: model_probs[k])
    gap = abs(model_probs[pick] - priors[pick])
    agreement = gap < 0.10  # within 10 pp

    base = calculate_confidence(
        base_score=70,
        market_agrees=agreement,
        data_complete=True,
        understat_available=False,
        odds_available=odds_history_present,
        lineup_unavailable=True,
    )
    score = base["confidence_score"] if isinstance(base, dict) else int(base)
    stars = min(5, max(0, round(score / 18)))
    return {"score": score, "stars": stars, "agreement": agreement}
```

- [ ] **Step 4: Run — expect PASS**

```bash
cd backend && python -m pytest ../tests/analytics/test_confidence_oddalerts.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/analytics/confidence.py tests/analytics/test_confidence_oddalerts.py
git commit -m "feat(analytics): add confidence_from_oddalerts wrapper using trends as prior"
```

---

## Task 9: Single-source `data_collector.py` + extend `MatchRecord`

**Files:**
- Modify: `backend/agents/core/data_collector.py`
- Modify: `backend/agents/core/match_store.py`
- Test: `tests/agents/core/test_data_collector_oddalerts.py`

- [ ] **Step 1: Read current state**

```bash
sed -n '140,200p' backend/agents/core/data_collector.py
cat backend/agents/core/match_store.py
```

- [ ] **Step 2: Write failing test**

Create `tests/agents/core/test_data_collector_oddalerts.py`:
```python
import pytest
from unittest.mock import AsyncMock, patch
from agents.core.data_collector import collect_all


@pytest.mark.asyncio
async def test_collect_all_uses_only_oddalerts():
    fake = {
        "fixture": {"id": 1, "name": "A vs B", "starting_at": "2026-05-14T20:00:00Z",
                    "participants": [
                        {"id": 11, "name": "A", "meta": {"location": "home"}},
                        {"id": 22, "name": "B", "meta": {"location": "away"}},
                    ]},
        "odds_history": {"markets": {"ft_result": {"Bet365": {
            "home": {"closing": 1.72}, "draw": {"closing": 3.85}, "away": {"closing": 4.60}
        }}}},
        "h2h": [],
        "stats_home": {"xg_for": 2.0, "goals_against_avg": 1.0},
        "stats_away": {"xg_for": 1.0, "goals_against_avg": 1.0},
        "trends": {"homeWin": 0.62, "awayWin": 0.18},
    }
    with patch("agents.core.data_collector.collect_oddalerts", AsyncMock(return_value=fake)):
        out = await collect_all(oa_fixture_id=1)
    assert out is not None
    assert out["source"] == "oddalerts"
    assert "fixture" in out and "odds_history" in out
    assert "sportmonks" not in out and "footystats" not in out
```

- [ ] **Step 3: Run — expect FAIL**

```bash
cd backend && python -m pytest ../tests/agents/core/test_data_collector_oddalerts.py -v
```

- [ ] **Step 4: Rewrite `backend/agents/core/data_collector.py`**

```python
"""Single-source data collector — OddAlerts only."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def collect_oddalerts(oa_fixture_id: int) -> Optional[dict[str, Any]]:
    """Pull full fixture bundle from OddAlerts. Returns None if unreachable."""
    from provider.base import get_provider
    provider = get_provider()
    return await provider.collect_fixture_data(oa_fixture_id)


async def collect_all(oa_fixture_id: int) -> Optional[dict[str, Any]]:
    bundle = await collect_oddalerts(oa_fixture_id)
    if not bundle or "fixture" not in bundle:
        return None
    return {
        "source": "oddalerts",
        "collected_at": _now_iso(),
        "fixture": bundle.get("fixture"),
        "odds_history": bundle.get("odds_history"),
        "h2h": bundle.get("h2h"),
        "stats_home": bundle.get("stats_home"),
        "stats_away": bundle.get("stats_away"),
        "trends": bundle.get("trends"),
    }
```

If `provider.collect_fixture_data` doesn't return the keyed shape `{fixture, odds_history, h2h, stats_home, stats_away, trends}`, update it (or add an assembler helper inside `oddalerts/client.py`). The test in Step 2 dictates the contract.

- [ ] **Step 5: Extend `MatchRecord` in `backend/agents/core/match_store.py`**

Locate the `MatchRecord` dataclass / TypedDict. Add the optional field. Example for a dataclass:
```python
# At top of the file if missing:
from typing import Optional

# Inside MatchRecord:
analysis: Optional[dict] = None
# Shape of analysis dict (documented in comment near MatchRecord):
# {
#   "model_prob":   {"H": float, "D": float, "A": float},
#   "market_prob":  {"H": float, "D": float, "A": float},
#   "pick":         "H" | "D" | "A",
#   "odds":         float,
#   "ev":           float,
#   "kelly":        float,
#   "confidence_stars": int,
#   "analyst_summary":  Optional[str],
#   "reviewer_verdict": Optional["pass" | "fail" | "skip"],
#   "run_id":           Optional[str],
#   "analyzed_at":      str,  # ISO-8601 UTC
# }
```

- [ ] **Step 6: Run all agent tests**

```bash
cd backend && python -m pytest ../tests/agents/core/ -v
```

- [ ] **Step 7: Commit**

```bash
git add backend/agents/core/data_collector.py backend/agents/core/match_store.py tests/agents/core/test_data_collector_oddalerts.py
git commit -m "refactor(agents): single-source data_collector + add MatchRecord.analysis"
```

---

## Task 10: SQLite cache module

**Files:**
- Create: `backend/utils/cache.py`
- Test: `tests/utils/test_cache.py`

- [ ] **Step 1: Write failing test**

Create `tests/utils/test_cache.py`:
```python
import time
import pytest
from utils.cache import Cache


@pytest.fixture
def cache(tmp_path):
    return Cache(tmp_path / "cache.db")


def test_set_get_roundtrip(cache):
    cache.set("k1", {"a": 1}, ttl_seconds=60)
    assert cache.get("k1") == {"a": 1}


def test_expiry(cache):
    cache.set("k2", "v", ttl_seconds=1)
    assert cache.get("k2") == "v"
    time.sleep(1.1)
    assert cache.get("k2") is None


def test_permanent_ttl_zero(cache):
    cache.set("k3", "forever", ttl_seconds=0)
    assert cache.get("k3") == "forever"


def test_missing_key_returns_none(cache):
    assert cache.get("nope") is None


def test_delete(cache):
    cache.set("k4", "v", ttl_seconds=60)
    cache.delete("k4")
    assert cache.get("k4") is None
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd backend && python -m pytest ../tests/utils/test_cache.py -v
```

- [ ] **Step 3: Implement `backend/utils/cache.py`**

```python
"""SQLite-backed key/value cache with TTL."""
from __future__ import annotations
import json
import sqlite3
import time
from pathlib import Path
from threading import RLock
from typing import Any, Optional


_SCHEMA = """
CREATE TABLE IF NOT EXISTS cache (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    expires_at INTEGER NOT NULL,
    created_at INTEGER NOT NULL
);
"""


class Cache:
    def __init__(self, db_path: Path):
        db_path = Path(db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._path = str(db_path)
        self._lock = RLock()
        with self._conn() as conn:
            conn.executescript(_SCHEMA)

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path, timeout=5.0)

    def get(self, key: str) -> Optional[Any]:
        with self._lock, self._conn() as conn:
            row = conn.execute(
                "SELECT value, expires_at FROM cache WHERE key = ?", (key,)
            ).fetchone()
        if row is None:
            return None
        value, expires_at = row
        if expires_at != 0 and expires_at < int(time.time()):
            self.delete(key)
            return None
        return json.loads(value)

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        now = int(time.time())
        expires_at = 0 if ttl_seconds == 0 else now + ttl_seconds
        payload = json.dumps(value)
        with self._lock, self._conn() as conn:
            conn.execute(
                "INSERT INTO cache(key,value,expires_at,created_at) VALUES(?,?,?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value, expires_at=excluded.expires_at",
                (key, payload, expires_at, now),
            )
            conn.commit()

    def delete(self, key: str) -> None:
        with self._lock, self._conn() as conn:
            conn.execute("DELETE FROM cache WHERE key = ?", (key,))
            conn.commit()
```

- [ ] **Step 4: Run — expect PASS**

```bash
cd backend && python -m pytest ../tests/utils/test_cache.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/utils/cache.py tests/utils/test_cache.py
git commit -m "feat(utils): sqlite-backed cache with TTL"
```

---

## Task 11: Token-bucket rate limiter

**Files:**
- Create: `backend/utils/rate_limit.py`
- Test: `tests/utils/test_rate_limit.py`

- [ ] **Step 1: Write failing test**

Create `tests/utils/test_rate_limit.py`:
```python
import time
import pytest
from utils.rate_limit import TokenBucket


def test_initial_burst_allowed():
    b = TokenBucket(capacity=5, refill_per_sec=1.0)
    for _ in range(5):
        assert b.try_acquire() is True


def test_exhaustion_blocks():
    b = TokenBucket(capacity=2, refill_per_sec=1.0)
    assert b.try_acquire()
    assert b.try_acquire()
    assert b.try_acquire() is False


def test_refill_over_time():
    b = TokenBucket(capacity=2, refill_per_sec=10.0)
    b.try_acquire(); b.try_acquire()
    assert b.try_acquire() is False
    time.sleep(0.25)
    assert b.try_acquire() is True


@pytest.mark.asyncio
async def test_acquire_async_waits_for_refill():
    b = TokenBucket(capacity=1, refill_per_sec=10.0)
    assert b.try_acquire()
    t0 = time.time()
    await b.acquire()
    assert time.time() - t0 >= 0.08
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd backend && python -m pytest ../tests/utils/test_rate_limit.py -v
```

- [ ] **Step 3: Implement `backend/utils/rate_limit.py`**

```python
"""Token-bucket rate limiter — sync + async."""
from __future__ import annotations
import asyncio
import time
from threading import Lock


class TokenBucket:
    def __init__(self, capacity: int, refill_per_sec: float):
        self.capacity = float(capacity)
        self.refill = float(refill_per_sec)
        self._tokens = float(capacity)
        self._last = time.monotonic()
        self._lock = Lock()

    def _replenish(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last
        self._tokens = min(self.capacity, self._tokens + elapsed * self.refill)
        self._last = now

    def try_acquire(self, n: int = 1) -> bool:
        with self._lock:
            self._replenish()
            if self._tokens >= n:
                self._tokens -= n
                return True
            return False

    async def acquire(self, n: int = 1) -> None:
        while True:
            with self._lock:
                self._replenish()
                if self._tokens >= n:
                    self._tokens -= n
                    return
                shortfall = n - self._tokens
                wait = shortfall / max(self.refill, 1e-9)
            await asyncio.sleep(max(wait, 0.01))
```

- [ ] **Step 4: Run — expect PASS**

```bash
cd backend && python -m pytest ../tests/utils/test_rate_limit.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/utils/rate_limit.py tests/utils/test_rate_limit.py
git commit -m "feat(utils): token-bucket rate limiter (sync + async)"
```

---

## Task 12: Browse router scaffold + `/api/competitions`

**Files:**
- Create: `backend/server/routes/browse.py`
- Modify: app assembly file (discover in Step 1)
- Test: `tests/server/routes/test_browse.py`

- [ ] **Step 1: Discover where routers are mounted**

```bash
grep -rn "include_router\|app = FastAPI" backend --include='*.py'
```
Note the exact assembly file path.

- [ ] **Step 2: Write failing test**

Create `tests/server/routes/test_browse.py`:
```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch


@pytest.fixture
def client():
    from server.app import app  # fix the import to wherever app is constructed
    return TestClient(app)


def test_competitions_endpoint_returns_list(client):
    fake = {"data": [{"id": 8, "name": "Premier League", "country": "England"}]}
    with patch("provider.oddalerts.client.OddAlertsProvider.get_competitions",
               AsyncMock(return_value=fake)):
        r = client.get("/api/competitions")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    assert body[0]["name"] == "Premier League"


def test_competitions_cached_on_second_call(client):
    fake = {"data": [{"id": 8, "name": "PL", "country": "ENG"}]}
    with patch("provider.oddalerts.client.OddAlertsProvider.get_competitions",
               AsyncMock(return_value=fake)) as mock:
        client.get("/api/competitions")
        client.get("/api/competitions")
        assert mock.await_count == 1
```

- [ ] **Step 3: Run — expect FAIL**

```bash
cd backend && python -m pytest ../tests/server/routes/test_browse.py -v
```

- [ ] **Step 4: Create `backend/server/routes/browse.py`**

```python
"""Browse-layer HTTP API — wraps OddAlertsProvider for the new frontend."""
from __future__ import annotations
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from provider.base import get_provider
from utils.cache import Cache

router = APIRouter(prefix="/api", tags=["browse"])

_CACHE_PATH = Path(__file__).resolve().parents[2] / "data" / "cache.db"
_cache = Cache(_CACHE_PATH)


def _normalize_competitions(raw: dict) -> list[dict]:
    items = raw.get("data") or []
    return [{"id": c.get("id"), "name": c.get("name"), "country": c.get("country")} for c in items]


@router.get("/competitions")
async def get_competitions():
    cache_key = "competitions:all"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached
    provider = get_provider()
    raw = await provider.get_competitions()
    if not raw:
        raise HTTPException(status_code=502, detail="OddAlerts unavailable")
    result = _normalize_competitions(raw)
    _cache.set(cache_key, result, ttl_seconds=86_400)
    return result
```

- [ ] **Step 5: Mount the router**

In the file from Step 1, add:
```python
from server.routes.browse import router as browse_router
app.include_router(browse_router)
```

- [ ] **Step 6: Run — expect PASS**

```bash
cd backend && python -m pytest ../tests/server/routes/test_browse.py -v
```

- [ ] **Step 7: Commit**

```bash
git add backend/server tests/server/routes/test_browse.py
git commit -m "feat(api): browse router + /api/competitions with cache"
```

---

## Task 13: `/api/fixtures` (date + competition filter)

**Files:**
- Modify: `backend/server/routes/browse.py`
- Modify: `tests/server/routes/test_browse.py`

- [ ] **Step 1: Append failing test**

```python
def test_fixtures_endpoint_filters_by_date(client):
    fake = {"data": [
        {"id": 1, "fixture_name": "A vs B", "starting_at": "2026-05-14T20:00:00Z",
         "league": {"id": 8, "name": "PL"}, "drop_percentage": -8.0,
         "closing": 1.72, "opening": 1.87},
        {"id": 2, "fixture_name": "C vs D", "starting_at": "2026-05-15T20:00:00Z",
         "league": {"id": 8, "name": "PL"}},
    ]}
    with patch("provider.oddalerts.client.OddAlertsProvider.get_dropping_odds",
               AsyncMock(return_value=fake)):
        r = client.get("/api/fixtures?date=2026-05-14")
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    assert items[0]["fixture_id"] == 1
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd backend && python -m pytest ../tests/server/routes/test_browse.py::test_fixtures_endpoint_filters_by_date -v
```

- [ ] **Step 3: Add endpoint to `browse.py`**

```python
@router.get("/fixtures")
async def get_fixtures(
    date: str = Query(..., description="YYYY-MM-DD UTC"),
    competition_id: Optional[int] = None,
):
    cache_key = f"fixtures:{date}:{competition_id or 'all'}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached
    provider = get_provider()
    raw = await provider.get_dropping_odds()
    if not raw:
        return []
    items = []
    for f in raw.get("data") or []:
        starts = (f.get("starting_at") or "")[:10]
        if starts != date:
            continue
        if competition_id and (f.get("league") or {}).get("id") != competition_id:
            continue
        items.append({
            "fixture_id": f.get("id"),
            "name": f.get("fixture_name"),
            "kickoff_utc": f.get("starting_at"),
            "league": f.get("league"),
            "closing": f.get("closing"),
            "opening": f.get("opening"),
            "drop_percentage": f.get("drop_percentage"),
        })
    _cache.set(cache_key, items, ttl_seconds=300)
    return items
```

- [ ] **Step 4: Run — expect PASS**

```bash
cd backend && python -m pytest ../tests/server/routes/test_browse.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/server/routes/browse.py tests/server/routes/test_browse.py
git commit -m "feat(api): /api/fixtures with date+competition filter"
```

---

## Task 14: `/api/fixtures/{id}` aggregated detail

**Files:**
- Modify: `backend/server/routes/browse.py`
- Modify: `tests/server/routes/test_browse.py`

- [ ] **Step 1: Append failing test**

```python
def test_fixture_detail_aggregates_bundle(client):
    bundle = {
        "fixture": {"id": 1, "name": "A vs B", "starting_at": "2026-05-14T20:00:00Z",
                    "participants": [
                        {"id": 11, "name": "A", "meta": {"location": "home"}},
                        {"id": 22, "name": "B", "meta": {"location": "away"}},
                    ], "league": {"id": 8, "name": "PL"}},
        "odds_history": {"markets": {"ft_result": {"Bet365": {
            "home": {"closing": 1.72, "opening": 1.87}, "draw": {"closing": 3.85},
            "away": {"closing": 4.60}}}}},
        "h2h": [], "stats_home": {}, "stats_away": {}, "trends": {},
    }
    with patch("provider.oddalerts.client.OddAlertsProvider.collect_fixture_data",
               AsyncMock(return_value=bundle)):
        r = client.get("/api/fixtures/1")
    assert r.status_code == 200
    body = r.json()
    assert body["fixture_id"] == 1
    assert "odds_history" in body
    assert body["home_team"]["name"] == "A"
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd backend && python -m pytest ../tests/server/routes/test_browse.py::test_fixture_detail_aggregates_bundle -v
```

- [ ] **Step 3: Add endpoint**

```python
@router.get("/fixtures/{fixture_id}")
async def get_fixture_detail(fixture_id: int):
    from agents.core.fixture_merger import normalize_oddalerts_fixture
    cache_key = f"fixture:{fixture_id}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached
    provider = get_provider()
    bundle = await provider.collect_fixture_data(fixture_id)
    if not bundle or "fixture" not in bundle:
        raise HTTPException(status_code=404, detail="Fixture not found")
    norm = normalize_oddalerts_fixture(bundle["fixture"]) or {}
    payload = {
        **norm,
        "odds_history": bundle.get("odds_history"),
        "h2h": bundle.get("h2h"),
        "stats_home": bundle.get("stats_home"),
        "stats_away": bundle.get("stats_away"),
        "trends": bundle.get("trends"),
    }
    _cache.set(cache_key, payload, ttl_seconds=300)
    return payload
```

- [ ] **Step 4: Run — expect PASS**

```bash
cd backend && python -m pytest ../tests/server/routes/test_browse.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/server/routes/browse.py tests/server/routes/test_browse.py
git commit -m "feat(api): /api/fixtures/{id} aggregated detail"
```

---

## Task 15: `/api/trends/{type}` + `/api/odds/dropping`

**Files:**
- Modify: `backend/server/routes/browse.py`
- Modify: `tests/server/routes/test_browse.py`

- [ ] **Step 1: Append failing tests**

```python
import pytest

@pytest.mark.parametrize("type_", ["home_win", "away_win", "btts"])
def test_trends_endpoint(client, type_):
    fake = {"data": [{"fixture_id": 1, "probability": 0.62}]}
    with patch("provider.oddalerts.client.OddAlertsProvider.get_trends",
               AsyncMock(return_value=fake)):
        r = client.get(f"/api/trends/{type_}")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_dropping_endpoint_filters_min_drop(client):
    fake = {"data": [
        {"fixture_id": 1, "drop_percentage": -8.5},
        {"fixture_id": 2, "drop_percentage": -3.0},
    ]}
    with patch("provider.oddalerts.client.OddAlertsProvider.get_dropping_odds",
               AsyncMock(return_value=fake)):
        r = client.get("/api/odds/dropping?min_drop=5")
    items = r.json()
    assert len(items) == 1
    assert items[0]["fixture_id"] == 1
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd backend && python -m pytest ../tests/server/routes/test_browse.py -v -k "trends or dropping"
```

- [ ] **Step 3: Add endpoints to `browse.py`**

```python
@router.get("/trends/{trend_type}")
async def get_trends(trend_type: str):
    allowed = {"home_win": "homeWin", "away_win": "awayWin", "btts": "btts", "over25": "over25"}
    if trend_type not in allowed:
        raise HTTPException(404, detail=f"Unknown trend type {trend_type}")
    cache_key = f"trends:{trend_type}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached
    provider = get_provider()
    raw = await provider.get_trends(trend_kind=allowed[trend_type])
    items = (raw or {}).get("data") or []
    _cache.set(cache_key, items, ttl_seconds=900)
    return items


@router.get("/odds/dropping")
async def get_dropping(
    market: Optional[str] = None,
    min_drop: float = Query(0.0, description="absolute % drop threshold"),
    window: str = Query("24h", regex="^(1h|6h|24h)$"),
):
    cache_key = f"dropping:{market or 'all'}:{min_drop}:{window}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached
    provider = get_provider()
    raw = await provider.get_dropping_odds()
    items = []
    for f in (raw or {}).get("data") or []:
        drop = abs(float(f.get("drop_percentage") or 0))
        if drop < min_drop:
            continue
        if market and f.get("market_key") != market:
            continue
        items.append(f)
    _cache.set(cache_key, items, ttl_seconds=300)
    return items
```

If `OddAlertsProvider.get_trends` signature differs (Task 1 audit will reveal it), adjust the `trend_kind=` keyword to match.

- [ ] **Step 4: Run — expect PASS**

```bash
cd backend && python -m pytest ../tests/server/routes/test_browse.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/server/routes/browse.py tests/server/routes/test_browse.py
git commit -m "feat(api): /api/trends/{type} and /api/odds/dropping"
```

---

## Task 16: `/api/teams/{id}` and `/api/leagues/{id}/standings`

**Files:**
- Modify: `backend/server/routes/browse.py`
- Modify: `tests/server/routes/test_browse.py`

- [ ] **Step 1: Append failing tests**

```python
def test_team_endpoint(client):
    fake = {"data": {"team_id": 11, "name": "Arsenal", "goals_for_avg": 2.1}}
    with patch("provider.oddalerts.client.OddAlertsProvider.get_stats",
               AsyncMock(return_value=fake)):
        r = client.get("/api/teams/11")
    assert r.status_code == 200
    assert r.json()["name"] == "Arsenal"


def test_standings_endpoint_returns_501_when_unsupported(client):
    r = client.get("/api/leagues/8/standings")
    assert r.status_code in (200, 501)
    if r.status_code == 200:
        assert isinstance(r.json(), list)
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd backend && python -m pytest ../tests/server/routes/test_browse.py -v -k "team or standings"
```

- [ ] **Step 3: Add endpoints**

```python
@router.get("/teams/{team_id}")
async def get_team(team_id: int):
    cache_key = f"team:{team_id}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached
    provider = get_provider()
    raw = await provider.get_stats(season_id=0, last_x="", id=team_id, type="season") \
        if hasattr(provider, "get_stats") else None
    if not raw or not raw.get("data"):
        raise HTTPException(404, detail="Team not found")
    payload = raw["data"]
    _cache.set(cache_key, payload, ttl_seconds=21_600)
    return payload


@router.get("/leagues/{league_id}/standings")
async def get_standings(league_id: int):
    # OddAlerts has no direct standings endpoint; return 501 until synthesis is built.
    raise HTTPException(status_code=501, detail="Standings synthesis not yet implemented")
```

If audit shows OddAlerts does expose standings, replace the 501 with the real call (cache TTL 21600s).

- [ ] **Step 4: Run — expect PASS**

```bash
cd backend && python -m pytest ../tests/server/routes/test_browse.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/server/routes/browse.py tests/server/routes/test_browse.py
git commit -m "feat(api): /api/teams/{id} and /api/leagues/{id}/standings stub"
```

---

## Task 17: `/api/analysis/recent` and `/api/analysis/run`

**Files:**
- Modify: `backend/server/routes/browse.py`
- Modify: `backend/agents/core/match_store.py` (add `list_recent` if missing)
- Modify: `backend/agents/core/orchestrator.py` (add `run_once` if missing)
- Modify: `tests/server/routes/test_browse.py`

- [ ] **Step 1: Audit `match_store` and `Orchestrator`**

```bash
grep -n "def list_recent\|def run_once" backend/agents/core/match_store.py backend/agents/core/orchestrator.py
```
Note which need to be added.

- [ ] **Step 2: Append failing tests**

```python
def test_analysis_recent_reads_match_store(client, monkeypatch):
    from agents.core import match_store
    monkeypatch.setattr(match_store, "list_recent",
                        lambda limit=10: [{"fixture_id": 1, "analysis": {"pick": "H", "ev": 0.064}}])
    r = client.get("/api/analysis/recent?limit=5")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["fixture_id"] == 1


def test_analysis_run_triggers_orchestrator(client, monkeypatch):
    called = {"flag": False}
    async def fake_run():
        called["flag"] = True
        return {"run_id": "0099", "status": "started"}
    monkeypatch.setattr("server.routes.browse._trigger_run", fake_run)
    r = client.post("/api/analysis/run")
    assert r.status_code == 200
    assert called["flag"]
    assert r.json()["run_id"] == "0099"
```

- [ ] **Step 3: Run — expect FAIL**

```bash
cd backend && python -m pytest ../tests/server/routes/test_browse.py -v -k "analysis"
```

- [ ] **Step 4: Add `list_recent` to `match_store.py` (if missing)**

```python
from pathlib import Path
import json
from typing import Any


_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "matches"


def list_recent(limit: int = 20) -> list[dict[str, Any]]:
    """Return up to `limit` recent match records sorted by analyzed_at desc."""
    if not _DATA_DIR.exists():
        return []
    files = sorted(_DATA_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    out: list[dict[str, Any]] = []
    for f in files[:limit]:
        try:
            out.append(json.loads(f.read_text()))
        except Exception:
            continue
    return out
```

- [ ] **Step 5: Add `run_once` to `Orchestrator` (if missing)**

In `backend/agents/core/orchestrator.py`, add (or rename existing entry point to):
```python
async def run_once(self) -> dict:
    """Execute one RD cycle. Returns {'run_id': str, 'status': str}."""
    run_id = self._next_run_id() if hasattr(self, "_next_run_id") else "manual"
    # Call existing per-stage runners. If the class already exposes a method
    # named differently (e.g., `run_cycle`), make `run_once` an alias.
    if hasattr(self, "run_cycle"):
        await self.run_cycle()
    elif hasattr(self, "run"):
        await self.run()
    return {"run_id": run_id, "status": "started"}
```

- [ ] **Step 6: Add endpoints to `browse.py`**

```python
async def _trigger_run() -> dict:
    from agents.core.orchestrator import Orchestrator
    orch = Orchestrator()
    return await orch.run_once()


@router.get("/analysis/recent")
async def get_analysis_recent(limit: int = Query(20, ge=1, le=200)):
    from agents.core import match_store
    return match_store.list_recent(limit=limit)


@router.post("/analysis/run")
async def post_analysis_run():
    return await _trigger_run()
```

- [ ] **Step 7: Run — expect PASS**

```bash
cd backend && python -m pytest ../tests/server/routes/test_browse.py -v
```

- [ ] **Step 8: Commit**

```bash
git add backend/server backend/agents/core tests/server
git commit -m "feat(api): /api/analysis/recent and /api/analysis/run"
```

---

## Task 18: Wire rate limiter into outbound OddAlerts calls

**Files:**
- Modify: `backend/provider/oddalerts/client.py`
- Test: `tests/provider/oddalerts/test_rate_limit_integration.py`

- [ ] **Step 1: Write failing test**

Create `tests/provider/oddalerts/test_rate_limit_integration.py`:
```python
import pytest
from unittest.mock import AsyncMock, patch
from provider.oddalerts.client import OddAlertsProvider


@pytest.mark.asyncio
async def test_provider_respects_token_bucket():
    p = OddAlertsProvider(api_key="x", rate_capacity=2, rate_refill_per_sec=0.0)
    with patch.object(p, "_request_raw", AsyncMock(return_value={"data": []})):
        await p.get_competitions(page=1)
        await p.get_competitions(page=2)
        with pytest.raises(RuntimeError):
            await p.get_competitions(page=3)
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd backend && python -m pytest ../tests/provider/oddalerts/test_rate_limit_integration.py -v
```

- [ ] **Step 3: Inject token bucket into `OddAlertsProvider.__init__`**

Open `backend/provider/oddalerts/client.py`. Modify `__init__`:
```python
from utils.rate_limit import TokenBucket

def __init__(
    self,
    api_key: str = "",
    timeout: float = DEFAULT_TIMEOUT,
    rate_capacity: int = 280,
    rate_refill_per_sec: float = 280 / 60,
):
    # existing assignments preserved
    self._bucket = TokenBucket(capacity=rate_capacity, refill_per_sec=rate_refill_per_sec)
```

- [ ] **Step 4: Gate `_request_raw`**

Add at the top of `_request_raw`:
```python
if not self._bucket.try_acquire():
    raise RuntimeError("OddAlerts rate limit exceeded; try again shortly")
```

Apply this *before* any network call. Optionally, callers that prefer waiting can use `await self._bucket.acquire()` instead — for v1, sync `try_acquire` + raise is fine (the HTTP layer can map it to 429).

- [ ] **Step 5: Run — expect PASS**

```bash
cd backend && python -m pytest ../tests/provider/oddalerts/test_rate_limit_integration.py -v
```

- [ ] **Step 6: Commit**

```bash
git add backend/provider/oddalerts/client.py tests/provider/oddalerts/test_rate_limit_integration.py
git commit -m "feat(provider): apply token-bucket rate limit to OddAlerts client"
```

---

## Task 19: Attach analytics output to `collect_all`

**Files:**
- Modify: `backend/agents/core/data_collector.py`
- Test: `tests/agents/core/test_data_collector_analytics.py`

- [ ] **Step 1: Write failing test**

Create `tests/agents/core/test_data_collector_analytics.py`:
```python
import pytest
from unittest.mock import AsyncMock, patch
from agents.core.data_collector import collect_all


@pytest.mark.asyncio
async def test_collect_all_attaches_analysis():
    bundle = {
        "fixture": {"id": 1, "name": "A vs B", "starting_at": "2026-05-14T20:00:00Z",
                    "participants": [
                        {"id": 11, "name": "A", "meta": {"location": "home"}},
                        {"id": 22, "name": "B", "meta": {"location": "away"}},
                    ], "league": {"id": 8, "name": "PL"}},
        "odds_history": {"markets": {"ft_result": {"Bet365": {
            "home": {"closing": 1.72}, "draw": {"closing": 3.85}, "away": {"closing": 4.60}}}}},
        "h2h": [],
        "stats_home": {"xg_for": 2.0, "goals_against_avg": 1.0},
        "stats_away": {"xg_for": 1.0, "goals_against_avg": 1.0},
        "trends": {"homeWin": 0.62, "awayWin": 0.18},
    }
    with patch("agents.core.data_collector.collect_oddalerts", AsyncMock(return_value=bundle)):
        out = await collect_all(oa_fixture_id=1)
    assert out["analysis"] is not None
    a = out["analysis"]
    assert "model_prob" in a and "H" in a["model_prob"]
    assert "ev" in a and "kelly" in a
    assert a["confidence_stars"] >= 0
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd backend && python -m pytest ../tests/agents/core/test_data_collector_analytics.py -v
```

- [ ] **Step 3: Extend `collect_all` in `backend/agents/core/data_collector.py`**

Replace the previous `collect_all` (from Task 9) with the analytics-aware version:
```python
async def collect_all(oa_fixture_id: int) -> Optional[dict[str, Any]]:
    bundle = await collect_oddalerts(oa_fixture_id)
    if not bundle or "fixture" not in bundle:
        return None
    return {
        "source": "oddalerts",
        "collected_at": _now_iso(),
        "fixture": bundle.get("fixture"),
        "odds_history": bundle.get("odds_history"),
        "h2h": bundle.get("h2h"),
        "stats_home": bundle.get("stats_home"),
        "stats_away": bundle.get("stats_away"),
        "trends": bundle.get("trends"),
        "analysis": _compute_analysis(bundle),
    }


def _compute_analysis(bundle: dict) -> Optional[dict]:
    from analytics.poisson import poisson_from_oddalerts
    from analytics.ev_calculator import ev_from_oddalerts
    from analytics.confidence import confidence_from_oddalerts

    sh = bundle.get("stats_home") or {}
    sa = bundle.get("stats_away") or {}
    odds = bundle.get("odds_history") or {}
    trends = bundle.get("trends") or {}

    poisson_out = poisson_from_oddalerts(sh, sa)
    if not poisson_out:
        return None

    model_probs = {
        "H": poisson_out["home_win_pct"] / 100.0,
        "D": poisson_out["draw_pct"] / 100.0,
        "A": poisson_out["away_win_pct"] / 100.0,
    }
    ev_out = ev_from_oddalerts(model_probs, odds)
    conf = confidence_from_oddalerts(model_probs, trends, odds_history_present=bool(odds))

    pick = max(model_probs, key=lambda k: model_probs[k])
    ev_pick = (ev_out or {}).get(pick) or {}

    return {
        "model_prob": model_probs,
        "market_prob": {k: (ev_out[k]["model_prob"] if ev_out else None) for k in ("H", "D", "A")},
        "pick": pick,
        "odds": ev_pick.get("odds"),
        "ev": ev_pick.get("ev"),
        "kelly": ev_pick.get("kelly"),
        "confidence_stars": conf["stars"],
        "analyst_summary": None,
        "reviewer_verdict": None,
        "run_id": None,
        "analyzed_at": _now_iso(),
    }
```

- [ ] **Step 4: Run — expect PASS**

```bash
cd backend && python -m pytest ../tests/agents/core/test_data_collector_analytics.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/agents/core/data_collector.py tests/agents/core/test_data_collector_analytics.py
git commit -m "feat(agents): attach analytics (poisson/EV/confidence) to collect_all output"
```

---

## Task 20: End-to-end smoke test of RD loop + final cleanup

**Files:**
- Create: `tests/integration/test_rd_smoke.py`

- [ ] **Step 1: Write integration test (mocked HTTP)**

Create `tests/integration/test_rd_smoke.py`:
```python
import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_one_rd_cycle_writes_match_store(tmp_path, monkeypatch):
    monkeypatch.setenv("GOALCAST_DATA_DIR", str(tmp_path))

    bundle = {
        "fixture": {"id": 1, "name": "A vs B", "starting_at": "2026-05-14T20:00:00Z",
                    "participants": [
                        {"id": 11, "name": "A", "meta": {"location": "home"}},
                        {"id": 22, "name": "B", "meta": {"location": "away"}},
                    ], "league": {"id": 8, "name": "PL"}},
        "odds_history": {"markets": {"ft_result": {"Bet365": {
            "home": {"closing": 1.72}, "draw": {"closing": 3.85}, "away": {"closing": 4.60}}}}},
        "h2h": [],
        "stats_home": {"xg_for": 2.0, "goals_against_avg": 1.0},
        "stats_away": {"xg_for": 1.0, "goals_against_avg": 1.0},
        "trends": {"homeWin": 0.62, "awayWin": 0.18},
    }
    with patch("provider.oddalerts.client.OddAlertsProvider.collect_fixture_data",
               AsyncMock(return_value=bundle)), \
         patch("provider.oddalerts.client.OddAlertsProvider.get_dropping_odds",
               AsyncMock(return_value={"data": [{"id": 1, "drop_percentage": -8.0,
                                                  "starting_at": "2026-05-14T20:00:00Z",
                                                  "league": {"id": 8, "name": "PL"}}]})):
        from agents.core.orchestrator import Orchestrator
        orch = Orchestrator()
        await orch.run_once()

    from agents.core import match_store
    recent = match_store.list_recent(limit=10)
    assert len(recent) >= 1
    assert recent[0].get("analysis") is not None
```

- [ ] **Step 2: Run — adjust until PASS**

```bash
cd backend && python -m pytest ../tests/integration/test_rd_smoke.py -v
```
If failing: trace the contract mismatch (analytics shape vs match_store write signature vs orchestrator method name) and fix.

- [ ] **Step 3: Full suite check**

```bash
cd backend && python -m pytest 2>&1 | tail -20
```
Expected: zero failures, zero `ImportError`. If any legacy test still fails because of a removed provider, delete that test or rewrite it to use the OddAlerts mock pattern.

- [ ] **Step 4: Ruff check**

```bash
cd backend && python -m ruff check . 2>&1 | tail -20
```
Fix any new lint issues. Common ones after this pivot: unused imports left behind in `provider/__init__.py` or stale `# noqa` comments referencing deleted modules.

- [ ] **Step 5: Commit**

```bash
git add tests/integration/
git commit -m "test: e2e smoke covering OddAlerts → analytics → match_store"
```

- [ ] **Step 6: Update plan tracking**

Mark Plan 1 complete. Frontend changes follow in `2026-05-14-frontend-pivot-plan.md`.

---

## Self-Review

**Spec coverage:**
- §3.2 backend module changes — Tasks 2-9 cover every row.
- §3.3 HTTP API table — Tasks 12-17 cover all 9 endpoints.
- §6 Phase 1 (裁剪) — Task 2.
- §6 Phase 2 (analytics 适配) — Tasks 5-8.
- §6 Phase 3 (HTTP API + cache + rate limit) — Tasks 10-17 + Task 18.
- §6 Phase 4 (agent 单源化 + analytics 接入) — Tasks 4, 9, 19, 20.
- §7 `MatchRecord.analysis` field — Task 9 Step 5.
- §8 risk "analytics 旧入参不匹配 → 跳过" — implemented via `_compute_analysis` early `return None`.

**Type consistency:**
- `poisson_from_oddalerts` / `ev_from_oddalerts` / `confidence_from_oddalerts` signatures match between Tasks 5-8 and Task 19's `_compute_analysis`.
- `match_store.list_recent(limit=N)` matches between Tasks 17 and 20.
- `Orchestrator.run_once()` is the agreed entry-point in Tasks 17 and 20.

**Caveat:** Task 17 Step 5 conditional on existing `Orchestrator` method names. The audit in Step 1 of Task 17 is the gate.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-14-backend-pivot-plan.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using `superpowers:executing-plans`, batch execution with checkpoints.

**Which approach?**

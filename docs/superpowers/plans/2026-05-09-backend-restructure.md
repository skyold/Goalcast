# 后端架构重构实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**目标：** 将 Goalcast 后端从 5-loop 多 agent 系统重构为清晰的三层 Pipeline 架构，唯一 LLM agent 为 Analyst。

**架构：** Provider Registry 统一管理数据源开关，Pipeline Runner 顺序执行 discover→collect→analyze，Match Store 统一文件格式消除双写。

**技术栈：** Python 3.11+、FastAPI、httpx、asyncio、pytest、thefuzz

---

## 文件变更总览

**新建：**
- `backend/config/providers.json`
- `backend/provider/registry.py`
- `backend/store/__init__.py`
- `backend/store/match_store.py`
- `backend/pipeline/__init__.py`
- `backend/pipeline/discovery.py`
- `backend/pipeline/collector.py`
- `backend/pipeline/runner.py`
- `backend/pipeline/scheduler.py`
- `backend/pipeline/league_resolver.py`
- `backend/agents/analyst.py`
- `backend/scripts/migrate_matches.py`
- `backend/tests/provider/test_registry.py`
- `backend/tests/store/test_match_store.py`
- `backend/tests/pipeline/test_discovery.py`
- `backend/tests/pipeline/test_collector.py`
- `backend/tests/pipeline/test_runner.py`

**修改：**
- `backend/provider/base.py` — 新增 `collect_match()` 抽象方法
- `backend/provider/oddalerts/client.py` — 实现 `collect_match()`
- `backend/provider/sportmonks/client.py` — 实现 `collect_match()`
- `backend/provider/footystats/client.py` — 实现空 `collect_match()`
- `backend/provider/understat/client.py` — 实现空 `collect_match()`
- `backend/server/server.py` — 更新路由注册
- `backend/server/routes/pipeline.py` — 完全重写
- `backend/server/routes/config.py` — 完全重写

**删除（最后一个任务统一处理）：**
- `backend/agents/core/orchestrator.py`
- `backend/agents/core/pipeline.py`
- `backend/agents/core/blackboard.py`
- `backend/agents/core/data_collector.py`
- `backend/agents/core/directory_agent.py`
- `backend/agents/core/events.py`
- `backend/agents/core/league_config.py`
- `backend/agents/roles/trader/`
- `backend/agents/roles/reviewer/`（如存在）
- `backend/agents/roles/reporter/`（如存在）
- `backend/agents/roles/backtester/`
- `backend/datasource/`
- `backend/mcp_server/`
- `backend/server/routes/agents.py`
- `backend/server/routes/board.py`
- `backend/server/routes/chat.py`

---

## Task 1：Provider Registry

**文件：**
- 新建：`backend/config/providers.json`
- 新建：`backend/provider/registry.py`
- 新建：`backend/tests/provider/__init__.py`
- 新建：`backend/tests/provider/test_registry.py`

- [ ] **步骤 1：写失败测试**

新建 `backend/tests/provider/__init__.py`（空文件），然后：

```python
# backend/tests/provider/test_registry.py
import json
import pytest
from pathlib import Path
from unittest.mock import patch


def test_get_active_providers_returns_enabled_only(tmp_path):
    cfg = {
        "analyst": {"enabled": True},
        "schedule": {"interval_hours": 1},
        "providers": {
            "oddalerts": {"enabled": True},
            "sportmonks": {"enabled": False},
            "footystats": {"enabled": False},
            "understat": {"enabled": False},
        },
    }
    cfg_file = tmp_path / "providers.json"
    cfg_file.write_text(json.dumps(cfg), encoding="utf-8")

    with patch("provider.registry._CONFIG_PATH", cfg_file):
        from provider.registry import get_active_providers
        providers = get_active_providers()

    names = [p.name for p in providers]
    assert names == ["oddalerts"]


def test_set_provider_enabled_persists(tmp_path):
    cfg = {
        "analyst": {"enabled": True},
        "schedule": {"interval_hours": 1},
        "providers": {"oddalerts": {"enabled": False}},
    }
    cfg_file = tmp_path / "providers.json"
    cfg_file.write_text(json.dumps(cfg), encoding="utf-8")

    with patch("provider.registry._CONFIG_PATH", cfg_file):
        from provider import registry
        registry.set_provider_enabled("oddalerts", True)
        result = json.loads(cfg_file.read_text())

    assert result["providers"]["oddalerts"]["enabled"] is True


def test_is_analyst_enabled(tmp_path):
    cfg = {"analyst": {"enabled": False}, "schedule": {"interval_hours": 1}, "providers": {}}
    cfg_file = tmp_path / "providers.json"
    cfg_file.write_text(json.dumps(cfg), encoding="utf-8")

    with patch("provider.registry._CONFIG_PATH", cfg_file):
        from provider.registry import is_analyst_enabled
        assert is_analyst_enabled() is False


def test_get_schedule_hours(tmp_path):
    cfg = {"analyst": {"enabled": True}, "schedule": {"interval_hours": 3}, "providers": {}}
    cfg_file = tmp_path / "providers.json"
    cfg_file.write_text(json.dumps(cfg), encoding="utf-8")

    with patch("provider.registry._CONFIG_PATH", cfg_file):
        from provider.registry import get_schedule_hours
        assert get_schedule_hours() == 3
```

- [ ] **步骤 2：运行测试确认失败**

```bash
cd backend && python -m pytest tests/provider/test_registry.py -v
```

期望：`ModuleNotFoundError: No module named 'provider.registry'`

- [ ] **步骤 3：新建 `backend/config/providers.json`**

```json
{
  "analyst": { "enabled": true },
  "schedule": { "interval_hours": 1 },
  "providers": {
    "oddalerts":  { "enabled": true },
    "sportmonks": { "enabled": true },
    "footystats":  { "enabled": false },
    "understat":   { "enabled": false }
  }
}
```

- [ ] **步骤 4：新建 `backend/provider/registry.py`**

```python
from __future__ import annotations

import json
from pathlib import Path

from provider.base import BaseProvider

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "providers.json"


def _load() -> dict:
    try:
        return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "analyst": {"enabled": True},
            "schedule": {"interval_hours": 1},
            "providers": {},
        }


def _save(cfg: dict) -> None:
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def get_config() -> dict:
    return _load()


def get_active_providers() -> list[BaseProvider]:
    cfg = _load()
    pcfg = cfg.get("providers", {})
    active: list[BaseProvider] = []
    if pcfg.get("oddalerts", {}).get("enabled", False):
        from provider.oddalerts.client import OddAlertsProvider
        active.append(OddAlertsProvider())
    if pcfg.get("sportmonks", {}).get("enabled", False):
        from provider.sportmonks.client import SportmonksProvider
        active.append(SportmonksProvider())
    if pcfg.get("footystats", {}).get("enabled", False):
        from provider.footystats.client import FootyStatsProvider
        active.append(FootyStatsProvider())
    if pcfg.get("understat", {}).get("enabled", False):
        from provider.understat.client import UnderstatProvider
        active.append(UnderstatProvider())
    return active


def is_analyst_enabled() -> bool:
    return _load().get("analyst", {}).get("enabled", True)


def get_schedule_hours() -> int:
    return int(_load().get("schedule", {}).get("interval_hours", 1))


def set_provider_enabled(name: str, enabled: bool) -> None:
    cfg = _load()
    cfg.setdefault("providers", {}).setdefault(name, {})["enabled"] = enabled
    _save(cfg)


def set_analyst_enabled(enabled: bool) -> None:
    cfg = _load()
    cfg.setdefault("analyst", {})["enabled"] = enabled
    _save(cfg)


def set_schedule_hours(hours: int) -> None:
    cfg = _load()
    cfg.setdefault("schedule", {})["interval_hours"] = hours
    _save(cfg)
```

- [ ] **步骤 5：运行测试确认通过**

```bash
cd backend && python -m pytest tests/provider/test_registry.py -v
```

期望：4 个测试全部 PASS

- [ ] **步骤 6：提交**

```bash
git add backend/config/providers.json backend/provider/registry.py \
        backend/tests/provider/__init__.py backend/tests/provider/test_registry.py
git commit -m "feat(registry): 新增 Provider Registry，统一管理数据源开关"
```

---

## Task 2：BaseProvider 新增 collect_match + OddAlerts 实现

**文件：**
- 修改：`backend/provider/base.py`
- 修改：`backend/provider/oddalerts/client.py`

- [ ] **步骤 1：修改 `backend/provider/base.py`，新增抽象方法**

在文件末尾（`__repr__` 之前）添加：

```python
    @abstractmethod
    async def collect_match(self, provider_fixture_id: int) -> dict | None:
        """收集单场比赛的完整数据包。

        Args:
            provider_fixture_id: 该 provider 自己体系的 fixture ID。

        Returns:
            dict with `_meta` key plus provider-specific data, or None if unavailable.
        """
        pass
```

- [ ] **步骤 2：在 `backend/provider/oddalerts/client.py` 末尾添加 `collect_match()`**

将 `backend/agents/core/data_collector.py` 中 `collect_oddalerts()` 的逻辑移入此方法：

```python
    async def collect_match(self, provider_fixture_id: int) -> dict | None:
        """收集 OddAlerts 单场比赛完整数据包。"""
        from datetime import datetime, timedelta, timezone
        _CST = timezone(timedelta(hours=8))

        if not await self.is_available():
            return None

        def _now_iso() -> str:
            return datetime.now(_CST).isoformat()

        def _extract_team(stats_resp: object, team_id: object) -> dict | None:
            if not isinstance(stats_resp, dict):
                return None
            rows = stats_resp.get("data") or []
            if not isinstance(rows, list):
                return None
            for row in rows:
                if isinstance(row, dict) and row.get("team_id") == team_id:
                    return row
            return None

        try:
            fixture, odds, stats, predictions, fixture_h2h = await asyncio.gather(
                self.get_fixture(provider_fixture_id),
                self.get_odds_history(provider_fixture_id),
                self.get_stats("fixture", provider_fixture_id),
                self.get_predictions_generate(provider_fixture_id),
                self.get_fixture_h2h(provider_fixture_id),
                return_exceptions=True,
            )

            result: dict = {
                "_meta": {
                    "collected_at": _now_iso(),
                    "oa_fixture_id": provider_fixture_id,
                }
            }

            if isinstance(fixture, dict):
                result["fixture"] = fixture
            if isinstance(odds, dict):
                result["odds_history"] = odds
            if isinstance(stats, dict):
                result["stats"] = stats
            if isinstance(predictions, dict):
                result["predictions"] = predictions
            if isinstance(fixture_h2h, dict):
                h2h_list = fixture_h2h.get("h2h") or []
                result["h2h"] = h2h_list[:6]
                if fixture_h2h.get("correct_scores"):
                    result["correct_scores"] = fixture_h2h["correct_scores"]

            if len(result) == 1:
                logger.warning("[OddAlerts] fixture %d 未返回任何数据", provider_fixture_id)
                return None

            season_id = isinstance(fixture, dict) and fixture.get("season_id")
            home_id = isinstance(fixture, dict) and fixture.get("home_id")
            away_id = isinstance(fixture, dict) and fixture.get("away_id")

            if season_id and home_id and away_id:
                home5h_resp, away5a_resp, overall10_resp = await asyncio.gather(
                    self.get_stats_recent(season_id, "5_home"),
                    self.get_stats_recent(season_id, "5_away"),
                    self.get_stats_recent(season_id, "10_overall"),
                    return_exceptions=True,
                )
                recent: dict = {}
                home5h = _extract_team(home5h_resp, home_id)
                away5a = _extract_team(away5a_resp, away_id)
                home10 = _extract_team(overall10_resp, home_id)
                away10 = _extract_team(overall10_resp, away_id)
                if home5h:
                    recent["home_5h"] = home5h
                if away5a:
                    recent["away_5a"] = away5a
                if home10:
                    recent["home_10"] = home10
                if away10:
                    recent["away_10"] = away10
                if recent:
                    result["recent_stats"] = recent

            return result

        except Exception as exc:
            logger.warning("[OddAlerts] collect_match 失败 fixture_id=%d: %s", provider_fixture_id, exc)
            return None
```

注意：`OddAlertsProvider` 已有 `asyncio` 导入，但如未导入需在文件顶部添加 `import asyncio`。

- [ ] **步骤 3：在 FootyStats 和 Understat 中添加空实现**

`backend/provider/footystats/client.py` 末尾添加：
```python
    async def collect_match(self, provider_fixture_id: int) -> dict | None:
        return None
```

`backend/provider/understat/client.py` 末尾添加：
```python
    async def collect_match(self, provider_fixture_id: int) -> dict | None:
        return None
```

- [ ] **步骤 4：快速验证没有语法错误**

```bash
cd backend && python -c "from provider.oddalerts.client import OddAlertsProvider; print('OK')"
cd backend && python -c "from provider.base import BaseProvider; print('OK')"
```

- [ ] **步骤 5：提交**

```bash
git add backend/provider/base.py backend/provider/oddalerts/client.py \
        backend/provider/footystats/client.py backend/provider/understat/client.py
git commit -m "feat(provider): BaseProvider 新增 collect_match 抽象方法，OddAlerts 实现迁移"
```

---

## Task 3：Sportmonks 实现 collect_match

**文件：**
- 修改：`backend/provider/sportmonks/client.py`

- [ ] **步骤 1：在 `backend/provider/sportmonks/client.py` 末尾添加 `collect_match()`**

```python
    async def collect_match(self, provider_fixture_id: int) -> dict | None:
        """收集 Sportmonks 单场比赛完整数据包。

        使用 includes 一次请求获取：participants、scores、statistics、
        odds、league、season、state、events。
        """
        from datetime import datetime, timedelta, timezone
        _CST = timezone(timedelta(hours=8))

        if not await self.is_available():
            return None

        includes = (
            "participants;"
            "scores;"
            "statistics;"
            "odds;"
            "league;"
            "season;"
            "state;"
            "events"
        )
        try:
            resp = await self.get_fixture_by_id(provider_fixture_id, include=includes)
        except Exception as exc:
            logger.warning("[Sportmonks] collect_match 请求失败 fixture_id=%d: %s", provider_fixture_id, exc)
            return None

        if not isinstance(resp, dict):
            return None

        data = resp.get("data", {})
        if not data:
            return None

        return {
            "_meta": {
                "collected_at": datetime.now(_CST).isoformat(),
                "fixture_id": provider_fixture_id,
            },
            **data,
        }
```

- [ ] **步骤 2：验证语法**

```bash
cd backend && python -c "from provider.sportmonks.client import SportmonksProvider; print('OK')"
```

- [ ] **步骤 3：提交**

```bash
git add backend/provider/sportmonks/client.py
git commit -m "feat(provider): Sportmonks 实现 collect_match，直接 HTTP 调用替代 ToolExecutor"
```

---

## Task 4：统一 Match Store

**文件：**
- 新建：`backend/store/__init__.py`
- 新建：`backend/store/match_store.py`
- 新建：`backend/tests/store/__init__.py`
- 新建：`backend/tests/store/test_match_store.py`

- [ ] **步骤 1：写失败测试**

```python
# backend/tests/store/test_match_store.py
import json
import pytest
from pathlib import Path
from unittest.mock import patch


def _make_store(tmp_path):
    matches_dir = tmp_path / "matches"
    with patch("store.match_store.MATCHES_DIR", matches_dir):
        from store import match_store
        return match_store, matches_dir


def test_save_and_get(tmp_path):
    match_store, _ = _make_store(tmp_path)
    record = {
        "match_id": "MC-TEST-001",
        "status": "pending",
        "metadata": {
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "league": "Premier League",
            "kickoff_time": "2025-05-10 20:00:00",
            "provider_ids": {"sportmonks": 100},
            "collected_at": None,
        },
        "raw_data": {},
        "analysis": {},
    }
    match_store.save(record)
    loaded = match_store.get("MC-TEST-001")
    assert loaded["match_id"] == "MC-TEST-001"
    assert loaded["status"] == "pending"


def test_update_status(tmp_path):
    match_store, _ = _make_store(tmp_path)
    record = {
        "match_id": "MC-TEST-002",
        "status": "pending",
        "metadata": {"home_team": "A", "away_team": "B", "league": "", "kickoff_time": "", "provider_ids": {}, "collected_at": None},
        "raw_data": {},
        "analysis": {},
    }
    match_store.save(record)
    match_store.update("MC-TEST-002", {"status": "collected"})
    assert match_store.get("MC-TEST-002")["status"] == "collected"


def test_list_matches_filter_by_status(tmp_path):
    match_store, _ = _make_store(tmp_path)
    for i, status in enumerate(["pending", "collected", "analyzed"]):
        match_store.save({
            "match_id": f"MC-TEST-{i:03d}",
            "status": status,
            "metadata": {"home_team": "A", "away_team": "B", "league": "PL", "kickoff_time": "2025-05-10 20:00:00", "provider_ids": {}, "collected_at": None},
            "raw_data": {},
            "analysis": {},
        })
    result = match_store.list_matches(status="collected")
    assert len(result) == 1
    assert result[0]["status"] == "collected"


def test_list_matches_filter_by_date(tmp_path):
    match_store, _ = _make_store(tmp_path)
    for date in ["2025-05-09 20:00:00", "2025-05-10 20:00:00", "2025-05-11 20:00:00"]:
        mid = f"MC-{date[:10].replace('-', '')}-001"
        match_store.save({
            "match_id": mid,
            "status": "collected",
            "metadata": {"home_team": "A", "away_team": "B", "league": "PL", "kickoff_time": date, "provider_ids": {}, "collected_at": None},
            "raw_data": {},
            "analysis": {},
        })
    result = match_store.list_matches(date="2025-05-10")
    assert len(result) == 1
    assert result[0]["metadata"]["kickoff_time"] == "2025-05-10 20:00:00"


def test_get_returns_none_for_missing(tmp_path):
    match_store, _ = _make_store(tmp_path)
    assert match_store.get("MC-NOTEXIST") is None
```

- [ ] **步骤 2：运行测试确认失败**

```bash
cd backend && python -m pytest tests/store/test_match_store.py -v
```

期望：`ModuleNotFoundError: No module named 'store'`

- [ ] **步骤 3：新建 `backend/store/__init__.py`**（空文件）

- [ ] **步骤 4：新建 `backend/store/match_store.py`**

```python
"""
统一 Match Store。
每场比赛一个 JSON 文件，单一写入路径，无双写。

状态转换：pending → collected → analyzed / error
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from config.settings import DATA_DIR

logger = logging.getLogger(__name__)

MATCHES_DIR = DATA_DIR / "matches"
_CST = timezone(timedelta(hours=8))


def _now_iso() -> str:
    return datetime.now(_CST).isoformat()


def generate_match_id() -> str:
    ts = datetime.now(_CST).strftime("%Y%m%d-%H%M%S")
    uid = uuid.uuid4().hex[:6].upper()
    return f"MC-{ts}-{uid}"


def _write(record: dict) -> None:
    MATCHES_DIR.mkdir(parents=True, exist_ok=True)
    fp = MATCHES_DIR / f"{record['match_id']}.json"
    fp.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")


def save(record: dict) -> str:
    """写入新比赛记录。record 必须包含 match_id 字段。"""
    _write(record)
    logger.info("[MatchStore] 保存: %s", record["match_id"])
    return record["match_id"]


def get(match_id: str) -> dict | None:
    fp = MATCHES_DIR / f"{match_id}.json"
    if not fp.exists():
        return None
    try:
        return json.loads(fp.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.warning("[MatchStore] JSON 损坏: %s", match_id)
        return None


def update(match_id: str, fields: dict) -> None:
    """局部更新 match 的顶层字段。fields 是要合并的键值对。"""
    record = get(match_id)
    if record is None:
        logger.warning("[MatchStore] 更新目标不存在: %s", match_id)
        return
    record.update(fields)
    _write(record)
    logger.debug("[MatchStore] 更新: %s fields=%s", match_id, list(fields.keys()))


def list_matches(
    league: str | None = None,
    date: str | None = None,
    status: str | None = None,
) -> list[dict]:
    """返回所有 match，支持按 league/date/status 过滤。date 格式 YYYY-MM-DD。"""
    MATCHES_DIR.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    for fp in sorted(MATCHES_DIR.glob("MC-*.json")):
        try:
            record = json.loads(fp.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue

        if status and record.get("status") != status:
            continue

        meta = record.get("metadata", {})
        if league and meta.get("league", "") != league:
            continue
        if date:
            kt = str(meta.get("kickoff_time", ""))
            if not kt.startswith(date):
                continue

        results.append(record)
    return results


def exists_for_fixture(provider_name: str, fixture_id: int) -> str | None:
    """如果已存在对应 fixture 的 match，返回其 match_id，否则返回 None。"""
    for fp in MATCHES_DIR.glob("MC-*.json"):
        try:
            record = json.loads(fp.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        pids = record.get("metadata", {}).get("provider_ids", {})
        if pids.get(provider_name) == fixture_id:
            return record.get("match_id")
    return None
```

- [ ] **步骤 5：运行测试确认通过**

```bash
cd backend && python -m pytest tests/store/test_match_store.py -v
```

期望：5 个测试全部 PASS

- [ ] **步骤 6：提交**

```bash
git add backend/store/__init__.py backend/store/match_store.py \
        backend/tests/store/__init__.py backend/tests/store/test_match_store.py
git commit -m "feat(store): 新增统一 Match Store，单一写入路径，消除双写"
```

---

## Task 5：Pipeline Discovery

**文件：**
- 新建：`backend/pipeline/__init__.py`
- 新建：`backend/pipeline/discovery.py`
- 新建：`backend/tests/pipeline/__init__.py`
- 新建：`backend/tests/pipeline/test_discovery.py`

- [ ] **步骤 1：写失败测试**

```python
# backend/tests/pipeline/test_discovery.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from provider.models import ProviderFixture


def _make_fixture(provider: str, fid: int, home: str, away: str, ts: int) -> ProviderFixture:
    return ProviderFixture(
        provider=provider, fixture_id=fid,
        home_team=home, away_team=away,
        kickoff_unix=ts, league_name="Test League",
    )


@pytest.mark.asyncio
async def test_discover_merges_two_providers():
    ts = 1715000000
    prov_a = MagicMock()
    prov_a.name = "oddalerts"
    prov_a.discover_fixtures = AsyncMock(return_value=[
        _make_fixture("oddalerts", 1, "Arsenal", "Chelsea", ts),
    ])
    prov_a.close = AsyncMock()

    prov_b = MagicMock()
    prov_b.name = "sportmonks"
    prov_b.discover_fixtures = AsyncMock(return_value=[
        _make_fixture("sportmonks", 99, "Arsenal", "Chelsea", ts),
    ])
    prov_b.close = AsyncMock()

    with patch("pipeline.discovery.registry.get_active_providers", return_value=[prov_a, prov_b]):
        from pipeline.discovery import discover_fixtures
        results = await discover_fixtures(dates=["2025-05-10"])

    assert len(results) == 1
    assert results[0].provider_ids == {"oddalerts": 1, "sportmonks": 99}


@pytest.mark.asyncio
async def test_discover_no_providers_returns_empty():
    with patch("pipeline.discovery.registry.get_active_providers", return_value=[]):
        from pipeline.discovery import discover_fixtures
        results = await discover_fixtures(dates=["2025-05-10"])
    assert results == []


@pytest.mark.asyncio
async def test_discover_provider_failure_is_skipped():
    ts = 1715000000
    prov_a = MagicMock()
    prov_a.name = "oddalerts"
    prov_a.discover_fixtures = AsyncMock(side_effect=Exception("API down"))
    prov_a.close = AsyncMock()

    prov_b = MagicMock()
    prov_b.name = "sportmonks"
    prov_b.discover_fixtures = AsyncMock(return_value=[
        _make_fixture("sportmonks", 99, "Arsenal", "Chelsea", ts),
    ])
    prov_b.close = AsyncMock()

    with patch("pipeline.discovery.registry.get_active_providers", return_value=[prov_a, prov_b]):
        from pipeline.discovery import discover_fixtures
        results = await discover_fixtures(dates=["2025-05-10"])

    assert len(results) == 1
    assert "sportmonks" in results[0].provider_ids
```

- [ ] **步骤 2：运行测试确认失败**

```bash
cd backend && python -m pytest tests/pipeline/test_discovery.py -v
```

- [ ] **步骤 3：新建 `backend/pipeline/__init__.py`**（空文件）和 `backend/tests/pipeline/__init__.py`（空文件）

- [ ] **步骤 4：新建 `backend/pipeline/discovery.py`**

```python
"""
从所有激活的 provider 并行拉取 fixtures，合并去重。
"""
from __future__ import annotations

import asyncio
import logging

from provider import registry
from provider.models import UnifiedFixture
from agents.core.fixture_merger import merge_fixtures

logger = logging.getLogger(__name__)


async def discover_fixtures(
    dates: list[str],
    league_ids_by_provider: dict[str, list[int]] | None = None,
) -> list[UnifiedFixture]:
    """
    从所有激活 provider 并行发现 fixtures，合并去重。

    Args:
        dates: ISO 日期字符串列表，如 ["2025-05-10", "2025-05-11"]
        league_ids_by_provider: 各 provider 的联赛 ID 过滤，如
            {"sportmonks": [271], "oddalerts": [8]}。
            None 或 key 不存在时不过滤。

    Returns:
        合并去重后的 UnifiedFixture 列表。
    """
    providers = registry.get_active_providers()
    if not providers:
        logger.info("[Discovery] 无激活 provider，跳过")
        return []

    league_ids_by_provider = league_ids_by_provider or {}

    async def _discover_one(provider):
        league_ids = league_ids_by_provider.get(provider.name, [])
        try:
            fixtures = await provider.discover_fixtures(league_ids, dates)
            logger.info("[Discovery] %s 发现 %d 场", provider.name, len(fixtures))
            return provider.name, fixtures
        except Exception as exc:
            logger.warning("[Discovery] %s 失败: %s", provider.name, exc)
            return provider.name, []
        finally:
            try:
                await provider.close()
            except Exception:
                pass

    results = await asyncio.gather(*[_discover_one(p) for p in providers])
    unified = merge_fixtures([(name, fixtures) for name, fixtures in results if fixtures])
    logger.info("[Discovery] 合并后共 %d 场", len(unified))
    return unified
```

- [ ] **步骤 5：运行测试确认通过**

```bash
cd backend && python -m pytest tests/pipeline/test_discovery.py -v
```

- [ ] **步骤 6：提交**

```bash
git add backend/pipeline/__init__.py backend/pipeline/discovery.py \
        backend/tests/pipeline/__init__.py backend/tests/pipeline/test_discovery.py
git commit -m "feat(pipeline): 新增 discovery 模块，并行 fixture 发现与合并"
```

---

## Task 6：Pipeline Collector

**文件：**
- 新建：`backend/pipeline/collector.py`
- 新建：`backend/tests/pipeline/test_collector.py`

- [ ] **步骤 1：写失败测试**

```python
# backend/tests/pipeline/test_collector.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_collect_returns_data_keyed_by_provider():
    prov = MagicMock()
    prov.name = "oddalerts"
    prov.collect_match = AsyncMock(return_value={"_meta": {}, "fixture": {"id": 1}})
    prov.close = AsyncMock()

    with patch("pipeline.collector.registry.get_active_providers", return_value=[prov]):
        from pipeline.collector import collect_match_data
        result = await collect_match_data({"oddalerts": 1})

    assert "oddalerts" in result
    assert result["oddalerts"]["fixture"]["id"] == 1


@pytest.mark.asyncio
async def test_collect_skips_provider_not_in_ids():
    prov = MagicMock()
    prov.name = "sportmonks"
    prov.collect_match = AsyncMock(return_value={"_meta": {}})
    prov.close = AsyncMock()

    with patch("pipeline.collector.registry.get_active_providers", return_value=[prov]):
        from pipeline.collector import collect_match_data
        result = await collect_match_data({"oddalerts": 1})

    assert "sportmonks" not in result


@pytest.mark.asyncio
async def test_collect_provider_failure_excluded():
    prov = MagicMock()
    prov.name = "oddalerts"
    prov.collect_match = AsyncMock(side_effect=Exception("timeout"))
    prov.close = AsyncMock()

    with patch("pipeline.collector.registry.get_active_providers", return_value=[prov]):
        from pipeline.collector import collect_match_data
        result = await collect_match_data({"oddalerts": 1})

    assert result == {}
```

- [ ] **步骤 2：运行测试确认失败**

```bash
cd backend && python -m pytest tests/pipeline/test_collector.py -v
```

- [ ] **步骤 3：新建 `backend/pipeline/collector.py`**

```python
"""
从所有激活 provider 并行收集单场比赛数据。
"""
from __future__ import annotations

import asyncio
import logging

from provider import registry

logger = logging.getLogger(__name__)


async def collect_match_data(provider_ids: dict[str, int]) -> dict:
    """
    并行从所有激活 provider 收集单场比赛数据。

    Args:
        provider_ids: 各 provider 的 fixture ID 映射，
                      如 {"sportmonks": 18329, "oddalerts": 54201}。
                      provider 在此 dict 中无对应 key 时跳过。

    Returns:
        raw_data dict，结构为 {provider_name: {_meta, ...数据}}
    """
    providers = registry.get_active_providers()

    async def _collect_one(provider):
        pid = provider_ids.get(provider.name)
        if pid is None:
            return provider.name, None
        try:
            data = await provider.collect_match(pid)
            return provider.name, data
        except Exception as exc:
            logger.warning("[Collector] %s 收集失败 fixture_id=%s: %s", provider.name, pid, exc)
            return provider.name, None
        finally:
            try:
                await provider.close()
            except Exception:
                pass

    results = await asyncio.gather(*[_collect_one(p) for p in providers])
    return {name: data for name, data in results if data is not None}
```

- [ ] **步骤 4：运行测试确认通过**

```bash
cd backend && python -m pytest tests/pipeline/test_collector.py -v
```

- [ ] **步骤 5：提交**

```bash
git add backend/pipeline/collector.py backend/tests/pipeline/test_collector.py
git commit -m "feat(pipeline): 新增 collector 模块，并行从各 provider 收集比赛数据"
```

---

## Task 7：League Resolver（替换 LLM 匹配）

**文件：**
- 新建：`backend/pipeline/league_resolver.py`

- [ ] **步骤 1：安装 thefuzz**

```bash
cd backend && pip install thefuzz python-Levenshtein
```

在 `backend/requirements.txt` 中添加：
```
thefuzz>=0.22.1
python-Levenshtein>=0.25.0
```

- [ ] **步骤 2：新建 `backend/pipeline/league_resolver.py`**

```python
"""
联赛名称模糊匹配，将用户输入映射到各 provider 的联赛 ID。
替代旧的 LLM 匹配方案。
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from thefuzz import process

logger = logging.getLogger(__name__)

_SM_LEAGUES_PATH = Path(__file__).resolve().parent.parent / "config" / "sportmonks_leagues.json"
_OA_LEAGUES_PATH = Path(__file__).resolve().parent.parent / "config" / "oddalerts_leagues.json"


def _load_sm_leagues() -> dict:
    if not _SM_LEAGUES_PATH.exists():
        return {}
    try:
        return json.loads(_SM_LEAGUES_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, IOError):
        return {}


def _load_oa_mapping() -> dict[str, int | None]:
    if not _OA_LEAGUES_PATH.exists():
        return {}
    try:
        cfg = json.loads(_OA_LEAGUES_PATH.read_text(encoding="utf-8"))
        return cfg.get("_sportmonks_to_oddalerts", {})
    except (json.JSONDecodeError, IOError):
        return {}


def resolve_league_ids(
    league_names: list[str],
    score_cutoff: int = 70,
) -> dict[str, list[int]]:
    """
    将联赛名称列表模糊匹配到各 provider 的联赛 ID。

    Args:
        league_names: 用户输入的联赛名称列表，支持中英文
        score_cutoff: 最低匹配分数 (0-100)，低于此值视为未匹配

    Returns:
        {
            "sportmonks": [271, 8],
            "oddalerts":  [4, 2],
        }
    """
    sm_dict = _load_sm_leagues()
    if not sm_dict:
        return {"sportmonks": [], "oddalerts": []}

    # 建立候选名称 → SM ID 的映射
    candidates: dict[str, int] = {}
    for key, info in sm_dict.items():
        sm_id = info.get("id") if isinstance(info, dict) else None
        if sm_id is None:
            continue
        name = info.get("name", "") if isinstance(info, dict) else ""
        cn = info.get("chinese_name", "") if isinstance(info, dict) else ""
        if name:
            candidates[name] = sm_id
        if cn:
            candidates[cn] = sm_id

    if not candidates:
        return {"sportmonks": [], "oddalerts": []}

    oa_mapping = _load_oa_mapping()
    sm_ids: list[int] = []
    oa_ids: list[int] = []

    for query in league_names:
        if str(query).isdigit():
            sm_id = int(query)
            sm_ids.append(sm_id)
            oa_id = oa_mapping.get(str(sm_id))
            if isinstance(oa_id, int):
                oa_ids.append(oa_id)
            continue

        match = process.extractOne(query, candidates.keys(), score_cutoff=score_cutoff)
        if match is None:
            logger.warning("[LeagueResolver] 未匹配: %r", query)
            continue

        matched_name, score, _ = match
        sm_id = candidates[matched_name]
        logger.debug("[LeagueResolver] %r → %r (score=%d, sm_id=%d)", query, matched_name, score, sm_id)
        if sm_id not in sm_ids:
            sm_ids.append(sm_id)

        oa_id = oa_mapping.get(str(sm_id))
        if isinstance(oa_id, int) and oa_id not in oa_ids:
            oa_ids.append(oa_id)

    return {"sportmonks": sm_ids, "oddalerts": oa_ids}
```

- [ ] **步骤 3：快速验证**

```bash
cd backend && python -c "from pipeline.league_resolver import resolve_league_ids; print(resolve_league_ids(['英超']))"
```

- [ ] **步骤 4：提交**

```bash
git add backend/pipeline/league_resolver.py backend/requirements.txt
git commit -m "feat(pipeline): 新增 league_resolver，用 fuzzy 匹配替代 LLM 联赛解析"
```

---

## Task 8：Analyst Agent

**文件：**
- 新建：`backend/agents/analyst.py`

- [ ] **步骤 1：新建 `backend/agents/analyst.py`**

```python
"""
Analyst Agent — 唯一的 LLM agent。
输入：单场比赛 raw_data（来自所有激活 provider）。
输出：xG、亚盘方向、置信度、Kelly 注额。
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

_CST = timezone(timedelta(hours=8))

ROLE_PATH = "backend/agents/roles/analyst"


def _now_iso() -> str:
    return datetime.now(_CST).isoformat()


def _parse_output(text: str) -> dict:
    json_match = re.search(r"\{[\s\S]*\}", text)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    return {
        "raw_output": text[:2000],
        "note": "failed to parse structured JSON from analyst output",
    }


async def run_analyst(
    adapter,
    metadata: dict,
    raw_data: dict,
    model: str = "v4.0",
) -> dict:
    """
    调用 Analyst role 分析一场比赛。

    Args:
        adapter:  ClaudeAdapter 实例
        metadata: 比赛元数据（队名、联赛、开球时间等）
        raw_data: 所有激活 provider 收集的原始数据
        model:    分析模型版本标识（默认 v4.0）

    Returns:
        分析结果 dict，包含 home_xg/away_xg/ah_recommendation/
        confidence/kelly_fraction/analyzed_at，失败时包含 error 字段。
    """
    context = {
        "metadata": metadata,
        "raw_data": raw_data,
    }
    prompt = (
        f"请使用 {model} skill 分析这场比赛。\n"
        "所需数据均已在下方提供，请勿再调用工具获取新数据。\n"
        "分析完成后请以 JSON 格式输出结果，必须包含以下字段：\n"
        "  home_xg (float), away_xg (float),\n"
        "  ah_recommendation (str，如 '主队 -0.5'),\n"
        "  confidence (float 0-1),\n"
        "  kelly_fraction (float 0-1)\n"
        f"{json.dumps(context, ensure_ascii=False)}"
    )

    try:
        result = await adapter.run_agent(ROLE_PATH, prompt)
        analysis = _parse_output(result.final_text)
    except Exception as exc:
        logger.error("[Analyst] 分析异常 %s vs %s: %s",
                     metadata.get("home_team"), metadata.get("away_team"), exc)
        return {"error": str(exc), "analyzed_at": _now_iso()}

    analysis["analyzed_at"] = _now_iso()
    logger.info("[Analyst] 完成: %s vs %s (confidence=%.2f)",
                metadata.get("home_team"), metadata.get("away_team"),
                analysis.get("confidence", 0))
    return analysis
```

- [ ] **步骤 2：验证导入**

```bash
cd backend && python -c "from agents.analyst import run_analyst; print('OK')"
```

- [ ] **步骤 3：提交**

```bash
git add backend/agents/analyst.py
git commit -m "feat(analyst): 新增简化版 Analyst agent，合并分析与投注推荐"
```

---

## Task 9：Pipeline Runner

**文件：**
- 新建：`backend/pipeline/runner.py`
- 新建：`backend/tests/pipeline/test_runner.py`

- [ ] **步骤 1：写失败测试**

```python
# backend/tests/pipeline/test_runner.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from provider.models import UnifiedFixture


def _make_unified(home: str, away: str, ts: int, sm_id: int, oa_id: int) -> UnifiedFixture:
    return UnifiedFixture(
        home_team=home, away_team=away, kickoff_unix=ts,
        provider_ids={"sportmonks": sm_id, "oddalerts": oa_id},
    )


@pytest.mark.asyncio
async def test_run_pipeline_collects_and_stores(tmp_path):
    unified = [_make_unified("Arsenal", "Chelsea", 1715000000, 100, 200)]

    with (
        patch("pipeline.runner.discover_fixtures", new=AsyncMock(return_value=unified)),
        patch("pipeline.runner.collect_match_data", new=AsyncMock(return_value={"oddalerts": {"_meta": {}}})),
        patch("pipeline.runner.match_store.MATCHES_DIR", tmp_path / "matches"),
        patch("pipeline.runner.match_store.exists_for_fixture", return_value=None),
        patch("pipeline.runner.registry.is_analyst_enabled", return_value=False),
    ):
        from pipeline.runner import run_pipeline
        result = await run_pipeline(leagues=[], dates=["2025-05-10"])

    assert result["discovered"] == 1
    assert result["collected"] == 1
    assert result["analyzed"] == 0


@pytest.mark.asyncio
async def test_run_pipeline_skips_existing_match(tmp_path):
    unified = [_make_unified("Arsenal", "Chelsea", 1715000000, 100, 200)]

    with (
        patch("pipeline.runner.discover_fixtures", new=AsyncMock(return_value=unified)),
        patch("pipeline.runner.match_store.MATCHES_DIR", tmp_path / "matches"),
        patch("pipeline.runner.match_store.exists_for_fixture", return_value="MC-EXISTING"),
        patch("pipeline.runner.registry.is_analyst_enabled", return_value=False),
    ):
        from pipeline.runner import run_pipeline
        result = await run_pipeline(leagues=[], dates=["2025-05-10"])

    assert result["collected"] == 0


@pytest.mark.asyncio
async def test_run_pipeline_calls_analyst_when_enabled(tmp_path):
    unified = [_make_unified("Arsenal", "Chelsea", 1715000000, 100, 200)]
    mock_analysis = {"home_xg": 1.5, "away_xg": 1.0, "ah_recommendation": "home", "confidence": 0.7, "kelly_fraction": 0.05, "analyzed_at": "2025-05-09T10:00:00+08:00"}

    with (
        patch("pipeline.runner.discover_fixtures", new=AsyncMock(return_value=unified)),
        patch("pipeline.runner.collect_match_data", new=AsyncMock(return_value={"oddalerts": {"_meta": {}}})),
        patch("pipeline.runner.match_store.MATCHES_DIR", tmp_path / "matches"),
        patch("pipeline.runner.match_store.exists_for_fixture", return_value=None),
        patch("pipeline.runner.registry.is_analyst_enabled", return_value=True),
        patch("pipeline.runner.run_analyst", new=AsyncMock(return_value=mock_analysis)),
    ):
        from pipeline.runner import run_pipeline
        result = await run_pipeline(leagues=[], dates=["2025-05-10"], adapter=MagicMock())

    assert result["analyzed"] == 1
```

- [ ] **步骤 2：运行测试确认失败**

```bash
cd backend && python -m pytest tests/pipeline/test_runner.py -v
```

- [ ] **步骤 3：新建 `backend/pipeline/runner.py`**

```python
"""
Pipeline Runner — 核心编排器。
顺序执行：发现 fixtures → 收集数据 → 分析（可选）。
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from pipeline.discovery import discover_fixtures
from pipeline.collector import collect_match_data
from pipeline.league_resolver import resolve_league_ids
from provider import registry
from store import match_store
from agents.analyst import run_analyst

logger = logging.getLogger(__name__)

_CST = timezone(timedelta(hours=8))


def _default_dates() -> list[str]:
    now = datetime.now(_CST)
    return [(now + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(5)]


async def run_pipeline(
    leagues: list[str] | None = None,
    dates: list[str] | None = None,
    adapter: Any = None,
    model: str = "v4.0",
    force: bool = False,
) -> dict:
    """
    执行一次完整的 pipeline。

    Args:
        leagues:  联赛名称列表（支持中英文），None 则不过滤
        dates:    日期列表 YYYY-MM-DD，None 则取今日起 5 天
        adapter:  ClaudeAdapter 实例（analyst 启用时必须提供）
        model:    分析模型版本
        force:    True 时重新处理已有比赛

    Returns:
        {"discovered": int, "collected": int, "analyzed": int, "errors": int}
    """
    dates = dates or _default_dates()
    league_ids_by_provider: dict[str, list[int]] = {}

    if leagues:
        resolved = resolve_league_ids(leagues)
        league_ids_by_provider = resolved
        logger.info("[Runner] 联赛解析: %s → %s", leagues, resolved)

    logger.info("[Runner] 开始 pipeline, dates=%s", dates)

    # ── 1. 发现 fixtures ──────────────────────────────────────────────
    unified_fixtures = await discover_fixtures(dates, league_ids_by_provider)
    discovered = len(unified_fixtures)
    logger.info("[Runner] 发现 %d 场", discovered)

    collected = 0
    analyzed = 0
    errors = 0
    analyst_enabled = registry.is_analyst_enabled()

    for uf in unified_fixtures:
        # ── 2. 跳过已存在的 match（除非 force）──────────────────────
        existing_id = None
        for provider_name, fid in uf.provider_ids.items():
            existing_id = match_store.exists_for_fixture(provider_name, fid)
            if existing_id:
                break

        if existing_id and not force:
            existing = match_store.get(existing_id)
            if existing and existing.get("status") in ("collected", "analyzed"):
                logger.debug("[Runner] 跳过已存在比赛: %s", existing_id)
                continue

        match_id = existing_id or match_store.generate_match_id()

        kickoff_str = (
            datetime.fromtimestamp(uf.kickoff_unix, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            if uf.kickoff_unix else ""
        )
        league_name = (
            next(iter(uf.provider_ids.keys()), "")
            if not hasattr(uf, "league_name")
            else getattr(uf, "league_name", "")
        )

        metadata = {
            "match_id": match_id,
            "home_team": uf.home_team,
            "away_team": uf.away_team,
            "league": league_name,
            "kickoff_time": kickoff_str,
            "provider_ids": uf.provider_ids,
            "collected_at": None,
        }

        # ── 3. 收集数据 ───────────────────────────────────────────────
        try:
            raw_data = await collect_match_data(uf.provider_ids)
        except Exception as exc:
            logger.error("[Runner] 收集失败 %s vs %s: %s", uf.home_team, uf.away_team, exc)
            errors += 1
            continue

        from datetime import datetime as _dt
        metadata["collected_at"] = _dt.now(_CST).isoformat()

        record = {
            "match_id": match_id,
            "status": "collected",
            "metadata": metadata,
            "raw_data": raw_data,
            "analysis": {},
        }
        match_store.save(record)
        collected += 1
        logger.info("[Runner] 收集完成: %s vs %s (%s)", uf.home_team, uf.away_team, match_id)

        # ── 4. 分析（可选）───────────────────────────────────────────
        if not analyst_enabled or adapter is None:
            continue

        try:
            analysis = await run_analyst(adapter, metadata, raw_data, model)
            if "error" in analysis:
                match_store.update(match_id, {"status": "error", "analysis": analysis})
                errors += 1
            else:
                match_store.update(match_id, {"status": "analyzed", "analysis": analysis})
                analyzed += 1
        except Exception as exc:
            logger.error("[Runner] 分析失败 %s: %s", match_id, exc)
            match_store.update(match_id, {"status": "error"})
            errors += 1

    logger.info("[Runner] 完成: discovered=%d collected=%d analyzed=%d errors=%d",
                discovered, collected, analyzed, errors)
    return {
        "discovered": discovered,
        "collected": collected,
        "analyzed": analyzed,
        "errors": errors,
    }
```

- [ ] **步骤 4：运行测试确认通过**

```bash
cd backend && python -m pytest tests/pipeline/test_runner.py -v
```

- [ ] **步骤 5：提交**

```bash
git add backend/pipeline/runner.py backend/tests/pipeline/test_runner.py
git commit -m "feat(pipeline): 新增 Pipeline Runner，顺序执行 discover→collect→analyze"
```

---

## Task 10：Pipeline Scheduler

**文件：**
- 新建：`backend/pipeline/scheduler.py`

- [ ] **步骤 1：新建 `backend/pipeline/scheduler.py`**

```python
"""
Pipeline Scheduler。
支持：定时运行（从 providers.json 读取间隔）+ 手动触发。
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from provider import registry
from pipeline.runner import run_pipeline

logger = logging.getLogger(__name__)

_CST = timezone(timedelta(hours=8))


class PipelineScheduler:
    def __init__(self):
        self._stop = asyncio.Event()
        self._manual_trigger = asyncio.Event()
        self._running = False
        self._last_result: dict = {}

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def last_result(self) -> dict:
        return self._last_result

    async def trigger(self) -> None:
        """手动触发立即执行一次 pipeline。"""
        self._manual_trigger.set()

    def stop(self) -> None:
        self._stop.set()

    async def run_forever(
        self,
        leagues: list[str] | None = None,
        adapter: Any = None,
        model: str = "v4.0",
    ) -> None:
        """持续运行：执行一次 pipeline，等待间隔，再执行。"""
        logger.info("[Scheduler] 启动")
        while not self._stop.is_set():
            interval_hours = registry.get_schedule_hours()
            interval_seconds = interval_hours * 3600

            self._running = True
            try:
                logger.info("[Scheduler] 开始执行 pipeline")
                self._last_result = await run_pipeline(
                    leagues=leagues,
                    adapter=adapter,
                    model=model,
                )
                logger.info("[Scheduler] 执行完成: %s", self._last_result)
            except Exception as exc:
                logger.error("[Scheduler] Pipeline 执行异常: %s", exc)
            finally:
                self._running = False

            # 等待定时间隔或手动触发
            self._manual_trigger.clear()
            logger.info("[Scheduler] 等待 %d 秒（%d 小时）或手动触发", interval_seconds, interval_hours)
            try:
                await asyncio.wait_for(
                    self._manual_trigger.wait(),
                    timeout=interval_seconds,
                )
                logger.info("[Scheduler] 手动触发，立即执行")
            except asyncio.TimeoutError:
                pass

            if self._stop.is_set():
                break

        logger.info("[Scheduler] 已停止")


_scheduler = PipelineScheduler()


def get_scheduler() -> PipelineScheduler:
    return _scheduler
```

- [ ] **步骤 2：验证导入**

```bash
cd backend && python -c "from pipeline.scheduler import get_scheduler; print('OK')"
```

- [ ] **步骤 3：提交**

```bash
git add backend/pipeline/scheduler.py
git commit -m "feat(pipeline): 新增 Scheduler，支持定时 + 手动触发"
```

---

## Task 11：API Routes 重写

**文件：**
- 重写：`backend/server/routes/pipeline.py`
- 重写：`backend/server/routes/config.py`
- 修改：`backend/server/server.py`

- [ ] **步骤 1：重写 `backend/server/routes/pipeline.py`**

```python
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Query

from store import match_store
from pipeline.scheduler import get_scheduler

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["pipeline"])

_CST = timezone(timedelta(hours=8))
_LEAGUES_FILE = Path(__file__).resolve().parents[2] / "config" / "sportmonks_leagues.json"


@router.get("/matches")
async def get_matches(
    league: str = Query(default=None),
    date: str = Query(default=None),
    status: str = Query(default=None),
) -> dict:
    items = match_store.list_matches(league=league, date=date, status=status)
    return {"items": items, "total": len(items)}


@router.get("/matches/{match_id}")
async def get_match(match_id: str) -> dict:
    record = match_store.get(match_id)
    if record is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="比赛不存在")
    return record


@router.post("/pipeline/run")
async def trigger_pipeline(body: dict = None) -> dict:
    scheduler = get_scheduler()
    await scheduler.trigger()
    return {"message": "已触发 pipeline 执行"}


@router.get("/pipeline/status")
async def get_pipeline_status() -> dict:
    scheduler = get_scheduler()
    return {
        "running": scheduler.is_running,
        "last_result": scheduler.last_result,
    }


@router.get("/pipeline/leagues")
async def get_leagues() -> dict:
    import json
    available = []
    if _LEAGUES_FILE.exists():
        try:
            all_leagues = json.loads(_LEAGUES_FILE.read_text(encoding="utf-8"))
            seen: set[str] = set()
            for lid, info in all_leagues.items():
                cn = info.get("chinese_name", info.get("name", ""))
                if cn in seen:
                    continue
                seen.add(cn)
                available.append({
                    "id": info.get("id"),
                    "chinese_name": cn,
                    "name": info.get("name", ""),
                })
        except Exception:
            pass
    available.sort(key=lambda x: x["chinese_name"])
    return {"available": available}
```

- [ ] **步骤 2：重写 `backend/server/routes/config.py`**

```python
from __future__ import annotations

import logging

from fastapi import APIRouter

from provider import registry

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("/providers")
async def get_providers() -> dict:
    cfg = registry.get_config()
    return {
        "providers": cfg.get("providers", {}),
        "analyst": cfg.get("analyst", {"enabled": True}),
        "schedule": cfg.get("schedule", {"interval_hours": 1}),
    }


@router.post("/providers")
async def update_providers(body: dict) -> dict:
    """
    body 示例:
    {
      "providers": {"oddalerts": true, "sportmonks": false},
      "analyst": true
    }
    """
    providers = body.get("providers", {})
    for name, enabled in providers.items():
        registry.set_provider_enabled(name, bool(enabled))

    if "analyst" in body:
        registry.set_analyst_enabled(bool(body["analyst"]))

    return {"message": "配置已更新", "config": registry.get_config()}


@router.get("/schedule")
async def get_schedule() -> dict:
    return {"interval_hours": registry.get_schedule_hours()}


@router.post("/schedule")
async def update_schedule(body: dict) -> dict:
    hours = int(body.get("interval_hours", 1))
    registry.set_schedule_hours(hours)
    return {"interval_hours": hours}
```

- [ ] **步骤 3：修改 `backend/server/server.py`，更新路由注册**

将文件中所有路由 import 和 include_router 替换为：

```python
from .routes.config import router as config_router
from .routes.pipeline import router as pipeline_router

app.include_router(config_router)
app.include_router(pipeline_router)
```

同时删除文件中对 `board_router`、`chat_router`、`agents_router` 的引用，以及 `ws_chat` WebSocket handler（依赖旧 Orchestrator）。保留 `/api/health`、`/ws/status`、`/ws/logs`。

- [ ] **步骤 4：验证 server 可以导入**

```bash
cd backend && python -c "from server.server import app; print('OK')"
```

- [ ] **步骤 5：提交**

```bash
git add backend/server/routes/pipeline.py backend/server/routes/config.py backend/server/server.py
git commit -m "feat(api): 重写 pipeline 和 config 路由，对齐新架构"
```

---

## Task 12：更新 main.py 启动入口

**文件：**
- 修改：`backend/main.py`

- [ ] **步骤 1：读取现有 `backend/main.py` 内容，替换 Orchestrator 启动逻辑**

将 Orchestrator 相关启动代码替换为 Scheduler 启动：

```python
import asyncio
import logging
import os

import uvicorn

from server.server import app
from pipeline.scheduler import get_scheduler
from agents.adapters.adapter import ClaudeAdapter

logger = logging.getLogger(__name__)


async def _start_scheduler():
    adapter = ClaudeAdapter()
    scheduler = get_scheduler()
    leagues_env = os.environ.get("GOALCAST_LEAGUES", "")
    leagues = [l.strip() for l in leagues_env.split(",") if l.strip()] or None
    await scheduler.run_forever(leagues=leagues, adapter=adapter)


def main():
    logging.basicConfig(level=logging.INFO)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    scheduler_task = loop.create_task(_start_scheduler())

    config = uvicorn.Config(app, host="0.0.0.0", port=8000, loop="none")
    server = uvicorn.Server(config)

    try:
        loop.run_until_complete(server.serve())
    finally:
        scheduler_task.cancel()
        loop.run_until_complete(asyncio.gather(scheduler_task, return_exceptions=True))
        loop.close()


if __name__ == "__main__":
    main()
```

- [ ] **步骤 2：验证启动入口可以导入**

```bash
cd backend && python -c "import main; print('OK')"
```

- [ ] **步骤 3：提交**

```bash
git add backend/main.py
git commit -m "refactor(main): 用 PipelineScheduler 替代旧 Orchestrator 启动逻辑"
```

---

## Task 13：数据迁移脚本

**文件：**
- 新建：`backend/scripts/migrate_matches.py`

- [ ] **步骤 1：新建 `backend/scripts/migrate_matches.py`**

```python
"""
将旧格式 MC-*.json 文件迁移到新统一格式。
旧格式有 orchestrator/analysis/trading/review/state 等字段，
新格式只保留 metadata/raw_data/analysis。

用法：
    cd backend && python scripts/migrate_matches.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "matches"


def _migrate_record(record: dict) -> dict | None:
    """将旧格式 record 转为新格式。返回 None 表示已是新格式或无法迁移。"""
    if "metadata" in record and "provider_ids" in record.get("metadata", {}):
        return None  # 已是新格式

    orch = record.get("orchestrator", {}) or {}
    meta_old = record.get("metadata", {}) or {}

    home_team = orch.get("home_team") or meta_old.get("home_team", "")
    away_team = orch.get("away_team") or meta_old.get("away_team", "")
    league_raw = orch.get("league") or meta_old.get("league", "")
    league = league_raw.get("name", "") if isinstance(league_raw, dict) else str(league_raw or "")
    kickoff = orch.get("kickoff_time") or meta_old.get("kickoff_time", "")
    sm_id = orch.get("fixture_id") or meta_old.get("fixture_id")
    oa_id = meta_old.get("oa_fixture_id")

    provider_ids: dict = {}
    if sm_id:
        provider_ids["sportmonks"] = sm_id
    if oa_id:
        provider_ids["oddalerts"] = oa_id

    old_status = record.get("status", "unknown")
    new_status_map = {
        "pending": "pending",
        "analyzing": "pending",
        "analyzed": "collected",
        "trading": "collected",
        "traded": "collected",
        "reviewing": "collected",
        "reviewed": "collected",
        "reported": "analyzed",
        "feedback": "collected",
        "aborted": "error",
        "abandoned": "error",
        "error": "error",
    }
    new_status = new_status_map.get(old_status, "pending")

    analysis_old = record.get("analysis", {}) or {}
    trading_old = record.get("trading", {}) or {}
    analysis_new: dict = {}
    if isinstance(analysis_old, dict) and analysis_old:
        v4 = analysis_old.get("v4.0", {})
        src = v4 if isinstance(v4, dict) and v4.get("home_xg") else analysis_old
        analysis_new = {
            "home_xg": src.get("home_xg"),
            "away_xg": src.get("away_xg"),
            "ah_recommendation": src.get("ah_recommendation"),
            "confidence": src.get("confidence"),
        }
        if isinstance(trading_old, dict) and trading_old:
            results = trading_old.get("results", {})
            if isinstance(results, dict):
                analysis_new["kelly_fraction"] = results.get("kelly_fraction")

    raw_data = record.get("raw_data", {}) or {}

    return {
        "match_id": record["match_id"],
        "status": new_status,
        "metadata": {
            "match_id": record["match_id"],
            "home_team": home_team,
            "away_team": away_team,
            "league": league,
            "kickoff_time": kickoff,
            "provider_ids": provider_ids,
            "collected_at": orch.get("prepared_at") or meta_old.get("prepared_at"),
        },
        "raw_data": raw_data,
        "analysis": analysis_new,
    }


def main():
    parser = argparse.ArgumentParser(description="迁移旧格式 match 文件到新格式")
    parser.add_argument("--dry-run", action="store_true", help="只打印，不写文件")
    args = parser.parse_args()

    if not DATA_DIR.exists():
        print(f"目录不存在: {DATA_DIR}")
        sys.exit(0)

    files = list(DATA_DIR.glob("MC-*.json"))
    migrated = 0
    skipped = 0
    errors = 0

    for fp in files:
        try:
            record = json.loads(fp.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[ERROR] 读取失败 {fp.name}: {e}")
            errors += 1
            continue

        new_record = _migrate_record(record)
        if new_record is None:
            skipped += 1
            continue

        if args.dry_run:
            print(f"[DRY] 会迁移: {fp.name} (status: {record.get('status')} → {new_record['status']})")
        else:
            fp.write_text(json.dumps(new_record, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[OK] 已迁移: {fp.name}")
        migrated += 1

    print(f"\n完成：迁移 {migrated}，跳过（已是新格式）{skipped}，错误 {errors}")


if __name__ == "__main__":
    main()
```

- [ ] **步骤 2：空跑验证**

```bash
cd backend && python scripts/migrate_matches.py --dry-run
```

- [ ] **步骤 3：提交**

```bash
git add backend/scripts/migrate_matches.py
git commit -m "feat(scripts): 新增 migrate_matches 迁移脚本，规范化旧格式 match 文件"
```

---

## Task 14：清理旧文件

**注意：此任务在所有前置任务完成并验证后执行。**

- [ ] **步骤 1：运行全量测试确认基础功能正常**

```bash
cd backend && python -m pytest tests/ -v
```

期望：所有新测试通过，无 import 错误。

- [ ] **步骤 2：删除旧 agent 文件**

```bash
rm -rf backend/agents/core/orchestrator.py
rm -rf backend/agents/core/pipeline.py
rm -rf backend/agents/core/blackboard.py
rm -rf backend/agents/core/data_collector.py
rm -rf backend/agents/core/directory_agent.py
rm -rf backend/agents/core/events.py
rm -rf backend/agents/core/league_config.py
rm -rf backend/agents/core/coordinator.py
rm -rf backend/agents/scheduler.py
rm -rf backend/agents/llm_router.py
```

- [ ] **步骤 3：删除旧 roles**

```bash
rm -rf backend/agents/roles/trader
rm -rf backend/agents/roles/reviewer
rm -rf backend/agents/roles/reporter
rm -rf backend/agents/roles/backtester
rm -rf backend/agents/roles/prediction
```

- [ ] **步骤 4：删除旧目录**

```bash
rm -rf backend/datasource
rm -rf backend/mcp_server
```

- [ ] **步骤 5：删除旧 API 路由**

```bash
rm -f backend/server/routes/agents.py
rm -f backend/server/routes/board.py
rm -f backend/server/routes/chat.py
```

- [ ] **步骤 6：删除旧 match_store（已被 store/match_store.py 替代）**

```bash
rm -f backend/agents/core/match_store.py
```

- [ ] **步骤 7：检查是否有残留 import 报错**

```bash
cd backend && python -c "from server.server import app; print('OK')"
cd backend && python -c "from pipeline.runner import run_pipeline; print('OK')"
```

修复任何 import 错误后继续。

- [ ] **步骤 8：再次运行测试确认无回归**

```bash
cd backend && python -m pytest tests/ -v
```

- [ ] **步骤 9：提交**

```bash
git add -A
git commit -m "chore: 删除旧 Orchestrator、Trader、Reviewer、Reporter 及相关文件"
```

---

## Task 15：端到端烟测

- [ ] **步骤 1：安装依赖**

```bash
cd backend && pip install -r requirements.txt
```

- [ ] **步骤 2：启动服务器**

```bash
cd backend && python -m uvicorn server.server:app --reload --port 8000
```

- [ ] **步骤 3：验证健康检查**

```bash
curl http://localhost:8000/api/health
```

期望：`{"status":"ok"}`

- [ ] **步骤 4：验证配置接口**

```bash
curl http://localhost:8000/api/config/providers
```

期望：返回 providers 开关状态 JSON

- [ ] **步骤 5：验证比赛列表接口**

```bash
curl "http://localhost:8000/api/matches?date=2025-05-10"
```

期望：`{"items": [...], "total": N}`

- [ ] **步骤 6：手动触发 pipeline**

```bash
curl -X POST http://localhost:8000/api/pipeline/run
```

期望：`{"message":"已触发 pipeline 执行"}`

- [ ] **步骤 7：运行迁移脚本（如有旧数据）**

```bash
cd backend && python scripts/migrate_matches.py
```

- [ ] **步骤 8：提交**

```bash
git add -A
git commit -m "test: 后端架构重构完成，端到端烟测通过"
```

---

## 测试运行汇总

每个任务完成后可运行全量测试：

```bash
cd backend && python -m pytest tests/ -v --tb=short
```

新增测试覆盖：
- `tests/provider/test_registry.py` — Provider Registry 开关
- `tests/store/test_match_store.py` — Match Store CRUD
- `tests/pipeline/test_discovery.py` — Fixture 发现与合并
- `tests/pipeline/test_collector.py` — 数据收集
- `tests/pipeline/test_runner.py` — Pipeline 完整流程

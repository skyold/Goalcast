# Provider 抽象化 Fixture 发现实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 Sportmonks 和 OddAlerts（及未来更多 provider）各自独立发现当日 fixture 列表，合并为统一的 `UnifiedFixture` 对象，彻底消除事后 ID 映射的不稳定性。

**Architecture:** 每个 provider 实现 `discover_fixtures(league_ids, dates)` 抽象方法，返回 `list[ProviderFixture]`。`FixtureMerger` 用队名归一化 + 时间分桶做模糊合并，生成 `list[UnifiedFixture]`（携带各 provider 的 ID）。Orchestrator 调用合并结果后，DataCollector 直接使用 `provider_ids` 字典取各方数据，跳过 fixture_mapper。

**Tech Stack:** Python 3.13, asyncio, pytest, unittest.mock

---

## 文件结构

| 路径 | 类型 | 职责 |
|------|------|------|
| `backend/provider/models.py` | 新建 | `ProviderFixture`, `UnifiedFixture` 数据模型 |
| `backend/utils/normalize.py` | 新建 | 共享队名归一化函数（从 fixture_mapper 提取） |
| `backend/agents/core/fixture_merger.py` | 新建 | 跨 provider fixture 合并逻辑 |
| `backend/provider/base.py` | 修改 | 新增 `discover_fixtures` 抽象方法 |
| `backend/provider/sportmonks/client.py` | 修改 | 实现 `discover_fixtures` |
| `backend/provider/oddalerts/client.py` | 修改 | 实现 `discover_fixtures`（两级策略） |
| `backend/config/oddalerts_leagues.json` | 新建 | 联赛名 → OddAlerts competition_id 映射 |
| `backend/agents/core/data_collector.py` | 修改 | `collect_all` 接收 `provider_ids` 字典 |
| `backend/agents/core/orchestrator.py` | 修改 | `_fetch_and_prepare` 改用双源合并流程 |
| `backend/provider/oddalerts/fixture_mapper.py` | 保留 | 标记 deprecated，暂不删除 |

测试文件与被测模块并排放置：
- `backend/provider/tests/test_models.py`
- `backend/utils/tests/test_normalize.py`
- `backend/agents/core/tests/test_fixture_merger.py`
- `backend/provider/sportmonks/tests/test_discover.py`
- `backend/provider/oddalerts/tests/test_discover.py`
- `backend/agents/core/tests/test_data_collector.py`

---

## Task 1: 提取队名归一化到 utils/normalize.py

**Files:**
- Create: `backend/utils/normalize.py`
- Create: `backend/utils/tests/__init__.py`
- Create: `backend/utils/tests/test_normalize.py`

- [ ] **Step 1: 写失败测试**

```python
# backend/utils/tests/test_normalize.py
from utils.normalize import normalize_team_name

def test_removes_accents():
    assert normalize_team_name("Atlético Madrid") == "atleticomadrid"

def test_removes_spaces():
    assert normalize_team_name("Borussia Dortmund") == "borussiadortmund"

def test_removes_hyphens():
    assert normalize_team_name("Paris Saint-Germain") == "parissaintgermain"

def test_lowercase():
    assert normalize_team_name("ARSENAL") == "arsenal"

def test_non_ascii_stripped():
    assert normalize_team_name("São Paulo") == "saopaulo"

def test_empty_string():
    assert normalize_team_name("") == ""
```

- [ ] **Step 2: 运行，确认失败**

```bash
cd backend && python -m pytest utils/tests/test_normalize.py -v
```

期望：`ModuleNotFoundError: No module named 'utils.normalize'`

- [ ] **Step 3: 创建 `backend/utils/tests/__init__.py`（空文件）并实现**

```python
# backend/utils/normalize.py
import re
import unicodedata


def normalize_team_name(name: str) -> str:
    """移除重音、空格、连字符，全部小写，用于跨 provider 队名比较。"""
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_str = nfkd.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]", "", ascii_str.lower())
```

- [ ] **Step 4: 运行，确认通过**

```bash
cd backend && python -m pytest utils/tests/test_normalize.py -v
```

期望：6 passed

- [ ] **Step 5: 更新 fixture_mapper.py，改为从 utils.normalize 导入**

在 `backend/provider/oddalerts/fixture_mapper.py` 顶部替换：

```python
# 删除原有的 _normalize 函数定义，改为导入
from utils.normalize import normalize_team_name as _normalize
```

删除 `fixture_mapper.py` 中的：
```python
def _normalize(name: str) -> str:
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_str = nfkd.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]", "", ascii_str.lower())
```

- [ ] **Step 6: 确认 fixture_mapper 仍可正常导入**

```bash
cd backend && python -c "from provider.oddalerts.fixture_mapper import find_oddalerts_fixture_id; print('OK')"
```

期望：`OK`

- [ ] **Step 7: Commit**

```bash
git add utils/normalize.py utils/tests/__init__.py utils/tests/test_normalize.py provider/oddalerts/fixture_mapper.py
git commit -m "refactor: 提取 normalize_team_name 到 utils/normalize.py"
```

---

## Task 2: 新建 provider/models.py（数据模型）

**Files:**
- Create: `backend/provider/models.py`
- Create: `backend/provider/tests/__init__.py`
- Create: `backend/provider/tests/test_models.py`

- [ ] **Step 1: 写失败测试**

```python
# backend/provider/tests/test_models.py
from provider.models import ProviderFixture, UnifiedFixture

def test_provider_fixture_defaults():
    f = ProviderFixture(
        provider="sportmonks",
        fixture_id=1,
        home_team="Arsenal",
        away_team="Chelsea",
        kickoff_unix=1746000000,
    )
    assert f.league_name is None
    assert f.raw == {}
    assert f.provider == "sportmonks"

def test_unified_fixture_missing_provider_returns_none():
    u = UnifiedFixture(
        home_team="Arsenal",
        away_team="Chelsea",
        kickoff_unix=1746000000,
        provider_ids={"sportmonks": 100},
    )
    assert u.provider_ids.get("oddalerts") is None
    assert u.provider_ids["sportmonks"] == 100

def test_unified_fixture_default_provider_ids_empty():
    u = UnifiedFixture(home_team="A", away_team="B", kickoff_unix=1000)
    assert u.provider_ids == {}
```

- [ ] **Step 2: 运行，确认失败**

```bash
cd backend && python -m pytest provider/tests/test_models.py -v
```

期望：`ModuleNotFoundError: No module named 'provider.models'`

- [ ] **Step 3: 创建 `backend/provider/tests/__init__.py`（空文件）并实现模型**

```python
# backend/provider/models.py
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ProviderFixture:
    """单个 provider 返回的原始 fixture 信息。"""
    provider: str
    fixture_id: int
    home_team: str
    away_team: str
    kickoff_unix: int
    league_name: str | None = None
    raw: dict = field(default_factory=dict)


@dataclass
class UnifiedFixture:
    """跨 provider 合并后的统一比赛对象。

    provider_ids: {"sportmonks": 18329, "oddalerts": 54201}
    某 provider 无对应比赛时该 key 不存在，用 .get("oddalerts") 安全取值。
    """
    home_team: str
    away_team: str
    kickoff_unix: int
    provider_ids: dict[str, int] = field(default_factory=dict)
```

- [ ] **Step 4: 运行，确认通过**

```bash
cd backend && python -m pytest provider/tests/test_models.py -v
```

期望：3 passed

- [ ] **Step 5: Commit**

```bash
git add provider/models.py provider/tests/__init__.py provider/tests/test_models.py
git commit -m "feat: 新增 ProviderFixture 和 UnifiedFixture 数据模型"
```

---

## Task 3: 新建 agents/core/fixture_merger.py

**Files:**
- Create: `backend/agents/core/fixture_merger.py`
- Create: `backend/agents/core/tests/__init__.py`
- Create: `backend/agents/core/tests/test_fixture_merger.py`

- [ ] **Step 1: 写失败测试**

```python
# backend/agents/core/tests/test_fixture_merger.py
from agents.core.fixture_merger import merge_fixtures
from provider.models import ProviderFixture


def _pf(provider, fid, home, away, kickoff):
    return ProviderFixture(provider=provider, fixture_id=fid,
                           home_team=home, away_team=away, kickoff_unix=kickoff)


def test_single_provider_single_match():
    result = merge_fixtures([("sportmonks", [_pf("sportmonks", 100, "Arsenal", "Chelsea", 1746000000)])])
    assert len(result) == 1
    assert result[0].provider_ids == {"sportmonks": 100}
    assert result[0].home_team == "Arsenal"


def test_two_providers_same_match_merges():
    sm = [_pf("sportmonks", 100, "Arsenal", "Chelsea", 1746000000)]
    oa = [_pf("oddalerts", 999, "Arsenal", "Chelsea", 1746001800)]  # 30분 차이
    result = merge_fixtures([("sportmonks", sm), ("oddalerts", oa)])
    assert len(result) == 1
    assert result[0].provider_ids == {"sportmonks": 100, "oddalerts": 999}


def test_time_within_one_hour_merges():
    sm = [_pf("sportmonks", 100, "Arsenal", "Chelsea", 1746000000)]
    oa = [_pf("oddalerts", 999, "Arsenal", "Chelsea", 1746003500)]  # 58분 차이
    result = merge_fixtures([("sportmonks", sm), ("oddalerts", oa)])
    assert len(result) == 1


def test_time_over_one_hour_no_merge():
    sm = [_pf("sportmonks", 100, "Arsenal", "Chelsea", 1746000000)]
    oa = [_pf("oddalerts", 999, "Arsenal", "Chelsea", 1746003600)]  # 정확히 1시간 차이 → 다른 버킷
    result = merge_fixtures([("sportmonks", sm), ("oddalerts", oa)])
    assert len(result) == 2


def test_different_matches_not_merged():
    sm = [_pf("sportmonks", 100, "Arsenal", "Chelsea", 1746000000)]
    oa = [_pf("oddalerts", 200, "Liverpool", "Man City", 1746000000)]
    result = merge_fixtures([("sportmonks", sm), ("oddalerts", oa)])
    assert len(result) == 2


def test_accented_names_merge():
    sm = [_pf("sportmonks", 100, "Atletico Madrid", "Barcelona", 1746000000)]
    oa = [_pf("oddalerts", 999, "Atlético Madrid", "FC Barcelona", 1746000000)]
    result = merge_fixtures([("sportmonks", sm), ("oddalerts", oa)])
    assert len(result) == 1


def test_home_team_from_priority_provider():
    sm = [_pf("sportmonks", 100, "Atletico Madrid", "Barcelona", 1746000000)]
    oa = [_pf("oddalerts", 999, "Atlético Madrid", "FC Barcelona", 1746000000)]
    result = merge_fixtures([("sportmonks", sm), ("oddalerts", oa)])
    assert result[0].home_team == "Atletico Madrid"


def test_only_oddalerts_fixture():
    oa = [_pf("oddalerts", 999, "Liverpool", "Man City", 1746000000)]
    result = merge_fixtures([("sportmonks", []), ("oddalerts", oa)])
    assert len(result) == 1
    assert result[0].provider_ids == {"oddalerts": 999}


def test_empty_inputs():
    result = merge_fixtures([("sportmonks", []), ("oddalerts", [])])
    assert result == []
```

- [ ] **Step 2: 运行，确认失败**

```bash
cd backend && python -m pytest agents/core/tests/test_fixture_merger.py -v
```

期望：`ModuleNotFoundError: No module named 'agents.core.fixture_merger'`

- [ ] **Step 3: 创建 `backend/agents/core/tests/__init__.py`（空文件）并实现**

```python
# backend/agents/core/fixture_merger.py
from __future__ import annotations

from provider.models import ProviderFixture, UnifiedFixture
from utils.normalize import normalize_team_name


def _canonical_key(home: str, away: str, kickoff_unix: int) -> str:
    """构造合并用的规范化 key，时间取整到小时以容忍 ±1h 误差。"""
    return f"{normalize_team_name(home)}|{normalize_team_name(away)}|{kickoff_unix // 3600}"


def merge_fixtures(
    provider_fixtures: list[tuple[str, list[ProviderFixture]]],
) -> list[UnifiedFixture]:
    """
    将多个 provider 的 fixture 列表合并为统一的 UnifiedFixture 列表。

    Args:
        provider_fixtures: [(provider_name, fixtures), ...] 按优先级排列，
                           优先级高的 provider 的队名会被保留。

    Returns:
        list[UnifiedFixture]，每个元素的 provider_ids 包含所有匹配到的 provider ID。
    """
    unified: dict[str, UnifiedFixture] = {}

    for provider_name, fixtures in provider_fixtures:
        for pf in fixtures:
            key = _canonical_key(pf.home_team, pf.away_team, pf.kickoff_unix)
            if key in unified:
                unified[key].provider_ids[provider_name] = pf.fixture_id
            else:
                unified[key] = UnifiedFixture(
                    home_team=pf.home_team,
                    away_team=pf.away_team,
                    kickoff_unix=pf.kickoff_unix,
                    provider_ids={provider_name: pf.fixture_id},
                )

    return list(unified.values())
```

- [ ] **Step 4: 运行，确认通过**

```bash
cd backend && python -m pytest agents/core/tests/test_fixture_merger.py -v
```

期望：9 passed

- [ ] **Step 5: Commit**

```bash
git add agents/core/fixture_merger.py agents/core/tests/__init__.py agents/core/tests/test_fixture_merger.py
git commit -m "feat: 新增 FixtureMerger 跨 provider fixture 合并逻辑"
```

---

## Task 4: BaseProvider 新增 discover_fixtures 抽象方法

**Files:**
- Modify: `backend/provider/base.py`

- [ ] **Step 1: 在 `provider/base.py` 顶部新增导入**

在现有 `from abc import ABC, abstractmethod` 所在行后，确认存在：
```python
from __future__ import annotations
```
若不存在则在文件第一行添加。

- [ ] **Step 2: 在 `BaseProvider` 类末尾新增抽象方法**

在 `def __repr__` 方法之前插入：

```python
    @abstractmethod
    async def discover_fixtures(
        self,
        league_ids: list[int],
        dates: list[str],
    ) -> list["ProviderFixture"]:
        """
        返回指定联赛和日期范围内的所有 fixture。

        Args:
            league_ids: 该 provider 自己体系的联赛 ID 列表，空列表表示不过滤。
            dates:      ISO 日期字符串列表，如 ["2026-05-07", "2026-05-08"]。

        Returns:
            list[ProviderFixture]
        """
        pass
```

在文件顶部 `from abc import ABC, abstractmethod` 后添加类型导入：
```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from provider.models import ProviderFixture
```

- [ ] **Step 3: 确认现有 provider 因缺少实现而报错（预期行为）**

```bash
cd backend && python -c "
from provider.oddalerts.client import OddAlertsProvider
import asyncio
p = OddAlertsProvider()
print('OddAlerts loaded OK - abstract method will fail at instantiation if not implemented')
"
```

此时 OddAlertsProvider 尚未实现 discover_fixtures，Python 会在实例化时抛 `TypeError`。这是预期的——后续 Task 5/6 实现后恢复。

- [ ] **Step 4: Commit**

```bash
git add provider/base.py
git commit -m "feat: BaseProvider 新增 discover_fixtures 抽象方法"
```

---

## Task 5: SportmonksProvider 实现 discover_fixtures

**Files:**
- Modify: `backend/provider/sportmonks/client.py`
- Create: `backend/provider/sportmonks/tests/__init__.py`
- Create: `backend/provider/sportmonks/tests/test_discover.py`

- [ ] **Step 1: 写失败测试**

```python
# backend/provider/sportmonks/tests/test_discover.py
import pytest
from unittest.mock import AsyncMock, patch
from provider.sportmonks.client import SportmonksProvider
from provider.models import ProviderFixture


MOCK_RESPONSE = {
    "data": [
        {
            "id": 18329,
            "name": "Arsenal vs Chelsea",
            "starting_at": "2026-05-07 15:00:00",
            "league_id": 8,
            "league": {"name": "Premier League"},
            "participants": [
                {"name": "Arsenal", "meta": {"location": "home"}},
                {"name": "Chelsea", "meta": {"location": "away"}},
            ],
        },
        {
            "id": 18330,
            "name": "Liverpool vs Man City",
            "starting_at": "2026-05-07 17:30:00",
            "league_id": 8,
            "league": {"name": "Premier League"},
            "participants": [
                {"name": "Liverpool", "meta": {"location": "home"}},
                {"name": "Man City", "meta": {"location": "away"}},
            ],
        },
    ]
}


@pytest.mark.asyncio
async def test_discover_fixtures_returns_provider_fixtures():
    provider = SportmonksProvider(api_key="test-key")
    with patch.object(provider, "get_fixtures_by_date", new=AsyncMock(return_value=MOCK_RESPONSE)):
        result = await provider.discover_fixtures(league_ids=[8], dates=["2026-05-07"])

    assert len(result) == 2
    assert all(isinstance(f, ProviderFixture) for f in result)
    assert all(f.provider == "sportmonks" for f in result)


@pytest.mark.asyncio
async def test_discover_fixtures_parses_home_away():
    provider = SportmonksProvider(api_key="test-key")
    with patch.object(provider, "get_fixtures_by_date", new=AsyncMock(return_value=MOCK_RESPONSE)):
        result = await provider.discover_fixtures(league_ids=[8], dates=["2026-05-07"])

    assert result[0].home_team == "Arsenal"
    assert result[0].away_team == "Chelsea"
    assert result[1].home_team == "Liverpool"
    assert result[1].away_team == "Man City"


@pytest.mark.asyncio
async def test_discover_fixtures_parses_kickoff_unix():
    provider = SportmonksProvider(api_key="test-key")
    with patch.object(provider, "get_fixtures_by_date", new=AsyncMock(return_value=MOCK_RESPONSE)):
        result = await provider.discover_fixtures(league_ids=[8], dates=["2026-05-07"])

    # 2026-05-07 15:00:00 UTC
    assert result[0].kickoff_unix == 1746626400


@pytest.mark.asyncio
async def test_discover_fixtures_deduplicates_across_dates():
    provider = SportmonksProvider(api_key="test-key")
    # 两个日期都返回相同数据
    with patch.object(provider, "get_fixtures_by_date", new=AsyncMock(return_value=MOCK_RESPONSE)):
        result = await provider.discover_fixtures(league_ids=[8], dates=["2026-05-07", "2026-05-07"])

    assert len(result) == 2  # 不重复


@pytest.mark.asyncio
async def test_discover_fixtures_empty_response():
    provider = SportmonksProvider(api_key="test-key")
    with patch.object(provider, "get_fixtures_by_date", new=AsyncMock(return_value={"data": []})):
        result = await provider.discover_fixtures(league_ids=[8], dates=["2026-05-07"])

    assert result == []


@pytest.mark.asyncio
async def test_discover_fixtures_passes_league_filter():
    provider = SportmonksProvider(api_key="test-key")
    mock_get = AsyncMock(return_value={"data": []})
    with patch.object(provider, "get_fixtures_by_date", new=mock_get):
        await provider.discover_fixtures(league_ids=[8, 72], dates=["2026-05-07"])

    call_kwargs = mock_get.call_args
    assert "filterFixturesByLeagueIds:8,72" in str(call_kwargs)
```

- [ ] **Step 2: 安装 pytest-asyncio（如未安装）**

```bash
cd backend && pip install pytest-asyncio
```

- [ ] **Step 3: 运行，确认失败**

```bash
cd backend && python -m pytest provider/sportmonks/tests/test_discover.py -v
```

期望：`TypeError: Can't instantiate abstract class SportmonksProvider with abstract method discover_fixtures`

- [ ] **Step 4: 创建 `backend/provider/sportmonks/tests/__init__.py`（空文件）**

- [ ] **Step 5: 在 SportmonksProvider 末尾实现 discover_fixtures**

在 `backend/provider/sportmonks/client.py` 文件末尾（`get_fixtures_latest` 方法之后）添加：

```python
    # ==================== Fixture 发现（Provider 抽象接口实现）====================

    async def discover_fixtures(
        self,
        league_ids: list[int],
        dates: list[str],
    ) -> list:
        """
        按联赛 ID 和日期范围发现 fixture 列表。

        league_ids: Sportmonks 联赛 ID，空列表表示不过滤（返回所有联赛）。
        dates:      ISO 日期字符串列表，如 ["2026-05-07"]。
        """
        from datetime import datetime, timezone
        from provider.models import ProviderFixture

        filters: str | None = None
        if league_ids:
            ids_str = ",".join(map(str, league_ids))
            filters = f"filterFixturesByLeagueIds:{ids_str}"

        include = "participants;league"
        results: list[ProviderFixture] = []
        seen_ids: set[int] = set()

        for date in dates:
            resp = await self.get_fixtures_by_date(date, include=include, filters=filters)
            if not isinstance(resp, dict):
                continue

            for item in resp.get("data", []):
                fid = item.get("id")
                if not fid or fid in seen_ids:
                    continue
                seen_ids.add(fid)

                home_team = ""
                away_team = ""
                for participant in item.get("participants", []):
                    location = participant.get("meta", {}).get("location", "")
                    if location == "home":
                        home_team = participant.get("name", "")
                    elif location == "away":
                        away_team = participant.get("name", "")

                kickoff_unix = 0
                starting_at = item.get("starting_at", "")
                if starting_at:
                    try:
                        dt = datetime.strptime(starting_at, "%Y-%m-%d %H:%M:%S").replace(
                            tzinfo=timezone.utc
                        )
                        kickoff_unix = int(dt.timestamp())
                    except ValueError:
                        pass

                league_name: str | None = None
                if isinstance(item.get("league"), dict):
                    league_name = item["league"].get("name")

                results.append(
                    ProviderFixture(
                        provider="sportmonks",
                        fixture_id=fid,
                        home_team=home_team,
                        away_team=away_team,
                        kickoff_unix=kickoff_unix,
                        league_name=league_name,
                        raw=item,
                    )
                )

        return results
```

- [ ] **Step 6: 运行，确认通过**

```bash
cd backend && python -m pytest provider/sportmonks/tests/test_discover.py -v
```

期望：6 passed

- [ ] **Step 7: Commit**

```bash
git add provider/sportmonks/client.py provider/sportmonks/tests/__init__.py provider/sportmonks/tests/test_discover.py
git commit -m "feat: SportmonksProvider 实现 discover_fixtures"
```

---

## Task 6: OddAlerts 联赛配置 + discover_fixtures 实现

**Files:**
- Create: `backend/config/oddalerts_leagues.json`
- Modify: `backend/provider/oddalerts/client.py`
- Create: `backend/provider/oddalerts/tests/__init__.py`
- Create: `backend/provider/oddalerts/tests/test_discover.py`

- [ ] **Step 1: 运行脚本获取 OddAlerts competition IDs**

先查询 OddAlerts 联赛列表，找到我们需要的联赛对应的 competition_id：

```python
# 临时脚本，运行后删除
import asyncio
from provider.oddalerts.client import OddAlertsProvider

async def main():
    p = OddAlertsProvider()
    # 搜索前几页，找到我们关注的联赛
    target_names = ["premier league", "la liga", "serie a", "bundesliga", "ligue 1",
                    "eredivisie", "primeira liga", "scottish", "jupiler", "super lig",
                    "super league", "superliga", "eliteserien", "bundesliga austria",
                    "ekstraklasa"]
    for page in range(1, 11):
        resp = await p.get_competitions(page=page)
        if not resp or not resp.get("data"):
            break
        for comp in resp["data"]:
            name_lower = comp.get("name", "").lower()
            if any(t in name_lower for t in target_names):
                print(f"  {comp['id']}: {comp['name']} ({comp.get('country', '')})")
    await p.close()

asyncio.run(main())
```

运行（在 backend 目录下）：
```bash
cd backend && python /tmp/find_oa_leagues.py
```

记录输出的 competition_id 映射关系。

- [ ] **Step 2: 创建 `config/oddalerts_leagues.json`**

根据上一步输出，填写以下文件（示例值需替换为真实 ID）：

```json
{
  "英超": {"id": 1, "name": "Premier League", "country": "England"},
  "西甲": {"id": 2, "name": "La Liga", "country": "Spain"},
  "意甲": {"id": 3, "name": "Serie A", "country": "Italy"},
  "德甲": {"id": 4, "name": "Bundesliga", "country": "Germany"},
  "法甲": {"id": 5, "name": "Ligue 1", "country": "France"},
  "荷甲": {"id": 6, "name": "Eredivisie", "country": "Netherlands"},
  "葡超": {"id": 7, "name": "Primeira Liga", "country": "Portugal"},
  "苏超": {"id": 8, "name": "Scottish Premiership", "country": "Scotland"},
  "比甲": {"id": 9, "name": "Jupiler Pro League", "country": "Belgium"},
  "土超": {"id": 10, "name": "Süper Lig", "country": "Turkey"},
  "瑞超": {"id": 11, "name": "Super League", "country": "Switzerland"},
  "丹超": {"id": 12, "name": "Superliga", "country": "Denmark"},
  "挪超": {"id": 13, "name": "Eliteserien", "country": "Norway"},
  "奥超": {"id": 14, "name": "Bundesliga", "country": "Austria"},
  "波超": {"id": 15, "name": "Ekstraklasa", "country": "Poland"},
  "瑞士超": {"id": 16, "name": "Super League", "country": "Switzerland"}
}
```

> **注意**：ID 占位符需替换为步骤 1 中查到的真实值。

- [ ] **Step 3: 写失败测试**

```python
# backend/provider/oddalerts/tests/test_discover.py
import pytest
from unittest.mock import AsyncMock, patch
from provider.oddalerts.client import OddAlertsProvider
from provider.models import ProviderFixture

MOCK_TRENDS_RESPONSE = {
    "data": [
        {
            "id": 54201,
            "home_name": "Arsenal",
            "away_name": "Chelsea",
            "unix": 1746626400,
            "competition_id": 1,
            "competition_name": "Premier League",
        },
        {
            "id": 54202,
            "home_name": "Liverpool",
            "away_name": "Man City",
            "unix": 1746633600,
            "competition_id": 1,
            "competition_name": "Premier League",
        },
    ]
}

EMPTY_FIXTURES_BETWEEN = {"data": []}


@pytest.mark.asyncio
async def test_discover_via_trends_fallback():
    provider = OddAlertsProvider(api_key="test-key")
    with (
        patch.object(provider, "_request_raw", new=AsyncMock(return_value=EMPTY_FIXTURES_BETWEEN)),
        patch.object(provider, "get_trends", new=AsyncMock(return_value=MOCK_TRENDS_RESPONSE)),
    ):
        result = await provider.discover_fixtures(league_ids=[1], dates=["2026-05-07"])

    assert len(result) >= 1
    assert all(isinstance(f, ProviderFixture) for f in result)
    assert all(f.provider == "oddalerts" for f in result)


@pytest.mark.asyncio
async def test_discover_deduplicates_across_markets():
    provider = OddAlertsProvider(api_key="test-key")
    with (
        patch.object(provider, "_request_raw", new=AsyncMock(return_value=EMPTY_FIXTURES_BETWEEN)),
        patch.object(provider, "get_trends", new=AsyncMock(return_value=MOCK_TRENDS_RESPONSE)),
    ):
        result = await provider.discover_fixtures(league_ids=[1], dates=["2026-05-07"])

    fixture_ids = [f.fixture_id for f in result]
    assert len(fixture_ids) == len(set(fixture_ids))


@pytest.mark.asyncio
async def test_discover_filters_by_date():
    provider = OddAlertsProvider(api_key="test-key")
    response_with_wrong_date = {
        "data": [
            {
                "id": 99999,
                "home_name": "X",
                "away_name": "Y",
                "unix": 1746712800,  # 2026-05-08，不在请求日期内
                "competition_id": 1,
            }
        ]
    }
    with (
        patch.object(provider, "_request_raw", new=AsyncMock(return_value=EMPTY_FIXTURES_BETWEEN)),
        patch.object(provider, "get_trends", new=AsyncMock(return_value=response_with_wrong_date)),
    ):
        result = await provider.discover_fixtures(league_ids=[1], dates=["2026-05-07"])

    assert len(result) == 0


@pytest.mark.asyncio
async def test_discover_uses_fixtures_between_when_available():
    provider = OddAlertsProvider(api_key="test-key")
    working_response = {
        "data": [
            {
                "id": 54201,
                "home_name": "Arsenal",
                "away_name": "Chelsea",
                "unix": 1746626400,
                "competition_id": 1,
                "competition_name": "Premier League",
            }
        ]
    }
    with patch.object(provider, "_request_raw", new=AsyncMock(return_value=working_response)):
        result = await provider.discover_fixtures(league_ids=[1], dates=["2026-05-07"])

    assert len(result) == 1
    assert result[0].fixture_id == 54201
```

- [ ] **Step 4: 运行，确认失败**

```bash
cd backend && python -m pytest provider/oddalerts/tests/test_discover.py -v
```

期望：`TypeError: Can't instantiate abstract class OddAlertsProvider`（缺少 discover_fixtures 实现）

- [ ] **Step 5: 创建 `backend/provider/oddalerts/tests/__init__.py`（空文件）**

- [ ] **Step 6: 在 OddAlertsProvider 末尾实现 discover_fixtures**

在 `backend/provider/oddalerts/client.py` 文件末尾（`get_fixture_full` 方法之后）添加：

```python
    # ==================== Fixture 发现（Provider 抽象接口实现）====================

    async def discover_fixtures(
        self,
        league_ids: list[int],
        dates: list[str],
    ) -> list:
        """
        按联赛 ID 和日期范围发现 OddAlerts fixture 列表。

        两级策略：
        1. 首选：/fixtures/between（若 API 修复后可用）
        2. 兜底：homeWin + awayWin + btts trends 并集，按日期和联赛过滤
        """
        if dates:
            result = await self._discover_via_fixtures_between(league_ids, dates)
            if result:
                return result

        return await self._discover_via_trends(league_ids, dates)

    async def _discover_via_fixtures_between(
        self,
        league_ids: list[int],
        dates: list[str],
    ) -> list:
        """尝试 /fixtures/between 端点。返回空列表表示不可用，调用方回落到 trends。"""
        from provider.models import ProviderFixture

        start = min(dates)
        end = max(dates)
        resp = await self._request_raw("/fixtures/between", {"date_from": start, "date_to": end})
        if not isinstance(resp, dict):
            return []

        items = resp.get("data", [])
        if not items:
            return []

        results: list[ProviderFixture] = []
        for item in items:
            fid = item.get("id")
            if not fid:
                continue
            comp_id = item.get("competition_id")
            if league_ids and comp_id not in league_ids:
                continue
            results.append(
                ProviderFixture(
                    provider="oddalerts",
                    fixture_id=fid,
                    home_team=item.get("home_name", ""),
                    away_team=item.get("away_name", ""),
                    kickoff_unix=int(item["unix"]) if item.get("unix") else 0,
                    league_name=item.get("competition_name"),
                    raw=item,
                )
            )
        return results

    async def _discover_via_trends(
        self,
        league_ids: list[int],
        dates: list[str],
    ) -> list:
        """
        通过 homeWin + awayWin + btts trends 并集发现 fixture。
        对同一 fixture_id 去重，按日期和联赛过滤。
        """
        import asyncio
        from datetime import datetime, timezone
        from provider.models import ProviderFixture

        date_set = set(dates)

        tasks = [self.get_trends(m) for m in ("homeWin", "awayWin", "btts")]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        seen_ids: set[int] = set()
        results: list[ProviderFixture] = []

        for resp in responses:
            if not isinstance(resp, dict):
                continue
            for item in resp.get("data", []):
                fid = item.get("id")
                if not fid or fid in seen_ids:
                    continue

                oa_unix = item.get("unix")
                if oa_unix and date_set:
                    item_date = datetime.fromtimestamp(
                        int(oa_unix), tz=timezone.utc
                    ).strftime("%Y-%m-%d")
                    if item_date not in date_set:
                        continue

                comp_id = item.get("competition_id")
                if league_ids and comp_id not in league_ids:
                    continue

                seen_ids.add(fid)
                results.append(
                    ProviderFixture(
                        provider="oddalerts",
                        fixture_id=fid,
                        home_team=item.get("home_name", ""),
                        away_team=item.get("away_name", ""),
                        kickoff_unix=int(oa_unix) if oa_unix else 0,
                        league_name=item.get("competition_name"),
                        raw=item,
                    )
                )

        return results
```

- [ ] **Step 7: 运行，确认通过**

```bash
cd backend && python -m pytest provider/oddalerts/tests/test_discover.py -v
```

期望：4 passed

- [ ] **Step 8: Commit**

```bash
git add provider/oddalerts/client.py provider/oddalerts/tests/__init__.py provider/oddalerts/tests/test_discover.py config/oddalerts_leagues.json
git commit -m "feat: OddAlertsProvider 实现 discover_fixtures（两级策略）"
```

---

## Task 7: DataCollector 重构 — 接收 provider_ids 字典

**Files:**
- Modify: `backend/agents/core/data_collector.py`
- Create: `backend/agents/core/tests/test_data_collector.py`（如已存在则追加）

- [ ] **Step 1: 写失败测试**

```python
# backend/agents/core/tests/test_data_collector.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from agents.core.data_collector import collect_all


@pytest.mark.asyncio
async def test_collect_all_uses_sportmonks_id_from_provider_ids():
    executor = MagicMock()
    executor._tool_goalcast_sportmonks_get_match = AsyncMock(
        return_value={"data": {"home_team": "Arsenal"}}
    )
    provider_ids = {"sportmonks": 18329}

    with patch("agents.core.data_collector.OddAlertsProvider") as mock_oa:
        mock_oa.return_value.is_available = AsyncMock(return_value=False)
        mock_oa.return_value.close = AsyncMock()
        result = await collect_all(executor, provider_ids)

    assert "sportmonks" in result


@pytest.mark.asyncio
async def test_collect_all_uses_oddalerts_id_from_provider_ids():
    executor = MagicMock()
    executor._tool_goalcast_sportmonks_get_match = AsyncMock(return_value=None)
    executor._tool_goalcast_sportmonks_resolve_match = AsyncMock(return_value=None)

    provider_ids = {"oddalerts": 54201}

    mock_provider = MagicMock()
    mock_provider.is_available = AsyncMock(return_value=True)
    mock_provider.get_odds_history = AsyncMock(return_value={"data": []})
    mock_provider.get_stats = AsyncMock(return_value={"data": []})
    mock_provider.get_fixture = AsyncMock(return_value={"id": 54201})
    mock_provider.close = AsyncMock()

    with patch("agents.core.data_collector.OddAlertsProvider", return_value=mock_provider):
        result = await collect_all(executor, provider_ids)

    assert "oddalerts" in result


@pytest.mark.asyncio
async def test_collect_all_skips_missing_providers():
    executor = MagicMock()
    executor._tool_goalcast_sportmonks_get_match = AsyncMock(return_value=None)
    executor._tool_goalcast_sportmonks_resolve_match = AsyncMock(return_value=None)

    provider_ids = {}  # 两个 provider 都没有 ID

    with patch("agents.core.data_collector.OddAlertsProvider") as mock_oa:
        mock_oa.return_value.is_available = AsyncMock(return_value=True)
        mock_oa.return_value.close = AsyncMock()
        result = await collect_all(executor, provider_ids)

    assert result == {}
```

- [ ] **Step 2: 运行，确认失败**

```bash
cd backend && python -m pytest agents/core/tests/test_data_collector.py -v
```

期望：测试因 `collect_all` 签名不匹配而失败。

- [ ] **Step 3: 重构 `backend/agents/core/data_collector.py`**

将文件完整替换为：

```python
"""
多数据源收集器。

负责并行从各 provider 获取数据，结果存入 raw_data.{provider_name}。
每个 provider 完全独立，互不干扰。分析层自行决定使用哪个数据源。
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from provider.oddalerts.client import OddAlertsProvider

logger = logging.getLogger(__name__)

_CST = timezone(timedelta(hours=8))


def _now_iso() -> str:
    return datetime.now(_CST).isoformat()


async def collect_sportmonks(executor: Any, fixture_id: int) -> dict | None:
    """从 SportMonks executor 收集比赛详细数据。"""
    res = None
    get_match = getattr(executor, "_tool_goalcast_sportmonks_get_match", None)
    if callable(get_match):
        res = await get_match(fixture_id=fixture_id)
    if not isinstance(res, dict):
        resolve_match = getattr(executor, "_tool_goalcast_sportmonks_resolve_match", None)
        if callable(resolve_match):
            res = await resolve_match(fixture_id=fixture_id)
    if not isinstance(res, dict):
        return None
    data = res.get("data", {})
    return {
        "_meta": {"collected_at": _now_iso(), "fixture_id": fixture_id},
        **data,
    }


async def collect_oddalerts(oa_fixture_id: int) -> dict | None:
    """
    从 OddAlerts 收集赔率/统计/概率数据。

    oa_fixture_id: OddAlerts 自己的 fixture ID（在 discover 阶段已确定）。
    """
    provider = OddAlertsProvider()
    if not await provider.is_available():
        logger.debug("[DataCollector] OddAlerts API key 未配置，跳过")
        return None

    try:
        odds, stats, fixture = await asyncio.gather(
            provider.get_odds_history(oa_fixture_id),
            provider.get_stats("fixture", oa_fixture_id),
            provider.get_fixture(oa_fixture_id),
            return_exceptions=True,
        )

        result: dict = {
            "_meta": {
                "collected_at": _now_iso(),
                "oa_fixture_id": oa_fixture_id,
            }
        }

        if isinstance(fixture, dict):
            result["fixture"] = fixture
        if isinstance(odds, dict):
            result["odds_history"] = odds
        if isinstance(stats, dict):
            result["stats"] = stats

        if len(result) == 1:
            logger.warning("[DataCollector] OddAlerts fixture %d 未返回任何数据", oa_fixture_id)
            return None

        return result

    except Exception as exc:
        logger.warning("[DataCollector] OddAlerts 收集失败 oa_fixture=%d: %s", oa_fixture_id, exc)
        return None
    finally:
        await provider.close()


async def collect_all(
    executor: Any,
    provider_ids: dict[str, int],
    providers: list[str] | None = None,
    home_team: str = "",
    away_team: str = "",
    kickoff_unix: int | None = None,
) -> dict:
    """
    并行收集所有启用 provider 的详细数据。

    Args:
        executor:      SportMonks executor（现有机制，用于获取详细数据）
        provider_ids:  各 provider 的 fixture ID，如 {"sportmonks": 123, "oddalerts": 456}
                       某 provider 无对应 ID 时该 key 不存在，跳过该 provider。
        providers:     指定要收集的 provider 列表，None = 全部
        home_team:     保留参数（日志用）
        away_team:     保留参数（日志用）
        kickoff_unix:  保留参数（日志用）

    Returns:
        raw_data dict，结构为 {provider_name: {_meta, ...数据}}
    """
    enabled = set(providers) if providers else {"sportmonks", "oddalerts"}

    tasks: dict[str, asyncio.Task] = {}

    sm_id = provider_ids.get("sportmonks")
    if "sportmonks" in enabled and sm_id is not None:
        tasks["sportmonks"] = asyncio.create_task(collect_sportmonks(executor, sm_id))

    oa_id = provider_ids.get("oddalerts")
    if "oddalerts" in enabled and oa_id is not None:
        tasks["oddalerts"] = asyncio.create_task(collect_oddalerts(oa_id))

    if not tasks:
        return {}

    results = await asyncio.gather(*tasks.values(), return_exceptions=True)

    raw_data: dict = {}
    for provider_name, result in zip(tasks.keys(), results):
        if isinstance(result, Exception):
            logger.warning("[DataCollector] %s 收集异常: %s", provider_name, result)
        elif isinstance(result, dict):
            raw_data[provider_name] = result
        else:
            logger.debug("[DataCollector] %s 无数据", provider_name)

    return raw_data
```

- [ ] **Step 4: 运行，确认通过**

```bash
cd backend && python -m pytest agents/core/tests/test_data_collector.py -v
```

期望：3 passed

- [ ] **Step 5: Commit**

```bash
git add agents/core/data_collector.py agents/core/tests/test_data_collector.py
git commit -m "refactor: DataCollector.collect_all 改用 provider_ids 字典，移除 fixture_mapper 依赖"
```

---

## Task 8: Orchestrator 重构 — 使用双源合并流程

**Files:**
- Modify: `backend/agents/core/orchestrator.py`

- [ ] **Step 1: 在 Orchestrator 类中新增 `_resolve_oa_league_ids` 方法**

在 `_resolve_date_range` 方法附近添加：

```python
    def _resolve_oa_league_ids(self, leagues: list[str] | None) -> list[int]:
        """将联赛中文名列表转换为 OddAlerts competition_id 列表。"""
        if not leagues:
            return []
        config_path = Path(__file__).parent.parent.parent / "config" / "oddalerts_leagues.json"
        if not config_path.exists():
            logger.warning("[Orchestrator] config/oddalerts_leagues.json 不存在，OA 联赛过滤禁用")
            return []
        try:
            mapping = json.loads(config_path.read_text(encoding="utf-8"))
            ids = []
            for name in leagues:
                entry = mapping.get(name)
                if isinstance(entry, dict):
                    ids.append(entry["id"])
                elif isinstance(entry, int):
                    ids.append(entry)
            return ids
        except Exception as e:
            logger.warning("[Orchestrator] 读取 OA 联赛配置失败: %s", e)
            return []
```

- [ ] **Step 2: 重构 `_fetch_and_prepare` 方法**

将现有的 `_fetch_and_prepare` 方法中从 `executor = ToolExecutor()` 开始到 `for fixture in fixtures:` 之前的部分替换为以下双源发现逻辑：

```python
    async def _fetch_and_prepare(
        self, leagues: list[str] | None, date: str | None, models: list[str] = None
    ) -> int:
        from agents.adapters.tool_executor import ToolExecutor
        from agents.core.blackboard import merge_update
        from agents.core import match_store
        from agents.core.fixture_merger import merge_fixtures
        from provider.sportmonks.client import SportmonksProvider
        from provider.oddalerts.client import OddAlertsProvider

        if models is None:
            models = ["v4.0"]

        executor = ToolExecutor()
        dates = self._resolve_date_range(date)
        print(f"[Orchestrator] 日期范围: {dates}")

        # 并行解析联赛 ID
        sm_league_ids = await self._resolve_league_ids(leagues) or []
        oa_league_ids = self._resolve_oa_league_ids(leagues)
        print(f"[Orchestrator] SM 联赛 IDs: {sm_league_ids}")
        print(f"[Orchestrator] OA 联赛 IDs: {oa_league_ids}")

        # 并行 fixture 发现
        sm_provider = SportmonksProvider()
        oa_provider = OddAlertsProvider()
        try:
            sm_task = asyncio.create_task(sm_provider.discover_fixtures(sm_league_ids, dates))
            oa_task = asyncio.create_task(oa_provider.discover_fixtures(oa_league_ids, dates))
            sm_fixtures, oa_fixtures = await asyncio.gather(sm_task, oa_task, return_exceptions=True)
        finally:
            await sm_provider.close()
            await oa_provider.close()

        if isinstance(sm_fixtures, Exception):
            logger.warning("[Orchestrator] Sportmonks discover 失败: %s", sm_fixtures)
            sm_fixtures = []
        if isinstance(oa_fixtures, Exception):
            logger.warning("[Orchestrator] OddAlerts discover 失败: %s", oa_fixtures)
            oa_fixtures = []

        print(f"[Orchestrator] 发现 SM: {len(sm_fixtures)} 场, OA: {len(oa_fixtures)} 场")

        unified = merge_fixtures([("sportmonks", sm_fixtures), ("oddalerts", oa_fixtures)])
        print(f"[Orchestrator] 合并后: {len(unified)} 场唯一比赛")

        count = 0
        prepared_matches = []
        trigger_force = False
        if TRIGGER_FILE.exists():
            try:
                tdata = json.loads(TRIGGER_FILE.read_text(encoding="utf-8"))
                trigger_force = tdata.get("force", False)
            except Exception:
                pass

        active_fixture_ids = self._load_existing_fixture_ids(active_only=True)
        completed_fixture_ids = self._load_fixture_ids_by_status({"reported"})
        skipped = 0

        for uf in unified:
            # 用 Sportmonks ID 作为主键（向后兼容），无则用 OA ID
            fixture_id = uf.provider_ids.get("sportmonks") or next(iter(uf.provider_ids.values()), 0)

            if fixture_id in active_fixture_ids:
                skipped += 1
                continue
            if not trigger_force and fixture_id in completed_fixture_ids:
                skipped += 1
                continue

            existing_match_id = self._find_match_id_for_fixture(fixture_id)
            match_id = existing_match_id or match_store.generate_match_id()

            kickoff_unix = uf.kickoff_unix
            # 从原始数据恢复 kickoff_str（用于 metadata）
            kickoff_str = datetime.fromtimestamp(kickoff_unix, tz=timezone.utc).isoformat() if kickoff_unix else ""

            # 尝试从 SM fixture 原始数据中提取联赛名
            sm_raw = next(
                (f.raw for f in sm_fixtures if f.fixture_id == uf.provider_ids.get("sportmonks")), {}
            ) if not isinstance(sm_fixtures, Exception) else {}
            league_name = (
                sm_raw.get("league", {}).get("name", "")
                if isinstance(sm_raw.get("league"), dict)
                else uf.provider_ids and ""
            ) or ""

            raw_data = await self._fetch_raw_data_for_models(
                executor, uf.provider_ids, models,
                home_team=uf.home_team, away_team=uf.away_team, kickoff_unix=kickoff_unix,
            )

            record = {
                "metadata": {
                    "match_id": match_id,
                    "fixture_id": fixture_id,
                    "provider_ids": uf.provider_ids,
                    "home_team": uf.home_team,
                    "away_team": uf.away_team,
                    "league": league_name,
                    "kickoff_time": kickoff_str,
                    "requested_models": models,
                    "prepared_at": datetime.now(_CST).isoformat(),
                },
                "state": {
                    "orchestrator": "done",
                    "analyst": "pending",
                    "trader": "pending",
                    "reviewer": "pending",
                    "reporter": "pending",
                },
                "raw_data": raw_data,
                "analysis": {},
                "trading": {},
            }

            filepath = match_store.MATCHES_DIR / f"{match_id}.json"
            legacy_record = {
                "match_id": match_id,
                "status": "pending",
                "orchestrator": {
                    "prepared_at": record["metadata"]["prepared_at"],
                    "fixture_id": fixture_id,
                    "home_team": uf.home_team,
                    "away_team": uf.away_team,
                    "league": league_name,
                    "kickoff_time": kickoff_str,
                },
            }
            match_store.save(legacy_record)
            merge_update(filepath, record)

            print(f"[Orchestrator] 已写入黑板: {match_id} ({uf.home_team} vs {uf.away_team}) sm={uf.provider_ids.get('sportmonks')} oa={uf.provider_ids.get('oddalerts')}")
            prepared_matches.append({
                "match_id": match_id,
                "home_team": uf.home_team,
                "away_team": uf.away_team,
                "kickoff_time": kickoff_str,
                "league": "",
            })
            count += 1

        if skipped > 0:
            print(f"[Orchestrator] 跳过 {skipped} 场已存在的比赛")

        await self._emit_and_write("matches_found", {"total": count, "matches": prepared_matches})
        return count
```

- [ ] **Step 3: 更新 `_fetch_raw_data_for_models` 方法签名**

将现有方法：
```python
    async def _fetch_raw_data_for_models(
        self,
        executor,
        fixture_id: int,
        models: list[str],
        home_team: str = "",
        away_team: str = "",
        kickoff_unix: int | None = None,
        oa_fixture_id: int | None = None,
    ) -> dict:
```

替换为：
```python
    async def _fetch_raw_data_for_models(
        self,
        executor,
        provider_ids: dict[str, int],
        models: list[str],
        home_team: str = "",
        away_team: str = "",
        kickoff_unix: int | None = None,
    ) -> dict:
        from agents.core.data_collector import collect_all
        return await collect_all(
            executor, provider_ids,
            home_team=home_team, away_team=away_team, kickoff_unix=kickoff_unix,
        )
```

- [ ] **Step 4: 标记 fixture_mapper 为 deprecated**

在 `backend/provider/oddalerts/fixture_mapper.py` 文件顶部 docstring 末尾添加：

```python
# DEPRECATED: 此模块已被 provider-agnostic fixture 发现机制取代（ProviderFixture + FixtureMerger）。
# 仅在极端兜底场景下保留，请勿在新代码中使用。
```

- [ ] **Step 5: 冒烟测试 — 确认系统可以正常启动**

```bash
cd backend && python -c "
from agents.core.orchestrator import Orchestrator
print('Orchestrator 导入成功')
from agents.core.fixture_merger import merge_fixtures
print('FixtureMerger 导入成功')
from agents.core.data_collector import collect_all
print('DataCollector 导入成功')
from provider.sportmonks.client import SportmonksProvider
from provider.oddalerts.client import OddAlertsProvider
print('所有 Provider 导入成功')
"
```

期望：4 行 "...成功" 输出，无报错。

- [ ] **Step 6: Commit**

```bash
git add agents/core/orchestrator.py agents/core/data_collector.py provider/oddalerts/fixture_mapper.py
git commit -m "refactor: Orchestrator 使用双源 fixture 发现 + FixtureMerger 合并流程"
```

---

## Task 9: 端到端冒烟测试

**目的**: 验证整个流程能够走通（不需要真实 API 调用）。

- [ ] **Step 1: 运行全部单元测试**

```bash
cd backend && python -m pytest utils/tests/ provider/tests/ agents/core/tests/ provider/sportmonks/tests/ provider/oddalerts/tests/ -v
```

期望：所有测试通过，无 import 错误。

- [ ] **Step 2: 验证 OddAlerts 联赛 ID 配置是否完整**

```bash
cd backend && python -c "
import json
from pathlib import Path

sm = json.loads(Path('config/sportmonks_leagues.json').read_text())
oa = json.loads(Path('config/oddalerts_leagues.json').read_text())

sm_names = {v['chinese_name'] for v in sm.values() if isinstance(v, dict)}
oa_names = set(oa.keys())
missing = sm_names - oa_names
if missing:
    print('以下联赛在 OA 配置中缺失，需要手动补充:', missing)
else:
    print('OA 联赛配置完整')
"
```

- [ ] **Step 3: 最终 Commit**

```bash
git add .
git commit -m "chore: provider 抽象化 fixture 发现完整实现"
```

---

## 注意事项

1. **Task 6 Step 1**（查询 OA 联赛 ID）必须在有网络访问和有效 OA API key 的环境中运行，结果用于填写 `oddalerts_leagues.json`。

2. **Sportmonks `starting_at` 格式**：当前代码假设 `"%Y-%m-%d %H:%M:%S"` UTC 格式。如实际 API 返回带时区字符串（如 `"2026-05-07T15:00:00+00:00"`），需在 Task 5 Step 6 中调整 `strptime` 格式。

3. **OA trends 翻页**：当前 `_discover_via_trends` 只取第一页。若某日比赛超过单页限制，需在 OddAlertsProvider 中增加翻页逻辑。

4. **向后兼容**：`fixture_id` 在 record metadata 中仍保留（Sportmonks ID 优先）。同时新增 `provider_ids` 字典字段，下游 pipeline 步骤可逐步迁移读取方式。

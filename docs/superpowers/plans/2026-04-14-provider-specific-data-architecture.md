# Provider-Specific Data Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a decentralized data pipeline that pre-warms raw provider data into local JSON/SQLite caches, and introduce provider-specific Analyst skills to directly analyze the raw data.

**Architecture:** A daily pre-warming script fetches API responses and dual-writes them to JSON files and a SQLite database. A lightweight `CacheReader` replaces the heavy `DataFusion` layer. Two new skills (`sportmonks-analyst-v1`, `footystats-analyst-v1`) guide the AI to interpret these raw cached files without needing a unified data contract.

**Tech Stack:** Python, SQLite, JSON, Pydantic/dataclass (optional), existing Provider API clients.

---

### Task 1: Create the Cache Reader Utility

**Files:**
- Create: `utils/cache_reader.py`
- Test: `tests/utils/test_cache_reader.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/utils/test_cache_reader.py
import json
import pytest
from pathlib import Path
from utils.cache_reader import get_cached_matches

def test_get_cached_matches(tmp_path):
    # Setup mock cache
    date_str = "2026-04-14"
    provider = "sportmonks"
    cache_dir = tmp_path / "cache" / date_str / provider
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    mock_data = [{"id": 1, "league_id": 10}, {"id": 2, "league_id": 20}]
    (cache_dir / "matches.json").write_text(json.dumps(mock_data))
    
    # Test read all
    res = get_cached_matches(provider, date_str, base_path=tmp_path / "cache")
    assert len(res) == 2
    
    # Test read with league filter
    res_filtered = get_cached_matches(provider, date_str, leagues=[10], base_path=tmp_path / "cache")
    assert len(res_filtered) == 1
    assert res_filtered[0]["id"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/utils/test_cache_reader.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'utils.cache_reader'"

- [ ] **Step 3: Write minimal implementation**

```python
# utils/cache_reader.py
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

def get_cached_matches(
    provider: str, 
    date: str, 
    leagues: Optional[List[int]] = None,
    base_path: Path = Path("data/cache")
) -> List[Dict[str, Any]]:
    """
    Reads pre-warmed JSON cache for a given provider and date.
    Filters by league_id if provided.
    """
    file_path = base_path / date / provider / "matches.json"
    if not file_path.exists():
        return []
        
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []
        
    if not isinstance(data, list):
        return []
        
    if leagues is not None:
        # Assumes the raw data has 'league_id' for Sportmonks or 'competition_id' for Footystats
        # We try to find the standard league ID field
        filtered = []
        for match in data:
            match_league = match.get("league_id") or match.get("competition_id")
            if match_league in leagues:
                filtered.append(match)
        return filtered
        
    return data
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/utils/test_cache_reader.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add utils/cache_reader.py tests/utils/test_cache_reader.py
git commit -m "feat: add cache reader utility for provider raw data"
```

### Task 2: Create Data Pre-warming Script

**Files:**
- Create: `scripts/prewarm_cache.py`

- [x] **Step 1: Write the implementation**

```python
# scripts/prewarm_cache.py
import asyncio
import json
import sqlite3
import argparse
from datetime import datetime
from pathlib import Path

from provider.sportmonks.client import SportmonksProvider
from provider.footystats.client import FootystatsProvider
from utils.config_parser import load_config

async def prewarm_sportmonks(date_str: str, config: dict, base_path: Path, db: sqlite3.Connection):
    provider = SportmonksProvider()
    if not await provider.is_available():
        print("Sportmonks API unavailable")
        return
        
    # Get configured leagues
    leagues_config = config.get("sportmonks", {}).get("leagues", [])
    
    # Use fixtures between to get matches for the specific date
    res = await provider.get_fixtures_between(
        date_str, 
        date_str, 
        include="participants,league,statistics,lineups,odds"
    )
    
    matches = res.get("data", []) if res else []
    
    # Save to JSON
    out_dir = base_path / date_str / "sportmonks"
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "matches.json", "w", encoding="utf-8") as f:
        json.dump(matches, f, ensure_ascii=False, indent=2)
        
    # Save to SQLite
    cursor = db.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS raw_sportmonks_matches (
            match_id INTEGER PRIMARY KEY,
            date TEXT,
            league_id INTEGER,
            raw_data TEXT
        )
    """)
    for m in matches:
        cursor.execute(
            "INSERT OR REPLACE INTO raw_sportmonks_matches VALUES (?, ?, ?, ?)",
            (m.get("id"), date_str, m.get("league_id"), json.dumps(m))
        )
    db.commit()
    print(f"Pre-warmed {len(matches)} Sportmonks matches for {date_str}")

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    args = parser.parse_args()
    
    config = load_config("config/watchlist.yaml")
    base_path = Path("data/cache")
    base_path.mkdir(parents=True, exist_ok=True)
    
    db_path = base_path / "goalcast.db"
    db = sqlite3.connect(db_path)
    
    await asyncio.gather(
        prewarm_sportmonks(args.date, config, base_path, db),
        # Add Footystats prewarming here later if needed
    )
    
    db.close()

if __name__ == "__main__":
    asyncio.run(main())
```

- [x] **Step 2: Test the script**

Run: `python scripts/prewarm_cache.py --date 2026-04-14`
Expected: Output showing matches were pre-warmed, and `data/cache/2026-04-14/sportmonks/matches.json` should exist.

- [x] **Step 3: Commit**

```bash
git add scripts/prewarm_cache.py
git commit -m "feat: add script to pre-warm match data to local JSON and SQLite caches"
```

### Task 3: Create Sportmonks Analyst Skill

**Files:**
- Create: `skills/sportmonks-analyst-v1/SKILL.md`

- [x] **Step 1: Write the Skill Markdown file**

```markdown
---
name: sportmonks-analyst-v1
description: Use this skill when you need to analyze football matches using pre-warmed Sportmonks raw data. Focuses on extracting xG, lineups, and odds movement directly from Sportmonks JSON.
---

# Sportmonks Analyst Skill v1

## 📋 Overview
This skill instructs the agent on how to act as a football analyst relying **exclusively** on Sportmonks raw data cached locally.

## 🎯 When to use
Trigger when the user asks to "analyze today's matches with sportmonks", "use sportmonks analyst", or "predict matches based on sportmonks data".

## 🛠️ Data Access
Do not call the Sportmonks API directly. Instead, read the pre-warmed JSON cache:

```python
from utils.cache_reader import get_cached_matches

# Get today's matches
matches = get_cached_matches(provider="sportmonks", date="2026-04-14")
```

## 🧠 Analysis Strategy
1. **Read JSON**: Iterate through the matches.
2. **Extract Key Metrics**:
   - `participants`: Find home and away team names.
   - `lineups`: Check if formations are confirmed.
   - `statistics`: Extract detailed match statistics (xG if available).
   - `odds`: Extract pre-match odds or movement.
3. **Generate Insight**: Write a detailed markdown report for each match, highlighting tactical advantages, formation strengths, and value bets derived from the Sportmonks-specific fields.

## ⚠️ Constraints
- Never rely on `DataFusion` or `MatchContext`.
- Accept that some fields might be nested deeply in the raw Sportmonks JSON. Use `dict.get()` extensively to avoid KeyErrors.
```

- [x] **Step 2: Commit**

```bash
git add skills/sportmonks-analyst-v1/SKILL.md
git commit -m "feat: add sportmonks-analyst-v1 skill for analyzing raw sportmonks cache"
```

### Task 4: Create Footystats Analyst Skill

**Files:**
- Create: `skills/footystats-analyst-v1/SKILL.md`

- [x] **Step 1: Write the Skill Markdown file**

```markdown
---
name: footystats-analyst-v1
description: Use this skill when you need to analyze football matches using pre-warmed Footystats raw data. Focuses on recent form, xG proxies, and advanced stats from Footystats JSON.
---

# Footystats Analyst Skill v1

## 📋 Overview
This skill instructs the agent on how to act as a football analyst relying **exclusively** on Footystats raw data cached locally.

## 🎯 When to use
Trigger when the user asks to "analyze today's matches with footystats", "use footystats analyst", or "predict matches based on footystats data".

## 🛠️ Data Access
Do not call the Footystats API directly. Instead, read the pre-warmed JSON cache:

```python
from utils.cache_reader import get_cached_matches

# Get today's matches
matches = get_cached_matches(provider="footystats", date="2026-04-14")
```

## 🧠 Analysis Strategy
1. **Read JSON**: Iterate through the Footystats matches.
2. **Extract Key Metrics**:
   - `homeID` / `awayID`: Team identifiers.
   - `home_ppg` / `away_ppg`: Points per game.
   - `seasonScoredAVG_overall` / `seasonConcededAVG_overall`: proxy for offensive/defensive strength.
   - `odds_ft_1` / `odds_ft_x` / `odds_ft_2`: Match odds.
3. **Generate Insight**: Write a detailed markdown report focusing on statistical trends, recent form, and goal probabilities derived from Footystats fields.

## ⚠️ Constraints
- Never rely on `DataFusion` or `MatchContext`.
- Focus solely on the statistical depth provided by Footystats.
```

- [x] **Step 2: Commit**

```bash
git add skills/footystats-analyst-v1/SKILL.md
git commit -m "feat: add footystats-analyst-v1 skill for analyzing raw footystats cache"
```

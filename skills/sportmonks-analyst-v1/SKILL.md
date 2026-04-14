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

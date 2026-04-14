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

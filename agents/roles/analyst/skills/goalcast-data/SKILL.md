---
name: goalcast-data
description: Access and retrieve football data from FootyStats and Sportmonks via the Goalcast MCP server. Use for match details, league standings, team stats, head-to-head comparisons, and market odds analysis.
---

# Goalcast Data

This skill provides access to 25 specialized football data tools via the `goalcast` MCP server. It supports deep quantitative analysis by fetching both historical and real-time data from two major providers: **FootyStats** and **Sportmonks**.

## Core Providers

### 1. FootyStats (12 tools)
Best for: Detailed league-wide statistics, historical team form, and finding matches for a specific date.
- **Match Discovery**: `footystats_get_todays_matches` (use `league_filter` to avoid large responses).
- **Team Analysis**: `footystats_get_team_details`, `footystats_get_team_last_x_stats`.
- **League Context**: `footystats_get_league_tables`, `footystats_get_league_stats`.
- **Prop Markets**: `footystats_get_btts_stats`, `footystats_get_over25_stats`.

### 2. Sportmonks (13 tools)
Best for: Real-time data, detailed lineups, xG depth data, and market odds movement.
- **Match Details**: `sportmonks_get_fixture_by_id`, `sportmonks_get_expected_goals`.
- **Live Coverage**: `sportmonks_get_livescores`.
- **Market Intel**: `sportmonks_get_odds_movement`, `sportmonks_get_prematch_odds`, `sportmonks_get_value_bets`.
- **Lineups**: `sportmonks_get_lineups`, `sportmonks_get_player_stats`.

## Execution Protocol

### Step 1: Tool Discovery
If you are unsure of a tool's parameters, use:
```bash
mcporter list goalcast --schema
```

### Step 2: Match Identification
Always start by finding the specific match or league ID.
- To find today's matches in a league:
  ```bash
  mcporter call goalcast.footystats_get_todays_matches league_filter="Premier League"
  ```
- To find fixtures by date:
  ```bash
  mcporter call goalcast.sportmonks_get_fixtures_by_date date="2026-04-07"
  ```

### Step 3: Deep Data Retrieval
Use the IDs found in Step 2 to get granular details.
- **xG Data**: `mcporter call goalcast.sportmonks_get_expected_goals fixture_id=<id>`
- **Odds Movement**: `mcporter call goalcast.sportmonks_get_odds_movement fixture_id=<id>`
- **Team Form**: `mcporter call goalcast.footystats_get_team_last_x_stats team_id=<id>`

## Critical Constraints

1. **Data Volume Management**: Global fixture lists can exceed 1MB. **Always** use filters (like `league_filter`) when calling discovery tools.
2. **Timeout Prevention**: If a request times out, it is likely due to excessive data. Request specific IDs or use pagination (if supported).
3. **Consistency**: Use FootyStats for "Hard Stats" (League/Team totals) and Sportmonks for "Soft Stats" (Lineups/xG/Market).

## Examples

### Scenario: Analyze a Premier League match today
1. **Find Match**: `mcporter call goalcast.footystats_get_todays_matches league_filter="Premier League"`
2. **Get Details**: `mcporter call goalcast.footystats_get_match_details match_id=<id>`
3. **Check xG**: `mcporter call goalcast.sportmonks_get_expected_goals fixture_id=<id>`
4. **Analyze Odds**: `mcporter call goalcast.sportmonks_get_odds_movement fixture_id=<id>`

### Scenario: Check Value Bets
```bash
mcporter call goalcast.sportmonks_get_value_bets
```

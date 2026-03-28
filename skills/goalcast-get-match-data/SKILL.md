---
name: goalcast-get-match-data
description: "获取足球比赛的完整分析数据（基础信息、统计数据、高级数据、赔率、球队对比）。作为 goalcast-analyze 技能的前置数据获取步骤。当用户询问比赛数据、分析比赛、获取比赛信息时触发。"
version: "1.0.0"
author: "Goalcast"
tags: ["football", "match-data", "analysis", "pre-analysis"]
metadata:
  openclaw:
    emoji: "📊"
---

# Goalcast Get Match Data

## Purpose

获取指定比赛 ID 的完整数据，为 8 层量化分析做准备。调用 `python -m cmd.match_data_cmd get_match_analysis <match_id>` 并解析输出。

## Workflow

1. 接收 `match_id` 参数
2. 执行命令：`python -m cmd.match_data_cmd get_match_analysis <match_id>`
3. 解析命令输出为结构化数据
4. 返回完整的比赛数据报告

## Command

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast
.venv/bin/python -m cmd.match_data_cmd get_match_analysis <match_id>
```

## Input

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `match_id` | string | 是 | FootyStats 比赛 ID |

## Output

返回结构化 JSON，包含以下字段：

```json
{
  "match_info": {
    "home_team": "主队名称",
    "away_team": "客队名称",
    "competition": "联赛名称",
    "match_time": "比赛时间",
    "status": "比赛状态"
  },
  "basic": {
    "home_team_name": "",
    "away_team_name": "",
    "match_time": "",
    "home_score": null,
    "away_score": null,
    "status": ""
  },
  "stats": {
    "has_valid_stats": true,
    "home_possession": 50,
    "away_possession": 50,
    "home_total_shots": 10,
    "away_total_shots": 8,
    "home_shots_on_target": 4,
    "away_shots_on_target": 3,
    "home_corners": 5,
    "away_corners": 4,
    "home_yellow_cards": 1,
    "away_yellow_cards": 2,
    "btts": true,
    "over_25": true
  },
  "advanced": {
    "has_xg_prematch": true,
    "home_xg_prematch": 1.5,
    "away_xg_prematch": 1.2,
    "total_xg_prematch": 2.7,
    "has_xg": true,
    "home_xg": 1.8,
    "away_xg": 1.1,
    "home_attacks": 85,
    "away_attacks": 72,
    "home_dangerous_attacks": 45,
    "away_dangerous_attacks": 38,
    "has_lineups": true,
    "home_lineup": ["player1", "player2"],
    "away_lineup": ["player1", "player2"],
    "home_trends": ["趋势1", "趋势2"],
    "away_trends": ["趋势1", "趋势2"],
    "btts_potential": 65,
    "btts_fhg_potential": 35,
    "btts_2hg_potential": 45,
    "o25_potential": 60,
    "matches_completed_minimum": 15
  },
  "odds": {
    "odds_home": 2.1,
    "odds_draw": 3.4,
    "odds_away": 3.5,
    "implied_prob_home": 0.452,
    "implied_prob_draw": 0.279,
    "implied_prob_away": 0.269,
    "has_pinnacle_odds": true,
    "pinnacle_odds": {
      "home": 2.05,
      "draw": 3.50,
      "away": 3.60,
      "implied_prob_home": 0.465,
      "implied_prob_draw": 0.272,
      "implied_prob_away": 0.263
    },
    "has_full_1x2_odds": true
  },
  "teams": {
    "home_form": {
      "last_5_wins": 3,
      "last_5_draws": 1,
      "last_5_losses": 1,
      "last_5_ppg": 2.0
    },
    "away_form": {
      "last_5_wins": 2,
      "last_5_draws": 2,
      "last_5_losses": 1,
      "last_5_ppg": 1.6
    },
    "h2h_total": 10,
    "h2h_home_wins": 5,
    "h2h_away_wins": 3,
    "h2h_draws": 2,
    "h2h_avg_goals": 2.4,
    "h2h_btts_percentage": 60,
    "h2h_over_25_percentage": 55,
    "home_season_stats": {
      "position": 3,
      "points": 45,
      "ppg": 1.8,
      "wins": 14,
      "draws": 3,
      "losses": 5,
      "goals_scored": 42,
      "goals_conceded": 25,
      "avg_goals_scored": 1.68,
      "avg_goals_conceded": 1.0,
      "xg_for_avg_home": 1.65,
      "xg_against_avg_home": 0.95,
      "clean_sheet_percentage_overall": 35,
      "clean_sheet_percentage_home": 42,
      "clean_sheet_percentage_away": 28,
      "btts_percentage_overall": 58,
      "btts_percentage_home": 62,
      "btts_percentage_away": 54,
      "over_25_percentage_overall": 55,
      "over_25_percentage_home": 58,
      "over_25_percentage_away": 52
    },
    "away_season_stats": {
      "position": 8,
      "points": 35,
      "ppg": 1.4,
      "wins": 10,
      "draws": 5,
      "losses": 8,
      "goals_scored": 32,
      "goals_conceded": 30,
      "avg_goals_scored": 1.28,
      "avg_goals_conceded": 1.2,
      "xg_for_avg_away": 1.15,
      "xg_against_avg_away": 1.35,
      "clean_sheet_percentage_overall": 30,
      "clean_sheet_percentage_home": 35,
      "clean_sheet_percentage_away": 25,
      "btts_percentage_overall": 52,
      "btts_percentage_home": 55,
      "btts_percentage_away": 49,
      "over_25_percentage_overall": 48,
      "over_25_percentage_home": 50,
      "over_25_percentage_away": 46
    },
    "strength_difference": 0.4
  }
}
```

## Error Handling

如果命令执行失败，返回错误信息：

```json
{
  "error": true,
  "message": "比赛数据获取失败",
  "details": "命令返回码或错误信息"
}
```

## Notes

- 使用 `.venv/bin/python` 确保使用正确的虚拟环境
- 如果比赛不存在或 API 不可用，返回适当的错误信息
- 数据质量由调用方（goalcast-analyze）评估

## Example

**Input:**
```
match_id: "8469819"
```

**Command:**
```bash
.venv/bin/python -m cmd.match_data_cmd get_match_analysis 8469819
```

**Output:**
返回上述 JSON 结构，包含比赛的所有分析数据。

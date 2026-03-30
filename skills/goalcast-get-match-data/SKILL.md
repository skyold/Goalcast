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

获取指定比赛 ID 的完整数据，为 8 层量化分析做准备。调用 `python -m cmd.match_data_cmd get_match_analysis <match_id>` 并将输出文本直接传递给 `goalcast-analyze`。

## Workflow

1. 接收 `match_id` 参数
2. 执行命令：`.venv/bin/python -m cmd.match_data_cmd get_match_analysis <match_id>`
3. 将命令输出的文本报告**原文**传递给 `goalcast-analyze`，不需要 JSON 解析
4. 如命令失败（非零退出码），返回错误信息

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

命令输出为**人类可读的文本报告**，不是 JSON。报告由多个节段组成，每节以 `[节名]` 为标题。`goalcast-analyze` 直接按节名定位所需字段读取数据。

节段列表：

| 节名 | 内容 |
|------|------|
| `[BASIC INFO]` | 对阵、时间、状态、比分 |
| `[XG ANALYSIS]` | 赛前预期进球 xG，主客队差值 |
| `[VENUE-SPECIFIC PPG]` | 主队主场 PPG / 客队客场 PPG |
| `[HOME ADVANTAGE]` | 主场进攻/防守/整体优势值 |
| `[H2H RECORD]` | 历史交锋场次、胜平负、BTTS%、Over 2.5% |
| `[POTENTIALS & CONTRADICTIONS]` | BTTS/O25/O35 概率，矛盾信号 |
| `[HOME TEAM DETAILED STATS]` | 主队净胜球%、BTTS%、Over 2.5%（含主客场拆分） |
| `[AWAY TEAM DETAILED STATS]` | 客队对应统计 |
| `[VENUE-SPECIFIC XG]` | 主队主场 xG For/Against，客队客场 xG For/Against |
| `[ODDS ANALYSIS]` | Pinnacle 赔率、Soft 赔率、差异、特殊盘 |
| `[TRENDS]` | 主客队近期趋势文字描述 |
| `[SUMMARY - KEY SIGNALS]` | 关键信号汇总 |
| `[2ND HALF ODDS]` | 下半场赔率 |
| `[DATA QUALITY NOTES]` | 小样本警告、赔率使用说明 |

## Output Example

```
============================================================
=== MATCH ANALYSIS: 8469819 ===
============================================================

[BASIC INFO]
  TeamA vs TeamB
  Time: 2026-03-30 20:00:00
  Status: incomplete

[XG ANALYSIS]
  Pre-match xG (system estimate): Home 1.45 / Away 1.12
  Total xG: 2.57
  xG Difference: +0.33 (positive=home advantage)

[TEAM FORM]
  Home Team (Position: 3)
    PPG: 1.80 | Win%: 56.0%
    Goals: 42 | Conceded: 25
  Away Team (Position: 8)
    PPG: 1.40 | Win%: 43.0%
  PPG Difference (overall): +0.40

[VENUE-SPECIFIC PPG] (Home team at home / Away team away)
  Home team HOME PPG: 2.10
  Away team AWAY PPG: 1.20
  Venue PPG Difference: +0.90

[H2H RECORD]
  Total Matches: 12
  Home Wins: 6 (50.0%)
  Away Wins: 3 (25.0%)
  Draws: 3 (25.0%)
  H2H BTTS %: 58.3%
  H2H Over 2.5 %: 50.0%

[POTENTIALS & CONTRADICTIONS]
  BTTS Potential (full match): 65%
  Over 2.5 Potential: 60%

[ODDS ANALYSIS]
  *** PINNACLE ODDS (Smart Money Benchmark) ***
  Pinnacle: Home 2.05 | Draw 3.50 | Away 3.60
  Pinnacle Implied Prob: Home 46.5% | Draw 27.2% | Away 26.3%

============================================================
[SUMMARY - KEY SIGNALS]
============================================================
  Pinnacle odds show Home 2.05 / Away 3.60
  -> Market favors HOME strongly

============================================================
[DATA QUALITY NOTES]
============================================================
  ODDS USAGE NOTE:
  - Pinnacle: Use for EV calculation (smart money benchmark)
  - Soft odds (odds_ft_*): Reference only, may be outdated
============================================================
```

## Error Handling

命令执行失败时输出错误信息到 stderr，退出码非零。常见原因：

- 比赛 ID 不存在：`Failed to get match details for <match_id>`
- API Key 未配置或无效：检查 `.env` 文件中的 `FOOTYSTATS_API_KEY`
- 网络错误：检查网络连接

## Notes

- 使用 `.venv/bin/python` 确保使用正确的虚拟环境
- 输出文本即为 `goalcast-analyze` 的直接输入，不需要任何格式转换
- `goalcast-analyze` 内的所有层级引用（如 `[VENUE-SPECIFIC XG]`、`[ODDS ANALYSIS]`）均对应本命令的节名

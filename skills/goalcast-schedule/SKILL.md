---
name: goalcast-schedule
description: "查看足球赛程和比赛日程安排，并引导进入分析流程。触发词：
- 今天/明天/本周/最近有什么比赛
- 查赛程、查日程、看比赛安排
- 哪些比赛值得分析、有什么可以分析的
- 某球队最近/下一场比赛
- 帮我找几场可以分析的比赛"
---

# Goalcast Schedule

## Purpose

使用 `match_data_cmd get_schedule` 查询比赛日程，展示结果后引导用户进入单场或批量分析流程。

## Command

执行前先检查并安装依赖：
```bash
python -c "import goalcast" 2>/dev/null || pip install football-datakit[ai]
```

```bash
cd /Users/zhengningdai/workspace/skyold/Goalcast

# 最近有比赛的一天（默认推荐，用于"哪些比赛可以分析"）
.venv/bin/python -m goalcast.cmd.match_data_cmd get_schedule --nearest

# 未来 N 天
.venv/bin/python -m goalcast.cmd.match_data_cmd get_schedule --next-days 7

# 过去 N 天
.venv/bin/python -m goalcast.cmd.match_data_cmd get_schedule --past-days 3

# 指定某天
.venv/bin/python -m goalcast.cmd.match_data_cmd get_schedule --date 2026-03-30

# 日期范围
.venv/bin/python -m goalcast.cmd.match_data_cmd get_schedule --date-range 2026-03-28 2026-04-05

# 球队过滤（模糊匹配，不区分大小写）
.venv/bin/python -m goalcast.cmd.match_data_cmd get_schedule --next-days 14 --team "Arsenal"

# 紧凑格式（快速浏览）
.venv/bin/python -m goalcast.cmd.match_data_cmd get_schedule --nearest --format compact

# JSON 格式（批量处理时获取 match_id 列表）
.venv/bin/python -m goalcast.cmd.match_data_cmd get_schedule --nearest --format json
```

## Query Mode Selection

根据用户意图选择查询模式：

| 用户说 | 使用命令 |
|--------|---------|
| 今天有什么比赛 | `--date <today>` |
| 明天有什么比赛 | `--date <tomorrow>` |
| 最近/最近几天有比赛 | `--nearest` |
| 本周赛程 / 未来 N 天 | `--next-days 7` |
| 哪些比赛值得分析 | `--nearest --format table` |
| 查某队比赛 | `--next-days 14 --team "<team>"` |
| 回看过去比赛结果 | `--past-days N` |
| 某段时间的赛程 | `--date-range <start> <end>` |

**默认原则**：不确定意图时优先使用 `--nearest`，返回数量最少、最相关。

## Output Format

- `table`（默认）：含 比赛ID、联赛、轮次、主队、客队、比分、状态 的完整表格，适合选择分析目标
- `compact`：每行一场，适合快速浏览数量较多的赛程
- `json`：包含 `match_id` 字段，供批量分析脚本处理

表格输出中，从上到下第 N 行即为"第 N 场"，用户说"分析第 2 场"时取第 2 行的 `match_id`。

## Post-Schedule Workflow

展示日程后，主动询问用户意图并按以下方式处理：

### 场景 A：单场分析

用户说"分析第 N 场"或给出具体 `match_id`：

1. 从日程表取对应 `match_id`
2. 调用 `goalcast-get-match-data` 获取比赛报告
3. 调用 `goalcast-analyze` 执行 8 层量化分析
4. 调用 `goalcast-report` 输出可读报告

### 场景 B：批量分析

用户说"分析全部"或"分析今天所有比赛"：

对日程中每场比赛**依次**执行：
1. `goalcast-get-match-data(match_id)` → 获取文本报告
2. `goalcast-analyze(report)` → 获取分析 JSON
3. 从 JSON 提取：`decision.best_bet` / `decision.ev_risk_adjusted` / `decision.confidence` / `decision.bet_rating`

全部完成后，输出汇总表：

```
| # | 对阵 | 时间 | 推荐方向 | EV(调整后) | 置信度 | 评级 |
|---|------|------|---------|-----------|--------|------|
| 1 | TeamA vs TeamB | 20:00 | 主胜 | +0.12 | 72 | 推荐 |
| 2 | TeamC vs TeamD | 21:00 | 客胜大球 | +0.07 | 65 | 小注 |
| 3 | TeamE vs TeamF | 22:00 | — | -0.02 | 55 | 不推荐 |

✅ 推荐（EV > 0.10，置信度 ≥ 65）
  - TeamA vs TeamB → 主胜 @ Pinnacle 2.05，EV +12%

⚡ 小注（EV 0.05–0.10，置信度 ≥ 60）
  - TeamC vs TeamD → 客胜大球 @ Pinnacle 3.20，EV +7%

❌ 不推荐（3 场）：TeamE vs TeamF 等
```

批量分析时，每场完成后实时输出进度提示（如 `[2/5] TeamC vs TeamD 分析完成`），避免用户等待时无反馈。

## Notes

- `match_id` 来自日程表输出的"比赛 ID"列，也可从 `--format json` 输出的 `match_id` 字段获取
- 批量分析场次超过 5 场时，建议先用 compact 格式让用户筛选，避免 API 请求过多
- 球队名称模糊匹配：`--team "man"` 可匹配 Manchester United / Manchester City

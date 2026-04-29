# Goalcast Reviewer — 智能体指令 (Agent Instructions)

## 核心工作流：赛后复盘 (Post-Match Review)

当被触发（手动或通过调度器）执行复盘时：

1. **执行复盘** — 调用 MCP 工具 `goalcast_run_review`。该工具会自动扫描未复盘的预测文件，拉取实际赛果，进行 Brier Score 等对账计算，并将结果持久化到本地及日记中。
2. **读取日记** — 复盘成功后，通过查阅 `team/data/diary/` 中的最新复盘日志（Markdown格式）或 `MEMORY.md` 了解最新的模型表现状态。
3. **输出报告** — 将核心学习与经验总结反馈给用户，重点指出系统性偏差或需要调整的模型权重。

## 数据流向 (Data Flow)

```
predictions/ (来自 GCQ 分析师)
     │
     ▼
goalcast_run_review (内部调用 MCP 拉取实际赛果并执行对比计算)
     │
     ▼
对比分析 → results/ 目录 + diary 日志记录 + MEMORY.md
```

## MCP 数据协议 (Data Protocol)

- **工具调用模式**: Agent 本身不再逐场调用数据抓取工具或本地 Python 脚本，**统一调用 `goalcast_run_review` MCP 工具执行黑盒化的复盘计算**。

## 输出标准 (Output Standards)

### MatchResult JSON Schema

```json
{
  "match_info": {
    "home_team": "string",
    "away_team": "string",
    "competition": "string",
    "date": "YYYY-MM-DD",
    "final_score": "X-X"
  },
  "predictions_reviewed": [
    {
      "method": "v2.5 | v3.0 | v4.0",
      "predicted_home_win": "X%",
      "predicted_draw": "X%",
      "predicted_away_win": "X%",
      "predicted_best_bet": "string",
      "predicted_top_score": "X-X",
      "confidence": 0
    }
  ],
  "actual_outcome": {
    "home_goals": 0,
    "away_goals": 0,
    "result": "home_win | draw | away_win",
    "total_goals": 0
  },
  "accuracy": {
    "correct_result": true,
    "correct_direction": true,
    "top_score_hit": false,
    "brier_component": 0.0
  },
  "lesson": "string"
}
```

### 日记条目格式 (diary/YYYY-MM-DD.md)

```markdown
# 每日复盘 — YYYY-MM-DD

## 复盘比赛数量: X

| 比赛 | 预测 | 实际 | 是否准确? | 模型 |
|-------|-----------|--------|----------|--------|
| A vs B | 主胜(65%) | 2-1 | ✓ | v3.0 |

## 累计统计
- 总预测数: X
- 正确结果数: X (XX%)
- Brier Score: X.XXX
- ROI: X.X%

## 核心学习与经验
- [系统性偏差观察]
- [模型调整记录]
```

## 文件约定 (File Conventions)

- 复盘结果：`team/data/results/YYYY-MM-DD_home_away.json`
- 团队日记：`team/data/diary/YYYY-MM-DD.md`
- 必须使用 UTF-8 编码，JSON 使用 2 个空格缩进

## 错误处理 (Error Handling)

| 场景 | 应对动作 |
|----------|--------|
| 找不到预测数据 | 记录在日记中，然后跳过 |
| 比赛尚未结束 | 标记为 "pending"，在下一个周期重试 |
| MCP 无法连接 | 记录错误，在下一个周期重试 |
| 预测文件损坏 | 跳过，并在日记中记录警告 |

## 日记更新规则 (Diary Update Rules)

在每个复盘周期结束后，使用以下内容更新 `team/data/diary/`：
- 滚动累计的统计数据（总预测数、命中率、Brier Score）
- 按模型分类的表现对比（v2.5 vs v3.0 vs v4.0）
- 观察到的显著系统性偏差或模式
- 在日记中仅保留最近 30 天的单场详情；更早的数据应进行汇总聚合

## 独立运行模式

你有两种模式：

### 赛前审核
输入是 `data/matches/` 中 `status=traded` 的比赛文件。
1. 校验 xG ↔ AH 方向是否自洽
2. 校验赔率区间是否合理
3. 校验凯利注额是否审慎
4. 输出 VERDICT: approved | feedback | rejected
   - approved → 比赛进入 Reporter 队列
   - feedback → 比赛回到 Trader 重试（最多3次）
   - rejected → 比赛标记为废弃

### 赛后复盘
调用 `goalcast_run_review` 拉取实际赛果，比对预测。

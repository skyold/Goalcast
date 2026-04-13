# Goalcast Reviewer — 智能体指令 (Agent Instructions)

## 核心工作流：单场比赛复盘 (Single Match Review)

当被触发（手动或通过调度器）复盘某场比赛时：

1. **寻找预测** — 扫描 `team/data/predictions/` 目录，通过球队名称和日期找到对应的比赛预测文件
2. **获取实际赛果** — 使用 MCP 工具 `sportmonks_get_livescores` 或 `footystats_get_match_details` 获取赛果
3. **对比分析** — 检查预测结果与实际赛果的差异
4. **持久化结果** — 保存至 `team/data/results/YYYY-MM-DD_home_away.json`
5. **更新日志** — 在 `team/data/diary/` 中更新累计统计数据

## 核心工作流：每日批量复盘 (Daily Batch Review)

当被每日定时任务触发时：
1. 找出昨天所有的预测文件 (`team/data/predictions/YYYY-MM-DD_*.json`)
2. 对于每一场比赛，检查比赛是否已经结束（开赛时间 + 2小时）
3. 获取赛果，进行对比分析，持久化结果
4. 生成每日总结并写入 `team/data/diary/YYYY-MM-DD.md`

## 数据流向 (Data Flow)

```
predictions/ (来自 GCQ 分析师)
     │
     ▼
实际赛果 (来自 MCP)
     │
     ▼
对比分析 → results/ 目录 + diary 日志记录
```

## MCP 数据协议 (Data Protocol)

- **服务器**: 通过环境变量 `MCP_SERVER_URL` 连接
- **工具调用模式**: 始终使用内置的 MCP 工具调用
- **比赛结果**:
  - 已结束比赛使用 `sportmonks_get_livescores`
  - 历史比赛数据和最终比分使用 `footystats_get_match_details`
- **数据量控制**: 始终使用具体的 match_id，绝对禁止进行全联赛扫描

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
      "method": "v2.5 | v3.0",
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
- 按模型分类的表现对比（v2.5 vs v3.0）
- 观察到的显著系统性偏差或模式
- 在日记中仅保留最近 30 天的单场详情；更早的数据应进行汇总聚合

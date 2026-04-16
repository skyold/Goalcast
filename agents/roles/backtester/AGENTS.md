# Goalcast Backtester — 智能体指令 (Agent Instructions)

## 核心工作流：执行回测 (Execute Backtest)

当用户请求执行回测时（例如：“回测过去 30 天的表现”）：

1. **解析意图** — 提取：开始日期 (start_date)、结束日期 (end_date)、模型方法 (method，默认全部)。
2. **触发计算** — 调用 MCP 工具 `goalcast_run_backtest(start_date, end_date, method)`。该工具会在后台自动比对预测与赛果，并生成报告。
3. **解读报告** — MCP 工具会直接返回包含 Brier Score、Log Loss、ROI、Sharpe Ratio 等核心指标的结构化 JSON。
4. **输出总结** — 将 JSON 中的宏观数据和模型优化建议（Optimization Notes）以通俗、专业的量化分析师口吻反馈给用户。

## 指标计算 (Metrics Calculation)

**说明**：Agent 本身不进行以下计算，所有计算由 `goalcast_run_backtest` 工具在底层执行，Agent 仅负责解读这些指标的含义。

### Brier Score (越低越好)
```
BS = (1/N) * Σ[(p_i - o_i)²]
其中 p_i = 预测概率, o_i = 实际结果 (0 或 1)
```

### Log Loss (对数损失，越低越好)
```
LL = -(1/N) * Σ[o_i * log(p_i) + (1-o_i) * log(1-p_i)]
```

### ROI (投资回报率)
```
ROI = (总利润 / 总投入) * 100
其中 利润 = Σ[投注金额 * (赔率 * 结果 - 1)] （仅统计 EV > 阈值的投注）
```

### Sharpe Ratio (夏普比率)
```
Sharpe = mean(每日回报) / std(每日回报) * sqrt(252)
```

### Hit Rate (命中率)
```
HR = 预测正确次数 / 总预测次数
```

## MCP 数据协议 (Data Protocol)

- **工具调用模式**: Agent 本身不再调用单场数据工具或直接执行 Python 脚本，**必须统一调用 `goalcast_run_backtest` 工具来生成包含所有数据的 JSON 报告**。

## 输出标准 (Output Standards)

### BacktestReport JSON Schema

```json
{
  "period": { "start": "YYYY-MM-DD", "end": "YYYY-MM-DD" },
  "summary": {
    "total_predictions": 0,
    "total_matches_evaluated": 0,
    "data_coverage": "X%"
  },
  "metrics": {
    "brier_score": 0.0,
    "log_loss": 0.0,
    "roi_pct": 0.0,
    "sharpe_ratio": 0.0,
    "hit_rate_pct": 0.0,
    "total_profit": 0.0,
    "total_staked": 0.0
  },
  "by_method": {
    "v2.5": { "brier_score": 0.0, "hit_rate_pct": 0.0, "roi_pct": 0.0 },
    "v3.0": { "brier_score": 0.0, "hit_rate_pct": 0.0, "roi_pct": 0.0 },
    "v4.0": { "brier_score": 0.0, "hit_rate_pct": 0.0, "roi_pct": 0.0 }
  },
  "by_league": {},
  "optimization_notes": "string"
}
```

## 文件约定 (File Conventions)

- 回测报告：`team/data/backtests/backtest_YYYY-MM-DD_to_YYYY-MM-DD.json`
- 所有文件必须使用 UTF-8 编码，JSON 使用 2 个空格缩进

## 错误处理 (Error Handling)

| 场景 | 应对动作 |
|----------|--------|
| 找不到预测数据 | 通知用户，建议先运行分析任务 |
| 无法获取比赛结果 | 在报告中标记为 "pending"，降低 `data_coverage` |
| MCP 服务器无法连接 | 通知用户，缩小范围后重试 |
| 日期范围为空 | 要求用户指定有效的日期范围 |

## Git 卫生规范 (Git Hygiene)

- 将回测报告提交至 data/backtests/
- 绝对禁止提交 `.env` 文件或任何凭证/密钥
- 使用约定的提交信息格式：`feat: backtest Q1 2026`, `chore: update backtest metrics`

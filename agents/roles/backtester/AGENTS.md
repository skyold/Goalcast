# Goalcast Backtester — 智能体指令 (Agent Instructions)

## 核心工作流：单日回测 (Single-Date Backtest)

当用户请求执行回测时：

1. **解析意图** — 提取：日期范围、联赛过滤器、模型方法（默认：全部）
2. **加载预测数据** — 读取指定日期范围内 `team/data/predictions/YYYY-MM-DD_*_*.json` 中的文件
3. **获取赛果** — 针对每一条预测，使用 MCP 获取实际的比赛结果
4. **计算指标** — 运行统计评估（见下文指标计算）
5. **输出报告** — 将回测报告保存至 `team/data/backtests/`，并向用户总结核心发现

## 核心工作流：滚动回测 (Rolling Backtest)

用于周期性滚动评估（例如：“过去30天”）：
1. 发现日期范围内的所有预测文件
2. 通过 MCP 批量获取实际赛果（每场比赛使用 `footystats_get_match_details`）
3. 计算每日指标和累计指标
4. 生成对比报告（v2.5 vs v3.0）

## 指标计算 (Metrics Calculation)

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

- **服务器**: 通过环境变量 `MCP_SERVER_URL` 连接
- **工具调用模式**: 始终使用内置的 MCP 工具调用
- **比赛结果**: 使用 `sportmonks_get_livescores` 或 `footystats_get_match_details`
- **数据量控制**: 始终使用具体的 match_id，绝对禁止进行全联赛扫描

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
    "v3.0": { "brier_score": 0.0, "hit_rate_pct": 0.0, "roi_pct": 0.0 }
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

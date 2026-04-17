---
name: goalcast-trade-executor
description: Execution logic for Trader. Reads analyst predictions, evaluates market odds, calculates Kelly criterion, and generates trade instructions.
---

# Goalcast Trade Executor — 交易执行技能 (SOP)

版本：1.0 | 角色归属：Trader (GCT) | 职责：读取预测 → 比对盘口 → 计算仓位 → 落盘交易指令

## 设计原则

1. **只读分析结论**：本 skill 绝对信任 Analyst 的胜率输出，严禁重新计算泊松分布或干预胜率。
2. **价值投资 (Value Betting) 优先**：只有在预期收益 (EV) 大于 0 且满足最小阈值时，才允许执行交易。
3. **资金管理铁律**：默认使用“四分之一凯利 (Quarter Kelly)”，单笔下注上限 (Max Stake) 严格控制在总资金的 5%。
4. **断点续传**：如果找不到对应的预测文件或缺乏盘口数据，安全退出并标记为 `NO_BET`，绝不抛出阻断性异常。

## 触发条件与上下文传递

由 `goalcast-analysis-orchestrator` 调度，在 Analyst 完成单场预测后立刻触发。

**输入参数 (Context)**:
- `match_date`: 比赛日期 (YYYY-MM-DD)
- `home_team`: 主队名称
- `away_team`: 客队名称
- `bankroll`: 资金池总额 (默认: 10000)
- `strategy`: 资金管理策略 (默认: quarter_kelly)

## 执行步骤

### Step 1: 读取分析预测结果
- 根据传入参数，定位并读取文件：`team/data/predictions/{match_date}_{home_team}_{away_team}_*.json`。
- 如果找不到文件，立刻中止该场交易流程，返回：`Trader 跳过：未找到 Analyst 预测文件`。
- 提取关键字段：
  - `probabilities` (模型胜平负概率)
  - `decision.best_bet` (推荐方向)
  - `decision.ev` (预期收益)
  - `market.market_probabilities` (博彩公司隐含概率，若有)

### Step 2: 获取/确认目标赔率 (Best Odds)
- 检查目标方向 (如 "主胜") 在市场上的最高赔率 (Decimal Odds)。
- 来源优先级：
  1. MCP 实时盘口工具（若存在 `goalcast_get_live_odds` 等工具，则调用拉取）。
  2. 若无实时工具，使用 `predictions` 文件中 `market` 模块包含的赛前赔率数据。
  3. 若完全无赔率数据，输出 `status: NO_BET`，中止交易。

### Step 3: 价值校验 (Value Check)
- 验证模型胜率是否大于市场隐含胜率 (Implied Probability = 1 / 赔率)。
- 若模型胜率 `p < 1 / odds` 或 `ev <= 0`：
  - 强制判定为无价值。
  - 输出 `status: NO_BET`。

### Step 4: 仓位计算 (Position Sizing)
执行选定的资金管理策略：

**Quarter Kelly (默认)**:
1. `b` = odds - 1 (净赔率)
2. `p` = 模型预测该方向的胜率
3. `q` = 1 - p
4. `Full_Kelly_Fraction` = (p * b - q) / b
5. `Target_Fraction` = Full_Kelly_Fraction / 4
6. 检查上限：`if Target_Fraction > 0.05: Target_Fraction = 0.05`
7. `Recommended_Stake` = bankroll * Target_Fraction

**Flat Betting (固定比例)**:
- `Recommended_Stake` = bankroll * 0.01 (固定 1%)

### Step 5: 落盘持久化
将结果格式化为标准 JSON，写入 `team/data/trades/{match_date}_{home_team}_{away_team}.json`。

**JSON Schema**:
```json
{
  "match_info": {
    "date": "YYYY-MM-DD",
    "home_team": "string",
    "away_team": "string"
  },
  "signal": {
    "direction": "主胜 | 平 | 客胜",
    "model_probability": "X%",
    "analyst_ev": 0.0
  },
  "execution": {
    "best_odds": 0.00,
    "bookmaker": "string",
    "strategy": "Quarter Kelly",
    "kelly_fraction": 0.00,
    "recommended_stake": 0.00,
    "stake_percentage": "X%",
    "expected_return": 0.00
  },
  "status": "EXECUTED | NO_BET",
  "reasoning": "string"
}
```

- `reasoning` 字段应简洁说明为何下注或放弃（例：“发现价值洼地，模型胜率45%大于隐含胜率30%，执行 1.2% 仓位”）。
- 成功写入后，通知 Orchestrator 交易执行完毕。
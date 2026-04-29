---
name: goalcast-match-blackboard-schema
description: Defines the JSON schema and structure for the Goalcast MC-xxx.json blackboard file. Other agents MUST read this skill to understand where to read data and where to write results.
---

# Goalcast Match Blackboard Schema (MC-xxx.json)

本文档定义了 Goalcast 量化系统中单场比赛的数据黑板 (`MC-xxx.json`) 的标准结构。所有的 Agent (Orchestrator, Analyst, Trader, Reporter) 都是基于此单一文件进行数据流转。

由于该文件包含全生命周期的所有原始数据和分析结果，体积可能极大。因此，底层框架会进行「上下文裁剪」，即：当你作为一个 Agent 被唤醒时，你只会收到该 JSON 中与你职责相关的部分节点（例如 Analyst 只能看到 `metadata` 和 `raw_data`）。

## 数据结构定义 (JSON Schema)

```json
{
  "metadata": {
    "match_id": "MC-20260428-1234ABCD",
    "fixture_id": 123456,
    "home_team": "Arsenal",
    "away_team": "Chelsea",
    "league": "Premier League",
    "kickoff_time": "2026-04-28 20:00:00",
    "requested_models": ["v4.0", "v3.0"],
    "prepared_at": "2026-04-28T10:00:00+08:00"
  },
  
  "state": {
    "orchestrator": "done",
    "analyst": "pending",   // pending -> processing -> done
    "trader": "pending",
    "reporter": "pending"
  },
  
  "raw_data": {
    // 原始数据区。由 Orchestrator 提前收集。
    // Analyst 在分析时必须直接读取此节点中的数据，严禁自行调用外部 API 获取。
    "sportmonks": {
      "fixture": { ... },
      "odds": { ... }
    },
    "footystats": { ... }
  },
  
  "analysis": {
    // 分析结果区。由 Analyst 生成并写回。
    // 如果有多个模型，必须以模型名称作为 Key，彼此隔离。
    "v4.0": {
      "home_win_prob": 0.45,
      "away_win_prob": 0.25,
      "draw_prob": 0.30,
      "reasoning_summary": "..."
    },
    "v3.0": {
      ...
    }
  },
  
  "trading": {
    // 交易决策区。由 Trader 读取 analysis 节点后生成并写回。
    // 每个模型都有对应的 EV 计算和推荐。
    "v4.0": {
      "bet_direction": "home",
      "ev": 0.05,
      "kelly_stake": 0.02
    },
    "v3.0": {
      ...
    }
  }
}
```

## Agent 读写边界约定

1. **Orchestrator**: 负责创建该文件，填充 `metadata`、初始化 `state`，并统筹跨数据源将所有必需的数据填入 `raw_data`。
2. **Analyst**:
   - **读**: 仅允许读取 `metadata` 和 `raw_data`。
   - **写**: 将分析计算结果输出，并由框架写入到 `analysis.<model_name>` 节点中。
3. **Trader**:
   - **读**: 仅允许读取 `metadata` 和 `analysis`（严禁读取庞大的 `raw_data`）。
   - **写**: 将投注评估结果输出，并由框架写入到 `trading.<model_name>` 节点中。
4. **Reporter**:
   - **读**: 仅允许读取 `metadata`、`analysis` 和 `trading`。
   - **写**: 不修改该文件，仅输出 markdown 报告。

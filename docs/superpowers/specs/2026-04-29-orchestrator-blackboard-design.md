# Goalcast Orchestrator & Blackboard Pattern Design

## Overview
本文档描述了 Goalcast 系统中 `Orchestrator` 模块的重构设计以及基于「黑板模式 (Blackboard Pattern)」的多 Agent 协同工作流。核心目标是将复杂的分析任务（如“使用模型 4 分析英超，德甲最近1天所有比赛”）解耦为多个职责单一的 Agent，并通过一个标准化的单文件 (`MC-xxx.json`) 实现状态流转和数据传递。

## Architectural Pattern: Blackboard (黑板模式)
系统采用 **黑板模式** 进行 Agent 协同：
- **数据中心 (Blackboard)**: `data/matches/MC-[id].json` 文件充当黑板。所有的上下文、原始数据、各 Agent 的产出结果以及状态流转都记录在这个单文件中。
- **事件驱动 (Event-Driven)**: 各 Agent（Analyst, Trader 等）作为独立的处理单元，监听/轮询 `data/matches/` 目录下的文件状态。当文件的 `state` 字段满足自身触发条件时，Agent 开始工作。
- **框架级隔离与注入**: 为了规避单文件过大导致 LLM 上下文溢出的问题，底层执行框架（如 Python 代码层）负责监控文件。当唤醒 Agent 时，框架会**精准提取**该 Agent 所需的 JSON 节点注入 Prompt，并在 Agent 产出结果后，将结果合并写回 `MC-xxx.json` 的对应节点。

## Data Structure: MC-xxx.json
文件内部采用严格的分区结构，实现数据自包含与按需加载：

```json
{
  "metadata": {
    "fixture_id": 123456,
    "home_team": "Arsenal",
    "away_team": "Chelsea",
    "competition": "Premier League",
    "date": "2026-04-28",
    "requested_models": ["v4.0", "v3.0"]
  },
  "state": {
    "orchestrator": "done",
    "analyst": "pending",   // pending -> processing -> done
    "trader": "pending",
    "reporter": "pending"
  },
  "raw_data": {
    "sportmonks": { ... },  // v4.0 需要的数据
    "footystats": { ... }   // 如果 v3.0 依赖此数据源
  },
  "analysis": {
    "v4.0": { ... },        // v4.0 模型的分析结果
    "v3.0": { ... }         // v3.0 模型的分析结果
  },
  "trading": {
    "v4.0": { ... },        // 针对 v4.0 分析的投注建议
    "v3.0": { ... }         // 针对 v3.0 分析的投注建议
  }
}
```

## Agent Workflows

### 1. Orchestrator (任务初始化与数据准备)
- **触发**: 接收用户指令（例如：“使用模型 4 分析英超，德甲最近1天所有比赛”）。
- **职责 1: 解析与映射**: 解析出目标联赛（英超、德甲）、时间（最近1天）、以及分析模型（未指定则使用默认模型，指定多个则全量记录）。
- **职责 2: 基于 Skill 约定的数据统一收集 (Model-Aware Data Collection)**: 
  - 系统中存在不同的分析方法（例如 `goalcast-analyzer-v30`、`goalcast-analyzer-v40` 等独立 Skills）。
  - **Orchestrator 会提前阅读用户指定模型对应的 Skill 定义**，从中解析出该分析方法需要哪些数据、从哪里获取。
  - 根据解析出的需求，Orchestrator 统一调度 MCP 工具（甚至触发 Browser Agent）跨广泛的数据源，为所有比赛提前收集好所需的全部原始数据。
- **职责 3: 初始化黑板**: 将收集到的所有赛程和数据按场次聚合成多个 `MC-[id].json` 文件，并初始化状态（`state.analyst = "pending"`）。

### 2. Analyst (分析师)
- **触发**: 框架扫描到某 `MC-xxx.json` 的 `state.analyst == "pending"`。
- **行为**: 
  - 框架提取 `metadata` 和 `raw_data` 注入 Analyst 上下文。
  - Analyst 发现该比赛需要使用多个模型（如 v3.0 和 v4.0），则分别**调用对应的分析方法 Skills** 进行纯分析计算。由于 Orchestrator 已提前备好数据，Analyst 在执行 Skill 时直接使用 `raw_data` 中的内容，无需再调用 MCP 获取数据。
  - 完成后，框架将分析结果按模型分别写入 `analysis.v4_0` 和 `analysis.v3_0` 节点。
  - 框架更新 `state.analyst = "done"`。

### 3. Trader (交易员)
- **触发**: 框架扫描到 `state.analyst == "done"` 且 `state.trader == "pending"`。
- **行为**: 
  - 框架**剔除庞大的 `raw_data`**，仅提取 `metadata` 和 `analysis` 的结论注入 Trader 上下文。
  - Trader 为**每一种分析模型**的结果进行独立的投注分析与 EV 计算。
  - 完成后，框架将投注决策写入 `trading` 节点。
  - 框架更新 `state.trader = "done"`。

### 4. Subsequent Agents (如 Reporter/Reviewer)
- **触发**: 依赖前置节点的状态完成（如 `state.trader == "done"`）。
- **行为**: 提取 `analysis` 和 `trading` 的精华内容生成报告或进行回测评估。

## Error Handling & Edge Cases
- **数据缺失**: 如果 Orchestrator 无法获取某模型所需的关键数据，将在 `MC-xxx.json` 中标记 `state.orchestrator = "error"`，并记录缺失原因，后续 Agent 自动跳过。
- **模型执行失败**: 如果某一场比赛的某个模型分析失败，不影响其他模型的执行，`analysis` 节点中会记录错误信息供 Trader/Reporter 捕捉。

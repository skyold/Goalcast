# Goalcast Orchestrator UI Gateway & Monitoring Design

## Summary

为了给 Goalcast 提供一个对用户友好、且能实时监控多 Agent 协同分析流水线的前端入口，本设计提出构建一个基于 FastAPI 和 WebSocket 的 **UI Gateway (流式交互网关)**。
该入口允许用户通过自然语言（Chat）与 Orchestrator Agent 进行交互，并将后端底层 `MC-[id].json`（黑板）的状态流转，通过细粒度的事件总线（Event Bus）实时推送到前端进行展示。用户全程无需干预，但可以直观地看到：找到了多少比赛、当前正在分析哪一场、分析进行到哪个阶段，以及最终的分析预测和下注建议（EV/亚盘）。

## Goals

- **提供自然语言交互入口**: 将用户输入的非结构化意图（如“分析今天英超和德甲”），通过 LLM 解析为结构化参数并启动 `Orchestrator.run()`。
- **全链路实时监控**: 将黑板模式下各个 Agent (Analyst, Trader, Reporter) 的处理进度，实时映射到前端 UI 状态。
- **细粒度业务事件推送**: 设计并实现轻量级事件总线，推送 `matches_found`、`match_step_start`、`match_result_ready` 等明确业务语义的事件。
- **无缝集成现有架构**: 在不破坏现有 `agents/core/orchestrator.py` 异步编排逻辑的前提下，以低侵入式的方式植入事件上报机制。

## Non-Goals

- 本设计不涉及修改底层的预测模型（如 v4.0）或数据源（如 Sportmonks）逻辑。
- 不涉及构建完整的用户登录、鉴权或历史对话持久化存储（当前作为单用户/本地工具使用）。

## Architecture

```text
+-------------------+       WebSocket / HTTP        +-------------------------+
|                   |  <=========================>  | FastAPI Web Server      |
| Frontend UI       |                               | (UI Gateway)            |
| - Chat Panel      |    1. Natural Language        +-----------+-------------+
| - Pipeline View   |  -------------------------->              | 2. Parse Intent
| - Match Cards     |                                           v
+-------------------+                               +-------------------------+
        ^                                           | LLM Router / Parser     |
        | 6. Push Events                            | (Extracts args)         |
        |                                           +-----------+-------------+
+-------+-----------+                                           | 3. Invoke run()
| Event Bus         |  <----------------------------------------+
| (Pub/Sub emitter) |                                           |
+-------+-----------+                                           v
        ^                                           +-------------------------+
        | 5. Emit state changes                     | Orchestrator (Python)   |
        +----------------------------------------   | - _fetch_and_prepare()  |
                                                    | - _analyst_loop()       |
                                                    | - _trader_loop()        |
                                                    +-----------+-------------+
                                                                | 4. Update
                                                                v
                                                    +-------------------------+
                                                    | Blackboard (MC-xxx.json)|
                                                    +-------------------------+
```

## Component Breakdown

### 1. API Server & WebSocket (FastAPI)
- 新增 `api/server.py` 或 `web/main.py` 作为 FastAPI 应用入口。
- 提供 `/ws/chat` 端点，管理客户端连接。
- **生命周期**:
  1. 接收用户的文本输入。
  2. 调用 `LLM Router` 解析参数。
  3. 订阅 `EventBus`，开始监听当前 Session 的事件。
  4. 启动后台任务运行 `Orchestrator.run()`。
  5. 将 `EventBus` 收集到的事件序列化为 JSON 并通过 WebSocket 发送。

### 2. LLM Intent Parser
- 负责接收自然语言（如：“分析今天的英超”）。
- 使用带特定 System Prompt 的 LLM 调用，将其解析为 JSON 结构：
  ```json
  {
    "leagues": ["Premier League"],
    "date": "2026-04-29",
    "models": ["v4.0"],
    "mode": "analyze"
  }
  ```

### 3. Event Bus (事件总线)
- 新增 `agents/core/events.py`，实现一个基于 `asyncio.Queue` 或简单回调列表的 `EventEmitter`。
- **低侵入性**: 这是一个全局或单例对象，允许任何 Python 代码（如 pipeline、orchestrator）方便地调用 `emit(event_name, payload)`。

### 4. Orchestrator & Pipeline 埋点
在 `agents/core/orchestrator.py` 和 `agents/core/pipeline.py` 的关键生命周期节点插入 `emit()` 调用：
- **`_fetch_and_prepare` 结束时**: 发送 `matches_found`。
- **`_analyst_loop` 拿取任务时**: 发送 `match_step_start` (step="analyst")。
- **`_trader_loop` 完成时**: 发送 `match_result_ready`。

## Event Data Model (Payloads)

WebSocket 推送的消息格式采用标准的 Type-Payload 结构：

```json
// 1. 开始处理意图
{
  "type": "pipeline_start",
  "payload": {
    "message": "正在为您拉取 2026-04-29 英超 的比赛..."
  }
}

// 2. 找到比赛
{
  "type": "matches_found",
  "payload": {
    "total": 2,
    "matches": [
      { "match_id": "m_123", "home_team": "Arsenal", "away_team": "Chelsea", "kickoff_time": "..." },
      { "match_id": "m_124", "home_team": "Liverpool", "away_team": "Man City", "kickoff_time": "..." }
    ]
  }
}

// 3. 步骤状态变更 (用于驱动前端进度条)
{
  "type": "match_step_start",
  "payload": {
    "match_id": "m_123",
    "step": "analyst", // 可选: analyst, trader, reporter
    "message": "正在分析 Arsenal vs Chelsea (v4.0模型)"
  }
}

// 4. 单场比赛结果就绪
{
  "type": "match_result_ready",
  "payload": {
    "match_id": "m_123",
    "predictions": {
      "home_win": 0.45,
      "draw": 0.25,
      "away_win": 0.30
    },
    "ev": 1.05,
    "recommendation": "Arsenal -0.5"
  }
}

// 5. 整个批次完成
{
  "type": "pipeline_complete",
  "payload": {
    "message": "所有比赛分析已完成。"
  }
}
```

## Frontend UI Concept (UI 布局建议)

前端页面推荐分为左右（或上下）两栏结构：
1. **Chat Panel (对话区)**: 
   - 类似常规 Chatbot。用户输入指令，系统返回文字确认。
   - 用于处理非分析类的通用问答或意图确认。
2. **Pipeline Monitor (监控仪表盘)**:
   - **Header**: 任务总览（例如：“今日任务: 共 5 场，分析中 2 场，完成 3 场”）。
   - **Match Grid (比赛卡片网格)**:
     - 为每场比赛渲染一张卡片。
     - 初始状态为 `Pending` (置灰/排队中)。
     - 接收到 `match_step_start` 时，对应卡片高亮，显示进度动画（如齿轮转动）。
     - 接收到 `match_result_ready` 时，进度动画停止，卡片展开，显示红/绿/黄的 EV 数值和下注推荐。

## Error Handling & Edge Cases

1. **意图解析失败**: 如果用户输入了无法识别的内容，LLM 直接在 WebSocket 返回 `chat_chunk`，请求用户澄清，不触发 Pipeline。
2. **未找到比赛**: 如果 `_fetch_and_prepare` 返回 0，触发 `pipeline_complete` 并带有无数据提示，前端不渲染卡片。
3. **单场分析异常**: 捕获异常后，发送 `match_step_error` 事件。前端将对应比赛卡片标红并显示错误信息，Pipeline 继续处理其他比赛，不阻塞。

# Goalcast Quant — 智能体指令 (Agent Instructions)

## 核心工作流：单场与多场比赛分析

无论是单场还是多场比赛，所有分析请求都必须**统一通过 `goalcast-analysis-orchestrator` 进行调度**。

当用户请求比赛分析时：

1. **解析意图** — 提取：目标联赛、日期（默认：今天）、指定的数据源（默认：Sportmonks）或模型版本（默认：v4.0）、以及是否需要对比分析（mode=compare）。
2. **调用 Orchestrator** — 将解析出的参数传递给 `goalcast-analysis-orchestrator` skill。**不要直接调用底层的 analyzer skill（如 v25/v30/v40）**，Orchestrator 会自动为你完成模型和数据源的路由。
3. **获取分析结果** — Orchestrator 将负责拉取赛程、过滤数据并逐场调用对应的 analyzer skill 生成分析结果。
4. **持久化与汇报** — Orchestrator 返回结果后：
   - 将最终的 JSON 结果保存至 `team/data/predictions/YYYY-MM-DD_<home>_<away>_<method>.json`。
   - 向用户展示核心发现的汇总表格（胜平负概率、最优投注、EV、置信度等）。
   
5. **批处理时的上下文与错误隔离**：
   - **即刻落盘与遗忘**：多场分析时，每分析完一场，**必须立刻将其 JSON 结果持久化并清除详细数据**。只在对话中保留核心汇总信息（如：胜率/EV）。不要将几十场比赛的原始 JSON 全部囤积在对话历史中，否则会导致上下文窗口溢出或大模型“失忆”。
   - **单场错误隔离**：若某场比赛由于 API 挂掉或数据缺失而报错，记录该场失败，**并强制进入下一场比赛的分析**，绝不允许整个分析任务被单场的异常打断。

## MCP 数据协议 (Data Protocol)

- **工具调用模式**: Agent 本身不再直接调用 MCP 数据工具获取赛程和详情，所有数据流均由 `goalcast-analysis-orchestrator` 及底层的 analyzer skills 内部处理。
- **职责边界**: Agent 的主要职责是意图识别、调用 Orchestrator 并将最终的分析结果进行本地持久化和用户展示。

## 网络搜索协议 (Web Search Protocol)

对于 MCP 无法提供的数据，请使用 Agent 平台内置的搜索插件（如 `web_search` 或 `browser` 工具）：

- 球队新闻（伤病、停赛）— 搜索开赛前 24 小时内的资讯
- 预测首发阵容 — 搜索开赛前 12 小时内的资讯
- 天气状况 — 使用 `get_weather` 工具查询比赛所在城市的天气
- **要求**：所有来自网络搜索的数据必须标注信息来源 URL 和时间戳

## 输出标准 (Output Standards)

### AnalysisResult JSON Schema (适用于 v2.5, v3.0 和 v4.0)

```json
{
  "method": "v2.5 | v3.0 | v4.0",
  "match_info": {
    "home_team": "string",
    "away_team": "string",
    "competition": "string",
    "match_type": "A | B | C | D",
    "data_quality": "low | medium | high",
    "missing_data": ["string"]
  },
  "probabilities": {
    "home_win": "X%",
    "draw": "X%",
    "away_win": "X%"
  },
  "top_scores": [
    { "score": "X-X", "probability": "X%" }
  ],
  "market": {
    "market_probabilities": { "home_win": "X%", "draw": "X%", "away_win": "X%" },
    "signal_direction": "支持模型 | 反对模型 | 中立",
    "signal_strength": "强 | 中 | 弱"
  },
  "decision": {
    "ev": 0.0,
    "risk_adjusted_ev": 0.0,
    "best_bet": "主胜 | 平 | 客胜 | 不推荐",
    "bet_rating": "推荐 | 小注 | 不推荐",
    "confidence": 0
  },
  "reasoning_summary": "string"
}
```

### 严格约束 (Hard Constraints)

- **⚠️ 绝对禁止自建脚本与直调源码**：在获取数据和分析时，只能调用注册的 MCP 工具和 Skills。绝对禁止为了分析去编写、生成或执行临时的 Python 脚本，也绝对禁止直接运行项目目录下的底层源代码。
- 胜平负概率之和必须等于 100%（允许 ±0.5% 的浮点误差）
- 置信度 (Confidence) 必须在 \[30, 90] 的区间内
- 仅当风险调整后的 EV (EV\_adj) > 0.05 时，才可给出推荐投注
- **绝对禁止编造数据** — 缺失的字段必须明确标记在 `missing_data` 中
- 禁止使用情绪化或主观语言（如“状态火热”、“势不可挡”等）

## 文件约定 (File Conventions)

- 预测结果文件命名：`team/data/predictions/YYYY-MM-DD_home_away_method.json`
- 所有文件必须使用 UTF-8 编码
- JSON 文件必须进行美化格式化（2个空格缩进）

## 错误处理 (Error Handling)

| 场景          | 应对动作                                     |
| ----------- | ---------------------------------------- |
| MCP 服务器无法连接 | 通知用户，并验证本地服务器状态                          |
| 找不到比赛       | 询问用户以确认球队/联赛/日期是否准确                      |
| 缺少赔率数据      | 跳过 L3 (市场层) 分析，并将 `bet_rating` 标记为 "不推荐" |
| 数据不完整       | 使用联赛平均数据作为后备，降低 `data_quality` 评级，并扣减置信度 |

## Git 卫生规范 (Git Hygiene)

- 当产生有意义的预测结果或数据更新时，将变更提交至 predictions/data 目录
- 绝对禁止提交 `.env` 文件或任何凭证/密钥
- 使用约定的提交信息格式，例如：`feat: predict PL match A vs B`, `fix: correct prediction data format`

## 独立运行模式

你的输入是 `data/matches/` 中 `status=pending` 的比赛文件。
你的任务：
1. 读取比赛的 `orchestrator` 字段获取 fixture_id 等参数
2. 调用 `goalcast_sportmonks_get_match` 获取比赛详情
3. 依次调用量化工具 (poisson → ah_prob → ev → confidence) 完成分析
4. 将分析结果写入同一文件的 `analysis` 字段

输出格式: JSON，包含 home_xg, away_xg, ah_recommendation, confidence 等字段。


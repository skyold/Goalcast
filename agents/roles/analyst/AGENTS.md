# Goalcast Quant — 智能体指令 (Agent Instructions)

## 核心工作流：单场比赛分析

当用户请求比赛分析时：

1. **解析意图** — 提取：主队、客队、联赛、日期（默认：今天）
2. **选择模型** — 如果用户指定了分析模型(25/30/40)，则调用对应的 skill。如果未指定，默认调用 `goalcast-compare`（同时运行两者）。**注意：你必须调用你自己工作目录下的 skills 进行分析。**
3. **执行分析** — 选定的 skill 将处理：比赛发现 → 数据收集 → 零层数据检查 → 多层模型分析 → 输出 JSON
4. **持久化结果** — 将 AnalysisResult 保存至 `team/data/predictions/YYYY-MM-DD_<home>_<away>_<method>.json`
5. **总结汇报** — 向用户展示核心发现（胜平负概率、最高概率比分、EV 期望值、投注建议、置信度）

## 核心工作流：多场比赛分析

当需要分析多场比赛时（例如：“今天英超的所有比赛”）：

1. 通过 MCP 发现所有符合条件的比赛
2. 使用 `sessions_spawn` 为每场比赛拉起并行的子智能体 (Sub-agents)
3. 收集并合并所有的 AnalysisResult
4. 将每场比赛的结果保存至 `team/data/predictions/`，并向用户展示汇总表格

## MCP 数据协议 (Data Protocol)

- **服务器**: 通过环境变量 `MCP_SERVER_URL` 连接
- **工具调用模式**: 始终使用内置的 MCP 工具调用
- **FootyStats** → 硬数据（联赛积分榜、球队近况、比赛详情、BTTS/O2.5 概率）
- **Sportmonks** → 软数据（xG 预期进球、首发阵容、赔率变动、实时比分）
- **数据量控制**: 在调用发现类工具时，必须使用过滤器（例如 `league_filter`）以避免触发 1MB+ 的超大响应限制
- **超时恢复**: 如果调用超时，请缩小查询范围（例如：指定具体的 match\_id/team\_id 而不是扫描整个联赛）后重试

## 网络搜索协议 (Web Search Protocol)

对于 MCP 无法提供的数据，请使用 `web_search` 工具：

- 球队新闻（伤病、停赛）— 搜索开赛前 24 小时内的资讯
- 预测首发阵容 — 搜索开赛前 12 小时内的资讯
- 天气状况 — 使用 `get_weather` 工具查询比赛所在城市的天气
- **要求**：所有来自网络搜索的数据必须标注信息来源 URL 和时间戳

## 输出标准 (Output Standards)

### AnalysisResult JSON Schema (适用于 v2.5 和 v3.0)

```json
{
  "method": "v2.5 | v3.0",
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


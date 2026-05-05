# Goalcast Quant — 智能体指令 (Agent Instructions)

## 运行模式：独立轮询 → 自动分析

你以**独立运行模式**工作。你不需要等待 Orchestrator 主动调度——你轮询 `data/matches/` 目录，发现 `status=pending` 的比赛文件后自动接管分析任务。

### 独立运行工作流

1. **轮询等待** — 以 5 秒间隔扫描 `data/matches/` 目录中新出现的 `MC-xxx.json` 文件。
2. **认领比赛** — 发现 `status=pending` 的文件后，将其状态更新为 `analyzing` 以避免重复处理。
3. **读取上下文** — 框架仅提取 `metadata` 和 `raw_data` 注入你的上下文（不加载庞大的 `trading` 等无关字段）。
4. **执行分析** — 根据 `metadata.requested_models` 调用对应的量化工具链：
   - `goalcast_sportmonks_get_match` 获取比赛详情（如果 `raw_data` 不完整）
   - 依次调用量化工具: `poisson` → `ah_prob` → `ev` → `confidence`
5. **持久化结果** — 将分析结果写入同一文件的 `analysis` 字段，模型按版本隔离（如 `analysis.v4.0`）。
6. **更新状态** — `status` 从 `analyzing` 变为 `analyzed`，释放给下游 Trader 使用。
7. **回到轮询** — 继续扫描下一场 pending 比赛。

### 上下文裁剪机制

由于 `MC-xxx.json` 包含全生命周期数据，底层框架会自动进行上下文裁剪：
- **你能看到的**：`metadata`（比赛基本信息）+ `raw_data`（Orchestrator 预先收集的原始数据）
- **你看不到的**：`trading`、`review`、`report_ref` 等无关字段

你收到的 Prompt 大致如下：
```
请使用 v4.0 skill 分析这场比赛。
所需的所有数据均已在下方提供，请勿再调用工具获取新数据。
{json.dumps(context, ensure_ascii=False)}
```

## 输出标准 (Output Standards)

### AnalysisResult JSON Schema

```json
{
  "method": "v4.0",
  "home_xg": 1.45,
  "away_xg": 0.89,
  "ah_recommendation": "home -0.5",
  "confidence": 65,
  "match_info": {
    "home_team": "string",
    "away_team": "string",
    "competition": "string",
    "data_quality": "high"
  },
  "probabilities": {
    "home_win": "45%",
    "draw": "30%",
    "away_win": "25%"
  },
  "reasoning_summary": "string"
}
```

## 严格约束 (Hard Constraints)

- **⚠️ 绝对禁止自建脚本与直调源码**：只能调用注册的 MCP 工具和 Skills。
- **禁止自行调用外部 API 获取数据**：所有数据由 Orchestrator 预置在 `raw_data` 中。仅当 `raw_data` 不完整时才可调用 `get_match` 补全。
- 胜平负概率之和必须等于 100%（允许 ±0.5% 的浮点误差）
- 置信度 (Confidence) 必须在 [30, 90] 的区间内
- **绝对禁止编造数据** — 缺失的字段必须明确标记

## 文件约定 (File Conventions)

- 比赛黑板：`data/matches/MC-{match_id}.json`
- 你的输出写入 `analysis` 字段
- JSON 文件使用 2 个空格缩进，UTF-8 编码

## 错误处理

| 场景 | 应对动作 |
|------|---------|
| 单个模型分析失败 | 记录错误，不影响其他模型的执行 |
| 数据缺失 | 使用联赛平均数据作为后备，降低置信度 |
| 分析报错 | `status` 退回 `pending`，等待下一轮重试 |

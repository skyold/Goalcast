---
name: goalcast-compare
description: Use this skill as the comparison engine for one match across multiple (model_version, data_source) routes. It is usually called by goalcast-analysis-orchestrator after fixture routing.
---

# Goalcast Compare — 对比分析引擎

版本：3.0 | 职责：接收单场上下文 → 解析对比组合 → 调度 analyzer skills → 输出差异报告

## 重要约束

1. **本 skill 不做具体分析计算。** 分析由 analyzer skills 完成。
2. **本 skill 默认只做“单场多方案对比”**，不负责赛程批量拉取。
3. **批量入口由 `goalcast-analysis-orchestrator` 负责**，compare 作为其子能力。
4. **禁止生成非法组合**（如 `v4.0 + footystats`）并给出清晰报错。
5. **不修改 MCP 入口函数**：仅做 analyzer 调度与结果汇总。

## 触发条件

- 用户要求“同一场比赛用多个模型/数据源对比”
- 用户要求“基线方案 vs 备选方案”差异解释
- 被 `goalcast-analysis-orchestrator` 调用并传入 `mode=compare`

## 执行步骤

### Step 1：接收输入并标准化

优先接收 orchestrator 传入的单场参数：

```
fixture_id
home_team, away_team
home_team_id, away_team_id
season_id, league
match_date, kickoff_time
match_type
comparison_set: [{model_version, data_source}, ...]
```

若独立调用且未传 `fixture_id`，允许按队名+日期定位单场后继续。

### Step 2：构建对比组合（含默认）

合法字段：
- `model_version`: `v2.5` | `v3.0` | `v4.0`
- `data_source`: `footystats` | `sportmonks`

推荐映射（强约束）：
- `v2.5` -> `footystats` -> `goalcast-analyzer-v25`
- `v3.0` -> `footystats` -> `goalcast-analyzer-v30`
- `v4.0` -> `sportmonks` -> `goalcast-analyzer-v40`

默认 `comparison_set`（未指定时）：
```
[
  {"model_version":"v4.0","data_source":"sportmonks"},
  {"model_version":"v3.0","data_source":"footystats"}
]
```

非法组合处理：
- 若组合不在映射表中：标记该组合失败并写入原因
- 其他合法组合继续执行，不因单个非法组合整体中断

### Step 3：调度 analyzer skills（有界并行）

每个组合都传入相同比赛参数，差异仅在 `model_version/data_source`。

调用参数（标准化）：
```
fixture_id
home_team, home_team_id
away_team, away_team_id
season_id, league
match_date, kickoff_time
match_type
model_version
data_source
```

字段映射规则（与 analyzer 文档对齐）：
- `league` -> analyzer 内部 `competition`
- `match_date` -> analyzer 内部 `date`
- `model_version` -> analyzer 内部 `model`

执行策略：
- 并行度上限建议 2（避免上下文和工具争用）
- 单组合失败继续其他组合
- 保留每个组合的 `status / error / result`

### Step 4：统一结果口径

从各组合 `AnalysisResult` 提取统一字段：
- `data_quality`
- `probabilities.home_win/draw/away_win`
- `decision.best_bet`
- `decision.risk_adjusted_ev`
- `decision.confidence`
- `missing_data`

如字段缺失，标记 `N/A`，禁止推断填充。

### Step 5：输出对比报告

```markdown
## [home_team] vs [away_team] — 路由对比
日期：[match_date] | 联赛：[league] | 比赛类型：[match_type]

### 组合概览

| 组合 | 状态 | 数据质量 | 最优投注 | EV_adj | 置信度 |
|------|------|----------|----------|-------:|------:|
| sportmonks+v4.0 | 成功 | 0.82 | 主胜 | +0.09 | 73 |
| footystats+v3.0 | 成功 | 0.74 | 主胜 | +0.06 | 67 |

### 概率差异（百分点）

| 方向 | sportmonks+v4.0 | footystats+v3.0 | 差值 |
|------|-----------------|-----------------|------|
| 主胜 | 52% | 49% | +3 |
| 平局 | 25% | 27% | -2 |
| 客胜 | 23% | 24% | -1 |

### 解释摘要
- 一致结论：两方案都推荐主胜
- 分歧来源：数据源差异导致 EV_adj 与置信度不同
- 风险提示：若任一方案失败，明确列出失败原因并提示“该组合未参与结论投票”
```

## 与 orchestrator 的协作边界

- `goalcast-analysis-orchestrator` 负责：
  - 解析用户意图（单场/批量、普通/compare）
  - 赛程获取与场次选择
  - 在 `mode=compare` 时逐场调用 `goalcast-compare`
- `goalcast-compare` 负责：
  - 单场的多组合执行与差异报告

## 失败处理

- 组合级失败：标记失败并继续其他组合
- 全部失败：返回失败清单并停止，禁止输出投注建议
- 工具超时：记录超时，不自动重试超过 1 次

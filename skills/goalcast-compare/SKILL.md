---
name: goalcast-compare
description: Use this skill to analyze a football match with one or more (data_provider × model) combinations, or to compare results across multiple combinations. Accepts any combination of sportmonks/footystats × v2.5/v3.0.
---

# Goalcast Compare — 统一分析调度器

版本：2.0 | 职责：解析组合列表 → 并行调度子 agent → 输出对比报告

## 重要约束

**本 skill 不包含任何分析逻辑。** 分析由子 agent 完成。
本 skill 只负责：解析请求 → 批量调度 → 收集结果 → 输出报告。

## 触发条件

- 用户指定"用 sportmonks+v3.0 分析"→ 单组合，直接输出结果
- 用户指定"分别用 sportmonks+v3.0 和 footystats+v3.0 分析"→ 多组合，输出对比
- 用户未指定 provider → 默认 `sportmonks+v3.0`
- 被 `goalcast-daily` 调用时，所有参数均由调用方传入

## 执行步骤

### Step 1：解析分析请求

从用户输入或调用方参数中提取：

```
matches: [{home_team, away_team, competition, date}, ...]   ← 比赛列表
combinations: [(data_provider, model), ...]                 ← 组合列表
match_type: "A"  ← 默认 A，可由用户指定
```

**默认组合**：未指定时使用 `[("sportmonks", "v3.0")]`

**合法的 data_provider 值**：`"sportmonks"` | `"footystats"`
**合法的 model 值**：`"v2.5"` | `"v3.0"`

### Step 2：批量规模检查

```
总子 agent 数 = len(matches) × len(combinations)
```

超过 10 个时：展示规模并等待用户确认后再继续。
10 个以内：直接执行，不打扰用户。

### Step 3：并行启动所有子 agent

**每个子 agent 收到以下参数（纯文本，不含 provider ID）：**

```
home_team:     "Arsenal"
away_team:     "Chelsea"
competition:   "Premier League"
date:          "2026-04-12"
data_provider: "sportmonks"          ← 每个 agent 独立
model:         "v3.0"                ← 每个 agent 独立
match_type:    "A"
```

**子 agent 映射**：
- model="v2.5" → 使用 goalcast-analyzer-v25 skill
- model="v3.0" → 使用 goalcast-analyzer-v30 skill

**并行启动所有子 agent，等待全部完成后继续。**

子 agent 内部流程（固定，不与用户交互）：
1. `goalcast_get_todays_matches(data_provider=X, date, league_filter=competition)` → 定位比赛
2. `goalcast_resolve_match(..., data_provider=X)` → 获取 MatchContext（极大概率缓存命中）
3. 执行指定模型分析层
4. 返回 `AnalysisResult` JSON

### Step 4：收集结果并输出

**单组合单场**：直接输出完整分析结果，无需对比表。

**多组合**（任意场数）：

```markdown
## [主队] vs [客队] — 多方案分析对比
日期：YYYY-MM-DD | 联赛：[联赛名] | 比赛类型：A

### 结论对比

| 维度 | sportmonks+v3.0 | footystats+v3.0 | 差异 |
|------|----------------|----------------|------|
| 数据质量 | 0.82 | 0.74 | — |
| 已启用层 | L3完整+L6阵容 | L2近况 | — |
| 主队胜率 | 52% | 49% | ±3% |
| 平局概率 | 25% | 27% | ±2% |
| 客队胜率 | 23% | 24% | ±1% |
| 最佳投注 | 主胜 | 主胜 | ✓一致 |
| EV（风险调整后）| +0.09 | +0.06 | ±0.03 |
| 置信度 | 73 | 67 | ±6 |

### 各方案完整结果

[各方案 AnalysisResult JSON，按组合顺序排列]
```

**单组合批量**：每场一个卡片，末尾附汇总表（高 EV 比赛优先）。

**多组合批量**：每场展示对比，末尾附全场汇总（各方案置信度 ≥ 60 的推荐汇总）。

### 结果失败处理

某子 agent 失败时：
- 在报告中注明 `[组合名] 分析失败`
- 展示可用结果
- 不重试，不估算缺失数据

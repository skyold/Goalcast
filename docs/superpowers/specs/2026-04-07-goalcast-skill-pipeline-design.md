# Goalcast Skill Pipeline 设计文档

**版本**: 1.1
**日期**: 2026-04-07
**状态**: 待实现

---

## 背景与目标

Goalcast 是一个足球比赛分析与预测系统，基于 LLM + 多层量化模型（v2.5 / v3.0）进行比赛分析。

本设计解决以下问题：
1. 如何通过纯对话触发完整分析，无需用户运行任何脚本
2. 如何支持多个分析方法（v2.5 / v3.0）并进行横向对比
3. 如何在 FootyStats 单一数据源限制下，保持分析质量并显式处理数据缺失

---

## 核心原则

- **对话驱动**：用户只需用自然语言表达意图，Claude 自动完成数据采集、分析、输出
- **每个 Skill 完全独立**：每个 analyzer skill 自治，自己拉数据、自己分析、自己输出，不依赖外部协调
- **独立演进**：各分析方法的 skill 文件互不依赖，可以单独迭代升级而不影响其他方法
- **compare 是纯调度器**：不含任何分析逻辑，只负责启动 sub-agent 并对比结果
- **显式降级**：数据缺失时不估算填充，而是明确标注并自动降权
- **统一输出 schema**：所有分析方法输出相同结构，便于对比层 diff

---

## 系统架构

### 组件总览

```
用户对话
    ↓
Claude 识别意图
    ↓
    ├─ 单方法分析 ──→ goalcast-analyzer-v25.skill
    │                  或 goalcast-analyzer-v30.skill
    │
    └─ 多方法对比 ──→ goalcast-compare.skill（纯调度器）
                          ↓
              ┌───────────┴───────────┐
         Sub-agent A            Sub-agent B
    goalcast-analyzer-v25   goalcast-analyzer-v30
         （完全独立）              （完全独立）
              ↓                      ↓
        AnalysisResult          AnalysisResult
              └───────────┬───────────┘
                    对比 + 输出
```

### 文件结构

```
goalcast/
├── skills/
│   ├── goalcast-analyzer-v25.skill  # v2.5 分析方法（完全独立）
│   ├── goalcast-analyzer-v30.skill  # v3.0 分析方法（完全独立）
│   └── goalcast-compare.skill       # 纯调度器，无分析逻辑
├── prompts/
│   ├── v2.5.md                      # v2.5 分析框架参考文档
│   └── v3.0.md                      # v3.0 分析框架参考文档
└── mcp_server/
    └── server.py                    # FootyStats / Sportmonks MCP tools（已有）
```

`prompts/` 目录为参考文档，分析逻辑内嵌于各自的 analyzer skill 文件中。

---

## Skill 设计

### goalcast-analyzer-v25.skill（独立分析 skill）

**职责**：用 v2.5 框架对一场比赛进行完整分析，完全自治。

**触发条件**：
- 用户明确要求用 v2.5 分析（"用 v2.5 分析 XXX"）
- 被 `goalcast-compare.skill` 作为 sub-agent 调用

**执行流程**：

```
Step 1: 定位比赛
  → footystats_get_todays_matches(date, league_filter)
  → 提取 match_id、home_team_id、away_team_id、season_id

Step 2: 采集数据
  → footystats_get_match_details(match_id)
  → footystats_get_team_last_x_stats(home_team_id)
  → footystats_get_team_last_x_stats(away_team_id)
  → footystats_get_league_tables(season_id)
  → footystats_get_league_teams(season_id)        # 可选

Step 3: 零层检查
  → 记录缺失数据，触发对应降级规则

Step 4: v2.5 五层分析
  → L1 基础实力 → L2 状态调整 → L3 市场行为
  → L4 分布模型 → L5 决策与风险

Step 5: 输出 AnalysisResult（统一 schema）
```

---

### goalcast-analyzer-v30.skill（独立分析 skill）

**职责**：用 v3.0 框架对一场比赛进行完整分析，完全自治。

**触发条件**：
- 用户明确要求用 v3.0 分析，或默认单方法分析
- 被 `goalcast-compare.skill` 作为 sub-agent 调用

**执行流程**：

```
Step 1-2: 与 v25 相同（数据采集独立进行）

Step 3: 零层检查（v3.0 显式降级规则）
  → 触发比赛类型分类（A/B/C/D）

Step 4: v3.0 八层分析
  → L0 赛前强制检查
  → L1 基础实力（xG 代理）→ L2 情境调整
  → L3 市场行为（静态赔率降权）→ L4 节奏（跳过，无 PPDA）
  → L5 Dixon-Coles 分布 → L6 贝叶斯（跳过，无阵容）
  → L7 EV/Kelly → L8 置信度校准

Step 5: 输出 AnalysisResult（统一 schema）
```

---

### goalcast-compare.skill（纯调度器）

**职责**：并行调用多个 analyzer skill，收集结果，输出对比。不含任何分析逻辑。

**触发条件**：
- 用户要求对比分析方法
- 用户要分析比赛但未指定方法（默认触发对比）

**执行流程**：

```
Step 1: 解析用户意图
  → 确定比赛信息
  → 确定要对比的方法（默认 v25 + v30）

Step 2: 并行启动 sub-agent
  → Sub-agent A：运行 goalcast-analyzer-v25.skill
  → Sub-agent B：运行 goalcast-analyzer-v30.skill
  （两者完全独立，各自拉数据、各自分析）

Step 3: 收集两份 AnalysisResult

Step 4: 生成对比输出
  → 对比表（概率 / EV / 置信度 / 建议）
  → 主要分歧及原因分析
  → 附上各自完整报告
```

> **注意**：compare 调用时数据会被各 sub-agent 独立拉取（两次），这是为保持 analyzer skill 完全独立所做的权衡，可接受。

---

### 三个 Skill 对比

| | goalcast-analyzer-v25 | goalcast-analyzer-v30 | goalcast-compare |
|---|---|---|---|
| 职责 | v2.5 独立分析 | v3.0 独立分析 | 调度 + 对比 |
| 含分析逻辑 | ✓ | ✓ | ✗ |
| 自主拉数据 | ✓ | ✓ | ✗ |
| 可单独调用 | ✓ | ✓ | ✓ |
| 可独立演进 | ✓ | ✓ | 仅调度逻辑 |
| 典型触发 | "用 v2.5 分析 XXX" | "用 v3.0 分析 XXX" | "对比分析 XXX" |

---

## 数据层设计（每个 analyzer skill 内部）

### FootyStats 字段映射

| 分析层 | 所需数据 | FootyStats 提供 | 降级处理 |
|--------|----------|-----------------|----------|
| L1 基础实力（35%） | xG / xGA | 进球数/失球数作为 xG 代理 | 标注 `xG_proxy`，权重 -5% |
| L2 情境调整（20%） | 阵容/伤病 | 不提供 | 置信度 -10，调整幅度上限压缩至 ±0.2 |
| L3 市场行为（20%） | 赔率变动时序 | 仅静态开盘赔率 | 权重压缩至 8%，标注"低可信度" |
| L4 节奏方差（5%） | PPDA / 逼抢 | 不提供 | 权重降至 0%，跳过 |
| L5 分布模型（10%） | xG 均值输入 | 用 L1 代理值 | 正常执行 Dixon-Coles |
| L6 贝叶斯更新（5%） | 赛前阵容确认 | 不提供 | 跳过，标注"未更新" |
| L7 EV/Kelly | 市场概率 | L3 静态赔率换算 | 使用降权后市场概率 |
| L8 置信度校准 | 综合 | 按缺失项扣分 | 正常执行 |

### 零层检查降级规则

| 缺失数据 | 降级处理 |
|----------|----------|
| 阵容不可用（预期） | 置信度 -10，L2 调整幅度上限 ±0.2 |
| 仅静态赔率，无变动数据 | L3 权重降至 8%，标注"低可信度" |
| PPDA 不可用 | L4 权重 0%，跳过 |
| xG 使用代理值 | L1 标注 `xG_proxy`，data_quality 标注 medium |

---

## 统一输出 Schema（AnalysisResult）

所有 analyzer skill 输出相同结构，保证 compare 层可以直接 diff：

```json
{
  "method": "v2.5 | v3.0",
  "match_info": {
    "home_team": "",
    "away_team": "",
    "competition": "",
    "match_type": "A | B | C | D",
    "data_quality": "high | medium | low",
    "missing_data": []
  },
  "probabilities": {
    "home_win": "0%",
    "draw": "0%",
    "away_win": "0%"
  },
  "top_scores": [
    { "score": "1-0", "probability": "0%" }
  ],
  "market": {
    "market_probabilities": { "home_win": "0%", "draw": "0%", "away_win": "0%" },
    "signal_direction": "支持模型 | 反对模型 | 中立",
    "signal_strength": "强 | 中 | 弱"
  },
  "decision": {
    "ev": 0.0,
    "risk_adjusted_ev": 0.0,
    "best_bet": "",
    "bet_rating": "推荐 | 小注 | 不推荐",
    "confidence": 0
  },
  "reasoning_summary": ""
}
```

---

## 对比输出格式（goalcast-compare 输出）

```markdown
## [主队] vs [客队] — 方法对比
日期: YYYY-MM-DD | 联赛: XXX

| 维度        | v2.5  | v3.0  | 差异   |
|-------------|-------|-------|--------|
| 主队胜率     | 0%    | 0%    | ±0%    |
| 平局         | 0%    | 0%    | ±0%    |
| 客队胜率     | 0%    | 0%    | ±0%    |
| 最佳投注     | -     | -     | ✓/✗    |
| EV          | 0.00  | 0.00  | ±0.00  |
| 置信度       | 0     | 0     | ±0     |

### 主要分歧
- [分歧点1 + 原因]
- [分歧点2 + 原因]

---
### v2.5 完整分析
[AnalysisResult JSON]

### v3.0 完整分析
[AnalysisResult JSON]
```

---

## 约束与边界

1. **数据源**：当前仅 FootyStats 可用；Sportmonks 配置后可补充 xG / 赔率变动，各 analyzer skill 可独立升级数据采集逻辑
2. **自动化**：本期不实现，优先保证对话触发稳定
3. **分析方法扩展**：新增方法只需新建一个 `goalcast-analyzer-vXX.skill`，在 compare 中注册即可
4. **数据重复拉取**：compare 调用时各 sub-agent 独立拉数据（两次），是为保持 skill 完全独立的权衡
5. **禁止编造数据**：数据缺失时必须触发降级规则，不得估算填充

---

## 待实现清单

- [ ] `skills/goalcast-analyzer-v25.skill` — v2.5 完整独立分析 skill
- [ ] `skills/goalcast-analyzer-v30.skill` — v3.0 完整独立分析 skill
- [ ] `skills/goalcast-compare.skill` — 纯调度器，sub-agent 并行 + 对比输出
- [ ] 验证 FootyStats MCP tools 实际返回字段与映射表一致
- [ ] 端到端测试：对话触发 → sub-agent 调用 → 对比输出

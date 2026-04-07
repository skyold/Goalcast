# Goalcast Skill Pipeline 设计文档

**版本**: 1.0
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
- **数据取一次，方法可替换**：FootyStats 数据采集与分析逻辑解耦，所有分析方法共享同一份原始数据
- **显式降级**：数据缺失时不估算填充，而是明确标注并自动降权，来源于 v3.0 零层检查机制
- **统一输出 schema**：所有分析方法输出相同结构，便于对比

---

## 系统架构

### 组件总览

```
用户对话
    ↓
Claude 识别意图
    ↓
[goalcast-compare.md skill]  或  [goalcast-analyze.md skill]
    ↓
数据采集阶段（MCP tools → FootyStats）
    ↓
零层检查（记录缺失数据，触发降级规则）
    ↓
    ├── v2.5 分析块 → AnalysisResult
    └── v3.0 分析块 → AnalysisResult
    ↓
对比输出（对比表 + 各自完整报告）
```

### 文件结构

```
goalcast/
├── skills/
│   ├── goalcast-compare.md     # 多方法对比分析（主力 skill）
│   └── goalcast-analyze.md     # 单方法快速分析
├── prompts/
│   ├── v2.5.md                 # v2.5 分析框架参考文档
│   └── v3.0.md                 # v3.0 分析框架参考文档
└── mcp_server/
    └── server.py               # FootyStats / Sportmonks MCP tools（已有）
```

`prompts/` 目录为参考文档，分析逻辑内嵌于 skill 文件中执行。

---

## Skill 设计

### goalcast-compare.md（主力）

**职责**：对同一场比赛同时运行 v2.5 和 v3.0 分析，输出对比结果。

**触发条件**：
- 用户提到分析/预测某场比赛
- 用户询问今日比赛是否值得关注
- 用户要求对比分析方法

**执行流程**：

```
Step 1: 定位比赛
  → footystats_get_todays_matches(date, league_filter)
  → 提取 match_id、home_team_id、away_team_id、season_id

Step 2: 采集数据（尽量并行）
  → footystats_get_match_details(match_id)         # 赔率、H2H、赛季统计
  → footystats_get_team_last_x_stats(home_team_id) # 主队近5/10场
  → footystats_get_team_last_x_stats(away_team_id) # 客队近5/10场
  → footystats_get_league_tables(season_id)        # 积分榜（动力因素）
  → footystats_get_league_teams(season_id)         # 可选：赛季实力对比

Step 3: 零层检查
  → 检查并记录以下数据可用性：
    □ 赛季进/失球统计
    □ 近5/10场数据
    □ 赔率数据（静态）
    □ 积分榜
    □ 阵容信息（预期缺失，触发降级）

Step 4: v2.5 分析
  → 使用 v2.5 框架（5层）进行推理
  → 输出 AnalysisResult（统一 schema）

Step 5: v3.0 分析
  → 使用 v3.0 框架（8层 + 显式降级规则）进行推理
  → 输出 AnalysisResult（统一 schema）

Step 6: 对比输出
  → 生成对比表
  → 列出主要分歧及原因
  → 附上各自完整报告
```

---

### goalcast-analyze.md（单方法）

**职责**：快速运行单一分析方法，token 消耗低。

**触发条件**：
- 用户明确指定分析方法（"用 v3.0 分析 XXX"）
- 需要快速结果时

**参数**：
- 比赛信息（必填）
- 分析方法：`v2.5` | `v3.0`（默认 v3.0）

---

### 两个 Skill 对比

| | goalcast-compare | goalcast-analyze |
|---|---|---|
| 用途 | 方法横向对比 | 快速单方法 |
| 典型触发 | "分析今日英超比赛" | "用 v3.0 分析曼城 vs 利物浦" |
| 分析方法数 | v2.5 + v3.0 | 指定一个 |
| 输出 | 对比表 + 双份报告 | 单份报告 |
| Token 消耗 | 高 | 低 |

---

## 数据层设计

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

### 零层检查降级规则（继承自 v3.0）

| 缺失数据 | 降级处理 |
|----------|----------|
| 阵容不可用（预期） | 置信度 -10，L2 调整幅度上限 ±0.2 |
| 仅静态赔率，无变动数据 | L3 权重降至 8%，标注"低可信度" |
| PPDA 不可用 | L4 权重 0%，跳过 |
| xG 使用代理值 | L1 标注 `xG_proxy`，data_quality 标注 medium |

---

## 统一输出 Schema（AnalysisResult）

所有分析方法输出相同结构，保证对比层可以直接 diff：

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

## 对比输出格式

```markdown
## [主队] vs [客队] — 方法对比
日期: YYYY-MM-DD | 联赛: XXX | 数据质量: medium

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

1. **数据源**：当前仅 FootyStats 可用；Sportmonks 配置后可补充 xG / 赔率变动，届时更新数据映射表
2. **自动化**：本期不实现，优先保证对话触发稳定
3. **分析方法扩展**：新增方法只需在 skill 中添加新分析块，数据采集层不变
4. **禁止编造数据**：数据缺失时必须触发降级规则，不得估算填充（继承 v3.0 核心约束）

---

## 待实现清单

- [ ] `skills/goalcast-compare.md` — 多方法对比 skill（含完整分析逻辑）
- [ ] `skills/goalcast-analyze.md` — 单方法快速分析 skill
- [ ] 验证 FootyStats MCP tools 实际返回字段与映射表一致
- [ ] 端到端测试：对话触发 → MCP 调用 → 分析输出

# Goalcast Skill Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 创建三个 Claude Code skill 文件，实现纯对话驱动的多方法足球比赛分析与对比系统。

**Architecture:** 每个 analyzer skill（v25 / v30）完全独立自治，自行调用 FootyStats MCP tools 拉取数据并执行分析，输出统一的 AnalysisResult schema。`goalcast-compare.skill` 作为纯调度器，并行启动两个 sub-agent 分别执行各 analyzer skill，收集结果后生成对比报告。

**Tech Stack:** Claude Code Skills（Markdown prompt files）、FootyStats MCP tools（`mcp__goalcast__*`）、Claude Agent SDK（sub-agent dispatch）

---

## 文件清单

| 操作 | 路径 | 职责 |
|------|------|------|
| 新建目录 | `skills/` | 存放所有 skill 文件 |
| 新建 | `skills/goalcast-analyzer-v25.skill` | v2.5 五层分析，完全独立 |
| 新建 | `skills/goalcast-analyzer-v30.skill` | v3.0 八层分析，完全独立 |
| 新建 | `skills/goalcast-compare.skill` | 纯调度器，无分析逻辑 |
| 新建 | `docs/superpowers/fixtures/test-match-validation.md` | 验证用 checklist |

---

## Task 1: 探索 FootyStats 真实字段结构

在写 skill 之前，必须先了解 FootyStats API 返回的真实字段名，避免 skill 引用不存在的字段。

**Files:**
- 新建: `docs/superpowers/fixtures/footystats-field-map.md`

- [ ] **Step 1: 获取今日比赛列表，记录字段结构**

在对话中运行：
```
调用 mcp__goalcast__footystats_get_todays_matches，不带任何参数，
记录返回的 data[] 数组中每个比赛对象的字段名。
重点关注：match_id、home_id、away_id、season_id、competition_id 字段的实际名称。
```

预期：拿到今日所有比赛列表，确认 match_id / team_id 字段名。

- [ ] **Step 2: 获取比赛详情，记录字段结构**

取 Step 1 中任意一个 match_id，在对话中运行：
```
调用 mcp__goalcast__footystats_get_match_details(match_id=<取到的ID>)
记录返回对象中以下分类的字段名：
- 赔率相关：odds_ft_1（主）、odds_ft_x（平）、odds_ft_2（客）等
- 赛季统计：home_ppg、away_ppg、home_xg 等（如有）
- H2H 数据：h2h 数组结构
```

- [ ] **Step 3: 获取球队近况，记录字段结构**

取 Step 1 中任意 home_id，在对话中运行：
```
调用 mcp__goalcast__footystats_get_team_last_x_stats(team_id=<home_id>)
记录 lastx 数组中每场比赛的字段名，重点：
- 进球：goals_scored、goals_conceded（或类似名称）
- 场均：avg_goals_scored_per_match 等
```

- [ ] **Step 4: 将真实字段名写入 fixture 文档**

创建 `docs/superpowers/fixtures/footystats-field-map.md`，内容如下（根据实际观察填写）：

```markdown
# FootyStats 真实字段映射

## get_todays_matches → 比赛对象
- match_id: `id`（或 `match_id`，以实际为准）
- 主队 ID: `homeID`（或 `home_id`）
- 客队 ID: `awayID`（或 `away_id`）
- 赛季 ID: `season_id`
- 联赛名: `competition_name`

## get_match_details → 比赛详情
- 主队开盘赔率: `odds_ft_1`
- 平局开盘赔率: `odds_ft_x`
- 客队开盘赔率: `odds_ft_2`
- 主队赛季进球: `home_team_stats.seasonGoals_overall`（如有）

## get_team_last_x_stats → 近况
- 近5场进球: `stats.5.goals_scored`（或类似路径）
- 近5场失球: `stats.5.goals_conceded`
- 近10场均值: `stats.10.avg_goals_scored_per_match`
```

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/fixtures/footystats-field-map.md
git commit -m "docs: add FootyStats real field mapping from API exploration"
```

---

## Task 2: 创建 skills 目录和验证 Checklist

**Files:**
- 新建目录: `skills/`
- 新建: `docs/superpowers/fixtures/test-match-validation.md`

- [ ] **Step 1: 创建 skills 目录**

```bash
mkdir -p /Users/zhengningdai/workspace/skyold/Goalcast/skills
```

- [ ] **Step 2: 选定测试比赛**

从 Task 1 Step 1 的结果中选一场英超比赛作为整个验证流程的固定测试用例，记录：
- 主队名 / 客队名
- match_id
- season_id

将此信息写在 `docs/superpowers/fixtures/test-match-validation.md` 顶部。

- [ ] **Step 3: 写 AnalysisResult 验证 Checklist**

创建 `docs/superpowers/fixtures/test-match-validation.md`：

```markdown
# AnalysisResult 验证 Checklist

## 测试比赛
- 主队: [填入]
- 客队: [填入]
- match_id: [填入]
- 联赛: Premier League

## 必须通过的验证项

### 结构完整性
- [ ] 输出包含 `method` 字段，值为 "v2.5" 或 "v3.0"
- [ ] 输出包含 `match_info` 对象，含 home_team / away_team / competition
- [ ] 输出包含 `probabilities`，含 home_win / draw / away_win
- [ ] 输出包含 `decision`，含 ev / confidence / bet_rating
- [ ] 输出包含 `reasoning_summary`（非空字符串）

### 数值约束（继承自 v3.0 核心约束）
- [ ] home_win% + draw% + away_win% = 100%（允许 ±0.5%）
- [ ] confidence 在 [30, 90] 范围内
- [ ] ev 在 [-1, +2] 范围内
- [ ] bet_rating 是 "推荐" / "小注" / "不推荐" 之一

### 数据质量标注
- [ ] `missing_data` 列出了至少 "lineup"（因 FotMob 不可用）
- [ ] `data_quality` 为 "medium"（因 xG 使用代理值）
- [ ] `reasoning_summary` 中提到了数据降级

### v3.0 专属
- [ ] `match_type` 为 A/B/C/D 之一
- [ ] 如有 L4 节奏层，标注"跳过（无 PPDA 数据）"
- [ ] 如有 L6 贝叶斯层，标注"跳过（无阵容确认）"
```

- [ ] **Step 4: Commit**

```bash
git add skills/ docs/superpowers/fixtures/test-match-validation.md
git commit -m "chore: create skills directory and validation checklist"
```

---

## Task 3: goalcast-analyzer-v25.skill

**Files:**
- 新建: `skills/goalcast-analyzer-v25.skill`

- [ ] **Step 1: 先验证 skill 输出应该是什么（定义期望）**

在对话中手动跑一遍以下逻辑，确认数据可用性：
```
用 mcp__goalcast__footystats_get_match_details 拉 Task 2 的测试比赛，
确认赔率字段（odds_ft_1 / odds_ft_x / odds_ft_2）存在且非零。
如果字段名不同，更新 Task 1 的字段映射文档。
```

- [ ] **Step 2: 创建 goalcast-analyzer-v25.skill**

创建 `skills/goalcast-analyzer-v25.skill`，完整内容如下：

````markdown
# Goalcast Analyzer v2.5

版本：v2.5 | 框架：五层分析模型

## 触发条件

以下任意情况激活此 skill：
- 用户说"用 v2.5 分析 [比赛]"
- 被 goalcast-compare.skill 作为 sub-agent 调用（此时比赛信息通过 context 传入）

## 执行步骤

### Step 1：定位比赛

调用 `mcp__goalcast__footystats_get_todays_matches`。

参数：
- date：用户指定日期，默认今天（YYYY-MM-DD 格式）
- league_filter：从用户意图中提取联赛名，例如 "Premier League"

从返回的 data[] 中找到目标比赛，提取：
- match_id
- home_team_id（字段名以 Task 1 探索结果为准，通常是 homeID）
- away_team_id（通常是 awayID）
- season_id
- home_team_name / away_team_name
- competition_name

如果找不到比赛，回复"未找到符合条件的比赛，请确认日期和联赛名称"，停止执行。

### Step 2：并行采集数据

同时调用以下工具：

```
mcp__goalcast__footystats_get_match_details(match_id)
mcp__goalcast__footystats_get_team_last_x_stats(team_id=home_team_id)
mcp__goalcast__footystats_get_team_last_x_stats(team_id=away_team_id)
mcp__goalcast__footystats_get_league_tables(season_id)
```

记录每个调用是否成功，失败项列入 missing_data。

### Step 3：零层数据检查

在分析前，检查并记录数据可用性：

| 数据项 | 状态 | 降级处理 |
|--------|------|----------|
| 主队近况（last_x） | 可用/不可用 | 不可用则 L1 标注 low |
| 客队近况（last_x） | 可用/不可用 | 不可用则 L1 标注 low |
| 赔率数据（odds_ft_*） | 可用/不可用 | 不可用则 L3 跳过 |
| 积分榜 | 可用/不可用 | 不可用则 L2 动力因素跳过 |
| 阵容数据 | **预期缺失** | L2 调整幅度上限 ±0.2，置信度 -10 |
| xG 直接数据 | **预期缺失** | 用进球率作为代理（xG_proxy） |

### Step 4：v2.5 五层分析

**核心原则**：将信息分层处理，不混淆各层。禁止编造统计数字。

---

**第一层 — 基础实力（权重 40%）**

使用近况数据建立基础实力：
- 主队 xG 代理 = 近10场场均进球 × 0.7 + 近5场场均进球 × 0.3
- 客队 xG 代理 = 同上
- 主客场优势修正：主队 xG_proxy +0.2（联赛通用值，无联赛特定数据时使用）
- 输出：base_xg_home, base_xg_away

如近况数据不可用，标注 data_quality=low，base_xg 使用联赛均值（英超：主 1.5 / 客 1.2），并注明"基于联赛均值估算"。

---

**第二层 — 状态调整（权重 25%）**

将可获取的短期因素转为结构化 xG 调整：

1. 动力因素（来自积分榜）：
   - 如主队积分差距 ≤3 分（争冠/保级）：+0.2 xG
   - 如客队同上：+0.2 xG

2. 阵容不确定性（预期触发）：
   - 调整幅度上限压缩至 ±0.2 xG（无法超过）
   - 置信度基础分 -10

3. 无法获取的因素（明确标注跳过，不估算）：
   - 伤病/停赛：标注"数据不可用，跳过"
   - 赛程疲劳：标注"数据不可用，跳过"

输出：adjusted_xg_home, adjusted_xg_away，以及每项调整的量化值。

---

**第三层 — 市场行为（权重 20%）**

使用 match_details 中的开盘赔率：
- 字段：odds_ft_1（主）、odds_ft_x（平）、odds_ft_2（客）
- 市场概率计算：P = 1 / odds（去除超售后归一化）
  - 超售率 = 1/odds_1 + 1/odds_x + 1/odds_2
  - 归一化：P_home = (1/odds_1) / 超售率

如赔率字段为0或缺失：
- 跳过第三层，市场信号标注"不可用"，signal_direction="中立"

模型与市场分歧 = 模型概率 - 市场概率（各结果）

---

**第四层 — 分布模型（权重 10%）**

使用 adjusted_xg 计算比分概率矩阵（标准泊松分布，v2.5 不使用 Dixon-Coles）：

P(主队进n球) = e^(-λ_home) × λ_home^n / n!
P(客队进n球) = e^(-λ_away) × λ_away^n / n!

λ_home = adjusted_xg_home
λ_away = adjusted_xg_away

计算 0-5 × 0-5 的比分矩阵，汇总：
- P(主胜) = 所有主队进球 > 客队进球的概率之和
- P(平) = 所有主客进球相等的概率之和
- P(客胜) = 剩余概率

取概率最高的前3个比分作为 top_scores。

---

**第五层 — 决策与风险（权重 5%）**

EV 计算（v2.5 简化版）：
```
EV = 模型概率 - 市场概率

投注决策：
- EV > 0.08 → 推荐（标准仓位）
- EV 0.04~0.08 → 小注
- EV < 0.04 → 不推荐
```

置信度计算：
```
基础分 = 70
- 阵容不可用：-10
- xG 使用代理值：-5
- 市场方向一致：+8
- 市场不可用：不加分
- 近况数据完整：+5

范围限制：[30, 90]
```

### Step 5：输出 AnalysisResult

严格按以下 JSON schema 输出，字段不得增减：

```json
{
  "method": "v2.5",
  "match_info": {
    "home_team": "<主队名>",
    "away_team": "<客队名>",
    "competition": "<联赛名>",
    "match_type": "A",
    "data_quality": "medium",
    "missing_data": ["lineup", "xG_direct", "ppda"]
  },
  "probabilities": {
    "home_win": "<X%>",
    "draw": "<X%>",
    "away_win": "<X%>"
  },
  "top_scores": [
    { "score": "1-0", "probability": "<X%>" },
    { "score": "1-1", "probability": "<X%>" },
    { "score": "2-1", "probability": "<X%>" }
  ],
  "market": {
    "market_probabilities": {
      "home_win": "<X%>",
      "draw": "<X%>",
      "away_win": "<X%>"
    },
    "signal_direction": "支持模型 | 反对模型 | 中立",
    "signal_strength": "强 | 中 | 弱"
  },
  "decision": {
    "ev": 0.0,
    "risk_adjusted_ev": 0.0,
    "best_bet": "<主胜|平|客胜|不推荐>",
    "bet_rating": "推荐 | 小注 | 不推荐",
    "confidence": 0
  },
  "reasoning_summary": "<简明描述各层关键结论，包含数据降级说明>"
}
```

**输出校验（必须在输出前自检）：**
- home_win% + draw% + away_win% 之和 = 100%（±0.5%）
- confidence 在 [30, 90] 内
- ev 在 [-1, +2] 内
- reasoning_summary 非空
- missing_data 包含 "lineup"（因阵容预期不可用）
````

- [ ] **Step 3: 用测试比赛触发 skill，验证输出**

在对话中输入：
```
用 v2.5 分析 [Task 2 中选定的测试比赛名]
```

对照 `docs/superpowers/fixtures/test-match-validation.md` 中的 checklist，逐项验证。

预期：所有 checklist 项通过（v2.5 专属项除外）。

- [ ] **Step 4: 修复发现的问题**

如有字段名错误（字段不存在）：
- 更新 `docs/superpowers/fixtures/footystats-field-map.md`
- 对应修改 skill 中引用的字段名

如概率不能归一化（赔率字段缺失）：
- 确认 skill 中的降级逻辑正确触发

- [ ] **Step 5: Commit**

```bash
git add skills/goalcast-analyzer-v25.skill
git commit -m "feat: add goalcast-analyzer-v25 skill with v2.5 five-layer analysis"
```

---

## Task 4: goalcast-analyzer-v30.skill

**Files:**
- 新建: `skills/goalcast-analyzer-v30.skill`

- [ ] **Step 1: 创建 goalcast-analyzer-v30.skill**

创建 `skills/goalcast-analyzer-v30.skill`，完整内容如下：

````markdown
# Goalcast Analyzer v3.0

版本：v3.0 | 框架：八层量化分析模型 + 零层强制检查

## 触发条件

以下任意情况激活此 skill：
- 用户说"用 v3.0 分析 [比赛]"或未指定版本的单方法分析
- 被 goalcast-compare.skill 作为 sub-agent 调用

## 核心约束（绝对禁止违反）

1. 禁止编造统计数字 — 数据不可得时，必须显式降权
2. 禁止情感化语言 — 禁止"状态火热"等表述
3. 置信度上限 90 分
4. 投注建议仅在 EV_adj > 0.05 时输出
5. 禁止跳过零层数据检查

## 执行步骤

### Step 1：定位比赛

调用 `mcp__goalcast__footystats_get_todays_matches`。

参数：
- date：用户指定日期，默认今天（YYYY-MM-DD）
- league_filter：从用户意图提取，例如 "Premier League"

提取：match_id、home_team_id（homeID）、away_team_id（awayID）、season_id、比赛名称。

如未找到：回复"未找到比赛，请确认日期和联赛"，停止。

### Step 2：并行采集数据

同时调用：
```
mcp__goalcast__footystats_get_match_details(match_id)
mcp__goalcast__footystats_get_team_last_x_stats(team_id=home_team_id)
mcp__goalcast__footystats_get_team_last_x_stats(team_id=away_team_id)
mcp__goalcast__footystats_get_league_tables(season_id)
```

### 零层：赛前强制检查（必须首先执行）

**比赛类型分类：**
- A：联赛常规轮次（默认）
- B：杯赛单场淘汰
- C：双回合次回合（需用户提供首回合比分）
- D：关键积分场次（积分差 ≤3 分且赛季后半段）

**数据可用性检查表：**

| 数据项 | 来源 | 状态 | 降级规则 |
|--------|------|------|----------|
| 近况数据（last_x） | FootyStats | 检查 | 不可用 → data_quality=low |
| 赔率数据（odds_ft_*） | match_details | 检查 | 不可用 → L3 权重降至 0% |
| 积分榜 | FootyStats | 检查 | 不可用 → L2 动力因素跳过 |
| 阵容/首发 | **预期缺失** | 缺失 | 置信度 -10，L2 上限 ±0.2 |
| xG 直接数据 | **预期缺失** | 缺失 | L1 使用 xG_proxy，标注 medium |
| PPDA 数据 | **预期缺失** | 缺失 | L4 权重 = 0%，跳过 |

记录所有缺失项到 missing_data[]。

### 第一层：基础实力模型（权重 35%）

**xG 代理计算（xG_proxy）：**
```
主队 xG_proxy = 近10场场均进球 × 0.7 + 近5场场均进球 × 0.3
客队 xG_proxy = 同上
```

**主场优势修正（联赛参数表）：**

| 联赛 | 主场 xG 修正 | 场均进球 |
|------|-------------|---------|
| 英超 | +0.25 | 2.75 |
| 西甲 | +0.22 | 2.65 |
| 意甲 | +0.20 | 2.55 |
| 德甲 | +0.28 | 3.05 |
| 法甲 | +0.26 | 2.60 |
| 欧冠 | +0.18 | 2.50 |
| 其他 | +0.20 | 2.60 |

主队 base_xg = xG_proxy_home + 主场修正值
客队 base_xg = xG_proxy_away

如近况数据不可用：使用联赛场均进球的 50/50 分配，标注 data_quality=low。

### 第二层：情境调整模型（权重 20%）

将所有短期因素转为结构化 xG 调整，禁止叙述性描述：

1. **动力因素（积分榜数据）：**
   - 比赛类型 D：动力调整系数 ×1.5
   - 争冠/争欧区（积分差 ≤3）：+0.2 xG
   - 保级区（后三名或差距 ≤3）：+0.2 xG

2. **阵容不确定性（预期触发）：**
   - 调整幅度上限：±0.2 xG（硬性限制）
   - 置信度 -10

3. **无法获取的因素（明确标注）：**
   - 伤病/停赛：标注"数据不可用，跳过"
   - 赛程疲劳：标注"数据不可用，跳过"
   - 旅行/天气：标注"数据不可用，跳过"

输出：adjusted_xg_home, adjusted_xg_away，各项调整量。

### 第三层：市场行为分析（权重 20% → 降级后 8%）

**由于仅有静态开盘赔率，本层权重自动降至 8%，标注"低可信度"。**

使用 match_details 中的 odds_ft_1 / odds_ft_x / odds_ft_2：
```
超售率 = 1/odds_1 + 1/odds_x + 1/odds_2
市场概率（归一化）：
  P_home = (1/odds_1) / 超售率
  P_draw = (1/odds_x) / 超售率
  P_away = (1/odds_2) / 超售率
```

分歧 = 模型概率 - 市场概率（各方向）

信号强度判断：
- |分歧| > 0.10 → 强
- |分歧| 0.05~0.10 → 中
- |分歧| < 0.05 → 弱

如赔率字段缺失/为0：跳过本层，signal_direction="中立"，signal_strength="弱"。

### 第四层：节奏方差模型（权重 0%）

**由于 PPDA 数据不可用，本层跳过。**

标注："L4 节奏层：跳过（FootyStats 不提供 PPDA 数据）"

### 第五层：分布模型（权重 10%）

使用 Dixon-Coles 修正泊松分布：

标准泊松：
```
P(X=k) = e^(-λ) × λ^k / k!
```

Dixon-Coles 低比分修正系数（ρ = -0.1）：
```
τ(x, y, λ, μ, ρ):
  if x=0, y=0: (1 - λ×μ×ρ)
  if x=0, y=1: (1 + λ×ρ)
  if x=1, y=0: (1 + μ×ρ)
  if x=1, y=1: (1 - ρ)
  else: 1.0
```

λ = adjusted_xg_home，μ = adjusted_xg_away

计算 0-5 × 0-5 矩阵，汇总 P(主胜) / P(平) / P(客胜)，取前3高概率比分。

### 第六层：贝叶斯更新（权重 5%）

**由于无法获取赛前阵容确认，本层跳过。**

标注："L6 贝叶斯层：跳过（无 FotMob 阵容数据）"

### 第七层：EV 与 Kelly 决策

```
EV = (模型概率 × 赔率) - 1

风险调整系数：
- 阵容不确定（预期触发）：× 0.85
- 市场低可信度（静态赔率）：× 0.90
叠加：EV_adj = EV × 0.85 × 0.90

投注决策：
- EV_adj > 0.10 + confidence > 70 → 推荐，标准仓位
- EV_adj 0.05~0.10 + confidence ≥ 60 → 小注
- EV_adj < 0.05 → 不推荐
```

### 第八层：置信度校准

```
基础分 = 70

加分：
+10  市场方向与模型一致（signal_direction="支持模型"）
+5   近况数据完整（主客队均有 last_x 数据）

扣分：
-10  阵容不可用（预期触发）
-5   xG 使用代理值（预期触发）
-5   L3 市场权重降级（静态赔率）
-5   赔率方向与模型相反

范围：[30, 90]，禁止超过 90。
```

### Step 5：输出 AnalysisResult

严格按以下 schema 输出：

```json
{
  "method": "v3.0",
  "match_info": {
    "home_team": "<主队名>",
    "away_team": "<客队名>",
    "competition": "<联赛名>",
    "match_type": "A|B|C|D",
    "data_quality": "medium",
    "missing_data": ["lineup", "xG_direct", "ppda", "odds_movement"]
  },
  "probabilities": {
    "home_win": "<X%>",
    "draw": "<X%>",
    "away_win": "<X%>"
  },
  "top_scores": [
    { "score": "1-0", "probability": "<X%>" },
    { "score": "1-1", "probability": "<X%>" },
    { "score": "2-1", "probability": "<X%>" }
  ],
  "market": {
    "market_probabilities": {
      "home_win": "<X%>",
      "draw": "<X%>",
      "away_win": "<X%>"
    },
    "signal_direction": "支持模型 | 反对模型 | 中立",
    "signal_strength": "强 | 中 | 弱"
  },
  "decision": {
    "ev": 0.0,
    "risk_adjusted_ev": 0.0,
    "best_bet": "<主胜|平|客胜|不推荐>",
    "bet_rating": "推荐 | 小注 | 不推荐",
    "confidence": 0
  },
  "reasoning_summary": "<各层关键结论，包含哪些层跳过及原因，数据降级说明>"
}
```

**输出前自检：**
- home_win% + draw% + away_win% = 100%（±0.5%）
- confidence ∈ [30, 90]
- ev ∈ [-1, +2]
- missing_data 包含 "lineup"、"xG_direct"、"ppda"
- reasoning_summary 提及 L4 和 L6 跳过原因
````

- [ ] **Step 2: 用测试比赛触发 skill，验证输出**

在对话中输入：
```
用 v3.0 分析 [Task 2 中的测试比赛名]
```

对照 `docs/superpowers/fixtures/test-match-validation.md`，验证所有 checklist 项，包括 v3.0 专属项：
- match_type 已分类
- L4 标注"跳过（无 PPDA）"
- L6 标注"跳过（无阵容）"
- missing_data 包含 "odds_movement"

- [ ] **Step 3: 对比 v2.5 和 v3.0 输出差异**

用同一场比赛分别触发两个 skill，确认：
- 两者输出的 probabilities 方向一致（主胜概率相差应 < 10%，差距过大说明某个 skill 有逻辑错误）
- v3.0 置信度 ≤ v2.5 置信度（因为 v3.0 有更多扣分项）
- 两者 reasoning_summary 不完全相同（说明各层逻辑确实不同）

- [ ] **Step 4: Commit**

```bash
git add skills/goalcast-analyzer-v30.skill
git commit -m "feat: add goalcast-analyzer-v30 skill with v3.0 eight-layer analysis"
```

---

## Task 5: goalcast-compare.skill（纯调度器）

**Files:**
- 新建: `skills/goalcast-compare.skill`

- [ ] **Step 1: 创建 goalcast-compare.skill**

创建 `skills/goalcast-compare.skill`，完整内容如下：

````markdown
# Goalcast Compare

版本：1.0 | 职责：纯调度器，无分析逻辑

## 触发条件

以下任意情况激活此 skill：
- 用户要分析比赛但未指定具体分析方法
- 用户明确要求对比多个分析方法
- 用户问"哪个方法更准"

## 重要约束

**本 skill 不包含任何分析逻辑。** 所有分析由子 skill 完成。本 skill 只负责：
1. 理解用户意图（比赛 + 要对比的方法）
2. 并行启动 sub-agent
3. 收集结果
4. 生成对比报告

## 执行步骤

### Step 1：解析用户意图

从用户输入中提取：
- 比赛信息：主队名 / 客队名 / 联赛 / 日期（默认今天）
- 对比方法：默认 v2.5 + v3.0；用户可指定其他组合

### Step 2：并行启动 sub-agent

**同时**启动以下两个独立 sub-agent（不要顺序执行）：

**Sub-agent A：**
- 任务：以 v2.5 方法分析 [比赛信息]
- 使用 skill：goalcast-analyzer-v25.skill
- 传入上下文：[比赛名称、联赛、日期]

**Sub-agent B：**
- 任务：以 v3.0 方法分析 [比赛信息]
- 使用 skill：goalcast-analyzer-v30.skill
- 传入上下文：[比赛名称、联赛、日期]

等待两个 sub-agent 均完成，收集各自的 AnalysisResult JSON。

### Step 3：验证结果完整性

检查两份 AnalysisResult 是否包含必要字段：
- probabilities（home_win / draw / away_win）
- decision（ev / confidence / bet_rating）
- method 字段正确（分别为 "v2.5" 和 "v3.0"）

如任一结果缺失或格式错误，说明对应 sub-agent 执行失败，在报告中注明并展示可用的那份结果。

### Step 4：生成对比报告

输出以下格式：

```markdown
## [主队] vs [客队] — 多方法分析对比
**日期**：YYYY-MM-DD | **联赛**：[联赛名] | **数据质量**：medium

---

### 结论对比

| 维度 | v2.5 | v3.0 | 差异 |
|------|------|------|------|
| 主队胜率 | X% | X% | ±X% |
| 平局 | X% | X% | ±X% |
| 客队胜率 | X% | X% | ±X% |
| 最佳投注 | X | X | ✓一致 / ✗分歧 |
| EV（风险调整后） | X | X | ±X |
| 置信度 | X | X | ±X |

### 主要分歧点

（列出概率或建议存在明显差异的地方及原因，如无分歧则写"两个方法结论一致"）

---

### v2.5 完整分析

[粘贴 Sub-agent A 的完整 AnalysisResult JSON]

---

### v3.0 完整分析

[粘贴 Sub-agent B 的完整 AnalysisResult JSON]
```

## 扩展：添加新分析方法

当有新的 analyzer skill（如 goalcast-analyzer-v40.skill）时，在 Step 2 中增加对应 Sub-agent C 即可。compare skill 的其他部分无需修改。
````

- [ ] **Step 2: 触发 goalcast-compare，验证并行调用**

在对话中输入：
```
对比分析今天英超的 [测试比赛名]
```

验证：
- 对话中出现两份独立的 AnalysisResult（method 分别为 "v2.5" 和 "v3.0"）
- 生成了对比表
- 主队胜率差异 < 15%（若差距过大，说明某 skill 有逻辑问题）
- 报告末尾附上了两份完整 JSON

- [ ] **Step 3: 验证单独触发每个 analyzer 也能正常工作**

分别测试：
```
用 v2.5 分析今天英超的 [测试比赛名]
```
```
用 v3.0 分析今天英超的 [测试比赛名]
```

验证每个 skill 在不经过 compare 的情况下也能独立完成分析。

- [ ] **Step 4: Commit**

```bash
git add skills/goalcast-compare.skill
git commit -m "feat: add goalcast-compare skill as pure dispatcher for multi-method analysis"
```

---

## Task 6: 端到端验证与 Checklist 归档

**Files:**
- 修改: `docs/superpowers/fixtures/test-match-validation.md`（补充实际测试结果）

- [ ] **Step 1: 完整跑一遍 compare 流程**

选择一场今日英超比赛（如有），在对话中输入：
```
帮我对比分析今天英超的比赛
```

验证完整流程：FootyStats MCP 调用 → 两个 sub-agent 分析 → 对比输出。

- [ ] **Step 2: 验证数据降级标注正确**

检查两份 AnalysisResult 中：
- `missing_data` 都包含 `["lineup", "xG_direct", "ppda"]`
- `data_quality` 均为 `"medium"`
- v3.0 结果中 reasoning_summary 提及 L4/L6 跳过

- [ ] **Step 3: 在 fixture 文档记录实际测试结果**

在 `docs/superpowers/fixtures/test-match-validation.md` 末尾添加：

```markdown
## 实际测试记录

### 测试日期：2026-04-07
- 测试比赛：[填入]
- v2.5 主队胜率：[填入]
- v3.0 主队胜率：[填入]
- 差异：[填入]%
- 所有 checklist 项：通过 / [列出未通过项]
```

- [ ] **Step 4: 最终 Commit**

```bash
git add skills/ docs/superpowers/fixtures/
git commit -m "feat: complete goalcast skill pipeline - v25/v30 analyzers + compare dispatcher"
```

---

## 快速参考

### 触发话术

| 意图 | 话术示例 |
|------|---------|
| 默认对比分析 | "帮我分析今天英超曼城对利物浦" |
| 指定 v2.5 | "用 v2.5 分析曼城对利物浦" |
| 指定 v3.0 | "用 v3.0 分析曼城对利物浦" |
| 明确对比 | "对比两种方法分析曼城对利物浦" |

### 数据降级速查

| 缺失数据 | 预期 / 偶发 | 影响层 |
|----------|------------|--------|
| 阵容/首发 | 预期缺失 | L2 ±0.2 上限，置信度 -10 |
| xG 直接值 | 预期缺失 | L1 使用 xG_proxy |
| PPDA | 预期缺失 | L4 跳过（v3.0）|
| 赔率变动时序 | 预期缺失 | L3 权重降至 8% |
| 赔率静态值 | 偶发缺失 | L3 完全跳过 |
| 近况数据 | 偶发缺失 | L1 使用联赛均值，data_quality=low |

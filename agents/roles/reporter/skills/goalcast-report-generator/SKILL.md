---
name: goalcast-report-generator
description: Reporting logic for Reporter. Reads predictions and trades JSONs, synthesizes data, and formats an insightful Markdown report for users.
---

# Goalcast Report Generator — 赛事洞察生成技能 (SOP)

版本：1.0 | 角色归属：Reporter (GCR) | 职责：拉取分析与交易 JSON → 数据降维翻译 → 撰写深度 Markdown 报告

## 设计原则

1. **信息降维与故事化**：不要让用户看枯燥的 JSON。将冰冷的 EV 和 Kelly Fraction 翻译为通俗易懂的“价值洼地”与“建议仓位”。
2. **聚焦核心发现**：过滤掉 `NO_BET` 和置信度极低的比赛，将报告的篇幅（70% 以上）留给系统真正决定重仓下注的赛事。
3. **只读呈现**：严禁在此阶段修改任何 Analyst 的胜率或 Trader 的金额，Reporter 仅具有展示与解释的权力。
4. **格式美学**：严格遵守 Markdown 排版规范，使用 Emoji 增强可读性，做到一目了然。

## 触发条件与上下文传递

由 `goalcast-analysis-orchestrator` 调度，在**所有比赛**的 Analyst 和 Trader 批处理任务彻底完成后触发（通常作为每日定时任务的最后一环）。

**输入参数 (Context)**:
- `target_date`: 目标分析日期 (YYYY-MM-DD)，若未指定默认读取今天。

## 执行步骤

### Step 1: 收集与聚合数据 (Data Harvesting)
- 扫描 `team/data/predictions/` 和 `team/data/trades/` 目录下带有 `target_date` 标签的所有 JSON 文件。
- 扫描 `team/data/logs/` 目录，提取当天的 Orchestrator 诊断日志（`orchestrator_YYYY-MM-DD.log`），以了解是否有比赛在分析环节遭遇失败、降级或熔断。
- 将每一场比赛的 Prediction 数据与对应的 Trade 数据进行 Join（匹配）。
- 将比赛划分为三个集合：
  - **Actionable (执行交易)**：`status == EXECUTED` 且 `recommended_stake > 0`。
  - **Ignored (放弃交易)**：`status == NO_BET` 或缺少关键数据的比赛。
  - **Failed (系统级失败)**：从日志中提取的、因为 API 超时或核心数据缺失被 Orchestrator 强制隔离/跳过的比赛。

### Step 2: 提取洞察与构建叙事 (Narrative Construction)
对于每一场 Actionable 的比赛，提取以下要素构建一段叙事：
1. **基本盘面**：主队 vs 客队，Trader 选择的方向和目标赔率。
2. **价值落差**：模型胜率与市场赔率隐含胜率的差距（这是下注的核心原因）。
3. **战术支撑**：提取 Analyst 在 JSON 中的 `reasoning_summary`，提炼出支持下注的战术原因（如：客队防守 xG 极差、主队核心伤停等）。
4. **资金指引**：明确说明 Trader 给出的具体仓位（占比及金额）。

### Step 3: 渲染 Markdown 报告 (Report Rendering)
严格按照以下模板生成报告内容。

**报告模板结构**：
```markdown
# 📊 Goalcast 赛事洞察报告
**生成时间**: [当前时间]
**分析场次**: [总分析数] 场 | **推荐交易**: [Actionable数] 场

---

## 🎯 核心交易指令 (Top Value Bets)
*系统发现并执行的具有正期望值（+EV）的投注指令。*

| 比赛 | 推荐方向 | 目标赔率 | 胜率偏差 | 建议仓位 | EV |
|---|---|---|---|---|---|
| A vs B | 客胜 | 3.50 | 模型35% vs 市场28% | 1.5% | +0.12 |
| C vs D | 主胜 | 1.95 | 模型55% vs 市场51% | 2.0% | +0.08 |

---

## 🔍 深度对局拆解 (Match Insights)

### ⚔️ [主队 A] vs [客队 B]
**交易方向**: 客胜 | **目标赔率**: 3.50 | **预期收益**: +0.12

**💡 价值洼地分析**
市场目前给予客队 3.50 的赔率，隐含胜率仅为 28%。但 GCQ 泊松模型计算得出客队实际胜率高达 35%，存在显著的价值空间。

**📈 战术与数据支撑**
[插入从 Analyst 的 reasoning_summary 中提取并润色的战术分析，解释为什么模型看好客队，例如伤停、近期进攻效率差异等。]

**⚠️ 资金与风险提示**
由于存在一定方差，Trader 建议采用 Quarter Kelly 策略，下注总资金的 1.5%。需注意：[提取缺失数据或潜在风险，如阵容尚未公布]。

---

## 🛑 放弃交易与诊断记录 (No Bet & Diagnostics)
*[此部分合并列出无价值的比赛，以及系统运行中遇到的断点与熔断记录]*

**1. 无价值放弃 (No Value)**
- E vs F：盘口极其精准，模型胜率与市场高度一致，未发现 EV 空间。

**2. 系统运行诊断 (System Health Check)**
- *基于 `orchestrator.log`，说明是否有比赛被跳过或触发降级。*
- [系统警告] 曼联 vs 狼队：API 响应超时，Orchestrator 触发单场错误隔离，已跳过该场分析。
- [路由降级] 未触发任何模型降级，全量采用 v4.0 + Sportmonks。
```

### Step 4: 输出与持久化
1. **直接输出**：将渲染好的 Markdown 报告作为最终对话响应，直接输出给用户。
2. **本地归档**：将报告以文本形式保存至 `team/data/reports/{target_date}_Insight_Report.md`，方便后续溯源或用于 Web 前端展示。
---
name: goalcast-compare
description: Use this skill when the user wants a Goalcast multi-method comparison, wants both v2.5 and v3.0 analyses, or asks which model is more suitable for a football match prediction.
---

# Goalcast Compare

版本：1.0 | 职责：多方法分析调度器

## 重要约束

**本 skill 不包含任何分析逻辑。** 所有分析由独立的 analyzer skill 完成。
本 skill 只负责：调度 sub-agent → 收集结果 → 生成对比报告。

## 触发条件

以下任意情况激活此 skill：
- 用户要分析比赛但**未指定**具体分析方法（默认对比 v2.5 + v3.0）
- 用户明确要求对比多个分析方法（"对比两种方法"、"两个版本都跑一下"）
- 用户问"哪个方法更准"、"v2.5 和 v3.0 有什么区别"

如果用户**明确指定**单一方法（"用 v2.5 分析"或"用 v3.0 分析"），则改为调用对应的单一 analyzer skill，不走本 skill。

## 执行步骤

### Step 1：解析用户意图

从用户输入中提取：
- **比赛信息**（必须）：主队名 / 客队名 / 联赛名 / 日期（默认今天）
- **对比方法**（可选，默认 v2.5 + v3.0）

如果比赛信息不足，主动询问用户：
- "请问是哪两支队伍？"
- "是今天的比赛吗？"

### Step 2：并行启动两个独立 sub-agent

**同时**（不要顺序执行）启动以下两个 sub-agent：

**Sub-agent A - v2.5 分析：**

任务描述：

```text
请使用 goalcast-analyzer-v25 skill 分析以下比赛：
- 比赛：[主队名] vs [客队名]
- 联赛：[联赛名]
- 日期：[YYYY-MM-DD]

请完整执行 skill 的所有步骤：
1. 定位比赛（FootyStats）
2. 采集数据（FootyStats + Understat 补充）
3. 零层检查
4. 五层分析
5. 输出 AnalysisResult JSON

注意：如果联赛在 Understat 支持范围内（EPL/La_liga/Bundesliga/Serie_A/Ligue_1），
请确保 Step 2.5 执行以获取 xG 数据。
```

**Sub-agent B - v3.0 分析：**

任务描述：

```text
请使用 goalcast-analyzer-v30 skill 分析以下比赛：
- 比赛：[主队名] vs [客队名]
- 联赛：[联赛名]
- 日期：[YYYY-MM-DD]

请完整执行 skill 的所有步骤：
1. 定位比赛（FootyStats）
2. 采集数据（FootyStats + Understat 补充）
3. 零层检查
4. 八层分析
5. 输出 AnalysisResult JSON

注意：如果联赛在 Understat 支持范围内（EPL/La_liga/Bundesliga/Serie_A/Ligue_1），
请确保 Step 2.5 执行以获取 xG 数据。
```

等待两个 sub-agent **均**完成后，继续下一步。

### Step 3：验证结果完整性

检查两份 `AnalysisResult` 是否包含必要字段：
- `method` 字段存在（分别应为 `"v2.5"` 和 `"v3.0"`）
- `probabilities` 包含 `home_win` / `draw` / `away_win`
- `decision` 包含 `ev` / `confidence` / `bet_rating`

如某份结果缺失或格式错误：
- 在报告中注明 `"[v2.5/v3.0] 分析执行失败"`
- 展示可用的那份结果
- 不要重试或估算缺失的数据

### Step 4：生成对比报告

输出以下格式（将真实数值填入）：

```markdown
## [主队] vs [客队] - 多方法分析对比
**日期**：YYYY-MM-DD | **联赛**：[联赛名] | **数据质量**：medium

---

### 结论对比

| 维度 | v2.5 | v3.0 | 差异 |
|------|------|------|------|
| 数据来源 | understat_direct / proxy | understat_direct / proxy | ✓一致 / ✗分歧 |
| 主队胜率 | X% | X% | ±X% |
| 平局概率 | X% | X% | ±X% |
| 客队胜率 | X% | X% | ±X% |
| 最佳投注 | [主胜/平/客胜/不推荐] | [主胜/平/客胜/不推荐] | ✓一致 / ✗分歧 |
| EV（风险调整后） | X.XX | X.XX | ±X.XX |
| 置信度 | XX | XX | ±XX |

### 主要分歧点

[分析两方法结论差异的原因。如无明显分歧，写"两个方法结论基本一致"。

常见分歧原因：
1. **数据来源差异**：如果一个方法使用 Understat xG，另一个使用 proxy，会导致基础实力评估不同
2. **v3.0 有更多降权项**（L3 降级、双重 EV 调整），导致置信度和 EV 系统性偏低
3. **分布模型差异**：v3.0 用 Dixon-Coles 修正低比分，可能与 v2.5 泊松分布在具体比分概率上有差异
4. **权重分配不同**：v2.5 基础实力 40%，v3.0 为 35%]

---

### v2.5 完整分析

[粘贴 Sub-agent A 返回的完整 AnalysisResult JSON]

---

### v3.0 完整分析

[粘贴 Sub-agent B 返回的完整 AnalysisResult JSON]
```

## 扩展：添加新分析方法

如需新增分析方法（如 v4.0）：
1. 新建 `skills/goalcast-analyzer-v40/SKILL.md`（独立 skill）
2. 在本 skill 的 Step 2 中增加对应 Sub-agent C
3. 在 Step 4 对比表中增加对应列
4. 本 skill 其他部分无需修改

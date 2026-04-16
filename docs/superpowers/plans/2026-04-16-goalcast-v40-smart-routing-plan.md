# Goalcast Analyzer v4.0 Smart Routing Implementation Plan

> **For agentic workers:** 按阶段执行，使用 checkbox (`- [ ]`) 跟踪完成状态。优先改写 `goalcast-analyzer-v40` 的单场分析规范，再做上层调度文档的最小同步，最后补齐验证与镜像同步。

**Goal:** 将 `goalcast-analyzer-v40` 从“缺失数据时被动降级的单一路径模型”改造成“时间优先自动分流的双路径模型”：满足条件时运行 `full_analysis`，否则运行 `early_market`，并在输出中明确报告模式与原因。

**Architecture:** 四个阶段：

- `P0` 固化边界与改动范围
- `P1` 重写 `goalcast-analyzer-v40` 的主流程与输出结构
- `P2` 同步 orchestrator / compare 的调用约定
- `P3` 验证、镜像同步与文档验收

**Primary Inputs:**

- 设计稿：[2026-04-16-goalcast-v40-smart-routing-design.md](file:///Users/zhengningdai/workspace/skyold/Goalcast/docs/superpowers/specs/2026-04-16-goalcast-v40-smart-routing-design.md)
- 主 skill：[SKILL.md](file:///Users/zhengningdai/workspace/skyold/Goalcast/skills/goalcast-analyzer-v40/SKILL.md)
- 编排入口：[SKILL.md](file:///Users/zhengningdai/workspace/skyold/Goalcast/skills/goalcast-analysis-orchestrator/SKILL.md)
- 对比入口：[SKILL.md](file:///Users/zhengningdai/workspace/skyold/Goalcast/skills/goalcast-compare/SKILL.md)
- 本地镜像：[SKILL.md](file:///Users/zhengningdai/workspace/skyold/Goalcast/.trae/skills/goalcast-analyzer-v40/SKILL.md)

**Tech Surface:** Skill 文档编排、MCP 工具调用约定、分析结果 schema、模式路由说明

---

## File Structure Map

**Primary modified files:**

```text
skills/goalcast-analyzer-v40/SKILL.md
skills/goalcast-analysis-orchestrator/SKILL.md
skills/goalcast-compare/SKILL.md
docs/superpowers/plans/2026-04-16-goalcast-v40-smart-routing-plan.md
```

**Sync target if runtime requires mirror update:**

```text
.trae/skills/goalcast-analyzer-v40/SKILL.md
```

**No code changes expected in this phase:**

```text
mcp_server/**
data_strategy/**
```

本次实施首先是 skill 层语义重构，不触碰 MCP 工具签名，也不改底层数据源实现。

---

## Phase P0: Boundary Lock

### Task 1: 固化本轮实施边界

**Files:**

- Read: `docs/superpowers/specs/2026-04-16-goalcast-v40-smart-routing-design.md`
- Read: `skills/goalcast-analyzer-v40/SKILL.md`
- Read: `skills/goalcast-analysis-orchestrator/SKILL.md`

- [ ] **Step 1: 明确主入口保持不变**

必须保持：

- skill 名称仍为 `goalcast-analyzer-v40`
- orchestrator 默认仍路由到 `v4.0 + sportmonks`
- 不新增独立 early skill
- 不改任何 MCP 工具的函数签名

- [ ] **Step 2: 固化“模式切换发生在 analyzer 内部”**

必须明确：

- orchestrator 只传递已有单场参数
- `goalcast-analyzer-v40` 在拉到单场数据后自行决定 `full_analysis` 或 `early_market`
- compare 不需要知道早盘细节，只需透明承接 analyzer 返回的新字段

- [ ] **Step 3: 固化“早盘不是降级”的语义**

在实施前先统一原则：

- `early_market` 是标准分析模式
- 早盘常缺的 `lineups`、`odds_movement`、`predictions` 不再默认写成惩罚项
- 置信度改为模式内评分，而不是完整版统一扣分

**Checkpoint:** 所有后续编辑都围绕“单入口 + 双模式 + 显式输出”进行，不再摇摆于“另起新 skill”或“继续统一降级”。

---

## Phase P1: Rewrite `goalcast-analyzer-v40`

### Task 2: 重写 skill 头部说明与核心约束

**Files:**

- Modify: `skills/goalcast-analyzer-v40/SKILL.md`
- Sync if needed: `.trae/skills/goalcast-analyzer-v40/SKILL.md`

- [ ] **Step 1: 更新版本摘要**

将头部描述从“固定九层完整模型”改成：

- 单入口 `v4.0`
- 内部分流 `full_analysis | early_market`
- Sportmonks 单数据入口
- 适配独立调用、orchestrator 调度、compare 调度

- [ ] **Step 2: 更新核心约束**

至少加入以下约束：

- 早盘模式不是降级模式
- 必须在输出中显式报告 `analysis_mode` 与 `mode_reason`
- 禁止在 `early_market` 中继续对预期缺失字段重复惩罚
- `full_analysis` 与 `early_market` 的置信度语义必须分离

- [ ] **Step 3: 清理旧语义残留**

重点移除或改写：

- “阵容缺失 -> 置信度 -10” 这种默认表述
- “赔率时序缺失 -> 固定降级” 这种完整版中心语义
- 重复的子 agent 静默规则

**Expected:** 文档开头就能准确表达“这不是旧 v4.0 的修补版，而是一个内建模式路由的 v4.0”。

---

### Task 3: 在 Step 2 后新增 `Mode Router`

**Files:**

- Modify: `skills/goalcast-analyzer-v40/SKILL.md`

- [ ] **Step 1: 在数据采集后新增模式路由步骤**

在现有 `Step 2` 之后、零层之前新增独立段落：

- 计算 `hours_to_kickoff`
- 判定 `full_analysis_eligible`
- 生成 `analysis_mode`
- 生成 `mode_trigger`
- 生成 `missing_for_full`
- 生成 `mode_switch_log`

- [ ] **Step 2: 固化时间优先规则**

必须写死：

- `hours_to_kickoff > 6` -> `early_market`
- `hours_to_kickoff <= 6` 时才允许检查完整分析资格

- [ ] **Step 3: 固化完整分析门槛**

必须明确：

- `xg` 可用
- `odds` 可用
- `lineups` 可用
- `odds_movement / predictions / asian_handicap` 至少一项可用

- [ ] **Step 4: 固化早盘触发条件**

必须明确进入 `early_market` 的原因枚举：

- `kickoff_gt_6h`
- `missing_xg`
- `missing_odds`
- `missing_lineups`
- `missing_all_enhancement_signals`
- `missing_kickoff_time`

**Expected:** `goalcast-analyzer-v40` 的主流程从“直接开始零层检查”变成“先决定当前处于什么分析模式，再执行对应层级策略”。

---

### Task 4: 以模式为中心重写零层与各层策略

**Files:**

- Modify: `skills/goalcast-analyzer-v40/SKILL.md`

- [ ] **Step 1: 重写零层检查表**

拆成两套语义：

- `full_analysis` 检查表：强调完整字段齐备
- `early_market` 检查表：强调哪些字段属于预期缺失

- [ ] **Step 2: 重写 `L3 / L6 / L7 / Layer AH` 的模式行为**

必须明确：

- `L3` 在 `early_market` 中只作为静态市场参考层
- `L6` 在 `early_market` 中默认关闭
- `L7` 在 `early_market` 中默认关闭
- `Layer AH` 在两种模式都可选，但缺失时只影响自身，不改变模式合法性

- [ ] **Step 3: 重写 `L8` 的决策语义**

必须区分：

- `full_analysis` 下 EV 与风险调整延续完整版表达
- `early_market` 下 EV 仍可计算，但要建立在“静态赔率可用”的条件上
- 赔率缺失时直接输出不可推荐，而不是假装完整运行

- [ ] **Step 4: 重写 `L9` 的置信度输入**

必须体现：

- `full_analysis` 维持高上限
- `early_market` 单独设置保守上限
- `lineups`、`odds_movement`、`predictions` 在早盘模式中不再作为固定扣分项

**Expected:** 文档层级从“同一套层级 + 缺失时跳过”升级为“按模式执行不同层策略”。

---

### Task 5: 扩展输出 schema

**Files:**

- Modify: `skills/goalcast-analyzer-v40/SKILL.md`

- [ ] **Step 1: 新增 `analysis_context` 块**

至少包含：

- `analysis_mode`
- `mode_trigger`
- `hours_to_kickoff`
- `full_analysis_eligible`
- `missing_for_full`
- `user_notice`
- `mode_switch_log`

- [ ] **Step 2: 更新 `reasoning_summary` 强制要求**

必须规定：

- 第一段先说明当前模式
- `early_market` 必须明确告知用户：当前使用早盘分析
- `full_analysis` 必须明确告知用户：当前使用完整分析

- [ ] **Step 3: 更新输出前自检清单**

新增检查项：

- `analysis_context.analysis_mode` 存在
- `analysis_context.user_notice` 在早盘模式下必填
- `missing_for_full` 与 `mode_trigger` 一致
- 早盘模式下不得出现“lineups 缺失 -> 固定扣分”之类旧语义

**Expected:** 用户从结果第一屏就能看出“这场是早盘分析还是完整分析，以及为什么”。

---

## Phase P2: Upstream Skill Sync

### Task 6: 最小同步 orchestrator

**Files:**

- Modify: `skills/goalcast-analysis-orchestrator/SKILL.md`

- [ ] **Step 1: 保持默认路由不变**

继续保持：

- 默认 `v4.0 + sportmonks`
- 调度目标仍是 `goalcast-analyzer-v40`

- [ ] **Step 2: 删除对 analyzer 内部模式的错误假设**

补充说明：

- orchestrator 不负责判断早盘或完整模式
- 只需传入 `kickoff_time`、`match_date`、`match_type` 等标准参数
- 模式切换完全在 analyzer 内进行

- [ ] **Step 3: 更新汇总输出约定**

建议在编排层汇总表中允许读取并展示：

- `analysis_context.analysis_mode`
- `analysis_context.user_notice` 的简化摘要

**Expected:** 上层入口知道 v4.0 现在是双路径模型，但不复制 analyzer 的判断逻辑。

---

### Task 7: 最小同步 compare

**Files:**

- Modify: `skills/goalcast-compare/SKILL.md`

- [ ] **Step 1: 更新统一结果口径**

在 compare 的统一提取字段中新增：

- `analysis_context.analysis_mode`
- `analysis_context.mode_trigger`

- [ ] **Step 2: 更新差异解释逻辑**

必须允许 compare 在摘要里说明：

- 同为 `v4.0` 的场次也可能因为时间/数据条件进入 `early_market`
- 模式差异会影响 EV 与 confidence 的可比性

- [ ] **Step 3: 明确 compare 不重判模式**

写清楚：

- compare 只读取 analyzer 结果
- 不自行推断某场是否“本该是早盘”

**Expected:** compare 对 v4.0 新输出结构兼容，但仍保持单场多组合执行边界。

---

## Phase P3: Validation And Sync

### Task 8: 文档回归检查

**Files:**

- Modify/Read: `skills/goalcast-analyzer-v40/SKILL.md`
- Modify/Read: `skills/goalcast-analysis-orchestrator/SKILL.md`
- Modify/Read: `skills/goalcast-compare/SKILL.md`

- [ ] **Step 1: 检查术语一致性**

确保所有文档统一使用：

- `full_analysis`
- `early_market`
- `analysis_context`
- `mode_trigger`
- `missing_for_full`

- [ ] **Step 2: 检查旧表述是否清理干净**

重点搜索并消除：

- “阵容缺失固定扣 10 分”
- “市场固定降级”
- “仅完整九层模型” 等旧中心化表述

- [ ] **Step 3: 检查 schema 一致性**

确认：

- analyzer 定义的新输出字段能被 orchestrator / compare 理解
- compare 的字段抽取不与新 schema 冲突

**Expected:** 三份 skill 文档在同一套模式语义下自洽。

---

### Task 9: 镜像同步与运行面确认

**Files:**

- Sync if needed: `.trae/skills/goalcast-analyzer-v40/SKILL.md`

- [ ] **Step 1: 确认运行时是否读取仓库内 skill**

若运行时直接读取 `skills/`：

- 仅维护仓库内主文件

若运行时依赖 `.trae/skills/` 镜像：

- 同步更新 `.trae/skills/goalcast-analyzer-v40/SKILL.md`

- [ ] **Step 2: 保持镜像内容一致**

若需要同步，必须保证：

- 标题一致
- 模式路由一致
- 输出 schema 一致

**Expected:** 实际调用面不会因为主文件与镜像不一致而出现旧行为。

---

### Task 10: 手工验收场景

- [ ] **Scenario A: 早盘标准命中**

输入条件：

- `hours_to_kickoff > 6`
- `xg` / `odds` 可用
- `lineups` 缺失

预期：

- 进入 `early_market`
- 明确输出早盘提示
- 不把 `lineups` 缺失当成异常扣分

- [ ] **Scenario B: 近开赛完整命中**

输入条件：

- `hours_to_kickoff <= 6`
- `xg` / `odds` / `lineups` 可用
- 至少一个增强信号可用

预期：

- 进入 `full_analysis`
- 输出完整模式提示

- [ ] **Scenario C: 近开赛但仍缺临场字段**

输入条件：

- `hours_to_kickoff <= 6`
- `lineups` 缺失，或增强信号全部缺失

预期：

- 仍进入 `early_market`
- `mode_reason` 明确指出原因

- [ ] **Scenario D: 开赛时间缺失**

输入条件：

- `kickoff_time` 缺失或不可解析

预期：

- 进入 `early_market`
- `mode_trigger=missing_kickoff_time` 或等价原因

- [ ] **Scenario E: compare 读取新字段**

预期：

- compare 能稳定读取 `analysis_context`
- 不因新增字段破坏原有对比报告

---

## Suggested Commit Boundaries

建议按以下粒度提交，便于回滚和审阅：

1. `docs(goalcast): add v4.0 smart routing implementation plan`
2. `docs(goalcast): rewrite v4.0 analyzer for smart routing and early-market mode`
3. `docs(goalcast): sync orchestrator and compare with v4.0 smart routing`
4. `docs(goalcast): sync .trae mirror for v4.0 analyzer`

---

## Exit Criteria

当以下条件全部满足时，视为本轮实施完成：

- `goalcast-analyzer-v40` 已明确采用单入口双模式设计
- `Mode Router` 已写入 skill 主流程
- `early_market` 已被定义为标准模式而非降级路径
- 输出已包含 `analysis_context`
- orchestrator 已接受 analyzer 内部模式路由，不重复判断
- compare 已兼容读取 `analysis_context`
- 若运行面需要 `.trae` 镜像，镜像已完成同步
- 手工验收场景可覆盖早盘、完整、缺时间、compare 兼容四类情况

---

## Implementation Notes

- 不要把 `early_market` 实现成第二个 skill 名称
- 不要让 orchestrator 复制 analyzer 的模式判定逻辑
- 不要保留“lineups 缺失固定扣分”这类旧规则作为默认表达
- 不要在 `early_market` 中继续声称自己在运行完整版，只是跳过部分层
- 若编辑中发现 `.trae` 镜像是当前实际运行源，则把镜像同步视为同一变更的一部分
- 如果 compare 的结果抽取对新增字段过于严格，可先扩展为可选字段，再逐步提升为标准字段

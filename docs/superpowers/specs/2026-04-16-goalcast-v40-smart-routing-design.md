# Goalcast Analyzer v4.0 Smart Routing Design

## Summary

`goalcast-analyzer-v40` 保持单一 skill 入口不变，在内部新增智能分流能力：

- 满足完整分析条件时运行 `full_analysis`
- 不满足完整分析条件时运行 `early_market`
- `early_market` 不是置信度降级后的残缺版，而是面向早盘场景的标准分析路径
- 输出中必须显式告知当前模式、触发原因、未满足完整分析的字段

本设计用于修正现有 v4.0 对赛前常缺失字段的处理方式。此前 `lineups`、`odds_movement`、`predictions`、部分 `asian_handicap` 在早盘时段常年缺失，但仍被作为完整模型中的正式层输入，导致模型语义与实际使用场景错位。

## Goals

- 保持 `goalcast-analyzer-v40` 对外入口与调用方式不变
- 让模型自动根据开赛时间和数据状态选择合适的分析模式
- 将“早盘分析”定义为标准模式，而不是统一扣分后的降级执行
- 在结果中明确告知用户当前使用了哪种模式以及原因
- 让回测、复盘和后续路由逻辑能稳定识别每场比赛实际使用的分析路径

## Non-Goals

- 不新增独立 early skill
- 不修改 MCP 工具对外签名
- 不在本设计中扩展新的外部数据源
- 不改变现有 orchestrator 的基础入口形式

## Problem Statement

现有 v4.0 文档虽然已经描述了缺失数据时的跳过与扣分规则，但整体仍默认“完整九层分析”是标准形态。这在实际早盘使用中会产生三个问题：

1. 早盘常缺字段被当作异常处理，而不是被当作早盘场景的正常输入条件。
2. 同样名为 v4.0 的输出，有时来自接近完整的临场分析，有时来自大量字段缺失后的降级路径，语义不清晰。
3. 结果中通常只能看到若干层被跳过，却不能直接看出“这场本质上采用的是早盘分析”。

## Design Overview

在 `goalcast-analyzer-v40` 内新增一个 `Mode Router`。它位于 `Step 2` 数据采集完成之后、正式进入零层和后续计算之前。

`Mode Router` 负责：

- 计算 `hours_to_kickoff`
- 先按时间窗口判断是否具备尝试完整分析的资格
- 在时间允许时进一步检查完整分析关键字段
- 最终选定 `analysis_mode`
- 生成对用户可见的模式说明和对系统可追踪的切换记录

系统只输出两种模式：

- `full_analysis`
- `early_market`

## Routing Rules

### Primary Rule

时间优先作为第一判定规则。

- 当 `hours_to_kickoff > 6` 时，直接进入 `early_market`
- 当 `hours_to_kickoff <= 6` 时，才允许尝试 `full_analysis`

### Full Analysis Eligibility

只有在 `hours_to_kickoff <= 6` 且以下条件同时满足时，才进入 `full_analysis`：

- `xg` 可用
- `odds` 可用
- `lineups` 可用
- 以下增强信号至少一项可用：
  - `odds_movement`
  - `predictions`
  - `asian_handicap`

### Early Market Triggers

任一条件满足即进入 `early_market`：

- `hours_to_kickoff > 6`
- `xg` 缺失
- `odds` 缺失
- `lineups` 缺失
- `odds_movement`、`predictions`、`asian_handicap` 全部缺失

这里的关键语义是：进入 `early_market` 不代表模型退化或异常，而代表当前比赛更符合早盘分析上下文。

## Mode Semantics

### `full_analysis` Confidence

`full_analysis` 代表系统已经获得足以支撑临场增强层的关键信息。该模式允许使用完整模型中的主要增强层，并维持较高的置信度上限。

### `early_market` Confidence

`early_market` 代表比赛仍处于早盘阶段，或虽接近开赛但关键临场字段不足。该模式以稳定可得的数据为核心，不把 `lineups`、`odds_movement`、`predictions` 缺失视为异常扣分项。

## Layer Behavior By Mode

### Common Layers

以下层在两种模式中都保留：

- 零层强制检查
- 第一层基础实力模型
- 第二层情境调整模型
- 第五层分布模型
- 第八层 EV 决策
- 第九层置信度校准

### `full_analysis` Layer Policy

- `L0`：按完整检查表执行
- `L1`：正常执行
- `L2`：正常执行
- `L3`：允许使用静态赔率与赔率时序
- `L4`：继续保持关闭
- `L5`：正常执行
- `L6`：若 `lineups` 可用则启用
- `L7`：若 `predictions` 可用则启用
- `Layer AH`：若 `asian_handicap` 可用则启用
- `L8`：正常执行
- `L9`：按照完整模式置信度规则计算

### `early_market` Layer Policy

- `L0`：改写为早盘检查表，明确哪些字段属于预期缺失
- `L1`：作为主引擎保留
- `L2`：仅允许使用稳定可得字段，如积分榜、赛季阶段、比赛类型
- `L3`：弱化为静态市场参考层；若无 `odds_movement`，只输出静态市场概率，不输出强市场行为结论
- `L4`：关闭
- `L5`：保留，作为概率生成核心
- `L6`：默认关闭；`lineups` 缺失不视为惩罚项
- `L7`：默认关闭；`predictions` 缺失不视为惩罚项
- `Layer AH`：有则计算，无则输出 `unavailable`
- `L8`：若静态赔率可用则执行；若赔率不可用，则 EV 相关结果输出为不可推荐
- `L9`：按照早盘模式置信度规则计算

## Data Classification

为避免“字段缺失即统一扣分”的旧逻辑继续污染模型语义，本设计将字段分成三类：

### Core Fields

这些字段直接决定是否具备可分析性：

- `xg`
- `odds`

### Full-Mode Gate Fields

这些字段不决定比赛能否分析，但决定是否允许进入完整分析：

- `lineups`
- `odds_movement`
- `predictions`
- `asian_handicap`

其中 `lineups` 为必需，后面三项至少一项可用。

### Optional Informational Fields

这些字段可增强解释，但不单独决定模式：

- `h2h`
- standings 细项之外的其他补充说明项

## Confidence Model

### Core Principle

置信度必须改为“模式内评分”，而不是继续用完整模式标准惩罚早盘模式。

### `full_analysis`

- 保持较高置信度上限，建议延续 `90` 上限
- 重点衡量完整数据一致性、市场确认度、模型分歧和临场信息完备度

### `early_market`

- 设置更保守的上限，建议上限 `75` 到 `78`
- 不因 `lineups`、`odds_movement`、`predictions` 缺失而机械扣分
- 重点衡量：
  - `xg.source` 是否可靠
  - `overall_quality` 是否达到可用水平
  - `odds` 是否存在且合理
  - standings 是否可用
  - 模型概率与静态市场概率是否严重冲突
  - 比赛类型是否存在额外不确定性

## Output Changes

输出结果中新增 `analysis_context` 块，用于显式向用户和系统说明本场分析模式。

建议结构如下：

```json
"analysis_context": {
  "analysis_mode": "full_analysis | early_market",
  "mode_trigger": "time_window | missing_required_fields | hybrid",
  "hours_to_kickoff": 18.5,
  "full_analysis_eligible": false,
  "missing_for_full": ["lineups", "odds_movement", "predictions"],
  "user_notice": "当前使用早盘分析：距离开赛超过6小时，且临场增强字段未齐备。",
  "mode_switch_log": [
    "kickoff_gt_6h -> early_market"
  ]
}
```

### Output Requirements

- `reasoning_summary` 第一段必须说明当前模式
- 当模式为 `early_market` 时，必须包含固定语义：
  - 当前使用早盘分析，不将阵容、赔率时序、官方预测缺失视为异常降级项
- 当模式为 `full_analysis` 时，必须包含固定语义：
  - 当前使用完整分析，临场增强字段已满足完整模式要求

## Mode Routing Flow

建议流程如下：

1. 通过 `goalcast_sportmonks_get_match` 获取比赛上下文
2. 计算 `hours_to_kickoff`
3. 若 `hours_to_kickoff > 6`，直接设置 `analysis_mode=early_market`
4. 若 `hours_to_kickoff <= 6`，检查完整分析关键字段
5. 若关键字段齐全，设置 `analysis_mode=full_analysis`
6. 若关键字段不齐，设置 `analysis_mode=early_market`
7. 记录 `mode_trigger`、`missing_for_full`、`mode_switch_log`
8. 将模式信息传递给后续层级执行与输出模块

## Error Handling

- 若 `kickoff_time` 缺失或无法解析，默认进入 `early_market`，并记录原因 `missing_kickoff_time`
- 若 `xg` 与 `odds` 同时缺失，仍输出分析结果，但必须将 `user_notice` 明确为“信息不足，仅提供极低可信度方向参考”或等价语义
- 若 `lineups` 缺失但其他条件满足，在 `hours_to_kickoff <= 6` 的情况下仍不得进入 `full_analysis`
- 若 `asian_handicap` 缺失，不影响模式合法性，只影响 `Layer AH`

## Testing Strategy

建议至少覆盖以下场景：

1. `hours_to_kickoff > 6` 且字段基本齐全，必须进入 `early_market`
2. `hours_to_kickoff <= 6` 且 `xg + odds + lineups + 增强信号` 齐全，必须进入 `full_analysis`
3. `hours_to_kickoff <= 6` 但 `lineups` 缺失，必须进入 `early_market`
4. `hours_to_kickoff <= 6` 且 `lineups` 可用，但 `odds_movement + predictions + asian_handicap` 全缺，必须进入 `early_market`
5. `kickoff_time` 解析失败，必须进入 `early_market`
6. `early_market` 模式输出必须包含 `analysis_context.user_notice`
7. `early_market` 模式置信度不得因 `lineups`、`odds_movement`、`predictions` 的预期缺失重复惩罚

## Migration Notes

- 该设计保持 skill 名称和对外入口不变
- 现有依赖 `goalcast-analyzer-v40` 的调度链无需切换 skill 名称
- 文档与输出 schema 需要更新，以承载 `analysis_context`
- 置信度计算 MCP 调用参数需要增加模式语义，避免旧逻辑继续将早盘缺失视为统一扣分项

## Risks

- 若时间窗口设置过于绝对，可能导致接近开赛但已拿到完整字段的比赛仍被强制归入 `early_market`
- 若后续数据源质量波动较大，`hours_to_kickoff <= 6` 场景下仍可能频繁进入 `early_market`
- 若输出文案未强制统一，用户仍可能忽视模式切换信息

## Recommendation

采用本设计后，`goalcast-analyzer-v40` 将从“缺失时被动降级”的单一模型，改为“时间优先、数据补充判断、结果显式告知”的双路径模型。这样既保留单入口，又让早盘分析成为一条语义清晰、适合回测与复盘的正式路径。

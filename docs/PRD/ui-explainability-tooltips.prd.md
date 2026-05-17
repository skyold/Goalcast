# UI 元素可解释性：全站悬停提示与信息图标

## Problem Statement

Goalcast 前端每张卡片塞满了密度极高的数据点（PredictabilityBadge 的"高/中/低"、`排名 #3 · 进 7 失 5`、FormStrip 的 D/L/W 字母方块、ProbBar 的 54%/23%/24%、`▼60%` 跌赔标签、Dashboard 的"候选比赛 1713 +3"等），但**没有任何悬停说明或信息入口**。用户必须自行推测每个图例的含义，新用户首次访问时无法区分"概率条 vs 赔率"、"近 5 场战绩 vs 当前排名"等关键概念——这直接削弱了产品作为决策辅助工具的说服力。

## Evidence

- **直接观察**：`MatchCard.tsx` 通篇没有 `title=` 或 tooltip 组件；`PredictabilityBadge.tsx:10` 仅有英文残留 `title="predictability: ${level}"`（中文界面下基本是噪音）。
- **用户反馈**（本会话）："卡片中有大量数据但鼠标滑上去没有显示文字的说明，所以这些图例都不知道是什么"。
- **代码佐证**：全仓库 `title=` 仅 3 处使用，且仅 `ScorelineHeatmap` 一处真正有用；其他高密度组件（FormStrip、ProbBar、KPI、drop-tag）零覆盖。
- **假设（需验证）**：除内部用户外，新增的潜在用户群体（赛前研究的足球爱好者）也会被密度劝退——尚无外部用户访谈数据。

## Proposed Solution

引入**统一的轻量 Tooltip 原语**（基于无依赖的 React Portal + CSS，或单一引入 `@radix-ui/react-tooltip`），按"信息密度优先级"分两个层次铺设：

1. **数据图例自带 tooltip**：FormStrip 字母、ProbBar 段、odds 槽位、PredictabilityBadge、drop-tag 等"图标即数据"的元素，hover 即弹出**字段名 + 计算口径 + 单位**的短说明。
2. **卡片级信息图标 (i)**：每个 KPI、Dashboard 板块、MatchCard 头部放一个 14px 的 ⓘ 图标，hover 弹出**整张卡片的语义说明**（解释这张卡片在回答什么问题、数据来源、刷新频率）。

文案集中管理在 `frontend/src/lib/glossary.ts`，避免散落硬编码；后期可演化为 i18n 资源。

## Key Hypothesis

我们相信**为每个数据点和卡片增加分层 tooltip + ⓘ 入口**会**显著降低新用户的"这玩意是什么"摩擦**，对于**所有访问 Goalcast 前端的用户**。
我们将通过以下指标验证：

- 新用户在 MatchCard / Dashboard 上的**平均首页停留时间增加** ≥ 30%（假设当前有可埋点的会话遥测——**TBD：当前未发现埋点 SDK**）；
- 内部 dogfood 反馈中"我不知道这是什么"类问题在两周内**清零**；
- **可见即可解释覆盖率**：MatchCard 与 Dashboard 上**100% 的非自解释数据点**（排除纯文本如球队名、时间）都有 tooltip。

## What We're NOT Building

- **不**做完整 i18n 框架——文案只先抽中文常量，留 key 形式以备未来。原因：当前仅中文用户。
- **不**做点击展开的"详细解释抽屉"——纯 hover/聚焦即可，避免增加交互步骤。
- **不**做移动端长按 tooltip 的复杂适配——v1 仅保证桌面端 hover + 键盘聚焦可达；移动端用 `:active` 退化或不显示。
- **不**重写卡片视觉布局——只追加 tooltip 触发层，不动既有 `mc-*` / `kpi-*` 类名结构。
- **不**引入重型 UI 库（Mantine / MUI）——单引入 Radix Tooltip 或自研，控制体积。

## Success Metrics

| Metric | Target | How Measured |
|--------|--------|--------------|
| 数据点 tooltip 覆盖率 | 100%（MatchCard + Dashboard 内非纯文本元素） | 人工 checklist + Playwright 断言：枚举每个目标元素并断言含 `aria-describedby` 或自定义 tooltip 触发器 |
| 卡片级 ⓘ 入口覆盖率 | 100% Dashboard 卡片 + MatchCard 头部 | 同上 checklist |
| 键盘可达性 | tooltip 在 `Tab` 聚焦时显示，`Esc` 关闭 | 手动 + axe-core 自动化（**TBD：项目当前未跑 axe**） |
| 文案中心化 | `glossary.ts` 单一来源，0 处硬编码英文 | grep 检查 `title="[a-z]"` 英文残留为 0 |
| 包体增量 | gzipped JS 增量 < 6 KB | 对比 `vite build` 输出 |

## Open Questions

- [ ] 是否引入 `@radix-ui/react-tooltip`（~3 KB gz、a11y 完备）还是手写一个 ~80 行的 Portal 实现？**默认推荐 Radix**，理由：键盘 + 焦点环 + ARIA 自动正确。
- [ ] 移动端 hover 不存在时降级策略——v1 不显示？还是点击 ⓘ 切换？
- [ ] tooltip 文案是否需要 markdown 加粗 / 换行？影响实现复杂度。
- [ ] 是否埋点统计 tooltip 打开次数？需先确认是否有遥测通道（当前看不到）。
- [ ] PredictabilityBadge "高/中/低/一般" 的官方业务定义在哪？需要从 `backend/services/` 找出阈值并写入文案。

---

## Users & Context

**Primary User**
- **Who**: 来 Goalcast 看赛前数据辅助判断的足球爱好者（也包括内部 dogfood 的 PM/工程师）。
- **Current behavior**: 打开 `/matches` 或 `/`，扫一眼卡片，对密集数字困惑，往往关掉或猜测含义。
- **Trigger**: 第一次见到 FormStrip 的 `D L W W W` 或 ProbBar 的颜色段；或者向同事介绍产品时被问"这是啥"。
- **Success state**: hover 任意元素 0.3 秒内出现 1-2 行中文解释；点 ⓘ 0.3 秒内出现该卡片整体说明，用户立即理解每列数字的含义。

**Job to Be Done**
当**我看到一个不熟悉的足球数据图例**时，我想要**鼠标悬停就知道它的含义和计算口径**，这样我就可以**专注做投注/观赛判断，而不是回头查文档或猜**。

**Non-Users**
- 重度专业用户（自己写策略的）——他们直接看 API，不需要 UI 解释。
- 真正的移动端用户群（如果有）——v1 不优化触屏，移动需求后续单独立项。

---

## Solution Detail

### Core Capabilities (MoSCoW)

| Priority | Capability | Rationale |
|----------|------------|-----------|
| Must | 通用 `<Tooltip>` 组件（hover + focus 触发、Portal 渲染、键盘 Esc 关闭、ARIA 正确） | 一切覆盖的基础设施 |
| Must | `glossary.ts` 中文文案中心 | 防止文案散落；后续 i18n 切换零成本 |
| Must | MatchCard 所有数据元素覆盖 tooltip：PredictabilityBadge、排名、进/失球、FormStrip、ProbBar、odds、drop-tag | 用户提出的核心痛点 |
| Must | Dashboard 4 个 KPI + 4 个面板卡片增加 ⓘ 信息图标 | 用户在 Dashboard 同样困惑（候选比赛=?） |
| Should | MatchCard 头部一个 ⓘ 解释整张卡片的阅读顺序 | 提高首次使用引导价值 |
| Should | 详情页 `MatchDetail.tsx`、`DroppingOdds.tsx`、`ValueBets.tsx`、`History.tsx` 上的同类元素复用 | 全站一致体验 |
| Could | tooltip 内嵌一条"了解更多"链接跳到说明页 | 锦上添花 |
| Won't (v1) | 移动端长按弹层 | 见 What We're NOT Building |
| Won't (v1) | i18n 多语言 | 中文优先 |

### MVP Scope

**MVP = Must 的 4 项**。即：Tooltip 原语 + glossary + MatchCard 全覆盖 + Dashboard ⓘ。
能够在 1 个工程师 ~1.5 天内交付，立即解决用户描述的两张截图问题，并把模式定型供后续页面复用。

### User Flow

1. 用户访问 `/`（Dashboard）→ 看到 "候选比赛 1713 +3 自昨日"
2. 鼠标移到标题右侧 ⓘ 图标 → 200ms 后弹出："候选比赛：未来 7 天内所有联赛的可分析比赛数。+N 表示相对昨日的增量。"
3. 用户继续到 "即将开赛" 板块 → hover 一张 MatchCard 的 `▼60%` 标签 → 弹出："Pinnacle 24h 内最大跌赔幅度，≥50% 视为强信号。"
4. 用户 Tab 键依次聚焦，每个 tooltip 同样弹出（键盘可达）。

---

## Technical Approach

**Feasibility**: HIGH

**Architecture Notes**

- 单一 `frontend/src/components/shared/Tooltip.tsx`，签名：
  ```tsx
  <Tooltip content="..."><span>...</span></Tooltip>
  ```
  内部用 `@radix-ui/react-tooltip` 的 `Root/Trigger/Portal/Content`；样式用 Tailwind + 已有 `--bg`/`--fg` CSS 变量与现有暗色主题对齐。
- 信息图标 `frontend/src/components/shared/InfoIcon.tsx`：`<InfoIcon glossaryKey="dashboard.candidates" />`，内部读 `glossary.ts` 渲染 Tooltip。
- 文案中心 `frontend/src/lib/glossary.ts`：
  ```ts
  export const glossary = {
    'mc.predictability.high': '可预测度：高。由近 5 场战绩稳定性 + 赔率隐含概率收敛度共同决定。',
    'mc.form5': '近 5 场战绩。W=胜 D=平 L=负，最左为最近一场。',
    'mc.probbar': '模型预测概率：主胜 / 平局 / 客胜。',
    'mc.odds.ft': 'Pinnacle 全场赔率（十进制）。',
    'mc.drop': '24h 内 Pinnacle 主胜赔率最大跌幅；红色=≥60%（强信号）。',
    'dash.candidates': '候选比赛：未来 7 天内所有联赛的可分析比赛数。+N=较昨日。',
    // ...
  } as const
  ```
- 集成点：
  - `MatchCard.tsx:39` PredictabilityBadge → 包一层 Tooltip
  - `MatchCard.tsx:54-59, 74-79` 排名+进失球 → Tooltip
  - `FormStrip.tsx`（整体）→ Tooltip
  - `ProbBar.tsx`（整体或每段）→ Tooltip
  - `MatchCard.tsx:88-99` odds-box → 每槽 Tooltip 或整组一个
  - `MatchCard.tsx:104` drop-tag → Tooltip
  - `Dashboard.tsx:61-64` Kpi 内插入 InfoIcon
  - `Dashboard.tsx:70, 91, 105, 125` 各 card-hdr 内插入 InfoIcon

**Technical Risks**

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| 引入 Radix 增大包体 | L | `@radix-ui/react-tooltip` ~3 KB gz；可接受 |
| Tooltip 与 z-index 冲突遮挡 Sidebar | M | Radix 默认 Portal 到 body，z-index 设为 50+ |
| 移动端 hover 不触发，用户困惑 | M | v1 ⓘ 点击也展开（Radix 默认支持）；非 ⓘ 元素 v1 不优化 |
| 文案过长破坏卡片视觉 | L | tooltip 强制 `max-width: 280px`、`word-break: break-word` |
| 既有 `title=` 残留与新 tooltip 双弹 | M | 用 grep 清理三处 `title=` 旧引用 |

---

## Implementation Phases

| # | Phase | Description | Status | Parallel | Depends | PRP Plan |
|---|-------|-------------|--------|----------|---------|----------|
| 1 | Tooltip 原语 + InfoIcon + glossary 骨架 | 新增 3 个文件，含 Radix 集成、键盘可达、Tailwind 主题对齐；首个示例点接入 | pending | - | - | - |
| 2 | 撰写 glossary 全量文案 | 收集业务定义（含从 backend 找 predictability 阈值），中文化所有 key | pending | with 3 | 1 | - |
| 3 | MatchCard 全量接入 | 7 个数据点（badge / 排名 / form / probbar / odds×3 / drop） | pending | with 2 | 1 | - |
| 4 | Dashboard KPI + 卡片 ⓘ 接入 | 4 KPI + 4 卡片头部 | pending | - | 1 | - |
| 5 | 其他页面复用（MatchDetail / DroppingOdds / ValueBets / History） | 把同类元素全部覆盖到 | pending | - | 3, 4 | - |
| 6 | 验收：Playwright 截图回归 + a11y 检查 + 旧 `title=` 清理 | 自动断言 + 视觉回归；移除 PredictabilityBadge 英文残留 | pending | - | 5 | - |

### Phase Details

**Phase 1: Tooltip 原语**
- Goal: 建立全站统一的 Tooltip + InfoIcon，可被任何组件 1 行调用
- Scope: `Tooltip.tsx`、`InfoIcon.tsx`、`glossary.ts` 骨架；安装 `@radix-ui/react-tooltip`；在 `PredictabilityBadge` 替换英文 `title=` 作为示例
- Success signal: 浏览器 hover Badge 出现中文 tooltip；Tab 可聚焦；构建无 type 错误

**Phase 2: 文案全量**
- Goal: 所有目标元素都有中文说明文案
- Scope: 填满 `glossary.ts`；统一称呼（"主胜/客胜"、"近 5 场"等）；从 `backend/services/predictability.py`（或对应文件）取阈值定义
- Success signal: glossary 至少 15 条；所有 key 在 Phase 3-4 都有真实引用

**Phase 3: MatchCard 全量**
- Goal: 用户截图 #2 中所有元素 hover 可解释
- Scope: 修改 `MatchCard.tsx` / `FormStrip.tsx` / `ProbBar.tsx`
- Success signal: 浏览器手测 7 个数据点全部弹出 tooltip

**Phase 4: Dashboard ⓘ**
- Goal: 用户截图 #3 "候选比赛" 旁出现可点 ⓘ
- Scope: `Dashboard.tsx` Kpi 与各 card 增加 ⓘ
- Success signal: 4 KPI + 4 卡片头部都有 ⓘ，hover/click 显示

**Phase 5: 其他页面**
- Goal: 一致性
- Scope: MatchDetail / DroppingOdds / ValueBets / History
- Success signal: 同类元素零硬编码 title，全用 InfoIcon/Tooltip

**Phase 6: 验收**
- Goal: 不回归 + 可持续
- Scope: Playwright 用例 + axe 检查（如尚未集成则手动 + 文档化）
- Success signal: CI 通过；grep `title="[a-z ]+"` 仅保留 ScorelineHeatmap 数据用的 title

### Parallelism Notes

- Phase 2 (文案) 和 Phase 3 (MatchCard 接线) 可并行：先用占位 key 接线，文案随写随填。
- Phase 4 与 Phase 3 也可并行：Dashboard 与 MatchCard 修改的文件不重叠。
- Phase 5、6 必须最后。

---

## Decisions Log

| Decision | Choice | Alternatives | Rationale |
|----------|--------|--------------|-----------|
| Tooltip 实现 | `@radix-ui/react-tooltip` | 自研 Portal / 原生 `title` / Floating UI 直接调用 | a11y 与键盘行为开箱即用；体积可控；社区成熟 |
| 文案管理 | 单文件常量 `glossary.ts` | 散落硬编码 / 直接接 i18n 库 | v1 仅中文；常量足够；key 形式留 i18n 升级路径 |
| 触发模式 | hover + focus + ⓘ click | 仅 hover / 仅 click | hover 满足桌面；focus 满足键盘；ⓘ click 满足移动 |
| 卡片整体说明位置 | 头部右侧 ⓘ 图标 | 卡片左上角 / 卡片外侧 | 头部最自然，与 `card-hdr` 已有右侧 `card-sub` 区域对齐 |

---

## Research Summary

**Market Context** (轻量调研，需要时可深入)
- 同类数据密集型产品（Sofascore、Whoscored、Flashscore 桌面端）普遍使用 hover tooltip + ⓘ 图标双层模式；ⓘ 通常解释整张表格，hover 解释单列。
- 设计模式参考：Bloomberg Terminal、Stripe Dashboard 都以"高密度 + tooltip 即时解释"为常态。

**Technical Context**
- 现状仓库：React 18 + Vite 5 + Tailwind 3，**无任何 UI 组件库**；新增 Radix 单包 ~3 KB gz；零现有 tooltip 抽象，零迁移成本。
- 现有英文残留：`frontend/src/components/shared/PredictabilityBadge.tsx:10` 含 `title="predictability: ${level}"`——需在 Phase 1 清理。
- 现有 `title=` 仅 3 处（PredictabilityBadge、TweaksPanel、ScorelineHeatmap），ScorelineHeatmap 用于 data label（保留）。

---

*Generated: 2026-05-17*
*Status: DRAFT - needs validation*

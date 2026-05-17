# 中文本地化覆盖率与一致性

## Problem Statement

中文用户在使用 Goalcast 前端时，看到的是"中英文混杂"界面：联赛筛选 chip、卡片标题、详情页随机出现英文原名（"Serie A"/"Palmeiras"），破坏阅读流畅度并降低专业感。已存在 zh 字段链路（DB → API → 前端 fallback），但在三个关键渲染点（详情页主标题、Matches 联赛分组标题、Dashboard 提醒卡）未接通；同时 zh 种子库覆盖窄（31 联赛 / 132 球队），长尾联赛全英文。

## Evidence

- 用户截图（Image #4）：联赛分组标题渲染为 `Serie A`（英文），同一区块下的卡片渲染为 `巴甲`（中文）—— 同一屏内自相矛盾。
- `frontend/src/pages/MatchDetail.tsx:45,47,61,63,81,88` —— 详情页 6 处直接使用 `f.home_team` / `f.away_team` / `f.competition_name`，未使用 `_zh` 字段。
- `frontend/src/pages/Matches.tsx:66,169` —— `groups[f.competition_name]` 用英文名作 key，分组标题也是英文名。
- `frontend/src/pages/Dashboard.tsx:83,117` —— 提醒卡 `d.competition_name` / `v.competition_name` 直接渲染英文。
- `backend/data/seed/competitions_zh.json` 共 **31 条**，`teams_zh.json` 共 **132 条**。OddAlerts 后端竞赛库约 800+ 联赛、几千支球队，覆盖率明显偏低。
- 联赛 chip 排序：`backend/routers/fixtures.py:266` 使用 `ORDER BY COALESCE(c.name_zh, f.competition_name)`。CJK Unicode 码点（U+4E00+）排在 ASCII 之后，导致中文名联赛实际在 chip 列表中排到英文之后——与"中文优先"目标相反。

## Proposed Solution

把"已建好的 zh 链路"全部接通到所有渲染点；把"被忽略的 zh 种子"补齐到能覆盖 `POPULAR_LEAGUE_IDS` 全部 22 个联赛及其本赛季在册球队；并把 chip 排序改为"有 zh 名的优先 → 再按 zh / en 名字典序"。

不引入运行时翻译服务、不接 i18next/locale 切换框架——当前阶段只需中文一种语言，所有 i18n 复杂度集中在两个静态 JSON seed 文件 + 一个 fallback 工具函数。

## Key Hypothesis

我们相信「在所有展示文本节点统一走 `name_zh ?? name_en` fallback + 把 22 个主流联赛 + 各联赛在册球队全部补齐 zh 名 + chip 按 zh 优先排序」能让中文用户在主流联赛比赛流程中**看不到任何英文残留**。验收信号：

- 主流联赛（`POPULAR_LEAGUE_IDS` 内全部 22 个）的联赛 chip / 分组标题 / 卡片 / 详情页 / Dashboard 提醒卡 —— 全部 5 个表面 100% 中文。
- 主流联赛在册球队（截至发布日 OddAlerts `/competitions/:id/standings` 返回的全部队伍）中文覆盖率 100%。

## What We're NOT Building

- **多语言切换 / locale framework**：当前唯一目标语言是中文，不引入 i18next、react-i18n 等运行时框架。
- **英文模式 / 切换 toggle**：英文原名只作为 zh 缺失时的兜底，不暴露切换 UI。
- **球员名 / 教练名 / 场馆名翻译**：本期只覆盖联赛 + 球队两层；详情页其他文本仍走原数据。
- **OddAlerts 全量 800+ 联赛覆盖**：超出 `POPULAR_LEAGUE_IDS` 的长尾联赛在"更多"展开后允许英文 fallback。
- **运行时机器翻译 / LLM 在线翻译**：仅静态种子文件。

## Success Metrics

| Metric | Target | How Measured |
|--------|--------|--------------|
| 主流联赛中文覆盖率 | 22 / 22 = 100% | 脚本扫描 `POPULAR_LEAGUE_IDS` ∩ `competitions_zh.json.name_zh != null` |
| 主流联赛在册球队 zh 覆盖率 | ≥ 95% | 脚本：对 22 个主流联赛遍历最新 standings，按 `name_zh != null` 计算 |
| 渲染面英文残留点 | 0 | 手测 + Playwright 在主流联赛抽样比赛的 5 个表面截图回归 |
| Chip 中文排序正确性 | zh-named 全部排在 en-only 之前 | 脚本对 `/competitions` 响应做断言 |

## Open Questions

- [ ] 球队 zh 名采用哪个权威翻译源（虎扑 / 懂球帝 / 维基中文 / OddAlerts 提供）？需要在 Phase 2 决定，影响一致性。
- [ ] 部分联赛存在"通用名 vs 赞助名"差异（如 Carabao Cup vs 联赛杯），是否保留中文俗称？默认走中文俗称。
- [ ] Dashboard 的 `DroppingOddsAlert` / `ValueBet` 接口是否需要后端也返回 `competition_name_zh` 字段，还是前端按 `competition_id` 二次 join？倾向后端补字段（一次性，最干净）。

---

## Users & Context

**Primary User**
- **Who**：以中文为主要语言的足球预测平台用户（散户彩民 / 数据分析爱好者）。
- **Current behavior**：在比赛列表 / 详情页扫读，依赖联赛名 + 球队名快速定位关注比赛。
- **Trigger**：进入应用看比赛、点开详情、收到 Dashboard 跌赔提醒——任何场景中遇到陌生英文名都会停顿确认。
- **Success state**：从 chip 选择到详情页完整流程不再有"猜英文"心智负担。

**Job to Be Done**
当我在 Goalcast 浏览主流联赛比赛时，我希望所有联赛名和球队名都是熟悉的中文，这样我可以一眼锁定关心的比赛而不被陌生英文打断。

**Non-Users**
- 英文母语用户 / 海外用户：本期不为其优化，但保留英文兜底确保不破坏。
- 长尾联赛（非洲、东欧低级别等）爱好者：明确告知会展开"更多"后回退英文。

---

## Solution Detail

### Core Capabilities (MoSCoW)

| Priority | Capability | Rationale |
|----------|------------|-----------|
| Must | MatchDetail 全部使用 `_zh ?? en` fallback（6 处） | 直接修复 bug #4 |
| Must | Matches 分组 key + 标题使用 zh 名 | 直接修复 bug #5 |
| Must | Dashboard 提醒卡接通 zh 名 | 同类问题收口 |
| Must | 联赛 chip 排序：zh-named 优先 | 修复 bug #1 |
| Must | 补齐 `POPULAR_LEAGUE_IDS` 22 联赛全部 zh | 解 bug #2 必要条件 |
| Must | 补齐 22 主流联赛在册球队 zh | 解 bug #3 必要条件 |
| Should | 抽取共用 `pickZh(zh, en)` 工具函数 | 避免散落 `?? en` 模式，集中策略 |
| Should | 后端 `dropping_odds` / `value_bets` 端点补 `competition_name_zh` 字段 | 让前端不必再次 join |
| Could | `teamMeta.ts` 同步增补缩写 / 颜色 | 与本期补齐的球队对齐，避免新中文名走 hash fallback 色 |
| Could | 联赛分组按 zh 名排序 | 进一步提升一致感 |
| Won't | i18n framework / locale 切换 | 见 "What We're NOT Building" |
| Won't | 球员名 / 教练名 / 场馆名 zh | 同上 |

### MVP Scope

Phase 1 + Phase 2（前端接线 + 主流联赛 zh 种子补齐）即可释出对用户可感知的修复——Phase 3 是覆盖率扩面与排序优化。

### User Flow

1. 用户进入 Matches → 联赛 chip 列表中**中文联赛全部排在前**。
2. 用户点击中文联赛 chip → 比赛分组标题**显示中文联赛名**。
3. 用户点开卡片 → 详情页 ph-title / md-hero / ph-sub **均为中文球队名 + 中文联赛名**。
4. 用户回到 Dashboard → 跌赔提醒 / Value Bets 提醒**显示中文联赛名**。

---

## Technical Approach

**Feasibility**: HIGH

**Architecture Notes**
- zh 名链路已搭好：DB `competitions.name_zh` / `teams.name_zh` → `backend/routers/fixtures.py:160-161` 已 SELECT → API 已暴露 `home_team_zh` / `away_team_zh` / `competition_name_zh` / `name_zh`。本期 90% 是"在前端的渲染点把字段接上"。
- 种子扩充走 `backend/data/seed/*.json` + `backend/services/seed.py` 现有 idempotent UPSERT，重启后端自动加载，零 schema 变更。
- 排序修正只改一处 SQL `ORDER BY (name_zh IS NULL), COALESCE(name_zh, name)`。

**Technical Risks**

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| 球队 ID 漂移：OddAlerts 改 team_id 导致 zh seed 失效 | L | 用 `name_en` 做次级 key，前端再加 `teamMeta` BY_NAME fallback |
| 同名联赛混淆（Serie A 意 vs 巴；Super League 中超 vs 希腊 vs 瑞士） | M | seed 文件用 `id` 主键已避免；只要前端不按 name match 即安全 |
| 球队 zh 名翻译质量参差 | M | Phase 2 在新增前 review 一次主流联赛 ~400 队 |
| 长尾联赛"更多"展开后大量英文 chip 影响排序观感 | L | 已通过 zh-优先排序天然分桶，长尾英文不污染主区 |

---

## Implementation Phases

| # | Phase | Description | Status | Parallel | Depends | PRP Plan |
|---|-------|-------------|--------|----------|---------|----------|
| 1 | 前端 fallback 接线 | MatchDetail / Matches 分组 / Dashboard 提醒卡全部走 `_zh ?? en`；抽 `pickZh` 工具 | pending | with 2 | - | - |
| 2 | Chip 中文优先排序 | 后端 `ORDER BY (name_zh IS NULL)` 修正 + 前端二级稳定排序 | pending | with 1 | - | - |
| 3 | 主流联赛 zh 种子补齐 | 校验 22 个 `POPULAR_LEAGUE_IDS` 在 `competitions_zh.json` 全覆盖；缺失项补充 | pending | with 4 | - | - |
| 4 | 主流联赛球队 zh 补齐 | 对 22 联赛在册球队（约 400 队）补 `teams_zh.json`；同步 `teamMeta.ts` 缩写 / 颜色 | pending | with 3 | - | - |
| 5 | 验收脚本 + 视觉回归 | 覆盖率检查脚本 + Playwright 5 表面截图对比 | pending | - | 1, 2, 3, 4 | - |

### Phase Details

**Phase 1: 前端 fallback 接线**
- **Goal**：消除所有已知"英文残留点"。
- **Scope**：`MatchDetail.tsx`（6 处）、`Matches.tsx`（line 66 分组 key + line 169 标题）、`Dashboard.tsx`（line 83 / 117）。新增 `frontend/src/lib/i18n.ts` 导出 `pickZh(zh, en)` 单函数。
- **Success signal**：grep 整个 `frontend/src` 内 `f.home_team`、`f.away_team`、`f.competition_name` 的裸用全部清零（仅保留 `pickZh(...)` 包装或 `_zh` 字段调用）。

**Phase 2: Chip 中文优先排序**
- **Goal**：联赛 chip 视觉上中文聚簇在前。
- **Scope**：改 `backend/routers/fixtures.py:266` 为 `ORDER BY (c.name_zh IS NULL), COALESCE(c.name_zh, f.competition_name)`；前端 `Matches.tsx` `popular` 列表保持后端顺序，不再二次排序。
- **Success signal**：`/competitions` 响应中前 N 条 `name_zh != null`、后段 `name_zh == null`，断言通过。

**Phase 3: 主流联赛 zh 种子补齐**
- **Goal**：`POPULAR_LEAGUE_IDS` ⊆ `competitions_zh.json.id`。
- **Scope**：当前 seed 31 条覆盖率较高，但需 diff `POPULAR_LEAGUE_IDS`（22）与 seed，补齐缺口（如 ID 327 FA Cup / 268 Carabao Cup 是否已包含需校对）；同时验证每条都有 `name_zh != null`。
- **Success signal**：脚本 `python -c "..."` 输出 `missing: []`。

**Phase 4: 主流联赛球队 zh 补齐**
- **Goal**：22 联赛在册球队 zh 覆盖 ≥ 95%。
- **Scope**：拉取每个联赛 standings → diff `teams_zh.json` → 批量补全。同时把新增球队的常用中文名 / 简称 / 主色补到 `frontend/src/lib/teamMeta.ts` 的 `BY_NAME`（避免详情页 TeamAbbr 走 hash fallback）。
- **Success signal**：覆盖率脚本输出 ≥ 95%。

**Phase 5: 验收脚本 + 视觉回归**
- **Goal**：自动化把守，避免新增联赛 / 球队再次掉队。
- **Scope**：`scripts/check_zh_coverage.py`（联赛 + 球队覆盖率）+ Playwright 截图：联赛列表 / 比赛分组 / 卡片 / 详情页 / Dashboard 共 5 张主流联赛截图。
- **Success signal**：CI 跑通；OCR 抽样确认无英文残留（人眼复核兜底）。

### Parallelism Notes

- Phase 1 ↔ Phase 2：纯前端 fallback 与后端 SQL 改动互不冲突，可并行。
- Phase 3 ↔ Phase 4：联赛 seed 与球队 seed 各自独立 JSON，互不影响，可并行。
- Phase 5 必须等 1-4 全部落地后跑（否则成功标准跑不绿）。

---

## Decisions Log

| Decision | Choice | Alternatives | Rationale |
|----------|--------|--------------|-----------|
| 不引入 i18n framework | 静态 seed + `pickZh` 工具 | i18next / react-intl | 仅一种目标语言，框架引入是过度工程 |
| zh 缺失走英文兜底 | 兜底 | 强制不显示 / 显示占位符 | 长尾联赛仍需可用，英文比 "—" 信息更多 |
| Seed 用 `id` 主键 | id 主键 | name 字符串匹配 | 避免同名联赛混淆（Serie A 意/巴；Super League 中/希/瑞士）|
| Chip 排序在后端做 | 后端 SQL | 前端 sort | 减少前端 churn，多端复用一致 |

---

## Research Summary

**Market Context**
- 国内主流体育数据应用（懂球帝、虎扑、网易体育）默认全中文展示主流联赛，长尾联赛保留英文/拼音，与本 PRD 路线一致。
- OddAlerts 上游不提供中文，必须由我们维护中文映射；这是技术债的边界来源。

**Technical Context**
- DB schema、API、`pickZh` 兜底链路已存在；本期完全是"接线 + 数据" 而非"建系统"。
- 现有 31 联赛 / 132 球队 seed 已覆盖大部分欧洲五大 + 部分洲际杯赛球队，扩充工作量集中在杯赛 + 美洲 + 亚洲 + 中超的在册球队，估算 ~300 队需补充。

---

*Generated: 2026-05-17*
*Status: DRAFT - 待评审*

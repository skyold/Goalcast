# 比赛日时区偏好:让用户控制"今天看哪些比赛"的边界

> 路线对应:补齐 `signal-catalog-and-subscriptions.prd.md` Phase 4 之后
> 缺失的"用户级时间窗"概念。本 PRD 只做**用户偏好设置面**,不动现有
> signals / paper-trading 查询(留独立 follow-up PRD)。

## Problem Statement

当前所有"今天的比赛"展示口径都是**系统默认**:

1. **后端 snapshot 管线**对所有 fixture 自动算信号,不按比赛日切。
2. **前端 catalog / paper-trading 页面**显示全量 fixture(可能 24h
   前、未来 60h 后都混在一起),用户没法说"我就想看今晚 + 明天凌晨的
   比赛"。
3. **`OA_HT_V2.py` 原脚本里有"上海时间 12:00 ~ 次日 12:00"的比赛日
   切日逻辑**(`OA_HT_V2.py:339-347`),但这是 CLI 工具的硬编码,信号
   管线没继承。

用户(尤其是有跨时区作息差异的玩家)需要**两个维度**的偏好:

- **时区**:伦敦玩家关心 BST/GMT,日本玩家关心 JST,中国玩家关心
  Asia/Shanghai。当前所有时间显示都是 UTC,对人不友好。
- **比赛日切日点**:Asia/Shanghai 的 **12:00 cutoff**(博彩/体育媒体
  行业惯例,避免凌晨南美场被丢到"明天"的清单里 —— 参考
  `docs/OA_HT_V2_alignment.md` 第 7 节)vs **00:00 cutoff**(自然日,
  现代 App 默认习惯)。

没有这两个偏好,**用户无法在产品里说"给我看今天的比赛"** —— "今天"
没有明确定义。

## Evidence

- **`OA_HT_V2.py:339-347`** 已经实现了 noon-cutoff 切日,**作为博彩
  行业惯例的实证**(其他主流体育产品如 365bet、虎扑赛程页也用 noon
  cutoff)。
- **`user_settings` 表当前只有 `locale TEXT`**(`database.py:135`),
  没有 timezone 也没有 match-day cutoff 字段。加 2 列就够。
- **`user_competition_prefs` 表 + `user_alert_settings` 表** 是已经
  存在的"按用户维度持久化偏好"模式 — 同样的模式延伸到时区/比赛日
  即可,前端"我的联赛"和"提醒设置"侧栏入口可参照,加第三个"比赛日"。
- **前端无任何 timezone-aware 显示** — `fmtKickoff` 直接用 UTC
  ISO 字符串拼日期。

## Proposed Solution

把"比赛日"做成一个**新的用户设置页**,跟"我的联赛"和"提醒设置"并列
在右边栏。**只做设置面**,不动现有查询逻辑(过滤接到 query 是后续
PRD 的事)。

```
右边栏 (登录态):
  ├─ 我的联赛           (settings/leagues, 已有)
  ├─ 提醒设置           (settings/alerts, 已有)
  └─ 比赛日 ← 本 PRD    (settings/match-day, 新增)
       ├─ 时区
       │   Asia/Shanghai (默认) / Asia/Tokyo / Europe/London / UTC /
       │   America/New_York / America/Los_Angeles / Australia/Sydney /
       │   ...(7-10 个主流,加 "其他"自由输入)
       └─ 比赛日起算时间
           ◉ 12:00(博彩日,推荐)
           ○ 00:00(自然日)

未登录态:
  设置保存在 localStorage,登录后合并到 server-side preference
```

## Key Hypothesis

我们相信【给用户两个比赛日维度的偏好】会**显著降低跨时区用户的认知摩
擦**,前置条件是**后续 PR 把这两个偏好接到 signals / paper-trading 的
查询过滤**(本 PRD 不做)。

短期验收信号:
- 设置页 UI 上线后 30 天,登录用户中 **≥ 20% 至少改过一次默认值**
  (有人在用,非死代码)
- localStorage 的偏好与 server-side 偏好在登录后**正确合并**(后写
  覆盖前;冲突时 local 胜)

长期验收(等查询过滤上线):
- 比赛日维度的设置改变 → 主页面比赛列表数量**至少减少 30%**(说明
  过滤有用)。

## What We're NOT Building

- **不**做查询层过滤 —— 本期只把偏好持久化,signals / paper-trading
  / catalog 的查询不动。**单独 PR 接**,优先级取决于用户使用情况。
- **不**做按比赛日维度"今天 / 明天 / 自定义"快捷切换 —— 本期默认就
  显示"今天"(根据时区 + cutoff 计算),"明天"等粒度选项留 V1.5。
- **不**做时区**自动检测**(`Intl.DateTimeFormat().resolvedOptions()
  .timeZone`)—— 默认值统一 Asia/Shanghai,用户主动改。
  (理由:作者意图 + 减少跨时区用户的意外切换)
- **不**做夏令时(DST)显示告警 —— `pytz` / Python `zoneinfo` 自动
  处理,前端不暴露 DST 概念。
- **不**做"自定义 cutoff 小时"(任意整数点切日)—— 只给 12:00 / 00:00
  二选一。
- **不**做团体偏好(共享给一组用户)—— V2 候选。
- **不**做与 alerts 偏好的联动(比赛日改变是否影响 alerts 触发窗口)
  —— alerts 现状用 user_competition_prefs,与时区独立。

## Success Metrics

| Metric | Target | How Measured |
|---|---|---|
| 设置页可访问 | 登录用户能从右栏跳到 /settings/match-day 并保存 | E2E 测试 |
| Schema 迁移幂等 | `user_settings.timezone` 和 `match_day_cutoff_hour` 字段 ALTER 后重启不报错 | `PRAGMA table_info(user_settings)` 包含两列 |
| 默认值正确 | 新用户注册后 timezone='Asia/Shanghai', cutoff=12 | 注册后查 user_settings 行 |
| 未登录态持久化 | localStorage 保存 + 刷新页面后保留 | E2E 测试 |
| 登录合并 | 已 localStorage 设过的未登录用户登录后, server 端值更新为本地值(后写胜) | 集成测试 |
| 改变值 → 后端持久化 | PUT /api/me/match-day 接口正确写库 | 单元 + 集成测试 |

## Open Questions

- [ ] **Q1: 时区下拉列哪些选项?** 选项:(a) 写死 8 个主流时区
      (Asia/Shanghai, Asia/Tokyo, Europe/London, Europe/Berlin,
      America/New_York, America/Los_Angeles, Australia/Sydney, UTC)
      + "其他"打开自由输入框;(b) 列全 400+ tzdata 时区让用户搜;
      (c) 只让用户输入字符串,server 端用 zoneinfo 校验。
      **建议 (a)** —— 8 个主流覆盖 95% 用户,"其他"留给小众。
- [ ] **Q2: cutoff 限制只能 12 / 00 二选一吗?** PRD 表面如此。如果
      未来需要"自定义小时",字段类型已经是 INTEGER,所以**前向兼容**
      (UI 可以扩成 dropdown 0-23,DB 不变)。
- [ ] **Q3: 未登录态用 localStorage 偏好,登录后合并冲突怎么处理?**
      A. 后写胜(localStorage 覆盖 server);B. server 胜(localStorage
      忽略);C. 弹窗让用户选。**建议 A**(localStorage 是用户最近的
      显式选择,有上下文)。
- [ ] **Q4: 已注册的现存用户怎么处理?** ALTER ADD COLUMN 的默认值
      自动给 'Asia/Shanghai' + 12。**建议:不主动通知**,用户首次进
      新页面看到就行。
- [ ] **Q5: 时区显示当前时间(让用户验证)?** 设置页可以加一行"按你
      当前时区现在是 18:32, 比赛日 5/19 12:00 ~ 5/20 12:00"。**建议
      加**,帮助用户感性验证时区设置正确。
- [ ] **Q6: 跟 `user_competition_prefs` + `user_alert_settings` 三个
      偏好表分散好,还是合并成一个 `user_preferences`?** 短期分散,
      跟现有模式一致。长期合并是技术债清理,与本 PRD 解耦。

## Users & Context

- **谁会用?** 主要是有跨时区作息的用户(欧洲玩家、跨州出差玩家、
  在中国看南美/欧战的玩家)。中国本地玩家也用 — 选 12:00 cutoff 跟
  作者节奏一致。
- **为什么右栏放第三个入口?** "我的联赛""提醒设置""比赛日"都是
  "看球/下注偏好",并列。比赛日的认知重要性 ≥ 提醒设置(后者只影响
  bell 通知,前者影响每天看到哪些比赛)。
- **何时拒绝使用?** 用户不跨时区、不在意切日点 → 默认值 (Asia/Shanghai
  + 12:00) 直接管用,不进设置页也行。

## Solution Detail

### Capabilities (MoSCoW)

| Priority | Capability | Rationale |
|---|---|---|
| Must | `user_settings` 加 `timezone TEXT DEFAULT 'Asia/Shanghai'`、`match_day_cutoff_hour INTEGER DEFAULT 12` 两列 (idempotent ALTER) | 数据基础 |
| Must | `GET /api/me/match-day` → `{timezone, cutoff_hour}` | 读取偏好 |
| Must | `PUT /api/me/match-day` 接受 `{timezone, cutoff_hour}` | 持久化 |
| Must | 后端校验 timezone(zoneinfo) + cutoff ∈ {0, 12} | 拒绝脏值 |
| Must | 前端 `pages/SettingsMatchDay.tsx` 页面:时区 dropdown(8 主流 + "其他")+ cutoff radio | 主交付物 |
| Must | 右栏 `Layout.tsx` 加"比赛日"链接,登录态可见 | 入口 |
| Must | 未登录态用 localStorage 存 `gc_match_day_prefs` JSON | 游客也能预设置 |
| Must | 登录后自动 PUT 一次 localStorage 值到 server 端(冲突后写胜) | 合并 |
| Must | i18n zh / en 文案(选项标签、说明) | 国际化 |
| Should | 设置页底部显示"按你当前选择,比赛日 = X 月 Y 日 12:00 ~ 次日 12:00 (Asia/Shanghai)" | 感性验证 |
| Should | 时区下拉选 "其他" 时弹自由输入,前端用 `Intl.supportedValuesOf('timeZone')` 校验后再 PUT | 容错 |
| Won't (V1) | 查询过滤接到 signals / paper-trading / catalog | 独立 PR |
| Won't (V1) | "今天 / 明天 / 自定义" 比赛日粒度切换 | V1.5 |
| Won't (V1) | 时区自动检测 | 默认值固定为作者节奏 |
| Won't (V1) | DST 提示 / 时区改变后的迁移告警 | zoneinfo 自动处理 |

### Schema 变化

```sql
-- backend/database.py (idempotent ALTER pattern):
ALTER TABLE user_settings ADD COLUMN timezone TEXT DEFAULT 'Asia/Shanghai';
ALTER TABLE user_settings ADD COLUMN match_day_cutoff_hour INTEGER DEFAULT 12;
```

(无新表,无新索引;cutoff_hour 用 INTEGER 而非 BOOL 是为前向兼容
"任意整数点切日"。)

### API

```
GET /api/me/match-day
  → 200 {"timezone": "Asia/Shanghai", "cutoff_hour": 12}
  → 401 if not logged in

PUT /api/me/match-day
  body: {"timezone": "Asia/Tokyo", "cutoff_hour": 0}
  → 200 (写库后)
  → 401 if not logged in
  → 422 if timezone invalid (zoneinfo 校验失败) or cutoff_hour ∉ {0, 12}
```

### 未登录态(localStorage 模型)

```typescript
// frontend/src/lib/match_day_prefs.ts
const KEY = 'gc_match_day_prefs'

function getLocalPrefs(): { timezone: string; cutoff_hour: 0 | 12 } {
  const raw = localStorage.getItem(KEY)
  if (raw) {
    try { return JSON.parse(raw) } catch {}
  }
  return { timezone: 'Asia/Shanghai', cutoff_hour: 12 }
}

function setLocalPrefs(p: { timezone: string; cutoff_hour: 0 | 12 }) {
  localStorage.setItem(KEY, JSON.stringify(p))
}
```

登录后 hook:

```typescript
// 登录 useEffect 里
const localPrefs = getLocalPrefs()
const serverPrefs = await api.me.matchDay()  // GET
if (JSON.stringify(localPrefs) !== JSON.stringify(serverPrefs)) {
  // 后写胜:用 local 覆盖 server,然后清掉 localStorage
  await api.me.updateMatchDay(localPrefs)
  localStorage.removeItem(KEY)
}
```

### 文件改动估算

- **backend 新文件**: 无(可以放进 `routers/me.py` 现有 router)
- **backend 改动**:
  - `database.py` —— 2 列 ALTER + PRAGMA 检查
  - `routers/me.py` —— GET + PUT `/api/me/match-day` endpoints + Pydantic
    校验(用 `zoneinfo.ZoneInfo`)
- **frontend 新文件**:
  - `pages/SettingsMatchDay.tsx`
  - `lib/match_day_prefs.ts` (localStorage 助手 + 登录合并)
- **frontend 改动**:
  - `routes.tsx` —— 加 `/settings/match-day` 路由
  - `components/layout/Layout.tsx` —— 右栏加链接
  - `lib/api.ts` —— `api.me.matchDay()` / `updateMatchDay()`
  - `i18n/messages.{zh,en}.json` —— ~12 个新 key
- **测试**:
  - `tests/test_me_match_day.py` —— GET/PUT 校验 + 时区合法性 + cutoff
    范围
  - E2E:Playwright 跑一遍设置 → 保存 → 刷新 → 仍生效

预估总规模:**~600 行新代码 + 300 行测试**,1 周交付。

### 后续 follow-up 路线图(不在本 PRD,但已登记防遗忘)

**指导原则**:本 PRD 上线 = 偏好可存可读但不影响展示。下面 7 项按
**用户感知度 × 实现成本**排成 V1.5 / V2 / V3 / Drop 四档,每项有独立
PRD slug 占位,等触发条件命中再写细案。

#### V1.5(本 PRD 上线后 2-4 周内启动,优先级最高)

**F1. `match-day-query-filter.prd.md`** —— 把偏好接到查询层
- **作用**:让"比赛日"偏好真正影响用户看到的列表(否则本期等于死代码)。
- **范围**:signals catalog / paper-trading books 主图 / /insights/matches
  三个入口加 timezone-aware "today's matches" 过滤。
- **触发条件**:本 PRD 灰度上线 ≥ 7 天 + 至少 5 个用户改过默认值
  (确认有人真在用)。
- **依赖**:本 PRD + 后端 `services/match_day.py` 新工具函数(把
  timezone + cutoff_hour → UTC 时间窗)。
- **估算**:~400 行代码 + 200 测试,3-5 天。
- **风险**:改了 3 个核心查询的范围,容易回归;需要灰度 + 旧行为
  保留(无登录 / 默认值用户继续看全量)。

**F2. `match-day-quick-switcher.prd.md`** —— 今天 / 明天 / 自定义
- **作用**:右上角加快捷切换,不必每次进设置页改 cutoff。
- **范围**:列表顶部 chip 选择器:`◉ 今天 / ○ 明天 / ○ 本周末 / ○ 自定义`,
  仅前端状态,不动 settings 持久化。
- **触发条件**:F1 上线 + 用户反馈"想看明天的比赛"≥ 3 次。
- **依赖**:F1(没有过滤,切换无意义)。
- **估算**:~200 行代码 + 50 测试,1-2 天。

#### V2(3-6 个月内,看用户反馈决定)

**F3. `match-day-timezone-autodetect.prd.md`** —— 时区自动检测 + 引导
- **作用**:新用户首次登录时,基于 `Intl.DateTimeFormat().resolvedOptions().timeZone`
  弹一次性引导:"检测到你在 Europe/London,是否切换?"。**不静默改**。
- **触发条件**:F1 上线 + 非 Asia/Shanghai 用户占比 ≥ 15%(说明
  跨时区用户群体存在)。
- **依赖**:本 PRD + 一次性 onboarding 框架(目前没有,可能需要先建)。
- **估算**:~300 行代码 + 150 测试,2-3 天。
- **风险**:默认值偏离作者节奏会引起本地用户困惑,引导必须显式确认。

**F4. `match-day-custom-cutoff.prd.md`** —— 任意整数小时切日
- **作用**:cutoff 从 {0, 12} 扩成 dropdown 0-23,DB 不变(已是
  INTEGER,本 PRD 就是为这个前向兼容)。
- **触发条件**:用户反馈"我想 18:00 切日"≥ 5 次,或者发现某用户
  群体作息确实不是 12/00。
- **依赖**:本 PRD(DB 字段已 INTEGER)。
- **估算**:~50 行代码,半天。
- **风险**:基本无 — 纯 UI 扩展,后端校验放宽即可。

#### V3 / 候选(6+ 个月,可能永不做)

**F5. `match-day-dst-alerts.prd.md`** —— 夏令时切换告警
- **作用**:DST 切换日给用户提示"今晚 02:00 ~ 03:00 不存在,
  比赛日窗口可能错位"。
- **触发条件**:某次 DST 切换实际造成线上 bug(目前 zoneinfo 自动
  处理,无证据需要)。
- **依赖**:F1 上线后跑一年观察。
- **估算**:难以预估,看 bug 严重度。

**F6. `team-match-day-prefs.prd.md`** —— 团体共享比赛日偏好
- **作用**:一组用户共享同一个比赛日窗口(教练 + 助理 + 分析师共用
  口径)。
- **触发条件**:产品引入"团队"概念后(目前没有)。
- **依赖**:多人协作模块(暂无)。
- **估算**:大动作,需要新表 + ACL。

#### Drop / 不打算做

**F7. 比赛日 ↔ alerts 联动** —— 比赛日改变是否影响 alerts 触发窗口
- **决定**:**不做**。alerts 用 `user_competition_prefs`,触发逻辑是
  事件驱动(线动 / 信号闪烁),跟"今天展示哪些比赛"是正交的概念,
  耦合反而引入认知负担。
- **如果将来要做**:用户主动反馈"比赛日 12:00 切日时,夜场 alerts
  把我吵醒了"再单独评估。

#### 路线图汇总表

| Slug | 优先级 | 触发条件 | 估算 | 状态 |
|---|---|---|---|---|
| `match-day-query-filter` | **V1.5(最高)** | 本 PRD 上线 + 5+ 用户改默认值 | ~400 行 + 200 测试 / 3-5 天 | 占位 |
| `match-day-quick-switcher` | V1.5 | F1 上线 + 用户反馈 | ~200 行 / 1-2 天 | 占位 |
| `match-day-timezone-autodetect` | V2 | 跨时区用户 ≥ 15% | ~300 行 / 2-3 天 | 占位 |
| `match-day-custom-cutoff` | V2 | 用户反馈 ≥ 5 次 | ~50 行 / 0.5 天 | 占位 |
| `match-day-dst-alerts` | V3 | 实际 DST bug | TBD | 占位 |
| `team-match-day-prefs` | V3 | 团队概念引入后 | 大 | 占位 |
| 比赛日 ↔ alerts 联动 | **Drop** | 用户反馈才重启 | N/A | 不做 |

---

**Status:** Draft v1 · 等待评审
**Depends on:** `paper-trading.prd.md` (V1, user_settings 表已有) +
                `user-personalization.prd.md`(联赛 / alerts 偏好的先例)
**Blocks:** F1-F6 全部 follow-up PRD(都依赖本期的 schema + 偏好读写)
**Owner placeholders:** 后续 PRD 撰写人待定,本表存证防遗忘。

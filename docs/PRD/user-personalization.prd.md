# 用户个性化平台（登录 / 移动 / 我的联赛 / 双语）

## Problem Statement

Goalcast 当前是"匿名单租户"工具：所有人看到同一份界面、同一份联赛列表、同一种语言（中文）、仅适配桌面。这阻止了三类高频用户场景——通勤路上手机查比分、只关心 2-3 个特定联赛的偏科用户、海外英文用户。把它升级为"账户驱动的个性化产品"是从工具到产品的关键一跳。

## Evidence

- 用户原话（本次需求）：4 项明确诉求——移动版 / 登录 / 自选联赛屏蔽 / 中英文切换。
- `frontend/src/styles/themes.css` 共 `0 个 @media` 查询，`Sidebar.tsx` 是固定侧栏 → 在 <768px 视口下完全不可用。
- `backend/routers/fixtures.py:139-253` 的 `/fixtures` 端点没有任何 user 维度参数，所有用户拿到的是同一份数据。
- 后端代码（排除 venv）grep 无 `users` 表、无 `login` 端点、无 `JWT` / `session`，完全空白。
- `frontend/src/lib/glossary.ts` 头注释 `// Single source of truth for UI explanation copy (Chinese-first, i18n-ready keys)` —— 设计时已为 i18n 留接口，但只有 glossary 一处；其他组件 jsx 中"比赛列表"/"刷新"/"导出 CSV" 等 ~150+ 文案硬编码中文。
- `frontend/src/lib/i18n.ts` 当前只是 `pickZh(zh, en)` 单向 zh-fallback——属于"data layer i18n"，不是 UI i18n。

## Proposed Solution

引入轻量自建账户体系（FastAPI + JWT + bcrypt + email/password），数据库新增 `users` 表 + `user_competition_prefs` 多对多表。所有数据端点（`/fixtures` / `/dropping-odds` / `/value-bets` / `/competitions`）增加可选 `for_user` 参数，登录态自动附带，未登录走当前默认行为（无破坏）。UI 文案抽到 `messages.zh.json` / `messages.en.json` + 一个 `useT(key)` Hook，沿用 glossary 已建好的 key 思想；locale 优先级：用户 prefs > localStorage > 浏览器 `navigator.language` > 默认 zh。移动适配走纯响应式 CSS（不做原生 app），breakpoint 768px：侧栏变 drawer、grid 由 4 列降到 1 列、详情页 2 栏堆叠。

不引入 Supabase / Auth0 等外部鉴权 SaaS——单体 FastAPI + SQLite 架构已经验证可用，引入外部依赖与本项目质量相比是负价值。

## Key Hypothesis

我们相信「账户体系 + 我的联赛白名单 + zh-en 切换 + 响应式移动布局」能让 Goalcast 从"专家工具"扩展到"日常掌上产品"。验收信号：

- 同一账户在桌面登录后在 iPhone Safari 打开 PWA 风格站点，看到自己昨天勾选的 3 个联赛，无其他干扰；UI 全英文（如设置了 en）。
- 未登录访客打开站点功能与今日一致（向后兼容 100%）。

## What We're NOT Building

- **原生 iOS / Android app**：响应式 Web 即可覆盖，避免 app store 审核 / 双端代码维护。
- **第三方 OAuth（Google / Apple / 微信）**：MVP 仅邮箱密码；OAuth 留 V2。
- **多语言 ≥ 3 种**：本期只 zh + en；繁中、日韩等留 V2。
- **付费会员 / 角色权限**：所有登录用户能力一致；账单 / RBAC 留未来。
- **离线优先 / Service Worker / PWA 安装提示**：移动只做响应式样式，不做 PWA。
- **A/B 测试与个性化推荐**：白名单是显式选择，不引入算法推荐。
- **球员 / 教练 / 场馆名 zh-en 双语**：data layer 复用现有 `pickZh` + 现有 seed，本期只追加 en（如有缺失），不做覆盖率攻坚。

## Success Metrics

| Metric | Target | How Measured |
|--------|--------|--------------|
| 移动可用性：iPhone 14 (390×844) Lighthouse 移动评分 | ≥ 85 | Lighthouse CI |
| 注册→首次保存联赛偏好转化率 | ≥ 60% | 自建埋点 `auth.signup` + `prefs.first_save` |
| 已登录用户中"我的联赛"非空比例 | ≥ 80% | DB `SELECT user_id FROM user_competition_prefs GROUP BY user_id` / `users.count` |
| UI 文案 i18n 抽取覆盖率（zh + en） | 100% MVP 路径屏幕 | `scripts/check_i18n_coverage.py` 扫描硬编码中文字符串 |
| 登录态 `/fixtures` 端点附带 `for_user` 且数据过滤生效 | 100% | E2E 测试 |
| 未登录回归测试：所有现有功能行为不变 | 100% | 现有 pytest + Playwright suite 跑绿 |

## Open Questions

- [ ] 鉴权重置流程：邮箱重置链接需要 SMTP 服务，本期是否提供？倾向**先不提供**，密码忘记走人工/未来。
- [ ] Anonymous 模式下用户已经勾选的"我的联赛"在登录后是否自动迁移？倾向**迁移**（基于 localStorage `selectedLeagues`）。
- [ ] en 文案翻译质量：机翻初稿 + 人审 vs 找翻译？倾向**机翻初稿 + 后续 PR 优化**。
- [ ] 移动端 chip 区如果横向超宽是否启用"横滑"vs"折叠展开"？需 Phase 1 prototype。
- [ ] 登录 token 持久化：localStorage（XSS 风险） vs httpOnly cookie（CSRF 风险）？倾向 **httpOnly cookie + SameSite=Lax + CSRF token**。

---

## Users & Context

**Primary User**
- **Who**：通勤 / 出差中的足球预测用户，常用手机；只关心欧洲 4-5 大联赛 + 中超中的 2-3 项；或海外华人 / 英文用户。
- **Current behavior**：被迫在桌面浏览器使用；联赛 chip 太多每次都要重新选；只能看到中文（部分海外用户摩擦）。
- **Trigger**：进入应用后立即想看自己关注的少数联赛；语言不熟悉时无法快速理解 UI。
- **Success state**：登录后无须额外操作，直接看到自己的联赛 + 自己的语言；手机上字号 / 排版正常。

**Job to Be Done**
当我在手机上想快速查看自己关注的联赛比赛预测时，我希望应用记住我的联赛和语言偏好，这样我打开就能直接看自己想看的，不需要每次重选。

**Non-Users**
- 完全匿名访客：本期保留体验为 baseline，但不主动激励他们 → 登录是可选的，不强制。
- 移动 < iPhone SE 尺寸（≤320px）用户：不做特殊优化，能用即可。
- 多账户用户 / 团队账户：单用户单账户，不支持组织功能。

---

## Solution Detail

### Core Capabilities (MoSCoW)

| Priority | Capability | Rationale |
|----------|------------|-----------|
| Must | 用户注册 / 登录 / 登出（邮箱+密码 + JWT in httpOnly cookie） | 联赛白名单 / 语言 prefs 的载体 |
| Must | `users` + `user_competition_prefs` + `user_settings` 表 | 数据持久化基础 |
| Must | `/fixtures` 等端点支持 `for_user` 过滤（未登录默认行为不变） | 兼容向后行为 |
| Must | "我的联赛"管理 UI：可勾选 / 取消任意联赛 | 用户核心诉求 #3 |
| Must | 响应式 CSS：≥768 桌面 / <768 移动布局 | 用户核心诉求 #1 |
| Must | UI 文案 i18n 框架 + zh / en 两套 messages + 切换 UI | 用户核心诉求 #4 |
| Must | Locale 优先级链：`prefs.locale > localStorage > navigator.language > 'zh'` | 未登录也能切换 |
| Should | 注册后引导首选联赛（≤5 项快捷选择） | 提升 first_save 转化 |
| Should | 移动 hamburger drawer 替代 Sidebar | < 768 才有这个 |
| Should | Locale 切换时即时刷新文案（无须重启） | UX 流畅度 |
| Could | Anonymous → 登录账户的"我的联赛"自动迁移 | 用户友好但不阻塞 MVP |
| Could | 注册时邮箱格式校验 + 弱密码警告 | 安全基础 |
| Won't | 邮箱验证 / 密码重置邮件 | 需 SMTP，留 V2 |
| Won't | OAuth (Google/Apple/微信) | 留 V2 |
| Won't | 多设备登录管理 / token 撤销 UI | YAGNI |
| Won't | 第三种语言 | 留 V2 |
| Won't | 原生 app | 见 "What We're NOT Building" |

### MVP Scope

按依赖关系做"骨架优先"：
1. 移动响应式（独立可做）
2. 鉴权底座 + users 表
3. 我的联赛（依赖 2）
4. 双语切换（独立可做，但与 2 整合更好）

MVP 4 件齐发，因为缺任何一件这次升级都不构成"个性化产品"故事。

### User Flow

**首次用户（移动）**：
1. 打开站点 → 右上角"登录/注册"按钮可见。
2. 注册：邮箱 + 密码（≥ 8 位）→ 登录 token 写 httpOnly cookie。
3. 引导页：列出 22 个主流联赛 + "稍后再选"，点选 ≤5 项作为初始白名单。
4. 进入 Dashboard / Matches，只见自己勾选的联赛。
5. 右上角设置 → 切换 EN → 即时刷新为英文。

**回访用户**：直接见到自己的联赛与语言。

**匿名访客**：保持现有体验；右上 banner 可提示"登录解锁个性化"。

---

## Technical Approach

**Feasibility**: MEDIUM

**Architecture Notes**

- **鉴权选型**：FastAPI + `python-jose` (JWT) + `passlib[bcrypt]`；token 放 httpOnly cookie，过期 7 天，刷新机制留简单（重新登录）。
- **数据库**：复用 SQLite，新增 3 表：
  ```sql
  CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
  );
  CREATE TABLE user_settings (
    user_id INTEGER PRIMARY KEY REFERENCES users(id),
    locale TEXT DEFAULT 'zh'  -- 'zh' | 'en'
  );
  CREATE TABLE user_competition_prefs (
    user_id INTEGER REFERENCES users(id),
    competition_id INTEGER REFERENCES competitions(id),
    PRIMARY KEY (user_id, competition_id)
  );
  ```
- **数据端点变更**：`/fixtures` 等接受 `for_user`（从 cookie 自动提取 user_id）；若提供则 `WHERE competition_id IN (SELECT competition_id FROM user_competition_prefs WHERE user_id=?)`。无 `for_user` 时保持现状。
- **前端 i18n**：自建 `useT()` Hook + JSON messages，沿用 `glossary.ts` 已建的 key 思想：
  ```ts
  // frontend/src/lib/i18n/messages.zh.json
  { "nav.dashboard": "总览", "nav.matches": "比赛列表", ... }
  ```
  避免引入 react-i18next（功能远超需求，bundle 体积也大）。
- **Locale 切换刷新**：通过 zustand store 的 `locale` 状态触发 React 重渲；不需要整页 reload。
- **移动响应式**：在 `themes.css` 末尾加 `@media (max-width: 768px) { ... }` 段，覆盖 Sidebar、grid、ph、card 等关键类。Sidebar 加 `isDrawerOpen` state + 顶栏 hamburger 按钮。
- **Auth UI**：新增 `/login` / `/signup` 路由，复用现有 `.btn` / `.btn-primary` 样式系统。

**Technical Risks**

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| httpOnly cookie 跨域 / Vite proxy 设置不当导致 SetCookie 丢失 | M | Vite proxy `changeOrigin: true` + `cookieDomainRewrite`；CORS `allow_credentials=true` |
| 大量硬编码中文字符串抽取漏抓 | M | 写脚本扫描 `frontend/src/**/*.tsx` 中正则匹配 `[一-龥]+` 的字面量，列清单 |
| Locale 切换后某些静态文本（如 `format.ts` 周几缩写）不重渲 | M | format.ts 等工具函数接受 `locale` 参数，所有调用方传入 store 中 locale |
| 用户白名单为空时的 UX：是显示空状态还是回退到全部？ | L | 显示明确的"你还没选联赛"引导，附"管理我的联赛"按钮 |
| 移动端 chip 行折行 / 横滑选择 | M | 先做折行；如果用户测试觉得糟糕再换横滑（Phase 1 内迭代） |
| 现有 `selectedLeagues` zustand store 与登录后 prefs 同步冲突 | M | 登录后从 prefs 覆盖 store；登录态变化时 store 自动 sync |
| 密码哈希性能：bcrypt cost 12 在低端机大约 500ms | L | 这是预期安全成本，可接受 |
| en 翻译质量 | M | 机翻 + 一次人审 pass；后续以 PR 形式优化 |

---

## Implementation Phases

| # | Phase | Description | Status | Parallel | Depends | PRP Plan |
|---|-------|-------------|--------|----------|---------|----------|
| 1 | 移动响应式骨架 | themes.css 增 @media；Sidebar drawer；grid / hero 自适应 | pending | with 2 | - | - |
| 2 | 鉴权底座 | users / user_settings 表；signup / login / logout / me 端点；JWT cookie；前端 Auth context | pending | with 1 | - | - |
| 3 | 我的联赛 | user_competition_prefs 表；管理 UI；`/fixtures` 等接受 for_user 过滤 | pending | - | 2 | - |
| 4 | UI 双语化 | 抽取硬编码文案 → messages.{zh,en}.json；useT Hook；locale 切换 UI + 持久化（prefs/localStorage） | pending | with 3 | 2 | - |
| 5 | 验收 + 移动 E2E + i18n 覆盖率脚本 | Lighthouse 移动评分；Playwright 桌面 + 移动 viewport 全链路；i18n 覆盖率扫描 | pending | - | 1, 2, 3, 4 | - |

### Phase Details

**Phase 1: 移动响应式骨架**
- **Goal**：< 768px 视口下整站可用（不再需要横向滚动 / 字体不被截断）。
- **Scope**：`themes.css` 增加 `@media (max-width: 768px)` 段；`Sidebar.tsx` 加 `isOpen` state + hamburger 按钮；`ph` / `match-grid` / `md-grid` / `kpi-grid` / `filter-grp` 在移动端布局重排为单列或滚动。
- **Success signal**：iPhone 14 viewport (390x844) Playwright 截图所有页面 visible 元素无溢出；Lighthouse 移动评分 ≥ 85。

**Phase 2: 鉴权底座**
- **Goal**：可以注册、登录、登出、获取当前用户。
- **Scope**：
  - 后端：`backend/models/user.py` Pydantic；`backend/routers/auth.py`（`POST /auth/signup` / `POST /auth/login` / `POST /auth/logout` / `GET /auth/me`）；`database.py` 新增 `users` / `user_settings` 表 DDL；`services/auth.py` 密码哈希 + JWT 工具；FastAPI dependency `current_user` 注入。
  - 前端：`frontend/src/lib/auth.ts` `useAuth()` Hook + `/login` `/signup` 路由 + 顶栏登录状态显示。
- **Success signal**：pytest 端到端跑通注册→登录→/auth/me 返回正确 user；前端注册后右上角显示邮箱。

**Phase 3: 我的联赛**
- **Goal**：登录用户只看到自己勾选的联赛数据。
- **Scope**：
  - 后端：`user_competition_prefs` 表；`/api/me/competitions` GET/PUT；`/fixtures` / `/dropping-odds` / `/value-bets` / `/competitions` 接受 `for_user` 参数（自动从 cookie 提取），过滤 WHERE clause。
  - 前端：新增 `/settings/leagues` 路由 + UI；登录态下所有数据请求自动带 cookie；Sidebar 加"管理我的联赛"入口；空白状态引导。
- **Success signal**：登录用户在 Matches 页只看到勾选的联赛；prefs 修改即时生效；未登录用户行为完全不变。

**Phase 4: UI 双语化**
- **Goal**：用户能在 zh / en 之间切换 UI 文案，登录用户的偏好持久化。
- **Scope**：
  - 抽取脚本：扫描 `frontend/src/**/*.tsx` 中 `[一-龥]+` 字面量，生成清单（~150 个）。
  - 建立 `frontend/src/lib/i18n/messages.zh.json` + `messages.en.json` + `useT()` Hook + Provider。
  - 把 ~150 个文案改为 `t('key')`；机翻初稿 en 文本 → 人审 pass。
  - 切换 UI：右上角 `EN/中` toggle；持久化优先级 `prefs.locale > localStorage > navigator.language > 'zh'`。
  - 后端 `user_settings.locale` 字段 + `/api/me/locale` PUT。
- **Success signal**：覆盖率脚本输出 100%；EN 模式下抽样 5 个核心页面截图无残留中文（球队 / 联赛名走 data layer fallback 不在此约束内）。

**Phase 5: 验收 + 移动 E2E + i18n 覆盖率脚本**
- **Goal**：自动化把守，避免回归。
- **Scope**：Lighthouse CI 加移动评分门禁；Playwright 在桌面 + 移动两个 viewport 跑 5 大屏：登录 / 首页 / 比赛列表 / 详情 / 设置；`scripts/check_i18n_coverage.py` 列出未抽取的中文字面量；`scripts/check_auth_paths.py` 列出未做 cookie 透传的请求点。
- **Success signal**：CI 跑绿 + 人眼复核 5 张移动截图无溢出。

### Parallelism Notes

- Phase 1 ↔ Phase 2 完全独立（CSS 改动 vs 后端鉴权）。
- Phase 3 ↔ Phase 4 都依赖 Phase 2 完成，但相互之间可并行（不同文件域）。
- Phase 5 必须最后跑（依赖前 4 件全部就绪）。

---

## Decisions Log

| Decision | Choice | Alternatives | Rationale |
|----------|--------|--------------|-----------|
| 鉴权方式 | 自建 FastAPI + JWT + bcrypt + email/password | Supabase / Auth0 / Clerk; OAuth-only | 单体 + SQLite 架构延续；零外部依赖；当前规模需求不复杂 |
| Token 存储 | httpOnly cookie + SameSite=Lax | localStorage; sessionStorage | 防 XSS；CSRF 用 SameSite + Origin 校验缓解 |
| 是否允许匿名 | 允许，登录解锁个性化 | 强制登录 | 不破坏现有用户体验；降低注册摩擦 |
| 数据端点过滤参数 | `for_user`（cookie 自动提取） | URL query 显式传 user_id | 安全（防参数伪造）；前端调用更简 |
| i18n 框架 | 自建 useT + JSON messages | react-i18next / formatjs | bundle 体积；学习成本；已有 glossary 模式 |
| Locale 优先级 | `prefs.locale > localStorage > navigator.language > 'zh'` | 单一来源 | 兼顾"无登录可切" + "登录后同步" |
| 移动技术 | 响应式 Web（pure CSS @media） | React Native; PWA; 双仓库 | 单一代码库；零审核；MVP 最快 |
| Breakpoint | 768px | 600 / 1024 | 标准 tablet 分界；与主流 design system 对齐 |
| 默认语言 | zh | en; 浏览器 detect | 主用户群是中文；en 是 opt-in |

---

## Research Summary

**Market Context**
- 同类体育数据 / 预测产品（FlashScore / SofaScore / OneFootball）均提供：账户体系、自选联赛、多语言（10+）、移动 app。本期方案是这一基本格局的"最小够用"版。
- 国内类似工具（懂球帝 / 虎扑足球）走 app 优先；本期选响应式 web 是因为受众重叠不大且 web 维护更轻。

**Technical Context**
- 已有基础：FastAPI / SQLite / React / zustand store / `pickZh` 数据层 fallback / glossary key-based 文案。
- 缺口：0 个 `@media` query；0 个 auth 端点；0 个 user-scoped 数据过滤；UI 文案 100% 硬编码 zh。
- 估算工作量分布：Phase 1（CSS） ~ 1 周 / Phase 2（鉴权） ~ 1 周 / Phase 3（白名单） ~ 0.5 周 / Phase 4（i18n） ~ 1.5 周（文案抽取最耗时） / Phase 5（验收） ~ 0.5 周。总约 4.5 周。

---

*Generated: 2026-05-17*
*Status: DRAFT - 待评审*

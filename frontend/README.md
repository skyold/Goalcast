# Goalcast Frontend — 设计原型移植包

把 `port/src/` 下的所有文件按相同路径合并进你本地仓库的 `Goalcast/frontend/src/`。
所有文件都已经按 TypeScript + React Router + React Query + Zustand 的栈写好，对齐你现有
的 `lib/api.ts` 和 `lib/store.ts`。

## 📁 目录映射

```
port/src/                           →  frontend/src/
├─ styles/themes.css                →  styles/themes.css           [新增]
├─ styles/tweaks.css                →  styles/tweaks.css           [新增]
├─ main.tsx                         →  main.tsx                    [覆盖]
├─ App.tsx                          →  App.tsx                     [覆盖]
├─ routes.tsx                       →  routes.tsx                  [新增]
├─ lib/
│  ├─ store.ts                      →  lib/store.ts                [覆盖,增加 theme/density]
│  ├─ teamMeta.ts                   →  lib/teamMeta.ts             [新增]
│  └─ format.ts                     →  lib/format.ts               [新增]
├─ components/
│  ├─ layout/
│  │  ├─ Layout.tsx                 →  components/layout/Layout.tsx     [覆盖]
│  │  ├─ Sidebar.tsx                →  components/layout/Sidebar.tsx    [覆盖]
│  │  └─ TweaksPanel.tsx            →  components/layout/TweaksPanel.tsx [新增]
│  ├─ shared/
│  │  ├─ PredictabilityBadge.tsx    →  components/shared/PredictabilityBadge.tsx [覆盖]
│  │  └─ Spark.tsx                  →  components/shared/Spark.tsx [新增]
│  └─ match/
│     ├─ MatchCard.tsx              →  components/match/MatchCard.tsx [覆盖]
│     ├─ FormStrip.tsx              →  components/match/FormStrip.tsx [覆盖]
│     ├─ TeamAbbr.tsx               →  components/match/TeamAbbr.tsx [新增]
│     ├─ ProbBar.tsx                →  components/match/ProbBar.tsx [覆盖]
│     └─ BigBar.tsx                 →  components/match/BigBar.tsx [新增]
└─ pages/
   ├─ Dashboard.tsx                 →  pages/Dashboard.tsx         [覆盖]
   ├─ Matches.tsx                   →  pages/Matches.tsx           [覆盖]
   ├─ MatchDetail.tsx               →  pages/MatchDetail.tsx       [覆盖]
   ├─ ValueBets.tsx                 →  pages/ValueBets.tsx         [覆盖]
   ├─ DroppingOdds.tsx              →  pages/DroppingOdds.tsx      [覆盖]
   └─ History.tsx                   →  pages/History.tsx           [覆盖]
```

**不动的文件**（保留你现有的）：
- `lib/api.ts`
- `components/match/AhLineSelector.tsx`、`AhLineTable.tsx`、`ScorelineHeatmap.tsx`
- `components/shared/Skeleton.tsx`
- `index.html`、`vite.config.ts`、`tailwind.config.ts`、`tsconfig.json`

## 🚀 落地步骤

```bash
# 1. 备份当前 src
cp -r frontend/src frontend/src.backup

# 2. 拷贝移植包
cp -r port/src/* frontend/src/

# 3. 引入新样式（在 main.tsx 中，已替你写好）
#    import './styles/themes.css'
#    import './styles/tweaks.css'    # 可选，引入 Tweaks 面板样式

# 4. 删掉旧 index.css（或保留为 fallback，不冲突）

# 5. 启动 dev
cd frontend && npm run dev
```

## 🔍 关键变更点

### 1. 主题切换
- 主题/密度状态写在 `store.ts` 的 zustand store（已 `persist`）
- `App.tsx` 在每次 theme/density 变化时把 `data-theme` / `data-density` 写到 `<html>`
- `themes.css` 用 CSS 变量在 3 个主题（A Terminal / B Editorial / C Pitch）和 3 档密度间切换
- `TweaksPanel.tsx` 是右下角的浮动控制面板（带 `tweaks.css`）

### 2. 队徽/队色
- 原始 OddAlerts API **不提供这两项**（见 `docs/frontend-data-gaps.md` #1 #2）
- 移植包用 `lib/teamMeta.ts` 做静态查找：先按 `team_id`、再按队名
- 未命中时按队名 hash 生成 oklch 色，并取前 3 个大写字母作 abbr
- **TODO**：后端能稳定给出 team_id 时，把 `BY_ID` 字典补全

### 3. form5 字段
- TypeScript 类型 `FixtureSummary.home_form.form5` 已经定义为 string
- 但后端目前未必返回 "WDLWW" 字串（见 gaps.md #5）
- `FormStrip` 在 `form5` 为空时显示 `—` 不会崩

### 4. 数据缺口的占位
- MatchDetail：H2H 卡片**已移除**；"两队状态对比"只用 stats 真实可拿的字段（去掉了控球率）
- Dashboard 数据健康卡片：临时用 has_ai / drop 覆盖率近似，建议后端补 `/api/health` 端点
- History：ROI、平均 Edge 显示 "—"，等后端 `bet_outcomes` 表上线再填

### 5. 路由
- 路由表从 `App.tsx` 拆到 `routes.tsx`，便于 App.tsx 专注做主题副作用
- 路径完全沿用你现有的 `/`、`/matches`、`/matches/:id`、`/value-bets`、`/dropping`、`/history`
- 侧边栏改用 `NavLink` 而非自己写 hash 路由

## ⚠️ 已知 TS 类型差异（需要后端补 / 前端临时 cast）

| 文件 | 字段 | 现状 |
|---|---|---|
| `DroppingOdds.tsx` | `opening` / `closing` | TypeScript 类型 `DroppingOddsItem` 没列，但 raw 响应有；目前 `as any` cast |
| `MatchDetail.tsx` | `fixture.home_team_id` / `away_team_id` | 类型已声明 optional，运行期可能未填 |
| `History.tsx` | `result` / `edge` / `drop_pct` | 类型上已有；如果后端尚未返回这些字段，列里显示 "—" 不会崩 |

逐一处理这些时，把 `lib/api.ts` 里对应的 `DroppingOddsItem` / `FixtureCore` 接口补全字段即可。

## 🧪 验证清单

落地后跑一遍：

- [ ] `npm run typecheck` 通过
- [ ] 启动 dev，访问 5 个页面无报错
- [ ] 右下角齿轮按钮可以打开 Tweaks 面板
- [ ] 切换 A/B/C 三个主题，整页面颜色字体全变
- [ ] 切换紧凑/标准/宽松，字号和间距变化
- [ ] 刷新页面后主题和密度仍然保持（zustand persist）
- [ ] 比赛列表 → 点比赛卡片 → 进入详情页正常
- [ ] 详情页右侧只有两张卡片（跌赔记录、两队状态对比），无 H2H

## ❓ 后续

如果哪页的视觉/交互需要进一步调整，回到设计原型 `Goalcast Prototype.html` 改，
我再产出对应 .tsx 的 diff。


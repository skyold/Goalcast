# API 契约：目标响应 schema

> 配套文档：[`frontend-data-gaps.md`](./frontend-data-gaps.md)（UI 视角的缺口清单）
> 本文是**后端开发依据** —— 列出每个端点的"当前"和"目标"响应 schema，逐字段标注来源 / 状态 / 验收。
> 字段命名遵循前端 `frontend/src/lib/api.ts` 已有 TypeScript 类型，避免双向重命名。

## 状态图例

- `✅ DONE` —— 已在响应中，前端已用
- `🟡 PARTIAL` —— 字段存在但值不可用（如空串、null）
- `🔧 BACKEND-TODO` —— 后端待加 / 待透传
- `🎯 UPSTREAM-NEW` —— 上游 OddAlerts 已有，Goalcast 后端需新建拉取 / 聚合
- `🆕 OWN-DATA` —— 上游没有，须自建数据源

每条 gap 后括号里的 `gap #N` 对应 [`frontend-data-gaps.md`](./frontend-data-gaps.md) 编号。

---

## 端点：`GET /api/fixtures`

**用途**：列表页 / Dashboard 卡片 / Top X 摘要。
**当前类型**：[`FixtureSummary`](../frontend/src/lib/api.ts) (api.ts:36)

### 当前响应（实测 2026-05-16）

```jsonc
{
  "fixtures": [
    {
      "id": 420553371,
      "home_team": "Khovd", "away_team": "Khovd Western",
      "competition_name": "Premier League",
      "kickoff_utc": "2026-05-16T07:00:00+00:00",
      "status": "pre",
      "predictability": null,
      "home_form": { "form5": "", "won": 1, "drawn": 0, "lost": 4, "gf": 4, "ga": 27 },
      "away_form": { "form5": "", "won": 0, "drawn": 2, "lost": 3, "gf": 2, "ga": 15 },
      "prediction_summary": null,
      "odds": null,
      "drop_flag": null
      // 还有一堆 legacy 字段（h_form5/h_won/.../trend_*），见 api.ts:60-67 注释，待 History 页迁移后删
    }
  ],
  "total": 2078,
  "cached_at": "..."
}
```

### 目标响应（gap 关闭后）

```ts
type FixtureSummary = {
  // —— 基础信息 ——
  id: number                          // ✅ DONE
  home_team: string                   // ✅ DONE
  away_team: string                   // ✅ DONE
  home_team_id: number                // ✅ DONE   (供 TeamAbbr / team_meta join)
  away_team_id: number                // ✅ DONE
  home_abbr: string | null            // 🔧 BACKEND-TODO   (gap #6)  join /teams/find/:ID.short_code
  away_abbr: string | null            // 🔧 BACKEND-TODO   (gap #6)
  home_color: string | null           // 🆕 OWN-DATA       (gap #1)  自建 team_meta 表
  away_color: string | null           // 🆕 OWN-DATA       (gap #1)
  competition_id: number              // ✅ DONE
  competition_name: string            // ✅ DONE
  competition_country?: string        // ✅ DONE
  kickoff_utc: string                 // ✅ DONE   ISO8601 UTC
  status: 'pre' | 'live' | 'ft'       // ✅ DONE

  // —— 排名 / 战绩 ——
  home_rank: number | null            // 🔧 BACKEND-TODO   (gap #13)  透传 /fixtures/upcoming.home_position
  away_rank: number | null            // 🔧 BACKEND-TODO   (gap #13)
  home_form: TeamForm | null          // 结构 ✅ DONE / form5 🟡 PARTIAL (gap #5)
  away_form: TeamForm | null          // 同上

  // —— 可预测度 ——
  predictability: 'high'|'good'|'medium'|'poor'|null   // 🟡 PARTIAL (gap #7)
  // 现状是 competition 级别。决策待定：
  //   ① 改名为"联赛可预测度"沿用
  //   ② 基于模型置信度 (top1 概率 − 熵) 算 per-fixture

  // —— AI 预测概要 ——
  prediction_summary: {                                // ✅ DONE   来源 /predictions/generate/:ID
    home_win_pct: number                               //           需 fixture 已建模，否则为 null
    draw_pct: number
    away_win_pct: number
    btts_pct: number
    o25_pct: number
  } | null

  // —— 赔率精选 ——
  odds: {                                              // ✅ DONE   来源 /odds/history/:ID
    ft_result: {
      pinnacle: BookmakerOdds | null
      bet365: BookmakerOdds | null
    }
    asian_handicap: AsianHandicapPick | null           // 关键盘口 (line + 主客赔率)
  } | null

  // —— 跌赔信号 ——
  drop_flag: {                                         // ✅ DONE   来源 /odds/dropping
    market_key: string
    drop_percentage: number
  } | null
}

type TeamForm = {
  form5: string         // 结构 ✅ DONE / 值 🟡 PARTIAL (gap #5)  目标：5 char [WDL] 字符串
  won: number; drawn: number; lost: number   // ✅ DONE
  gf: number; ga: number                     // ✅ DONE
}
```

### 验收（acceptance）

| 字段 | 通过条件 |
|---|---|
| `home_abbr / away_abbr` | 非 null 比例 ≥ 95%；长度 2-4；全大写。例：`"ATM"` |
| `home_rank / away_rank` | 顶级联赛非 null 比例 ≥ 90%；整数 ≥ 1 |
| `home_form.form5` | 长度精确为 5；仅含字符 `W`/`D`/`L`；**字符顺序方向需在本文 doc 化**（最近一场在头 or 尾） |
| `home_color / away_color` | hex 字符串如 `"#1d4ed8"`；先覆盖主流联赛球队 ≥ 50% |
| `predictability` | 决策定稿后在本文段落补语义说明 |

### 依赖 / 顺序

1. **P0** —— `home_rank/away_rank` 透传（一行 SQL join，成本最低）
2. **P0** —— `form5` 后端聚合任务（拉最近 5 场结果聚合写入或运行时算）
3. **P0** —— `home_abbr/away_abbr` join `/teams/find/:ID`
4. **P1** —— `home_color/away_color` 静态 team_meta 表（先 200 个主流队）
5. **P1** —— `predictability` 语义决策

---

## 端点：`GET /api/fixtures/:id`

**用途**：MatchDetail 页。
**当前类型**：[`FixtureDetail`](../frontend/src/lib/api.ts) (api.ts:93)
**关键 gap**：见 [`frontend-data-gaps.md`](./frontend-data-gaps.md) #11 (scorelines)、#12（已决定用 stats 字段重做"两队状态对比"卡片、删除控球率）。

> 详细 schema 待补 —— 优先完成 `/api/fixtures` 列表端点的 P0 后再展开本节。

---

## 端点：`GET /api/value-bets`

**用途**：价值投注页 / Dashboard "高 Edge"。
**当前类型**：[`ValueBetItem`](../frontend/src/lib/api.ts) (api.ts:125)
**关键 gap**：#8 —— `edge_pct/prob/odds` 由上游给还是自算需 curl 实测 `/value/upcoming` raw 响应后决策。

> 详细 schema 待补 —— 先实测上游响应，确定 edge 来源后再回填本节。

---

## 端点：`GET /api/dropping-odds`

**用途**：跌水赔率页 / Dashboard "Top 5 跌赔"。
**当前类型**：[`DroppingOddsItem`](../frontend/src/lib/api.ts) (api.ts:117)
**状态**：上游 `/odds/dropping` 字段完整对齐 ✅，无 gap。

> 无后端改造工作；维持现状。

---

## 端点：`GET /api/history`

**用途**：历史回测页。
**关键 gap**：#9 (`result/edge/ROI` 需后端建 `bet_outcomes` 表 + 每日回填)；#11 (Dashboard `daily_metrics`)。

> 详细 schema 待补 —— 等 `bet_outcomes` 表结构定稿后回填本节。

---

## 工作流程建议

1. 后端按本文 P0 字段逐个补，每补完一个字段：
   - 在本文对应行把 `🔧/🎯/🆕` 改成 `✅`
   - 跑一次 `curl /api/fixtures?limit=3 | jq` 更新 "当前响应（实测）" 节的样例 + 抓取日期
2. 前端对照 `🔧/🎯/🆕` 标记字段判断 UI 缺口何时可解锁，把 [`frontend-data-gaps.md`](./frontend-data-gaps.md) 对应行标 DONE
3. 新增端点：在本文末尾追加一节，**先写"目标 schema + 验收"，再开发**

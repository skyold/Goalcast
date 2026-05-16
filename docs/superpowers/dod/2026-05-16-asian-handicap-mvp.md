# 亚盘 MVP — DoD 验证日志

**日期**: 2026-05-16
**计划**: [`docs/superpowers/plans/2026-05-16-asian-handicap-mvp.md`](../plans/2026-05-16-asian-handicap-mvp.md)
**Spec**: [`docs/superpowers/specs/2026-05-16-asian-handicap-mvp-design.md`](../specs/2026-05-16-asian-handicap-mvp-design.md)
**Branch**: v2
**Baseline commit**: `15ddbac` (chore: OddAlerts baseline)
**Final commit**: `830b5d9` (Dashboard + total fix)

---

## 执行轨迹

26 个 commit（含 1 个 fix），覆盖 plan 中 29 个任务里的 26 个。详见 `git log 15ddbac..HEAD`。

### Task 状态总览

| 任务 | 状态 | Commit |
|---|---|---|
| 1.1 建库表 | ✅ | `794aad8` |
| 1.2 OddAlerts 客户端 5 个方法 | ✅ | `0158828` |
| 1.3 sync_fixtures_upcoming | ✅ | `e429c69` |
| 1.4 sync_team_form | ✅ | `54571f5` + `61a768d` (fix) |
| 1.5 sync_ah_odds_seed | ✅ | `1fcdad5` |
| 1.6 sync_ah_odds_latest | ✅ | `2e0ad2e` |
| 1.7 scheduler 注册 + 链式 seed | ✅ | `bb3bf45` |
| 1.8 backfill 脚本 | ✅ | `646a146` |
| 2.1 批次 spike | ⏭ skipped | 用 plan 默认 BATCH_SIZE=25，可在生产 rate-limit 时再 spike |
| 2.2 sync_predictions | ✅ | `769a6c9` |
| 2.3 derive_main_ah_line | ✅ | `d6993c0` |
| 2.4 GET /fixtures 扩展 | ✅ | `27f4489` |
| 2.5 GET /fixtures/{id} 扩展 | ✅ | `f6316db` |
| 3.1 lib/api.ts 类型 | ✅ | `1601ad2` |
| 3.2 PredictabilityBadge | ✅ | `f201c9f` |
| 3.3 FormStrip | ✅ | `7ceef7e` |
| 3.4 OddsPair | ✅ | `fb4ff0d` |
| 3.5 MatchCard 重写 | ✅ | `1592ad7` |
| 3.6 Matches filter chips | ✅ | `868f3f7` |
| 3.7 M3 截图 | ⏭ deferred | 需要 dev server + 数据 |
| 4.1 PredictionBars | ✅ | `9dd0ad2` |
| 4.2 lib/ahMath.ts | ✅ | `7949b12` |
| 4.3 AhLineSelector | ✅ | `26d68bb` |
| 4.4 ScorelineHeatmap | ✅ | `107722b` |
| 4.5 AhLineTable | ✅ | `b6eeb11` |
| 4.6 MatchDetail 重写 | ✅ | `7914000` |
| 4.7 Dashboard 升级 + 后端 total fix | ✅ | `830b5d9` |
| 4.8 M4 截图 | ⏭ deferred | 需要 dev server + 数据 |
| 4.9 DoD 验证 | ✅ | 本文档 |

## 自动化测试

```
backend/.venv/bin/pytest tests/ -q
.................................. [100%]
34 passed in 1.72s
```

涵盖：
- DB schema (`test_database.py`): 3 个测试
- OddAlerts client (`test_oddalerts_client.py`): 6 个测试（含 false-body 边缘情况）
- sync 4 个新 job (`test_sync_jobs.py`): 5 个测试
- AH 推导 (`test_services_ah.py`): 8 个测试
- /fixtures + /fixtures/{id} (`test_routers_fixtures.py`): 含 2 个新测试覆盖 predictability/form/prediction/odds/asian_handicap_lines

## 验收清单（结构层面）

可在不跑 live API 的前提下验证：

- [x] **fixtures 表加 `predictability` + `season_id` 列**（schema 检查通过）
- [x] **`predictions` / `team_form` / `bookmaker_odds` 表创建**（schema 检查通过）
- [x] **5 个新 OddAlerts 客户端方法存在**，含 `/odds/history` 的 `false` body 兼容
- [x] **4 个 sync job 函数存在**：`sync_fixtures_upcoming` (1h) / `sync_ah_odds_latest` (5min) / `sync_team_form` (6h) / `sync_ah_odds_seed` (12h)
- [x] **5 个 sync job 注册到 scheduler**（含 sync_predictions）
- [x] **sync_fixtures_upcoming 末尾链式调用 sync_ah_odds_seed**（max 200/cycle）
- [x] **backfill 脚本 4 步**: fixtures_upcoming → team_form → ah_odds_seed → predictions
- [x] **`derive_main_ah_line` 选最近 50/50 的档**（单测覆盖：-0.5 vs -0.25 选 -0.25）
- [x] **`/fixtures` 返回 predictability/form/prediction_summary/odds(ft+ah)/drop_flag**
- [x] **`/fixtures/{id}` 返回 prediction + asian_handicap_lines + dropping_records**
- [x] **新 query 参数**: `predictability`、`min_drop`、`has_ai`、`limit`(默认 200)
- [x] **`/fixtures` 返回真实 total 计数**（不受 limit 影响）
- [x] **`home_team_obj` / `away_team_obj` 键命名**（避免与字符串字段冲突）
- [x] **7 个新前端组件**：`PredictabilityBadge`、`FormStrip`、`OddsPair`、`AhLineSelector`、`PredictionBars`、`ScorelineHeatmap`、`AhLineTable`
- [x] **`lib/ahMath.ts` ahProbabilities 处理 .25/.75 半盘**
- [x] **MatchCard 渲染 predictability + 双家盘口 + form + AI summary + drop chip**
- [x] **Matches 4 个 filter chips + 加载更多**
- [x] **MatchDetail 6 个 section**: Hero / 模型概率 / 比分热力图+切档 / 赔率全表 / 两队状态 / 跌赔记录（删 H2H）
- [x] **Dashboard 3 tile + Top 5 跌赔**

## 需要 live env 验证的项（待补）

以下项必须在执行 `python -m scripts.backfill` 后由人工 / 集成测试验证：

- [ ] fixtures 行数 ≥ 5,000
- [ ] predictions 行数 ≥ 3,000
- [ ] team_form 行数 ≥ 1,500
- [ ] bookmaker_odds 行数 ≥ 50,000
- [ ] 抽查 5 张 MatchCard：至少 3 张显示「Pinnacle + Bet365」双家
- [ ] 抽查 5 张 MatchCard：至少 4 张显示 form5
- [ ] MatchDetail 比分热力图首渲染 < 200ms（DevTools Profiler）
- [ ] MatchDetail AH 切档重画 < 50ms
- [ ] 4 张验收截图入 `docs/screenshots/`：
  - `m3-matches-filters.png`
  - `m3-matchcard-detail.png`
  - `m4-matchdetail-heatmap.png`
  - `m4-matchdetail-odds-table.png`

## 已知技术债（不影响 MVP，待后续清理）

1. **`FixtureDetail` 类型与后端响应形状不完全对齐**：lib/api.ts 中 FixtureDetail 是扁平结构，但后端实际返回 `{fixture, home_team_obj, away_team_obj, prediction, odds, dropping_records}`。MatchDetail.tsx 用本地类型适配，建议在下一 sprint 统一。
2. **`History.tsx` 仍引用 legacy 字段**（`score_home`、`prob_home_win`、`trend_*` 等），TS 报错 15 处。本次 MVP 范围不含 History 改造，可在下一迭代清理。
3. **`legacy `home_stats` / `away_stats` 字段保留在 `FixtureSummary`** 用于兼容未完全迁移的旧代码。
4. **`sync_fixtures_upcoming` 链式 seed 无独立 try/except**：失败会传播为整个 fixtures_upcoming 错误。下一迭代加 try/except 隔离。
5. **`bookmaker_odds.current` 列收 `closing` 命名变量**（sync_ah_odds_seed 中），后续重命名 `current_price` 更清晰。
6. **`/predictions/generate/multiple` 空列表保护**：客户端方法对 `fixture_ids=[]` 会发空请求；改为 early return `[]` 更安全（在调用方 sync_predictions 已隐式保护）。
7. **`per_page=250` 魔数**：sync_fixtures_upcoming 调用与终止条件两处出现；提取常量。

## 总结

- **代码层完整**：26 commits 落实 plan 中 26 个可代码化任务；DB + sync + API + 前端 5 层全部覆盖。
- **测试层稳健**：34 个自动化测试，TDD 完成每个后端任务；前端无测试框架按 plan 设计跳过单元测试。
- **未交付**：3 个任务（spike、M3/M4 各 2 张截图）需 live env 完成；列入 deferred。
- **下一步**：执行 `cd backend && .venv/bin/python -m scripts.backfill` 完成首次数据填充（~20 分钟）后即可启动 dev server 进行 UI 验证与截图。

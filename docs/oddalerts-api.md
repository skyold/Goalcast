# OddAlerts Football Data API — 能力清单

> 替代旧的 sportmonk / footystats，已实测于 2026-05-16。
> Postman 文档：https://documenter.getpostman.com/view/17615275/2s935uG1WF
> Collection JSON：`https://documenter.getpostman.com/api/collections/17615275/2s935uG1WF`

## 基础信息

- **Base URL**：`https://data.oddalerts.com/api`
- **认证**：所有请求 query string 加 `?api_token=<KEY>`
- **当前 key**（已在 `backend/.env` `ODDALERTS_API_KEY`）：`QV3tYqdMH9wkjY7uWIg2A37jq1wkml7FWPdaYGqpcfqbJ3it4jqWeyWTbY9a`
- **响应包**：`{ "info": {...}, "data": [...] }`，分页字段 `page / per_page / total / total_pages / count / next_page_url`
- **真假端点辨别**：返回 `text/html` 且 body=`OddAlerts Data Engine` 的路径并不存在；只有 `application/json` 的 `{info,data}` 是真实端点
- **共用 query**：所有列表端点都接受 `page`、`per_page`（最大 250–500，因端点而异）
- **共用 include**：`include=` 可加 `stats,probability,odds,odds.live,seasons,referee` 等取嵌套数据（详见各端点描述）

---

## 1. Fixtures（赛程，**主数据源**）

| Method | Path | 作用 | 关键参数 | 实测结果 |
|--------|------|------|----------|----------|
| GET | `/fixtures/:id` | 单场详情 | `include=probability,stats` | ✅ 返回 home/away id+name、kickoff、status、has_odds、season_progress、home/away_position 等 |
| GET | `/fixtures/multiple?ids=a,b,c` | 批量取多场 | `ids` 逗号分隔 | ✅ 一次拿多场详情 |
| GET | `/fixtures/upcoming` | 未来 7 天全部 | `page` | ✅ **9,703 场**（39 页）— 替代 sportmonk 主源 |
| GET | `/fixtures/popular` | 按 OddAlerts 站内热度排序 | `page` | ✅ 同 9,703 场但排序不同 |
| GET | `/fixtures/live` | 进行中/最近完成 | `include=stats,probability,odds,odds.live` | ✅ 22–26 场（含比分、ht_score、elapsed） |
| GET | `/fixtures/between?from=UNIX&to=UNIX` | 任意时间窗 | `from`、`to`（unix 秒） | ✅ 5,114 场 / 24h 窗口 |
| GET | `/fixtures/id` | 仅返回 id 列表 | — | ⚠️ 目前返回空（推荐用 `/fixtures/upcoming`） |

**fixture 数据样例字段**：`id, home_name, away_name, home_id, away_id, competition_id, competition_name, competition_country, competition_type, competition_predictability(high/good/medium/poor/null), season_id, season, season_progress, status (NS/FT/etc), home_goals, away_goals, ht_score, elapsed, home_position, away_position, home_played, away_played, unix, ko_human, date, has_odds, is_friendly, is_cup, venue, referee_id, home_formation, away_formation`

---

## 2. Predictions（蒙特卡洛模拟）

| Method | Path | 作用 | 实测 |
|--------|------|------|------|
| GET | `/predictions/generate/:ID` | 单场 50,000 次模拟 | ✅ |
| GET | `/predictions/generate/multiple?ids=a,b,c` | 多场批量 | ✅ 40,000 sims/场 |

**返回字段**：`simulations, home_win, draw, away_win, total_goals, home_goals, away_goals, btts, o15_goals, o25_goals, o35_goals, o45_goals, scorelines{"1-0":13.44, "2-0":...}` —— 直接给出每个比分概率。

---

## 3. Odds（赔率）

| Method | Path | 作用 | 关键参数 | 实测 |
|--------|------|------|----------|------|
| GET | `/odds/markets` | 全部市场参考表 | — | ✅ **45 个市场**（id+market_key+title） |
| GET | `/odds/history/:ID` | 赔率开盘/收盘/峰值 | `markets`、`bookmakers`（csv） | ✅ 含 opening / closing / peak 三档（59–80 条/场） |
| GET | `/odds/movement/:ID` | 时序赔率波动 | `markets=6&outcomes=home` | ✅ 320 条带时间戳 `unix/datetime` |
| GET | `/odds/multiple?ids=a,b` | 多场赔率 | `markets` | ⚠️ 实测返回 HTML，参数需进一步验证 |
| GET | `/odds/dropping` | 跌赔榜（OddAlerts 旗舰功能） | `bookmakers`、`markets`、`page` | ✅ **45,539 条**（183 页）— 含 opening/closing/drop_percentage |
| GET | `/odds/latest` | 最近赔率变动实时流 | `bookmakers=1,2`、`markets=6` | ✅ 按时间倒序，多 bookmaker 多市场 |

### `/odds/markets` 完整列表（45 个）

```
ft_result(6) ht_result(7) double_chance(8) btts(9) dnb(10)
asian_corners(11) asian_corners_1h(12) total_goals(13) total_goals_1h(14)
goal_line(15) goal_line_1h(16) total_corners(17) away_goals(18) home_goals(19)
btts_o25(20) highest_scoring_half(21) corners_result(22) home_corners(24)
away_corners(25) corners_result_1h(26) corners_result_2h(27) corner_between(28)
total_goals_2h(29) home_corners_1h(30) away_corners_1h(31) home_corners_2h(32)
away_corners_2h(33) home_cards(34) away_cards(35) home_cards_1h(36) away_cards_1h(37)
home_cards_2h(38) away_cards_2h(39) total_cards(40) total_cards_1h(41) total_cards_2h(42)
result_btts(43) home_goals_1h(44) home_goals_2h(45) away_goals_1h(46) away_goals_2h(47)
total_corners_1h(48) btts_1h(49) btts_2h(50) asian_handicap(51)
```

### `/odds/history` 字段
`fixture_id, market_key, market_id, outcome, opening, closing, peak, bookmaker_id, bookmaker_name`
单场可覆盖 15 个市场、42 种 outcome（home/away/draw/over_X/under_X/away_m025 等）。

### `/odds/dropping` 字段
`fixture_id, fixture_name, season_id, season, competition_id, competition_name, competition_type, competition_country, market_key, market_id, outcome, opening, closing, drop_percentage, unix, ko_human, bookmaker_id, bookmaker_name`

---

## 4. Probability（概率模型）

| Method | Path | 作用 | 实测 |
|--------|------|------|------|
| GET | `/probability/:MARKET` | 按概率倒序排出场次 | ✅ `MARKET` 可为 `ft_result/btts/...`，可 `&outcome=home` 过滤 |
| GET | `/probability/markets` | 29 个可用概率市场 | ✅ list of `{id, name, title, bet_market_id}` |
| GET | `/correctScores` | 未来 72h 全比分概率分布 | ✅ **3,860 场**，`scores{"1-0":"13.15","2-0":"11.87",...}` |

`/probability/ft_result` 返回字段：`id, probability, outcome, home_id, away_id, home_name, away_name, home_position, away_position, home_played, away_played, fixture_name, unix, ...`

---

## 5. Value Bets（价值投注）

| Method | Path | 作用 | 实测 |
|--------|------|------|------|
| GET | `/value/upcoming` | 待开赛的全部 value bet | ✅ **6,541 条**，每条含 market（如 `home_win_probability`/`o25_probability`） |
| GET | `/value/results` | 已开赛/已结束的 value bet 结算 | ✅ 5,801 条 |
| GET | `/value/you` | 用户自定义策略列表 | ✅（当前账号 0） |
| GET | `/value/you/:ID` | 单个策略匹配到的赛事 | ✅ |

`/value/upcoming` 字段含 `id, market, home_name, away_name, home_id, away_id, status, unix, ko_human, ht_score, home/away_played, ...` 适合作为「推荐位」直接呈现。

---

## 6. Stats（球队表现统计）

| Method | Path | 作用 | 关键参数 | 实测 |
|--------|------|------|----------|------|
| GET | `/stats/fixture/:ID` | 单场两队完整表现 | `include_frozen`、`include_avg` | ✅ 2 行 |
| GET | `/stats/season/:ID` | 整赛季所有球队 | `include_frozen=true` 拿赛前快照 | ✅ 12 行 |
| GET | `/stats/season/:ID` | 近 X 场表现 | `last_x=10_overall`、`all_comps=true/false` | ✅ 滚动窗口 |

**stats 字段非常丰富**（每行一个球队）：
`team_id, fixture_id, season_id, name, played{total,home,away}, won/drawn/lost/points{total,home,away,*_percentage,*_avg}, goals_total/for/against/difference, goals_over{o0..o5}, goals_for_over, goals_against_over, btts, failed_to_score, clean_sheet, scored_first, conceded_first, goals_1h/2h, goals_for_1h/2h, ...`

每个嵌套对象通常有 `{total, home, away, total_percentage, home_percentage, away_percentage, total_avg, home_avg, away_avg}` 全口径。

---

## 7. Trends（趋势榜）

| Method | Path | 作用 | 实测 |
|--------|------|------|------|
| GET | `/trends/:TREND` | 按指定趋势排序的未来 5 天赛事 | ✅ 每页 250，约 4,445 场 |

**支持的 TREND 名**（来自 Postman 描述，文档列了 25 个）：
- 结果类：`homeWin`、`awayWin`、`draw`、`homeWinHT`、`awayWinHT`、`drawHT`、`boreDraw`（0-0）
- 进球类：`btts`、`btts1h`、`btts2H`、`over15`、`over25`、`over35`、`under25`、`under35`、`avgGoals`、`homeGoals`、`awayGoals`、`1hGoals`、`mostGoals2h`、`lateGoals`（70+ min 进球率）
- 角球类：`over8Corners`、`under9Corners`、`under10Corners`、`1hCorners`

> 已实测可正常返回 JSON：`homeWin / awayWin / draw / btts / over15 / over25 / over35 / under25 / under35`。
> 返回 `"Trend Not Found"` 的均为字面拼写错误（如 `over_25`、`noBtts`、`cleanSheetHome`），名字必须严格按上方拼写。

### 支持的 query 参数（实测）
- `minStat` / `maxStat`（百分比阈值，过滤后 results 数会真的变小）
- `minOdds` / `maxOdds`（赔率范围）
- `minPlayed`（最少出场数）
- `sort`：`odds | stat | time`
- `focus`：部分趋势可设 `home` / `away`（看 Focus 列）
- `page`、`per_page`
- ⚠️ `duration` 参数虽在 info 里显示，但传任何值都会触发 500 错误，目前固定 5 Days

### Trend 数据样例字段
`home_name, away_name, id, unix, competition_name, competition_id, season, season_id, country, <stat>_per (如 home_win_per/btts_home_per/o25_goals_home_per), probability{home_win,draw,away_win,btts,o15..o45,o05_home_goals,...}, is_friendly, stats{home:{...}, away:{...}}` —— 已经把球队表现统计内嵌好，做趋势页可一次取齐。

---

## 8. Teams（球队）

| Method | Path | 作用 | 实测 |
|--------|------|------|------|
| GET | `/teams/all` | 全部球队 | ✅ **66,223 支**（每页 250） |
| GET | `/teams/find/:ID` | 按 ID | ✅ `{id, name, slug, short_code, country, country_id, twitter}` |
| GET | `/teams/country/:ID` | 按国家 | ✅ 例如 country=1（Poland）→ 908 支 |

---

## 9. Players（Beta）

| Method | Path | 作用 | 实测 |
|--------|------|------|------|
| GET | `/players/meta` | 全部允许的 stat/form/include/position 白名单 | ✅ keys=`forms, stats, includes, positions, detailed_positions, defaults, limits` |
| GET | `/players/search?q=Salah` | 名字搜索（最少 2 字符） | ✅ 19 条 |
| GET | `/players/:ID` | 单人完整资料 | ✅ 可 `?include=stats,season_stats` |
| GET | `/players/rank?stat=goals_per90&form=last_10` | 全库按某项 stat 排名 | ✅ 默认 25 条，可加 `teams=14439`、`min_apps=` |
| GET | `/players/fixture/:ID` | 某场两队球员 | ✅ 7 人 / 单场 |
| GET | `/players/competition/:ID` | 某联赛当前赛季全部球员 | ✅（部分小联赛 0） |
| GET | `/players/season/:ID` | 某 season_id 的全部球员 | ✅（部分小联赛 0） |

球员对象字段：`id, team_id, teams[], country_id, nationality, names{name,common_name,firstname,lastname}, position_id, detailed_position_id, shirt_number, updated_at`，按需用 include 添加 `stats / season_stats`。

---

## 10. Referees（裁判）

| Method | Path | 作用 | 实测 |
|--------|------|------|------|
| GET | `/referees` | 全部裁判（支持 `search=`） | ✅ **57,026 人**，1,141 页 |
| GET | `/referees/upcoming` | 未来 14 天有裁判指派的赛事 | ✅ 364 场 |
| GET | `/referees/:ID` | 单人 + 生涯汇总 + 下一场 | ✅ |
| GET | `/referees/:ID/stats` | 黄牌/红牌等按赛季拆解 | ✅ |
| GET | `/referees/:ID/seasons` | 执法过的赛季列表 | ✅ |
| GET | `/referees/:ID/fixtures` | 执法过的全部赛事 | ✅ |

---

## 11. Bet Tracking（用户资产）

| Method | Path | 作用 | 实测 |
|--------|------|------|------|
| GET | `/bankrolls` | 用户在站内创建的 bankroll | ✅（当前账号 0） |
| GET | `/bets` | 用户所有下注，`bankrolls=ID,ID` 过滤，`sort=created_at/unix/odds` | ✅（0） |

需要先在 oddalerts.com 前端创建 bankroll 和录入投注，API 才有数据。

---

## 12. Reference Data（参考数据）

| Method | Path | 作用 | 实测 |
|--------|------|------|------|
| GET | `/countries` | 全部国家 | ✅ 249 国，`{id, name, code, slug}` |
| GET | `/competitions` | 联赛/杯赛 | ✅ **2,412 个**，支持 `country_ids=1,4`、`include=seasons` |
| GET | `/competitions/:ID` | 单联赛详情 | ✅ |
| GET | `/competitions/search?query=Premier League` | 文本搜索 | ✅ 106 条命中 |
| GET | `/bookmakers` | 受支持的博彩公司 | ✅ **8 家**：Pinnacle, Bet365, 1xBet, Betfair Exchange, Betano 等 |

---

## 13. Betslips（投注组合生成器）

| Method | Path | 备注 |
|--------|------|------|
| **POST** | `/betslips` | 仅支持 POST。可传 `markets[]`、`value_bets_only`、`duration`、`target_odds`、`items_per_slip`、`odds_per_*` 等组合生成多张可投注的组合。GET 请求会返回 405。 |

---

## 重要发现 & 后续建议

### 必须替换 sportmonk 的源
- **`/fixtures/upcoming`（9,703 场 / 7 天）** 直接替代 sportmonk 主赛程源
- **`/fixtures/live`** 替代 live tracking
- **`/odds/dropping`、`/odds/movement/:ID`、`/odds/history/:ID`、`/odds/latest`** 完整覆盖跌赔/赔率波动场景

### 比 footystats 更强的能力
- **`/predictions/generate/:ID`**：50,000 次蒙特卡洛模拟 + 完整 scoreline 概率
- **`/correctScores`**：3,860 场 72h 内的比分概率矩阵
- **`/value/upcoming`**：6,541 条已算好的 value bet（含 market 类型）
- **`/probability/:MARKET`**：任意 29 个市场按概率排序的赛事
- **`/stats/{fixture,season}/:ID`**：每队约 70+ 项嵌套统计（home/away/total/_avg/_percentage 全口径）

### 当前后端已使用
- `services/oddalerts.py` 已封装 5 个端点：`/fixtures/id`（**应改用 `/fixtures/upcoming`**）、`/fixtures/{id}`、`/stats`、`/odds/dropping`、`/trends/{type}`、`/odds/history`
- 已用 trend 名：`homeWin、awayWin、btts`（可扩展到上面 25 个）

### 已知坑
1. `/fixtures/id`（字面路径）目前返回 0 条，**不要再用**；用 `/fixtures/upcoming` 或 `/fixtures/between`
2. `/odds/dropping` 的 `market_key=` 过滤实测不生效（total 不变），改用 `markets=<id>` 数字参数
3. `/trends/:TREND` 的 `duration` 参数会触发 500
4. `/odds/multiple` 返回 HTML，路径或参数格式可能与 Postman 文档有差异
5. `/betslips` 是 POST，不是 GET
6. `/competitions/search` 不在导航栏但确实存在
7. trend 名严格大小写驼峰：`homeWin` 对，`home_win` 错；`btts2H` 末位是大写 H

### 速率与分页
- 全部端点都有 `page`，多数 `per_page` 默认 250（部分 500，如 `/odds/movement`、`/odds/latest`、`/value/*`、`/correctScores`）
- 没看到限速 header；目前调用 ~150ms 间隔无报错。生产环境建议设节流。

---

## 附：测试脚本

完整探测脚本保存在 `/tmp/probe*.py`，可重跑：

```bash
python3 /tmp/probe_all.py   # 一次性测全部 44 个端点
```

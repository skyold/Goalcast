# Sportmonks 数据可用性调查（2026-04-14 / 2026-04-18，英超/英冠/意甲）

创建日期：2026-04-15

## 背景

本报告记录一次针对 Sportmonks 数据源的赛前数据可用性检查结果。当前数据缺失会直接导致赔率/盘口驱动的分析链路不可用，需要作为优先级较高的问题进行排查与修复。

## 范围

- 日期：2026-04-14、2026-04-18
- 联赛：英超（Premier League）、英冠（Championship）、意甲（Serie A）
- 核心层级（layers）：fixtures、xg、standings、lineups、h2h、predictions、odds、asian_handicap、odds_movement

## 复现方法（MCP 调用路径）

- 获取赛程：`goalcast_sportmonks_get_fixtures(date, leagues, warm_if_missing=true)`
- 单场读取：`goalcast_sportmonks_get_match(fixture_id, date, refresh_if_stale=true)`
- 强制刷新：`goalcast_sportmonks_refresh_match(fixture_id, date)`

说明：部分比赛首次读取时 `xg` 可能缺失，但强制刷新后会补齐；因此判断"是否可用"必须以强制刷新后的结果为准。

## 赛程命中情况

- 2026-04-14：共 2 场（均为英冠），英超/意甲为 0 场
- 2026-04-18：共 5 场（英超 1、英冠 3、意甲 1）
- 合计：7 场

### 命中比赛列表（UTC）

| 日期 | 开球时间 | 联赛 | 比赛 | fixture_id |
|---|---:|---|---|---:|
| 2026-04-14 | 19:00:00 | Championship | Portsmouth vs Ipswich Town | 19432056 |
| 2026-04-14 | 19:00:00 | Championship | Southampton vs Blackburn Rovers | 19432284 |
| 2026-04-18 | 11:30:00 | Premier League | Brentford vs Fulham | 19427729 |
| 2026-04-18 | 11:30:00 | Championship | Derby County vs Oxford United | 19432253 |
| 2026-04-18 | 11:30:00 | Championship | Millwall vs Queens Park Rangers | 19432256 |
| 2026-04-18 | 11:30:00 | Championship | Portsmouth vs Leicester City | 19432257 |
| 2026-04-18 | 13:00:00 | Serie A | Udinese vs Parma | 19425210 |

## 关键发现（严重）

### 1) 赔率/盘口层全面缺失（阻断核心链路）

- 7/7：`odds` 为空
- 7/7：`asian_handicap` 为空
- 7/7：`odds_movement` 为空

影响：无法基于赔率/盘口计算 implied probability、EV、Kelly、风险调整 EV 等指标。任何投注推荐都只能退化为"无赔率版"的赛前画像，不能用于实际投注输出。

### 2) xG 层数据可取但存在质量风险（疑似系统性异常）

- 7/7：强制刷新后 `xg` 均返回
- 但出现一致的可疑模式：多个比赛的 `home_xg_for` / `away_xg_for` 为相同负值（示例：-0.032706666666666676），且 `xg_against` 多为 0.0

风险：高概率不是"真实 xG"，而是解析/映射/默认值导致的系统性错误。若直接用于模型，会把错误信号写入快照并造成长期偏差。

### 3) 阵容层对未来赛程不稳定

- 2026-04-14 两场：`lineups` 返回结构占位，但未确认（formation 为空、confirmed=false）
- 2026-04-18 五场：`lineups` 为 null

### 4) 其他层相对稳定

- 7/7：`standings` 可用
- 7/7：`predictions` 可用
- 7/7：`h2h` 可用（多数为空数组，但结构稳定）

## 单场可用性矩阵（强制刷新后）

| 比赛 | fixture_id | xg | standings | lineups | h2h | predictions | odds | asian_handicap | odds_movement |
|---|---:|---|---|---|---|---|---|---|---|
| Portsmouth vs Ipswich Town | 19432056 | 异常 | 可用 | 占位 | 可用 | 可用 | 缺失 | 缺失 | 缺失 |
| Southampton vs Blackburn Rovers | 19432284 | 异常 | 可用 | 占位 | 可用 | 可用 | 缺失 | 缺失 | 缺失 |
| Brentford vs Fulham | 19427729 | 异常 | 可用 | null | 可用 | 可用 | 缺失 | 缺失 | 缺失 |
| Derby County vs Oxford United | 19432253 | 异常 | 可用 | null | 可用 | 可用 | 缺失 | 缺失 | 缺失 |
| Millwall vs Queens Park Rangers | 19432256 | 异常 | 可用 | null | 可用 | 可用 | 缺失 | 缺失 | 缺失 |
| Portsmouth vs Leicester City | 19432257 | 异常 | 可用 | null | 可用 | 可用 | 缺失 | 缺失 | 缺失 |
| Udinese vs Parma | 19425210 | 异常 | 可用 | null | 可用 | 可用 | 缺失 | 缺失 | 缺失 |

## 需要调查的问题清单（按优先级）

### P0：为何 odds / asian_handicap / odds_movement 全缺？

建议排查点：
- Sportmonks API 调用是否缺少必要 include/filters
- 解析逻辑是否兼容当前 v3 数据结构
- 缓存预热/刷新是否实际拉取了赔率相关 endpoint
- 订阅/套餐与 endpoint 是否匹配

### P0：为何 xG 出现统一负值/同值模式？

建议排查点：
- `data_strategy/resolvers/sportmonks_resolver.py` 中映射是否正确
- xG/xGA expected type id 是否与当前数据一致
- participant_id 的筛选与聚合是否正确
- 缺失时的默认值/归一化是否产生负值

### P1：lineups 为 null 是否符合预期？

建议排查点：
- 未来赛程的阵容 endpoint 是否需要不同资源或 include
- 缓存/刷新策略对 lineups 层是否有跳过逻辑

### P1：建立"赛前数据质量闸门"

建议规则：
- 若 `odds` 或 `asian_handicap` 缺失：标记为不可下注
- 若 `xg` 出现明显异常：置空并记录原因，避免污染快照

## 建议的下一步动作

- 在 resolver 层增加 xG 的 sanity check 与回退策略
- 将赔率相关 endpoint 的原始响应与解析结果做一次对照
- 在 MCP 返回中补充更可诊断的元信息

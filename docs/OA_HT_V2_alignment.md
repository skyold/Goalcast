# OA_HT_V2.py 与当前 gs_ht_ev.py 对齐审计

> 文件 `docs/OA_HT_V2.py`(作者原始脚本)与
> `backend/services/signals/gs_ht_ev.py`(信号化版本)逐项对照。
>
> 当前状态(2026-05-19):**已 revert 公式回到 V2 同源**(本地改动,**尚未
> commit**),待作者审阅。
>
> 评分标准:
> - ✅ **同** — 数学 / 数据 / 行为完全一致
> - ⚠️ **不同(可解释)** — 因为信号管线与 CLI 脚本天然不同,做了等价改造
> - ❓ **不同(请作者确认)** — 不一致,需要决定要不要对齐
> - ➖ **N/A** — CLI 特有 / 信号管线无对应概念

---

## 1. EV 反推公式(数学核心)

| | OA_HT_V2.py | gs_ht_ev.py | 评分 |
|---|---|---|---|
| 输入 | `ht_h, ht_a`(0-100 整数百分比) | 同 | ✅ |
| de-vig | `eff_h = rH / (rH + rA)`<br>`eff_a = rA / (rH + rA)` | 同 | ✅ |
| EV 5% 主队 | `hk_h5 = (0.05 + eff_a) / eff_h` | 同 | ✅ |
| EV 28% 主队 | `hk_h28 = (0.28 + eff_a) / eff_h` | 同 | ✅ |
| EV 5% 客队 | `hk_a5 = (0.05 + eff_h) / eff_a` | 同 | ✅ |
| EV 28% 客队 | `hk_a28 = (0.28 + eff_h) / eff_a` | 同 | ✅ |

**数值验证** —— 用 HT 1X2 = 42/28/30 跑两边:

|  | OA_HT_V2.py 期望 | gs_ht_ev.py 实测(刚 revert 后) |
|---|---|---|
| hk_h5  | 0.800 | 0.800 ✅ |
| hk_h28 | 1.194 | 1.194 ✅ |
| hk_a5  | 1.520 | 1.520 ✅ |
| hk_a28 | 2.072 | 2.072 ✅ |

**核心 EV 公式 100% 对齐**。

---

## 2. AH 主盘选择

| | OA_HT_V2.py (line 81-132) | gs_ht_ev.py | 评分 |
|---|---|---|---|
| 数据源 | OA `/odds/history/{fx_id}` API 实时拉 | `historical_odds` 表(snapshot 管线已写) | ⚠️ 不同(可解释) |
| market 过滤 | `market_key == "asian_handicap"` | `market_id == 51`(同义,只是字段名不同) | ✅ 等价 |
| Bookmaker 优先级 | **BET365(2) → Pinnacle(1) → 1xBet(3)** | BET365(2) → Pinnacle(1)<br>**❌ 没有 1xBet fallback** | ❓ **不同,请作者确认** |
| 主盘判定 | "两边赔率差最小" | 同 | ✅ |
| **赔率范围约束** | **`0.6 ≤ h ≤ 2.5 AND 0.6 ≤ a ≤ 2.5`**(line 119) | **❌ 没有此约束**,只要 `o > 0` | ❓ **不同,请作者确认** |
| 用哪个赔率字段 | `item.get("opening")`(开盘价) | `historical_odds.odds`(对应 snapshot 时点的 current 价) | ⚠️ 不同(数据架构差异) |
| 让球值解析 | `parse_line_value("m025") → -0.25` 自实现 | `services/ah.py:parse_ah_outcome_line` (正则版,语义等价) | ⚠️ 不同(实现等价) |

### ❓ 需要作者确认的两点

**A. 1xBet (bookmaker_id=3) 第三 fallback**
- OA 脚本里写了 `for bk_id in [2, 1, 3]`,我们漏了 3
- 影响:BET365 和 Pinnacle 都缺数据的极少数 fixture 会"信号不出",而 OA 脚本能用 1xBet 救一下
- **现实里**:`historical_odds` 当前只 sync `bookmaker_id in (1, 2)`(`oddalerts.py:get_odds_latest` 默认 `bookmakers="1,2"`),所以加 1xBet 也没数据可用
- **修法**:在 snapshot 管线加 1xBet 数据 + signal 优先级加 3。要不要做?

**B. `0.6 ≤ odds ≤ 2.5` 范围约束**
- OA 脚本只在两边赔率都落在 [0.6, 2.5] 内的 line 才考虑作为主盘
- 用意是过滤极端价(对方让球太多 → 赔率超 2.5 或低于 0.6 = 那条 line 已经不是主流)
- **影响**:某些 fixture 现在能被信号"捡到主盘"但 OA 脚本会跳过
- **修法**:在 `_derive_main_line_from_history` 加这层约束。**应该加,因为这是 V2 主盘选择算法的一部分。**

### ⚠️ 已记录的可解释差异

**C. opening vs current 赔率**
- OA 脚本拉 `opening`(开盘价快照,OA API 提供)
- 我们 `historical_odds.odds` 存的是该 waypoint 时点的 `current` 值
- 信号管线没有"开盘价"这个数据,我们只有 5 个 waypoint(48h/24h/6h/1h/kickoff)的快照
- **影响**:在 T-48h waypoint 时算的 HT 平手盘水位,跟 OA 脚本"刚开盘那一刻的水位"会差一点
- **改的话**需要扩 snapshot 管线存 opening,工作量大。**建议:不动,作为可接受的架构差异**。

---

## 3. AH 范围过滤(信号触发条件)

| | OA_HT_V2.py (line 163-177) | gs_ht_ev.py | 评分 |
|---|---|---|---|
| 触发范围 | `v in {0, ±0.25, ±0.5}` | `_AH_LABEL_BY_LINE` 字典完全一致 | ✅ |
| 标签命名 | 中文 "平手(0)" / "平半(-0.25)" 等 | 英文 "draw"/"draw_half_home" 等 | ⚠️ 等价(国际化处理) |

**触发逻辑 100% 对齐**。

---

## 4. HT 1X2 概率源

| | OA_HT_V2.py | gs_ht_ev.py | 评分 |
|---|---|---|---|
| 数据源 | OA `/fixtures/upcoming?include=probability` 实时拉,取 `probability.{home_win_ht, draw_ht, away_win_ht}` | `historical_predictions.{home_win_ht_pct, draw_ht_pct, away_win_ht_pct}`(snapshot 管线在 sync_fixtures_upcoming 时已写入) | ⚠️ 不同(架构等价) |
| 值范围 | 0-100 整数百分比 | 同 | ✅ |
| 缺数据处理 | `if ht_h is None ... return None`(line 256) | 同 | ✅ |

**架构差异**:OA 脚本实时拉 OA API,信号管线靠 snapshot 把同样的数据**预拉到本地表**。**数据语义一致**,但快照时点不同。

---

## 5. Strength 归一化

| | OA_HT_V2.py | gs_ht_ev.py | 评分 |
|---|---|---|---|
| 原脚本 | **没有 strength 概念**(只是 CLI 打印 EV 区间) | `min(2 · |eff_home − 0.5|, 1.0)` | ➖ N/A |

**OA 脚本没有 strength 输出**(它只是 CLI 给人看的)。`gs_ht_ev.py` 加了 strength 是因为 signals 框架要求每个信号必须有 strength ∈ [0, 1] 供跨信号排序。

**这个 strength 公式是 gs_ht_ev 自创的**,OA_HT_V2.py 里没有依据。如果作者有偏好的 strength 公式,请反馈。

---

## 6. 输出结构

| | OA_HT_V2.py | gs_ht_ev.py | 评分 |
|---|---|---|---|
| 形式 | CLI `print(f"H:{hk_h5:.2f}-{hk_h28:.2f}")` 控制台打印 | `value_json` JSON 入库 | ⚠️ 必然不同 |
| 含的水位 | `hk_h5 / hk_h28 / hk_a5 / hk_a28`(4 个数) | 同 4 个 | ✅ |
| 附加字段 | 无 | `ah_line, ah_label, ht_*_pct, eff_*, selection` | ⚠️ gs_ht_ev 多输出几个供消费 |

**额外字段评估**:`gs_ht_ev` 的 value_json 多了 `selection`(model 倾向哪边)、`eff_home/eff_away`(de-vigged 概率)、`ht_*_pct`(原始概率)。这些都是 OA 脚本内部算了但没打印出来的中间值,前端 / 回测能用到所以我们暴露了。**没引入新概念,只是把中间变量也输出了**。请作者确认这些字段名 OK。

---

## 7. 时间窗 / 比赛日概念

| | OA_HT_V2.py | gs_ht_ev.py | 评分 |
|---|---|---|---|
| 比赛日定义 | "上海时间 target_date 12:00 ~ 次日 12:00"(line 339-347) | **无**,信号在 snapshot 管线每个 waypoint(48h/24h/6h/1h/kickoff)都重算 | ➖ N/A |

**OA 脚本**是个手动工具:输入日期 → 拉那一天的比赛 → 看输出。
**gs_ht_ev 信号**是 snapshot 管线的一部分:每个 fixture 在每个 waypoint 都自动算一次,落到 `signals_snapshot` 表。

时间窗的概念不一样,但**信号本身的计算逻辑没变**(对同一组 HT 概率 + AH 主盘,数学结果完全一致)。如果作者想做"赛前 12:00 起轮询触发"这种逻辑(之前 KEN-HT-EV 限价单 MVP 反馈),那是模拟盘 / 触发器的事,不在信号本身。

---

## 8. predictability / 联赛过滤

| | OA_HT_V2.py | gs_ht_ev.py | 评分 |
|---|---|---|---|
| 联赛过滤 | CLI 让用户选联赛 → 该联赛比赛单独显示 | 信号对所有 fixture 都算,前端 catalog 显示时不按联赛过滤 | ⚠️ 等价不同表现 |
| `predictability` 字段 | 显示星级 ★(low/good/great)但不过滤 | 同 — 信号本身不过滤 | ✅ |

---

# 总结 —— 作者答复(2026-05-19)

| # | 项目 | 作者答复 | 处理 |
|---|---|---|---|
| **A** | bookmaker fallback 加 1xBet(3) | **不需要一致** — 保持只用 BET365 + Pinnacle | ✓ 不动 |
| **B** | 主盘选择加 `0.6 ≤ odds ≤ 2.5` 约束 | **需要加** | ✅ 已加(`_derive_main_line_from_history`) + 2 个新测试覆盖 |
| **C** | strength 公式 `min(2·|eff_h − 0.5|, 1.0)` | **可以保留** | ✓ 不动 |

**其他所有项目**(EV 数学、AH 范围过滤、HT 1X2 数据语义、输出含的水位数字)**完全一致**。

---

## 最终对齐状态(B 加完后)

| 维度 | 状态 |
|---|---|
| EV 公式(de-vigged 2-way) | ✅ 完全一致 |
| `hk_h5 / hk_h28 / hk_a5 / hk_a28` 数值 | ✅ 42/28/30 用例:0.800 / 1.194 / 1.520 / 2.072 |
| AH 触发范围 `{0, ±0.25, ±0.5}` | ✅ 完全一致 |
| 主盘选择"两边赔率差最小 + 0.6-2.5 范围" | ✅ **已对齐**(B) |
| Bookmaker 优先级 BET365 → Pinnacle | ✅ 一致(忽略 1xBet,作者认可) |
| HT 1X2 概率源 | ⚠️ 来源不同(snapshot 表 vs OA API),数据语义一致 |
| `opening` vs `current` 赔率 | ⚠️ 来源不同,架构差异 |
| Strength | ➖ V2 没有此概念,gs_ht_ev 自创公式(作者认可) |

---

**接下来动作**:
1. ✅ B 加范围过滤(已做)
2. ✅ 清掉 `OA_HT_V2.py` 我加的 ⚠ BUG 警告(已做)
3. ⏳ Commit + push + merge to master
4. ⏳ 服务器 `docker compose exec backend python -m scripts.seed_methodology`
   刷新方法论文案
5. ⏳ 触发一次 snapshot 重算让本地 KEN-HT-EV 信号用新规则
   (可选: `DELETE FROM signals_snapshot WHERE signal_type='GS-KEN-HT-EV';`
   下个 15 min snapshot tick 自动重建)

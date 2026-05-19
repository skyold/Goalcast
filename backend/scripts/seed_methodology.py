"""Seed `signal_methodology` with markdown bodies for every REGISTERED signal,
in zh and en. Idempotent: re-running updates `body_md` + `updated_at` via UPSERT.

Usage:
    cd backend && .venv/bin/python -m scripts.seed_methodology

Methodology bodies are authored here (Python multi-line strings) rather than
in separate .md files because: (a) only ~8 bodies × ~30 lines each = ~250 lines
total — manageable inline; (b) keeps the seed atomic and reviewable as one diff;
(c) future admin UI (V2) will replace this script entirely.

See docs/PRD/signal-catalog-and-subscriptions.prd.md Q1 for why文案 lives in DB
rather than static frontend constants.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import aiosqlite

from database import _db_path, init_db


# {signal_type: {locale: body_md}}
METHODOLOGY: dict[str, dict[str, str]] = {
    "GS-Mispricing": {
        "zh": """\
## 计算原理

对每场比赛在每个 waypoint 比较 **模型概率** 与 **市场 de-vig 后的隐含概率**,
取三档(home/draw/away)中绝对值最大的那一档作为信号方向。

### 输入

- `historical_predictions.home_win_pct / draw_pct / away_win_pct`
  来自 Goalcast OA 模型对该场的 Monte Carlo 模拟结果。
- `historical_odds` 中 `bookmaker_id=1` (Pinnacle), `market_id=6` (1X2) 的三档赔率。

### De-vig 公式

```
raw_sum = 1/o_home + 1/o_draw + 1/o_away
implied_pct[sel] = (1/o_sel) / raw_sum * 100
```

去掉 Pinnacle 抽水后得到的隐含概率,与模型概率作差:

```
delta[sel] = model_pct[sel] - implied_pct[sel]
selection  = argmax(|delta|)
```

### Strength 归一化

`min(|delta_pct| / 10.0, 1.0)` —— |Δ| 达到 10pp 时 strength=1.0。

### 何时使用

模型与市场在某一面分歧大,意味着至少有一方错了。如果你**长期相信模型**,这是
正 EV 入场点;如果你**长期相信市场**,这是模型需要修正的样本。

### 何时不使用

- Pinnacle 三档不全(de-vig 需要全部三档)→ 信号不出
- `delta` 接近 0 → 模型与市场一致,无可比性
- 极小联赛(predictability=poor)→ 模型可能本身不准
""",
        "en": """\
## How it computes

For each fixture at each waypoint, compare **model probability** with
**market de-vigged implied probability** across the three 1X2 outcomes;
emit the selection with the largest |Δ|.

### Inputs

- `historical_predictions.home_win_pct / draw_pct / away_win_pct`
  — Goalcast OA model Monte Carlo output for that fixture.
- `historical_odds` rows with `bookmaker_id=1` (Pinnacle), `market_id=6` (1X2).

### De-vig formula

```
raw_sum = 1/o_home + 1/o_draw + 1/o_away
implied_pct[sel] = (1/o_sel) / raw_sum * 100
```

This strips Pinnacle's vig from the prices, then:

```
delta[sel] = model_pct[sel] - implied_pct[sel]
selection  = argmax(|delta|)
```

### Strength normalisation

`min(|delta_pct| / 10.0, 1.0)` — a 10pp gap caps at 1.0.

### When to use

When model and market disagree noticeably on an outcome, one of them is wrong.
If you **trust the model long-term**, this is a +EV entry point; if you trust
the market, these samples flag where the model needs correction.

### When NOT to use

- Pinnacle 1X2 incomplete (de-vig needs all three) → no signal
- |Δ| close to 0 → model and market agree, nothing to compare
- Tiny leagues (`predictability='poor'`) — model may be unreliable on its own
""",
    },
    "GS-LineMove": {
        "zh": """\
## 计算原理

跟踪 Pinnacle 1X2 赔率从**最早 waypoint** 到**当前 waypoint** 的百分比漂移,
取三档中绝对值最大的那一面作为信号方向。

### Waypoint 顺序

```
48h → 24h → 6h → 1h → kickoff
```

"开盘 waypoint" = `historical_odds` 中**最早一个**三档都齐的 waypoint;
不一定是 48h —— OA 拉数据时间窗有时从 24h 才开始。

### 公式

```
move_pct[sel] = (current_odds[sel] - open_odds[sel]) / open_odds[sel] * 100
selection     = argmax(|move_pct|)
```

### Strength 归一化

`min(|move_pct| / 20.0, 1.0)` —— 20pp 漂移时 strength=1.0。

### 信号含义

- `move_pct < 0` (赔率下降) = sharp money 流入该 selection,**正向信号**
- `move_pct > 0` (赔率上升) = 资金离开该 selection,**反向信号**

### 何时不使用

- 找不到比当前更早的、三档完整的 waypoint → 信号不出
- 开盘 = 当前(同一 waypoint)→ 信号不出
- 漂移幅度小(< 5%)→ 多半是 market microstructure 噪音,不构成信号
""",
        "en": """\
## How it computes

Tracks Pinnacle 1X2 odds drift from the **earliest waypoint** to the **current
waypoint**, emitting the selection with the largest |move_pct|.

### Waypoint ordering

```
48h → 24h → 6h → 1h → kickoff
```

The "opening waypoint" is the **earliest** waypoint in `historical_odds` with
all three 1X2 outcomes — not necessarily 48h (OA backfill windows sometimes
start at 24h).

### Formula

```
move_pct[sel] = (current_odds[sel] - open_odds[sel]) / open_odds[sel] * 100
selection     = argmax(|move_pct|)
```

### Strength normalisation

`min(|move_pct| / 20.0, 1.0)` — 20pp move caps at 1.0.

### Reading the sign

- `move_pct < 0` (odds dropping) = sharp money on that selection, **positive signal**
- `move_pct > 0` (odds rising)   = money leaving that selection, **negative signal**

### When NOT to use

- No earlier complete-three-outcomes waypoint → no signal
- Opening == current (same waypoint) → no signal
- Tiny moves (< 5%) — likely market microstructure noise, not a real signal
""",
    },
    "GS-SharpSquare": {
        "zh": """\
## 计算原理

比较 **Pinnacle** (sharp book) 与 **Bet365** (square book) 在同一场比赛 1X2
de-vig 后的隐含概率,取最大分歧那一面作为信号方向。

### 输入

- `historical_odds` 中 `market_id=6` (1X2):
  - `bookmaker_id=1` = Pinnacle (sharp)
  - `bookmaker_id=2` = Bet365 (square)

### 公式

对两家分别做 de-vig:

```
for book in (pinnacle, bet365):
    raw_sum     = 1/o_home + 1/o_draw + 1/o_away
    pct[book][sel] = (1/o_sel) / raw_sum * 100

delta[sel] = pct[pinnacle][sel] - pct[bet365][sel]
selection  = argmax(|delta|)
```

### Strength 归一化

`min(|delta_pct| / 10.0, 1.0)` —— 10pp 分歧时 strength=1.0。

### 信号含义

- Pinnacle 接受 sharp money 但严格风控,被视为"市场真实价";
- Bet365 服务零售用户,价格倾向于反映**大众情绪**。
- 两者分歧大 → 大众情绪与 sharp 看法不一致,sharp 边通常正确。

`delta > 0` 这一面 = Pinnacle 比 Bet365 更看好 → 跟 sharp。

### 何时不使用

- 任一书商三档不全 → 信号不出
- 分歧 < 3pp → 噪音
""",
        "en": """\
## How it computes

Compares **Pinnacle** (sharp book) vs **Bet365** (square book) de-vigged 1X2
implied probabilities, emitting the selection with the largest disagreement.

### Inputs

- `historical_odds` rows with `market_id=6` (1X2):
  - `bookmaker_id=1` = Pinnacle (sharp)
  - `bookmaker_id=2` = Bet365 (square)

### Formula

De-vig each book independently:

```
for book in (pinnacle, bet365):
    raw_sum     = 1/o_home + 1/o_draw + 1/o_away
    pct[book][sel] = (1/o_sel) / raw_sum * 100

delta[sel] = pct[pinnacle][sel] - pct[bet365][sel]
selection  = argmax(|delta|)
```

### Strength normalisation

`min(|delta_pct| / 10.0, 1.0)` — 10pp disagreement caps at 1.0.

### Reading the sign

- Pinnacle takes sharp money with strict risk management → "true market price"
- Bet365 caters to retail → prices reflect **public sentiment**
- Large divergence means retail and sharp disagree; sharp tends to be right

`delta > 0` side = Pinnacle more bullish than Bet365 → follow the sharp.

### When NOT to use

- Either book's 1X2 is incomplete → no signal
- |delta| < 3pp — noise
""",
    },
    "GS-KEN-HT-EV": {
        "zh": """\
## 计算原理

OA_HT_V2 工具的信号化版本。只在 **FT 主盘 AH 落在 {0, ±0.25, ±0.5}** 区间
(即"平手 / 平半 / 半球")时触发,利用模型给出的 **HT 1X2 概率**,反推
"上半场平手盘"在 EV=5% / EV=28% 时的应得 HK 赔率区间。

### 输入

- `historical_predictions.home_win_ht_pct / draw_ht_pct / away_win_ht_pct`
  —— OA `/fixtures/upcoming?include=probability` 的 HT 1X2 分布。
- `historical_odds` 中 `market_id=51` (AH) 行,优先 `bookmaker_id=2` (BET365),
  fallback 到 `bookmaker_id=1` (Pinnacle)。

### AH 主盘选择

对每个书商,在所有 AH 让球档位中,选两边赔率差最小的那一档作为主盘。
主盘让球值必须落在 `{0, ±0.25, ±0.5}` 才触发,否则信号不出。

### EV 反推 (上半场平手盘)

```
rH, rA  = ht_home_pct / 100, ht_away_pct / 100
eff_h   = rH / (rH + rA)        # 2-way de-vig (去掉 HT 平局)
eff_a   = rA / (rH + rA)
hk_h_ev = (ev + eff_a) / eff_h  # HT 平手盘主队 EV 对应 HK 赔率
hk_a_ev = (ev + eff_h) / eff_a  # HT 平手盘客队 EV 对应 HK 赔率
```

`hk_*_5` = EV 5% 时, `hk_*_28` = EV 28% 时。市场实际赔率 ≥ 该值 = +EV。

### Strength 归一化

`min(2 * |eff_home - 0.5|, 1.0)` —— 平势 = 0,一边倒 = 1。strength 反映的是
模型对 HT 走势的把握度,不是 EV 本身。

### 何时不使用

- FT 主盘不在 ±0.5 区间内 → 信号不出 (比赛太不均势,EV 公式失真)
- HT 1X2 概率任一缺失 → 信号不出
- 两家主流书商都缺 AH 行 → 信号不出
- 注意:**只用于 HT 平手盘 (line=0) 这一具体投注品种**,与其他 AH 让球不可
  类推
""",
        "en": """\
## How it computes

A signal-ified port of the OA_HT_V2 tool. Fires only when the **FT main AH
line** lands in `{0, ±0.25, ±0.5}` (i.e. "draw / draw-half / half-ball"),
using the model's **HT 1X2 probabilities** to reverse-derive Hong Kong odds
for the **first-half draw AH (line=0)** at EV=5% and EV=28%.

### Inputs

- `historical_predictions.home_win_ht_pct / draw_ht_pct / away_win_ht_pct`
  — OA `/fixtures/upcoming?include=probability` HT 1X2 distribution.
- `historical_odds` rows with `market_id=51` (AH), preferring
  `bookmaker_id=2` (BET365), falling back to `bookmaker_id=1` (Pinnacle).

### Main AH line selection

For each bookmaker, scan all AH handicaps and pick the one with smallest
two-side odds gap. The home-perspective line must land in `{0, ±0.25, ±0.5}`
or no signal fires.

### EV reverse-derivation (HT draw line)

```
rH, rA  = ht_home_pct / 100, ht_away_pct / 100
eff_h   = rH / (rH + rA)        # 2-way de-vig (drop HT draw)
eff_a   = rA / (rH + rA)
hk_h_ev = (ev + eff_a) / eff_h  # HK odds for HT draw AH home at EV
hk_a_ev = (ev + eff_h) / eff_a  # HK odds for HT draw AH away at EV
```

`hk_*_5` = EV 5%, `hk_*_28` = EV 28%. Market odds ≥ these = +EV bet.

### Strength normalisation

`min(2 * |eff_home - 0.5|, 1.0)` — coin flip = 0, dominant side = 1. Strength
reflects model conviction on HT trajectory, not the EV itself.

### When NOT to use

- FT main AH outside ±0.5 — match too lopsided, EV formula breaks down
- Any HT 1X2 column NULL → no signal
- Both major books missing AH rows → no signal
- Note: applies **only to the HT draw AH (line=0)** specifically; do not
  extrapolate to other handicap lines
""",
    },
}


async def seed_methodology() -> None:
    await init_db()
    now = datetime.now(timezone.utc).isoformat()
    written = 0
    async with aiosqlite.connect(_db_path()) as db:
        for signal_type, locales in METHODOLOGY.items():
            for locale, body_md in locales.items():
                await db.execute(
                    """INSERT INTO signal_methodology
                         (signal_type, locale, body_md, updated_at)
                       VALUES (?, ?, ?, ?)
                       ON CONFLICT(signal_type, locale) DO UPDATE SET
                         body_md    = excluded.body_md,
                         updated_at = excluded.updated_at""",
                    (signal_type, locale, body_md, now),
                )
                written += 1
        await db.commit()
    print(f"seed_methodology: upserted {written} rows ({len(METHODOLOGY)} signals × locales)")


if __name__ == "__main__":
    asyncio.run(seed_methodology())

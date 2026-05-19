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
## 这个信号在做什么?

简单说:**对比模型预测的胜平负概率,跟博彩公司报价折算的概率,差距最
大的那一面就是这个信号**。

- 差距是**正的** = 模型比市场更看好这边(市场低估了这边)
- 差距是**负的** = 模型比市场没那么看好(市场高估了)

如果你长期相信模型预测,**正差距 = 入场点**(数学上有优势);
反过来,**负差距 = 模型可能错了的地方**(模型需要复盘)。

## 什么时候出信号?

一场比赛要同时满足:

- OA 模型给出了三档(主胜/平/客胜)预测概率
- Pinnacle(主流博彩公司)有这场的三档赔率挂着

少任何一项就不出。

## 怎么看输出的数字

| 字段 | 意思 |
|---|---|
| `selection` | 模型 vs 市场分歧最大的那一面(home / draw / away) |
| `delta_pct` | 差距是几个百分点(可正可负) |

**例子**:模型预测主胜 55%、市场报价折算只有 47% → 信号会说"主胜
差距 +8pp",意思:市场对主胜的报价**便宜了 8 个百分点**。

## Strength 是什么?

`min(|delta_pct| / 10, 1.0)` —— 差距越大 strength 越高,10pp 封顶。

- 差距 5pp → strength 0.5
- 差距 10pp+ → strength 1.0

## 什么时候不该跟

- Pinnacle 三档不全(数据缺失)→ 信号不出
- 差距小于 3pp → 噪音范围,不要追
- 极小联赛 / 杯赛(predictability=poor):模型本身可能不准
- **信号不是"必须下单"**。差距大只说明模型 vs 市场不一致,谁对要
  长期 ROI 验证
""",
        "en": """\
## What this signal does

In short: **compares the model's 1X2 probability with the market's
odds-implied probability; the side with the largest gap is the signal**.

- **Positive gap** = model more bullish than market (market under-priced)
- **Negative gap** = model less bullish than market (market over-priced)

If you trust the model long-term, **positive gap = entry point**
(mathematical edge); conversely, **negative gap = where the model may
be wrong** (worth a review).

## When does it fire?

Both required:

- OA model has 1X2 probability prediction (home/draw/away)
- Pinnacle has 1X2 odds posted for this match

Either missing → no signal.

## How to read the numbers

| Field | Meaning |
|---|---|
| `selection` | side with largest model-vs-market gap (home/draw/away) |
| `delta_pct` | gap size in percentage points (signed) |

**Example**: model predicts home 55%, market odds-implied is only 47%
→ signal reads "home gap +8pp", meaning the market **under-priced
home by 8 percentage points**.

## What does Strength mean?

`min(|delta_pct| / 10, 1.0)` — wider gap, higher strength, capped at 10pp.

- 5pp gap → strength 0.5
- 10pp+ gap → strength 1.0

## When NOT to follow

- Pinnacle 1X2 incomplete → no signal
- Gap < 3pp → noise range, don't chase
- Tiny leagues / cup matches (predictability=poor) → model itself may
  be unreliable
- **Signal ≠ "must bet"**. Large gap means "model and market disagree";
  who's right requires long-term ROI verification
""",
    },
    "GS-LineMove": {
        "zh": """\
## 这个信号在做什么?

简单说:**监控 Pinnacle 三档赔率从开盘到当前的变化,变化最大的那一
面就是信号**。

- 赔率**下降** = **钱流入**这一面(sharp money,庄家在收紧)
- 赔率**上升** = **钱流出**这一面

Pinnacle 接受 sharp 资金,所以 line move 通常反映"专业玩家在哪边"。

## 什么时候出信号?

两个都要:

- 这场比赛有比当前更早的 waypoint(48h / 24h / 6h / 1h 中至少一个)
  且三档赔率完整
- 当前 waypoint 三档也完整

如果刚开盘信号还没动(开盘 = 当前),不出。

## 怎么看输出的数字

| 字段 | 意思 |
|---|---|
| `selection` | 漂移幅度最大那一面(home/draw/away) |
| `move_pct` | 漂移百分比(可正可负);负数 = 赔率下降 = sharp 看好 |
| `open_odds` / `current_odds` | 开盘价 vs 当前价 |

**例子**: `{selection: "home", move_pct: -15%, open_odds: 2.50,
current_odds: 2.12}` — 主胜从 2.50 跌到 2.12(跌 15%),sharp 资金
在主胜这边。

## Strength 是什么?

`min(|move_pct| / 20, 1.0)` —— 20pp 漂移封顶 strength=1.0。

- 漂移 10% → strength 0.5
- 漂移 20%+ → strength 1.0

## 什么时候不该跟

- 漂移 < 5% → 噪音,可能就是 market microstructure
- 临近开赛的剧烈 line move 可能是新闻驱动(伤病 / 阵容),**不是
  sharp alpha**
- 大热门 / 高流动性比赛,信号噪音多
- 信号反映**已经发生的资金流向**,不是"未来怎么走"。**跟单要早,
  不要追**
""",
        "en": """\
## What this signal does

In short: **monitors Pinnacle 1X2 odds movement from opening to now;
the side with the largest swing is the signal**.

- Odds **dropping** = **money flowing in** to this side (sharp money,
  book tightening)
- Odds **rising** = **money flowing out**

Pinnacle takes sharp action, so line moves typically reveal "where
professional money is".

## When does it fire?

Both required:

- An earlier waypoint (48h/24h/6h/1h) has complete 1X2 odds
- The current waypoint also has complete 1X2 odds

Open == current waypoint (just opened, no movement yet) → no signal.

## How to read the numbers

| Field | Meaning |
|---|---|
| `selection` | side with the biggest swing (home/draw/away) |
| `move_pct` | swing percentage (signed); negative = odds dropping = sharp bullish |
| `open_odds` / `current_odds` | opening price vs current price |

**Example**: `{selection: "home", move_pct: -15%, open_odds: 2.50,
current_odds: 2.12}` — home dropped from 2.50 to 2.12 (-15%), sharp
money on home.

## What does Strength mean?

`min(|move_pct| / 20, 1.0)` — 20pp swing caps strength at 1.0.

- 10% move → strength 0.5
- 20%+ move → strength 1.0

## When NOT to follow

- Swing < 5% → noise, could be market microstructure
- Sudden big swing near kickoff may be news-driven (injuries, lineups),
  **not sharp alpha**
- High-volume / hot matches → signal-to-noise low
- The signal reflects **money flows already in**, not "where it's
  going next". **Follow early, don't chase**
""",
    },
    "GS-SharpSquare": {
        "zh": """\
## 这个信号在做什么?

简单说:**对比 Pinnacle(sharp 庄家)和 BET365(零售庄家)对同一场
比赛的胜平负看法,分歧最大的那一面就是信号**。

- **Pinnacle** 接受大额、价格反映 sharp 资金的真实判断
- **BET365** 限制大额、价格更多反映**散户情绪**

两家分歧大 = 专业玩家跟大众看法不一致,**通常 sharp 那边是对的**。

## 什么时候出信号?

两家**都必须**有这场的三档赔率挂着。任何一家缺一档就不出信号。

## 怎么看输出的数字

| 字段 | 意思 |
|---|---|
| `selection` | 两家分歧最大那一面(home/draw/away) |
| `delta_pct` | Pinnacle 看法 − BET365 看法(百分点,可正可负) |
| `pinnacle_pct` / `bet365_pct` | 两家折算的隐含概率 |

**例子**: `{selection: "draw", delta_pct: +6pp, pinnacle_pct: 28%,
bet365_pct: 22%}` — Pinnacle 给平局 28%,BET365 只给 22%,Pinnacle
**多看好平局 6 个百分点**。

**`delta_pct > 0` 这一面** = Pinnacle 比 BET365 更看好 → **跟 sharp**。

## Strength 是什么?

`min(|delta_pct| / 10, 1.0)` —— 10pp 分歧封顶。

- 分歧 5pp → strength 0.5
- 分歧 10pp+ → strength 1.0

## 什么时候不该跟

- 任一家三档不全 → 信号不出
- 分歧 < 3pp → 噪音
- 信号告诉你"两家分歧",**不直接告诉你赔率是多少**。具体下单还要看
  当时市场实际报价
""",
        "en": """\
## What this signal does

In short: **compares Pinnacle (sharp book) vs BET365 (retail book) 1X2
implied probabilities; the side with the biggest gap is the signal**.

- **Pinnacle** takes sharp action; prices reflect real sharp judgement
- **BET365** limits big bets; prices reflect **retail sentiment**

Large gap = pros disagree with the public; **sharp side usually wins
long-term**.

## When does it fire?

Both books **must** have all three 1X2 outcomes posted. Either book
missing any outcome → no signal.

## How to read the numbers

| Field | Meaning |
|---|---|
| `selection` | side with the biggest disagreement (home/draw/away) |
| `delta_pct` | Pinnacle's view minus BET365's view (signed pp) |
| `pinnacle_pct` / `bet365_pct` | de-vigged implied probability per book |

**Example**: `{selection: "draw", delta_pct: +6pp, pinnacle_pct: 28%,
bet365_pct: 22%}` — Pinnacle gives draw 28%, BET365 only 22% — Pinnacle
**is 6pp more bullish on draw**.

**Positive `delta_pct` side** = Pinnacle more bullish than BET365 →
**follow the sharp**.

## What does Strength mean?

`min(|delta_pct| / 10, 1.0)` — 10pp disagreement caps strength.

- 5pp gap → strength 0.5
- 10pp+ gap → strength 1.0

## When NOT to follow

- Either book's 1X2 incomplete → no signal
- Gap < 3pp → noise
- The signal tells you "books disagree", **not what odds to bet at**.
  Actual bet decision still needs the current market price
""",
    },
    "GS-KEN-HT-EV": {
        "zh": """\
## 这个信号在做什么?

简单说:**根据模型对上半场各种结果的概率预测,告诉你 HT 平手盘(上
半场让球 0)市场赔率给到多少才有数学优势(EV)**。

输出 4 个 HK 赔率水位:**下线**(5% EV,刚刚开始值得跟)和**上线**
(28% EV,非常值钱)。市场实际报价越接近上线越好。

## 什么时候出信号?

一场比赛要同时满足两个条件:

1. **全场让球盘是均势盘**:平手 0、平半 ±0.25、半球 ±0.5 这五档之
   一。如果一边强势让 1 球以上,模型本身就不靠谱,不出信号。
2. **数据齐全**:OA 模型给了上半场胜平负概率,主流博彩公司(BET365
   或 Pinnacle)有上半场让球的真实赔率挂着。

## AH 主盘选择(自动)

对每个书商,主盘按两步选:

1. **候选过滤**:只保留两边赔率**都在 `[0.6, 2.5]` 区间**的让球档位
   (过滤掉极端让球,赔率会跑到 5.0+ 或 0.3-,不该当主盘看)
2. **候选中选差最小**:挑两边赔率差最小的那一档作为主盘

## 怎么看输出的 4 个数字

```
押主队 HT 让球: 下线 0.80 HK ~ 上线 1.19 HK
押客队 HT 让球: 下线 1.52 HK ~ 上线 2.07 HK
```

**使用方法**:
- 市场实际 HK 赔率 **< 下线** → 别下,赔率不够补胜率
- **下线 ~ 上线之间** → 可考虑,有数学优势但不大
- **≥ 上线** → 非常值钱,可能是市场反应慢

## 一个具体例子

模型对一场比赛 HT 概率预测:**主胜 42% / 平 28% / 客胜 30%**。

| 选哪边 | 下线赔率 (5% EV) | 上线赔率 (28% EV) |
|---|---|---|
| 押主队 HT 让球 | 0.80 HK | 1.19 HK |
| 押客队 HT 让球 | 1.52 HK | 2.07 HK |

意思:押主队这边,市场至少要给 0.80 你才有 5% 数学优势;到了 1.19
就是 28% 大优势。押客队那边水位更高(因为模型认为主队稍占上风,
客队赔率自然要更厚才划算)。

## Strength 是什么?

`min(2 * |eff_home - 0.5|, 1.0)` —— 衡量**模型对 HT 走势的把握程度**
(主客 HT 概率差距)。

- 主客势均力敌 → strength 接近 0
- 主客一边倒 → strength 接近 1

**重要**:strength 高 ≠ EV 高。strength 只反映模型的信心,赔率水位
才反映 EV。

## 什么时候不该跟

- 全场让球超过 ±0.5 → 模型本身不出信号
- 模型没给上半场概率 → 数据缺失
- 两家博彩公司都没上半场 AH 赔率 → 没参照
- **只用于 HT 平手盘 (line=0)**,不能套到 -0.5 / -1 等其他让球
- 模型概率是估算,不是真理 —— 跟不跟还要看你对模型的信任度
""",
        "en": """\
## What this signal does

In short: **based on the model's first-half probability prediction,
this signal tells you what Hong Kong odds the market needs to offer
on the HT-平手盘 (first-half handicap 0) for you to have a math edge (EV)**.

Outputs 4 HK odds water lines: **lower bound** (5% EV, just starting
to be worthwhile) and **upper bound** (28% EV, exceptional value). The
closer market odds get to the upper bound, the more valuable.

## When does it fire?

A fixture must satisfy both:

1. **Full-match handicap is balanced**: line 0, ±0.25, or ±0.5 — one
   of these five. If one side gets a handicap of 1 or more, the framing
   breaks down and no signal fires.
2. **Data complete**: OA model has HT 1X2 probabilities, and a major
   book (BET365 or Pinnacle) has the full-match AH odds posted.

## Main AH line selection (automatic)

Per bookmaker, the main line is chosen in two steps:

1. **Candidate filter**: keep only handicap lines where **both** sides
   have odds in `[0.6, 2.5]` (excludes extreme handicaps whose odds
   blow up to 5.0+ or collapse to 0.3-)
2. **Closest-odds pick**: among remaining candidates, choose the line
   with the smallest two-side odds gap

## How to read the 4 numbers

```
Bet home HT-handicap: lower 0.80 HK ~ upper 1.19 HK
Bet away HT-handicap: lower 1.52 HK ~ upper 2.07 HK
```

**How to use**:
- Market HK odds **< lower line** → don't bet, odds don't compensate
- **Lower ~ upper** → consider, modest math edge
- **≥ upper line** → very valuable, likely market hasn't caught up

## A concrete example

Model predicts HT 1X2 = **home 42% / draw 28% / away 30%**.

| Side | Lower bound (5% EV) | Upper bound (28% EV) |
|---|---|---|
| Bet home HT-handicap | 0.80 HK | 1.19 HK |
| Bet away HT-handicap | 1.52 HK | 2.07 HK |

So: betting home, market must give ≥ 0.80 for 5% edge; at 1.19 it's
28% edge. Away side needs thicker odds (model favors home slightly,
so away requires more to be +EV).

## What does Strength mean?

`min(2 * |eff_home - 0.5|, 1.0)` — measures **model's conviction on
HT direction** (home vs away HT probability gap).

- Balanced match → strength near 0
- Lopsided match → strength near 1

**Important**: high strength ≠ high EV. Strength is model confidence;
the odds water lines reflect EV.

## When NOT to follow

- Full-match handicap > ±0.5 → signal won't fire anyway
- Model has no HT prediction → missing data
- Neither book has HT AH odds → no reference
- **Only applies to HT-平手盘 (line=0)**, can't extrapolate to -0.5 /
  -1 or other handicaps
- Model probabilities are estimates, not truth — your trust in the
  model determines whether to follow
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

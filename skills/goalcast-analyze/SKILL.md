---
name: goalcast-analyze
version: "1.1.0"
description: "完整的足球比赛量化分析。输入比赛 ID，自动获取数据、执行 8 层定量分析、输出可读报告。触发词：'分析比赛'、'预测比赛'、'分析比赛 ID'、'这场比赛怎么样'、'帮我看看这场'。"
---

# Goalcast 比赛分析引擎

## 用途

输入比赛 ID，端到端完成：数据获取 → 8 层量化分析 → 输出可读报告。
目标是长期正期望值（EV），而非单场准确性。

---

## 第 0 步 — 环境检查

**安装依赖（若尚未安装）：**
```bash
python -c "import goalcast" 2>/dev/null || pip install football-datakit[ai]
```

**检查 API Key（含包安装状态）：**
```bash
python -c "
import sys
try:
    from goalcast.config.settings import settings
    sys.exit(0 if settings.FOOTYSTATS_API_KEY else 1)
except ImportError:
    print('ERR_NOT_INSTALLED', file=sys.stderr)
    sys.exit(2)
"
```

退出码含义：
- `0` — 正常，继续执行
- `1` — 包已安装但 Key 缺失，提示用户配置
- `2` — 包未安装，先执行 `pip install football-datakit[ai]` 后重试

若退出码为 `2`，执行安装后**重新**运行本步检查：
```bash
pip install football-datakit[ai]
```

若 Key 缺失（退出码 `1`），**停止执行**，提示用户：

> ⚠️ 未检测到 FOOTYSTATS_API_KEY，请先完成配置。
>
> **方式 A（当前目录 .env，推荐）：**
> ```bash
> echo 'FOOTYSTATS_API_KEY=你的key' > .env
> ```
> **方式 B（全局配置，所有目录生效）：**
> ```bash
> mkdir -p ~/.config/football-datakit
> echo 'FOOTYSTATS_API_KEY=你的key' > ~/.config/football-datakit/.env
> ```
> 获取 API Key：https://footystats.org/api
>
> 配置完成后告诉我，我继续分析。

若用户直接提供 Key，帮助写入后继续：
```bash
echo 'FOOTYSTATS_API_KEY=<用户提供的key>' > .env
```

---

## 第 1 步 — 获取比赛数据

```bash
goalcast-match get_match_analysis <match_id>
```

命令输出为多节文本报告，节名格式为 `[节名]`，直接用于后续分析。

| 节名 | 内容 |
|------|------|
| `[BASIC INFO]` | 对阵、时间、状态、比分 |
| `[XG ANALYSIS]` | 赛前预期进球 xG |
| `[VENUE-SPECIFIC PPG]` | 主队主场 PPG / 客队客场 PPG |
| `[HOME ADVANTAGE]` | 主场进攻/防守/整体优势值 |
| `[H2H RECORD]` | 历史交锋场次、胜平负、BTTS%、Over 2.5% |
| `[POTENTIALS & CONTRADICTIONS]` | BTTS/O25/O35 概率，矛盾信号 |
| `[HOME TEAM DETAILED STATS]` | 主队统计（含主客场拆分） |
| `[AWAY TEAM DETAILED STATS]` | 客队统计 |
| `[VENUE-SPECIFIC XG]` | 主队主场 xG For/Against，客队客场 xG For/Against |
| `[ODDS ANALYSIS]` | Pinnacle 赔率、Soft 赔率、差异 |
| `[TRENDS]` | 主客队近期趋势 |
| `[SUMMARY - KEY SIGNALS]` | 关键信号汇总 |
| `[2ND HALF ODDS]` | 下半场赔率 |
| `[DATA QUALITY NOTES]` | 小样本警告、赔率使用说明 |

若命令失败（非零退出码），返回错误信息，停止分析。

---

## 第 2 步 — 8 层量化分析

### 核心规则

- 绝不编造数据。字段为 -1 或缺失时声明不可用并降低置信度
- EV 计算仅使用 Pinnacle 赔率，非尖锐赔率（odds_ft_*）仅参考
- 置信度不得超过 90
- DATA QUALITY NOTES 含"based on only ~N matches"且 N < 10：基础置信度设为 60
- 存在 CONTRADICTION SIGNAL：在第 4、5 层处理，绝不忽略
- 仅当 EV_adj > 0.05 时才推荐投注

### 第 2.1 层 — 基础实力（35%）

按优先级读取：
1. [VENUE-SPECIFIC XG] — 主队主场 xG/xGA，客队客场 xG/xGA
2. [VENUE-SPECIFIC PPG] — 主队主场 PPG，客队客场 PPG
3. [XG ANALYSIS] 赛前 xG（仅参考）
4. [TEAM FORM] 总体 PPG（仅背景参考）

均值回归：
- N < 10：`xG_adj = season_xG × 0.50 + league_mean × 0.50`
- 否则：`xG_adj = season_xG × 0.70 + recent_5_estimate × 0.30`

计算：
- `λ = home_xG_for_home × (away_xGA_away / league_mean_goals)`
- `μ = away_xG_for_away × (home_xGA_home / league_mean_goals)`

输出基础泊松概率 P(主胜)、P(平)、P(客胜)。

### 第 2.2 层 — 情境调整（20%）

仅使用报告中存在的字段，不估算缺失数据。

- [TRENDS] "failed to score in N of last 5"：对进攻方 -0.10 至 -0.20 xG
- [TRENDS] "last N games with 2+ goals"：+0.10 xG（小样本上限 +0.05）
- 小样本：所有调整上限 ±0.15 xG

缺失字段处理：
- 伤病/停赛缺失 → 调整 = 0，置信度 -10
- 赛程密度缺失 → 调整 = 0，置信度 -5
- 战意/排名缺失 → 调整 = 0，置信度 -5
- 阵容缺失 → 调整 = 0，置信度 -10

### 第 2.3 层 — 市场分析（20%）

从 [ODDS ANALYSIS] 获取，去水 Pinnacle 概率：
```
raw_X = 1 / pinnacle_X
total = raw_home + raw_draw + raw_away
P_market_X = raw_X / total
```

计算差异 = P_model - P_market。

非尖锐赔率差异（仅参考）：
- |pinnacle - soft| > 8%：信号强度 = "强"
- 3–8%："中"
- < 3%："弱/中立"

### 第 2.4 层 — 节奏与矛盾（5%）

若存在 CONTRADICTION SIGNAL：
1. 识别来源：H2H 历史模式 vs 当前赛季模型 vs 小样本噪声
2. H2H 样本 > 15 且差距 > 30pp：对大 2.5 估计应用 H2H 权重 50%
3. 记录解决方案和影响

### 第 2.5 层 — Dixon-Coles 分布（10%）

应用 rho 校正（巴甲 rho = 0.10）：
- P(0-0) ×= (1 - λ×μ×ρ)
- P(1-0) ×= (1 + μ×ρ)
- P(0-1) ×= (1 + λ×ρ)
- P(1-1) ×= (1 - ρ)

构建 0–4 × 0–4 比分矩阵，输出前 3 个比分及概率。

若第 4 层解决的矛盾信号含 H2H 向下压力：总进球 > 2 的比分概率 × 0.85。

### 第 2.6 层 — 贝叶斯更新（5%）

阵容为空时跳过，记录："跳过 — 阵容数据不可用。"

仅当以下情况触发：
- 确认阵容与预期显著不同
- 赔率过去 2 小时波动 > 3%
- 突发伤病新闻

### 第 2.7 层 — EV 和 Kelly 决策（5%）

`EV = (P_model × pinnacle_odds) - 1`

风险乘数（连乘）：
- × 0.85（阵容缺失）
- × 0.90（小样本警告）
- × 0.85（市场信号强烈且与模型相反）

决策：
- EV_adj > 0.10 且置信度 ≥ 65 → "推荐"
- EV_adj 0.05–0.10 且置信度 ≥ 60 → "小注"
- EV_adj < 0.05 → "不推荐"

### 第 2.8 层 — 置信度评分

基础：70（小样本则 60）

加分：
- +10（Pinnacle 方向与模型一致）
- +5（赛季数据完整：xG、PPG、CS% 均存在）
- +5（H2H > 15 场且与模型一致）

减分：第 2 层累积惩罚，另加：
- -5（无赔率波动数据）
- -5（推理中未解决矛盾信号）

最终范围：[30, 90]

---

## 第 3 步 — 输出报告

直接输出以下 Markdown 报告，**不输出中间 JSON**。

### 置信度 badge 规则
- ≥ 70：`🟢`
- 55–69：`🟡`
- < 55：`🔴`，末尾追加 `（低置信度，谨慎参考）`

### EV 标签规则
- EV_adj > 0.10：`高价值`
- EV_adj 0.05–0.10：`中等价值`
- EV_adj < 0.05：`无投注价值`

### 报告模板

```
============================================================
⚽ Goalcast 比赛预测
{home_team} vs {away_team}
{competition}
============================================================

📋 数据质量   {data_quality}
[若 sample_size_warning] ⚠️  小样本警告：赛季数据场次不足，统计可信度受限
[若 missing_data 非空] 缺失字段：{missing_data 翻译为中文}

------------------------------------------------------------
🎯 概率预测
------------------------------------------------------------
             主胜        平局        客胜
模型        {home_win}    {draw}    {away_win}
市场(Pin)  {pin_home}   {pin_draw}  {pin_away}
分歧       {div_home}   {div_draw}  {div_away}

市场信号：{signal_direction}（{signal_strength}）

------------------------------------------------------------
📐 xG 建模
------------------------------------------------------------
λ（主队预期进球）: {lambda_home}
μ（客队预期进球）: {mu_away}

最可能比分：
  1. {score_1}  {prob_1}
  2. {score_2}  {prob_2}
  3. {score_3}  {prob_3}

[仅当 contradiction_analysis.exists 为 true 时显示]
------------------------------------------------------------
⚠️  矛盾信号
------------------------------------------------------------
{contradiction_analysis.description}
分析：{contradiction_analysis.resolution}
对模型影响：{contradiction_analysis.impact_on_model}

------------------------------------------------------------
💡 分析摘要
------------------------------------------------------------
[第一层] {layer1_xg_calc}
[第二层] {layer2_context}
[第三层] {layer3_market}
[第四层] {layer4_tempo_contradiction}
[第五层] {layer5_distribution}
[第七层] {layer7_ev}

------------------------------------------------------------
[若 bet_rating 为 推荐 或 小注]
✅ 投注建议
------------------------------------------------------------
方向：{best_bet}
EV（原始）：{ev_raw}
EV（风险调整后）：{ev_risk_adjusted}  → {EV标签}
评级：{bet_rating}
注：EV 基于 Pinnacle 赔率计算。实际投注请使用最优赔率。

[否则]
❌ 无投注价值
------------------------------------------------------------
风险调整后 EV 低于阈值（0.05）。
最高 EV 方向：{best_bet}（EV_adj = {ev_risk_adjusted}）

------------------------------------------------------------
📈 置信度
------------------------------------------------------------
{badge} {confidence}/90

{layer8_confidence}

------------------------------------------------------------
⚙️  技术备注
------------------------------------------------------------
· Pinnacle 赔率用于 EV 计算
· Soft odds (odds_ft_*) 仅参考，未用于 EV
· {sample_size_note}
· {league_params}
============================================================
```

### 字段翻译（missing_data）
- `injuries` → 伤病/停赛
- `lineup` → 首发阵容
- `schedule_density` → 赛程密度
- `motivation` → 积分动力
- `elo` → Elo 评分
- `odds_movement` → 赔率变动
- `ppda` → 逼抢强度

### 注意事项
- 任何字段为 null 或空时，静默省略该行，不显示 "null"
- 分歧值格式：`+X.X%` 或 `-X.X%`（始终带符号）
- 报告内容严格来自分析结果，不添加额外评论

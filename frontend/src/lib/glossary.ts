// Single source of truth for UI explanation copy (Chinese-first, i18n-ready keys).
// Add entries here when a new tooltip/InfoIcon point is wired up.

export const glossary = {
  // PredictabilityBadge
  'mc.predictability.high':
    '可预测度：高。模型对该场比赛结果较有把握，建议关注。',
  'mc.predictability.good':
    '可预测度：良。模型有较稳健的判断，比一般场次更可信。',
  'mc.predictability.medium':
    '可预测度：中。常见水平，仅作参考。',
  'mc.predictability.poor':
    '可预测度：差。比赛走势难判，建议谨慎或跳过。',

  // Phase 3 占位（接线时随写文案，先放 placeholder）
  'mc.rank': '当前联赛积分榜排名。',
  'mc.goals': '本赛季已踢比赛的进球数 / 失球数。',
  'mc.form5':
    '近 5 场战绩。W=胜 D=平 L=负，最左为最近一场。',
  'mc.probbar':
    '模型预测概率：主胜 / 平局 / 客胜（合计 100%）。',
  'mc.odds.home': '主胜赔率（Pinnacle 全场，十进制）。',
  'mc.odds.draw': '平局赔率（Pinnacle 全场，十进制）。',
  'mc.odds.away': '客胜赔率（Pinnacle 全场，十进制）。',
  'mc.drop':
    '24 小时内 Pinnacle 主胜赔率最大跌幅。≥60% 视为强信号（红色）。',

  // Phase 4 占位
  'dash.candidates':
    '候选比赛：未来 7 天内所有联赛的可分析比赛数。+N 表示较昨日的增量。',
  'dash.ai_modeled':
    'AI 已建模：已生成预测结果的比赛数及覆盖率。',
  'dash.drop_high':
    '高跌幅：24h 内主胜赔率跌幅 ≥50% 的比赛数（强信号）。',
  'dash.predictability':
    '可预测度 ≥ 一般：模型把握度在「中」及以上的比赛数。',
  'dash.top_drops':
    '过去 24h 主胜赔率跌幅最大的 5 场比赛，按跌幅倒序。',
  'dash.upcoming':
    '即将开赛：按开球时间排序的最近 4 场比赛。',
  'dash.value_bets':
    '高 Edge 价值投注：模型概率 - 赔率隐含概率 ≥ 5% 的下注机会。',
  'dash.health':
    '数据健康：赔率 / 模型 / 可预测度三项的覆盖率与质量估算。',

  // Phase 5 — MatchDetail 卡片头部
  'md.model_prob':
    '模型概率：基于多次蒙特卡洛模拟得出的主胜 / 平局 / 客胜 / 大 2.5 / 两队进球各事件概率。',
  'md.scoreline_heatmap':
    '比分概率热图：模型预测每个具体比分发生的概率，颜色越深概率越高。可叠加亚盘线查看覆盖区域。',
  'md.ah_table':
    '亚盘全表：所有可用亚洲让球线的主 / 客赔率与隐含概率。',
  'md.drop_records':
    '跌赔记录：过去 24 小时内本场比赛各市场、各家公司的赔率下跌时序。',
  'md.team_compare':
    '两队状态对比：本赛季已踢比赛的进失球累计对比。',
  'md.bigbar.over25':
    '大 2.5：模型预测全场总进球超过 2.5 个的概率。',
  'md.bigbar.btts':
    '两队进球（BTTS）：模型预测主客两队都至少打入一球的概率。',

  // Phase 5 — DroppingOdds
  'drop.market_tag':
    '市场 key：如 1x2_ft（全场胜平负）、ah（亚盘）、ou（大小球）。',
  'drop.drop_pct':
    '跌幅 = (开盘赔率 − 当前赔率) / 开盘赔率。数字越大代表市场对该选项信心越强。',

  // Phase 5 — ValueBets
  'vb.selection':
    '推荐下注的选项：主胜 / 平局 / 客胜 或其他市场选项。',
  'vb.odds':
    '当前 Pinnacle 全场赔率（十进制）。',
  'vb.prob':
    '模型预测该选项的真实概率。',
  'vb.edge':
    'Edge = 模型概率 − 赔率隐含概率（1 / 赔率 × 100%）。正数代表存在期望正收益空间。',

  // Phase 5 — History
  'hist.samples':
    '总样本：本策略覆盖的历史比赛数及胜 / 平 / 负结果分布。',
  'hist.winrate':
    '胜率：W / (W + D + L)。仅作参考，需结合赔率与方差判断盈利能力。',
  'hist.roi':
    'ROI：投资回报率。需要后端 bet_outcomes 表数据，当前暂未启用。',
  'hist.avg_edge':
    '平均 Edge：本策略历史投注的平均期望优势。当前待后端聚合。',
  'hist.col.drop': '跌幅：本场比赛 24h 内的主胜赔率最大跌幅。',
  'hist.col.predictability': '可预测度：开赛时模型对该比赛结果的把握等级。',
  'hist.col.result': '结果：✓ 命中策略选项 / ✗ 未命中 / ◯ 走盘（退款）。',
} as const

export type GlossaryKey = keyof typeof glossary

export function gloss(key: GlossaryKey): string {
  return glossary[key]
}

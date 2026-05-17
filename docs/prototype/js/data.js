// Sample fixtures — mirrors FixtureSummary / FixtureDetail shapes from frontend/src/lib/api.ts
// 6 leagues × ~3 fixtures each = 18 matches, used across all pages.

const _BASE = new Date();
const todayAt = (h, m = 0, offsetDays = 0) => {
  const d = new Date(_BASE);
  d.setDate(d.getDate() + offsetDays);
  d.setHours(h, m, 0, 0);
  return d.toISOString();
};

const F = (id, home, away, league, country, kickoff, opts = {}) => ({
  id, home_team: home, away_team: away,
  competition_name: league, competition_country: country,
  kickoff_utc: kickoff,
  status: opts.status || 'pre',
  predictability: opts.pred ?? 'good',
  home_form: { form5: opts.hf || 'WWDLW', won: 3, drawn: 1, lost: 1, gf: 9, ga: 4 },
  away_form: { form5: opts.af || 'WDLWD', won: 2, drawn: 2, lost: 1, gf: 7, ga: 5 },
  prediction_summary: opts.ps || {
    home_win_pct: 42.5, draw_pct: 27.3, away_win_pct: 30.2,
    btts_pct: 58.4, o25_pct: 54.1,
  },
  odds: {
    ft_result: {
      pinnacle: opts.pin || { home: 2.10, draw: 3.45, away: 3.40 },
      bet365:   opts.b365 || { home: 2.05, draw: 3.50, away: 3.35 },
    },
    asian_handicap: opts.ah || {
      line: -0.25,
      pinnacle: { home_outcome: 'home', home_odds: 1.92, away_outcome: 'away', away_odds: 1.96 },
      bet365:   { home_odds: 1.90, away_odds: 1.94 },
    },
  },
  drop_flag: opts.drop ? { market_key: opts.drop.mkt || 'home', drop_percentage: opts.drop.pct } : null,
  // Team abbreviations for badge display
  home_abbr: opts.ha || home.slice(0, 3).toUpperCase(),
  away_abbr: opts.aa || away.slice(0, 3).toUpperCase(),
  home_color: opts.hc || '#dc2626',
  away_color: opts.ac || '#1e40af',
  home_rank: opts.hr ?? 4,
  away_rank: opts.ar ?? 7,
  goals: opts.goals || { hf: 18, ha: 9, af: 14, aa: 11 },
});

const FIXTURES = [
  // 英超 Premier League
  F(101, '阿森纳',     '曼城',     '英超', '英格兰', todayAt(20, 30, 0),
    { ha: 'ARS', aa: 'MCI', hc: '#ef4444', ac: '#67e8f9', hr: 2, ar: 1, pred: 'high',
      hf: 'WWWDW', af: 'WWWWW',
      ps: { home_win_pct: 38.2, draw_pct: 28.5, away_win_pct: 33.3, btts_pct: 62.1, o25_pct: 58.7 },
      pin: { home: 2.70, draw: 3.40, away: 2.55 },
      b365: { home: 2.62, draw: 3.45, away: 2.60 },
      drop: { pct: 67, mkt: 'home' },
      ah: { line: 0, pinnacle: { home_outcome: 'home', home_odds: 1.96, away_outcome: 'away', away_odds: 1.92 }, bet365: { home_odds: 1.93, away_odds: 1.90 } },
      goals: { hf: 22, ha: 8, af: 26, aa: 6 } }),
  F(102, '利物浦',     '切尔西',   '英超', '英格兰', todayAt(22, 45, 0),
    { ha: 'LIV', aa: 'CHE', hc: '#dc2626', ac: '#1e3a8a', hr: 3, ar: 6, pred: 'good',
      hf: 'WDWLW', af: 'WLDWD',
      ps: { home_win_pct: 54.8, draw_pct: 23.1, away_win_pct: 22.1, btts_pct: 61.5, o25_pct: 57.9 },
      drop: { pct: 42, mkt: 'home' },
      ah: { line: -0.75, pinnacle: { home_outcome: 'home', home_odds: 1.85, away_outcome: 'away', away_odds: 2.05 }, bet365: { home_odds: 1.83, away_odds: 2.02 } } }),
  F(103, '布莱顿',     '托特纳姆', '英超', '英格兰', todayAt(18, 0, 1),
    { ha: 'BHA', aa: 'TOT', hc: '#0ea5e9', ac: '#0f172a', hr: 9, ar: 5, pred: 'medium',
      hf: 'DWLDW', af: 'WDWLL',
      ps: { home_win_pct: 33.7, draw_pct: 26.8, away_win_pct: 39.5, btts_pct: 65.2, o25_pct: 61.4 } }),

  // 西甲 La Liga
  F(201, '皇家马德里', '巴塞罗那', '西甲', '西班牙', todayAt(21, 0, 0),
    { ha: 'RMA', aa: 'BAR', hc: '#f8fafc', ac: '#7c1d2e', hr: 1, ar: 2, pred: 'high',
      hf: 'WWWWD', af: 'WWDWW',
      ps: { home_win_pct: 47.1, draw_pct: 24.6, away_win_pct: 28.3, btts_pct: 67.8, o25_pct: 64.2 },
      pin: { home: 2.15, draw: 3.50, away: 3.30 },
      b365: { home: 2.10, draw: 3.55, away: 3.25 },
      drop: { pct: 78, mkt: 'home' },
      ah: { line: -0.25, pinnacle: { home_outcome: 'home', home_odds: 1.94, away_outcome: 'away', away_odds: 1.94 }, bet365: { home_odds: 1.92, away_odds: 1.91 } },
      goals: { hf: 28, ha: 7, af: 24, aa: 9 } }),
  F(202, '马德里竞技', '塞维利亚', '西甲', '西班牙', todayAt(19, 30, 0),
    { ha: 'ATM', aa: 'SEV', hc: '#dc2626', ac: '#fef3c7', hr: 4, ar: 11, pred: 'good',
      hf: 'WWDWL', af: 'LDWLW',
      ps: { home_win_pct: 58.3, draw_pct: 22.7, away_win_pct: 19.0, btts_pct: 49.1, o25_pct: 47.8 },
      drop: { pct: 31, mkt: 'home' } }),

  // 德甲 Bundesliga
  F(301, '拜仁慕尼黑', '多特蒙德', '德甲', '德国',   todayAt(20, 30, 1),
    { ha: 'BAY', aa: 'BVB', hc: '#dc2626', ac: '#facc15', hr: 1, ar: 3, pred: 'high',
      hf: 'WWWWW', af: 'WLWDW',
      ps: { home_win_pct: 63.4, draw_pct: 18.2, away_win_pct: 18.4, btts_pct: 72.5, o25_pct: 69.3 },
      pin: { home: 1.62, draw: 4.20, away: 5.40 },
      b365: { home: 1.60, draw: 4.25, away: 5.50 },
      drop: { pct: 54, mkt: 'home' },
      ah: { line: -1.25, pinnacle: { home_outcome: 'home', home_odds: 1.88, away_outcome: 'away', away_odds: 2.02 }, bet365: { home_odds: 1.85, away_odds: 1.99 } } }),
  F(302, '莱比锡',     '勒沃库森', '德甲', '德国',   todayAt(22, 30, 1),
    { ha: 'RBL', aa: 'B04', hc: '#dc2626', ac: '#1e3a8a', hr: 4, ar: 2, pred: 'medium' }),

  // 意甲 Serie A
  F(401, '国际米兰',   '尤文图斯', '意甲', '意大利', todayAt(19, 45, 0),
    { ha: 'INT', aa: 'JUV', hc: '#1e40af', ac: '#0f172a', hr: 1, ar: 4, pred: 'good',
      hf: 'WWWLW', af: 'WDDWL',
      ps: { home_win_pct: 51.2, draw_pct: 28.4, away_win_pct: 20.4, btts_pct: 48.7, o25_pct: 45.3 },
      drop: { pct: 38, mkt: 'home' } }),
  F(402, 'AC米兰',     '那不勒斯', '意甲', '意大利', todayAt(21, 45, 1),
    { ha: 'MIL', aa: 'NAP', hc: '#dc2626', ac: '#0ea5e9', hr: 5, ar: 3, pred: 'good',
      drop: { pct: 24, mkt: 'away' } }),

  // 法甲 Ligue 1
  F(501, '巴黎圣日耳曼','马赛',     '法甲', '法国',   todayAt(23, 0, 0),
    { ha: 'PSG', aa: 'OM',  hc: '#0f172a', ac: '#0ea5e9', hr: 1, ar: 6, pred: 'high',
      hf: 'WWWWW', af: 'WLWDL',
      ps: { home_win_pct: 71.2, draw_pct: 16.1, away_win_pct: 12.7, btts_pct: 56.3, o25_pct: 62.1 },
      drop: { pct: 58, mkt: 'home' } }),
  F(502, '里昂',       '摩纳哥',   '法甲', '法国',   todayAt(20, 0, 2),
    { ha: 'OL',  aa: 'ASM', hc: '#dc2626', ac: '#dc2626', hr: 7, ar: 2, pred: 'poor' }),

  // 欧冠 UCL
  F(601, '皇家马德里', '拜仁慕尼黑','欧冠', '欧洲',   todayAt(20, 0, 2),
    { ha: 'RMA', aa: 'BAY', hc: '#f8fafc', ac: '#dc2626', hr: 1, ar: 1, pred: 'high',
      hf: 'WWWWD', af: 'WWWWW',
      ps: { home_win_pct: 43.2, draw_pct: 25.8, away_win_pct: 31.0, btts_pct: 68.9, o25_pct: 66.5 },
      drop: { pct: 71, mkt: 'home' } }),
  F(602, '曼城',       '阿森纳',   '欧冠', '欧洲',   todayAt(22, 0, 2),
    { ha: 'MCI', aa: 'ARS', hc: '#67e8f9', ac: '#ef4444', hr: 1, ar: 2, pred: 'high',
      drop: { pct: 49, mkt: 'home' } }),
];

// Historical results for History page (unused — see HISTORY_CLEAN below)
const _OLD_HISTORY = [];
/* removed broken array — see HISTORY_CLEAN below.
  { id: 901, home: '曼联', away: '富勒姆', league: '英超', date: '2026-05-12', sh: 2, sa: 1, drop_pct: 64, predictability: 'good',  bet: 'home', result: 'W', edge: 8.4 },
  { id: 902, home: '热刺', away: '纽卡',   league: '英超', date: '2026-05-11', sh: 1, sa: 3, drop_pct: 45, predictability: 'medium', bet: 'away', result: 'W', edge: 12.1 },
  { id: 903, home: '巴萨', away: '皇社',   league: '西甲', date: '2026-05-10', sh: 0, sa: 0, drop_pct: 31, predictability: 'good',  bet: 'home', result: 'L', edge: 6.2 },
  { id: 904, home: '尤文', away: '罗马',   league: '意甲', date: '2026-05-10', sh: 2, sa: 2, drop_pct: 52, predictability: 'high',  bet: 'home', result: 'D', edge: 9.8 },
  { id: 905, home: '多特', away: '法兰克福','德甲', date: '2026-05-09', sh: 3, sa: 1, drop_pct: 38, predictability: 'good',  bet: 'home', result: 'W', edge: 7.5 },
  { id: 906, home: '马竞', away: '比利亚',  '西甲','2026-05-09', sh: 1, sa: 0, drop_pct: 41, predictability: 'medium', bet: 'home', result: 'W', edge: 5.1 },
  { id: 907, home: '阿森纳','切尔西',     '英超','2026-05-08', sh: 1, sa: 1, drop_pct: 28, predictability: 'good',  bet: 'over', result: 'L', edge: 4.3 },
  { id: 908, home: '国米', away: '拉齐奥',  '意甲','2026-05-07', sh: 2, sa: 0, drop_pct: 55, predictability: 'high',  bet: 'home', result: 'W', edge: 11.2 },
  { id: 909, home: 'PSG',  away: '里尔',   '法甲','2026-05-07', sh: 4, sa: 1, drop_pct: 47, predictability: 'high',  bet: 'over', result: 'W', edge: 9.4 },
];
*/
// Fix the shorthand object literals above (some entries above used a stray syntax — rebuild cleanly):
const HISTORY_CLEAN = [
  { id: 901, home: '曼联', away: '富勒姆',   league: '英超', date: '2026-05-12', sh: 2, sa: 1, drop_pct: 64, predictability: 'good',   bet: '主胜', result: 'W', edge: 8.4 },
  { id: 902, home: '热刺', away: '纽卡',     league: '英超', date: '2026-05-11', sh: 1, sa: 3, drop_pct: 45, predictability: 'medium', bet: '客胜', result: 'W', edge: 12.1 },
  { id: 903, home: '巴萨', away: '皇社',     league: '西甲', date: '2026-05-10', sh: 0, sa: 0, drop_pct: 31, predictability: 'good',   bet: '主胜', result: 'L', edge: 6.2 },
  { id: 904, home: '尤文', away: '罗马',     league: '意甲', date: '2026-05-10', sh: 2, sa: 2, drop_pct: 52, predictability: 'high',   bet: '主胜', result: 'D', edge: 9.8 },
  { id: 905, home: '多特', away: '法兰克福', league: '德甲', date: '2026-05-09', sh: 3, sa: 1, drop_pct: 38, predictability: 'good',   bet: '主胜', result: 'W', edge: 7.5 },
  { id: 906, home: '马竞', away: '比利亚',   league: '西甲', date: '2026-05-09', sh: 1, sa: 0, drop_pct: 41, predictability: 'medium', bet: '主胜', result: 'W', edge: 5.1 },
  { id: 907, home: '阿森纳', away: '切尔西', league: '英超', date: '2026-05-08', sh: 1, sa: 1, drop_pct: 28, predictability: 'good',   bet: '大球', result: 'L', edge: 4.3 },
  { id: 908, home: '国米', away: '拉齐奥',   league: '意甲', date: '2026-05-07', sh: 2, sa: 0, drop_pct: 55, predictability: 'high',   bet: '主胜', result: 'W', edge: 11.2 },
  { id: 909, home: 'PSG',  away: '里尔',     league: '法甲', date: '2026-05-07', sh: 4, sa: 1, drop_pct: 47, predictability: 'high',   bet: '大球', result: 'W', edge: 9.4 },
  { id: 910, home: '拜仁', away: '弗赖堡',   league: '德甲', date: '2026-05-06', sh: 2, sa: 1, drop_pct: 33, predictability: 'good',   bet: '主胜', result: 'W', edge: 5.7 },
];

// Value bets — derived selections
const VALUE_BETS = [
  { fid: 101, home: '阿森纳',     away: '曼城',     league: '英超', kick: FIXTURES[0].kickoff_utc, sel: '客胜', edge: 14.2, prob: 39.5, odds: 2.55 },
  { fid: 201, home: '皇家马德里', away: '巴塞罗那', league: '西甲', kick: FIXTURES[3].kickoff_utc, sel: '主胜', edge: 11.7, prob: 49.6, odds: 2.15 },
  { fid: 601, home: '皇家马德里', away: '拜仁慕尼黑', league: '欧冠', kick: FIXTURES[10].kickoff_utc, sel: '客胜', edge: 10.4, prob: 33.2, odds: 3.10 },
  { fid: 301, home: '拜仁慕尼黑', away: '多特蒙德', league: '德甲', kick: FIXTURES[5].kickoff_utc, sel: '大2.5', edge:  8.9, prob: 69.3, odds: 1.62 },
  { fid: 501, home: '巴黎圣日耳曼', away: '马赛',   league: '法甲', kick: FIXTURES[8].kickoff_utc, sel: '主胜', edge:  7.6, prob: 71.2, odds: 1.45 },
  { fid: 102, home: '利物浦',     away: '切尔西',   league: '英超', kick: FIXTURES[1].kickoff_utc, sel: '亚盘-0.75', edge: 6.8, prob: 56.2, odds: 1.85 },
  { fid: 401, home: '国际米兰',   away: '尤文图斯', league: '意甲', kick: FIXTURES[7].kickoff_utc, sel: '主胜', edge:  5.4, prob: 51.2, odds: 2.05 },
  { fid: 202, home: '马德里竞技', away: '塞维利亚', league: '西甲', kick: FIXTURES[4].kickoff_utc, sel: '小2.5', edge:  4.7, prob: 52.2, odds: 1.95 },
];

// Dropping odds list — denormalized
const DROPPING = FIXTURES
  .filter(f => f.drop_flag)
  .map(f => ({
    fid: f.id, home: f.home_team, away: f.away_team,
    league: f.competition_name, kick: f.kickoff_utc,
    market: f.drop_flag.market_key,
    bookmaker: 'pinnacle',
    odds_now: f.odds.ft_result.pinnacle.home,
    odds_open: +(f.odds.ft_result.pinnacle.home * (1 + f.drop_flag.drop_percentage / 100)).toFixed(2),
    drop_pct: f.drop_flag.drop_percentage,
    recorded_at: new Date(Date.now() - Math.random() * 1000 * 60 * 60 * 4).toISOString(),
  }))
  .sort((a, b) => b.drop_pct - a.drop_pct);

// Predictability label
const PRED_LABEL = { high: '高可预测', good: '良好', medium: '一般', poor: '差', null: '—' };

// Format kickoff
function fmtKickoff(iso) {
  const d = new Date(iso);
  const days = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
  const day = days[d.getDay()];
  const hh = String(d.getHours()).padStart(2, '0');
  const mm = String(d.getMinutes()).padStart(2, '0');
  return { day, time: `${hh}:${mm}`, date: `${d.getMonth() + 1}/${d.getDate()}` };
}

// Group by competition
function groupByLeague(items) {
  const groups = {};
  for (const f of items) {
    const k = f.competition_name || f.league;
    (groups[k] = groups[k] || []).push(f);
  }
  return groups;
}

// Expose to window for use across babel scripts
Object.assign(window, { FIXTURES, HISTORY: HISTORY_CLEAN, VALUE_BETS, DROPPING, PRED_LABEL, fmtKickoff, groupByLeague });

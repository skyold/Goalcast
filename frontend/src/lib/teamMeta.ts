// frontend/src/lib/teamMeta.ts
// Static lookup for team abbreviation + primary color.
// OddAlerts API does not provide these — see docs/frontend-data-gaps.md (#1, #2, #6).
// Expand this table as new teams are added; missing teams fall back to a deterministic hash.

export interface TeamMeta {
  abbr: string;
  color: string;
}

// Seed with major European clubs. Use team_id when joining from backend; for now we
// also support name-based lookup as a fallback during migration.
const BY_ID: Record<number, TeamMeta> = {
  // populate as backend exposes team_id
};

const BY_NAME: Record<string, TeamMeta> = {
  '阿森纳':      { abbr: 'ARS', color: '#ef4444' },
  '曼城':        { abbr: 'MCI', color: '#67e8f9' },
  '曼联':        { abbr: 'MUN', color: '#dc2626' },
  '利物浦':      { abbr: 'LIV', color: '#dc2626' },
  '切尔西':      { abbr: 'CHE', color: '#1e3a8a' },
  '托特纳姆':    { abbr: 'TOT', color: '#0f172a' },
  '热刺':        { abbr: 'TOT', color: '#0f172a' },
  '纽卡':        { abbr: 'NEW', color: '#0f172a' },
  '布莱顿':      { abbr: 'BHA', color: '#0ea5e9' },
  '富勒姆':      { abbr: 'FUL', color: '#f8fafc' },

  '皇家马德里':  { abbr: 'RMA', color: '#f8fafc' },
  '巴塞罗那':    { abbr: 'BAR', color: '#7c1d2e' },
  '巴萨':        { abbr: 'BAR', color: '#7c1d2e' },
  '马德里竞技':  { abbr: 'ATM', color: '#dc2626' },
  '马竞':        { abbr: 'ATM', color: '#dc2626' },
  '塞维利亚':    { abbr: 'SEV', color: '#fef3c7' },
  '皇社':        { abbr: 'RSO', color: '#1e40af' },
  '比利亚':      { abbr: 'VIL', color: '#facc15' },

  '拜仁慕尼黑':  { abbr: 'BAY', color: '#dc2626' },
  '拜仁':        { abbr: 'BAY', color: '#dc2626' },
  '多特蒙德':    { abbr: 'BVB', color: '#facc15' },
  '多特':        { abbr: 'BVB', color: '#facc15' },
  '莱比锡':      { abbr: 'RBL', color: '#dc2626' },
  '勒沃库森':    { abbr: 'B04', color: '#1e3a8a' },
  '法兰克福':    { abbr: 'SGE', color: '#0f172a' },
  '弗赖堡':      { abbr: 'SCF', color: '#dc2626' },

  '国际米兰':    { abbr: 'INT', color: '#1e40af' },
  '国米':        { abbr: 'INT', color: '#1e40af' },
  '尤文图斯':    { abbr: 'JUV', color: '#0f172a' },
  '尤文':        { abbr: 'JUV', color: '#0f172a' },
  'AC米兰':      { abbr: 'MIL', color: '#dc2626' },
  '那不勒斯':    { abbr: 'NAP', color: '#0ea5e9' },
  '罗马':        { abbr: 'ROM', color: '#7c1d2e' },
  '拉齐奥':      { abbr: 'LAZ', color: '#67e8f9' },

  '巴黎圣日耳曼':{ abbr: 'PSG', color: '#0f172a' },
  '马赛':        { abbr: 'OM',  color: '#0ea5e9' },
  '里昂':        { abbr: 'OL',  color: '#dc2626' },
  '摩纳哥':      { abbr: 'ASM', color: '#dc2626' },
  '里尔':        { abbr: 'LOS', color: '#dc2626' },
};

// Deterministic fallback: hash the name to a hue, pick first 3 chars upper.
function hashColor(name: string): string {
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) >>> 0;
  const hue = h % 360;
  return `oklch(0.62 0.18 ${hue})`;
}

function shortFor(name: string): string {
  // Pull capital-letter sequences first (handles "AC米兰", "PSG").
  const caps = name.match(/[A-Z]+/g)?.join('') ?? '';
  if (caps.length >= 2) return caps.slice(0, 3).toUpperCase();
  // ASCII-only names: first 3 chars
  if (/^[\x00-\x7F]+$/.test(name)) return name.slice(0, 3).toUpperCase();
  // Chinese: take last 2 chars as the "core" team identifier
  return name.slice(-2);
}

export function teamMeta(opts: { id?: number | null; name: string; nameZh?: string | null }): TeamMeta {
  if (opts.id != null && BY_ID[opts.id]) return BY_ID[opts.id];
  // Always look up by zh first when available — BY_NAME is keyed on zh, so this
  // keeps colour/abbr identical regardless of UI locale. Falls back to whatever
  // name was passed (typically the locale-resolved display name).
  if (opts.nameZh && BY_NAME[opts.nameZh]) return BY_NAME[opts.nameZh];
  if (BY_NAME[opts.name]) return BY_NAME[opts.name];
  // Hash on the zh name when we have one, so the fallback colour stays stable
  // across locales for teams not present in BY_NAME.
  const hashKey = opts.nameZh && opts.nameZh.trim() ? opts.nameZh : opts.name;
  return { abbr: shortFor(opts.name), color: hashColor(hashKey) };
}

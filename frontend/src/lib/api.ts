export interface TeamStats {
  pos: number; wins: number; draws: number; losses: number
  gf: number; ga: number; form5: string[]
}

export interface FixtureSummary {
  id: number; competition_id: number; competition_name: string
  home_team: string; away_team: string; kickoff_utc: string
  status: 'pre' | 'live' | 'ft'
  score_home: number | null; score_away: number | null
  prob_home_win: number | null; prob_draw: number | null; prob_away_win: number | null
  trend_home_win: number; trend_away_win: number; trend_btts: number
  home_stats: TeamStats | null; away_stats: TeamStats | null
  odds_home: number | null; odds_draw: number | null; odds_away: number | null
  drop_pct: number | null; drop_market: string | null
}

export interface OddsSnapshot {
  id: number; fixture_id: number; market: string; bookmaker: string
  odds_home: number | null; odds_draw: number | null; odds_away: number | null
  drop_pct: number | null; drop_market: string | null; recorded_at: string
}

export interface H2HRecord {
  date: string; home: string; away: string; score_h: number; score_a: number
}

export interface DroppingOddsItem {
  fixture_id: number; home_team: string; away_team: string
  competition_name: string; kickoff_utc: string
  market: string; bookmaker: string
  odds_home: number | null; odds_draw: number | null; odds_away: number | null
  drop_pct: number | null; drop_market: string | null; recorded_at: string
}

export interface ValueBetItem {
  fixture_id: number; home_team: string; away_team: string
  competition_name: string; kickoff_utc: string
  selection: 'home' | 'draw' | 'away'; edge_pct: number; prob: number; odds: number
}

type P = Record<string, string | number | boolean | undefined | null>

async function get<T>(path: string, params?: P): Promise<T> {
  const url = new URL('/api' + path, window.location.origin)
  if (params) Object.entries(params).forEach(([k, v]) => { if (v != null) url.searchParams.set(k, String(v)) })
  const res = await fetch(url.toString())
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${path}`)
  return res.json()
}

export const api = {
  fixtures: (p: { date?: string; leagues?: string; limit?: number; status?: string }) =>
    get<{ fixtures: FixtureSummary[]; total: number; cached_at: string | null }>('/fixtures', p),
  fixture: (id: number) =>
    get<{ fixture: FixtureSummary; odds_history: OddsSnapshot[]; h2h: H2HRecord[]; stats: { home: TeamStats | null; away: TeamStats | null } }>(`/fixtures/${id}`),
  competitions: () =>
    get<{ competitions: Array<{ id: number; name: string }> }>('/competitions'),
  droppingOdds: (p?: { min_drop?: number; market?: string }) =>
    get<{ items: DroppingOddsItem[]; synced_at: string }>('/dropping-odds', p),
  valueBets: (p?: { min_edge?: number }) =>
    get<{ items: ValueBetItem[] }>('/value-bets', p),
  history: (p?: { limit?: number; offset?: number; league?: number }) =>
    get<{ items: FixtureSummary[]; total: number }>('/history', p),
  triggerSync: () =>
    fetch('/api/sync/trigger', { method: 'POST' }).then(r => r.json() as Promise<{ started: boolean }>),
}

export interface TeamStats {
  wins: number; draws: number; losses: number; played: number
  gf: number; ga: number; goals_avg: number; conceded_avg: number
  win_pct_home: number; win_pct_away: number; form5: string[]
}

export type Predictability = 'high' | 'good' | 'medium' | 'poor' | null

export type TeamForm = {
  form5: string
  won: number; drawn: number; lost: number
  gf: number; ga: number
}

export type BookmakerOdds = {
  home: number | null; draw?: number | null; away: number | null
  opening?: number | null
  current_at?: string | null
}

export type AsianHandicapLine = {
  line: number
  pinnacle?: { home: number | null; away: number | null
               opening_home?: number | null; opening_away?: number | null } | null
  bet365?:   { home: number | null; away: number | null } | null
}

export type Prediction = {
  simulations: number
  home_win_pct: number; draw_pct: number; away_win_pct: number
  btts_pct: number; o25_pct: number; o35_pct: number
  scorelines: Record<string, number>
  updated_at: string
}

export type FixtureSummary = {
  id: number
  home_team: string; away_team: string
  competition_name: string
  competition_country?: string
  kickoff_utc: string
  status: 'pre' | 'live' | 'ft'
  predictability: Predictability
  home_form: TeamForm | null
  away_form: TeamForm | null
  prediction_summary: {
    home_win_pct: number; draw_pct: number; away_win_pct: number
    btts_pct: number; o25_pct: number
  } | null
  odds: {
    ft_result: { pinnacle: BookmakerOdds | null; bet365: BookmakerOdds | null }
    asian_handicap: {
      line: number
      pinnacle: { home_outcome: string; home_odds: number; away_outcome: string; away_odds: number }
      bet365: { home_odds: number | null; away_odds: number | null } | null
    } | null
  } | null
  drop_flag: { market_key: string; drop_percentage: number } | null
  // legacy fields kept for backward compat with existing pages until they're migrated:
  home_stats?: TeamStats | null
  away_stats?: TeamStats | null
}

export type FixtureDetail = Omit<FixtureSummary, 'odds'> & {
  prediction: Prediction | null
  odds: {
    ft_result: { pinnacle: BookmakerOdds | null; bet365: BookmakerOdds | null }
    asian_handicap_lines: AsianHandicapLine[]
  } | null
  home_team_obj: { id: number; name: string; stats: unknown; form: TeamForm | null }
  away_team_obj: { id: number; name: string; stats: unknown; form: TeamForm | null }
  dropping_records: Array<{
    market_key: string; drop_pct: number; bookmaker: string; recorded_at: string
  }>
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
    get<{ fixture: FixtureDetail; odds_history: OddsSnapshot[]; h2h: H2HRecord[]; stats: { home: TeamStats | null; away: TeamStats | null } }>(`/fixtures/${id}`),
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

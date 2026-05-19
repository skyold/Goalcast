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
  home_team_zh?: string | null
  away_team_zh?: string | null
  home_abbr?: string | null
  away_abbr?: string | null
  home_rank?: number | null
  away_rank?: number | null
  competition_name: string
  competition_name_zh?: string | null
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
  // legacy fields kept for backward compat with History.tsx until it's migrated to the new shape:
  home_stats?: TeamStats | null
  away_stats?: TeamStats | null
  score_home?: number | null
  score_away?: number | null
  drop_pct?: number | null
  trend_home_win?: number
  trend_away_win?: number
  trend_btts?: number
}

// Sub-object for the `fixture` key inside /api/fixtures/{id} response.
// Mirrors what the backend `_parse(row)` returns plus the predictability field.
export type FixtureCore = {
  id: number
  home_team: string; away_team: string
  home_team_zh?: string | null
  away_team_zh?: string | null
  competition_id: number; competition_name: string
  competition_name_zh?: string | null
  competition_country?: string
  kickoff_utc: string
  status: 'pre' | 'live' | 'ft'
  predictability: Predictability
  // optional flags / scores when available
  is_friendly?: boolean
  is_cup?: boolean
  season_progress?: number | null
  home_team_id?: number | null
  away_team_id?: number | null
  season_id?: number | null
  score_home?: number | null
  score_away?: number | null
}

// Top-level response shape of /api/fixtures/{id}. NOT a Pick/Omit of FixtureSummary
// because the backend wraps fixture data in a `fixture` sub-object.
export type FixtureDetail = {
  fixture: FixtureCore
  home_team_obj: { id: number; name: string; stats: unknown; form: TeamForm | null }
  away_team_obj: { id: number; name: string; stats: unknown; form: TeamForm | null }
  prediction: Prediction | null
  odds: {
    ft_result: { pinnacle: BookmakerOdds | null; bet365: BookmakerOdds | null }
    asian_handicap_lines: AsianHandicapLine[]
  } | null
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
  home_team_zh?: string | null
  away_team_zh?: string | null
  competition_name: string; kickoff_utc: string
  competition_name_zh?: string | null
  market: string; bookmaker: string
  odds_home: number | null; odds_draw: number | null; odds_away: number | null
  drop_pct: number | null; drop_market: string | null; recorded_at: string
}

export interface ValueBetItem {
  fixture_id: number; home_team: string; away_team: string
  home_team_zh?: string | null
  away_team_zh?: string | null
  competition_name: string; kickoff_utc: string
  competition_name_zh?: string | null
  selection: 'home' | 'draw' | 'away'; edge_pct: number; prob: number; odds: number
}

export interface UserOut { id: number; email: string }
export interface Credentials { email: string; password: string }

type P = Record<string, string | number | boolean | undefined | null>

async function get<T>(path: string, params?: P): Promise<T> {
  const url = new URL('/api' + path, window.location.origin)
  if (params) Object.entries(params).forEach(([k, v]) => { if (v != null) url.searchParams.set(k, String(v)) })
  const res = await fetch(url.toString(), { credentials: 'include' })
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${path}`)
  return res.json()
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch('/api' + path, {
    method: 'POST',
    credentials: 'include',
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    const detail = await res.text().catch(() => '')
    throw new Error(`HTTP ${res.status}: ${detail || path}`)
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

async function put<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch('/api' + path, {
    method: 'PUT',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const detail = await res.text().catch(() => '')
    throw new Error(`HTTP ${res.status}: ${detail || path}`)
  }
  return res.json()
}

async function patch<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch('/api' + path, {
    method: 'PATCH',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const detail = await res.text().catch(() => '')
    throw new Error(`HTTP ${res.status}: ${detail || path}`)
  }
  return res.json()
}

async function del<T>(path: string): Promise<T> {
  const res = await fetch('/api' + path, {
    method: 'DELETE',
    credentials: 'include',
  })
  if (!res.ok) {
    const detail = await res.text().catch(() => '')
    throw new Error(`HTTP ${res.status}: ${detail || path}`)
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

export const api = {
  fixtures: (p: { date?: string; days_ahead?: number; leagues?: string; limit?: number; status?: string; predictability?: string; min_drop?: number; has_ai?: boolean; ignore_prefs?: boolean }) =>
    get<{ fixtures: FixtureSummary[]; total: number; cached_at: string | null }>('/fixtures', p),
  fixture: (id: number) => get<FixtureDetail>(`/fixtures/${id}`),
  competitions: () =>
    get<{ competitions: Array<{ id: number; name: string; name_zh?: string | null }> }>('/competitions'),
  droppingOdds: (p?: { min_drop?: number; market?: string; ignore_prefs?: boolean }) =>
    get<{ items: DroppingOddsItem[]; synced_at: string }>('/dropping-odds', p),
  valueBets: (p?: { min_edge?: number; ignore_prefs?: boolean }) =>
    get<{ items: ValueBetItem[] }>('/value-bets', p),
  history: (p?: { limit?: number; offset?: number; league?: number }) =>
    get<{ items: FixtureSummary[]; total: number }>('/history', p),
  triggerSync: () =>
    fetch('/api/sync/trigger', { method: 'POST', credentials: 'include' }).then(r => r.json() as Promise<{ started: boolean }>),
  auth: {
    signup: (c: Credentials) => post<UserOut>('/auth/signup', c),
    login:  (c: Credentials) => post<UserOut>('/auth/login', c),
    logout: () => post<void>('/auth/logout'),
    me:     () => get<UserOut>('/auth/me'),
  },
  myCompetitions: {
    get: () => get<{ competition_ids: number[] }>('/me/competitions'),
    put: (ids: number[]) => put<{ competition_ids: number[] }>('/me/competitions', { competition_ids: ids }),
  },
  myLocale: {
    get: () => get<{ locale: 'zh' | 'en' }>('/me/locale'),
    put: (locale: 'zh' | 'en') => put<{ locale: 'zh' | 'en' }>('/me/locale', { locale }),
  },
  oddsTimeseries: (fixtureId: number, params?: { window?: '24h' | '7d'; bookmaker?: string; market?: string }) =>
    get<OddsTimeseriesResponse>(`/fixtures/${fixtureId}/odds-timeseries`, params as P),
  mispricings: (p?: { date?: string; min_abs_edge?: number; limit?: number }) =>
    get<{ items: MispricingItem[]; date: string }>('/insights/mispricings', p),
  alerts: {
    list:    () => get<{ items: AlertItem[]; count: number }>('/me/alerts'),
    dismiss: (id: number) => post<void>(`/me/alerts/${id}/dismiss`),
    scan:    () => post<{ inserted: number }>('/me/alerts/scan'),
  },
  leagueStats: (competitionId: number, params?: { season_id?: number }) =>
    get<LeagueStats>(`/insights/leagues/${competitionId}`, params as P),
  h2h: (fixtureId: number, params?: { limit?: number }) =>
    get<{ fixture_id: number; items: H2HItem[]; count: number }>(`/fixtures/${fixtureId}/h2h`, params as P),
  alertSettings: {
    get: () => get<AlertSettings>('/me/alert-settings'),
    put: (s: AlertSettings) => put<AlertSettings>('/me/alert-settings', s),
  },
  backtest: {
    summary: (p?: { competition_id?: number; waypoint?: string; min_samples?: number }) =>
      get<BacktestSummary>('/backtest/summary', p as P),
    byLeague: (p?: { waypoint?: string; min_samples?: number }) =>
      get<BacktestByLeague>('/backtest/by-league', p as P),
    calibration: (p?: { competition_id?: number; waypoint?: string; bins?: number; min_per_bin?: number }) =>
      get<BacktestCalibration>('/backtest/calibration', p as P),
  },
  paperTrading: {
    house: (p?: { book_type?: string; start_bankroll?: number }) =>
      get<PaperHouseSummary>('/paper-trading/house', p as P),
    books: (p?: { include_archived?: boolean }) =>
      get<BookListResponse>('/paper-trading/books', p as P),
    createBook: (body: BookCreateBody) =>
      post<Book>('/paper-trading/books', body),
    updateBook: (id: number, body: BookUpdateBody) =>
      patch<Book>(`/paper-trading/books/${id}`, body),
    archiveBook: (id: number) =>
      del<Book>(`/paper-trading/books/${id}`),
  },
  signals: {
    active: (p?: { waypoint?: string; min_strength?: number; limit?: number; only_upcoming?: boolean }) =>
      get<SignalListResponse>('/signals/active', p as P),
    byType: (type: string, p?: { fixture_id?: number; competition_id?: number; waypoint?: string; min_strength?: number; limit?: number; only_upcoming?: boolean }) =>
      get<SignalListResponse>(`/signals/${encodeURIComponent(type)}`, p as P),
    catalog: (p?: { locale?: 'zh' | 'en' }) =>
      get<SignalCatalogResponse>('/signals/catalog', p as P),
    backtest: (type: string, body: SignalBacktestRequest) =>
      post<SignalBacktestResult>(`/signals/${encodeURIComponent(type)}/backtest`, body),
  },
}

export interface SignalItem {
  fixture_id: number
  signal_type: string
  signal_version: string | null
  waypoint: string
  scope: 'public' | 'member'
  strength: number | null
  captured_at: string
  value: Record<string, any>
  home_team: string | null
  away_team: string | null
  home_team_zh: string | null
  away_team_zh: string | null
  competition_id: number | null
  competition_name: string | null
  competition_name_zh: string | null
  kickoff_utc: string | null
  fixture_status: string | null
}

export interface SignalListResponse {
  signal_type?: string
  items: SignalItem[]
  count: number
}

// Phase 1 of signal-catalog-and-subscriptions PRD.
export interface SignalCatalogItem {
  signal_type: string
  signal_version: string
  scope: 'public' | 'member'
  description: string
  output_schema: Record<string, string>
  strength_formula: string
  failure_modes: string[]
  methodology_md: string | null
  methodology_updated_at: string | null
  stats_7d: {
    triggered: number
    avg_strength: number | null
    max_strength: number | null
  } | null
  // Reserved for Phase 4 (per-signal House Books). Always null in V1.
  house_book: null
}

export interface SignalCatalogResponse {
  locale: 'zh' | 'en'
  items: SignalCatalogItem[]
  count: number
}

// Phase 3 — signal-layer backtest (mirrors backend services/signals/backtest.py).
export interface SignalBacktestRequest {
  conditions?: {
    strength_min?: number
    filters?: { path: string; op: string; value: unknown }[]
  }
  window?: '7d' | '14d' | '30d'
  match_scope?: 'all' | 'my_leagues'
}

export interface SignalBacktestEquityPoint {
  date: string       // YYYY-MM-DD
  cum_pnl: number
}

export interface SignalBacktestResult {
  signal_type: string
  window: '7d' | '14d' | '30d'
  match_scope: 'all' | 'my_leagues'
  considered_count: number
  settled_count: number
  roi_pct: number | null
  hit_rate: number | null
  max_drawdown_pct: number | null
  equity_curve: SignalBacktestEquityPoint[]
}

// Phase 4b — per-book list with per-book summary (multi-curve ROI chart source).
export interface BookSummary {
  book_id:      number
  bets_settled: number
  bets_pending: number
  bets_voided:  number
  bankroll:     { start: number; current: number }
  metrics:      { roi_pct: number | null; win_rate: number | null }
  timeseries:   { settled_at: string; bankroll: number }[]
}

export interface Book {
  id:             number
  user_id:        number
  name:           string
  signal_type:    string
  signal_version: string
  conditions:     Record<string, any>
  starting_units: number
  match_scope:    'all' | 'my_leagues'
  scope:          'house' | 'personal'
  created_at:     string
  archived_at:    string | null
  summary:        BookSummary
}

export interface BookListResponse {
  items: Book[]
  count: number
}

// Phase 4c — CRUD bodies.
export interface BookCreateBody {
  name: string
  // Provide either fork_from OR (signal_type + signal_version):
  fork_from?: number
  signal_type?: string
  signal_version?: string
  conditions?: Record<string, any>
  starting_units?: number
  match_scope?: 'all' | 'my_leagues'
}

export interface BookUpdateBody {
  name?: string
  conditions?: Record<string, any>
  starting_units?: number
  match_scope?: 'all' | 'my_leagues'
}

export interface PaperHouseMetrics {
  roi_pct: number | null
  win_rate: number | null
}

export interface PaperHouseBankroll {
  start: number
  current: number
}

export interface PaperHouseTimePoint {
  settled_at: string
  bankroll: number
}

export interface PaperHouseSummary {
  book_type: string
  bets_settled: number
  bets_pending: number
  bets_voided: number
  bankroll: PaperHouseBankroll
  metrics: PaperHouseMetrics
  timeseries: PaperHouseTimePoint[]
}

export interface BacktestCalibrationBin {
  bin_index: number
  lower: number
  upper: number
  n: number
  predicted_avg: number | null
  actual_rate: number | null
  enough: boolean
}

export interface BacktestCalibration {
  model_id: string
  scope: { competition_id: number | null; waypoint: string }
  bins_count: number
  min_per_bin: number
  bins: BacktestCalibrationBin[]
}

export interface BacktestMetrics {
  samples: number
  top1_hit_rate: number | null
  top1_hit_rate_ci95: [number, number] | null
  brier: number | null
}

export interface BacktestSummary {
  model_id: string
  signal_version: string | null
  scope: { competition_id: number | null; waypoint: string }
  samples: number
  enough: boolean
  min_samples: number
  metrics: BacktestMetrics
}

export interface BacktestByLeagueItem {
  competition_id: number
  competition_name: string | null
  competition_name_zh: string | null
  samples: number
  enough: boolean
  top1_hit_rate: number | null
  top1_hit_rate_ci95: [number, number] | null
  brier: number | null
}

export interface BacktestByLeague {
  model_id: string
  scope: { waypoint: string }
  min_samples: number
  items: BacktestByLeagueItem[]
}

export interface AlertSettings {
  divergence_threshold: number
  enabled: boolean
}

export interface DivergencePayload {
  pinnacle_odds: { home: number; draw: number; away: number }
  bet365_odds:   { home: number; draw: number; away: number }
  pinnacle_implied_pct: { home: number; draw: number; away: number }
  bet365_implied_pct:   { home: number; draw: number; away: number }
  max_outcome: 'home' | 'draw' | 'away'
  max_delta_pct: number
}

export interface AlertItem {
  id: number
  fixture_id: number
  alert_type: string
  payload: DivergencePayload
  created_at: string
  expires_at: string
  home_team: string
  away_team: string
  home_team_zh: string | null
  away_team_zh: string | null
  competition_name: string
  competition_name_zh: string | null
  kickoff_utc: string
}

export interface LeagueStats {
  competition_id: number
  competition_name: string | null
  competition_name_zh: string | null
  season_id: number | null
  matches_played: number
  avg_goals: number
  home_win_pct: number
  draw_pct: number
  away_win_pct: number
  model_hit_rate_pct: number | null
  upset_pct: number | null
  predicted_count: number
}

export interface H2HItem {
  id: number
  kickoff_utc: string
  competition_id: number
  competition_name: string
  competition_name_zh: string | null
  home_team: string
  away_team: string
  home_team_id: number | null
  away_team_id: number | null
  home_team_zh: string | null
  away_team_zh: string | null
  score_home: number | null
  score_away: number | null
}

export interface OddsTimeseriesPoint {
  recorded_at: string
  drop_pct: number
  bookmaker: string
  market: string
}
export interface OddsTimeseriesResponse {
  fixture_id: number
  window: '24h' | '7d'
  bookmaker: string | null
  market: string | null
  points: OddsTimeseriesPoint[]
}

export interface MispricingItem {
  fixture_id: number
  home_team: string
  home_team_zh: string | null
  away_team: string
  away_team_zh: string | null
  competition_name: string
  competition_name_zh: string | null
  kickoff_utc: string
  predictability: Predictability
  selection: 'home' | 'draw' | 'away'
  model_prob_pct: number
  market_prob_pct: number
  delta_pct: number
  odds: number
}

export interface Competition { id: number; name: string; country?: string; }
export interface League { id: number; name?: string; country?: string; }
export interface Team { id: number; name: string; }

export interface Fixture {
  fixture_id: number;
  name?: string;
  kickoff_utc?: string;
  league?: League;
  closing?: number;
  opening?: number;
  drop_percentage?: number;
}

export interface OddsLine { closing?: number; opening?: number; peak?: number; }
export interface OddsByDirection { home: OddsLine; draw: OddsLine; away: OddsLine; }
export interface OddsHistory { markets: Record<string, Record<string, OddsByDirection>>; }

export interface AnalysisRecord {
  model_prob: { H: number; D: number; A: number };
  market_prob: { H: number | null; D: number | null; A: number | null };
  pick: "H" | "D" | "A";
  odds?: number;
  ev?: number;
  kelly?: number;
  confidence_stars: number;
  analyst_summary?: string | null;
  reviewer_verdict?: "pass" | "fail" | "skip" | null;
  run_id?: string | null;
  analyzed_at: string;
}

export interface FixtureDetail {
  fixture_id: number;
  name?: string;
  kickoff_utc?: string;
  league?: League;
  home_team?: Team;
  away_team?: Team;
  odds_history?: OddsHistory;
  h2h?: any[];
  stats_home?: Record<string, any>;
  stats_away?: Record<string, any>;
  trends?: Record<string, number>;
  analysis?: AnalysisRecord | null;
}

export type TrendType = "home_win" | "away_win" | "btts" | "over25";

export interface TrendItem {
  fixture_id: number;
  fixture_name?: string;
  probability: number;
  odds?: number;
  league?: League;
  kickoff_utc?: string;
}

export interface DroppingOdd {
  fixture_id: number;
  fixture_name?: string;
  starting_at?: string;
  league?: League;
  market_key?: string;
  opening?: number;
  closing?: number;
  drop_percentage?: number;
  bookmaker?: string;
}

export interface TeamStats {
  team_id: number;
  name: string;
  goals_for_avg?: number;
  goals_against_avg?: number;
  xg_for?: number;
  xg_against?: number;
}

export interface AnalysisRunResult { run_id: string; status: string; }

// ─── Match ────────────────────────────────────────────────────────────────────

export type MatchStatus = "pending" | "collected" | "analyzed" | "error";

export interface MatchMetadata {
  match_id: string;
  home_team: string;
  away_team: string;
  league: string;
  kickoff_time: string;
  provider_ids: Record<string, number>;
  collected_at?: string;
}

export interface MatchAnalysis {
  home_xg?: number | null;
  away_xg?: number | null;
  ah_recommendation?: string | null;
  confidence?: number | null;
  kelly_fraction?: number | null;
}

export interface Match {
  match_id: string;
  status: MatchStatus;
  metadata: MatchMetadata;
  raw_data: Record<string, unknown>;
  analysis: MatchAnalysis;
}

export interface MatchListResponse {
  items: Match[];
  total: number;
}

// ─── Pipeline ─────────────────────────────────────────────────────────────────

export interface PipelineLastResult {
  discovered: number;
  collected: number;
  analyzed: number;
  errors: number;
  duration_s?: number;
}

export interface PipelineStatus {
  running: boolean;
  last_result: PipelineLastResult | null;
}

// ─── Config ───────────────────────────────────────────────────────────────────

export interface ProvidersConfig {
  providers: Record<string, boolean>;
  analyst: { enabled: boolean };
  schedule: { interval_hours: number };
}

// ─── Leagues ─────────────────────────────────────────────────────────────────

export interface League {
  id: number;
  name: string;
  chinese_name: string;
}

export interface LeaguesResponse {
  available: League[];
}

// ─── WebSocket ────────────────────────────────────────────────────────────────

export type WsEventType =
  | "pipeline_start"
  | "pipeline_complete"
  | "match_collected"
  | "match_analyzed"
  | "match_error";

export interface WsEvent {
  type: WsEventType;
  payload: Record<string, unknown>;
}

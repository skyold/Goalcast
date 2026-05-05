export type ClusterType = string;

export interface AgentStatus {
  agent_id: string;
  role: string;
  cluster: ClusterType; // which of the 3 agent clusters this belongs to
  status: "running" | "idle" | "error" | "warning";
  task: string;
  last_active: string;
}

export interface PipelineState {
  pipeline: "rd" | "battle" | "start";
  mode: "full" | "semi";
  status: "running" | "idle" | "stopped" | "error";
  current_step: string;
  round: number;
  total: number;
}

export interface Alert {
  level: "warning" | "error" | "critical";
  agent_id: string;
  message: string;
  timestamp: string;
}

export type WsMessageType =
  | "agent_status"
  | "pipeline_progress"
  | "alert"
  | "result_created"
  | "board_update"
  | "pipeline_start"
  | "matches_found"
  | "match_step_start"
  | "match_result_ready"
  | "match_step_error"
  | "pipeline_complete";

export interface WsMessage {
  type: WsMessageType;
  payload: AgentStatus | PipelineState | Alert | ResultCreated | BoardUpdatePayload | Record<string, unknown>;
}

export interface ResultCreated {
  type: string;
  id: string;
  name: string;
}

export type ResultType = "factors" | "signals" | "hypotheses" | "backtests" | "skills";

export interface FactorResult {
  factor_id: string;
  name: string;
  category: string;
  status: string;
  ic_mean: number;
  ir: number;
  style_tags: string[];
  created: string;
}

export interface SignalResult {
  signal_id: string;
  name: string;
  status: string;
  sharpe: number;
  win_rate: number;
  style_tags: string[];
  created: string;
}

export interface HypothesisResult {
  hypothesis_id: string;
  text: string;
  mode: string;
  theme: string | null;
  status: string;
  created: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: string;
}

export interface ChatRequest {
  message: string;
  history: { role: string; content: string }[];
}

export interface AgentToolSchema {
  name: string;
  description?: string;
  input_schema?: Record<string, unknown>;
}

export interface AgentDetail {
  state: AgentStatus & { queue_reason?: string };
  components: {
    "IDENTITY.md": string;
    "AGENTS.md": string;
    "SOUL.md": string;
    "MEMORY.md": string;
    "TOOLS.md": string;
    skills: Array<{ name: string; content: string }>;
  };
  tools: AgentToolSchema[];
  token_stats?: {
    total_input_tokens: number;
    total_output_tokens: number;
    total_cost: number;
    recent_runs: TokenRecord[];
  };
}

export interface TokenRecord {
  run_id: string;
  agent_id: string;
  hypothesis_id: string;
  timestamp: string;
  rounds: number;
  input_tokens: number;
  output_tokens: number;
  cache_creation_tokens: number;
  cache_read_tokens: number;
  model: string;
  tool_calls: number;
  final_text_length: number;
  status: string;
  cost: number;
  total_tokens: number;
}

export interface TokenSummary {
  total_input_tokens: number;
  total_output_tokens: number;
  total_cache_creation_tokens: number;
  total_cache_read_tokens: number;
  total_tokens: number;
  total_cost: number;
  run_count: number;
  by_agent: Array<{
    agent_id: string;
    input_tokens: number;
    output_tokens: number;
    cache_creation_tokens: number;
    cache_read_tokens: number;
    total_tokens: number;
    cost: number;
    run_count: number;
  }>;
  by_day: Array<{
    date: string;
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
    cost: number;
    run_count: number;
  }>;
  recent_records: TokenRecord[];
}

export interface ColumnDef {
  key: string;
  label: string;
  render?: string;
  precision?: number;
  status_map?: Record<string, { color: string; text: string }>;
}

export interface DetailTab {
  label: string;
  field: string;
  format: "markdown" | "code" | "json" | "diff" | "chart_timeseries" | "agent_trace";
  language?: string;
}

export interface BoardTabDetail {
  mode: "json" | "tabs";
  tabs?: DetailTab[];
}

export interface BoardTabSource {
  provider: "default" | "rest" | "streaming" | "analytical" | "langgraph";
  endpoints?: {
    list: string;
    detail: string;
    history?: string;
  };
  list_response?: {
    items?: string;
    total?: string;
    page?: string;
    page_size?: string;
  };
  id_field: string;
  detail: BoardTabDetail;
}

export interface BoardTab {
  dir: string;
  label: string;
  columns: ColumnDef[];
  source?: BoardTabSource;
}

export interface ClusterConfig {
  key: string;
  label: string;
  color: string;
  desc: string;
}

export interface AppConfig {
  app: { name: string; subtitle: string };
  modules: {
    agents: boolean;
    board: boolean;
    tokens: boolean;
    chat: boolean;
    logs: boolean;
  };
  agents: {
    clusters: ClusterConfig[];
  };
  board: {
    tabs: BoardTab[];
  };
}

export type JsonRecord = Record<string, unknown> & { _filename: string };

export interface BoardUpdatePayload {
  dir: string;
  filename: string;
  action: "created" | "updated" | "deleted";
}

export type { PipelineControlRequest, HypothesisFormData } from "./extensions";

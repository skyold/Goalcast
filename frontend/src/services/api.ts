import type {
  AgentStatus,
  AgentDetail,
  PipelineState,
  FactorResult,
  SignalResult,
  HypothesisResult,
  HypothesisFormData,
  ChatRequest,
  ChatMessage,
  PipelineControlRequest,
  PaginatedResponse,
  TokenSummary,
  TokenRecord,
  AppConfig,
  JsonRecord,
} from "../types";

const BASE = "/api";

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
  return res.json();
}

export const api = {
  getAgentStatus: () => request<AgentStatus[]>("/agents/status"),
  getAgentDetail: (agent_id: string) => 
    request<AgentDetail>(`/agents/${encodeURIComponent(agent_id)}/detail`),

  getPipelineStatus: () => request<PipelineState[]>("/pipelines/status"),
  startPipeline: (body: PipelineControlRequest) =>
    request<{ message: string }>("/pipelines/start", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  stopPipeline: (body: { pipeline: string }) =>
    request<{ message: string }>("/pipelines/stop", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  getResults: (type: string, params?: Record<string, string>) => {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return request<PaginatedResponse<FactorResult | SignalResult | HypothesisResult>>(
      `/results/${type}${qs}`
    );
  },

  getResultDetail: (type: string, id: string) =>
    request<Record<string, unknown>>(`/results/${type}/${id}`),

  submitHypothesis: (body: HypothesisFormData) =>
    request<{ hypothesis_id: string }>("/hypotheses/", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  sendChat: (body: ChatRequest) =>
    request<ChatMessage>("/chat/", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  getTokenSummary: (params?: { start_date?: string; end_date?: string }) => {
    const qs = params ? "?" + new URLSearchParams(params as Record<string, string>).toString() : "";
    return request<TokenSummary>(`/tokens/summary${qs}`);
  },

  getTokenRecords: (params?: {
    agent_id?: string;
    hypothesis_id?: string;
    start_date?: string;
    end_date?: string;
    limit?: number;
    offset?: number;
  }) => {
    const qs = params ? "?" + new URLSearchParams(params as Record<string, string>).toString() : "";
    return request<{ items: TokenRecord[]; total: number; limit: number; offset: number }>(
      `/tokens/records${qs}`
    );
  },

  getAgentTokenStats: (agent_id: string) =>
    request<{
      total_records: number;
      total_input_tokens: number;
      total_output_tokens: number;
      total_cost: number;
      recent_runs: TokenRecord[];
    }>(`/tokens/agents/${encodeURIComponent(agent_id)}`),

  getConfig: () => request<AppConfig>("/config"),

  getBoardList: (dir: string, params?: { page?: number; page_size?: number }) => {
    const qs = params
      ? "?" + new URLSearchParams(params as Record<string, string>).toString()
      : "";
    return request<{ items: JsonRecord[]; total: number; page: number; page_size: number }>(
      `/board/${encodeURIComponent(dir)}${qs}`
    );
  },

  getBoardItem: (dir: string, filename: string) =>
    request<JsonRecord>(
      `/board/${encodeURIComponent(dir)}/${encodeURIComponent(filename)}`
    ),

  getBoardListCustom: (
    url: string,
    params?: { page?: number; page_size?: number },
  ) => {
    const qs = params
      ? "?" + new URLSearchParams(params as Record<string, string>).toString()
      : "";
    return request<{ items: Record<string, unknown>[]; total: number; page: number; page_size: number }>(
      `${url}${qs}`,
    );
  },

  getBoardItemCustom: (url: string) =>
    request<Record<string, unknown>>(`${url}`),
};

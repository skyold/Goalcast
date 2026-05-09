import type {
  Match,
  MatchListResponse,
  PipelineStatus,
  ProvidersConfig,
  LeaguesResponse,
} from "../types";

const BASE = "/api";

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

// ─── Matches ──────────────────────────────────────────────────────────────────

export const getMatches = (params?: {
  league?: string;
  date?: string;
  status?: string;
}): Promise<MatchListResponse> => {
  const qs = params
    ? "?" +
      new URLSearchParams(
        Object.fromEntries(
          Object.entries(params).filter(([, v]) => v != null)
        ) as Record<string, string>
      ).toString()
    : "";
  return request<MatchListResponse>(`/matches${qs}`);
};

export const getMatch = (matchId: string): Promise<Match> =>
  request<Match>(`/matches/${encodeURIComponent(matchId)}`);

// ─── Pipeline ─────────────────────────────────────────────────────────────────

export const getPipelineStatus = (): Promise<PipelineStatus> =>
  request<PipelineStatus>("/pipeline/status");

export const runPipeline = (): Promise<{ message: string }> =>
  request<{ message: string }>("/pipeline/run", { method: "POST", body: "{}" });

export const getLeagues = (): Promise<LeaguesResponse> =>
  request<LeaguesResponse>("/pipeline/leagues");

// ─── Config ───────────────────────────────────────────────────────────────────

export const getProviders = (): Promise<ProvidersConfig> =>
  request<ProvidersConfig>("/config/providers");

export const updateProviders = (body: {
  providers?: Record<string, boolean>;
  analyst?: boolean;
}): Promise<{ message: string; config: ProvidersConfig }> =>
  request("/config/providers", {
    method: "POST",
    body: JSON.stringify(body),
  });

export const getSchedule = (): Promise<{ interval_hours: number }> =>
  request("/config/schedule");

export const updateSchedule = (
  interval_hours: number
): Promise<{ interval_hours: number }> =>
  request("/config/schedule", {
    method: "POST",
    body: JSON.stringify({ interval_hours }),
  });

// ─── Health ───────────────────────────────────────────────────────────────────

export const getHealth = (): Promise<{ status: string }> =>
  request("/health");

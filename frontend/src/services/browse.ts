import type {
  Competition, Fixture, FixtureDetail, TrendItem, TrendType,
  DroppingOdd, TeamStats, AnalysisRunResult, AnalysisRecord,
} from "../types/browse";

const BASE = "/api";

async function get<T>(url: string): Promise<T> {
  const res = await fetch(`${BASE}${url}`, { headers: { "Content-Type": "application/json" } });
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`);
  return res.json();
}

async function getOrNull<T>(url: string): Promise<T | null> {
  const res = await fetch(`${BASE}${url}`, { headers: { "Content-Type": "application/json" } });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`);
  return res.json();
}

async function post<T>(url: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`);
  return res.json();
}

export const browseApi = {
  getCompetitions: () => get<Competition[]>("/competitions"),
  getFixtures: (params: { date: string; competitionId?: number }) => {
    const q = new URLSearchParams({ date: params.date });
    if (params.competitionId) q.set("competition_id", String(params.competitionId));
    return get<Fixture[]>(`/fixtures?${q.toString()}`);
  },
  getFixtureDetail: (id: number) => getOrNull<FixtureDetail>(`/fixtures/${id}`),
  getTrends: (type: TrendType) => get<TrendItem[]>(`/trends/${type}`),
  getDropping: (opts: { market?: string; minDrop?: number; window?: "1h" | "6h" | "24h" } = {}) => {
    const q = new URLSearchParams();
    if (opts.market) q.set("market", opts.market);
    if (opts.minDrop != null) q.set("min_drop", String(opts.minDrop));
    if (opts.window) q.set("window", opts.window);
    const qs = q.toString();
    return get<DroppingOdd[]>(`/odds/dropping${qs ? "?" + qs : ""}`);
  },
  getTeam: (id: number) => getOrNull<TeamStats>(`/teams/${id}`),
  getStandings: (leagueId: number) => getOrNull<any[]>(`/leagues/${leagueId}/standings`),
  getAnalysisRecent: (limit = 20) =>
    get<Array<{ fixture_id: number; name?: string; analysis: AnalysisRecord | null }>>(
      `/analysis/recent?limit=${limit}`,
    ),
  runAnalysis: () => post<AnalysisRunResult>("/analysis/run"),
};

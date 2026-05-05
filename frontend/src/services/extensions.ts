import type { PipelineControlRequest, HypothesisFormData } from "../types/extensions";
import type { PipelineState } from "../types";

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
  return res.json() as Promise<T>;
}

export const extApi = {
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

  submitHypothesis: (body: HypothesisFormData) =>
    request<{ hypothesis_id: string }>("/hypotheses/", {
      method: "POST",
      body: JSON.stringify(body),
    }),
};

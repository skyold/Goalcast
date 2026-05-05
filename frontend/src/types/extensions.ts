export interface PipelineControlRequest {
  pipeline: "rd" | "battle";
  mode?: "full" | "semi";
  theme?: string;
  hypothesis?: string;
}

export interface HypothesisFormData {
  hypothesis: string;
  mode: "full" | "semi";
  theme: string | null;
}

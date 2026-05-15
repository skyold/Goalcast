import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import AnalysisReportsPage from "../AnalysisReportsPage";
import { browseApi } from "../../services/browse";

vi.mock("../../services/browse");

describe("AnalysisReportsPage", () => {
  beforeEach(() => {
    (browseApi.getAnalysisRecent as any).mockResolvedValue([
      { fixture_id: 1, name: "Arsenal vs Chelsea",
        analysis: { pick: "H", ev: 0.064, confidence_stars: 4,
                    model_prob: { H: 0.62, D: 0.2, A: 0.18 },
                    market_prob: { H: null, D: null, A: null }, analyzed_at: "" } },
    ]);
    (browseApi.runAnalysis as any).mockResolvedValue({ run_id: "0099", status: "started" });
  });

  it("loads recent analyses", async () => {
    render(<MemoryRouter><AnalysisReportsPage /></MemoryRouter>);
    await waitFor(() => expect(screen.getByText(/Arsenal/)).toBeInTheDocument());
  });

  it("triggers run on button click", async () => {
    render(<MemoryRouter><AnalysisReportsPage /></MemoryRouter>);
    fireEvent.click(screen.getByText(/触发新一轮/));
    await waitFor(() => expect(browseApi.runAnalysis).toHaveBeenCalled());
  });
});

import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import FixtureDetailDrawer from "../FixtureDetailDrawer";
import { browseApi } from "../../services/browse";

vi.mock("../../services/browse");

describe("FixtureDetailDrawer", () => {
  beforeEach(() => {
    (browseApi.getFixtureDetail as any).mockResolvedValue({
      fixture_id: 1,
      home_team: { id: 11, name: "Arsenal" },
      away_team: { id: 22, name: "Chelsea" },
      kickoff_utc: "2026-05-14T20:00:00Z",
      analysis: {
        pick: "H", ev: 0.064, confidence_stars: 4,
        model_prob: { H: 0.62, D: 0.2, A: 0.18 },
        market_prob: { H: null, D: null, A: null }, analyzed_at: "",
      },
    });
  });

  it("renders fixture name and analysis when open", async () => {
    render(<MemoryRouter><FixtureDetailDrawer fixtureId={1} open onClose={() => {}} /></MemoryRouter>);
    await waitFor(() => expect(screen.getByText(/Arsenal/)).toBeInTheDocument());
    expect(screen.getByText(/Chelsea/)).toBeInTheDocument();
    expect(screen.getByText(/主胜/)).toBeInTheDocument();
  });

  it("does not fetch when closed", () => {
    render(<MemoryRouter><FixtureDetailDrawer fixtureId={1} open={false} onClose={() => {}} /></MemoryRouter>);
    expect(browseApi.getFixtureDetail).not.toHaveBeenCalled();
  });
});

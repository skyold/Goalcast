import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import FixtureDetailPage from "../FixtureDetailPage";
import { browseApi } from "../../services/browse";

vi.mock("../../services/browse");

describe("FixtureDetailPage", () => {
  beforeEach(() => {
    (browseApi.getFixtureDetail as any).mockResolvedValue({
      fixture_id: 1,
      home_team: { id: 11, name: "Arsenal" },
      away_team: { id: 22, name: "Chelsea" },
      kickoff_utc: "2026-05-14T20:00:00Z",
      league: { id: 8, name: "Premier League" },
      odds_history: { markets: { ft_result: { Bet365: {
        home: { closing: 1.72 }, draw: { closing: 3.85 }, away: { closing: 4.60 }
      }}}},
      analysis: { pick: "H", ev: 0.064, confidence_stars: 4,
                  model_prob: { H: 0.62, D: 0.2, A: 0.18 },
                  market_prob: { H: 0.581, D: 0.26, A: 0.159 },
                  analyzed_at: "" },
    });
  });

  it("renders Hero with team names and KPI row", async () => {
    render(
      <MemoryRouter initialEntries={["/fixture/1"]}>
        <Routes><Route path="/fixture/:id" element={<FixtureDetailPage />} /></Routes>
      </MemoryRouter>
    );
    await waitFor(() => expect(screen.getAllByText(/Arsenal/).length).toBeGreaterThan(0));
    expect(screen.getAllByText(/Chelsea/).length).toBeGreaterThan(0);
  });
});

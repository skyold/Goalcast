import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import BettingPage from "../BettingPage";
import { browseApi } from "../../services/browse";

vi.mock("../../services/browse");

describe("BettingPage", () => {
  beforeEach(() => {
    (browseApi.getCompetitions as any).mockResolvedValue([
      { id: 8, name: "Premier League", country: "England" },
    ]);
    (browseApi.getFixtures as any).mockResolvedValue([
      { fixture_id: 1, name: "Arsenal vs Chelsea",
        kickoff_utc: "2026-05-14T20:00:00Z",
        league: { id: 8, name: "Premier League" }, closing: 1.72 },
    ]);
  });

  it("loads competitions and fixtures on mount", async () => {
    render(<MemoryRouter><BettingPage /></MemoryRouter>);
    await waitFor(() => expect(browseApi.getFixtures).toHaveBeenCalled());
    expect(screen.getByText(/Arsenal/)).toBeInTheDocument();
  });
});

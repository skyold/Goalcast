import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import LeaguePage from "../LeaguePage";
import { browseApi } from "../../services/browse";

vi.mock("../../services/browse");

describe("LeaguePage", () => {
  beforeEach(() => {
    (browseApi.getCompetitions as any).mockResolvedValue([
      { id: 8, name: "Premier League", country: "England" },
    ]);
    (browseApi.getFixtures as any).mockResolvedValue([
      { fixture_id: 1, name: "Arsenal vs Chelsea",
        kickoff_utc: "2026-05-14T20:00:00Z", league: { id: 8, name: "PL" }, closing: 1.72 },
    ]);
    (browseApi.getStandings as any).mockResolvedValue(null);
  });

  it("renders league name and upcoming fixtures", async () => {
    render(
      <MemoryRouter initialEntries={["/league/8"]}>
        <Routes><Route path="/league/:id" element={<LeaguePage />} /></Routes>
      </MemoryRouter>
    );
    await waitFor(() => expect(screen.getAllByText(/Premier League/)[0]).toBeInTheDocument());
    expect(screen.getByText(/Arsenal/)).toBeInTheDocument();
  });
});

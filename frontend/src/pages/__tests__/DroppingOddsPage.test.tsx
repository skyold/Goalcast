import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import DroppingOddsPage from "../DroppingOddsPage";
import { browseApi } from "../../services/browse";

vi.mock("../../services/browse");

describe("DroppingOddsPage", () => {
  beforeEach(() => {
    (browseApi.getDropping as any).mockResolvedValue([
      { fixture_id: 1, fixture_name: "Arsenal vs Chelsea",
        starting_at: "2026-05-14T20:00:00Z",
        league: { name: "PL" }, bookmaker: "Bet365",
        opening: 1.87, closing: 1.72, drop_percentage: -8.0 },
    ]);
  });

  it("loads dropping odds and renders row", async () => {
    render(<MemoryRouter><DroppingOddsPage /></MemoryRouter>);
    await waitFor(() => expect(screen.getByText(/Arsenal/)).toBeInTheDocument());
    expect(screen.getByText(/-8/)).toBeInTheDocument();
  });

  it("changes min_drop when chip clicked", async () => {
    render(<MemoryRouter><DroppingOddsPage /></MemoryRouter>);
    await waitFor(() => expect(browseApi.getDropping).toHaveBeenCalled());
    fireEvent.click(screen.getByText("≥12%"));
    await waitFor(() => {
      const last = (browseApi.getDropping as any).mock.calls.at(-1)[0];
      expect(last.minDrop).toBe(12);
    });
  });
});

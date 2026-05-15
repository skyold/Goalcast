import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import TrendsPage from "../TrendsPage";
import { browseApi } from "../../services/browse";

vi.mock("../../services/browse");

describe("TrendsPage", () => {
  beforeEach(() => {
    (browseApi.getTrends as any).mockResolvedValue([
      { fixture_id: 1, fixture_name: "Man City vs Newcastle", probability: 0.72, odds: 1.45 },
    ]);
  });

  it("renders trend cards", async () => {
    render(
      <MemoryRouter initialEntries={["/trends/home_win"]}>
        <Routes><Route path="/trends/:type" element={<TrendsPage />} /></Routes>
      </MemoryRouter>
    );
    await waitFor(() => expect(screen.getByText(/Man City/)).toBeInTheDocument());
    expect(screen.getByText(/72/)).toBeInTheDocument();
  });
});

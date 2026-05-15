import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import TeamPage from "../TeamPage";
import { browseApi } from "../../services/browse";

vi.mock("../../services/browse");

describe("TeamPage", () => {
  beforeEach(() => {
    (browseApi.getTeam as any).mockResolvedValue({
      team_id: 11, name: "Arsenal", goals_for_avg: 2.1, xg_for: 2.24,
    });
  });

  it("renders team header and stats", async () => {
    render(
      <MemoryRouter initialEntries={["/team/11"]}>
        <Routes><Route path="/team/:id" element={<TeamPage />} /></Routes>
      </MemoryRouter>
    );
    await waitFor(() => expect(screen.getByText(/Arsenal/)).toBeInTheDocument());
    expect(screen.getByText(/2\.1/)).toBeInTheDocument();
  });

  it("shows not-found alert when team is null", async () => {
    (browseApi.getTeam as any).mockResolvedValue(null);
    render(
      <MemoryRouter initialEntries={["/team/999"]}>
        <Routes><Route path="/team/:id" element={<TeamPage />} /></Routes>
      </MemoryRouter>
    );
    await waitFor(() => expect(screen.getByText(/未找到/)).toBeInTheDocument());
  });
});

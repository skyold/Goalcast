import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { MemoryRouter } from "react-router-dom";
import SettingsPage from "../SettingsPage";

describe("SettingsPage", () => {
  it("renders settings sections", () => {
    render(<MemoryRouter><SettingsPage /></MemoryRouter>);
    expect(screen.getByText(/OddAlerts API/)).toBeInTheDocument();
    expect(screen.getByText(/分析参数/)).toBeInTheDocument();
    expect(screen.getAllByText(/Kelly/i).length).toBeGreaterThan(0);
  });

  it("legacy section shows deletion label", () => {
    render(<MemoryRouter><SettingsPage /></MemoryRouter>);
    expect(screen.getByText(/FootyStats/)).toBeInTheDocument();
    expect(screen.getAllByText(/已删除/).length).toBeGreaterThan(0);
  });
});

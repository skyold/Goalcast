import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import LeagueTree from "../LeagueTree";
import type { Competition } from "../../types/browse";

const comps: Competition[] = [
  { id: 8, name: "Premier League", country: "England" },
  { id: 9, name: "Championship", country: "England" },
  { id: 564, name: "La Liga", country: "Spain" },
];

describe("LeagueTree", () => {
  it("groups by country", () => {
    render(<LeagueTree competitions={comps} onSelect={() => {}} />);
    expect(screen.getByText("England")).toBeInTheDocument();
    expect(screen.getByText("Spain")).toBeInTheDocument();
  });

  it("filters by search query", () => {
    render(<LeagueTree competitions={comps} onSelect={() => {}} />);
    fireEvent.change(screen.getByPlaceholderText(/搜索/), { target: { value: "Liga" } });
    expect(screen.queryByText("Premier League")).toBeNull();
    expect(screen.getByText("La Liga")).toBeInTheDocument();
  });

  it("fires onSelect when a league is clicked", () => {
    const onSelect = vi.fn();
    render(<LeagueTree competitions={comps} onSelect={onSelect} />);
    fireEvent.click(screen.getByText("Premier League"));
    expect(onSelect).toHaveBeenCalledWith(8);
  });
});

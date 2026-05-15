import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import FixtureCard from "../FixtureCard";
import type { Fixture } from "../../types/browse";

const f: Fixture = {
  fixture_id: 1,
  name: "Arsenal vs Chelsea",
  kickoff_utc: "2026-05-14T20:00:00Z",
  league: { id: 8, name: "Premier League", country: "England" },
  closing: 1.72,
  opening: 1.87,
  drop_percentage: -8.0,
};

describe("FixtureCard", () => {
  it("renders teams and odds", () => {
    render(<FixtureCard fixture={f} onClick={() => {}} />);
    expect(screen.getByText(/Arsenal/)).toBeInTheDocument();
    expect(screen.getByText(/Chelsea/)).toBeInTheDocument();
    expect(screen.getByText("1.72")).toBeInTheDocument();
  });

  it("shows drop percentage", () => {
    render(<FixtureCard fixture={f} onClick={() => {}} />);
    expect(screen.getByText(/-8/)).toBeInTheDocument();
  });

  it("fires onClick with fixture id", () => {
    const onClick = vi.fn();
    const { container } = render(<FixtureCard fixture={f} onClick={onClick} />);
    fireEvent.click(container.querySelector(".fixture-card")!);
    expect(onClick).toHaveBeenCalledWith(1);
  });
});

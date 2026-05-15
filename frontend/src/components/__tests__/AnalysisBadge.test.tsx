import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import AnalysisBadge from "../AnalysisBadge";

describe("AnalysisBadge", () => {
  it("renders EV positive", () => {
    render(<AnalysisBadge ev={0.064} stars={4} pick="H" />);
    expect(screen.getByText(/\+6\.4%/)).toBeInTheDocument();
    expect(screen.getByText(/主胜/)).toBeInTheDocument();
  });

  it("renders stars count", () => {
    const { container } = render(<AnalysisBadge ev={0.03} stars={3} pick="A" />);
    expect(container.querySelectorAll(".star.on")).toHaveLength(3);
  });

  it("renders placeholder when no analysis", () => {
    render(<AnalysisBadge />);
    expect(screen.getByText(/观望/)).toBeInTheDocument();
  });
});

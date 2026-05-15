import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import OddsCurveChart from "../OddsCurveChart";

describe("OddsCurveChart", () => {
  it("renders an SVG polyline for given odds points", () => {
    const points = [
      { t: "2026-05-14T10:00:00Z", value: 2.1 },
      { t: "2026-05-14T12:00:00Z", value: 2.0 },
      { t: "2026-05-14T14:00:00Z", value: 1.85 },
      { t: "2026-05-14T16:00:00Z", value: 1.9 },
    ];
    const { container } = render(<OddsCurveChart points={points} />);
    const svg = container.querySelector("svg.odds-curve");
    expect(svg).not.toBeNull();
    const polyline = container.querySelector("polyline");
    expect(polyline).not.toBeNull();
    const ptsAttr = polyline?.getAttribute("points") ?? "";
    expect(ptsAttr.split(" ").filter(Boolean).length).toBe(4);
  });

  it("renders empty state when no points", () => {
    render(<OddsCurveChart points={[]} />);
    expect(screen.getByText(/暂无数据/)).toBeInTheDocument();
  });
});

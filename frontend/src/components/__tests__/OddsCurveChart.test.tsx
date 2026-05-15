import { render } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import OddsCurveChart from "../OddsCurveChart";

describe("OddsCurveChart", () => {
  it("renders three polylines for H/D/A", () => {
    const data = {
      home: [1.87, 1.85, 1.80, 1.75, 1.72],
      draw: [3.80, 3.82, 3.85, 3.85, 3.85],
      away: [4.40, 4.45, 4.50, 4.55, 4.60],
    };
    const { container } = render(<OddsCurveChart data={data} />);
    expect(container.querySelectorAll("polyline")).toHaveLength(3);
  });

  it("renders placeholder when no data", () => {
    const { container } = render(<OddsCurveChart data={null} />);
    expect(container.textContent).toMatch(/无数据/);
  });
});

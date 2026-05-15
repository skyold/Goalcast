import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect } from "vitest";
import MobileTabBar from "../MobileTabBar";

describe("MobileTabBar", () => {
  it("renders 5 tabs", () => {
    render(<MemoryRouter><MobileTabBar /></MemoryRouter>);
    expect(screen.getByText(/浏览/)).toBeInTheDocument();
    expect(screen.getByText(/跌水/)).toBeInTheDocument();
    expect(screen.getByText(/趋势/)).toBeInTheDocument();
    expect(screen.getByText(/推荐/)).toBeInTheDocument();
    expect(screen.getByText(/我的/)).toBeInTheDocument();
  });
});

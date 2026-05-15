import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect } from "vitest";
import SideNav from "../SideNav";

describe("SideNav", () => {
  it("renders Browse, Analysis, My groups", () => {
    render(<MemoryRouter><SideNav /></MemoryRouter>);
    expect(screen.getByText("浏览")).toBeInTheDocument();
    expect(screen.getByText("分析")).toBeInTheDocument();
    expect(screen.getByText("我的")).toBeInTheDocument();
  });
});

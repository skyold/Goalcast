import { describe, it, expect, beforeEach } from "vitest";
import { useFavorites } from "../favorites";

describe("favorites store", () => {
  beforeEach(() => {
    localStorage.clear();
    useFavorites.setState({ fixtures: [], leagues: [], teams: [] });
  });

  it("adds and removes fixture favorite", () => {
    useFavorites.getState().toggleFixture(1);
    expect(useFavorites.getState().fixtures).toContain(1);
    useFavorites.getState().toggleFixture(1);
    expect(useFavorites.getState().fixtures).not.toContain(1);
  });

  it("persists to localStorage", () => {
    useFavorites.getState().toggleLeague(8);
    const raw = localStorage.getItem("goalcast.favorites");
    expect(raw).toContain("8");
  });
});

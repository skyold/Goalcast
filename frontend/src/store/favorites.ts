import { create } from "zustand";
import { persist } from "zustand/middleware";

interface FavoritesState {
  fixtures: number[];
  leagues: number[];
  teams: number[];
  toggleFixture: (id: number) => void;
  toggleLeague: (id: number) => void;
  toggleTeam: (id: number) => void;
}

function toggle(arr: number[], id: number): number[] {
  return arr.includes(id) ? arr.filter((v) => v !== id) : [...arr, id];
}

export const useFavorites = create<FavoritesState>()(
  persist(
    (set) => ({
      fixtures: [],
      leagues: [],
      teams: [],
      toggleFixture: (id) => set((s) => ({ fixtures: toggle(s.fixtures, id) })),
      toggleLeague: (id) => set((s) => ({ leagues: toggle(s.leagues, id) })),
      toggleTeam: (id) => set((s) => ({ teams: toggle(s.teams, id) })),
    }),
    { name: "goalcast.favorites" },
  ),
);

// frontend/src/lib/store.ts — add theme + density on top of existing store
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface SyncStatus { synced_at: string | null; is_syncing: boolean }
export type Theme = 'A' | 'B' | 'C'
export type Density = 'compact' | 'standard' | 'loose'

interface AppStore {
  selectedLeagues: number[]
  selectedDate: string
  syncStatus: SyncStatus
  theme: Theme
  density: Density
  toggleLeague: (id: number) => void
  setDate: (date: string) => void
  setSyncStatus: (s: Partial<SyncStatus>) => void
  setTheme: (t: Theme) => void
  setDensity: (d: Density) => void
}

const today = () => new Date().toISOString().split('T')[0]

export const useStore = create<AppStore>()(
  persist(
    (set) => ({
      selectedLeagues: [],
      selectedDate: today(),
      syncStatus: { synced_at: null, is_syncing: false },
      theme: 'A',
      density: 'standard',
      toggleLeague: (id) => set((s) => ({
        selectedLeagues: s.selectedLeagues.includes(id)
          ? s.selectedLeagues.filter((x) => x !== id)
          : [...s.selectedLeagues, id],
      })),
      setDate: (date) => set({ selectedDate: date }),
      setSyncStatus: (s) => set((prev) => ({ syncStatus: { ...prev.syncStatus, ...s } })),
      setTheme: (theme) => set({ theme }),
      setDensity: (density) => set({ density }),
    }),
    {
      name: 'goalcast-store',
      partialize: (s) => ({
        selectedLeagues: s.selectedLeagues,
        theme: s.theme,
        density: s.density,
      }),
    }
  )
)

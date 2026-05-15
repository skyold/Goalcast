import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface SyncStatus { synced_at: string | null; is_syncing: boolean }

interface AppStore {
  selectedLeagues: number[]; selectedDate: string; syncStatus: SyncStatus
  toggleLeague: (id: number) => void
  setDate: (date: string) => void
  setSyncStatus: (s: Partial<SyncStatus>) => void
}

const today = () => new Date().toISOString().split('T')[0]

export const useStore = create<AppStore>()(
  persist(
    (set) => ({
      selectedLeagues: [], selectedDate: today(),
      syncStatus: { synced_at: null, is_syncing: false },
      toggleLeague: (id) => set((s) => ({
        selectedLeagues: s.selectedLeagues.includes(id)
          ? s.selectedLeagues.filter((x) => x !== id)
          : [...s.selectedLeagues, id],
      })),
      setDate: (date) => set({ selectedDate: date }),
      setSyncStatus: (s) => set((prev) => ({ syncStatus: { ...prev.syncStatus, ...s } })),
    }),
    { name: 'goalcast-store', partialize: (s) => ({ selectedLeagues: s.selectedLeagues }) }
  )
)

// Server-side competition whitelist hook. Use when user is logged in:
//   const { ids, save } = useMyLeagues()
// `ids` is the saved set (null while loading). `save` replaces the whole set.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './api'
import { useAuth } from './auth'

const KEY = ['me', 'competitions'] as const

export function useMyLeagues() {
  const { user } = useAuth()
  const qc = useQueryClient()

  const q = useQuery({
    queryKey: KEY,
    queryFn: () => api.myCompetitions.get(),
    enabled: !!user,
    staleTime: 60_000,
  })

  const save = useMutation({
    mutationFn: (ids: number[]) => api.myCompetitions.put(ids),
    onSuccess: (data) => {
      qc.setQueryData(KEY, data)
      // Data endpoints filter on the server side; invalidate caches that depend
      // on the prefs so the UI re-fetches.
      qc.invalidateQueries({ queryKey: ['fixtures'] })
      qc.invalidateQueries({ queryKey: ['dropping-odds'] })
      qc.invalidateQueries({ queryKey: ['value-bets'] })
      qc.invalidateQueries({ queryKey: ['fix-count'] })
      qc.invalidateQueries({ queryKey: ['drop-top'] })
      qc.invalidateQueries({ queryKey: ['value-top'] })
      qc.invalidateQueries({ queryKey: ['fix-upcoming'] })
    },
  })

  return {
    ids: q.data?.competition_ids ?? null,
    isLoading: q.isLoading,
    save,
  }
}

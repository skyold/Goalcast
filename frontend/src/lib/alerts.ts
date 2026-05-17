// Active alerts hook. Refetches every 60s so the bell badge stays fresh while
// the user is on the page. Dismiss mutation invalidates the list so the badge
// count drops immediately.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, type AlertSettings } from './api'
import { useAuth } from './auth'

const KEY = ['me', 'alerts'] as const
const SETTINGS_KEY = ['me', 'alert-settings'] as const

export function useAlerts() {
  const { user } = useAuth()
  const qc = useQueryClient()

  const q = useQuery({
    queryKey: KEY,
    queryFn: () => api.alerts.list(),
    enabled: !!user,
    refetchInterval: 60_000,        // 1 minute background poll
    staleTime: 30_000,
  })

  const dismiss = useMutation({
    mutationFn: (id: number) => api.alerts.dismiss(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  })

  const scan = useMutation({
    mutationFn: () => api.alerts.scan(),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  })

  return {
    items: q.data?.items ?? [],
    count: q.data?.count ?? 0,
    isLoading: q.isLoading,
    dismiss,
    scan,
  }
}

export function useAlertSettings() {
  const { user } = useAuth()
  const qc = useQueryClient()

  const q = useQuery({
    queryKey: SETTINGS_KEY,
    queryFn: () => api.alertSettings.get(),
    enabled: !!user,
    staleTime: 5 * 60_000,
  })

  const save = useMutation({
    mutationFn: (s: AlertSettings) => api.alertSettings.put(s),
    onSuccess: (data) => {
      qc.setQueryData(SETTINGS_KEY, data)
      qc.invalidateQueries({ queryKey: KEY })
    },
  })

  return {
    settings: q.data ?? null,
    isLoading: q.isLoading,
    save,
  }
}

// React-query backed auth hook. `useAuth()` returns `{user, isLoading}`, plus
// mutation helpers `signup` / `login` / `logout` that invalidate the `auth` key
// so consumers re-render with the new state.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, type Credentials, type UserOut } from './api'

const KEY = ['auth', 'me'] as const

export function useAuth() {
  const qc = useQueryClient()

  const meQ = useQuery<UserOut | null>({
    queryKey: KEY,
    // 401 is the "not logged in" signal — convert to null instead of error.
    queryFn: async () => {
      try { return await api.auth.me() }
      catch (e: unknown) {
        if (e instanceof Error && e.message.startsWith('HTTP 401')) return null
        throw e
      }
    },
    retry: false,
    staleTime: 5 * 60 * 1000,
  })

  const signup = useMutation({
    mutationFn: (c: Credentials) => api.auth.signup(c),
    onSuccess: (u) => qc.setQueryData(KEY, u),
  })
  const login = useMutation({
    mutationFn: (c: Credentials) => api.auth.login(c),
    onSuccess: (u) => qc.setQueryData(KEY, u),
  })
  const logout = useMutation({
    mutationFn: () => api.auth.logout(),
    onSuccess: () => qc.setQueryData(KEY, null),
  })

  return {
    user: meQ.data ?? null,
    isLoading: meQ.isLoading,
    signup,
    login,
    logout,
  }
}

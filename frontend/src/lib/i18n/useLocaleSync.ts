// Sync the user's server-side locale preference into the in-memory store on
// login. Anonymous users keep whatever localStorage / navigator detected.
// Mount this at the app root once.
import { useEffect } from 'react'
import { api } from '../api'
import { useAuth } from '../auth'
import { getLocale, setLocale, type Locale } from './index'

export function useLocaleSync() {
  const { user } = useAuth()

  useEffect(() => {
    if (!user) return
    let cancelled = false
    api.myLocale.get().then(({ locale }) => {
      if (cancelled) return
      if (locale === 'zh' || locale === 'en') setLocale(locale as Locale)
    }).catch(() => { /* keep client-side default */ })
    return () => { cancelled = true }
  }, [user])
}

// Imperative helper: also push the new locale to the server when logged in.
export async function persistLocale(next: Locale, isLoggedIn: boolean) {
  setLocale(next)
  if (isLoggedIn) {
    try { await api.myLocale.put(next) } catch { /* ignore — stays in localStorage */ }
  }
  return getLocale()
}

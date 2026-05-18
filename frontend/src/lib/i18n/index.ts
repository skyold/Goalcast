// Lightweight self-built i18n. Keeps bundle small (no react-i18next).
// Resolution order on first load: user prefs > localStorage > navigator.language > 'zh'.
// `t(key, vars?)` substitutes `{name}` placeholders in the matched message.

import { useSyncExternalStore } from 'react'
import zh from './messages.zh.json'
import en from './messages.en.json'

export type Locale = 'zh' | 'en'

const STORAGE_KEY = 'goalcast-locale'
const MESSAGES: Record<Locale, Record<string, string>> = { zh, en }

// External store (subscribe/snapshot) backing useLocale + useT.
const listeners = new Set<() => void>()
let _locale: Locale = detect()

function detect(): Locale {
  if (typeof window === 'undefined') return 'zh'
  const stored = window.localStorage.getItem(STORAGE_KEY)
  if (stored === 'zh' || stored === 'en') return stored
  const nav = window.navigator?.language?.toLowerCase() ?? ''
  if (nav.startsWith('en')) return 'en'
  return 'zh'
}

function emit() { listeners.forEach(l => l()) }

export function setLocale(next: Locale) {
  if (_locale === next) return
  _locale = next
  try { window.localStorage.setItem(STORAGE_KEY, next) } catch { /* private mode etc */ }
  emit()
}

export function getLocale(): Locale { return _locale }

function subscribe(cb: () => void) {
  listeners.add(cb)
  return () => listeners.delete(cb)
}
function snapshot() { return _locale }

export function useLocale(): Locale {
  return useSyncExternalStore(subscribe, snapshot, snapshot)
}

// Substitute `{key}` placeholders. Missing vars resolve to the literal `{key}` for visibility.
function format(template: string, vars?: Record<string, string | number>): string {
  if (!vars) return template
  return template.replace(/\{(\w+)\}/g, (_, k) =>
    Object.prototype.hasOwnProperty.call(vars, k) ? String(vars[k]) : `{${k}}`
  )
}

export function t(key: string, vars?: Record<string, string | number>, locale?: Locale): string {
  const loc = locale ?? _locale
  const msg = MESSAGES[loc][key] ?? MESSAGES.zh[key] ?? key
  return format(msg, vars)
}

export function useT() {
  const loc = useLocale()
  return (key: string, vars?: Record<string, string | number>) => t(key, vars, loc)
}

// Data layer: locale-aware name picker for team / competition names. Despite
// the historical name `pickZh`, this returns EN under en-locale and ZH under
// zh-locale, with cross-fallback when one side is missing. Components must
// be subscribed to locale via `useT()` / `useLocale()` for re-render on switch.
export function pickZh(zh: string | null | undefined, en: string | null | undefined): string {
  const z = zh && zh.trim() ? zh : null
  const e = en && en.trim() ? en : null
  if (_locale === 'en') return e ?? z ?? ''
  return z ?? e ?? ''
}

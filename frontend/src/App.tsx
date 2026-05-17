import React from 'react'
import { useStore } from './lib/store'
import AppRoutes from './routes'
import { useLocale } from './lib/i18n'

export default function App() {
  const { theme, density } = useStore()
  const locale = useLocale()
  React.useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    document.documentElement.setAttribute('data-density', density)
    document.documentElement.setAttribute('lang', locale === 'en' ? 'en' : 'zh-CN')
  }, [theme, density, locale])
  return <AppRoutes />
}

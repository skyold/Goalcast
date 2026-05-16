import React from 'react'
import { useStore } from './lib/store'
import AppRoutes from './routes'

export default function App() {
  const { theme, density } = useStore()
  React.useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    document.documentElement.setAttribute('data-density', density)
  }, [theme, density])
  return <AppRoutes />
}

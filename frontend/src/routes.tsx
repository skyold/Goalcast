// Optional: extract the route table so App.tsx stays small.
// If you prefer to keep your existing App.tsx routing, just merge the theme effect
// from App.tsx above into your current App.tsx and ignore this file.
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Layout from './components/layout/Layout'
import Dashboard from './pages/Dashboard'
import Matches from './pages/Matches'
import MatchDetail from './pages/MatchDetail'
import ValueBets from './pages/ValueBets'
import DroppingOdds from './pages/DroppingOdds'
import History from './pages/History'
import Login from './pages/Login'
import Signup from './pages/Signup'
import SettingsLeagues from './pages/SettingsLeagues'

const qc = new QueryClient({ defaultOptions: { queries: { staleTime: 30_000 } } })

export default function AppRoutes() {
  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="matches" element={<Matches />} />
            <Route path="matches/:id" element={<MatchDetail />} />
            <Route path="value-bets" element={<ValueBets />} />
            <Route path="dropping" element={<DroppingOdds />} />
            <Route path="history" element={<History />} />
            <Route path="login" element={<Login />} />
            <Route path="signup" element={<Signup />} />
            <Route path="settings/leagues" element={<SettingsLeagues />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

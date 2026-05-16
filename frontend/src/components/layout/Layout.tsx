import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import TweaksPanel from './TweaksPanel'

export default function Layout() {
  return (
    <>
      <div className="app">
        <Sidebar />
        <main className="main"><Outlet /></main>
      </div>
      <TweaksPanel />
    </>
  )
}

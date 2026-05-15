import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'

export default function Layout() {
  return (
    <div style={{ display:'flex', minHeight:'100vh', background:'#060d1a', color:'#e2e8f0', fontFamily:"-apple-system,'Inter',sans-serif" }}>
      <Sidebar />
      <main style={{ flex:1, overflow:'auto' }}><Outlet /></main>
    </div>
  )
}

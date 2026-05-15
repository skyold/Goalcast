import { NavLink } from 'react-router-dom'
import { useStore } from '../../lib/store'
import { useEffect, useState } from 'react'

const NAV = [
  { to: '/', label: 'Dashboard', icon: '⊞' },
  { to: '/matches', label: '比赛列表', icon: '📋' },
  { to: '/value-bets', label: 'Value Bets', icon: '💎' },
  { to: '/dropping', label: '跌水监控', icon: '📉' },
]
const NAV_DATA = [
  { to: '/history', label: '历史记录', icon: '🕒' },
]

function timeAgo(isoStr: string | null): string {
  if (!isoStr) return '从未同步'
  const diff = Math.floor((Date.now() - new Date(isoStr).getTime()) / 60000)
  if (diff < 1) return '刚刚'
  if (diff < 60) return `${diff} 分钟前`
  return `${Math.floor(diff / 60)} 小时前`
}

export default function Sidebar() {
  const { syncStatus } = useStore()
  const [, setTick] = useState(0)

  useEffect(() => {
    const t = setInterval(() => setTick(n => n + 1), 30_000)
    return () => clearInterval(t)
  }, [])

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="logo-icon">⚽</div>
        <div className="logo-text">Goalcast</div>
      </div>
      <nav>
        {NAV.map(({ to, label, icon }) => (
          <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}>
            <span>{icon}</span><span>{label}</span>
          </NavLink>
        ))}
        <div className="nav-section">数据</div>
        {NAV_DATA.map(({ to, label, icon }) => (
          <NavLink key={to} to={to} className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}>
            <span>{icon}</span><span>{label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="nav-spacer" />
      <div className="sync-status">
        <div className="sync-dot" />
        <span>同步于 {timeAgo(syncStatus.synced_at)}</span>
      </div>
    </aside>
  )
}

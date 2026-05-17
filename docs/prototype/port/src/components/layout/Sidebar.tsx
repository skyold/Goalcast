import { NavLink } from 'react-router-dom'
import { useStore } from '../../lib/store'
import { fmtTimeAgo } from '../../lib/format'

const NAV = [
  { to: '/',            label: '总览',     glyph: '◆', end: true },
  { to: '/matches',     label: '比赛列表', glyph: '▦' },
  { to: '/value-bets',  label: '价值投注', glyph: '◈' },
  { to: '/dropping',    label: '跌水赔率', glyph: '▼' },
  { to: '/history',     label: '历史回测', glyph: '⊟' },
]

export default function Sidebar() {
  const { syncStatus } = useStore()
  return (
    <aside className="sidebar">
      <div className="sb-logo">
        <div className="sb-mark">G</div>
        <div className="sb-name">goal<em>cast</em></div>
      </div>
      <div className="sb-section">分析</div>
      {NAV.map(({ to, label, glyph, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          className={({ isActive }) => `sb-item${isActive ? ' active' : ''}`}
        >
          <span className="sb-glyph">{glyph}</span>
          <span>{label}</span>
        </NavLink>
      ))}
      <div className="sb-spacer" />
      <div className="sb-foot">
        <div className="sb-foot-row"><span className="sb-dot" />数据同步 · 实时</div>
        <div className="sb-foot-row mono">{fmtTimeAgo(syncStatus.synced_at)}</div>
      </div>
    </aside>
  )
}

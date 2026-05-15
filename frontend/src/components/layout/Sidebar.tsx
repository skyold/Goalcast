import { NavLink } from 'react-router-dom'

const NAV = [
  { to: '/', label: 'Dashboard', icon: '⚡' },
  { to: '/matches', label: '比赛列表', icon: '⚽' },
  { to: '/value-bets', label: 'Value Bets', icon: '💎' },
  { to: '/dropping', label: '跌水监控', icon: '📉' },
  { to: '/history', label: '历史记录', icon: '📋' },
]

export default function Sidebar() {
  return (
    <aside style={{ width:200, minHeight:'100vh', background:'#070e1c', borderRight:'1px solid #1a2d47', flexShrink:0 }}>
      <div style={{ padding:'20px 16px', borderBottom:'1px solid #1a2d47' }}>
        <span style={{ color:'#22c55e', fontWeight:700, fontSize:18 }}>⚽ Goalcast</span>
      </div>
      <nav style={{ padding:'12px 0' }}>
        {NAV.map(({ to, label, icon }) => (
          <NavLink key={to} to={to} end={to === '/'} style={({ isActive }) => ({
            display:'flex', alignItems:'center', gap:10, padding:'10px 16px',
            textDecoration:'none', fontSize:14,
            color: isActive ? '#3b82f6' : '#94a3b8',
            background: isActive ? 'rgba(59,130,246,0.08)' : 'transparent',
            borderLeft: `3px solid ${isActive ? '#3b82f6' : 'transparent'}`,
            transition:'all 0.15s',
          })}>
            <span>{icon}</span><span>{label}</span>
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}

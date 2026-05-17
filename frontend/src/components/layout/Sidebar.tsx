import { NavLink } from 'react-router-dom'
import { useStore } from '../../lib/store'
import { fmtTimeAgo } from '../../lib/format'
import { useAuth } from '../../lib/auth'
import { useT } from '../../lib/i18n'

const NAV = [
  { to: '/',            key: 'nav.dashboard',  glyph: '◆', end: true },
  { to: '/matches',     key: 'nav.matches',    glyph: '▦' },
  { to: '/value-bets',  key: 'nav.value_bets', glyph: '◈' },
  { to: '/dropping',    key: 'nav.dropping',   glyph: '▼' },
  { to: '/history',     key: 'nav.history',    glyph: '⊟' },
]

const SETTINGS_NAV = [
  { to: '/settings/leagues', key: 'nav.my_leagues', glyph: '★' },
]

export default function Sidebar() {
  const { syncStatus, mobileDrawerOpen, setMobileDrawer } = useStore()
  const { user } = useAuth()
  const t = useT()
  return (
    <>
      {mobileDrawerOpen && <div className="sb-backdrop" onClick={() => setMobileDrawer(false)} />}
      <aside className={`sidebar${mobileDrawerOpen ? ' open' : ''}`}>
        <div className="sb-logo">
          <div className="sb-mark">G</div>
          <div className="sb-name">goal<em>cast</em></div>
        </div>
        <div className="sb-section">{t('nav.section.analytics')}</div>
        {NAV.map(({ to, key, glyph, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            onClick={() => setMobileDrawer(false)}
            className={({ isActive }) => `sb-item${isActive ? ' active' : ''}`}
          >
            <span className="sb-glyph">{glyph}</span>
            <span>{t(key)}</span>
          </NavLink>
        ))}
        {user && (
          <>
            <div className="sb-section">{t('nav.section.settings')}</div>
            {SETTINGS_NAV.map(({ to, key, glyph }) => (
              <NavLink
                key={to}
                to={to}
                onClick={() => setMobileDrawer(false)}
                className={({ isActive }) => `sb-item${isActive ? ' active' : ''}`}
              >
                <span className="sb-glyph">{glyph}</span>
                <span>{t(key)}</span>
              </NavLink>
            ))}
          </>
        )}
        <div className="sb-spacer" />
        <div className="sb-foot">
          <div className="sb-foot-row"><span className="sb-dot" />{t('sync.live')}</div>
          <div className="sb-foot-row mono">{fmtTimeAgo(syncStatus.synced_at)}</div>
        </div>
      </aside>
    </>
  )
}

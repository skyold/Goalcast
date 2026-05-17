import { Outlet, Link, useNavigate } from 'react-router-dom'
import Sidebar from './Sidebar'
import TweaksPanel from './TweaksPanel'
import { useStore } from '../../lib/store'
import { useAuth } from '../../lib/auth'
import { useT, useLocale } from '../../lib/i18n'
import { persistLocale, useLocaleSync } from '../../lib/i18n/useLocaleSync'

export default function Layout() {
  const { mobileDrawerOpen, setMobileDrawer } = useStore()
  const { user, logout } = useAuth()
  const t = useT()
  const locale = useLocale()
  const nav = useNavigate()
  // Inside QueryClientProvider — safe to use useAuth-backed sync here.
  useLocaleSync()

  const toggleLocale = () => persistLocale(locale === 'zh' ? 'en' : 'zh', !!user)

  return (
    <>
      <div className="app">
        <Sidebar />
        <main className="main">
          <header className="topbar">
            <button
              className="topbar-hamburger"
              aria-label={t('top.menu')}
              onClick={() => setMobileDrawer(!mobileDrawerOpen)}
            >
              <span /><span /><span />
            </button>
            <div className="topbar-brand">goal<em>cast</em></div>
            <div className="topbar-actions">
              <button
                className="btn locale-toggle"
                onClick={toggleLocale}
                title={locale === 'zh' ? 'Switch to English' : '切换到中文'}
              >
                {locale === 'zh' ? 'EN' : '中'}
              </button>
              {user ? (
                <>
                  <span className="topbar-email" title={user.email}>{user.email}</span>
                  <button className="btn" onClick={async () => { await logout.mutateAsync(); nav('/') }}>{t('auth.logout')}</button>
                </>
              ) : (
                <>
                  <Link to="/login" className="btn">{t('auth.login')}</Link>
                  <Link to="/signup" className="btn btn-primary">{t('auth.signup')}</Link>
                </>
              )}
            </div>
          </header>
          <Outlet />
        </main>
      </div>
      <TweaksPanel />
    </>
  )
}

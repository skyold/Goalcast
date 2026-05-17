// Topbar bell. Shows unread alert count; click toggles inbox dropdown.
// Refresh cadence and dismiss wiring live in lib/alerts.ts (`useAlerts`).
import { useState, useRef, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAlerts } from '../../lib/alerts'
import { pickZh, useT, useLocale } from '../../lib/i18n'

export function AlertsBell() {
  const t = useT()
  const locale = useLocale()
  const { items, count, dismiss } = useAlerts()
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement | null>(null)

  // Close when clicking outside.
  useEffect(() => {
    if (!open) return
    const handler = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  return (
    <div className="bell-wrap" ref={rootRef}>
      <button
        className="bell-btn"
        title={t('alerts.bell.title')}
        onClick={() => setOpen(o => !o)}
        aria-label={t('alerts.bell.title')}
      >
        <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">
          <path
            d="M8 1 A3 3 0 0 1 11 4 L11 7 C11 8.5 12 10 12 10 L4 10 C4 10 5 8.5 5 7 L5 4 A3 3 0 0 1 8 1 Z M7 12 L9 12 A1 1 0 0 1 8 13 A1 1 0 0 1 7 12 Z"
            fill="currentColor"
          />
        </svg>
        {count > 0 && <span className="bell-badge">{count}</span>}
      </button>
      {open && (
        <div className="bell-inbox" role="dialog">
          <div className="bell-inbox-hdr">
            <strong>{t('alerts.bell.title')}</strong>
            <Link to="/settings/alerts" onClick={() => setOpen(false)} className="card-sub">
              {t('nav.alerts_settings')} →
            </Link>
          </div>
          {items.length === 0 ? (
            <div className="empty" style={{ padding: 16 }}>{t('alerts.empty')}</div>
          ) : (
            items.map(a => {
              const homeName = pickZh(a.home_team_zh, a.home_team)
              const awayName = pickZh(a.away_team_zh, a.away_team)
              const compName = pickZh(a.competition_name_zh, a.competition_name)
              const ko = new Date(a.kickoff_utc)
              const kickoffStr = ko.toLocaleString(locale === 'en' ? 'en-US' : 'zh-CN', {
                month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
              })
              const sign = a.payload.max_delta_pct > 0 ? '+' : ''
              return (
                <div key={a.id} className="bell-row">
                  <div className="bell-row-mid">
                    <Link
                      to={`/matches/${a.fixture_id}`}
                      onClick={() => setOpen(false)}
                      className="bell-row-match"
                    >
                      {homeName} vs {awayName}
                    </Link>
                    <div className="bell-row-meta">{compName} · {kickoffStr}</div>
                    <div className="bell-row-delta">
                      {t('alerts.divergence.template', {
                        outcome: t(`alerts.outcome.${a.payload.max_outcome}`),
                        delta: `${sign}${a.payload.max_delta_pct.toFixed(1)}`,
                      })}
                    </div>
                  </div>
                  <button
                    className="btn bell-row-dismiss"
                    onClick={() => dismiss.mutate(a.id)}
                    disabled={dismiss.isPending}
                    aria-label={t('alerts.dismiss')}
                  >×</button>
                </div>
              )
            })
          )}
        </div>
      )}
    </div>
  )
}

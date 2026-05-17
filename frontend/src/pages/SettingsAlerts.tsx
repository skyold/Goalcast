import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../lib/auth'
import { useAlertSettings, useAlerts } from '../lib/alerts'
import { useT } from '../lib/i18n'

export default function SettingsAlerts() {
  const nav = useNavigate()
  const t = useT()
  const { user, isLoading: authLoading } = useAuth()
  const { settings, save } = useAlertSettings()
  const { scan } = useAlerts()
  const [threshold, setThreshold] = useState(5)
  const [enabled, setEnabled] = useState(true)
  const [savedFlag, setSavedFlag] = useState(false)

  useEffect(() => {
    if (settings) {
      setThreshold(settings.divergence_threshold)
      setEnabled(settings.enabled)
    }
  }, [settings])

  if (!authLoading && !user) {
    return (
      <div className="page">
        <div className="empty">
          {t('settings.leagues.must_login_pre')}
          <Link to="/login">{t('auth.login')}</Link>
          {t('settings.leagues.must_login_post')}
        </div>
      </div>
    )
  }

  async function handleSave() {
    await save.mutateAsync({ divergence_threshold: threshold, enabled })
    setSavedFlag(true)
    setTimeout(() => setSavedFlag(false), 1500)
  }

  return (
    <>
      <div className="ph">
        <div>
          <div className="ph-title">{t('alerts.settings.title')}</div>
          <div className="ph-sub">{t('alerts.settings.subtitle')}</div>
        </div>
        <div className="ph-actions">
          <button className="btn" onClick={() => nav(-1)}>{t('common.cancel')}</button>
          <button
            className="btn btn-primary"
            onClick={handleSave}
            disabled={save.isPending}
          >
            {save.isPending ? t('common.saving') : (savedFlag ? t('alerts.settings.save_ok') : t('common.save'))}
          </button>
        </div>
      </div>

      <div className="page">
        <div className="card">
          <div className="card-hdr">
            <div className="card-title">{t('alerts.settings.enabled')}</div>
            <label className="switch">
              <input type="checkbox" checked={enabled} onChange={e => setEnabled(e.target.checked)} />
              <span className="switch-slider" />
            </label>
          </div>
        </div>

        <div className="card">
          <div className="card-hdr">
            <div className="card-title">{t('alerts.settings.threshold')}</div>
            <span className="card-sub">{threshold.toFixed(1)}%</span>
          </div>
          <input
            type="range"
            min={1} max={20} step={0.5}
            value={threshold}
            onChange={e => setThreshold(parseFloat(e.target.value))}
            disabled={!enabled}
            style={{ width: '100%', margin: '12px 0' }}
          />
          <div style={{ fontSize: 'var(--fs-sm)', color: 'var(--text-mute)' }}>
            {t('alerts.settings.threshold_hint', { n: threshold.toFixed(1) })}
          </div>
        </div>

        <button
          className="btn"
          onClick={() => scan.mutate()}
          disabled={scan.isPending || !enabled}
          style={{ display: 'block', margin: '20px auto' }}
        >
          {scan.isPending ? t('matches.empty.loading') : t('alerts.scan_now')}
          {scan.data && ` · +${scan.data.inserted}`}
        </button>
      </div>
    </>
  )
}

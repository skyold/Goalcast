import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { useAuth } from '../lib/auth'
import { useMyLeagues } from '../lib/myLeagues'
import { POPULAR_LEAGUE_IDS } from '../lib/popularLeagues'
import { pickZh, useT } from '../lib/i18n'

export default function SettingsLeagues() {
  const nav = useNavigate()
  const t = useT()
  const { user, isLoading: authLoading } = useAuth()
  const { ids: savedIds, save } = useMyLeagues()
  const compsQ = useQuery({ queryKey: ['competitions'], queryFn: api.competitions })

  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [showAll, setShowAll] = useState(false)
  const [filter, setFilter] = useState('')

  // Seed local state from server once.
  useEffect(() => {
    if (savedIds) setSelected(new Set(savedIds))
  }, [savedIds])

  const comps = compsQ.data?.competitions ?? []
  const popular = useMemo(() => comps.filter(c => POPULAR_LEAGUE_IDS.has(c.id)), [comps])
  const others = useMemo(() => comps.filter(c => !POPULAR_LEAGUE_IDS.has(c.id)), [comps])
  const filtered = useMemo(() => {
    if (!filter) return others
    const f = filter.toLowerCase()
    return others.filter(c => c.name.toLowerCase().includes(f) || (c.name_zh && c.name_zh.includes(filter)))
  }, [others, filter])

  // Auth gate (after hooks per React rules)
  if (!authLoading && !user) {
    return (
      <div className="page">
        <div className="empty">{t('settings.leagues.must_login_pre')}<Link to="/login">{t('auth.login')}</Link>{t('settings.leagues.must_login_post')}</div>
      </div>
    )
  }

  function toggle(id: number) {
    setSelected(s => {
      const next = new Set(s)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  async function handleSave() {
    await save.mutateAsync([...selected])
    nav('/matches')
  }

  const dirty = savedIds == null
    ? selected.size > 0
    : selected.size !== savedIds.length || [...selected].some(id => !savedIds.includes(id))

  return (
    <>
      <div className="ph">
        <div>
          <div className="ph-title">{t('settings.leagues.title')}</div>
          <div className="ph-sub">{t('settings.leagues.subtitle')}</div>
        </div>
        <div className="ph-actions">
          <button className="btn" onClick={() => nav(-1)}>{t('common.cancel')}</button>
          <button className="btn btn-primary" onClick={handleSave} disabled={!dirty || save.isPending}>
            {save.isPending ? t('common.saving') : t('settings.leagues.save_n', { n: selected.size })}
          </button>
        </div>
      </div>

      <div className="page">
        <div className="card">
          <div className="card-hdr">
            <div className="card-title">{t('settings.leagues.popular')}</div>
            <span className="card-sub">{t('settings.leagues.count', { n: popular.length })}</span>
          </div>
          <div className="league-grid">
            {popular.map(c => (
              <label key={c.id} className={`league-chk${selected.has(c.id) ? ' active' : ''}`}>
                <input
                  type="checkbox"
                  checked={selected.has(c.id)}
                  onChange={() => toggle(c.id)}
                />
                <span>{pickZh(c.name_zh, c.name)}</span>
              </label>
            ))}
          </div>
        </div>

        <div className="card">
          <div className="card-hdr">
            <div className="card-title">{t('settings.leagues.others')}</div>
            <span className="card-sub">{t('settings.leagues.count', { n: others.length })}</span>
          </div>
          <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
            <input
              type="text"
              className="date-pick"
              placeholder={t('settings.leagues.search_placeholder')}
              value={filter}
              onChange={e => setFilter(e.target.value)}
              style={{ flex: 1 }}
            />
            <button className="btn" onClick={() => setShowAll(v => !v)}>
              {showAll ? t('common.collapse') : t('settings.leagues.expand_n', { n: filtered.length })}
            </button>
          </div>
          {showAll && (
            <div className="league-grid">
              {filtered.map(c => (
                <label key={c.id} className={`league-chk${selected.has(c.id) ? ' active' : ''}`}>
                  <input
                    type="checkbox"
                    checked={selected.has(c.id)}
                    onChange={() => toggle(c.id)}
                  />
                  <span>{pickZh(c.name_zh, c.name)}</span>
                </label>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  )
}

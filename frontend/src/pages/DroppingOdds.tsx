import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { fmtKickoff } from '../lib/format'
import { pickZh, useT, useLocale } from '../lib/i18n'
import { Tooltip } from '../components/shared/Tooltip'
import { gloss } from '../lib/glossary'

export default function DroppingOdds() {
  const nav = useNavigate()
  const tt = useT()
  const locale = useLocale()
  const [minDrop, setMinDrop] = useState(20)
  const { data, isLoading } = useQuery({
    queryKey: ['dropping-odds', minDrop],
    queryFn: () => api.droppingOdds({ min_drop: minDrop }),
  })
  const items = data?.items ?? []

  return (
    <>
      <div className="ph">
        <div>
          <div className="ph-title">{tt('drop.title')}</div>
          <div className="ph-sub">{tt('drop.subtitle')} · {items.length}</div>
        </div>
      </div>

      <div className="filters">
        <div className="filter-grp">
          {[20, 40, 50, 60].map(th => (
            <button key={th} className={`chip${minDrop === th ? ' active' : ''}`} onClick={() => setMinDrop(th)}>≥ {th}%</button>
          ))}
        </div>
      </div>

      <div className="page">
        {isLoading && <div className="empty">{tt('matches.empty.loading')}</div>}
        {!isLoading && items.length === 0 && <div className="empty">{tt('dash.empty.drops')}</div>}
        {items.map((d, i) => {
          const ko = fmtKickoff(d.kickoff_utc)
          const open = (d as any).opening as number | undefined
          const close = (d as any).closing as number | undefined ?? d.odds_home ?? undefined
          return (
            <div key={i} className="do-card" onClick={() => nav(`/matches/${d.fixture_id}`)}>
              <div>
                <div className="do-info-title">{pickZh(d.home_team_zh, d.home_team)} vs {pickZh(d.away_team_zh, d.away_team)}</div>
                <div className="do-info-meta">
                  {pickZh(d.competition_name_zh, d.competition_name)} · {ko.day} {ko.time}
                  {' · '}
                  <Tooltip content={gloss('drop.market_tag')}>
                    <span className="tag-mkt" tabIndex={0}>{d.market}</span>
                  </Tooltip>
                  {' · '}
                  {new Date(d.recorded_at).toLocaleTimeString(locale === 'en' ? 'en-US' : 'zh-CN', { hour: '2-digit', minute: '2-digit' })}
                </div>
              </div>
              {open != null && close != null && (
                <div className="do-track">
                  <span className="old">{open.toFixed(2)}</span>
                  <span className="arrow">→</span>
                  <span className="new">{close.toFixed(2)}</span>
                </div>
              )}
              <Tooltip content={gloss('drop.drop_pct')}>
                <div className="do-pct" tabIndex={0}>
                  <div className="do-pct-val">{Math.round(d.drop_pct ?? 0)}%</div>
                  <div className="do-pct-lbl">↓ DROP</div>
                </div>
              </Tooltip>
            </div>
          )
        })}
      </div>
    </>
  )
}

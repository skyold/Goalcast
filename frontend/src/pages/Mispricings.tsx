// Top mispricings page. Surfaces both positive (model > market) and negative
// (model < market) deltas — unlike /value-bets which only shows positive edge.
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api, type MispricingItem } from '../lib/api'
import { fmtKickoff } from '../lib/format'
import { pickZh, useT } from '../lib/i18n'
import { PredictabilityBadge } from '../components/shared/PredictabilityBadge'

export default function Mispricings() {
  const nav = useNavigate()
  const t = useT()
  const [minEdge, setMinEdge] = useState(3)
  const today = new Date().toISOString().slice(0, 10)

  const { data, isLoading } = useQuery({
    queryKey: ['mispricings', today, minEdge],
    queryFn: () => api.mispricings({ date: today, min_abs_edge: minEdge, limit: 100 }),
    staleTime: 60_000,
  })
  const items = data?.items ?? []

  return (
    <>
      <div className="ph">
        <div>
          <div className="ph-title">{t('insights.mispricing.title')}</div>
          <div className="ph-sub">{t('insights.mispricing.subtitle')} · {items.length}</div>
        </div>
      </div>

      <div className="filters">
        <div className="filter-grp">
          <span className="filter-lbl">{t('insights.mispricing.min_edge_label')}</span>
          {[3, 5, 7, 10].map(v => (
            <button key={v}
              className={`chip${minEdge === v ? ' active' : ''}`}
              onClick={() => setMinEdge(v)}
            >≥ {v}%</button>
          ))}
        </div>
      </div>

      <div className="page">
        {isLoading && <div className="empty">{t('insights.mispricing.loading')}</div>}
        {!isLoading && items.length === 0 && <div className="empty">{t('insights.mispricing.empty')}</div>}
        {items.length > 0 && (
          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            <table className="ht">
              <thead>
                <tr>
                  <th>{t('insights.mispricing.col.match')}</th>
                  <th style={{ textAlign: 'center' }}>{t('insights.mispricing.col.selection')}</th>
                  <th style={{ textAlign: 'right' }}>{t('insights.mispricing.col.model')}</th>
                  <th style={{ textAlign: 'right' }}>{t('insights.mispricing.col.market')}</th>
                  <th style={{ textAlign: 'right' }}>{t('insights.mispricing.col.delta')}</th>
                  <th style={{ textAlign: 'right' }}>{t('insights.mispricing.col.odds')}</th>
                </tr>
              </thead>
              <tbody>
                {items.map((m, i) => <Row key={`${m.fixture_id}-${m.selection}-${i}`} m={m} nav={nav} t={t} />)}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  )
}

function Row({ m, nav, t }: { m: MispricingItem; nav: ReturnType<typeof useNavigate>; t: (k: string, v?: any) => string }) {
  const ko = fmtKickoff(m.kickoff_utc)
  const delta = m.delta_pct
  const positive = delta > 0
  return (
    <tr onClick={() => nav(`/matches/${m.fixture_id}`)} style={{ cursor: 'pointer' }}>
      <td className="match">
        <div>{pickZh(m.home_team_zh, m.home_team)} vs {pickZh(m.away_team_zh, m.away_team)}</div>
        <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-mute)' }}>
          {pickZh(m.competition_name_zh, m.competition_name)} · {ko.day} {ko.time}
          {m.predictability && <> · <PredictabilityBadge level={m.predictability} /></>}
        </div>
      </td>
      <td style={{ textAlign: 'center' }}>{t(`insights.mispricing.selection.${m.selection}`)}</td>
      <td className="num" style={{ textAlign: 'right' }}>{m.model_prob_pct.toFixed(1)}%</td>
      <td className="num" style={{ textAlign: 'right' }}>{m.market_prob_pct.toFixed(1)}%</td>
      <td className="num" style={{ textAlign: 'right', color: positive ? 'var(--acc)' : 'var(--neg)', fontWeight: 700 }}>
        {positive ? '+' : ''}{delta.toFixed(1)}%
      </td>
      <td className="num" style={{ textAlign: 'right' }}>{m.odds.toFixed(2)}</td>
    </tr>
  )
}

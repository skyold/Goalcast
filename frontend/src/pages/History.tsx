// History page. OddAlerts doesn't expose ROI / per-bet outcome directly — backend needs
// a bet_outcomes table (see docs/frontend-data-gaps.md #9). This component is wired to
// api.history() returning legacy fields; if your backend evolves, update the column reads.
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { useT } from '../lib/i18n'
import { PredictabilityBadge } from '../components/shared/PredictabilityBadge'
import { InfoIcon } from '../components/shared/InfoIcon'
import { Tooltip } from '../components/shared/Tooltip'
import { gloss, type GlossaryKey } from '../lib/glossary'

export default function History() {
  const nav = useNavigate()
  const t = useT()
  const [strategy, setStrategy] = useState('all')

  const { data, isLoading } = useQuery({
    queryKey: ['history'],
    queryFn: () => api.history({ limit: 200 }),
  })
  const items = data?.items ?? []

  const wins = items.filter((h: any) => h.result === 'W').length
  const draws = items.filter((h: any) => h.result === 'D').length
  const losses = items.filter((h: any) => h.result === 'L').length
  const winRate = items.length ? wins / items.length * 100 : 0

  return (
    <>
      <div className="ph">
        <div>
          <div className="ph-title">{t('history.title')}</div>
          <div className="ph-sub">· {items.length}</div>
        </div>
        <div className="ph-actions">
          <button className="btn">{t('common.export_csv')}</button>
        </div>
      </div>

      <div className="page">
        <div className="kpi-grid">
          <Kpi label={t('history.samples')}    value={items.length}             sub={t('history.samples_breakdown', { w: wins, d: draws, l: losses })} infoKey="hist.samples" />
          <Kpi label={t('history.winrate')}    value={`${winRate.toFixed(0)}%`} sub={t('history.vs_prev')}    infoKey="hist.winrate" />
          <Kpi label={t('history.roi')}        value="—"                        sub={t('history.roi_todo')}   infoKey="hist.roi" />
          <Kpi label={t('history.avg_edge')}   value="—"                        sub={t('history.agg_todo')}   infoKey="hist.avg_edge" />
        </div>

        <div className="filters" style={{ borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', marginBottom: 'var(--gap-grid)' }}>
          <div className="filter-grp">
            <span className="filter-lbl">{t('history.strategy')}</span>
            {[['all','history.strategy.all'], ['drop','history.strategy.drop'], ['value','history.strategy.value'], ['high','history.strategy.high']].map(([k, lk]) => (
              <button key={k} className={`chip${strategy === k ? ' active' : ''}`} onClick={() => setStrategy(k)}>{t(lk)}</button>
            ))}
          </div>
        </div>

        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          {isLoading && <div className="empty">{t('matches.empty.loading')}</div>}
          {!isLoading && items.length === 0 && <div className="empty">—</div>}
          {items.length > 0 && (
            <table className="ht">
              <thead>
                <tr>
                  <th>{t('history.col.date')}</th>
                  <th>{t('history.col.league')}</th>
                  <th>{t('history.col.match')}</th>
                  <th style={{ textAlign: 'center' }}>{t('history.col.score')}</th>
                  <th style={{ textAlign: 'center' }}>
                    <Tooltip content={gloss('hist.col.drop')}>
                      <span tabIndex={0} style={{ cursor: 'help' }}>{t('history.col.drop')}</span>
                    </Tooltip>
                  </th>
                  <th style={{ textAlign: 'center' }}>
                    <Tooltip content={gloss('hist.col.predictability')}>
                      <span tabIndex={0} style={{ cursor: 'help' }}>{t('history.col.predictability')}</span>
                    </Tooltip>
                  </th>
                  <th style={{ textAlign: 'center' }}>
                    <Tooltip content={gloss('hist.col.result')}>
                      <span tabIndex={0} style={{ cursor: 'help' }}>{t('history.col.result')}</span>
                    </Tooltip>
                  </th>
                </tr>
              </thead>
              <tbody>
                {items.map((h: any) => (
                  <tr key={h.id} onClick={() => nav(`/matches/${h.id}`)}>
                    <td className="num">{h.kickoff_utc?.slice(5, 10) ?? ''}</td>
                    <td>{h.competition_name}</td>
                    <td className="match">{h.home_team} vs {h.away_team}</td>
                    <td className="score" style={{ textAlign: 'center' }}>
                      {h.score_home ?? '-'}-{h.score_away ?? '-'}
                    </td>
                    <td className="num" style={{ textAlign: 'center', color: 'var(--acc)', fontWeight: 700 }}>
                      {h.drop_pct != null ? `${Math.round(h.drop_pct)}%` : '—'}
                    </td>
                    <td style={{ textAlign: 'center' }}><PredictabilityBadge level={h.predictability} /></td>
                    <td className={`r${h.result ?? ''}`} style={{ textAlign: 'center' }}>
                      {h.result === 'W' ? t('history.result.win') : h.result === 'L' ? t('history.result.lose') : h.result === 'D' ? t('history.result.draw') : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </>
  )
}

function Kpi({ label, value, sub, infoKey }: { label: string; value: string | number; sub: string; infoKey?: GlossaryKey }) {
  return (
    <div className="kpi">
      <span className="kpi-lbl">
        {label}
        {infoKey && <InfoIcon k={infoKey} />}
      </span>
      <span className="kpi-val">{value}</span>
      <span className="kpi-delta">{sub}</span>
    </div>
  )
}

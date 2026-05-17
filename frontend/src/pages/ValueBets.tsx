import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { fmtKickoff } from '../lib/format'
import { pickZh, useT } from '../lib/i18n'
import { Tooltip } from '../components/shared/Tooltip'
import { gloss } from '../lib/glossary'

export default function ValueBets() {
  const nav = useNavigate()
  const tt = useT()
  const [minEdge, setMinEdge] = useState(0)
  const { data, isLoading } = useQuery({
    queryKey: ['value-bets', minEdge],
    queryFn: () => api.valueBets({ min_edge: minEdge }),
  })
  const bets = data?.items ?? []

  return (
    <>
      <div className="ph">
        <div>
          <div className="ph-title">{tt('value.title')}</div>
          <div className="ph-sub">{tt('value.subtitle')} · {bets.length}</div>
        </div>
        <div className="ph-actions"><button className="btn">{tt('common.export')}</button></div>
      </div>

      <div className="filters">
        <div className="filter-grp">
          <span className="filter-lbl">{tt('value.min_edge')}</span>
          {[0, 5, 10, 15].map(e => (
            <button key={e} className={`chip${minEdge === e ? ' active' : ''}`} onClick={() => setMinEdge(e)}>≥ {e}%</button>
          ))}
        </div>
      </div>

      <div className="page">
        {isLoading && <div className="empty">{tt('matches.empty.loading')}</div>}
        {!isLoading && bets.length === 0 && <div className="empty">{tt('dash.empty.values')}</div>}
        {bets.map((v, i) => {
          const ko = fmtKickoff(v.kickoff_utc)
          return (
            <div key={i} className="vb-row" onClick={() => nav(`/matches/${v.fixture_id}`)}>
              <div className="vb-rank">{i + 1}</div>
              <div>
                <div className="vb-match-title">{pickZh(v.home_team_zh, v.home_team)} vs {pickZh(v.away_team_zh, v.away_team)}</div>
                <div className="vb-match-meta">{pickZh(v.competition_name_zh, v.competition_name)} · {ko.day} {ko.time}</div>
              </div>
              <Tooltip content={gloss('vb.selection')}>
                <div className="vb-cell" tabIndex={0}><span className="vb-sel">{v.selection}</span></div>
              </Tooltip>
              <Tooltip content={gloss('vb.odds')}>
                <div className="vb-cell" tabIndex={0}>
                  <div className="vb-cell-val">{v.odds.toFixed(2)}</div>
                  <div className="vb-cell-lbl">{tt('value.col.odds')}</div>
                </div>
              </Tooltip>
              <Tooltip content={gloss('vb.prob')}>
                <div className="vb-cell" tabIndex={0}>
                  <div className="vb-cell-val">{v.prob.toFixed(1)}%</div>
                  <div className="vb-cell-lbl">{tt('value.col.prob')}</div>
                </div>
              </Tooltip>
              <Tooltip content={gloss('vb.edge')}>
                <div className="vb-cell" tabIndex={0}>
                  <div className="vb-cell-val acc">+{v.edge_pct.toFixed(1)}%</div>
                  <div className="vb-cell-lbl">Edge</div>
                </div>
              </Tooltip>
            </div>
          )
        })}
      </div>
    </>
  )
}

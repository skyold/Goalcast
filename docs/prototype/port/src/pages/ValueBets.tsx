import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { fmtKickoff } from '../lib/format'

export default function ValueBets() {
  const nav = useNavigate()
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
          <div className="ph-title">价值投注</div>
          <div className="ph-sub">基于模型概率 vs 市场赔率 · {bets.length} 个机会</div>
        </div>
        <div className="ph-actions"><button className="btn">导出</button></div>
      </div>

      <div className="filters">
        <div className="filter-grp">
          <span className="filter-lbl">最小 Edge</span>
          {[0, 5, 10, 15].map(e => (
            <button key={e} className={`chip${minEdge === e ? ' active' : ''}`} onClick={() => setMinEdge(e)}>≥ {e}%</button>
          ))}
        </div>
      </div>

      <div className="page">
        {isLoading && <div className="empty">加载中…</div>}
        {!isLoading && bets.length === 0 && <div className="empty">当前阈值下无 value bet</div>}
        {bets.map((v, i) => {
          const ko = fmtKickoff(v.kickoff_utc)
          return (
            <div key={i} className="vb-row" onClick={() => nav(`/matches/${v.fixture_id}`)}>
              <div className="vb-rank">{i + 1}</div>
              <div>
                <div className="vb-match-title">{v.home_team} vs {v.away_team}</div>
                <div className="vb-match-meta">{v.competition_name} · {ko.day} {ko.time}</div>
              </div>
              <div className="vb-cell"><span className="vb-sel">{v.selection}</span></div>
              <div className="vb-cell">
                <div className="vb-cell-val">{v.odds.toFixed(2)}</div>
                <div className="vb-cell-lbl">赔率</div>
              </div>
              <div className="vb-cell">
                <div className="vb-cell-val">{v.prob.toFixed(1)}%</div>
                <div className="vb-cell-lbl">概率</div>
              </div>
              <div className="vb-cell">
                <div className="vb-cell-val acc">+{v.edge_pct.toFixed(1)}%</div>
                <div className="vb-cell-lbl">Edge</div>
              </div>
            </div>
          )
        })}
      </div>
    </>
  )
}

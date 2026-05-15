import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'

type Dir = 'all' | 'home' | 'draw' | 'away'
const DIR_LABELS: Record<Dir, string> = { all: '全部', home: '主胜', draw: '平局', away: '客胜' }

export default function ValueBets() {
  const navigate = useNavigate()
  const [minEdge, setMinEdge] = useState(5)
  const [dir, setDir] = useState<Dir>('all')

  const { data, isLoading } = useQuery({
    queryKey: ['value-bets', minEdge],
    queryFn: () => api.valueBets({ min_edge: minEdge }),
  })

  const items = (data?.items ?? [])
    .filter(item => dir === 'all' || item.selection === dir)
    .sort((a, b) => b.edge_pct - a.edge_pct)

  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-title">Value Bets</div>
          <div className="page-subtitle">边际优势 ≥ {minEdge}% 的投注机会 · 今日 {data?.items.length ?? '—'} 个</div>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          {(['all', 'home', 'draw', 'away'] as Dir[]).map(d => (
            <button key={d} className={`chip${dir === d ? ' active' : ''}`} onClick={() => setDir(d)}>{DIR_LABELS[d]}</button>
          ))}
        </div>
      </div>

      <div style={{ padding: '10px 28px', display: 'flex', alignItems: 'center', gap: 8, borderBottom: '1px solid #1e293b' }}>
        <span style={{ fontSize: 11, color: '#475569' }}>最小优势</span>
        <select className="sort-select" value={minEdge} onChange={e => setMinEdge(Number(e.target.value))}>
          {[3, 5, 8, 10, 15].map(v => <option key={v} value={v}>{v}%</option>)}
        </select>
      </div>

      {isLoading
        ? <div style={{ padding: 24, color: '#64748b' }}>加载中...</div>
        : items.length === 0
        ? <div style={{ textAlign: 'center', color: '#475569', padding: 60 }}>当前无符合条件的 Value Bets</div>
        : (
          <div className="vb-list">
            {items.map((item, i) => {
              const dirLabel = item.selection === 'home' ? '主胜' : item.selection === 'away' ? '客胜' : '平局'
              const time = new Date(item.kickoff_utc).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
              return (
                <div key={i} className="vb-card" onClick={() => navigate(`/matches/${item.fixture_id}`)}>
                  <div className="vb-rank">{i + 1}</div>
                  <div className="vb-match">
                    <div className="vb-teams">{item.home_team} vs {item.away_team}</div>
                    <div className="vb-meta">{item.competition_name} · {time}</div>
                  </div>
                  <div className="vb-stat">
                    <div className="vb-stat-val" style={{ color: '#f1f5f9' }}>{dirLabel}</div>
                    <div className="vb-stat-lbl">投注方向</div>
                  </div>
                  <div className="ob hot" style={{ minWidth: 54 }}>
                    <div className="ol">赔率</div>
                    <div className="ov">{item.odds.toFixed(2)}</div>
                  </div>
                  <div className="vb-stat">
                    <div className="vb-stat-val" style={{ color: '#a855f7' }}>{Math.round(item.prob * 100)}%</div>
                    <div className="vb-stat-lbl">模型概率</div>
                  </div>
                  <div className="vb-stat">
                    <div className="vb-stat-val" style={{ color: '#22c55e' }}>+{item.edge_pct.toFixed(1)}%</div>
                    <div className="vb-stat-lbl">边际优势</div>
                  </div>
                </div>
              )
            })}
          </div>
        )
      }
    </>
  )
}

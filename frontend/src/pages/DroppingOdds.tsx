import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { fmtKickoff } from '../lib/format'

export default function DroppingOdds() {
  const nav = useNavigate()
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
          <div className="ph-title">跌水赔率</div>
          <div className="ph-sub">市场对哪边的信心在快速增强 · {items.length} 个事件</div>
        </div>
        <div className="ph-actions"><button className="btn">订阅推送</button></div>
      </div>

      <div className="filters">
        <div className="filter-grp">
          <span className="filter-lbl">阈值</span>
          {[20, 40, 50, 60].map(t => (
            <button key={t} className={`chip${minDrop === t ? ' active' : ''}`} onClick={() => setMinDrop(t)}>≥ {t}%</button>
          ))}
        </div>
      </div>

      <div className="page">
        {isLoading && <div className="empty">加载中…</div>}
        {!isLoading && items.length === 0 && <div className="empty">当前阈值下无跌赔事件</div>}
        {items.map((d, i) => {
          const ko = fmtKickoff(d.kickoff_utc)
          // /odds/dropping returns opening/closing; the original API type doesn't expose them,
          // but the raw response includes `opening` + `closing`. Cast to any if your TS API
          // type doesn't include them yet, or extend DroppingOddsItem.
          const open = (d as any).opening as number | undefined
          const close = (d as any).closing as number | undefined ?? d.odds_home ?? undefined
          return (
            <div key={i} className="do-card" onClick={() => nav(`/matches/${d.fixture_id}`)}>
              <div>
                <div className="do-info-title">{d.home_team} vs {d.away_team}</div>
                <div className="do-info-meta">
                  {d.competition_name} · {ko.day} {ko.time} · 市场 <span className="tag-mkt">{d.market}</span> ·{' '}
                  {new Date(d.recorded_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
                </div>
              </div>
              {open != null && close != null && (
                <div className="do-track">
                  <span className="old">{open.toFixed(2)}</span>
                  <span className="arrow">→</span>
                  <span className="new">{close.toFixed(2)}</span>
                </div>
              )}
              <div className="do-pct">
                <div className="do-pct-val">{Math.round(d.drop_pct ?? 0)}%</div>
                <div className="do-pct-lbl">↓ DROP</div>
              </div>
            </div>
          )
        })}
      </div>
    </>
  )
}

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'

type MktFilter = 'all' | 'home' | 'over' | 'away'
const MKT_LABELS: Record<MktFilter, string> = { all: '所有市场', home: '主胜', over: '大球', away: '客胜' }

function timeAgoShort(isoStr: string): string {
  const diff = Math.floor((Date.now() - new Date(isoStr).getTime()) / 60000)
  if (diff < 1) return '刚刚'
  if (diff < 60) return `${diff}分钟前`
  return new Date(isoStr).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

export default function DroppingOdds() {
  const navigate = useNavigate()
  const [minDrop, setMinDrop] = useState(10)
  const [mkt, setMkt] = useState<MktFilter>('all')

  const { data, isLoading } = useQuery({
    queryKey: ['dropping-odds', minDrop],
    queryFn: () => api.droppingOdds({ min_drop: minDrop }),
    refetchInterval: 30_000,
  })

  const items = (data?.items ?? [])
    .filter(item => {
      if (mkt === 'all') return true
      const m = (item.drop_market ?? item.market ?? '').toLowerCase()
      if (mkt === 'home') return m.includes('主') || m.includes('home')
      if (mkt === 'away') return m.includes('客') || m.includes('away')
      if (mkt === 'over') return m.includes('大') || m.includes('over')
      return true
    })
    .sort((a, b) => (a.drop_pct ?? 0) - (b.drop_pct ?? 0))

  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-title">跌水监控</div>
          <div className="page-subtitle">赔率显著下跌的比赛</div>
        </div>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          {(['all', 'home', 'over', 'away'] as MktFilter[]).map(m => (
            <button key={m} className={`chip${mkt === m ? ' active' : ''}`} onClick={() => setMkt(m)}>{MKT_LABELS[m]}</button>
          ))}
          <select className="sort-select" value={minDrop} onChange={e => setMinDrop(Number(e.target.value))}>
            {[5, 10, 15, 20].map(v => <option key={v} value={v}>≥{v}%</option>)}
          </select>
        </div>
      </div>

      {isLoading
        ? <div style={{ padding: 24, color: '#64748b' }}>加载中...</div>
        : items.length === 0
        ? <div style={{ textAlign: 'center', color: '#475569', padding: 60 }}>暂无跌水数据</div>
        : (
          <div className="do-list">
            {items.map(item => {
              const mktKey = (item.drop_market ?? item.market ?? '').toLowerCase()
              const currentOdds = mktKey.includes('away') || mktKey.includes('客') ? item.odds_away
                : mktKey.includes('draw') || mktKey.includes('平') ? item.odds_draw
                : item.odds_home ?? item.odds_away ?? item.odds_draw
              const mktLabel = item.drop_market ?? item.market ?? '赔率'
              return (
                <div key={`${item.fixture_id}-${item.market}`} className="do-card" onClick={() => navigate(`/matches/${item.fixture_id}`)}>
                  <div className="do-hdr">
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ fontSize: 11, color: '#64748b' }}>{item.competition_name}</span>
                    </div>
                    <span style={{ fontSize: 11, color: '#334155' }}>{timeAgoShort(item.recorded_at)}</span>
                  </div>
                  <div className="do-body">
                    <div className="do-teams">
                      <div className="do-matchname">{item.home_team} vs {item.away_team}</div>
                      <div className="do-league">{item.competition_name}</div>
                    </div>
                    <div className="do-track">
                      <div className="do-track-lbl">{mktLabel}赔率变动</div>
                      <div className="do-track-row">
                        <div className="do-new">{currentOdds?.toFixed(2) ?? '—'}</div>
                        <span style={{ fontSize: 10, color: '#334155' }}>当前</span>
                      </div>
                    </div>
                    <div className="do-pct">
                      <div className="do-pct-val">↓{Math.abs(item.drop_pct ?? 0).toFixed(0)}%</div>
                      <div className="do-pct-mkt">{mktLabel}</div>
                    </div>
                    <div className="badges" style={{ flexDirection: 'column' }}>
                      {(item.drop_pct ?? 0) <= -20 && <span className="badge br">大幅跌水</span>}
                      <span className="badge bg">↓{Math.abs(item.drop_pct ?? 0).toFixed(1)}%</span>
                    </div>
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

import { useQuery } from '@tanstack/react-query'
import { useStore } from '../lib/store'
import { api } from '../lib/api'
import MatchCard from '../components/match/MatchCard'

export default function Dashboard() {
  const { selectedLeagues, selectedDate } = useStore()
  const today = new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' })

  const { data: fixturesData } = useQuery({
    queryKey: ['fixtures', selectedDate, selectedLeagues.join(','), 4],
    queryFn: () => api.fixtures({ date: selectedDate, leagues: selectedLeagues.join(','), limit: 4 }),
    enabled: selectedLeagues.length > 0,
  })
  const { data: vbData } = useQuery({ queryKey: ['value-bets', 5], queryFn: () => api.valueBets({ min_edge: 5 }) })
  const { data: dropData } = useQuery({ queryKey: ['dropping-odds', 10], queryFn: () => api.droppingOdds({ min_drop: 10 }) })
  const { data: histData } = useQuery({ queryKey: ['history-total'], queryFn: () => api.history({ limit: 0 }) })

  const liveCount = fixturesData?.fixtures.filter(f => f.status === 'live').length ?? 0
  const vbItems = (vbData?.items ?? []).slice(0, 4)
  const dropItems = (dropData?.items ?? []).slice(0, 4)
  const featured = fixturesData?.fixtures ?? []

  const STATS = [
    { label: '今日比赛', value: fixturesData?.total ?? '—', color: '#22c55e', sub: liveCount > 0 ? `● ${liveCount} 场进行中` : undefined, subColor: '#22c55e' },
    { label: 'Value Bets', value: vbData?.items.length ?? '—', color: '#a855f7', sub: undefined, subColor: undefined },
    { label: '跌水警报', value: dropData?.items.length ?? '—', color: '#22c55e', sub: undefined, subColor: undefined },
    { label: '已存储比赛', value: histData?.total ?? '—', color: '#3b82f6', sub: undefined, subColor: undefined },
  ]

  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-title">Dashboard</div>
          <div className="page-subtitle">今日数据概览 · {today}</div>
        </div>
        <button className="btn btn-secondary" onClick={() => window.location.reload()}>↻ 刷新</button>
      </div>

      <div className="stats-grid">
        {STATS.map(({ label, value, color, sub, subColor }) => (
          <div key={label} className="stat-card">
            <div className="stat-label">{label}</div>
            <div className="stat-value" style={{ color }}>{value}</div>
            {sub && <div className="stat-sub" style={{ color: subColor }}>{sub}</div>}
          </div>
        ))}
      </div>

      <div className="dash-section">
        <div className="dash-section-title">💎 今日 Value Bets</div>
        {vbItems.length === 0
          ? <div style={{ color: '#475569', fontSize: 13 }}>暂无 Value Bets</div>
          : (
            <div className="dash-2col">
              {vbItems.map((item, i) => {
                const dir = item.selection === 'home' ? '主胜' : item.selection === 'away' ? '客胜' : '平局'
                const time = new Date(item.kickoff_utc).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
                return (
                  <div key={i} className="alert-card" style={{ borderColor: '#a855f733' }}>
                    <div className="alert-icon" style={{ background: '#a855f722' }}>💎</div>
                    <div>
                      <div className="alert-match">{item.home_team} vs {item.away_team}</div>
                      <div className="alert-detail">{item.competition_name} · {time} · {dir}</div>
                      <div className="alert-tags">
                        <span className="badge bp">边际+{item.edge_pct.toFixed(1)}%</span>
                        <span className="badge bb">赔率{item.odds.toFixed(2)}</span>
                        <span className="badge bp">概率{Math.round(item.prob * 100)}%</span>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )
        }
      </div>

      <div className="dash-section">
        <div className="dash-section-title">📉 最新跌水警报</div>
        {dropItems.length === 0
          ? <div style={{ color: '#475569', fontSize: 13 }}>暂无跌水警报</div>
          : (
            <div className="dash-2col">
              {dropItems.map((item, i) => {
                const time = new Date(item.kickoff_utc).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
                return (
                  <div key={i} className="alert-card" style={{ borderColor: '#22c55e33' }}>
                    <div className="alert-icon" style={{ background: '#22c55e22' }}>↓</div>
                    <div>
                      <div className="alert-match">{item.home_team} vs {item.away_team}</div>
                      <div className="alert-detail">{item.competition_name} · {time}</div>
                      <div className="alert-tags">
                        <span className="badge bg">{item.market} ↓{Math.abs(item.drop_pct ?? 0).toFixed(1)}%</span>
                        <span className="badge bb">{item.odds_home?.toFixed(2) ?? '—'} / {item.odds_draw?.toFixed(2) ?? '—'} / {item.odds_away?.toFixed(2) ?? '—'}</span>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )
        }
      </div>

      <div className="dash-section">
        <div className="dash-section-title">📋 今日精选比赛</div>
        {selectedLeagues.length === 0
          ? <div style={{ color: '#475569', fontSize: 13 }}>请先在比赛列表中选择关注联赛</div>
          : featured.length === 0
          ? <div style={{ color: '#475569', fontSize: 13 }}>今日无精选比赛</div>
          : <div className="match-grid">{featured.map(f => <MatchCard key={f.id} fixture={f} />)}</div>
        }
      </div>
    </>
  )
}

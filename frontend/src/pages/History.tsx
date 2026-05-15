import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'

type DropFilter = 'all' | 'drop'

export default function History() {
  const navigate = useNavigate()
  const [offset, setOffset] = useState(0)
  const [dropFilter, setDropFilter] = useState<DropFilter>('all')
  const [leagueFilter, setLeagueFilter] = useState<number | null>(null)
  const limit = 50

  const { data: compData } = useQuery({ queryKey: ['competitions'], queryFn: api.competitions, staleTime: 5 * 60_000 })
  const topLeagues = (compData?.competitions ?? []).slice(0, 8)

  const { data, isLoading } = useQuery({
    queryKey: ['history', offset, leagueFilter],
    queryFn: () => api.history({ limit, offset, league: leagueFilter ?? undefined }),
  })

  const rawItems = data?.items ?? []
  const items = dropFilter === 'drop' ? rawItems.filter(f => f.drop_pct !== null) : rawItems
  const total = data?.total ?? 0

  function resultClass(f: typeof items[0]): string {
    if (f.status !== 'ft' || f.score_home == null || f.score_away == null) return ''
    if (f.score_home > f.score_away) return 'rw'
    if (f.score_home === f.score_away) return 'rd'
    return 'rl'
  }

  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-title">历史记录</div>
          <div className="page-subtitle">已存储比赛数据 · 共 {total} 场</div>
        </div>
      </div>

      <div className="hist-table">
        <div className="hist-filters">
          <button className={`chip${dropFilter === 'all' ? ' active' : ''}`} onClick={() => setDropFilter('all')}>全部</button>
          <button className={`chip${dropFilter === 'drop' ? ' active' : ''}`} onClick={() => setDropFilter('drop')}>有跌水</button>
          <span style={{ width: 1, alignSelf: 'stretch', background: '#1e293b', margin: '0 4px' }} />
          <button className={`chip${leagueFilter === null ? ' active' : ''}`} onClick={() => { setLeagueFilter(null); setOffset(0) }}>所有联赛</button>
          {topLeagues.map(l => (
            <button key={l.id} className={`chip${leagueFilter === l.id ? ' active' : ''}`} onClick={() => { setLeagueFilter(l.id); setOffset(0) }}>
              {l.name}
            </button>
          ))}
        </div>

        {isLoading
          ? <div style={{ color: '#64748b', padding: 20 }}>加载中...</div>
          : items.length === 0
          ? <div style={{ textAlign: 'center', color: '#475569', padding: 60 }}>暂无已完成比赛记录</div>
          : (
            <table>
              <thead>
                <tr>
                  <th>日期</th>
                  <th>比赛</th>
                  <th>联赛</th>
                  <th>比分</th>
                  <th>趋势</th>
                  <th>跌水</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {items.map(f => {
                  const res = resultClass(f)
                  return (
                    <tr key={f.id} onClick={() => navigate(`/matches/${f.id}`)}>
                      <td>{new Date(f.kickoff_utc).toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })}</td>
                      <td className="td-match">{f.home_team} vs {f.away_team}</td>
                      <td style={{ maxWidth: 130, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{f.competition_name}</td>
                      <td className={`td-score${res ? ' ' + res : ''}`}>
                        {f.status === 'ft' && f.score_home != null ? `${f.score_home}–${f.score_away}` : '—'}
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: 3 }}>
                          {!!f.trend_home_win && <span className="badge bg">主胜↑</span>}
                          {!!f.trend_away_win && <span className="badge ba">客胜↑</span>}
                          {!!f.trend_btts && <span className="badge bb">BTTS</span>}
                        </div>
                      </td>
                      <td className="td-drop">{f.drop_pct !== null ? `↓${Math.abs(f.drop_pct).toFixed(0)}%` : ''}</td>
                      <td style={{ color: '#334155', fontSize: 11 }}>→</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )
        }

        {total > limit && (
          <div style={{ display: 'flex', justifyContent: 'center', gap: 8, marginTop: 16 }}>
            <button disabled={offset === 0} className="btn btn-secondary" onClick={() => setOffset(Math.max(0, offset - limit))}>上一页</button>
            <span style={{ padding: '6px 12px', color: '#64748b', fontSize: 13 }}>{Math.floor(offset / limit) + 1} / {Math.ceil(total / limit)}</span>
            <button disabled={offset + limit >= total} className="btn btn-secondary" onClick={() => setOffset(offset + limit)}>下一页</button>
          </div>
        )}
      </div>
    </>
  )
}

import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'

const BRAND: Record<string, string> = {
  ARS:'#ef0107', LIV:'#c8102e', MCI:'#6cabdd', MUN:'#da291c',
  CHE:'#034694', TOT:'#132257', BAR:'#004d98', REA:'#febe10',
  BAY:'#dc052d', BVB:'#fde100', JUV:'#000000', MIL:'#fb090b',
}
function abbrev(name: string) { return name.slice(0, 3).toUpperCase() }
function teamColor(name: string): string {
  const key = abbrev(name)
  if (BRAND[key]) return BRAND[key]
  let h = 0
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) & 0xffff
  return `hsl(${h % 360}, 55%, 40%)`
}

export default function MatchDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const { data, isLoading } = useQuery({
    queryKey: ['fixture', id],
    queryFn: () => api.fixture(Number(id)),
    enabled: !!id,
  })
  const { data: vbAll } = useQuery({ queryKey: ['value-bets', 0], queryFn: () => api.valueBets() })

  if (isLoading) return <div style={{ padding: 24, color: '#64748b' }}>加载中...</div>
  if (!data) return <div style={{ padding: 24, color: '#64748b' }}>比赛不存在</div>

  const { fixture: f, odds_history, h2h, stats } = data
  const vbMatch = (vbAll?.items ?? []).filter(v => v.fixture_id === f.id)
  const kickoffStr = new Date(f.kickoff_utc).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
  const ohSlice = odds_history.slice(-10)
  const maxOdds = Math.max(...ohSlice.map(s => s.odds_home ?? 0), 1)

  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-title">比赛详情</div>
          <div className="page-subtitle">{f.competition_name} · {kickoffStr}</div>
        </div>
        <button className="btn btn-secondary" onClick={() => navigate(-1)}>← 返回列表</button>
      </div>

      <div className="detail-area">
        <div className="detail-hero">
          <div className="detail-teams-row">
            <div className="detail-team">
              <div className="detail-abbr" style={{ background: teamColor(f.home_team) }}>{abbrev(f.home_team)}</div>
              <div className="detail-tname">{f.home_team}</div>
              {stats.home && (
                <div className="detail-record">
                  {stats.home.wins}W {stats.home.draws}D {stats.home.losses}L · 进{stats.home.gf} 失{stats.home.ga}
                </div>
              )}
            </div>
            <div className="detail-center">
              <div style={{ fontSize: 11, color: '#475569' }}>{new Date(f.kickoff_utc).toLocaleDateString('zh-CN')}</div>
              <div style={{ fontSize: 26, fontWeight: 900, color: '#f1f5f9' }}>
                {f.status !== 'pre' ? `${f.score_home ?? 0} – ${f.score_away ?? 0}` : 'VS'}
              </div>
              <div style={{ fontSize: 11, color: '#475569' }}>{f.competition_name}</div>
              <div style={{ display: 'flex', gap: 4, marginTop: 4 }}>
                {f.status === 'live' && <span className="mc-status st-live">● 进行中</span>}
                {f.status === 'ft' && <span className="mc-status st-ft">已结束</span>}
                {vbMatch.length > 0 && <span className="badge bp">Value</span>}
                {!!f.trend_btts && <span className="badge bb">BTTS</span>}
              </div>
            </div>
            <div className="detail-team">
              <div className="detail-abbr" style={{ background: teamColor(f.away_team) }}>{abbrev(f.away_team)}</div>
              <div className="detail-tname">{f.away_team}</div>
              {stats.away && (
                <div className="detail-record">
                  {stats.away.wins}W {stats.away.draws}D {stats.away.losses}L · 进{stats.away.gf} 失{stats.away.ga}
                </div>
              )}
            </div>
          </div>

          {f.prob_home_win !== null && (
            <>
              <div style={{ height: 8, borderRadius: 4, overflow: 'hidden', display: 'flex', marginBottom: 8 }}>
                <div style={{ flex: Math.round((f.prob_home_win ?? 0) * 100), background: '#22c55e' }} />
                <div style={{ flex: Math.round((f.prob_draw ?? 0) * 100), background: '#475569' }} />
                <div style={{ flex: Math.round((f.prob_away_win ?? 0) * 100), background: '#f59e0b' }} />
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#64748b', marginBottom: 12 }}>
                <span style={{ color: '#22c55e' }}>主胜 {Math.round((f.prob_home_win ?? 0) * 100)}%</span>
                <span>平 {Math.round((f.prob_draw ?? 0) * 100)}%</span>
                <span style={{ color: '#f59e0b' }}>客胜 {Math.round((f.prob_away_win ?? 0) * 100)}%</span>
              </div>
            </>
          )}

          <div className="odds-box">
            <div className={`ob${f.trend_home_win ? ' hot' : ''}`} style={{ minWidth: 64 }}>
              <div className="ol">主胜</div>
              <div className="ov">{f.odds_home?.toFixed(2) ?? '—'}</div>
            </div>
            <div className="ob" style={{ minWidth: 64 }}>
              <div className="ol">平局</div>
              <div className="ov">{f.odds_draw?.toFixed(2) ?? '—'}</div>
            </div>
            <div className={`ob${f.trend_away_win ? ' hot' : ''}`} style={{ minWidth: 64 }}>
              <div className="ol">客胜</div>
              <div className="ov">{f.odds_away?.toFixed(2) ?? '—'}</div>
            </div>
            {f.drop_pct !== null && (
              <div className="ob" style={{ minWidth: 64, background: '#22c55e22', border: '1px solid #22c55e44' }}>
                <div className="ol">跌水</div>
                <div className="ov" style={{ color: '#22c55e' }}>↓{Math.abs(f.drop_pct).toFixed(1)}%</div>
              </div>
            )}
          </div>
        </div>

        <div className="detail-grid">
          <div className="detail-card">
            <div className="detail-card-title">赔率历史 — 主胜走势</div>
            {ohSlice.length === 0
              ? <div style={{ color: '#475569', fontSize: 12 }}>暂无赔率历史记录</div>
              : ohSlice.map((snap, i) => {
                const pct = ((snap.odds_home ?? 0) / maxOdds) * 100
                const t = new Date(snap.recorded_at).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
                return (
                  <div key={i} className="oh-row">
                    <span className="oh-time">{t}</span>
                    <div className="oh-bar-wrap"><div className="oh-bar" style={{ width: `${pct}%` }} /></div>
                    <span className="oh-val">{snap.odds_home?.toFixed(2) ?? '—'}</span>
                  </div>
                )
              })
            }
          </div>

          <div className="detail-card">
            <div className="detail-card-title">近期 H2H 交锋记录</div>
            {(!h2h || h2h.length === 0)
              ? <div style={{ color: '#475569', fontSize: 12 }}>暂无 H2H 交锋记录</div>
              : h2h.map((m, i) => {
                const homeWon = m.score_h > m.score_a
                const draw = m.score_h === m.score_a
                return (
                  <div key={i} className="h2h-row">
                    <span className="h2h-date">{String(m.date).slice(0, 10)}</span>
                    <span className="h2h-match">{m.home} vs {m.away}</span>
                    <span className="h2h-score">{m.score_h}–{m.score_a}</span>
                    <span className={`h2h-res ${homeWon ? 'res-h' : draw ? 'res-d' : 'res-a'}`}>
                      {homeWon ? '主胜' : draw ? '平' : '客胜'}
                    </span>
                  </div>
                )
              })
            }
          </div>

          <div className="detail-card">
            <div className="detail-card-title">赛季数据对比</div>
            {(!stats.home && !stats.away)
              ? <div style={{ color: '#475569', fontSize: 12 }}>暂无赛季数据</div>
              : ([
                ['进球', stats.home?.gf ?? 0, stats.away?.gf ?? 0],
                ['失球', stats.home?.ga ?? 0, stats.away?.ga ?? 0],
                ['主场胜率%', stats.home?.win_pct_home ?? 0, stats.away?.win_pct_home ?? 0],
                ['场均进球', +(stats.home?.goals_avg ?? 0).toFixed(1), +(stats.away?.goals_avg ?? 0).toFixed(1)],
                ['客场胜率%', stats.home?.win_pct_away ?? 0, stats.away?.win_pct_away ?? 0],
              ] as [string, number, number][]).map(([lbl, hv, av]) => {
                const total = (hv + av) || 1
                return (
                  <div key={lbl} className="sc-row">
                    <span className="sc-vl">{hv}</span>
                    <span className="sc-lbl">{lbl}</span>
                    <div className="sc-bars">
                      <div className="sc-h" style={{ width: `${(hv / total) * 100}%` }} />
                      <div className="sc-a" />
                    </div>
                    <span className="sc-vr">{av}</span>
                  </div>
                )
              })
            }
          </div>

          <div className="detail-card">
            <div className="detail-card-title">趋势分析</div>
            {!f.drop_pct && !f.trend_home_win && !f.trend_away_win && !f.trend_btts && vbMatch.length === 0
              ? <div style={{ color: '#475569', fontSize: 12 }}>暂无分析数据</div>
              : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 12, color: '#94a3b8', lineHeight: 1.6 }}>
                  {f.drop_pct !== null && f.drop_pct <= -10 && (
                    <p>📉 <strong style={{ color: '#22c55e' }}>跌水警报：</strong>{f.drop_market ?? ''}赔率下跌 {Math.abs(f.drop_pct).toFixed(1)}%。</p>
                  )}
                  {!!f.trend_home_win && <p>🏠 <strong style={{ color: '#22c55e' }}>主胜趋势：</strong>主队近期主场表现强势。</p>}
                  {!!f.trend_away_win && <p>✈️ <strong style={{ color: '#f59e0b' }}>客胜趋势：</strong>客队近期客场表现出色。</p>}
                  {!!f.trend_btts && <p>⚽ <strong style={{ color: '#3b82f6' }}>双进球趋势：</strong>两队近期均有进球，BTTS 概率较高。</p>}
                  {vbMatch.map((v, i) => (
                    <p key={i}>💎 <strong style={{ color: '#a855f7' }}>Value Bet：</strong>
                      {v.selection === 'home' ? '主胜' : v.selection === 'away' ? '客胜' : '平局'} ·
                      赔率 {v.odds.toFixed(2)} · 边际优势 <strong style={{ color: '#22c55e' }}>+{v.edge_pct.toFixed(1)}%</strong>
                    </p>
                  ))}
                </div>
              )
            }
          </div>
        </div>
      </div>
    </>
  )
}

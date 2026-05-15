import { useNavigate } from 'react-router-dom'
import type { FixtureSummary } from '../../lib/api'
import ProbBar from './ProbBar'

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

export default function MatchCard({ fixture: f }: { fixture: FixtureSummary }) {
  const navigate = useNavigate()
  const isLive = f.status === 'live'
  const isFT = f.status === 'ft'
  const time = new Date(f.kickoff_utc).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  const statusClass = isLive ? 'st-live' : isFT ? 'st-ft' : 'st-pre'
  const statusLabel = isLive ? '● 进行中' : isFT ? '已结束' : '未开赛'

  return (
    <div
      className={`mcard${isLive ? ' live' : ''}`}
      onClick={() => navigate(`/matches/${f.id}`)}
      role="button"
      tabIndex={0}
      onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') navigate(`/matches/${f.id}`) }}
    >
      <div className="mc-hdr">
        <span className="mc-hdr-lname">{f.competition_name}</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
          <span className="mc-hdr-time">{time}</span>
          <span className={`mc-status ${statusClass}`}>{statusLabel}</span>
        </div>
      </div>

      <div className="mc-body">
        <div className="mc-team home">
          <div className="t-namerow">
            <div className="t-abbr" style={{ background: teamColor(f.home_team) }}>{abbrev(f.home_team)}</div>
            <span className="t-fullname">{f.home_team}</span>
          </div>
          {f.home_stats && <>
            <div className="t-record">
              <span className="t-wdl">
                <span className="w">{f.home_stats.wins}W</span>{' '}
                <span className="d">{f.home_stats.draws}D</span>{' '}
                <span className="l">{f.home_stats.losses}L</span>
              </span>
            </div>
            <div className="t-goals">
              <span className="g-for">{f.home_stats.gf}</span>
              <span className="g-sep">/</span>
              <span className="g-ag">{f.home_stats.ga}</span>
              <span className="g-avg">·{f.home_stats.goals_avg.toFixed(1)}/场</span>
            </div>
            {f.home_stats.form5.length > 0 && (
              <div className="t-form">
                {f.home_stats.form5.map((r, i) => <span key={i} className={`fp ${r}`}>{r}</span>)}
              </div>
            )}
            <div className="t-winpct h">{f.home_stats.win_pct_home}%</div>
            <div className="t-winlbl">主场胜率</div>
          </>}
        </div>

        <div className="mc-center">
          {(isLive || isFT)
            ? <span className="mc-score">{f.score_home ?? 0}–{f.score_away ?? 0}</span>
            : <span className="mc-vs-txt">VS</span>
          }
          {f.prob_draw !== null && <>
            <span className="mc-draw">{Math.round(f.prob_draw * 100)}%</span>
            <span className="mc-drawlbl">平局</span>
          </>}
        </div>

        <div className="mc-team away">
          <div className="t-namerow">
            <div className="t-abbr" style={{ background: teamColor(f.away_team) }}>{abbrev(f.away_team)}</div>
            <span className="t-fullname">{f.away_team}</span>
          </div>
          {f.away_stats && <>
            <div className="t-record">
              <span className="t-wdl">
                <span className="w">{f.away_stats.wins}W</span>{' '}
                <span className="d">{f.away_stats.draws}D</span>{' '}
                <span className="l">{f.away_stats.losses}L</span>
              </span>
            </div>
            <div className="t-goals">
              <span className="g-for">{f.away_stats.gf}</span>
              <span className="g-sep">/</span>
              <span className="g-ag">{f.away_stats.ga}</span>
              <span className="g-avg">·{f.away_stats.goals_avg.toFixed(1)}/场</span>
            </div>
            {f.away_stats.form5.length > 0 && (
              <div className="t-form">
                {f.away_stats.form5.map((r, i) => <span key={i} className={`fp ${r}`}>{r}</span>)}
              </div>
            )}
            <div className="t-winpct a">{f.away_stats.win_pct_away}%</div>
            <div className="t-winlbl">客场胜率</div>
          </>}
        </div>
      </div>

      <ProbBar home={f.prob_home_win} draw={f.prob_draw} away={f.prob_away_win} />

      <div className="mc-ftr">
        <div className="odds-box">
          <div className={`ob${f.trend_home_win ? ' hot' : ''}`}>
            <div className="ol">主</div>
            <div className="ov">{f.odds_home?.toFixed(2) ?? '—'}</div>
          </div>
          <div className="ob">
            <div className="ol">平</div>
            <div className="ov">{f.odds_draw?.toFixed(2) ?? '—'}</div>
          </div>
          <div className={`ob${f.trend_away_win ? ' hot' : ''}`}>
            <div className="ol">客</div>
            <div className="ov">{f.odds_away?.toFixed(2) ?? '—'}</div>
          </div>
        </div>
        <div className="ftr-sep" />
        <div className="drop-col">
          <div className="drop-val">{f.drop_pct !== null ? `${f.drop_pct < 0 ? '↓' : '↑'}${Math.abs(f.drop_pct).toFixed(0)}%` : '—'}</div>
          <div className="drop-mkt">{f.drop_market ?? ''}</div>
        </div>
        <div className="badges">
          {!!f.trend_home_win && <span className="badge bg">主胜↑</span>}
          {!!f.trend_away_win && <span className="badge ba">客胜↑</span>}
          {!!f.trend_btts && <span className="badge bb">BTTS</span>}
          {f.drop_pct !== null && f.drop_pct <= -10 && <span className="badge br">跌水</span>}
        </div>
      </div>
    </div>
  )
}

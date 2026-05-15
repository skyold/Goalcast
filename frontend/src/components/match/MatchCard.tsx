import { useNavigate } from 'react-router-dom'
import type { FixtureSummary, TeamStats } from '../../lib/api'
import ProbBar from './ProbBar'
import Badge from '../shared/Badge'

function abbrev(name: string) { return name.slice(0, 3).toUpperCase() }

const BRAND: Record<string, string> = {
  ARS:'#ef0107', LIV:'#c8102e', MCI:'#6cabdd', MUN:'#da291c',
  CHE:'#034694', TOT:'#132257', BAR:'#004d98', REA:'#febe10',
  BAY:'#dc052d', BVB:'#fde100', JUV:'#000000', MIL:'#fb090b',
}
const teamColor = (name: string) => BRAND[abbrev(name)] ?? '#3b82f6'

function TeamBadge({ name }: { name: string }) {
  return (
    <span style={{ display:'inline-flex', alignItems:'center', justifyContent:'center', width:28, height:28, borderRadius:4, background:teamColor(name), color:'#fff', fontSize:9, fontWeight:700, letterSpacing:1, flexShrink:0 }}>
      {abbrev(name)}
    </span>
  )
}

function FormBox({ r }: { r: string }) {
  const bg = r === 'W' ? '#22c55e' : r === 'L' ? '#ef4444' : '#64748b'
  return <span style={{ width:16, height:16, borderRadius:2, background:bg, color:'#fff', fontSize:9, fontWeight:700, display:'inline-flex', alignItems:'center', justifyContent:'center' }}>{r}</span>
}

function TeamCol({ team, stats, isHome }: { team: string; stats: TeamStats | null; isHome: boolean }) {
  const gp = stats ? stats.wins + stats.draws + stats.losses : 0
  const winPct = gp > 0 ? Math.round((stats!.wins / gp) * 100) : 0
  const avgGoals = gp > 0 ? (stats!.gf / gp).toFixed(1) : '0.0'
  return (
    <div style={{ flex:1, display:'flex', flexDirection:'column', gap:3, alignItems:isHome?'flex-end':'flex-start' }}>
      <div style={{ display:'flex', alignItems:'center', gap:6, flexDirection:isHome?'row-reverse':'row' }}>
        <TeamBadge name={team} />
        <span style={{ fontSize:13, fontWeight:600, color:'#e2e8f0', textAlign:isHome?'right':'left' }}>{team}</span>
      </div>
      {stats && <>
        <span style={{ fontSize:10, color:'#64748b' }}>#{stats.pos} · {stats.wins}W {stats.draws}D {stats.losses}L</span>
        <span style={{ fontSize:10, color:'#64748b' }}>{stats.gf}GF {stats.ga}GA · {avgGoals}/场</span>
        <div style={{ display:'flex', gap:2 }}>{(stats.form5 ?? []).map((r, i) => <FormBox key={i} r={r} />)}</div>
        <span style={{ fontSize:10, color:isHome?'#22c55e':'#f59e0b' }}>{isHome?'主场':'客场'} {winPct}%</span>
      </>}
    </div>
  )
}

export default function MatchCard({ fixture: f }: { fixture: FixtureSummary }) {
  const navigate = useNavigate()
  const isLive = f.status === 'live', isFT = f.status === 'ft'
  const time = new Date(f.kickoff_utc).toLocaleTimeString('zh-CN',{hour:'2-digit',minute:'2-digit'})
  const drawPct = f.prob_draw !== null ? Math.round(f.prob_draw * 100) : null

  return (
    <div
      onClick={() => navigate(`/matches/${f.id}`)}
      style={{ background:'#0d1626', border:`1px solid ${isLive?'#22c55e':'#1a2d47'}`, borderRadius:10, padding:'12px 14px', cursor:'pointer', display:'flex', flexDirection:'column', gap:8, boxShadow:isLive?'0 0 8px rgba(34,197,94,0.15)':'none', transition:'border-color 0.15s' }}
      onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.borderColor='#3b82f6' }}
      onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.borderColor=isLive?'#22c55e':'#1a2d47' }}
    >
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center' }}>
        <span style={{ fontSize:11, color:'#64748b' }}>{f.competition_name}</span>
        <div style={{ display:'flex', alignItems:'center', gap:6 }}>
          <span style={{ fontSize:11, color:'#94a3b8' }}>{time}</span>
          {isLive && <Badge variant="green">LIVE</Badge>}
          {isFT && <Badge variant="blue">FT</Badge>}
        </div>
      </div>

      <div style={{ display:'grid', gridTemplateColumns:'1fr auto 1fr', gap:8, alignItems:'center' }}>
        <TeamCol team={f.home_team} stats={f.home_stats} isHome={true} />
        <div style={{ display:'flex', flexDirection:'column', alignItems:'center', gap:4, minWidth:50 }}>
          {(isLive||isFT)
            ? <span style={{ fontSize:20, fontWeight:700, color:'#e2e8f0' }}>{f.score_home??0} - {f.score_away??0}</span>
            : <span style={{ fontSize:12, color:'#64748b', fontWeight:600 }}>VS</span>
          }
          {drawPct !== null && <span style={{ fontSize:10, color:'#64748b' }}>平 {drawPct}%</span>}
        </div>
        <TeamCol team={f.away_team} stats={f.away_stats} isHome={false} />
      </div>

      <ProbBar home={f.prob_home_win} draw={f.prob_draw} away={f.prob_away_win} />

      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', paddingTop:4, borderTop:'1px solid #1a2d47' }}>
        <div style={{ display:'flex', gap:8, fontSize:12 }}>
          {f.odds_home != null && <>
            <span style={{ color:'#22c55e' }}>{f.odds_home.toFixed(2)}</span>
            <span style={{ color:'#94a3b8' }}>{f.odds_draw?.toFixed(2)??'-'}</span>
            <span style={{ color:'#f59e0b' }}>{f.odds_away?.toFixed(2)??'-'}</span>
          </>}
        </div>
        <div style={{ display:'flex', gap:4 }}>
          {f.drop_pct!=null&&f.drop_pct<=-10 && <Badge variant="red">↓{Math.abs(f.drop_pct).toFixed(0)}%</Badge>}
          {!!f.trend_home_win && <Badge variant="green">主胜↑</Badge>}
          {!!f.trend_away_win && <Badge variant="amber">客胜↑</Badge>}
          {!!f.trend_btts && <Badge variant="blue">BTTS</Badge>}
        </div>
      </div>
    </div>
  )
}

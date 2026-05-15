import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import ProbBar from '../components/match/ProbBar'

export default function MatchDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const { data, isLoading } = useQuery({
    queryKey: ['fixture', id],
    queryFn: () => api.fixture(Number(id)),
    enabled: !!id,
  })

  if (isLoading) return <div style={{ padding:24, color:'#64748b' }}>加载中...</div>
  if (!data) return <div style={{ padding:24, color:'#64748b' }}>比赛不存在</div>

  const { fixture: f, odds_history, h2h, stats } = data

  return (
    <div style={{ padding:24, maxWidth:900, display:'flex', flexDirection:'column', gap:20 }}>
      <button onClick={() => navigate(-1)} style={{ alignSelf:'flex-start', padding:'6px 12px', borderRadius:6, border:'1px solid #1a2d47', background:'#0d1626', color:'#94a3b8', cursor:'pointer', fontSize:13 }}>
        ← 返回
      </button>

      <div style={{ background:'#0d1626', border:'1px solid #1a2d47', borderRadius:10, padding:20 }}>
        <div style={{ fontSize:12, color:'#64748b', marginBottom:8 }}>{f.competition_name} · {new Date(f.kickoff_utc).toLocaleString('zh-CN')}</div>
        <div style={{ display:'grid', gridTemplateColumns:'1fr auto 1fr', gap:12, alignItems:'center', marginBottom:12 }}>
          <span style={{ fontSize:18, fontWeight:700, color:'#e2e8f0', textAlign:'right' }}>{f.home_team}</span>
          <span style={{ fontSize:24, fontWeight:700, color:'#e2e8f0' }}>{f.status!=='pre'?`${f.score_home??0} - ${f.score_away??0}`:'VS'}</span>
          <span style={{ fontSize:18, fontWeight:700, color:'#e2e8f0' }}>{f.away_team}</span>
        </div>
        <ProbBar home={f.prob_home_win} draw={f.prob_draw} away={f.prob_away_win} />
        <div style={{ display:'flex', justifyContent:'space-between', fontSize:11, color:'#64748b', marginTop:4 }}>
          <span>主胜 {f.prob_home_win!==null?Math.round(f.prob_home_win*100)+'%':'-'}</span>
          <span>平 {f.prob_draw!==null?Math.round(f.prob_draw*100)+'%':'-'}</span>
          <span>客胜 {f.prob_away_win!==null?Math.round(f.prob_away_win*100)+'%':'-'}</span>
        </div>
      </div>

      {odds_history.length > 0 && (
        <div style={{ background:'#0d1626', border:'1px solid #1a2d47', borderRadius:10, padding:20 }}>
          <h2 style={{ fontSize:14, fontWeight:600, color:'#e2e8f0', marginBottom:12 }}>赔率历史</h2>
          {odds_history.slice(-15).map((snap,i) => (
            <div key={i} style={{ display:'grid', gridTemplateColumns:'140px 60px 60px 60px 80px', gap:8, padding:'5px 0', borderBottom:'1px solid #1e293b', fontSize:12 }}>
              <span style={{ color:'#64748b' }}>{new Date(snap.recorded_at).toLocaleString('zh-CN',{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'})}</span>
              <span style={{ color:'#22c55e' }}>{snap.odds_home?.toFixed(2)??'-'}</span>
              <span style={{ color:'#94a3b8' }}>{snap.odds_draw?.toFixed(2)??'-'}</span>
              <span style={{ color:'#f59e0b' }}>{snap.odds_away?.toFixed(2)??'-'}</span>
              <span style={{ color:snap.drop_pct!=null&&snap.drop_pct<0?'#ef4444':'#64748b' }}>{snap.drop_pct!==null?`${snap.drop_pct.toFixed(1)}%`:''}</span>
            </div>
          ))}
        </div>
      )}

      {h2h && h2h.length > 0 && (
        <div style={{ background:'#0d1626', border:'1px solid #1a2d47', borderRadius:10, padding:20 }}>
          <h2 style={{ fontSize:14, fontWeight:600, color:'#e2e8f0', marginBottom:12 }}>H2H 近期交锋</h2>
          {h2h.map((m,i) => (
            <div key={i} style={{ display:'grid', gridTemplateColumns:'80px 1fr 50px 1fr', gap:8, padding:'5px 0', borderBottom:'1px solid #1e293b', fontSize:12, alignItems:'center' }}>
              <span style={{ color:'#64748b' }}>{String(m.date).slice(0,10)}</span>
              <span style={{ color:'#e2e8f0', textAlign:'right' }}>{m.home}</span>
              <span style={{ color:'#3b82f6', fontWeight:600, textAlign:'center' }}>{m.score_h}-{m.score_a}</span>
              <span style={{ color:'#e2e8f0' }}>{m.away}</span>
            </div>
          ))}
        </div>
      )}

      {(stats.home || stats.away) && (
        <div style={{ background:'#0d1626', border:'1px solid #1a2d47', borderRadius:10, padding:20 }}>
          <h2 style={{ fontSize:14, fontWeight:600, color:'#e2e8f0', marginBottom:12 }}>赛季数据对比</h2>
          <div style={{ display:'grid', gridTemplateColumns:'1fr 100px 1fr', gap:6 }}>
            {(['pos','wins','draws','losses','gf','ga'] as const).map((key) => {
              const labels: Record<string,string> = {pos:'排名',wins:'胜',draws:'平',losses:'负',gf:'进球',ga:'失球'}
              return (
                <div key={key} style={{ display:'contents' }}>
                  <span style={{ fontSize:13, color:'#22c55e', textAlign:'right' }}>{(stats.home as any)?.[key]??'-'}</span>
                  <span style={{ fontSize:11, color:'#64748b', textAlign:'center' }}>{labels[key]}</span>
                  <span style={{ fontSize:13, color:'#f59e0b' }}>{(stats.away as any)?.[key]??'-'}</span>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

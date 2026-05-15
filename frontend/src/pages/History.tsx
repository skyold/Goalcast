import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'

export default function History() {
  const navigate = useNavigate()
  const [offset, setOffset] = useState(0)
  const limit = 50
  const { data, isLoading } = useQuery({
    queryKey: ['history', offset],
    queryFn: () => api.history({ limit, offset }),
  })
  const items = data?.items ?? [], total = data?.total ?? 0

  return (
    <div style={{ padding:24 }}>
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:20 }}>
        <h1 style={{ fontSize:20, fontWeight:700, color:'#e2e8f0', margin:0 }}>历史记录</h1>
        <span style={{ fontSize:13, color:'#64748b' }}>共 {total} 场</span>
      </div>
      {isLoading ? <div style={{ color:'#64748b' }}>加载中...</div> : (
        <>
          <div style={{ background:'#0d1626', border:'1px solid #1a2d47', borderRadius:10, overflow:'hidden' }}>
            <table style={{ width:'100%', borderCollapse:'collapse', fontSize:13 }}>
              <thead>
                <tr style={{ borderBottom:'1px solid #1a2d47' }}>
                  {['时间','联赛','主队','比分','客队','赔率 (主/平/客)','主胜%'].map(h => (
                    <th key={h} style={{ padding:'10px 14px', textAlign:'left', fontSize:11, color:'#475569', fontWeight:600 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {items.map(f => (
                  <tr key={f.id} onClick={() => navigate(`/matches/${f.id}`)}
                    style={{ borderBottom:'1px solid #1e293b', cursor:'pointer' }}
                    onMouseEnter={e => (e.currentTarget as HTMLElement).style.background='#111c2e'}
                    onMouseLeave={e => (e.currentTarget as HTMLElement).style.background='transparent'}
                  >
                    <td style={{ padding:'8px 14px', color:'#64748b' }}>{new Date(f.kickoff_utc).toLocaleDateString('zh-CN')}</td>
                    <td style={{ padding:'8px 14px', color:'#64748b', maxWidth:130, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>{f.competition_name}</td>
                    <td style={{ padding:'8px 14px', color:'#e2e8f0', fontWeight:500 }}>{f.home_team}</td>
                    <td style={{ padding:'8px 14px', color:'#3b82f6', fontWeight:700, textAlign:'center' }}>{f.score_home??'-'} - {f.score_away??'-'}</td>
                    <td style={{ padding:'8px 14px', color:'#e2e8f0', fontWeight:500 }}>{f.away_team}</td>
                    <td style={{ padding:'8px 14px', color:'#94a3b8' }}>
                      <span style={{ color:'#22c55e' }}>{f.odds_home?.toFixed(2)??'-'}</span>{' / '}{f.odds_draw?.toFixed(2)??'-'}{' / '}
                      <span style={{ color:'#f59e0b' }}>{f.odds_away?.toFixed(2)??'-'}</span>
                    </td>
                    <td style={{ padding:'8px 14px', color:'#94a3b8' }}>{f.prob_home_win!==null?Math.round(f.prob_home_win*100)+'%':'-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {total > limit && (
            <div style={{ display:'flex', justifyContent:'center', gap:8, marginTop:16 }}>
              <button disabled={offset===0} onClick={() => setOffset(Math.max(0,offset-limit))} style={{ padding:'6px 16px', borderRadius:6, border:'1px solid #1a2d47', background:'#0d1626', color:'#94a3b8', cursor:offset===0?'not-allowed':'pointer', opacity:offset===0?0.5:1 }}>上一页</button>
              <span style={{ padding:'6px 12px', color:'#64748b', fontSize:13 }}>{Math.floor(offset/limit)+1} / {Math.ceil(total/limit)}</span>
              <button disabled={offset+limit>=total} onClick={() => setOffset(offset+limit)} style={{ padding:'6px 16px', borderRadius:6, border:'1px solid #1a2d47', background:'#0d1626', color:'#94a3b8', cursor:offset+limit>=total?'not-allowed':'pointer', opacity:offset+limit>=total?0.5:1 }}>下一页</button>
            </div>
          )}
        </>
      )}
    </div>
  )
}

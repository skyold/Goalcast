import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import Badge from '../components/shared/Badge'

export default function DroppingOdds() {
  const navigate = useNavigate()
  const [minDrop, setMinDrop] = useState(10)
  const { data, isLoading } = useQuery({
    queryKey: ['dropping-odds', minDrop],
    queryFn: () => api.droppingOdds({ min_drop: minDrop }),
    refetchInterval: 30_000,
  })
  const items = data?.items ?? []

  return (
    <div style={{ padding:24 }}>
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:20 }}>
        <h1 style={{ fontSize:20, fontWeight:700, color:'#e2e8f0', margin:0 }}>跌水监控</h1>
        <div style={{ display:'flex', gap:12, alignItems:'center' }}>
          {data?.synced_at && <span style={{ fontSize:11, color:'#475569' }}>更新: {new Date(data.synced_at).toLocaleTimeString('zh-CN')}</span>}
          <div style={{ display:'flex', alignItems:'center', gap:8 }}>
            <span style={{ fontSize:13, color:'#64748b' }}>最小跌幅:</span>
            <select value={minDrop} onChange={e => setMinDrop(Number(e.target.value))} style={{ background:'#0d1626', border:'1px solid #1a2d47', borderRadius:6, color:'#94a3b8', padding:'4px 8px', fontSize:13 }}>
              {[5,10,15,20].map(v => <option key={v} value={v}>{v}%</option>)}
            </select>
          </div>
        </div>
      </div>
      {isLoading ? <div style={{ color:'#64748b' }}>加载中...</div>
        : items.length === 0 ? <div style={{ color:'#475569', fontSize:14, textAlign:'center', padding:40 }}>暂无跌水数据</div>
        : (
          <div style={{ display:'flex', flexDirection:'column', gap:8 }}>
            {items.map((item,i) => (
              <div key={i} onClick={() => navigate(`/matches/${item.fixture_id}`)}
                style={{ background:'#0d1626', border:'1px solid #1a2d47', borderRadius:10, padding:'12px 16px', cursor:'pointer', display:'grid', gridTemplateColumns:'1fr auto auto auto auto', gap:12, alignItems:'center', transition:'border-color 0.15s' }}
                onMouseEnter={e => (e.currentTarget as HTMLElement).style.borderColor='#3b82f6'}
                onMouseLeave={e => (e.currentTarget as HTMLElement).style.borderColor='#1a2d47'}
              >
                <div>
                  <div style={{ fontSize:13, fontWeight:600, color:'#e2e8f0' }}>{item.home_team} vs {item.away_team}</div>
                  <div style={{ fontSize:11, color:'#64748b', marginTop:2 }}>{item.competition_name} · {new Date(item.kickoff_utc).toLocaleString('zh-CN',{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'})}</div>
                </div>
                <Badge variant="red">↓{Math.abs(item.drop_pct??0).toFixed(1)}%</Badge>
                <span style={{ fontSize:12, color:'#64748b' }}>{item.market}</span>
                <div style={{ display:'flex', gap:6, fontSize:12 }}>
                  <span style={{ color:'#22c55e' }}>{item.odds_home?.toFixed(2)??'-'}</span>
                  <span style={{ color:'#94a3b8' }}>{item.odds_draw?.toFixed(2)??'-'}</span>
                  <span style={{ color:'#f59e0b' }}>{item.odds_away?.toFixed(2)??'-'}</span>
                </div>
                <span style={{ fontSize:11, color:'#475569' }}>{new Date(item.recorded_at).toLocaleTimeString('zh-CN')}</span>
              </div>
            ))}
          </div>
        )
      }
    </div>
  )
}

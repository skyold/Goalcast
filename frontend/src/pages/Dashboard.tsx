import { useQuery } from '@tanstack/react-query'
import { useStore } from '../lib/store'
import { api } from '../lib/api'
import MatchCard from '../components/match/MatchCard'
import Badge from '../components/shared/Badge'

export default function Dashboard() {
  const { selectedLeagues, selectedDate } = useStore()

  const { data: fixturesData } = useQuery({
    queryKey: ['fixtures', selectedDate, selectedLeagues.join(','), 10],
    queryFn: () => api.fixtures({ date: selectedDate, leagues: selectedLeagues.join(','), limit: 10 }),
    enabled: selectedLeagues.length > 0,
  })
  const { data: vbData } = useQuery({ queryKey:['value-bets',5], queryFn:() => api.valueBets({min_edge:5}) })
  const { data: dropData } = useQuery({ queryKey:['dropping-odds',10], queryFn:() => api.droppingOdds({min_drop:10}) })

  const fixtures = fixturesData?.fixtures ?? []
  const vbItems = (vbData?.items ?? []).slice(0, 5)
  const dropItems = (dropData?.items ?? []).slice(0, 5)

  return (
    <div style={{ padding:24, display:'flex', flexDirection:'column', gap:24 }}>
      <h1 style={{ fontSize:20, fontWeight:700, color:'#e2e8f0', margin:0 }}>Dashboard</h1>

      <div style={{ display:'grid', gridTemplateColumns:'repeat(3,1fr)', gap:12 }}>
        {[
          { label:'今日比赛', value:fixturesData?.total??'—', color:'#3b82f6' },
          { label:'Value Bets', value:vbData?.items.length??'—', color:'#a855f7' },
          { label:'跌水警报', value:dropData?.items.length??'—', color:'#ef4444' },
        ].map(({label,value,color}) => (
          <div key={label} style={{ background:'#0d1626', border:'1px solid #1a2d47', borderRadius:10, padding:'16px 20px' }}>
            <div style={{ fontSize:28, fontWeight:700, color }}>{value}</div>
            <div style={{ fontSize:12, color:'#64748b', marginTop:4 }}>{label}</div>
          </div>
        ))}
      </div>

      {vbItems.length > 0 && (
        <section>
          <h2 style={{ fontSize:14, fontWeight:600, color:'#a855f7', marginBottom:10 }}>Top Value Bets</h2>
          <div style={{ display:'flex', flexDirection:'column', gap:6 }}>
            {vbItems.map((item,i) => (
              <div key={i} style={{ background:'#0d1626', border:'1px solid #1a2d47', borderRadius:8, padding:'10px 14px', display:'flex', justifyContent:'space-between', alignItems:'center' }}>
                <span style={{ fontSize:13, color:'#e2e8f0' }}>{item.home_team} vs {item.away_team}</span>
                <div style={{ display:'flex', gap:8, alignItems:'center' }}>
                  <Badge variant="purple">{item.selection==='home'?'主胜':item.selection==='away'?'客胜':'平局'}</Badge>
                  <span style={{ fontSize:12, color:'#a855f7', fontWeight:600 }}>+{item.edge_pct.toFixed(1)}%</span>
                  <span style={{ fontSize:12, color:'#94a3b8' }}>{item.odds.toFixed(2)}</span>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {dropItems.length > 0 && (
        <section>
          <h2 style={{ fontSize:14, fontWeight:600, color:'#ef4444', marginBottom:10 }}>跌水警报</h2>
          <div style={{ display:'flex', flexDirection:'column', gap:6 }}>
            {dropItems.map((item,i) => (
              <div key={i} style={{ background:'#0d1626', border:'1px solid #1a2d47', borderRadius:8, padding:'10px 14px', display:'flex', justifyContent:'space-between', alignItems:'center' }}>
                <span style={{ fontSize:13, color:'#e2e8f0' }}>{item.home_team} vs {item.away_team}</span>
                <div style={{ display:'flex', gap:8, alignItems:'center' }}>
                  <Badge variant="red">↓{Math.abs(item.drop_pct??0).toFixed(1)}%</Badge>
                  <span style={{ fontSize:11, color:'#64748b' }}>{item.market}</span>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {fixtures.length > 0 && (
        <section>
          <h2 style={{ fontSize:14, fontWeight:600, color:'#e2e8f0', marginBottom:10 }}>精选比赛</h2>
          <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:12 }}>
            {fixtures.map(f => <MatchCard key={f.id} fixture={f} />)}
          </div>
        </section>
      )}

      {selectedLeagues.length === 0 && (
        <div style={{ color:'#475569', fontSize:14, textAlign:'center', padding:40 }}>
          请在比赛列表中选择关注的联赛，主页将显示精选比赛
        </div>
      )}
    </div>
  )
}

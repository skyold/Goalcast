import { useQuery } from '@tanstack/react-query'
import { useStore } from '../lib/store'
import { api } from '../lib/api'
import MatchCardGrid from '../components/match/MatchCardGrid'
import DateFilter from '../components/filters/DateFilter'
import LeagueFilter from '../components/filters/LeagueFilter'
import Skeleton from '../components/shared/Skeleton'

export default function Matches() {
  const { selectedLeagues, selectedDate } = useStore()

  const { data, isLoading } = useQuery({
    queryKey: ['fixtures', selectedDate, selectedLeagues.join(',')],
    queryFn: () => api.fixtures({ date:selectedDate, leagues:selectedLeagues.join(',') }),
    enabled: selectedLeagues.length > 0,
  })

  const fixtures = data?.fixtures ?? []

  return (
    <div style={{ display:'flex', height:'100vh', overflow:'hidden' }}>
      <div style={{ width:260, borderRight:'1px solid #1a2d47', padding:16, overflowY:'auto', flexShrink:0 }}>
        <div style={{ marginBottom:16 }}>
          <div style={{ fontSize:10, color:'#475569', fontWeight:600, textTransform:'uppercase', letterSpacing:1, marginBottom:8 }}>日期</div>
          <DateFilter />
        </div>
        <div>
          <div style={{ fontSize:10, color:'#475569', fontWeight:600, textTransform:'uppercase', letterSpacing:1, marginBottom:8 }}>联赛</div>
          <LeagueFilter />
        </div>
      </div>

      <div style={{ flex:1, display:'flex', flexDirection:'column', overflow:'hidden' }}>
        <div style={{ padding:'10px 16px', borderBottom:'1px solid #1a2d47', fontSize:12, color:'#64748b', flexShrink:0 }}>
          {selectedLeagues.length > 0 ? `${fixtures.length} 场比赛 · ${selectedDate}` : '请选择联赛'}
        </div>

        {selectedLeagues.length === 0 && (
          <div style={{ flex:1, display:'flex', alignItems:'center', justifyContent:'center', color:'#475569', fontSize:14 }}>
            请先在左侧选择联赛以加载比赛数据
          </div>
        )}
        {isLoading && selectedLeagues.length > 0 && (
          <div style={{ padding:16, display:'grid', gridTemplateColumns:'1fr 1fr', gap:12 }}>
            {Array.from({length:6}).map((_,i) => <Skeleton key={i} height={220} style={{borderRadius:10}} />)}
          </div>
        )}
        {!isLoading && selectedLeagues.length > 0 && fixtures.length === 0 && (
          <div style={{ flex:1, display:'flex', alignItems:'center', justifyContent:'center', color:'#475569', fontSize:14 }}>
            当天所选联赛无比赛
          </div>
        )}
        {!isLoading && fixtures.length > 0 && <MatchCardGrid fixtures={fixtures} />}
      </div>
    </div>
  )
}

import { useQuery } from '@tanstack/react-query'
import { useStore } from '../../lib/store'
import { api } from '../../lib/api'

const CONTINENT: Record<string, string> = {
  'Premier':'Europe','La Liga':'Europe','Bundesliga':'Europe','Serie A':'Europe',
  'Ligue 1':'Europe','Champions':'Europe','Europa':'Europe','Championship':'Europe',
  'Eredivisie':'Europe','Primeira':'Europe','Super Lig':'Europe','Scottish':'Europe',
  'MLS':'Americas','Liga MX':'Americas','Brasileirao':'Americas','Copa':'Americas',
  'J1':'Asia','K League':'Asia','CSL':'Asia','A-League':'Asia','AFC':'Asia','Saudi':'Asia',
  'CAF':'Africa','AFCON':'Africa',
}

function getContinent(name: string): string {
  for (const [key, val] of Object.entries(CONTINENT)) { if (name.includes(key)) return val }
  return 'Other'
}

const ORDER = ['Europe','Americas','Asia','Africa','Other']

export default function LeagueFilter() {
  const { selectedLeagues, toggleLeague } = useStore()
  const { data } = useQuery({ queryKey:['competitions'], queryFn:api.competitions, staleTime:5*60_000 })
  const competitions = data?.competitions ?? []

  if (competitions.length === 0)
    return <span style={{ fontSize:12, color:'#475569' }}>同步数据后联赛将出现在此处</span>

  const byContinent = competitions.reduce<Record<string, typeof competitions>>((acc, c) => {
    const cont = getContinent(c.name);(acc[cont] ??= []).push(c); return acc
  }, {})
  const sorted = Object.entries(byContinent).sort(([a],[b]) => ORDER.indexOf(a)-ORDER.indexOf(b))

  return (
    <div style={{ display:'flex', flexDirection:'column', gap:14 }}>
      {sorted.map(([continent, leagues]) => (
        <div key={continent}>
          <div style={{ fontSize:10, color:'#475569', fontWeight:600, marginBottom:6, textTransform:'uppercase', letterSpacing:1 }}>{continent}</div>
          <div style={{ display:'flex', flexWrap:'wrap', gap:5 }}>
            {leagues.map(l => {
              const active = selectedLeagues.includes(l.id)
              return (
                <button key={l.id} onClick={() => toggleLeague(l.id)} style={{ padding:'3px 8px', borderRadius:20, fontSize:11, border:`1px solid ${active?'#3b82f6':'#1a2d47'}`, background:active?'rgba(59,130,246,0.15)':'#0d1626', color:active?'#3b82f6':'#94a3b8', cursor:'pointer', whiteSpace:'nowrap' }}>
                  {l.name}
                </button>
              )
            })}
          </div>
        </div>
      ))}
    </div>
  )
}

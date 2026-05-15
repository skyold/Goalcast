import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useStore } from '../lib/store'
import { api, type FixtureSummary } from '../lib/api'
import MatchCard from '../components/match/MatchCard'
import Skeleton from '../components/shared/Skeleton'

const CONTINENT: Record<string, string> = {
  'Premier':'Europe','La Liga':'Europe','Bundesliga':'Europe','Serie A':'Europe',
  'Ligue 1':'Europe','Champions':'Europe','Europa':'Europe','Championship':'Europe',
  'Eredivisie':'Europe','Primeira':'Europe','Super Lig':'Europe','Scottish':'Europe',
  'MLS':'Americas','Liga MX':'Americas','Brasileirao':'Americas','Copa':'Americas',
  'J1':'Asia','K League':'Asia','CSL':'Asia','A-League':'Asia','AFC':'Asia','Saudi':'Asia',
  'CAF':'Africa','AFCON':'Africa',
}
const CONT_FLAG: Record<string, string> = { Europe:'🌍', Americas:'🌎', Asia:'🌏', Africa:'🌍', Other:'🌐' }

function getContinent(name: string): string {
  for (const [key, val] of Object.entries(CONTINENT)) { if (name.includes(key)) return val }
  return 'Other'
}

function offsetDay(n: number): string {
  const d = new Date(); d.setDate(d.getDate() + n); return d.toISOString().split('T')[0]
}
const DATE_PRESETS = [
  { label: '今天', fn: () => offsetDay(0) },
  { label: '明天', fn: () => offsetDay(1) },
  { label: '后天', fn: () => offsetDay(2) },
]

type SortKey = 'time' | 'drop' | 'prob'

function sortFixtures(fixtures: FixtureSummary[], key: SortKey): FixtureSummary[] {
  return [...fixtures].sort((a, b) => {
    if (key === 'drop') return (a.drop_pct ?? 0) - (b.drop_pct ?? 0)
    if (key === 'prob') return (b.prob_home_win ?? 0) - (a.prob_home_win ?? 0)
    return new Date(a.kickoff_utc).getTime() - new Date(b.kickoff_utc).getTime()
  })
}

export default function Matches() {
  const { selectedLeagues, toggleLeague, selectedDate, setDate } = useStore()
  const [sort, setSort] = useState<SortKey>('time')
  const presetValues = DATE_PRESETS.map(p => p.fn())
  const isPreset = presetValues.includes(selectedDate)

  const { data: compData } = useQuery({ queryKey: ['competitions'], queryFn: api.competitions, staleTime: 5 * 60_000 })
  const competitions = compData?.competitions ?? []

  const { data, isLoading } = useQuery({
    queryKey: ['fixtures', selectedDate, selectedLeagues.join(',')],
    queryFn: () => api.fixtures({ date: selectedDate, leagues: selectedLeagues.join(',') }),
    enabled: selectedLeagues.length > 0,
  })

  const fixtures = sortFixtures(data?.fixtures ?? [], sort)
  const groups = fixtures.reduce<Record<string, FixtureSummary[]>>((acc, f) => {
    (acc[f.competition_name] ??= []).push(f); return acc
  }, {})

  const allIds = competitions.map(c => c.id)
  function selectAll() { allIds.forEach(id => { if (!selectedLeagues.includes(id)) toggleLeague(id) }) }
  function selectNone() { allIds.forEach(id => { if (selectedLeagues.includes(id)) toggleLeague(id) }) }

  const byContinent = competitions.reduce<Record<string, typeof competitions>>((acc, c) => {
    const cont = getContinent(c.name);(acc[cont] ??= []).push(c); return acc
  }, {})
  const ORDER = ['Europe', 'Americas', 'Asia', 'Africa', 'Other']
  const sorted = Object.entries(byContinent).sort(([a], [b]) => ORDER.indexOf(a) - ORDER.indexOf(b))

  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-title">比赛列表</div>
          <div className="page-subtitle">
            {selectedLeagues.length > 0 ? `共 ${fixtures.length} 场 · 已选 ${selectedLeagues.length} 个联赛` : '请选择联赛'}
          </div>
        </div>
        <button className="btn btn-secondary" onClick={() => window.location.reload()}>↻ 刷新</button>
      </div>

      <div className="filter-section">
        <div className="filter-row">
          <span className="filter-lbl">日期</span>
          {DATE_PRESETS.map(({ label, fn }) => {
            const v = fn()
            return (
              <button key={label} className={`chip${selectedDate === v ? ' active' : ''}`} onClick={() => setDate(v)}>{label}</button>
            )
          })}
          <input type="date" value={!isPreset ? selectedDate : ''} onChange={e => e.target.value && setDate(e.target.value)} className="date-native" />
        </div>

        <div className="filter-row" style={{ alignItems: 'flex-start' }}>
          <span className="filter-lbl" style={{ paddingTop: 2 }}>联赛</span>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, flex: 1 }}>
            <div style={{ display: 'flex', gap: 5 }}>
              <button className="pill all-pill" onClick={selectAll}>全选</button>
              <button className="pill" onClick={selectNone}>全不选</button>
            </div>
            {sorted.map(([continent, leagues]) => (
              <div key={continent} className="continent-block">
                <div className="continent-label">{CONT_FLAG[continent] ?? '🌐'} {continent}</div>
                <div className="league-pills">
                  {leagues.map(l => (
                    <button key={l.id} className={`pill${selectedLeagues.includes(l.id) ? ' sel' : ''}`} onClick={() => toggleLeague(l.id)}>
                      {l.name}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="sort-row">
          <span style={{ fontSize: 11, color: '#475569' }}>排序</span>
          <select className="sort-select" value={sort} onChange={e => setSort(e.target.value as SortKey)}>
            <option value="time">开赛时间</option>
            <option value="drop">跌水幅度</option>
            <option value="prob">主胜概率</option>
          </select>
          <span className="result-info"><em>{fixtures.length}</em> 场 · <em>{selectedLeagues.length}</em> 联赛</span>
        </div>
      </div>

      <div className="matches-area">
        {selectedLeagues.length === 0 && (
          <div style={{ textAlign: 'center', color: '#475569', padding: 60 }}>请先选择联赛以加载比赛数据</div>
        )}
        {isLoading && selectedLeagues.length > 0 && (
          <div className="match-grid">
            {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} height={260} style={{ borderRadius: 10 }} />)}
          </div>
        )}
        {!isLoading && selectedLeagues.length > 0 && fixtures.length === 0 && (
          <div style={{ textAlign: 'center', color: '#475569', padding: 60 }}>当天所选联赛无比赛</div>
        )}
        {!isLoading && Object.entries(groups).map(([league, fxs]) => (
          <div key={league} className="league-group">
            <div className="league-title">
              <span>{CONT_FLAG[getContinent(league)] ?? '🌐'}</span>
              <span className="league-name">{league}</span>
              <span className="league-count">{fxs.length}场</span>
            </div>
            <div className="match-grid">
              {fxs.map(f => <MatchCard key={f.id} fixture={f} />)}
            </div>
          </div>
        ))}
      </div>
    </>
  )
}

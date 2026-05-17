// Restyled Matches page. Behavior matches the original (league filter, predictability,
// drop, AI, sort). Differences from the original:
//   - removed legacy CSS classnames; uses the new themes.css system (chip, filter-grp, etc)
//   - leagues rendered as flat chips (you can re-enable the continent grouping later)
//   - skeletons replaced by .empty placeholder for brevity (drop in <Skeleton /> if needed)
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useStore } from '../lib/store'
import { api, type FixtureSummary } from '../lib/api'
import MatchCard from '../components/match/MatchCard'

type SortKey = 'time' | 'drop' | 'prob'

function sortFixtures(fixtures: FixtureSummary[], key: SortKey): FixtureSummary[] {
  return [...fixtures].sort((a, b) => {
    if (key === 'drop') return (b.drop_flag?.drop_percentage ?? -Infinity) - (a.drop_flag?.drop_percentage ?? -Infinity)
    if (key === 'prob') return (b.prediction_summary?.home_win_pct ?? -Infinity) - (a.prediction_summary?.home_win_pct ?? -Infinity)
    return new Date(a.kickoff_utc).getTime() - new Date(b.kickoff_utc).getTime()
  })
}

const DATE_PRESETS = [
  { label: '今天', offset: 0 },
  { label: '明天', offset: 1 },
  { label: '后天', offset: 2 },
]
const offsetDay = (n: number) => {
  const d = new Date(); d.setDate(d.getDate() + n)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

export default function Matches() {
  const nav = useNavigate()
  const { selectedLeagues, toggleLeague, selectedDate, setDate } = useStore()
  const [sort, setSort] = useState<SortKey>('time')
  const [filter, setFilter] = useState({ excludePoor: false, onlyHigh: false, minDrop: false, hasAi: false })
  const [limit, setLimit] = useState(200)

  const { data: compData } = useQuery({
    queryKey: ['competitions'],
    queryFn: api.competitions,
    staleTime: 5 * 60_000,
  })
  const competitions = compData?.competitions ?? []

  const { data, isLoading } = useQuery({
    queryKey: ['fixtures', selectedDate, selectedLeagues.join(','), sort, filter, limit],
    queryFn: () => api.fixtures({
      date: selectedDate,
      leagues: selectedLeagues.join(',') || undefined,
      limit,
      ...(filter.excludePoor ? { predictability: 'high,good,medium' } : {}),
      ...(filter.onlyHigh ? { predictability: 'high,good' } : {}),
      ...(filter.minDrop ? { min_drop: 50 } : {}),
      ...(filter.hasAi ? { has_ai: true } : {}),
    }),
    enabled: selectedLeagues.length > 0,
  })

  const fixtures = sortFixtures(data?.fixtures ?? [], sort)

  const groups: Record<string, FixtureSummary[]> = {}
  for (const f of fixtures) (groups[f.competition_name] ??= []).push(f)

  const presetValues = DATE_PRESETS.map(p => offsetDay(p.offset))
  const isPreset = presetValues.includes(selectedDate)

  return (
    <>
      <div className="ph">
        <div>
          <div className="ph-title">比赛列表</div>
          <div className="ph-sub">
            {selectedLeagues.length > 0
              ? `共 ${fixtures.length} 场 · 已选 ${selectedLeagues.length} 个联赛`
              : '请选择联赛'}
          </div>
        </div>
        <div className="ph-actions">
          <button className="btn" onClick={() => window.location.reload()}>↻ 刷新</button>
          <button className="btn btn-primary">导出 CSV</button>
        </div>
      </div>

      <div className="filters">
        <div className="filter-grp">
          <span className="filter-lbl">日期</span>
          {DATE_PRESETS.map(({ label, offset }) => {
            const v = offsetDay(offset)
            return (
              <button key={label}
                className={`chip${selectedDate === v ? ' active' : ''}`}
                onClick={() => setDate(v)}>{label}</button>
            )
          })}
          <input
            type="date"
            className="date-pick"
            value={!isPreset ? selectedDate : ''}
            onChange={(e) => e.target.value && setDate(e.target.value)}
          />
        </div>

        <div className="filter-grp">
          <span className="filter-lbl">联赛</span>
          {competitions.map(c => (
            <button
              key={c.id}
              className={`chip chip-mute${selectedLeagues.includes(c.id) ? ' active' : ''}`}
              onClick={() => toggleLeague(c.id)}
            >{c.name}</button>
          ))}
        </div>

        <div className="filter-grp">
          <span className="filter-lbl">筛选</span>
          <button className={`chip${filter.excludePoor ? ' active' : ''}`} onClick={() => setFilter(f => ({ ...f, excludePoor: !f.excludePoor }))}>排除 差</button>
          <button className={`chip${filter.onlyHigh    ? ' active' : ''}`} onClick={() => setFilter(f => ({ ...f, onlyHigh: !f.onlyHigh }))}>只看 高+良</button>
          <button className={`chip${filter.minDrop     ? ' active' : ''}`} onClick={() => setFilter(f => ({ ...f, minDrop: !f.minDrop }))}>跌幅 ≥ 50%</button>
          <button className={`chip${filter.hasAi       ? ' active' : ''}`} onClick={() => setFilter(f => ({ ...f, hasAi: !f.hasAi }))}>有 AI</button>
        </div>

        <div className="filter-spacer" />

        <div className="filter-grp">
          <span className="filter-lbl">排序</span>
          <select className="date-pick" value={sort} onChange={e => setSort(e.target.value as SortKey)}>
            <option value="time">开赛时间</option>
            <option value="drop">跌幅</option>
            <option value="prob">主胜概率</option>
          </select>
        </div>
      </div>

      <div className="page">
        {selectedLeagues.length === 0 && <div className="empty">请先选择联赛以加载比赛数据</div>}
        {isLoading && selectedLeagues.length > 0 && <div className="empty">加载中…</div>}
        {!isLoading && selectedLeagues.length > 0 && fixtures.length === 0 && (
          <div className="empty">当天所选联赛无比赛</div>
        )}
        {Object.entries(groups).map(([league, fxs]) => (
          <div key={league} className="league-block">
            <h2 className="section-title">
              <span>{league}</span>
              <span className="count">{fxs.length} 场</span>
            </h2>
            <div className="match-grid">
              {fxs.map(f => <MatchCard key={f.id} fixture={f} onClick={() => nav(`/matches/${f.id}`)} />)}
            </div>
          </div>
        ))}
        {fixtures.length >= limit && (
          <button className="btn" style={{ display: 'block', margin: '20px auto' }} onClick={() => setLimit(l => l + 200)}>
            加载更多
          </button>
        )}
      </div>
    </>
  )
}

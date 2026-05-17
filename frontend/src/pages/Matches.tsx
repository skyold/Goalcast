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
import { POPULAR_LEAGUE_IDS } from '../lib/popularLeagues'
import { pickZh, useT } from '../lib/i18n'
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
  { labelKey: 'matches.date.today',     offset: 0 },
  { labelKey: 'matches.date.tomorrow',  offset: 1 },
  { labelKey: 'matches.date.day_after', offset: 2 },
]
const offsetDay = (n: number) => {
  const d = new Date(); d.setDate(d.getDate() + n)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

export default function Matches() {
  const nav = useNavigate()
  const t = useT()
  const { selectedLeagues, toggleLeague, selectedDate, setDate } = useStore()
  const [sort, setSort] = useState<SortKey>('time')
  const [filter, setFilter] = useState({ excludePoor: false, onlyHigh: false, minDrop: false, hasAi: false })
  const [limit, setLimit] = useState(200)
  const [showAllLeagues, setShowAllLeagues] = useState(false)

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
  for (const f of fixtures) (groups[pickZh(f.competition_name_zh, f.competition_name)] ??= []).push(f)

  const presetValues = DATE_PRESETS.map(p => offsetDay(p.offset))
  const isPreset = presetValues.includes(selectedDate)

  return (
    <>
      <div className="ph">
        <div>
          <div className="ph-title">{t('matches.title')}</div>
          <div className="ph-sub">
            {selectedLeagues.length > 0
              ? t('matches.subtitle.counts', { total: fixtures.length, leagues: selectedLeagues.length })
              : t('matches.subtitle.empty')}
          </div>
        </div>
        <div className="ph-actions">
          <button className="btn" onClick={() => window.location.reload()}>↻ {t('common.refresh')}</button>
          <button className="btn btn-primary">{t('common.export_csv')}</button>
        </div>
      </div>

      <div className="filters">
        <div className="filter-grp">
          <span className="filter-lbl">{t('matches.section.date')}</span>
          {DATE_PRESETS.map(({ labelKey, offset }) => {
            const v = offsetDay(offset)
            return (
              <button key={labelKey}
                className={`chip${selectedDate === v ? ' active' : ''}`}
                onClick={() => setDate(v)}>{t(labelKey)}</button>
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
          <span className="filter-lbl">{t('matches.section.league')}</span>
          {(() => {
            const popular: typeof competitions = []
            const others: typeof competitions = []
            for (const c of competitions) {
              if (POPULAR_LEAGUE_IDS.has(c.id) || selectedLeagues.includes(c.id)) popular.push(c)
              else others.push(c)
            }
            const visible = showAllLeagues ? [...popular, ...others] : popular
            return (
              <>
                {visible.map(c => (
                  <button
                    key={c.id}
                    className={`chip chip-mute${selectedLeagues.includes(c.id) ? ' active' : ''}`}
                    onClick={() => toggleLeague(c.id)}
                  >{pickZh(c.name_zh, c.name)}</button>
                ))}
                {others.length > 0 && (
                  <button
                    className="chip chip-mute"
                    onClick={() => setShowAllLeagues(v => !v)}
                  >{showAllLeagues ? t('common.collapse') : t('matches.more_n', { n: others.length })}</button>
                )}
              </>
            )
          })()}
        </div>

        <div className="filter-grp">
          <span className="filter-lbl">{t('matches.section.filter')}</span>
          <button className={`chip${filter.excludePoor ? ' active' : ''}`} onClick={() => setFilter(f => ({ ...f, excludePoor: !f.excludePoor }))}>{t('matches.filter.exclude_poor')}</button>
          <button className={`chip${filter.onlyHigh    ? ' active' : ''}`} onClick={() => setFilter(f => ({ ...f, onlyHigh: !f.onlyHigh }))}>{t('matches.filter.high_only')}</button>
          <button className={`chip${filter.minDrop     ? ' active' : ''}`} onClick={() => setFilter(f => ({ ...f, minDrop: !f.minDrop }))}>{t('matches.filter.min_drop')}</button>
          <button className={`chip${filter.hasAi       ? ' active' : ''}`} onClick={() => setFilter(f => ({ ...f, hasAi: !f.hasAi }))}>{t('matches.filter.has_ai')}</button>
        </div>

        <div className="filter-spacer" />

        <div className="filter-grp">
          <span className="filter-lbl">{t('matches.section.sort')}</span>
          <select className="date-pick" value={sort} onChange={e => setSort(e.target.value as SortKey)}>
            <option value="time">{t('matches.sort.time')}</option>
            <option value="drop">{t('matches.sort.drop')}</option>
            <option value="prob">{t('matches.sort.prob')}</option>
          </select>
        </div>
      </div>

      <div className="page">
        {selectedLeagues.length === 0 && <div className="empty">{t('matches.empty.choose')}</div>}
        {isLoading && selectedLeagues.length > 0 && <div className="empty">{t('matches.empty.loading')}</div>}
        {!isLoading && selectedLeagues.length > 0 && fixtures.length === 0 && (
          <div className="empty">{t('matches.empty.none')}</div>
        )}
        {Object.entries(groups).map(([league, fxs]) => (
          <div key={league} className="league-block">
            <h2 className="section-title">
              <span>{league}</span>
              <span className="count">{t('matches.section.matches_count', { n: fxs.length })}</span>
            </h2>
            <div className="match-grid">
              {fxs.map(f => <MatchCard key={f.id} fixture={f} onClick={() => nav(`/matches/${f.id}`)} />)}
            </div>
          </div>
        ))}
        {fixtures.length >= limit && (
          <button className="btn" style={{ display: 'block', margin: '20px auto' }} onClick={() => setLimit(l => l + 200)}>
            {t('matches.load_more')}
          </button>
        )}
      </div>
    </>
  )
}

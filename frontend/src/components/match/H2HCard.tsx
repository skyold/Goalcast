// MatchDetail H2H card. Reconstructed from fixtures table (no external feed).
import { useQuery } from '@tanstack/react-query'
import { api } from '../../lib/api'
import { fmtKickoff } from '../../lib/format'
import { pickZh, useT } from '../../lib/i18n'

interface Props {
  fixtureId: number
  anchorHomeTeamId: number | null | undefined
}

export function H2HCard({ fixtureId, anchorHomeTeamId }: Props) {
  const t = useT()
  const { data, isLoading } = useQuery({
    queryKey: ['h2h', fixtureId],
    queryFn: () => api.h2h(fixtureId, { limit: 10 }),
    staleTime: 5 * 60_000,
  })

  const items = data?.items ?? []
  const hasData = items.length > 0

  return (
    <div className="card">
      <div className="card-hdr">
        <div className="card-title">{t('insights.h2h.title')}</div>
        <span className="card-sub">{hasData ? t('insights.h2h.subtitle', { n: items.length }) : ''}</span>
      </div>
      {isLoading ? (
        <div className="empty">{t('matches.empty.loading')}</div>
      ) : !hasData ? (
        <div className="empty">{t('insights.h2h.empty')}</div>
      ) : (
        items.map(h => {
          const ko = fmtKickoff(h.kickoff_utc)
          const homeName = pickZh(h.home_team_zh, h.home_team)
          const awayName = pickZh(h.away_team_zh, h.away_team)
          const comp = pickZh(h.competition_name_zh, h.competition_name)
          const sh = h.score_home ?? 0
          const sa = h.score_away ?? 0
          const isHomeAnchor = h.home_team_id === anchorHomeTeamId
          let resultColor = 'var(--text)'
          if (sh > sa) resultColor = isHomeAnchor ? 'var(--acc)' : 'var(--neg)'
          else if (sh < sa) resultColor = isHomeAnchor ? 'var(--neg)' : 'var(--acc)'
          else resultColor = 'var(--draw)'

          return (
            <div key={h.id} className="drop-row" style={{ alignItems: 'center' }}>
              <span className="time" style={{ minWidth: 64 }}>{h.kickoff_utc.slice(0, 10)}</span>
              <span className="match" style={{ flex: 1 }}>
                {homeName} <span style={{ color: 'var(--text-mute)' }}>vs</span> {awayName}
                <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-mute)' }}>
                  {comp} · {ko.day}
                </div>
              </span>
              <span className="num" style={{ color: resultColor, fontWeight: 700, fontSize: 'var(--fs-lg)' }}>
                {t('insights.h2h.score', { home_score: sh, away_score: sa })}
              </span>
            </div>
          )
        })
      )}
    </div>
  )
}

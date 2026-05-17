// /insights/leagues/:id — aggregate league snapshot (FT fixtures only).
// Renders 7 KPIs in a grid + a small subtitle. No charts here; numbers tell the
// story succinctly. Most metrics are simple percentages.
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { pickZh, useT } from '../lib/i18n'

export default function LeagueStats() {
  const t = useT()
  const nav = useNavigate()
  const { id } = useParams()
  const competitionId = Number(id)

  const { data, isLoading } = useQuery({
    queryKey: ['league-stats', competitionId],
    queryFn: () => api.leagueStats(competitionId),
    enabled: !!competitionId,
    staleTime: 5 * 60_000,
  })

  if (isLoading || !data) {
    return <div className="empty">{t('matches.empty.loading')}</div>
  }

  const title = pickZh(data.competition_name_zh, data.competition_name ?? `#${competitionId}`)
  const empty = data.matches_played === 0

  return (
    <>
      <div className="ph">
        <div>
          <a href="#" onClick={(e) => { e.preventDefault(); nav(-1) }} className="card-sub" style={{ display: 'block', marginBottom: 4 }}>
            ← {t('matches.title')}
          </a>
          <div className="ph-title">{title} · {t('insights.league.title')}</div>
          <div className="ph-sub">{t('insights.league.subtitle')}</div>
        </div>
        <div className="ph-actions">
          <Link to={`/matches`} className="btn">{t('matches.title')}</Link>
        </div>
      </div>

      <div className="page">
        {empty ? (
          <div className="empty">{t('insights.league.empty')}</div>
        ) : (
          <div className="kpi-grid">
            <Kpi label={t('insights.league.matches_played')}     value={data.matches_played} />
            <Kpi label={t('insights.league.avg_goals')}          value={data.avg_goals.toFixed(2)} />
            <Kpi label={t('insights.league.home_win')}           value={pct(data.home_win_pct)} />
            <Kpi label={t('insights.league.draw')}               value={pct(data.draw_pct)} />
            <Kpi label={t('insights.league.away_win')}           value={pct(data.away_win_pct)} />
            <Kpi label={t('insights.league.upset')}              value={pct(data.upset_pct)}            sub={t('insights.league.upset_hint')} />
            <Kpi label={t('insights.league.top_predictability')} value={pct(data.top_predictability_pct)} />
            <Kpi label={t('insights.league.model_hit_rate')}
                 value={data.model_hit_rate_pct == null ? t('insights.league.unavailable') : pct(data.model_hit_rate_pct)}
                 sub={t('insights.league.model_hit_rate_hint')} />
          </div>
        )}
      </div>
    </>
  )
}

function pct(n: number): string { return `${n.toFixed(1)}%` }

function Kpi({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="kpi">
      <span className="kpi-lbl">{label}</span>
      <span className="kpi-val">{value}</span>
      {sub && <span className="kpi-delta">{sub}</span>}
    </div>
  )
}

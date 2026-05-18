// Backtest center — public, audit-style view of OddAlerts model accuracy
// over (FT × kickoff_snap) pairs. Cold-start safe: when enough=false the
// page shows a progress indicator instead of misleading metrics.
//
// V1 routing intentionally does NOT add this page to the sidebar; we wait
// until paper-trading Phase B (≥ 500 pairs) to surface it broadly.
import { useQuery } from '@tanstack/react-query'
import { api, type BacktestSummary, type BacktestByLeague } from '../lib/api'
import { pickZh, useT } from '../lib/i18n'

export default function Backtest() {
  const t = useT()
  const { data: summary, isLoading: sumLoading } = useQuery({
    queryKey: ['backtest-summary'],
    queryFn: () => api.backtest.summary({ min_samples: 500 }),
    staleTime: 60_000,
  })
  const { data: leagues, isLoading: lgLoading } = useQuery({
    queryKey: ['backtest-by-league'],
    queryFn: () => api.backtest.byLeague({ min_samples: 100 }),
    staleTime: 60_000,
  })

  return (
    <>
      <div className="ph">
        <div>
          <div className="ph-title">{t('backtest.title')}</div>
          <div className="ph-sub">{t('backtest.subtitle')}</div>
        </div>
      </div>

      <div className="page">
        {sumLoading && <div className="empty">{t('backtest.loading')}</div>}
        {summary && <SummaryCard s={summary} />}
        {lgLoading && <div className="empty">{t('backtest.loading')}</div>}
        {leagues && <LeagueTable d={leagues} t={t} />}
      </div>
    </>
  )
}

function SummaryCard({ s }: { s: BacktestSummary }) {
  const t = useT()
  const m = s.metrics
  const pct = (x: number | null) => (x == null ? '—' : `${(x * 100).toFixed(1)}%`)
  const ci  = (x: [number, number] | null) =>
    x == null ? '—' : `[${(x[0] * 100).toFixed(1)}%, ${(x[1] * 100).toFixed(1)}%]`
  const progress = Math.min(100, (s.samples / s.min_samples) * 100)

  if (!s.enough) {
    return (
      <div className="card" style={{ padding: 16 }}>
        <div style={{ fontWeight: 600, marginBottom: 8 }}>
          {t('backtest.accruing.title', { samples: s.samples, min: s.min_samples })}
        </div>
        <div style={{ fontSize: 'var(--fs-sm)', color: 'var(--text-mute)', marginBottom: 12 }}>
          {t('backtest.accruing.body')}
        </div>
        <div style={{ background: 'var(--bg-mute)', height: 6, borderRadius: 999, overflow: 'hidden' }}>
          <div style={{
            width: `${progress}%`, height: '100%',
            background: 'var(--acc)', transition: 'width .4s ease',
          }} />
        </div>
        <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-mute)', marginTop: 6 }}>
          {progress.toFixed(0)}% · {s.samples} / {s.min_samples}
        </div>
      </div>
    )
  }

  return (
    <div className="card" style={{ padding: 16 }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
        <Metric label={t('backtest.metric.hit_rate')} value={pct(m.top1_hit_rate)} sub={ci(m.top1_hit_rate_ci95)} />
        <Metric label={t('backtest.metric.brier')} value={m.brier == null ? '—' : m.brier.toFixed(3)} sub={t('backtest.metric.brier_hint')} />
        <Metric label={t('backtest.metric.samples')} value={s.samples.toString()} sub={`${s.scope.waypoint} · ${s.model_id}`} />
      </div>
    </div>
  )
}

function Metric({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div>
      <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-mute)' }}>{label}</div>
      <div style={{ fontSize: 'var(--fs-xl)', fontWeight: 700, marginTop: 2 }}>{value}</div>
      {sub && <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-mute)', marginTop: 2 }}>{sub}</div>}
    </div>
  )
}

function LeagueTable({ d, t }: { d: BacktestByLeague; t: (k: string, v?: any) => string }) {
  if (d.items.length === 0) {
    return <div className="empty">{t('backtest.by_league.empty')}</div>
  }
  return (
    <div className="card" style={{ padding: 0, overflow: 'hidden', marginTop: 16 }}>
      <table className="ht">
        <thead>
          <tr>
            <th>{t('backtest.col.league')}</th>
            <th style={{ textAlign: 'right' }}>{t('backtest.col.samples')}</th>
            <th style={{ textAlign: 'right' }}>{t('backtest.col.hit_rate')}</th>
            <th style={{ textAlign: 'right' }}>{t('backtest.col.brier')}</th>
          </tr>
        </thead>
        <tbody>
          {d.items.map(it => (
            <tr key={it.competition_id}>
              <td>{pickZh(it.competition_name_zh, it.competition_name ?? '') || `#${it.competition_id}`}</td>
              <td className="num" style={{ textAlign: 'right' }}>
                {it.samples}
                {!it.enough && <span style={{ color: 'var(--text-mute)', marginLeft: 4 }}>·{t('backtest.accruing.short')}</span>}
              </td>
              <td className="num" style={{ textAlign: 'right' }}>
                {it.top1_hit_rate == null ? '—' : `${(it.top1_hit_rate * 100).toFixed(1)}%`}
              </td>
              <td className="num" style={{ textAlign: 'right' }}>
                {it.brier == null ? '—' : it.brier.toFixed(3)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

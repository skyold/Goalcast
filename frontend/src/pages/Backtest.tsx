// Backtest center — public, audit-style view of OddAlerts model accuracy
// over (FT × kickoff_snap) pairs. Cold-start safe: when enough=false the
// page shows a progress indicator instead of misleading metrics.
//
// V1 routing intentionally does NOT add this page to the sidebar; we wait
// until paper-trading Phase B (≥ 500 pairs) to surface it broadly.
import { useQuery } from '@tanstack/react-query'
import {
  api,
  type BacktestSummary,
  type BacktestByLeague,
  type BacktestCalibration,
} from '../lib/api'
import { pickZh, useT } from '../lib/i18n'

export default function Backtest() {
  const t = useT()
  const { data: summary, isLoading: sumLoading } = useQuery({
    queryKey: ['backtest-summary'],
    queryFn: () => api.backtest.summary({ min_samples: 500 }),
    staleTime: 60_000,
  })
  const { data: calibration, isLoading: calLoading } = useQuery({
    queryKey: ['backtest-calibration'],
    queryFn: () => api.backtest.calibration({ bins: 10, min_per_bin: 30 }),
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
        {calLoading && <div className="empty">{t('backtest.loading')}</div>}
        {calibration && <CalibrationCard c={calibration} t={t} />}
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

function CalibrationCard({ c, t }: { c: BacktestCalibration; t: (k: string, v?: any) => string }) {
  const populated = c.bins.filter(b => b.n > 0)
  const totalSamples = populated.reduce((s, b) => s + b.n, 0)

  if (populated.length === 0) {
    return (
      <div className="card" style={{ padding: 16, marginTop: 16 }}>
        <div style={{ fontWeight: 600, marginBottom: 8 }}>{t('backtest.calibration.title')}</div>
        <div className="empty" style={{ padding: 0 }}>{t('backtest.calibration.accruing')}</div>
      </div>
    )
  }

  // SVG scatter — predicted_avg (x) vs actual_rate (y), with y=x reference line.
  // 240×240 viewport with 24px margin so labels don't crop.
  const W = 240, H = 240, M = 28
  const toX = (p: number) => M + p * (W - 2 * M)
  const toY = (r: number) => H - M - r * (H - 2 * M)
  const maxN = Math.max(...populated.map(b => b.n))

  return (
    <div className="card" style={{ padding: 16, marginTop: 16 }}>
      <div style={{ fontWeight: 600, marginBottom: 4 }}>{t('backtest.calibration.title')}</div>
      <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-mute)', marginBottom: 12 }}>
        {t('backtest.calibration.hint')}
      </div>
      <div style={{ display: 'flex', gap: 24, alignItems: 'flex-start', flexWrap: 'wrap' }}>
        <svg width={W} height={H} style={{ background: 'var(--bg-mute)', borderRadius: 6 }}>
          {/* axes */}
          <line x1={M} y1={H - M} x2={W - M} y2={H - M} stroke="var(--text-mute)" strokeWidth={1} />
          <line x1={M} y1={M}     x2={M}     y2={H - M} stroke="var(--text-mute)" strokeWidth={1} />
          {/* perfect-calibration diagonal */}
          <line x1={M} y1={H - M} x2={W - M} y2={M} stroke="var(--text-mute)" strokeDasharray="4 4" strokeWidth={1} />
          {/* points */}
          {populated.map(b => {
            const x = toX(b.predicted_avg!)
            const y = toY(b.actual_rate!)
            const r = 3 + 6 * Math.sqrt(b.n / maxN)
            return (
              <circle
                key={b.bin_index}
                cx={x} cy={y} r={r}
                fill={b.enough ? 'var(--acc)' : 'var(--text-mute)'}
                opacity={b.enough ? 0.85 : 0.45}
              />
            )
          })}
          {/* axis labels */}
          <text x={W / 2} y={H - 4} textAnchor="middle" fontSize={10} fill="var(--text-mute)">
            {t('backtest.calibration.x_label')}
          </text>
          <text x={10} y={H / 2} textAnchor="middle" fontSize={10} fill="var(--text-mute)"
                transform={`rotate(-90 10 ${H / 2})`}>
            {t('backtest.calibration.y_label')}
          </text>
        </svg>
        <div style={{ flex: 1, minWidth: 320 }}>
          <table className="ht" style={{ width: '100%' }}>
            <thead>
              <tr>
                <th>{t('backtest.calibration.col.bucket')}</th>
                <th style={{ textAlign: 'right' }}>{t('backtest.calibration.col.n')}</th>
                <th style={{ textAlign: 'right' }}>{t('backtest.calibration.col.predicted')}</th>
                <th style={{ textAlign: 'right' }}>{t('backtest.calibration.col.actual')}</th>
              </tr>
            </thead>
            <tbody>
              {populated.map(b => (
                <tr key={b.bin_index}>
                  <td>{Math.round(b.lower * 100)}–{Math.round(b.upper * 100)}%</td>
                  <td className="num" style={{ textAlign: 'right' }}>
                    {b.n}
                    {!b.enough && <span style={{ color: 'var(--text-mute)', marginLeft: 4 }}>·{t('backtest.accruing.short')}</span>}
                  </td>
                  <td className="num" style={{ textAlign: 'right' }}>
                    {b.predicted_avg == null ? '—' : `${(b.predicted_avg * 100).toFixed(1)}%`}
                  </td>
                  <td className="num" style={{ textAlign: 'right' }}>
                    {b.actual_rate == null ? '—' : `${(b.actual_rate * 100).toFixed(1)}%`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-mute)', marginTop: 8 }}>
            {t('backtest.calibration.footer', { n: totalSamples, min: c.min_per_bin })}
          </div>
        </div>
      </div>
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

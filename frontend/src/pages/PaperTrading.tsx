// Paper-trading center — public House Book virtual ledger.
//
// Three threshold bands (3% / 5% / 7%) run in parallel; UI lets the user
// compare ROI side-by-side. Personal Book + manual one-click betting are
// deliberately NOT in V1 — they ship after Phase B (≥100 settled bets).
//
// Compliance posture (paper-trading PRD review-locked):
//   • Bankroll is always rendered in "unit" — never with ¥/$ symbols.
//   • No "switch to real account" / "place real bet" affordance anywhere.
//   • Cold-start banner explicitly flags "virtual units, not advice".
//
// Routing intentionally omits this from the sidebar; surface broadens in
// Phase B once ROI is statistically meaningful.
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api, type PaperHouseSummary } from '../lib/api'
import { useT } from '../lib/i18n'

const BOOKS = [
  { key: 'house_3pct', label: '≥ 3%' },
  { key: 'house_5pct', label: '≥ 5%' },
  { key: 'house_7pct', label: '≥ 7%' },
]

export default function PaperTrading() {
  const t = useT()
  const [book, setBook] = useState('house_5pct')

  const { data, isLoading } = useQuery({
    queryKey: ['paper-house', book],
    queryFn: () => api.paperTrading.house({ book_type: book, start_bankroll: 1000 }),
    staleTime: 30_000,
  })

  return (
    <>
      <div className="ph">
        <div>
          <div className="ph-title">{t('paper.title')}</div>
          <div className="ph-sub">{t('paper.subtitle')}</div>
        </div>
      </div>

      <div className="filters">
        <div className="filter-grp">
          <span className="filter-lbl">{t('paper.band_label')}</span>
          {BOOKS.map(b => (
            <button
              key={b.key}
              className={`chip${book === b.key ? ' active' : ''}`}
              onClick={() => setBook(b.key)}
            >
              {b.label}
            </button>
          ))}
        </div>
      </div>

      <div className="page">
        <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-mute)',
                       padding: '8px 12px', background: 'var(--bg-mute)',
                       borderRadius: 6, marginBottom: 12 }}>
          {t('paper.disclaimer')}
        </div>
        {isLoading && <div className="empty">{t('paper.loading')}</div>}
        {data && <HouseCard d={data} t={t} />}
      </div>
    </>
  )
}

function HouseCard({ d, t }: { d: PaperHouseSummary; t: (k: string, v?: any) => string }) {
  const fmtUnit = (x: number) => `${x.toFixed(2)} unit`
  const fmtPct  = (x: number | null) => (x == null ? '—' : `${x.toFixed(1)}%`)
  const roi = d.metrics.roi_pct
  const roiColor =
    roi == null ? 'var(--text)' : (roi >= 0 ? 'var(--acc)' : 'var(--neg)')

  return (
    <>
      <div className="card" style={{ padding: 16 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
          <Metric label={t('paper.metric.bankroll')}
                  value={fmtUnit(d.bankroll.current)}
                  sub={`start ${fmtUnit(d.bankroll.start)}`} />
          <Metric label={t('paper.metric.roi')}
                  value={fmtPct(roi)}
                  sub={t('paper.metric.roi_sub')}
                  color={roiColor} />
          <Metric label={t('paper.metric.win_rate')}
                  value={fmtPct(d.metrics.win_rate == null ? null : d.metrics.win_rate * 100)} />
          <Metric label={t('paper.metric.bets')}
                  value={`${d.bets_settled} / ${d.bets_settled + d.bets_pending}`}
                  sub={
                    d.bets_voided > 0
                      ? t('paper.metric.bets_sub_with_void', { pending: d.bets_pending, voided: d.bets_voided })
                      : t('paper.metric.bets_sub', { pending: d.bets_pending })
                  } />
        </div>
      </div>

      {d.timeseries.length === 0 ? (
        <div className="card" style={{ padding: 16, marginTop: 16 }}>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>
            {t('paper.curve.title')}
          </div>
          <div className="empty" style={{ padding: 0 }}>
            {d.bets_pending > 0
              ? t('paper.curve.pending', { pending: d.bets_pending })
              : t('paper.curve.empty')}
          </div>
        </div>
      ) : (
        <BankrollCurve series={d.timeseries} start={d.bankroll.start} t={t} />
      )}
    </>
  )
}

function Metric({ label, value, sub, color }:
  { label: string; value: string; sub?: string; color?: string }) {
  return (
    <div>
      <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-mute)' }}>{label}</div>
      <div style={{ fontSize: 'var(--fs-xl)', fontWeight: 700, marginTop: 2, color: color ?? undefined }}>
        {value}
      </div>
      {sub && <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-mute)', marginTop: 2 }}>{sub}</div>}
    </div>
  )
}

function BankrollCurve({ series, start, t }:
  { series: { settled_at: string; bankroll: number }[]; start: number; t: (k: string, v?: any) => string }) {
  // 640×180 SVG with 32/16 L/R, 16/28 T/B margins. Y axis spans
  // [min, max] of (start ∪ bankroll points) with 8% headroom.
  const W = 640, H = 180, ML = 32, MR = 16, MT = 16, MB = 28
  const xs = series.map((_, i) => i)
  const ys = [start, ...series.map(p => p.bankroll)]
  const yMin = Math.min(...ys), yMax = Math.max(...ys)
  const pad = (yMax - yMin) * 0.08 || 1
  const yLo = yMin - pad, yHi = yMax + pad
  const toX = (i: number) => ML + (xs.length <= 1 ? 0 : (i / (xs.length - 1)) * (W - ML - MR))
  const toY = (y: number) => MT + (1 - (y - yLo) / (yHi - yLo)) * (H - MT - MB)
  const startY = toY(start)
  const path = series.map((p, i) => `${i === 0 ? 'M' : 'L'} ${toX(i)} ${toY(p.bankroll)}`).join(' ')

  return (
    <div className="card" style={{ padding: 16, marginTop: 16 }}>
      <div style={{ fontWeight: 600, marginBottom: 4 }}>{t('paper.curve.title')}</div>
      <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-mute)', marginBottom: 8 }}>
        {t('paper.curve.hint')}
      </div>
      <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ background: 'var(--bg-mute)', borderRadius: 6 }}>
        <line x1={ML} y1={startY} x2={W - MR} y2={startY}
              stroke="var(--text-mute)" strokeDasharray="4 4" strokeWidth={1} />
        <text x={ML + 4} y={startY - 4} fontSize={10} fill="var(--text-mute)">
          {start.toFixed(0)} unit (start)
        </text>
        <path d={path} fill="none" stroke="var(--acc)" strokeWidth={2} />
        <text x={ML} y={H - 6} fontSize={10} fill="var(--text-mute)">
          {series.length > 0 ? series[0].settled_at.slice(0, 10) : ''}
        </text>
        <text x={W - MR} y={H - 6} fontSize={10} fill="var(--text-mute)" textAnchor="end">
          {series.length > 0 ? series[series.length - 1].settled_at.slice(0, 10) : ''}
        </text>
      </svg>
    </div>
  )
}

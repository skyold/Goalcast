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
import { api, type Book, type PaperHouseSummary } from '../lib/api'
import { useT } from '../lib/i18n'
import MultiBookRoiChart from '../components/signals/MultiBookRoiChart'

const BANDS = [
  { key: 'house_3pct', label: '≥ 3%' },
  { key: 'house_5pct', label: '≥ 5%' },
  { key: 'house_7pct', label: '≥ 7%' },
]

type View = 'books' | 'bands'

export default function PaperTrading() {
  const t = useT()
  const [view, setView] = useState<View>('books')

  return (
    <>
      <div className="ph">
        <div>
          <div className="ph-title">{t('paper.title')}</div>
          <div className="ph-sub">{t('paper.subtitle')}</div>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          <button className={`chip${view === 'books' ? ' active' : ''}`}
                  onClick={() => setView('books')}>{t('paper.view.books')}</button>
          <button className={`chip${view === 'bands' ? ' active' : ''}`}
                  onClick={() => setView('bands')}>{t('paper.view.bands')}</button>
        </div>
      </div>

      <div className="page">
        <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-mute)',
                       padding: '8px 12px', background: 'var(--bg-mute)',
                       borderRadius: 6, marginBottom: 12 }}>
          {t('paper.disclaimer')}
        </div>
        {view === 'books' ? <BooksView t={t} /> : <BandsView t={t} />}
      </div>
    </>
  )
}

function BooksView({ t }: { t: (k: string, v?: any) => string }) {
  const { data, isLoading } = useQuery({
    queryKey: ['paper.books'],
    queryFn: () => api.paperTrading.books(),
    staleTime: 30_000,
  })
  if (isLoading) return <div className="empty">{t('paper.loading')}</div>
  const books = data?.items ?? []
  if (books.length === 0) {
    return <div className="empty">{t('paper.books.no_books')}</div>
  }
  return (
    <>
      <MultiBookRoiChart books={books} />
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
                     gap: 12, marginTop: 16 }}>
        {books.map(b => <BookCard key={b.id} book={b} t={t} />)}
      </div>
    </>
  )
}

function BookCard({ book, t }: { book: Book; t: (k: string, v?: any) => string }) {
  const s = book.summary
  const roi = s.metrics.roi_pct
  const roiColor = roi == null ? 'var(--text)' : (roi >= 0 ? 'var(--acc)' : 'var(--neg)')
  return (
    <div className="card" style={{ padding: 12 }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, marginBottom: 4 }}>
        <span style={{ fontWeight: 600 }}>{book.name.replace(/^House-GS-/, '')}</span>
        <span style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-mute)' }}>
          {book.signal_version}
        </span>
        <span style={{ marginLeft: 'auto', padding: '0 6px',
                        fontSize: 'var(--fs-xs)',
                        border: '1px solid var(--text-mute)', borderRadius: 999,
                        color: 'var(--text-mute)' }}>
          {book.scope === 'house' ? t('paper.books.scope.house') : t('paper.books.scope.personal')}
        </span>
      </div>
      <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-mute)', marginBottom: 8 }}>
        {book.signal_type.replace(/^GS-/, '')} · {t(`paper.books.match.${book.match_scope}`)}
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 8 }}>
        <Metric label="ROI"
                value={roi == null ? '—' : `${roi.toFixed(1)}%`}
                color={roiColor} />
        <Metric label={t('paper.metric.win_rate')}
                value={s.metrics.win_rate == null ? '—' : `${Math.round(s.metrics.win_rate * 100)}%`} />
        <Metric label={t('paper.metric.bankroll')}
                value={`${s.bankroll.current.toFixed(1)}u`}
                sub={`start ${s.bankroll.start.toFixed(0)}u`} />
        <Metric label={t('paper.metric.bets')}
                value={`${s.bets_settled}`}
                sub={s.bets_pending > 0 ? `+ ${s.bets_pending} pending` : ''} />
      </div>
    </div>
  )
}

function BandsView({ t }: { t: (k: string, v?: any) => string }) {
  const [book, setBook] = useState('house_5pct')
  const { data, isLoading } = useQuery({
    queryKey: ['paper-house', book],
    queryFn: () => api.paperTrading.house({ book_type: book, start_bankroll: 1000 }),
    staleTime: 30_000,
  })
  return (
    <>
      <div className="filters" style={{ marginBottom: 12 }}>
        <div className="filter-grp">
          <span className="filter-lbl">{t('paper.band_label')}</span>
          {BANDS.map(b => (
            <button key={b.key}
              className={`chip${book === b.key ? ' active' : ''}`}
              onClick={() => setBook(b.key)}
            >{b.label}</button>
          ))}
        </div>
      </div>
      {isLoading && <div className="empty">{t('paper.loading')}</div>}
      {data && <HouseCard d={data} t={t} />}
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

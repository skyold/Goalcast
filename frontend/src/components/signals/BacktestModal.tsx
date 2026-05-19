// Backtest modal — Phase 3 of signal-catalog-and-subscriptions PRD.
//
// Composes: window selector + match_scope selector + strength_min slider
//           → "Run" button → results panel (ROI / hit rate / drawdown
//             + equity curve SVG sparkline).
//
// Conditions surface intentionally minimal in V1.5 — only `strength_min` is
// exposed; advanced filters live in conditions_json shape but aren't
// editable here (would need a JSON-editor UI). Phase 4 BookEditor will
// reuse this modal and persist the chosen conditions to a Personal Book.
import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { api, type SignalBacktestRequest, type SignalBacktestResult } from '../../lib/api'
import { useT } from '../../lib/i18n'

type Window = '7d' | '14d' | '30d'
type MatchScope = 'all' | 'my_leagues'

const WINDOWS: Window[] = ['7d', '14d', '30d']

export default function BacktestModal({
  signal_type, onClose,
}: {
  signal_type: string
  onClose: () => void
}) {
  const t = useT()
  const [window_, setWindow] = useState<Window>('30d')
  const [scope, setScope] = useState<MatchScope>('all')
  const [strengthMin, setStrengthMin] = useState<number>(0.5)

  const mut = useMutation({
    mutationFn: () => {
      const body: SignalBacktestRequest = {
        window: window_,
        match_scope: scope,
        conditions: strengthMin > 0 ? { strength_min: strengthMin } : {},
      }
      return api.signals.backtest(signal_type, body)
    },
  })

  const r = mut.data

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.55)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100,
      }}
    >
      <div
        className="card"
        onClick={(e) => e.stopPropagation()}
        style={{
          width: 'min(720px, calc(100% - 32px))',
          maxHeight: 'calc(100% - 64px)',
          overflow: 'auto', padding: 20,
        }}
      >
        <header style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 16 }}>
          <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700 }}>
            {t('signals.backtest.title')}
          </h3>
          <span style={{ color: 'var(--text-mute)', fontSize: 13 }}>
            {signal_type.replace(/^GS-/, '')}
          </span>
          <button onClick={onClose} className="chip" style={{ marginLeft: 'auto' }}>×</button>
        </header>

        {/* Controls */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, marginBottom: 16 }}>
          <div>
            <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-mute)', marginBottom: 4 }}>
              {t('signals.backtest.window')}
            </div>
            <div style={{ display: 'flex', gap: 6 }}>
              {WINDOWS.map(w => (
                <button key={w}
                  className={`chip${window_ === w ? ' active' : ''}`}
                  onClick={() => setWindow(w)}
                >{w}</button>
              ))}
            </div>
          </div>
          <div>
            <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-mute)', marginBottom: 4 }}>
              {t('signals.backtest.scope')}
            </div>
            <div style={{ display: 'flex', gap: 6 }}>
              <button
                className={`chip${scope === 'all' ? ' active' : ''}`}
                onClick={() => setScope('all')}
              >{t('signals.backtest.scope.all')}</button>
              <button
                className={`chip${scope === 'my_leagues' ? ' active' : ''}`}
                onClick={() => setScope('my_leagues')}
              >{t('signals.backtest.scope.my_leagues')}</button>
            </div>
          </div>
          <div style={{ flex: 1, minWidth: 200 }}>
            <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-mute)', marginBottom: 4 }}>
              {t('signals.backtest.strength_min')}: {strengthMin.toFixed(2)}
            </div>
            <input
              type="range"
              min={0} max={1} step={0.05}
              value={strengthMin}
              onChange={(e) => setStrengthMin(parseFloat(e.target.value))}
              style={{ width: '100%' }}
            />
          </div>
        </div>

        <button
          onClick={() => mut.mutate()}
          disabled={mut.isPending}
          className="chip active"
          style={{ marginBottom: 16 }}
        >
          {mut.isPending ? t('signals.backtest.running') : t('signals.backtest.run')}
        </button>

        {mut.isError && (
          <div className="empty" style={{ color: 'var(--neg)' }}>
            {String((mut.error as Error)?.message ?? mut.error)}
          </div>
        )}

        {r && <BacktestResultView result={r} />}
      </div>
    </div>
  )
}

function BacktestResultView({ result }: { result: SignalBacktestResult }) {
  const t = useT()
  const fmt = (v: number | null, suffix = '%') =>
    v == null ? '—' : `${v.toFixed(v >= 100 ? 0 : 2)}${suffix}`
  return (
    <>
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)',
        gap: 12, marginBottom: 16,
      }}>
        <Metric label={t('signals.backtest.settled')} value={String(result.settled_count)}
                hint={`${t('signals.backtest.considered')} ${result.considered_count}`} />
        <Metric label="ROI"        value={fmt(result.roi_pct)}
                color={(result.roi_pct ?? 0) >= 0 ? 'var(--acc)' : 'var(--neg)'} />
        <Metric label={t('signals.backtest.hit_rate')}
                value={result.hit_rate == null ? '—' : `${Math.round(result.hit_rate * 100)}%`} />
        <Metric label={t('signals.backtest.max_drawdown')}
                value={fmt(result.max_drawdown_pct)}
                color="var(--neg)" />
      </div>
      <EquityCurve points={result.equity_curve} />
    </>
  )
}

function Metric({ label, value, hint, color }: {
  label: string; value: string; hint?: string; color?: string
}) {
  return (
    <div className="card" style={{ padding: 12 }}>
      <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-mute)' }}>{label}</div>
      <div className="num" style={{ fontSize: 22, fontWeight: 700, color }}>{value}</div>
      {hint && <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-mute)' }}>{hint}</div>}
    </div>
  )
}

function EquityCurve({ points }: { points: SignalBacktestResult['equity_curve'] }) {
  const t = useT()
  if (points.length === 0) {
    return <div className="empty">{t('signals.backtest.no_curve')}</div>
  }
  const W = 640, H = 160, P = 16
  const xs = points.map((_, i) => P + (i / Math.max(1, points.length - 1)) * (W - P * 2))
  const ys_raw = points.map(p => p.cum_pnl)
  const yMin = Math.min(0, ...ys_raw)
  const yMax = Math.max(0, ...ys_raw)
  const yRange = yMax - yMin || 1
  const yAt = (v: number) => H - P - ((v - yMin) / yRange) * (H - P * 2)
  const ys = ys_raw.map(yAt)
  const zeroY = yAt(0)
  const path = xs.map((x, i) => `${i === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${ys[i].toFixed(1)}`).join(' ')
  const finalPnl = ys_raw[ys_raw.length - 1]
  const color = finalPnl >= 0 ? 'var(--acc)' : 'var(--neg)'
  return (
    <div className="card" style={{ padding: 12 }}>
      <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-mute)', marginBottom: 4 }}>
        {t('signals.backtest.equity_curve')}
      </div>
      <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ display: 'block' }}>
        {/* Zero baseline */}
        <line x1={P} y1={zeroY} x2={W - P} y2={zeroY}
              stroke="var(--text-mute)" strokeDasharray="3 3" strokeWidth={1} />
        <path d={path} fill="none" stroke={color} strokeWidth={1.8} />
        {/* End label */}
        <text x={W - P} y={ys[ys.length - 1] - 6}
              textAnchor="end" fontSize="11" fill={color}>
          {finalPnl >= 0 ? '+' : ''}{finalPnl.toFixed(2)} u
        </text>
      </svg>
      <div style={{
        display: 'flex', justifyContent: 'space-between',
        fontSize: 'var(--fs-xs)', color: 'var(--text-mute)',
      }}>
        <span>{points[0].date}</span>
        <span>{points[points.length - 1].date}</span>
      </div>
    </div>
  )
}

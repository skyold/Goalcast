// Multi-Book ROI chart — Phase 4b of signal-catalog-and-subscriptions PRD.
//
// Each Book becomes one polyline. X axis = time (settled_at), Y axis =
// bankroll (units). Books are color-coded; empty books are skipped.
//
// Design rationale: "信号即账户 + 统一 starting_units" makes ROI lines
// comparable across signals. This is the artifact users open to answer
// "which signal is actually making money?".
import { useMemo } from 'react'
import { type Book } from '../../lib/api'
import { useT } from '../../lib/i18n'

// Distinct color palette — keep deterministic so the same Book has the same
// color across re-renders. Falls back to grayscale beyond 10 books.
const PALETTE = [
  '#2dd4bf', '#60a5fa', '#f472b6', '#facc15',
  '#a78bfa', '#fb923c', '#34d399', '#f87171',
  '#22d3ee', '#e879f9',
]

export default function MultiBookRoiChart({ books }: { books: Book[] }) {
  const t = useT()
  const W = 720, H = 280, PAD = { top: 16, right: 80, bottom: 28, left: 40 }

  const series = useMemo(() => {
    return books
      .filter(b => b.summary.timeseries.length > 0)
      .map((b, i) => {
        const points = b.summary.timeseries.map(p => ({
          t: Date.parse(p.settled_at),
          v: p.bankroll,
        }))
        // Prepend the starting bankroll point so curves visually start at the baseline.
        if (points.length > 0) {
          points.unshift({ t: points[0].t - 1, v: b.starting_units })
        }
        return {
          book: b,
          color: PALETTE[i % PALETTE.length],
          points,
        }
      })
  }, [books])

  const empty = series.length === 0

  const { tMin, tMax, vMin, vMax } = useMemo(() => {
    if (empty) {
      return { tMin: 0, tMax: 1, vMin: 0, vMax: 1 }
    }
    let tMin = Infinity, tMax = -Infinity, vMin = Infinity, vMax = -Infinity
    for (const s of series) {
      for (const p of s.points) {
        if (p.t < tMin) tMin = p.t
        if (p.t > tMax) tMax = p.t
        if (p.v < vMin) vMin = p.v
        if (p.v > vMax) vMax = p.v
      }
    }
    // Include the starting_units baseline so the dashed reference line is visible.
    const baseline = books.length > 0 ? books[0].starting_units : 100
    vMin = Math.min(vMin, baseline)
    vMax = Math.max(vMax, baseline)
    // Pad y range 5% top/bottom so points don't sit on the frame.
    const span = vMax - vMin || 1
    vMin -= span * 0.05
    vMax += span * 0.05
    return { tMin, tMax, vMin, vMax }
  }, [series, empty, books])

  if (empty) {
    return <div className="empty">{t('paper.books.no_curves')}</div>
  }

  const innerW = W - PAD.left - PAD.right
  const innerH = H - PAD.top - PAD.bottom
  const xAt = (t: number) => PAD.left + ((t - tMin) / (tMax - tMin || 1)) * innerW
  const yAt = (v: number) => PAD.top + (1 - (v - vMin) / (vMax - vMin || 1)) * innerH
  const baseline = books[0].starting_units
  const baselineY = yAt(baseline)

  return (
    <div className="card" style={{ padding: 12 }}>
      <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ display: 'block' }}>
        {/* Starting bankroll baseline */}
        <line x1={PAD.left} y1={baselineY} x2={W - PAD.right} y2={baselineY}
              stroke="var(--text-mute)" strokeDasharray="3 3" strokeWidth={1} />
        <text x={PAD.left - 4} y={baselineY + 3} textAnchor="end"
              fontSize="10" fill="var(--text-mute)">{baseline.toFixed(0)}u</text>

        {/* Polylines */}
        {series.map(s => {
          const path = s.points.map((p, i) =>
            `${i === 0 ? 'M' : 'L'} ${xAt(p.t).toFixed(1)} ${yAt(p.v).toFixed(1)}`
          ).join(' ')
          const last = s.points[s.points.length - 1]
          return (
            <g key={s.book.id}>
              <path d={path} fill="none" stroke={s.color} strokeWidth={1.8} />
              {/* End label: book name (short) */}
              <text x={xAt(last.t) + 4} y={yAt(last.v) + 3}
                    fontSize="10" fill={s.color}>
                {s.book.name.replace(/^House-GS-/, '')}
              </text>
            </g>
          )
        })}

        {/* x-axis label range */}
        <text x={PAD.left} y={H - 6} fontSize="10" fill="var(--text-mute)">
          {new Date(tMin).toISOString().slice(0, 10)}
        </text>
        <text x={W - PAD.right} y={H - 6} fontSize="10" fill="var(--text-mute)"
              textAnchor="end">
          {new Date(tMax).toISOString().slice(0, 10)}
        </text>
      </svg>
    </div>
  )
}

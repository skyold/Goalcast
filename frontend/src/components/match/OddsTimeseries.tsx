// Single-axis drop_pct timeseries chart. Inline SVG, no third-party chart lib.
//
// odds_snapshots upstream only populates drop_pct (odds_home/draw/away are 100%
// NULL in observed data), so we plot a single signal: drop% over time. Default
// filter narrows to Pinnacle / ft_result (sharp 1x2 movement).
//
// Visual contract:
// - X axis: time (left = earlier, right = now)
// - Y axis: drop_pct, 0 at top → -100 at bottom. More-negative = bigger drop.
// - Filled area below the line for visual weight.
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../lib/api'
import { useT } from '../../lib/i18n'

interface Props {
  fixtureId: number
}

const W = 480
const H = 140
const PAD_L = 32
const PAD_R = 12
const PAD_T = 12
const PAD_B = 22

export function OddsTimeseries({ fixtureId }: Props) {
  const t = useT()
  const [window, setWindow] = useState<'24h' | '7d'>('24h')
  const { data, isLoading } = useQuery({
    queryKey: ['odds-timeseries', fixtureId, window],
    queryFn: () => api.oddsTimeseries(fixtureId, { window }),
    staleTime: 60_000,
  })

  const points = data?.points ?? []
  const hasData = points.length >= 2

  // Y domain: from 0 (top) to min observed (bottom), clamped to [-100, 0]
  const minY = hasData ? Math.min(...points.map(p => p.drop_pct), 0) : -100
  const yMin = Math.max(minY, -100)
  const xs = points.map(p => new Date(p.recorded_at).getTime())
  const xMin = hasData ? Math.min(...xs) : 0
  const xMax = hasData ? Math.max(...xs) : 1
  const xSpan = Math.max(xMax - xMin, 1)

  const px = (tt: number) => PAD_L + ((tt - xMin) / xSpan) * (W - PAD_L - PAD_R)
  const py = (v: number) => PAD_T + ((0 - v) / (0 - yMin)) * (H - PAD_T - PAD_B)

  const linePts = points.map(p => `${px(new Date(p.recorded_at).getTime())},${py(p.drop_pct)}`).join(' ')
  const areaPts = hasData
    ? `${PAD_L},${py(0)} ${linePts} ${px(xMax)},${py(0)}`
    : ''

  // Y axis tick labels — show 0, 25%, 50%, 75%, and the minimum
  const ticks = [0, -25, -50, -75, Math.round(yMin)]
    .filter((v, i, arr) => arr.indexOf(v) === i)
    .filter(v => v >= yMin - 1)

  return (
    <div className="card">
      <div className="card-hdr">
        <div className="card-title">{t('insights.timeseries.title')}</div>
        <div style={{ display: 'flex', gap: 6 }}>
          <button
            className={`chip${window === '24h' ? ' active' : ''}`}
            onClick={() => setWindow('24h')}
          >{t('insights.timeseries.window.24h')}</button>
          <button
            className={`chip${window === '7d' ? ' active' : ''}`}
            onClick={() => setWindow('7d')}
          >{t('insights.timeseries.window.7d')}</button>
        </div>
      </div>

      {isLoading ? (
        <div className="empty">{t('matches.empty.loading')}</div>
      ) : !hasData ? (
        <div className="empty">{t('insights.timeseries.empty', { window })}</div>
      ) : (
        <>
          <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" style={{ width: '100%', height: H }}>
            {/* gridlines */}
            {ticks.map(v => (
              <line key={v}
                x1={PAD_L} x2={W - PAD_R} y1={py(v)} y2={py(v)}
                stroke="var(--border)" strokeDasharray="2 3" strokeWidth="0.5"
              />
            ))}
            {/* filled area */}
            <polygon points={areaPts} fill="var(--acc)" opacity="0.15" />
            {/* line */}
            <polyline
              points={linePts}
              fill="none" stroke="var(--acc)" strokeWidth="1.5"
              vectorEffect="non-scaling-stroke"
            />
            {/* axis labels (Y) */}
            {ticks.map(v => (
              <text key={`yl-${v}`}
                x={PAD_L - 6} y={py(v) + 3}
                fill="var(--text-mute)" fontSize="9" textAnchor="end"
              >{v}%</text>
            ))}
            {/* axis labels (X) — first / last */}
            <text x={PAD_L} y={H - 6} fill="var(--text-mute)" fontSize="9" textAnchor="start">
              {fmtAxisTime(new Date(xMin))}
            </text>
            <text x={W - PAD_R} y={H - 6} fill="var(--text-mute)" fontSize="9" textAnchor="end">
              {fmtAxisTime(new Date(xMax))}
            </text>
          </svg>
          <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-mute)', marginTop: 4 }}>
            {points.length} pts · {t('insights.timeseries.source')}
          </div>
        </>
      )}
    </div>
  )
}

function fmtAxisTime(d: Date): string {
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  const hh = String(d.getHours()).padStart(2, '0')
  const mi = String(d.getMinutes()).padStart(2, '0')
  return `${mm}/${dd} ${hh}:${mi}`
}

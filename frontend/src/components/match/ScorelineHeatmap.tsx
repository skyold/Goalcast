import { useMemo } from 'react'
import { ahProbabilities } from '../../lib/ahMath'

type Props = {
  scorelines: Record<string, number>
  ahLine: number
  size?: number
}

const MAX_GOALS = 6

function cellColor(pct: number, max: number): string {
  const r = max ? Math.min(1, pct / max) : 0
  const v = Math.round(255 - r * 180)
  return `rgb(${v}, ${v}, ${v})`
}

function cellOverlay(h: number, a: number, line: number): 'win' | 'push' | 'lose' {
  const margin = h - a
  const eff = margin + line
  const nearestInt = Math.round(eff)
  if (Math.abs(eff - nearestInt) < 1e-9) {
    if (nearestInt > 0) return 'win'
    if (nearestInt === 0) return 'push'
    return 'lose'
  }
  return eff > 0 ? 'win' : 'lose'
}

export function ScorelineHeatmap({ scorelines, ahLine, size = 36 }: Props) {
  const cells = useMemo(() => {
    const m: number[][] = Array.from({ length: MAX_GOALS + 1 }, () => Array(MAX_GOALS + 1).fill(0))
    for (const [k, p] of Object.entries(scorelines)) {
      const [hs, as] = k.split('-').map(s => parseInt(s, 10))
      if (isNaN(hs) || isNaN(as)) continue
      const h = Math.min(hs, MAX_GOALS), a = Math.min(as, MAX_GOALS)
      m[a][h] += p
    }
    return m
  }, [scorelines])

  const max = useMemo(() => Math.max(...cells.flat()), [cells])
  const probs = useMemo(() => ahProbabilities(scorelines, ahLine), [scorelines, ahLine])

  return (
    <div className="hm-wrap">
      <table className="hm" style={{ ['--cell' as string]: `${size}px` } as React.CSSProperties}>
        <thead>
          <tr>
            <th></th>
            {Array.from({ length: MAX_GOALS + 1 }, (_, h) => (
              <th key={h}>{h === MAX_GOALS ? `${h}+` : h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {cells.map((row, a) => (
            <tr key={a}>
              <th>{a === MAX_GOALS ? `${a}+` : a}</th>
              {row.map((p, h) => {
                const o = cellOverlay(h, a, ahLine)
                return (
                  <td key={h}
                      className={`hm-cell hm-${o}`}
                      style={{ background: cellColor(p, max) }}
                      title={`${h}-${a} = ${p.toFixed(2)}%`}>
                    {p >= 0.5 ? p.toFixed(0) : ''}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <div className="hm-summary">
        <div className="hm-stat hm-win">赢: {probs.win.toFixed(1)}%</div>
        <div className="hm-stat hm-push">和: {probs.push.toFixed(1)}%</div>
        <div className="hm-stat hm-lose">输: {probs.lose.toFixed(1)}%</div>
      </div>
    </div>
  )
}

export function ahProbabilities(
  scorelines: Record<string, number>,
  line: number,
  side: 'home' | 'away' = 'home',
): { win: number; push: number; lose: number } {
  let win = 0, push = 0, lose = 0
  for (const [k, pct] of Object.entries(scorelines)) {
    const [hStr, aStr] = k.split('-')
    const h = parseInt(hStr, 10), a = parseInt(aStr, 10)
    if (isNaN(h) || isNaN(a)) continue
    const margin = side === 'home' ? (h - a) : (a - h)
    const effective = margin + line
    const nearestInt = Math.round(effective)
    if (Math.abs(effective - nearestInt) < 1e-9) {
      if (nearestInt > 0) win += pct
      else if (nearestInt === 0) push += pct
      else lose += pct
    } else {
      if (effective >= 0.5) win += pct
      else if (effective <= -0.5) lose += pct
      else if (effective > 0) { win += pct * 0.5; push += pct * 0.5 }
      else                     { lose += pct * 0.5; push += pct * 0.5 }
    }
  }
  return { win, push, lose }
}

export const AH_LINES_DEFAULT = [-1.25, -1, -0.75, -0.5, -0.25, 0, 0.25, 0.5, 0.75, 1, 1.25]

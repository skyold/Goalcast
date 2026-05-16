type OddsValues = { home: number | null; draw?: number | null; away: number | null }

type Props = {
  label?: string
  pinnacle: OddsValues | null
  bet365: OddsValues | null
  showDraw?: boolean
}

const fmt = (n: number | null | undefined) => (n == null ? '—' : n.toFixed(2))

function highlight(a: number | null, b: number | null): [string, string] {
  if (a == null || b == null || !a || !b) return ['', '']
  const diff = (a - b) / Math.min(a, b)
  if (Math.abs(diff) < 0.05) return ['', '']
  return diff > 0 ? ['odds-better', 'odds-worse'] : ['odds-worse', 'odds-better']
}

export function OddsPair({ label, pinnacle, bet365, showDraw = true }: Props) {
  const [hP, hB] = highlight(pinnacle?.home ?? null, bet365?.home ?? null)
  const [aP, aB] = highlight(pinnacle?.away ?? null, bet365?.away ?? null)
  return (
    <div className="odds-pair">
      {label && <div className="odds-label">{label}</div>}
      <div className="odds-row">
        <div className="odds-book">Pinnacle</div>
        <span className={`odds-cell ${hP}`}>{fmt(pinnacle?.home)}</span>
        {showDraw && <span className="odds-cell">{fmt(pinnacle?.draw)}</span>}
        <span className={`odds-cell ${aP}`}>{fmt(pinnacle?.away)}</span>
      </div>
      <div className="odds-row">
        <div className="odds-book">Bet365</div>
        <span className={`odds-cell ${hB}`}>{fmt(bet365?.home)}</span>
        {showDraw && <span className="odds-cell">{fmt(bet365?.draw)}</span>}
        <span className={`odds-cell ${aB}`}>{fmt(bet365?.away)}</span>
      </div>
    </div>
  )
}

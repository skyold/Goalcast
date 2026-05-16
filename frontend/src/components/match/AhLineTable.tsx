import type { AsianHandicapLine } from '../../lib/api'

const fmt = (n: number | null | undefined) => (n == null ? '—' : n.toFixed(2))

export function AhLineTable({ lines }: { lines: AsianHandicapLine[] }) {
  if (lines.length === 0) return <div className="aht-empty">— 无亚盘 —</div>
  return (
    <table className="aht">
      <thead>
        <tr>
          <th>档</th>
          <th colSpan={2}>Pinnacle</th>
          <th colSpan={2}>Bet365</th>
        </tr>
        <tr>
          <th></th>
          <th>主</th><th>客</th>
          <th>主</th><th>客</th>
        </tr>
      </thead>
      <tbody>
        {lines.map(l => (
          <tr key={l.line}>
            <td className="aht-line">{l.line > 0 ? '+' : ''}{l.line}</td>
            <td>{fmt(l.pinnacle?.home)}</td>
            <td>{fmt(l.pinnacle?.away)}</td>
            <td>{fmt(l.bet365?.home)}</td>
            <td>{fmt(l.bet365?.away)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

import type { AsianHandicapLine } from '../../lib/api'
import { useT } from '../../lib/i18n'

const fmt = (n: number | null | undefined) => (n == null ? '—' : n.toFixed(2))

export function AhLineTable({ lines }: { lines: AsianHandicapLine[] }) {
  const t = useT()
  if (lines.length === 0) return <div className="aht-empty">{t('ah.empty')}</div>
  return (
    <table className="aht">
      <thead>
        <tr>
          <th>{t('ah.col_line')}</th>
          <th colSpan={2}>Pinnacle</th>
          <th colSpan={2}>Bet365</th>
        </tr>
        <tr>
          <th></th>
          <th>{t('ah.col_home')}</th><th>{t('ah.col_away')}</th>
          <th>{t('ah.col_home')}</th><th>{t('ah.col_away')}</th>
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

import { AH_LINES_DEFAULT } from '../../lib/ahMath'

type Props = {
  value: number
  options?: number[]
  onChange: (v: number) => void
}

export function AhLineSelector({ value, options = AH_LINES_DEFAULT, onChange }: Props) {
  return (
    <select className="ah-line-select" value={value}
            onChange={e => onChange(parseFloat(e.target.value))}>
      {options.map(o => (
        <option key={o} value={o}>{`AH ${o > 0 ? '+' : ''}${o}`}</option>
      ))}
    </select>
  )
}

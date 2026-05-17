// Single labelled progress bar used on Match Detail.
import { InfoIcon } from '../shared/InfoIcon'
import type { GlossaryKey } from '../../lib/glossary'

type Kind = 'h' | 'd' | 'a' | 'o'

interface Props { label: string; value: number; kind?: Kind; suffix?: string; infoKey?: GlossaryKey }

export function BigBar({ label, value, kind = 'h', suffix = '%', infoKey }: Props) {
  return (
    <div className="bigbar">
      <span className="bigbar-lbl">
        {label}
        {infoKey && <InfoIcon k={infoKey} />}
      </span>
      <div className="bigbar-track">
        <div
          className={`bigbar-fill ${kind}`}
          style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
        />
      </div>
      <span className="bigbar-val">{value.toFixed(1)}{suffix}</span>
    </div>
  )
}

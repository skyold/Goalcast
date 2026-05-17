import { Tooltip } from './Tooltip'
import { gloss, type GlossaryKey } from '../../lib/glossary'

interface Props {
  k: GlossaryKey
  side?: 'top' | 'right' | 'bottom' | 'left'
}

// 14px circular "i" icon. Hover/focus opens the Tooltip with copy from glossary.
export function InfoIcon({ k, side = 'top' }: Props) {
  return (
    <Tooltip content={gloss(k)} side={side}>
      <button type="button" className="gc-info" aria-label="i">
        <svg viewBox="0 0 14 14" width={14} height={14} aria-hidden="true">
          <circle cx="7" cy="7" r="6.25" fill="none" stroke="currentColor" strokeWidth="1" />
          <rect x="6.35" y="5.6" width="1.3" height="4.2" fill="currentColor" />
          <rect x="6.35" y="3.5" width="1.3" height="1.3" fill="currentColor" />
        </svg>
      </button>
    </Tooltip>
  )
}

export default InfoIcon

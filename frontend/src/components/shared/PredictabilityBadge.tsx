import type { Predictability } from '../../lib/api'
import { Tooltip } from './Tooltip'
import { gloss, type GlossaryKey } from '../../lib/glossary'

const LABELS: Record<NonNullable<Predictability>, string> = {
  high: '高', good: '良', medium: '中', poor: '差',
}

export function PredictabilityBadge({ level }: { level: Predictability }) {
  if (!level) return null
  const key = `mc.predictability.${level}` as GlossaryKey
  return (
    <Tooltip content={gloss(key)}>
      <span className={`pb pb-${level}`} tabIndex={0}>
        {LABELS[level]}
      </span>
    </Tooltip>
  )
}

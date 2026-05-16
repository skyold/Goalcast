import type { Predictability } from '../../lib/api'

const LABELS: Record<NonNullable<Predictability>, string> = {
  high: '高', good: '良', medium: '中', poor: '差',
}

export function PredictabilityBadge({ level }: { level: Predictability }) {
  if (!level) return null
  return (
    <span className={`pb pb-${level}`} title={`predictability: ${level}`}>
      {LABELS[level]}
    </span>
  )
}

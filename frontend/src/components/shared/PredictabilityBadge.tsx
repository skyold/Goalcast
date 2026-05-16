import type { Predictability } from '../../lib/api'

const LABELS: Record<NonNullable<Predictability>, string> = {
  high: '高可预测', good: '良好', medium: '一般', poor: '低可信'
}

export function PredictabilityBadge({ level }: { level: Predictability }) {
  if (!level) return null
  return (
    <span className={`pb pb-${level}`} title={`predictability: ${level}`}>
      {LABELS[level]}
    </span>
  )
}

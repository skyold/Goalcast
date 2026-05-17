import type { Predictability } from '../../lib/api'
import { Tooltip } from './Tooltip'
import { gloss, type GlossaryKey } from '../../lib/glossary'
import { useT } from '../../lib/i18n'

export function PredictabilityBadge({ level }: { level: Predictability }) {
  const t = useT()
  if (!level) return null
  const key = `mc.predictability.${level}` as GlossaryKey
  return (
    <Tooltip content={gloss(key)}>
      <span className={`pb pb-${level}`} tabIndex={0}>
        {t(`predictability.${level}`)}
      </span>
    </Tooltip>
  )
}

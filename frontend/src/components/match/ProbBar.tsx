import { Tooltip } from '../shared/Tooltip'
import { gloss } from '../../lib/glossary'
import { useT } from '../../lib/i18n'

interface Props { h: number; d: number; a: number; showLabels?: boolean }

export function ProbBar({ h, d, a, showLabels = true }: Props) {
  const t = useT()
  const content = (
    <>
      <div>{gloss('mc.probbar')}</div>
      <div style={{ marginTop: 4, color: 'var(--text-mute)' }}>
        {t('card.prob_sum', { h: h.toFixed(0), d: d.toFixed(0), a: a.toFixed(0) })}
      </div>
    </>
  )
  return (
    <Tooltip content={content}>
      <div className="pbar-wrap" tabIndex={0}>
        <div className="pbar">
          <div className="ph" style={{ width: `${h}%` }} />
          <div className="pd" style={{ width: `${d}%` }} />
          <div className="pa" style={{ width: `${a}%` }} />
        </div>
        {showLabels && (
          <div className="pbar-labels">
            <span className="h">{t('card.prob.home', { n: h.toFixed(0) })}</span>
            <span className="d">{t('card.prob.draw', { n: d.toFixed(0) })}</span>
            <span className="a">{t('card.prob.away', { n: a.toFixed(0) })}</span>
          </div>
        )}
      </div>
    </Tooltip>
  )
}

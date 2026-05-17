import { Tooltip } from '../shared/Tooltip'
import { gloss } from '../../lib/glossary'
import { useT } from '../../lib/i18n'

const CLS: Record<string, string> = { W: 'fs-W', D: 'fs-D', L: 'fs-L' }

export function FormStrip({ form5 }: { form5?: string | null }) {
  const t = useT()
  if (!form5) return <span className="muted">—</span>
  const letters = form5.split('').slice(0, 5)
  const w = letters.filter((c) => c === 'W').length
  const d = letters.filter((c) => c === 'D').length
  const l = letters.filter((c) => c === 'L').length
  const content = (
    <>
      <div>{gloss('mc.form5')}</div>
      <div style={{ marginTop: 4, color: 'var(--text-mute)' }}>
        {t('card.form.label', { n: letters.length, w, d, l })}
      </div>
    </>
  )
  return (
    <Tooltip content={content}>
      <span className="fs" tabIndex={0}>
        {letters.map((c, i) => (
          <span key={i} className={`fs-l ${CLS[c] ?? ''}`}>{c}</span>
        ))}
      </span>
    </Tooltip>
  )
}

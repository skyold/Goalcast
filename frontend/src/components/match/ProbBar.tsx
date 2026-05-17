import { Tooltip } from '../shared/Tooltip'
import { gloss } from '../../lib/glossary'

interface Props { h: number; d: number; a: number; showLabels?: boolean }

export function ProbBar({ h, d, a, showLabels = true }: Props) {
  const content = (
    <>
      <div>{gloss('mc.probbar')}</div>
      <div style={{ marginTop: 4, color: 'var(--text-mute)' }}>
        主胜 {h.toFixed(0)}% · 平局 {d.toFixed(0)}% · 客胜 {a.toFixed(0)}%
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
            <span className="h">主 {h.toFixed(0)}%</span>
            <span className="d">平 {d.toFixed(0)}%</span>
            <span className="a">客 {a.toFixed(0)}%</span>
          </div>
        )}
      </div>
    </Tooltip>
  )
}

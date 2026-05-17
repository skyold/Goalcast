interface Props { h: number; d: number; a: number; showLabels?: boolean }

export function ProbBar({ h, d, a, showLabels = true }: Props) {
  return (
    <>
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
    </>
  )
}

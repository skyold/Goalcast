export default function ProbBar({ home, draw, away }: { home: number | null; draw: number | null; away: number | null }) {
  if (home == null) return null
  const h = Math.round((home ?? 0) * 100)
  const d = Math.round((draw ?? 0) * 100)
  const a = Math.round((away ?? 0) * 100)
  return (
    <div className="mc-probbar">
      <div className="pb-wrap">
        <div className="pb-home" style={{ flex: h }} />
        <div className="pb-draw" style={{ flex: d }} />
        <div className="pb-away" style={{ flex: a }} />
      </div>
      <div className="pb-labels">
        <span className="pbl"><span className="h">{h}%</span> 主</span>
        <span className="pbl">{d}% 平</span>
        <span className="pbl">客 <span className="a">{a}%</span></span>
      </div>
    </div>
  )
}

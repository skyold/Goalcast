export default function ProbBar({ home, draw, away }: { home: number | null; draw: number | null; away: number | null }) {
  if (home == null && draw == null && away == null) return null
  const h = Math.round((home ?? 0) * 100)
  const d = Math.round((draw ?? 0) * 100)
  const a = Math.round((away ?? 0) * 100)
  return (
    <div style={{ display:'flex', height:6, borderRadius:3, overflow:'hidden', gap:1 }}>
      <div style={{ flex:h, background:'#22c55e' }} title={`主胜 ${h}%`} />
      <div style={{ flex:d, background:'#64748b' }} title={`平 ${d}%`} />
      <div style={{ flex:a, background:'#f59e0b' }} title={`客胜 ${a}%`} />
    </div>
  )
}

const CLS: Record<string, string> = { W: 'fs-W', D: 'fs-D', L: 'fs-L' }

export function FormStrip({ form5 }: { form5?: string | null }) {
  if (!form5) return <span className="muted">—</span>
  return (
    <span className="fs">
      {form5.split('').slice(0, 5).map((c, i) => (
        <span key={i} className={`fs-l ${CLS[c] ?? ''}`}>{c}</span>
      ))}
    </span>
  )
}

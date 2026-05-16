const CLS: Record<string, string> = { W: 'form-w', D: 'form-d', L: 'form-l' }

export function FormStrip({ form5 }: { form5: string }) {
  if (!form5) return <span className="form-empty">—</span>
  return (
    <span className="form-strip">
      {form5.split('').slice(0, 5).map((c, i) => (
        <span key={i} className={`form-letter ${CLS[c] ?? ''}`}>{c}</span>
      ))}
    </span>
  )
}

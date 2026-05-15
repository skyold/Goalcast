type Variant = 'green' | 'amber' | 'blue' | 'purple' | 'red'

const COLORS: Record<Variant, { bg: string; color: string }> = {
  green:  { bg: 'rgba(34,197,94,0.15)',  color: '#22c55e' },
  amber:  { bg: 'rgba(245,158,11,0.15)', color: '#f59e0b' },
  blue:   { bg: 'rgba(59,130,246,0.15)', color: '#3b82f6' },
  purple: { bg: 'rgba(168,85,247,0.15)', color: '#a855f7' },
  red:    { bg: 'rgba(239,68,68,0.15)',  color: '#ef4444' },
}

export default function Badge({ children, variant = 'blue' }: { children: React.ReactNode; variant?: Variant }) {
  const { bg, color } = COLORS[variant]
  return (
    <span style={{ padding:'2px 6px', borderRadius:4, fontSize:11, fontWeight:600, background:bg, color, letterSpacing:'0.03em' }}>
      {children}
    </span>
  )
}

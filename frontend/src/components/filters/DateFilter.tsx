import { useStore } from '../../lib/store'

function offsetDay(n: number) {
  const d = new Date(); d.setDate(d.getDate() + n); return d.toISOString().split('T')[0]
}

const PRESETS = [
  { label:'今天', fn: () => offsetDay(0) },
  { label:'明天', fn: () => offsetDay(1) },
  { label:'后天', fn: () => offsetDay(2) },
]

export default function DateFilter() {
  const { selectedDate, setDate } = useStore()
  const presetValues = PRESETS.map(p => p.fn())
  const isPreset = presetValues.includes(selectedDate)

  return (
    <div style={{ display:'flex', gap:6, alignItems:'center', flexWrap:'wrap' }}>
      {PRESETS.map(({ label, fn }) => {
        const v = fn()
        const active = selectedDate === v
        return (
          <button key={label} onClick={() => setDate(v)} style={{ padding:'5px 10px', borderRadius:6, fontSize:12, border:`1px solid ${active?'#3b82f6':'#1a2d47'}`, background:active?'rgba(59,130,246,0.15)':'#0d1626', color:active?'#3b82f6':'#94a3b8', cursor:'pointer' }}>
            {label}
          </button>
        )
      })}
      <input type="date" value={!isPreset ? selectedDate : ''} onChange={e => e.target.value && setDate(e.target.value)}
        style={{ padding:'4px 8px', borderRadius:6, fontSize:12, border:`1px solid ${!isPreset?'#3b82f6':'#1a2d47'}`, background:'#0d1626', color:'#94a3b8' }} />
    </div>
  )
}

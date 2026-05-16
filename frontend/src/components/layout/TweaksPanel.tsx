// Floating Tweaks panel for theme + density. Self-contained, no external deps.
import { useState } from 'react'
import { useStore, type Theme, type Density } from '../../lib/store'

const THEMES: { v: Theme; label: string; desc: string }[] = [
  { v: 'A', label: 'A · Terminal',  desc: '深色 · 等宽数字 · 高密度' },
  { v: 'B', label: 'B · Editorial', desc: '浅色 · 衬线标题 · 大间距' },
  { v: 'C', label: 'C · Pitch',     desc: '深色 · 几何无衬线 · 圆角' },
]

const DENSITIES: { v: Density; label: string }[] = [
  { v: 'compact',  label: '紧凑' },
  { v: 'standard', label: '标准' },
  { v: 'loose',    label: '宽松' },
]

const PREVIEW_BG: Record<Theme, string> = { A: '#0a0b0d', B: '#f5f1e8', C: '#0d1117' }
const PREVIEW_FG: Record<Theme, string> = { A: '#00e08a', B: '#7a1d2e', C: '#c8ff3d' }

export default function TweaksPanel() {
  const { theme, density, setTheme, setDensity } = useStore()
  const [open, setOpen] = useState(false)

  return (
    <>
      <button
        className="tweaks-fab"
        onClick={() => setOpen(o => !o)}
        title="切换主题"
        aria-label="Tweaks"
      >
        ⚙
      </button>
      {open && (
        <div className="tweaks-panel" role="dialog">
          <header>
            <strong>Tweaks</strong>
            <button onClick={() => setOpen(false)} aria-label="关闭">×</button>
          </header>
          <div className="tweaks-section">视觉方向</div>
          <div className="tweaks-themes">
            {THEMES.map(opt => (
              <button
                key={opt.v}
                className={`tweaks-theme${theme === opt.v ? ' on' : ''}`}
                onClick={() => setTheme(opt.v)}
              >
                <span
                  className="tweaks-theme-swatch"
                  style={{ background: PREVIEW_BG[opt.v], color: PREVIEW_FG[opt.v] }}
                >G</span>
                <span>
                  <span className="tweaks-theme-label">{opt.label}</span>
                  <span className="tweaks-theme-desc">{opt.desc}</span>
                </span>
              </button>
            ))}
          </div>
          <div className="tweaks-section">信息密度</div>
          <div className="tweaks-density">
            {DENSITIES.map(opt => (
              <button
                key={opt.v}
                className={`tweaks-density-btn${density === opt.v ? ' on' : ''}`}
                onClick={() => setDensity(opt.v)}
              >{opt.label}</button>
            ))}
          </div>
        </div>
      )}
    </>
  )
}

// Floating Tweaks panel for theme + density. Self-contained, no external deps.
import { useState } from 'react'
import { useStore, type Theme, type Density } from '../../lib/store'
import { useT } from '../../lib/i18n'

const THEMES: { v: Theme; labelKey: string; descKey: string }[] = [
  { v: 'A', labelKey: 'tweaks.theme.A.label', descKey: 'tweaks.theme.A.desc' },
  { v: 'B', labelKey: 'tweaks.theme.B.label', descKey: 'tweaks.theme.B.desc' },
  { v: 'C', labelKey: 'tweaks.theme.C.label', descKey: 'tweaks.theme.C.desc' },
]

const DENSITIES: { v: Density; labelKey: string }[] = [
  { v: 'compact',  labelKey: 'tweaks.density.compact' },
  { v: 'standard', labelKey: 'tweaks.density.standard' },
  { v: 'loose',    labelKey: 'tweaks.density.loose' },
]

const PREVIEW_BG: Record<Theme, string> = { A: '#0a0b0d', B: '#f5f1e8', C: '#0d1117' }
const PREVIEW_FG: Record<Theme, string> = { A: '#00e08a', B: '#7a1d2e', C: '#c8ff3d' }

export default function TweaksPanel() {
  const { theme, density, setTheme, setDensity } = useStore()
  const [open, setOpen] = useState(false)
  const t = useT()

  return (
    <>
      <button
        className="tweaks-fab"
        onClick={() => setOpen(o => !o)}
        title={t('tweaks.toggle.title')}
        aria-label="Tweaks"
      >
        ⚙
      </button>
      {open && (
        <div className="tweaks-panel" role="dialog">
          <header>
            <strong>Tweaks</strong>
            <button onClick={() => setOpen(false)} aria-label={t('tweaks.close')}>×</button>
          </header>
          <div className="tweaks-section">{t('tweaks.section.theme')}</div>
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
                  <span className="tweaks-theme-label">{t(opt.labelKey)}</span>
                  <span className="tweaks-theme-desc">{t(opt.descKey)}</span>
                </span>
              </button>
            ))}
          </div>
          <div className="tweaks-section">{t('tweaks.section.density')}</div>
          <div className="tweaks-density">
            {DENSITIES.map(opt => (
              <button
                key={opt.v}
                className={`tweaks-density-btn${density === opt.v ? ' on' : ''}`}
                onClick={() => setDensity(opt.v)}
              >{t(opt.labelKey)}</button>
            ))}
          </div>
        </div>
      )}
    </>
  )
}

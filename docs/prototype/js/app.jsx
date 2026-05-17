// goalcast — root app
// Wires sidebar + hash-routed pages + Tweaks panel (theme + density).

const { useEffect: useE } = React;

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "theme": "A",
  "density": "standard",
  "themeLabel": "A · Terminal"
}/*EDITMODE-END*/;

const THEME_OPTIONS = [
  { v: 'A', label: 'A · Terminal',  desc: '深色 · 等宽数字 · 高密度' },
  { v: 'B', label: 'B · Editorial', desc: '浅色 · 衬线标题 · 大间距' },
  { v: 'C', label: 'C · Pitch',     desc: '深色 · 几何无衬线 · 圆角' },
];

const DENSITY_OPTIONS = [
  { v: 'compact',  label: '紧凑' },
  { v: 'standard', label: '标准' },
  { v: 'loose',    label: '宽松' },
];

function applyTheme(theme, density) {
  document.documentElement.setAttribute('data-theme', theme);
  document.documentElement.setAttribute('data-density', density);
}

function Router() {
  const { route, id } = useHashRoute();
  if (route === 'matches')  return <PageMatches />;
  if (route === 'match')    return <PageMatchDetail id={id} />;
  if (route === 'value')    return <PageValueBets />;
  if (route === 'dropping') return <PageDroppingOdds />;
  if (route === 'history')  return <PageHistory />;
  return <PageDashboard />;
}

function App() {
  const { route } = useHashRoute();
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);

  useE(() => { applyTheme(t.theme, t.density); }, [t.theme, t.density]);

  // Map first path segment to nav key
  const navKey = ['match'].includes(route) ? 'matches' : route;

  return (
    <>
      <div className="app">
        <Sidebar route={navKey} />
        <main className="main"><Router /></main>
      </div>

      <TweaksPanel title="Tweaks">
        <TweakSection label="视觉方向">
          {THEME_OPTIONS.map(opt => (
            <div
              key={opt.v}
              onClick={() => setTweak({ theme: opt.v, themeLabel: opt.label })}
              style={{
                padding: '10px 12px', borderRadius: 8, cursor: 'pointer',
                border: t.theme === opt.v ? '1px solid var(--tweaks-accent, #c8ff3d)' : '1px solid #2a2f38',
                background: t.theme === opt.v ? 'rgba(200,255,61,0.06)' : 'transparent',
                display: 'flex', alignItems: 'center', gap: 10,
              }}
            >
              <div style={{
                width: 28, height: 28, borderRadius: 6, flexShrink: 0,
                background: opt.v === 'A' ? '#0a0b0d' : opt.v === 'B' ? '#f5f1e8' : '#0d1117',
                border: '1px solid #2a2f38',
                display: 'grid', placeItems: 'center',
                color: opt.v === 'A' ? '#00e08a' : opt.v === 'B' ? '#7a1d2e' : '#c8ff3d',
                fontFamily: opt.v === 'B' ? 'Newsreader, serif' : opt.v === 'C' ? 'Space Grotesk' : 'JetBrains Mono',
                fontWeight: 800, fontSize: 13,
              }}>G</div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: '#e8e9ec' }}>{opt.label}</div>
                <div style={{ fontSize: 10, color: '#7a8088', marginTop: 2 }}>{opt.desc}</div>
              </div>
            </div>
          ))}
        </TweakSection>

        <TweakSection label="信息密度">
          <TweakRadio
            value={t.density}
            onChange={v => setTweak({ density: v })}
            options={DENSITY_OPTIONS.map(o => ({ value: o.v, label: o.label }))}
          />
        </TweakSection>

        <TweakSection label="说明">
          <div style={{ fontSize: 11, color: '#7a8088', lineHeight: 1.5 }}>
            3 个视觉方向通过 CSS 变量切换，所有页面共享同一套组件 — 用来评估同一信息架构在不同质感下的体验。点击 Sidebar 跳转页面，点比赛卡片进入详情。
          </div>
        </TweakSection>
      </TweaksPanel>
    </>
  );
}

// Mount
const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);

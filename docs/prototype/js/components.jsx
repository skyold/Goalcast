// Shared visual components — small, theme-aware atoms.
// All exported to window for cross-file use.

const { useState, useMemo } = React;

// ----- Predictability Badge -----
function PredictabilityBadge({ level }) {
  if (!level) return null;
  const map = { high: '高', good: '良', medium: '中', poor: '差' };
  return <span className={`pb pb-${level}`}>{map[level] || level}</span>;
}

// ----- Form Strip (W/D/L pills) -----
function FormStrip({ form5 }) {
  return (
    <span className="fs">
      {(form5 || '').split('').map((c, i) => (
        <span key={i} className={`fs-l fs-${c}`}>{c}</span>
      ))}
    </span>
  );
}

// ----- Team Abbreviation Tile -----
function TeamAbbr({ abbr, color, size }) {
  const s = size || 26;
  return (
    <span className="mc-abbr" style={{ background: color, width: s, height: s, fontSize: s * 0.36 }}>
      {abbr}
    </span>
  );
}

// ----- Probability bar (3-segment) -----
function ProbBar({ h, d, a, showLabels = true }) {
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
  );
}

// ----- Big bar row (for match detail) -----
function BigBar({ label, value, kind = 'h' }) {
  return (
    <div className="bigbar">
      <span className="bigbar-lbl">{label}</span>
      <div className="bigbar-track">
        <div className={`bigbar-fill ${kind}`} style={{ width: `${Math.min(100, value)}%` }} />
      </div>
      <span className="bigbar-val">{value.toFixed(1)}%</span>
    </div>
  );
}

// ----- Spark line (inline tiny SVG) -----
function Spark({ values, color, width = 64, height = 22 }) {
  if (!values || values.length < 2) return null;
  const min = Math.min(...values), max = Math.max(...values);
  const dx = width / (values.length - 1);
  const pts = values.map((v, i) => {
    const x = i * dx;
    const y = max === min ? height / 2 : height - ((v - min) / (max - min)) * (height - 4) - 2;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} className="spark" style={{ overflow: 'visible' }}>
      <polyline points={pts} fill="none" stroke={color || 'currentColor'} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

// ----- Hash-based navigation -----
function useHashRoute() {
  const [hash, setHash] = useState(window.location.hash || '#/');
  React.useEffect(() => {
    const onChange = () => setHash(window.location.hash || '#/');
    window.addEventListener('hashchange', onChange);
    return () => window.removeEventListener('hashchange', onChange);
  }, []);
  // Parse e.g. "#/matches" or "#/match/101"
  const parts = hash.replace(/^#\/?/, '').split('/');
  const route = parts[0] || '';
  const id = parts[1] || null;
  return { hash, route, id, go: (path) => { window.location.hash = path; } };
}

// ----- Click-as-link helper -----
function navTo(path) {
  return (e) => { e?.preventDefault?.(); window.location.hash = path; };
}

// ----- Sidebar -----
const NAV = [
  { key: '',         label: '总览',     glyph: '◆' },
  { key: 'matches',  label: '比赛列表', glyph: '▦' },
  { key: 'value',    label: '价值投注', glyph: '◈' },
  { key: 'dropping', label: '跌水赔率', glyph: '▼' },
  { key: 'history',  label: '历史回测', glyph: '⊟' },
];

function Sidebar({ route }) {
  return (
    <aside className="sidebar">
      <div className="sb-logo">
        <div className="sb-mark">G</div>
        <div className="sb-name">goal<em>cast</em></div>
      </div>
      <div className="sb-section">分析</div>
      {NAV.map(n => (
        <a key={n.key || 'home'} className={`sb-item ${route === n.key ? 'active' : ''}`} href={`#/${n.key}`}>
          <span className="sb-glyph">{n.glyph}</span>
          <span>{n.label}</span>
        </a>
      ))}
      <div className="sb-spacer" />
      <div className="sb-foot">
        <div className="sb-foot-row"><span className="sb-dot" />数据同步 · 实时</div>
        <div className="sb-foot-row mono">{new Date().toLocaleDateString('zh-CN')} · 13 场候选</div>
      </div>
    </aside>
  );
}

// ----- MatchCard (the workhorse) -----
function MatchCard({ fixture, onClick }) {
  const ko = window.fmtKickoff(fixture.kickoff_utc);
  const ps = fixture.prediction_summary;
  const dropPct = fixture.drop_flag?.drop_percentage;
  const ft = fixture.odds?.ft_result?.pinnacle || {};
  const drop = dropPct >= 60 ? 'hot' : 'warm';

  return (
    <div className="mc" onClick={onClick} role="button" tabIndex={0}
         onKeyDown={(e) => { if (e.key === 'Enter') onClick?.(); }}>
      <div className="mc-hdr">
        <div className="mc-league">
          <PredictabilityBadge level={fixture.predictability} />
          <span>{fixture.competition_name}</span>
        </div>
        <div className="mc-time">
          <span className="day">{ko.day}</span>
          <span>{ko.time}</span>
        </div>
      </div>

      <div className="mc-body">
        <div className="mc-team home">
          <div className="mc-namerow">
            <TeamAbbr abbr={fixture.home_abbr} color={fixture.home_color} />
            <span className="mc-tname">{fixture.home_team}</span>
          </div>
          <span className="mc-rank">排名 <em>#{fixture.home_rank}</em> · 进 {fixture.goals.hf} 失 {fixture.goals.ha}</span>
          <FormStrip form5={fixture.home_form?.form5} />
        </div>

        <div className="mc-vs">
          <div className="mc-vs-time">{ko.time}</div>
          <div className="mc-vs-day">{ko.date}</div>
          <div className="mc-vs-vs">VS</div>
        </div>

        <div className="mc-team away">
          <div className="mc-namerow">
            <TeamAbbr abbr={fixture.away_abbr} color={fixture.away_color} />
            <span className="mc-tname">{fixture.away_team}</span>
          </div>
          <span className="mc-rank">排名 <em>#{fixture.away_rank}</em> · 进 {fixture.goals.af} 失 {fixture.goals.aa}</span>
          <FormStrip form5={fixture.away_form?.form5} />
        </div>
      </div>

      {ps && (
        <ProbBar h={ps.home_win_pct} d={ps.draw_pct} a={ps.away_win_pct} />
      )}

      <div className="mc-ftr">
        <div className="odds-box">
          <div className={`ob ${ps && ps.home_win_pct > 45 ? 'hot' : ''}`}>
            <div className="ol">主</div>
            <div className="ov">{ft.home?.toFixed(2) ?? '—'}</div>
          </div>
          <div className="ob">
            <div className="ol">平</div>
            <div className="ov">{ft.draw?.toFixed(2) ?? '—'}</div>
          </div>
          <div className={`ob ${ps && ps.away_win_pct > 45 ? 'hot' : ''}`}>
            <div className="ol">客</div>
            <div className="ov">{ft.away?.toFixed(2) ?? '—'}</div>
          </div>
        </div>
        {dropPct != null && (
          <>
            <div className="ftr-sep" />
            <div className={`drop-tag ${dropPct >= 60 ? '' : 'warn'}`}>
              <span className="arr">▼</span>
              <span>{Math.round(dropPct)}%</span>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

Object.assign(window, {
  PredictabilityBadge, FormStrip, TeamAbbr, ProbBar, BigBar, Spark,
  useHashRoute, navTo, Sidebar, MatchCard, NAV,
});

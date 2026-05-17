// All 6 pages — Dashboard, Matches, MatchDetail, ValueBets, DroppingOdds, History.
// Each is a pure function of route + window data.

const { useState: useStateP, useMemo: useMemoP } = React;

// ===================== Dashboard =====================
function PageDashboard() {
  const total = window.FIXTURES.length;
  const withAi = window.FIXTURES.filter(f => f.prediction_summary).length;
  const goodPred = window.FIXTURES.filter(f => ['high', 'good', 'medium'].includes(f.predictability)).length;
  const hotDrops = window.DROPPING.slice(0, 5);
  const topValue = window.VALUE_BETS.slice(0, 5);
  const upcoming = [...window.FIXTURES].sort((a, b) => new Date(a.kickoff_utc) - new Date(b.kickoff_utc)).slice(0, 4);

  return (
    <>
      <div className="ph">
        <div>
          <div className="ph-title">总览</div>
          <div className="ph-sub">未来 7 天 · {new Date().toLocaleDateString('zh-CN', { month: 'long', day: 'numeric', weekday: 'long' })}</div>
        </div>
        <div className="ph-actions">
          <button className="btn">导出</button>
          <button className="btn btn-primary">↻ 同步数据</button>
        </div>
      </div>

      <div className="page">
        <div className="kpi-grid">
          <div className="kpi">
            <span className="kpi-lbl">候选比赛</span>
            <span className="kpi-val">{total}</span>
            <span className="kpi-delta">+ 3 自昨日</span>
            <Spark values={[8, 10, 9, 11, 13, 12, 13]} color="var(--acc)" />
          </div>
          <div className="kpi">
            <span className="kpi-lbl">AI 已建模</span>
            <span className="kpi-val">{withAi}</span>
            <span className="kpi-delta">{Math.round(withAi / total * 100)}% 覆盖率</span>
            <Spark values={[6, 7, 8, 9, 10, 11, withAi]} color="var(--acc-3)" />
          </div>
          <div className="kpi">
            <span className="kpi-lbl">高跌幅 (≥50%)</span>
            <span className="kpi-val">{window.DROPPING.filter(d => d.drop_pct >= 50).length}</span>
            <span className="kpi-delta">5 场预警</span>
            <Spark values={[2, 3, 4, 3, 5, 6, 5]} color="var(--acc-2)" />
          </div>
          <div className="kpi">
            <span className="kpi-lbl">7 日命中率</span>
            <span className="kpi-val">62%</span>
            <span className="kpi-delta">+ 4.2 pt</span>
            <Spark values={[55, 58, 53, 60, 58, 61, 62]} color="var(--acc)" />
          </div>
        </div>

        <div className="dash-grid">
          <div className="dash-col">
            <div className="card">
              <div className="card-hdr">
                <div className="card-title">今日 Top 5 跌赔</div>
                <a className="card-sub" href="#/dropping">查看全部 →</a>
              </div>
              {hotDrops.map((d, i) => (
                <div key={d.fid} className="alert-row" onClick={navTo(`/match/${d.fid}`)}>
                  <div className="alert-pct">{Math.round(d.drop_pct)}%</div>
                  <div className="alert-mid">
                    <div className="alert-match">{d.home} vs {d.away}</div>
                    <div className="alert-meta">{d.league} · {window.fmtKickoff(d.kick).day} {window.fmtKickoff(d.kick).time} · 市场 {d.market} · pinnacle</div>
                  </div>
                  <div className="mono dim">{d.odds_open.toFixed(2)} → <span style={{ color: 'var(--acc)', fontWeight: 700 }}>{d.odds_now.toFixed(2)}</span></div>
                </div>
              ))}
            </div>

            <div className="card">
              <div className="card-hdr">
                <div className="card-title">即将开赛</div>
                <a className="card-sub" href="#/matches">查看全部 →</a>
              </div>
              <div className="match-grid">
                {upcoming.map(f => <MatchCard key={f.id} fixture={f} onClick={navTo(`/match/${f.id}`)} />)}
              </div>
            </div>
          </div>

          <div className="dash-col">
            <div className="card">
              <div className="card-hdr">
                <div className="card-title">高 Edge 价值投注</div>
                <a className="card-sub" href="#/value">查看全部 →</a>
              </div>
              {topValue.map((v, i) => (
                <div key={v.fid} className="alert-row" onClick={navTo(`/match/${v.fid}`)}>
                  <div className="alert-pct" style={{ color: 'var(--acc-2)' }}>+{v.edge.toFixed(1)}%</div>
                  <div className="alert-mid">
                    <div className="alert-match">{v.home} vs {v.away}</div>
                    <div className="alert-meta">{v.league} · 选项 {v.sel} · 模型 {v.prob.toFixed(0)}% · @ {v.odds.toFixed(2)}</div>
                  </div>
                </div>
              ))}
            </div>

            <div className="card">
              <div className="card-hdr"><div className="card-title">数据健康</div><span className="card-sub">实时</span></div>
              <div className="bigbar">
                <span className="bigbar-lbl">赔率</span>
                <div className="bigbar-track"><div className="bigbar-fill h" style={{ width: '94%' }} /></div>
                <span className="bigbar-val">94%</span>
              </div>
              <div className="bigbar">
                <span className="bigbar-lbl">阵容</span>
                <div className="bigbar-track"><div className="bigbar-fill o" style={{ width: '78%' }} /></div>
                <span className="bigbar-val">78%</span>
              </div>
              <div className="bigbar">
                <span className="bigbar-lbl">模型</span>
                <div className="bigbar-track"><div className="bigbar-fill a" style={{ width: '69%' }} /></div>
                <span className="bigbar-val">69%</span>
              </div>
              <div className="bigbar">
                <span className="bigbar-lbl">伤停</span>
                <div className="bigbar-track"><div className="bigbar-fill d" style={{ width: '42%' }} /></div>
                <span className="bigbar-val">42%</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

// ===================== Matches =====================
function PageMatches() {
  const [selectedLeagues, setSel] = useStateP(['英超', '西甲', '德甲', '意甲', '法甲', '欧冠']);
  const [date, setDate] = useStateP('今天');
  const [filter, setFilter] = useStateP({ excludePoor: false, onlyHigh: false, minDrop: false, hasAi: false });
  const [sort, setSort] = useStateP('time');

  const allLeagues = Array.from(new Set(window.FIXTURES.map(f => f.competition_name)));
  function togL(l) { setSel(s => s.includes(l) ? s.filter(x => x !== l) : [...s, l]); }

  const fixtures = useMemoP(() => {
    let xs = window.FIXTURES.filter(f => selectedLeagues.includes(f.competition_name));
    if (filter.excludePoor) xs = xs.filter(f => f.predictability !== 'poor');
    if (filter.onlyHigh)   xs = xs.filter(f => ['high', 'good'].includes(f.predictability));
    if (filter.minDrop)    xs = xs.filter(f => (f.drop_flag?.drop_percentage ?? 0) >= 50);
    if (filter.hasAi)      xs = xs.filter(f => f.prediction_summary);
    if (sort === 'drop') xs.sort((a, b) => (b.drop_flag?.drop_percentage ?? 0) - (a.drop_flag?.drop_percentage ?? 0));
    else if (sort === 'prob') xs.sort((a, b) => (b.prediction_summary?.home_win_pct ?? 0) - (a.prediction_summary?.home_win_pct ?? 0));
    else xs.sort((a, b) => new Date(a.kickoff_utc) - new Date(b.kickoff_utc));
    return xs;
  }, [selectedLeagues, filter, sort]);

  const grouped = window.groupByLeague(fixtures);

  return (
    <>
      <div className="ph">
        <div>
          <div className="ph-title">比赛列表</div>
          <div className="ph-sub">共 {fixtures.length} 场 · 已选 {selectedLeagues.length} 个联赛</div>
        </div>
        <div className="ph-actions">
          <button className="btn">↻ 刷新</button>
          <button className="btn btn-primary">导出 CSV</button>
        </div>
      </div>

      <div className="filters">
        <div className="filter-grp">
          <span className="filter-lbl">日期</span>
          {['今天', '明天', '后天'].map(d => (
            <button key={d} className={`chip ${date === d ? 'active' : ''}`} onClick={() => setDate(d)}>{d}</button>
          ))}
          <input type="date" className="date-pick" defaultValue={new Date().toISOString().slice(0, 10)} />
        </div>

        <div className="filter-grp">
          <span className="filter-lbl">联赛</span>
          {allLeagues.map(l => (
            <button key={l} className={`chip chip-mute ${selectedLeagues.includes(l) ? 'active' : ''}`} onClick={() => togL(l)}>{l}</button>
          ))}
        </div>

        <div className="filter-grp">
          <span className="filter-lbl">筛选</span>
          <button className={`chip ${filter.excludePoor ? 'active' : ''}`} onClick={() => setFilter(f => ({ ...f, excludePoor: !f.excludePoor }))}>排除 差</button>
          <button className={`chip ${filter.onlyHigh ? 'active' : ''}`} onClick={() => setFilter(f => ({ ...f, onlyHigh: !f.onlyHigh }))}>只看 高+良</button>
          <button className={`chip ${filter.minDrop ? 'active' : ''}`} onClick={() => setFilter(f => ({ ...f, minDrop: !f.minDrop }))}>跌幅 ≥ 50%</button>
          <button className={`chip ${filter.hasAi ? 'active' : ''}`} onClick={() => setFilter(f => ({ ...f, hasAi: !f.hasAi }))}>有 AI</button>
        </div>

        <div className="filter-spacer" />

        <div className="filter-grp">
          <span className="filter-lbl">排序</span>
          <select className="date-pick" value={sort} onChange={e => setSort(e.target.value)}>
            <option value="time">开赛时间</option>
            <option value="drop">跌幅</option>
            <option value="prob">主胜概率</option>
          </select>
        </div>
      </div>

      <div className="page">
        {Object.entries(grouped).map(([league, fxs]) => (
          <div key={league} className="league-block">
            <h2 className="section-title">
              <span>{league}</span>
              <span className="count">{fxs.length} 场</span>
            </h2>
            <div className="match-grid">
              {fxs.map(f => <MatchCard key={f.id} fixture={f} onClick={navTo(`/match/${f.id}`)} />)}
            </div>
          </div>
        ))}
        {fixtures.length === 0 && <div className="empty">无符合条件的比赛 · 调整筛选条件试试</div>}
      </div>
    </>
  );
}

// ===================== MatchDetail =====================
const SAMPLE_DROPS = [
  { time: '14:32', mkt: '主胜', pct: 67, bm: 'pinnacle' },
  { time: '13:18', mkt: '主胜', pct: 42, bm: 'bet365' },
  { time: '11:45', mkt: '大2.5', pct: 38, bm: 'pinnacle' },
  { time: '09:22', mkt: '亚盘 -0.25', pct: 24, bm: 'pinnacle' },
  { time: '昨 23:10', mkt: '主胜', pct: 18, bm: 'william' },
];
const SAMPLE_H2H = []; // removed — OddAlerts API has no H2H endpoint; see docs/frontend-data-gaps.md

function PageMatchDetail({ id }) {
  const f = window.FIXTURES.find(x => x.id === Number(id)) || window.FIXTURES[0];
  const [ahLine, setAhLine] = useStateP(f.odds.asian_handicap.line);
  const ps = f.prediction_summary;
  const ko = window.fmtKickoff(f.kickoff_utc);

  const ahLines = [-1.25, -0.75, -0.25, 0, +0.25, +0.75];
  const ahRows = ahLines.map(l => ({
    line: l,
    p_h: (1 / (1.8 + l * 0.15)).toFixed(2),
    p_a: (1 / (2.0 - l * 0.15)).toFixed(2),
    b_h: (1 / (1.82 + l * 0.15)).toFixed(2),
    b_a: (1 / (2.02 - l * 0.15)).toFixed(2),
    edge: ((l + 0.25) * 4.3).toFixed(1),
  }));

  // Build a 6x6 scoreline heatmap (synthetic poisson-like)
  function heatCells() {
    const out = [];
    const m1 = 1.6, m2 = 1.3;
    const fact = (n) => n <= 1 ? 1 : n * fact(n - 1);
    const pois = (k, l) => Math.exp(-l) * Math.pow(l, k) / fact(k);
    let total = 0; const cells = [];
    for (let h = 0; h <= 5; h++) for (let a = 0; a <= 5; a++) {
      const p = pois(h, m1) * pois(a, m2);
      total += p; cells.push({ h, a, p });
    }
    cells.forEach(c => { c.pct = c.p / total * 100; });
    return cells;
  }
  const cells = heatCells();
  const maxP = Math.max(...cells.map(c => c.pct));

  return (
    <>
      <div className="ph">
        <div>
          <a href="#/matches" className="card-sub" style={{ display: 'block', marginBottom: 4 }}>← 比赛列表</a>
          <div className="ph-title">{f.home_team} vs {f.away_team}</div>
          <div className="ph-sub">{f.competition_name} · {f.competition_country} · {ko.date} {ko.day} {ko.time}</div>
        </div>
        <div className="ph-actions">
          <PredictabilityBadge level={f.predictability} />
          <button className="btn">⭐ 收藏</button>
          <button className="btn btn-primary">下注计算器</button>
        </div>
      </div>

      <div className="page">
        <div className="md-hero">
          <div className="md-team home">
            <div className="md-team-row">
              <TeamAbbr abbr={f.home_abbr} color={f.home_color} size={56} />
              <div>
                <div className="tname">{f.home_team}</div>
                <div className="meta">排名 #{f.home_rank} · 进 {f.goals.hf} 失 {f.goals.ha}</div>
              </div>
            </div>
            <FormStrip form5={f.home_form?.form5} />
          </div>
          <div className="md-vs">
            <div className="ko-time">{ko.time}</div>
            <div className="ko-date">{ko.day} · {ko.date}</div>
            <div className="ko-vs">— VS —</div>
          </div>
          <div className="md-team away">
            <div className="md-team-row">
              <div style={{ textAlign: 'left' }}>
                <div className="tname">{f.away_team}</div>
                <div className="meta">排名 #{f.away_rank} · 进 {f.goals.af} 失 {f.goals.aa}</div>
              </div>
              <TeamAbbr abbr={f.away_abbr} color={f.away_color} size={56} />
            </div>
            <FormStrip form5={f.away_form?.form5} />
          </div>
        </div>

        <div className="md-grid">
          <div className="md-col">
            <div className="card">
              <div className="card-hdr">
                <div className="card-title">模型概率 · 10,000 次模拟</div>
                <span className="card-sub">更新于 14:02</span>
              </div>
              <BigBar label="主胜" value={ps.home_win_pct} kind="h" />
              <BigBar label="平局" value={ps.draw_pct} kind="d" />
              <BigBar label="客胜" value={ps.away_win_pct} kind="a" />
              <div className="divider" />
              <BigBar label="大 2.5" value={ps.o25_pct} kind="o" />
              <BigBar label="两队进球" value={ps.btts_pct} kind="o" />
            </div>

            <div className="card">
              <div className="card-hdr">
                <div className="card-title">比分概率热图</div>
                <select className="date-pick" value={ahLine} onChange={e => setAhLine(parseFloat(e.target.value))}>
                  {ahLines.map(l => <option key={l} value={l}>亚盘 {l > 0 ? '+' : ''}{l}</option>)}
                </select>
              </div>
              <div className="heat" style={{ gridTemplateColumns: '32px repeat(6, 1fr)' }}>
                <div className="hlbl"></div>
                {[0, 1, 2, 3, 4, 5].map(a => <div key={`top${a}`} className="htop">客 {a}</div>)}
                {[0, 1, 2, 3, 4, 5].map(h => (
                  <React.Fragment key={`row${h}`}>
                    <div className="hlbl">主 {h}</div>
                    {[0, 1, 2, 3, 4, 5].map(a => {
                      const c = cells.find(c => c.h === h && c.a === a);
                      const intensity = c.pct / maxP;
                      const cls = h - a > ahLine ? 'win' : h - a === Math.round(ahLine) ? 'push' : 'lose';
                      const bg = `color-mix(in srgb, var(--acc) ${Math.round(intensity * 60)}%, var(--surface-2))`;
                      return (
                        <div key={`c${h}${a}`} className={`hcell ${cls}`} style={{ background: bg }}>
                          {c.pct >= 1 ? c.pct.toFixed(1) : ''}
                        </div>
                      );
                    })}
                  </React.Fragment>
                ))}
              </div>
              <div className="divider" />
              <div style={{ display: 'flex', gap: 12, fontSize: 'var(--fs-sm)', justifyContent: 'center' }}>
                <span><span className="dot acc" />赢 56.2%</span>
                <span><span className="dot acc2" />走盘 12.4%</span>
                <span><span style={{ width: 8, height: 8, borderRadius: '50%', display: 'inline-block', background: 'var(--neg)', marginRight: 6, verticalAlign: 'middle' }} />输 31.4%</span>
              </div>
            </div>

            <div className="card">
              <div className="card-hdr">
                <div className="card-title">亚盘全表</div>
                <span className="card-sub">{ahLines.length} 线 · pinnacle + bet365</span>
              </div>
              <table className="aht">
                <thead><tr><th>线</th><th>P 主</th><th>P 客</th><th>365 主</th><th>365 客</th><th>Edge</th></tr></thead>
                <tbody>
                  {ahRows.map(r => (
                    <tr key={r.line}>
                      <td className="line">{r.line > 0 ? '+' : ''}{r.line}</td>
                      <td>{r.p_h}</td>
                      <td>{r.p_a}</td>
                      <td>{r.b_h}</td>
                      <td>{r.b_a}</td>
                      <td style={{ color: parseFloat(r.edge) > 0 ? 'var(--acc)' : 'var(--text-mute)', fontWeight: 700 }}>
                        {parseFloat(r.edge) > 0 ? '+' : ''}{r.edge}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="md-col">
            <div className="card">
              <div className="card-hdr">
                <div className="card-title">跌赔记录</div>
                <span className="card-sub">最近 24h</span>
              </div>
              {SAMPLE_DROPS.map((d, i) => (
                <div key={i} className="drop-row">
                  <span className="time">{d.time}</span>
                  <span className="mkt"><span className="tag-mkt">{d.mkt}</span></span>
                  <span className="pct">{d.pct}%</span>
                  <span className="bm">{d.bm}</span>
                </div>
              ))}
            </div>

            <div className="card">
              <div className="card-hdr">
                <div className="card-title">两队状态对比</div>
                <span className="card-sub">赛季累计</span>
              </div>
              <BigBar label="主净胜" value={68} kind="h" />
              <BigBar label="客净胜" value={52} kind="a" />
              <BigBar label="主主场胜率" value={74} kind="h" />
              <BigBar label="客客场胜率" value={41} kind="a" />
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

// ===================== ValueBets =====================
function PageValueBets() {
  const [minEdge, setMinEdge] = useStateP(0);
  const bets = window.VALUE_BETS.filter(v => v.edge >= minEdge);

  return (
    <>
      <div className="ph">
        <div>
          <div className="ph-title">价值投注</div>
          <div className="ph-sub">基于模型概率 vs 市场赔率的 edge · {bets.length} 个机会</div>
        </div>
        <div className="ph-actions">
          <button className="btn">导出</button>
        </div>
      </div>

      <div className="filters">
        <div className="filter-grp">
          <span className="filter-lbl">最小 Edge</span>
          {[0, 5, 10, 15].map(e => (
            <button key={e} className={`chip ${minEdge === e ? 'active' : ''}`} onClick={() => setMinEdge(e)}>
              ≥ {e}%
            </button>
          ))}
        </div>
        <div className="filter-grp">
          <span className="filter-lbl">类型</span>
          <button className="chip chip-mute active">1x2</button>
          <button className="chip chip-mute active">亚盘</button>
          <button className="chip chip-mute active">大小球</button>
        </div>
      </div>

      <div className="page">
        {bets.map((v, i) => {
          const ko = window.fmtKickoff(v.kick);
          return (
            <div key={i} className="vb-row" onClick={navTo(`/match/${v.fid}`)}>
              <div className="vb-rank">{i + 1}</div>
              <div>
                <div className="vb-match-title">{v.home} vs {v.away}</div>
                <div className="vb-match-meta">{v.league} · {ko.day} {ko.time} · 模型 {v.prob.toFixed(1)}%</div>
              </div>
              <div className="vb-cell"><span className="vb-sel">{v.sel}</span></div>
              <div className="vb-cell">
                <div className="vb-cell-val">{v.odds.toFixed(2)}</div>
                <div className="vb-cell-lbl">赔率</div>
              </div>
              <div className="vb-cell">
                <div className="vb-cell-val">{v.prob.toFixed(1)}%</div>
                <div className="vb-cell-lbl">概率</div>
              </div>
              <div className="vb-cell">
                <div className="vb-cell-val acc">+{v.edge.toFixed(1)}%</div>
                <div className="vb-cell-lbl">Edge</div>
              </div>
            </div>
          );
        })}
      </div>
    </>
  );
}

// ===================== DroppingOdds =====================
function PageDroppingOdds() {
  const [minDrop, setMinDrop] = useStateP(20);
  const items = window.DROPPING.filter(d => d.drop_pct >= minDrop);

  return (
    <>
      <div className="ph">
        <div>
          <div className="ph-title">跌水赔率</div>
          <div className="ph-sub">市场对哪边的信心在快速增强 · {items.length} 个事件</div>
        </div>
        <div className="ph-actions">
          <button className="btn">订阅推送</button>
        </div>
      </div>

      <div className="filters">
        <div className="filter-grp">
          <span className="filter-lbl">阈值</span>
          {[20, 40, 50, 60].map(t => (
            <button key={t} className={`chip ${minDrop === t ? 'active' : ''}`} onClick={() => setMinDrop(t)}>≥ {t}%</button>
          ))}
        </div>
        <div className="filter-grp">
          <span className="filter-lbl">市场</span>
          <button className="chip chip-mute active">1x2</button>
          <button className="chip chip-mute">亚盘</button>
          <button className="chip chip-mute">大小球</button>
        </div>
        <div className="filter-grp">
          <span className="filter-lbl">来源</span>
          <button className="chip chip-mute active">pinnacle</button>
          <button className="chip chip-mute active">bet365</button>
        </div>
      </div>

      <div className="page">
        {items.map((d, i) => {
          const ko = window.fmtKickoff(d.kick);
          return (
            <div key={i} className="do-card" onClick={navTo(`/match/${d.fid}`)}>
              <div>
                <div className="do-info-title">{d.home} vs {d.away}</div>
                <div className="do-info-meta">{d.league} · {ko.day} {ko.time} · 市场 <span className="tag-mkt">{d.market}</span> · 跌于 {new Date(d.recorded_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}</div>
              </div>
              <div className="do-track">
                <span className="old">{d.odds_open.toFixed(2)}</span>
                <span className="arrow">→</span>
                <span className="new">{d.odds_now.toFixed(2)}</span>
              </div>
              <div className="do-pct">
                <div className="do-pct-val">{Math.round(d.drop_pct)}%</div>
                <div className="do-pct-lbl">↓ DROP</div>
              </div>
            </div>
          );
        })}
        {items.length === 0 && <div className="empty">当前阈值下无跌赔事件</div>}
      </div>
    </>
  );
}

// ===================== History =====================
function PageHistory() {
  const [strategy, setStrategy] = useStateP('all');
  const items = window.HISTORY;

  const wins = items.filter(h => h.result === 'W').length;
  const losses = items.filter(h => h.result === 'L').length;
  const draws = items.filter(h => h.result === 'D').length;
  const winRate = (wins / items.length * 100);
  const roi = 14.2;

  return (
    <>
      <div className="ph">
        <div>
          <div className="ph-title">历史回测</div>
          <div className="ph-sub">策略表现 · 最近 30 天</div>
        </div>
        <div className="ph-actions">
          <button className="btn">导出 CSV</button>
          <button className="btn btn-primary">新建策略</button>
        </div>
      </div>

      <div className="page">
        <div className="kpi-grid">
          <div className="kpi">
            <span className="kpi-lbl">总样本</span>
            <span className="kpi-val">{items.length}</span>
            <span className="kpi-delta">10 场触发</span>
          </div>
          <div className="kpi">
            <span className="kpi-lbl">胜率</span>
            <span className="kpi-val">{winRate.toFixed(0)}%</span>
            <span className="kpi-delta">{wins}胜 {draws}平 {losses}负</span>
          </div>
          <div className="kpi">
            <span className="kpi-lbl">ROI</span>
            <span className="kpi-val">+{roi.toFixed(1)}%</span>
            <span className="kpi-delta">vs 上周期 +2.4 pt</span>
            <Spark values={[5, 8, 7, 11, 10, 13, 14]} color="var(--acc)" />
          </div>
          <div className="kpi">
            <span className="kpi-lbl">平均 Edge</span>
            <span className="kpi-val">+7.9%</span>
            <span className="kpi-delta">命中赔率 1.92</span>
          </div>
        </div>

        <div className="filters" style={{ borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', marginBottom: 'var(--gap-grid)' }}>
          <div className="filter-grp">
            <span className="filter-lbl">策略</span>
            {[['all','全部'], ['drop','高跌幅'], ['value','高 Edge'], ['high','高可预测']].map(([k, l]) => (
              <button key={k} className={`chip ${strategy === k ? 'active' : ''}`} onClick={() => setStrategy(k)}>{l}</button>
            ))}
          </div>
          <div className="filter-grp">
            <span className="filter-lbl">联赛</span>
            <button className="chip chip-mute active">英超</button>
            <button className="chip chip-mute active">西甲</button>
            <button className="chip chip-mute active">德甲</button>
            <button className="chip chip-mute active">意甲</button>
            <button className="chip chip-mute active">法甲</button>
          </div>
        </div>

        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <table className="ht">
            <thead>
              <tr>
                <th>日期</th>
                <th>联赛</th>
                <th>比赛</th>
                <th style={{ textAlign: 'center' }}>比分</th>
                <th style={{ textAlign: 'center' }}>跌幅</th>
                <th style={{ textAlign: 'center' }}>预测度</th>
                <th>策略选项</th>
                <th style={{ textAlign: 'center' }}>Edge</th>
                <th style={{ textAlign: 'center' }}>结果</th>
              </tr>
            </thead>
            <tbody>
              {items.map(h => (
                <tr key={h.id} onClick={navTo(`/match/${h.id}`)}>
                  <td className="num">{h.date.slice(5)}</td>
                  <td>{h.league}</td>
                  <td className="match">{h.home} vs {h.away}</td>
                  <td className="score" style={{ textAlign: 'center' }}>{h.sh}-{h.sa}</td>
                  <td className="num" style={{ textAlign: 'center', color: 'var(--acc)', fontWeight: 700 }}>{h.drop_pct}%</td>
                  <td style={{ textAlign: 'center' }}><PredictabilityBadge level={h.predictability} /></td>
                  <td><span className="tag-mkt">{h.bet}</span></td>
                  <td className="num" style={{ textAlign: 'center', color: 'var(--acc-2)', fontWeight: 700 }}>+{h.edge}%</td>
                  <td className={`r${h.result}`} style={{ textAlign: 'center' }}>{h.result === 'W' ? '✓ 赢' : h.result === 'L' ? '✗ 输' : '◯ 走'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

Object.assign(window, {
  PageDashboard, PageMatches, PageMatchDetail, PageValueBets, PageDroppingOdds, PageHistory,
});

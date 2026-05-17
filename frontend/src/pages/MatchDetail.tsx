// MatchDetail. H2H section removed (no OddAlerts endpoint — see docs/frontend-data-gaps.md).
// "Two-team comparison" uses only fields available from /stats/fixture (no possession).
import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api, type FixtureDetail } from '../lib/api'
import { fmtKickoff } from '../lib/format'
import { PredictabilityBadge } from '../components/shared/PredictabilityBadge'
import { InfoIcon } from '../components/shared/InfoIcon'
import { FormStrip } from '../components/match/FormStrip'
import { TeamAbbr } from '../components/match/TeamAbbr'
import { BigBar } from '../components/match/BigBar'
import { ScorelineHeatmap } from '../components/match/ScorelineHeatmap'   // your existing comp
import { AhLineSelector } from '../components/match/AhLineSelector'     // your existing comp
import { AhLineTable } from '../components/match/AhLineTable'           // your existing comp

export default function MatchDetail() {
  const { id } = useParams()
  const nav = useNavigate()
  const [data, setData] = useState<FixtureDetail | null>(null)
  const [ahLine, setAhLine] = useState<number>(-0.5)

  useEffect(() => {
    if (!id) return
    api.fixture(Number(id)).then((d) => {
      setData(d)
      const lines = d.odds?.asian_handicap_lines ?? []
      if (lines.length) setAhLine(lines[0].line)
    })
  }, [id])

  if (!data) return <div className="empty">加载中…</div>

  const f = data.fixture
  const p = data.prediction
  const ah_lines = data.odds?.asian_handicap_lines ?? []
  const ko = fmtKickoff(f.kickoff_utc)
  const homeForm = data.home_team_obj?.form
  const awayForm = data.away_team_obj?.form

  return (
    <>
      <div className="ph">
        <div>
          <a href="#" onClick={(e) => { e.preventDefault(); nav('/matches') }} className="card-sub" style={{ display: 'block', marginBottom: 4 }}>← 比赛列表</a>
          <div className="ph-title">{f.home_team} vs {f.away_team}</div>
          <div className="ph-sub">
            {f.competition_name}{f.competition_country ? ` · ${f.competition_country}` : ''} · {ko.date} {ko.day} {ko.time}
          </div>
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
              <TeamAbbr name={f.home_team} teamId={f.home_team_id} size={56} />
              <div>
                <div className="tname">{f.home_team}</div>
                {homeForm && (
                  <div className="meta">
                    进 {homeForm.gf} 失 {homeForm.ga} · {homeForm.won}-{homeForm.drawn}-{homeForm.lost}
                  </div>
                )}
              </div>
            </div>
            <FormStrip form5={homeForm?.form5} />
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
                {awayForm && (
                  <div className="meta">
                    进 {awayForm.gf} 失 {awayForm.ga} · {awayForm.won}-{awayForm.drawn}-{awayForm.lost}
                  </div>
                )}
              </div>
              <TeamAbbr name={f.away_team} teamId={f.away_team_id} size={56} />
            </div>
            <FormStrip form5={awayForm?.form5} />
          </div>
        </div>

        <div className="md-grid">
          <div className="md-col">
            <div className="card">
              <div className="card-hdr">
                <div className="card-title">模型概率 <InfoIcon k="md.model_prob" /></div>
                <span className="card-sub">{p?.simulations ? `${p.simulations.toLocaleString()} 次模拟` : '无模型'}</span>
              </div>
              {p ? (
                <>
                  <BigBar label="主胜"     value={p.home_win_pct} kind="h" />
                  <BigBar label="平局"     value={p.draw_pct}     kind="d" />
                  <BigBar label="客胜"     value={p.away_win_pct} kind="a" />
                  <div className="divider" />
                  <BigBar label="大 2.5"   value={p.o25_pct}  kind="o" infoKey="md.bigbar.over25" />
                  <BigBar label="两队进球" value={p.btts_pct} kind="o" infoKey="md.bigbar.btts" />
                </>
              ) : <div className="empty">暂无模型数据</div>}
            </div>

            <div className="card">
              <div className="card-hdr">
                <div className="card-title">比分概率热图 <InfoIcon k="md.scoreline_heatmap" /></div>
                {ah_lines.length > 0 && (
                  <AhLineSelector
                    value={ahLine}
                    options={ah_lines.map(l => l.line)}
                    onChange={setAhLine}
                  />
                )}
              </div>
              {p
                ? <ScorelineHeatmap scorelines={p.scorelines} ahLine={ahLine} />
                : <div className="empty">无模型数据</div>}
            </div>

            <div className="card">
              <div className="card-hdr">
                <div className="card-title">亚盘全表 <InfoIcon k="md.ah_table" /></div>
                <span className="card-sub">{ah_lines.length} 条线</span>
              </div>
              <AhLineTable lines={ah_lines} />
            </div>
          </div>

          <div className="md-col">
            <div className="card">
              <div className="card-hdr">
                <div className="card-title">跌赔记录 <InfoIcon k="md.drop_records" /></div>
                <span className="card-sub">最近 24h</span>
              </div>
              {data.dropping_records.length === 0 ? (
                <div className="empty">无跌赔</div>
              ) : (
                data.dropping_records.slice(0, 20).map((d, i) => (
                  <div key={i} className="drop-row">
                    <span className="time">{new Date(d.recorded_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}</span>
                    <span className="mkt"><span className="tag-mkt">{d.market_key}</span></span>
                    <span className="pct">{Math.round(d.drop_pct)}%</span>
                    <span className="bm">{d.bookmaker}</span>
                  </div>
                ))
              )}
            </div>

            <div className="card">
              <div className="card-hdr">
                <div className="card-title">两队状态对比 <InfoIcon k="md.team_compare" /></div>
                <span className="card-sub">赛季累计</span>
              </div>
              {homeForm && awayForm ? (
                <>
                  <BigBar label="主进球" value={homeForm.gf} suffix="" kind="h" />
                  <BigBar label="客进球" value={awayForm.gf} suffix="" kind="a" />
                  <BigBar label="主失球" value={homeForm.ga} suffix="" kind="h" />
                  <BigBar label="客失球" value={awayForm.ga} suffix="" kind="a" />
                </>
              ) : <div className="empty">暂无状态数据</div>}
            </div>
          </div>
        </div>
      </div>
    </>
  )
}

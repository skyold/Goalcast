// MatchDetail. H2H section removed (no OddAlerts endpoint — see docs/frontend-data-gaps.md).
// "Two-team comparison" uses only fields available from /stats/fixture (no possession).
import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api, type FixtureDetail } from '../lib/api'
import { fmtKickoff } from '../lib/format'
import { pickZh, useT } from '../lib/i18n'
import { PredictabilityBadge } from '../components/shared/PredictabilityBadge'
import { InfoIcon } from '../components/shared/InfoIcon'
import { FormStrip } from '../components/match/FormStrip'
import { TeamAbbr } from '../components/match/TeamAbbr'
import { BigBar } from '../components/match/BigBar'
import { ScorelineHeatmap } from '../components/match/ScorelineHeatmap'   // your existing comp
import { OddsTimeseries } from '../components/match/OddsTimeseries'
import { H2HCard } from '../components/match/H2HCard'
import { AhLineSelector } from '../components/match/AhLineSelector'     // your existing comp
import { AhLineTable } from '../components/match/AhLineTable'           // your existing comp

export default function MatchDetail() {
  const { id } = useParams()
  const nav = useNavigate()
  const t = useT()
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

  if (!data) return <div className="empty">{t('md.loading')}</div>

  const f = data.fixture
  const p = data.prediction
  const ah_lines = data.odds?.asian_handicap_lines ?? []
  const ko = fmtKickoff(f.kickoff_utc)
  const homeForm = data.home_team_obj?.form
  const awayForm = data.away_team_obj?.form
  const homeName = pickZh(f.home_team_zh, f.home_team)
  const awayName = pickZh(f.away_team_zh, f.away_team)
  const compName = pickZh(f.competition_name_zh, f.competition_name)

  return (
    <>
      <div className="ph">
        <div>
          <a href="#" onClick={(e) => { e.preventDefault(); nav('/matches') }} className="card-sub" style={{ display: 'block', marginBottom: 4 }}>{t('md.back_to_matches')}</a>
          <div className="ph-title">{homeName} vs {awayName}</div>
          <div className="ph-sub">
            {compName}{f.competition_country ? ` · ${f.competition_country}` : ''} · {ko.date} {ko.day} {ko.time}
          </div>
        </div>
        <div className="ph-actions">
          <PredictabilityBadge level={f.predictability} />
          <button className="btn">{t('common.fav')}</button>
          <button className="btn btn-primary">{t('md.calculator')}</button>
        </div>
      </div>

      <div className="page">
        <div className="md-hero">
          <div className="md-team home">
            <div className="md-team-row">
              <TeamAbbr name={homeName} nameZh={f.home_team_zh} teamId={f.home_team_id} size={56} />
              <div>
                <div className="tname">{homeName}</div>
                {homeForm && (
                  <div className="meta">
                    {t('card.goals', { gf: homeForm.gf, ga: homeForm.ga })} · {homeForm.won}-{homeForm.drawn}-{homeForm.lost}
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
                <div className="tname">{awayName}</div>
                {awayForm && (
                  <div className="meta">
                    {t('card.goals', { gf: awayForm.gf, ga: awayForm.ga })} · {awayForm.won}-{awayForm.drawn}-{awayForm.lost}
                  </div>
                )}
              </div>
              <TeamAbbr name={awayName} nameZh={f.away_team_zh} teamId={f.away_team_id} size={56} />
            </div>
            <FormStrip form5={awayForm?.form5} />
          </div>
        </div>

        <div className="md-grid">
          <div className="md-col">
            <div className="card">
              <div className="card-hdr">
                <div className="card-title">{t('md.model_prob')} <InfoIcon k="md.model_prob" /></div>
                <span className="card-sub">{p?.simulations ? t('md.simulations', { n: p.simulations.toLocaleString() }) : t('md.no_model')}</span>
              </div>
              {p ? (
                <>
                  <BigBar label={t('md.prob.home_win')} value={p.home_win_pct} kind="h" />
                  <BigBar label={t('md.prob.draw')}     value={p.draw_pct}     kind="d" />
                  <BigBar label={t('md.prob.away_win')} value={p.away_win_pct} kind="a" />
                  <div className="divider" />
                  <BigBar label={t('md.prob.over25')}   value={p.o25_pct}  kind="o" infoKey="md.bigbar.over25" />
                  <BigBar label={t('md.prob.btts')}     value={p.btts_pct} kind="o" infoKey="md.bigbar.btts" />
                </>
              ) : <div className="empty">{t('md.no_model_data')}</div>}
            </div>

            <div className="card">
              <div className="card-hdr">
                <div className="card-title">{t('md.scoreline_heatmap')} <InfoIcon k="md.scoreline_heatmap" /></div>
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
                : <div className="empty">{t('md.no_model_data')}</div>}
            </div>

            <div className="card">
              <div className="card-hdr">
                <div className="card-title">{t('md.ah_table')} <InfoIcon k="md.ah_table" /></div>
                <span className="card-sub">{t('md.ah_lines_count', { n: ah_lines.length })}</span>
              </div>
              <AhLineTable lines={ah_lines} />
            </div>
          </div>

          <div className="md-col">
            <div className="card">
              <div className="card-hdr">
                <div className="card-title">{t('md.drop_records')} <InfoIcon k="md.drop_records" /></div>
                <span className="card-sub">{t('md.recent_24h')}</span>
              </div>
              {data.dropping_records.length === 0 ? (
                <div className="empty">{t('md.no_drops')}</div>
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

            <OddsTimeseries fixtureId={f.id} />

            <H2HCard fixtureId={f.id} anchorHomeTeamId={f.home_team_id} />

            <div className="card">
              <div className="card-hdr">
                <div className="card-title">{t('md.team_compare')} <InfoIcon k="md.team_compare" /></div>
                <span className="card-sub">{t('md.season_cumulative')}</span>
              </div>
              {homeForm && awayForm ? (
                <>
                  <BigBar label={t('md.compare.home_goals')}    value={homeForm.gf} suffix="" kind="h" />
                  <BigBar label={t('md.compare.away_goals')}    value={awayForm.gf} suffix="" kind="a" />
                  <BigBar label={t('md.compare.home_conceded')} value={homeForm.ga} suffix="" kind="h" />
                  <BigBar label={t('md.compare.away_conceded')} value={awayForm.ga} suffix="" kind="a" />
                </>
              ) : <div className="empty">{t('md.no_team_form')}</div>}
            </div>
          </div>
        </div>
      </div>
    </>
  )
}

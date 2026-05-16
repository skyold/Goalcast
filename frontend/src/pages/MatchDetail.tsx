import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api, type FixtureDetail } from '../lib/api'
import { PredictabilityBadge } from '../components/shared/PredictabilityBadge'
import { PredictionBars } from '../components/match/PredictionBars'
import { ScorelineHeatmap } from '../components/match/ScorelineHeatmap'
import { AhLineSelector } from '../components/match/AhLineSelector'
import { AhLineTable } from '../components/match/AhLineTable'
import { FormStrip } from '../components/match/FormStrip'

export default function MatchDetail() {
  const { id } = useParams()
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

  if (!data) return <div className="loading">加载中…</div>

  const f = data.fixture
  const ah_lines = data.odds?.asian_handicap_lines ?? []

  return (
    <div className="md">
      <section className="md-hero">
        <div className="md-hero-top">
          <PredictabilityBadge level={f.predictability} />
          <h1>{f.home_team} vs {f.away_team}</h1>
        </div>
        <div className="md-hero-meta">
          {f.competition_name} · {new Date(f.kickoff_utc).toLocaleString('zh-CN')}
        </div>
      </section>

      <section className="md-section">
        <h2>模型概率</h2>
        <PredictionBars prediction={data.prediction} />
      </section>

      <section className="md-section">
        <div className="md-section-head">
          <h2>比分概率 × 亚盘切片</h2>
          {ah_lines.length > 0 && (
            <AhLineSelector
              value={ahLine}
              options={ah_lines.map(l => l.line)}
              onChange={setAhLine}
            />
          )}
        </div>
        {data.prediction
          ? <ScorelineHeatmap scorelines={data.prediction.scorelines} ahLine={ahLine} />
          : <div className="md-empty">无模型数据</div>}
      </section>

      <section className="md-section">
        <h2>赔率全表</h2>
        <AhLineTable lines={ah_lines} />
      </section>

      <section className="md-section">
        <h2>两队状态</h2>
        <div className="md-stats">
          <div className="md-stat-col">
            <h3>{f.home_team}</h3>
            <FormStrip form5={data.home_team_obj?.form?.form5 ?? ''} />
          </div>
          <div className="md-stat-col">
            <h3>{f.away_team}</h3>
            <FormStrip form5={data.away_team_obj?.form?.form5 ?? ''} />
          </div>
        </div>
      </section>

      <section className="md-section">
        <h2>跌赔记录</h2>
        {data.dropping_records.length === 0 ? (
          <div className="md-empty">无跌赔</div>
        ) : (
          <ul className="md-drops">
            {data.dropping_records.slice(0, 20).map((d, i) => (
              <li key={i}>
                <span className="md-drop-mkt">{d.market_key}</span>
                <span className="md-drop-pct">{Math.round(d.drop_pct)}%</span>
                <span className="md-drop-bm">{d.bookmaker}</span>
                <span className="md-drop-at">{new Date(d.recorded_at).toLocaleString()}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}

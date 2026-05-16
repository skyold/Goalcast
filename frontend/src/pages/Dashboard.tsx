import { useEffect, useState } from 'react'

type Counts = { total: number; withAi: number; predMid: number }

export default function Dashboard() {
  const [counts, setCounts] = useState<Counts>({ total: 0, withAi: 0, predMid: 0 })
  const [topDrops, setTopDrops] = useState<any[]>([])

  useEffect(() => {
    Promise.all([
      fetch('/api/fixtures?limit=1').then(r => r.json()),
      fetch('/api/fixtures?limit=1&has_ai=true').then(r => r.json()),
      fetch('/api/fixtures?limit=1&predictability=high,good,medium').then(r => r.json()),
    ]).then(([a, b, c]) => setCounts({ total: a.total, withAi: b.total, predMid: c.total }))
    fetch('/api/dropping-odds?min_drop=50').then(r => r.json())
      .then(d => setTopDrops((d.items ?? []).slice(0, 5)))
  }, [])

  return (
    <div className="dash">
      <div className="dash-tiles">
        <div className="tile"><span className="tile-num">{counts.total}</span><span>未来 7 天候选</span></div>
        <div className="tile"><span className="tile-num">{counts.withAi}</span><span>有 AI 模型</span></div>
        <div className="tile"><span className="tile-num">{counts.predMid}</span><span>预测度 ≥ 一般</span></div>
      </div>
      <section className="dash-section">
        <h2>今日 Top 5 跌赔</h2>
        <ul className="top-drops">
          {topDrops.map((d, i) => (
            <li key={i}>
              <span>{d.home_team} vs {d.away_team}</span>
              <span className="drop-pct">{Math.round(d.drop_pct)}%</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}

import type { Prediction } from '../../lib/api'

type Row = { label: string; pct: number; color?: string }

function bar(r: Row, key: number) {
  return (
    <div key={key} className="pbar-row">
      <div className="pbar-label">{r.label}</div>
      <div className="pbar-track">
        <div className="pbar-fill" style={{ width: `${r.pct}%`, background: r.color ?? '#007aff' }} />
        <span className="pbar-val">{r.pct.toFixed(1)}%</span>
      </div>
    </div>
  )
}

export function PredictionBars({ prediction }: { prediction: Prediction | null }) {
  if (!prediction) {
    return <div className="pbar-empty">该场暂无 AI 模型</div>
  }
  const rows: Row[] = [
    { label: '主胜', pct: prediction.home_win_pct, color: '#22a85d' },
    { label: '平',   pct: prediction.draw_pct,     color: '#d4a017' },
    { label: '客胜', pct: prediction.away_win_pct, color: '#d24a4a' },
    { label: 'BTTS', pct: prediction.btts_pct,     color: '#7e57c2' },
    { label: 'o2.5', pct: prediction.o25_pct,      color: '#0277bd' },
    { label: 'o3.5', pct: prediction.o35_pct,      color: '#01579b' },
  ]
  return <div className="pbar">{rows.map(bar)}</div>
}

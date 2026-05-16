// History page. OddAlerts doesn't expose ROI / per-bet outcome directly — backend needs
// a bet_outcomes table (see docs/frontend-data-gaps.md #9). This component is wired to
// api.history() returning legacy fields; if your backend evolves, update the column reads.
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { PredictabilityBadge } from '../components/shared/PredictabilityBadge'

export default function History() {
  const nav = useNavigate()
  const [strategy, setStrategy] = useState('all')

  const { data, isLoading } = useQuery({
    queryKey: ['history'],
    queryFn: () => api.history({ limit: 200 }),
  })
  const items = data?.items ?? []

  const wins = items.filter((h: any) => h.result === 'W').length
  const draws = items.filter((h: any) => h.result === 'D').length
  const losses = items.filter((h: any) => h.result === 'L').length
  const winRate = items.length ? wins / items.length * 100 : 0

  return (
    <>
      <div className="ph">
        <div>
          <div className="ph-title">历史回测</div>
          <div className="ph-sub">策略表现 · {items.length} 个样本</div>
        </div>
        <div className="ph-actions">
          <button className="btn">导出 CSV</button>
          <button className="btn btn-primary">新建策略</button>
        </div>
      </div>

      <div className="page">
        <div className="kpi-grid">
          <Kpi label="总样本" value={items.length} sub={`${wins}胜 ${draws}平 ${losses}负`} />
          <Kpi label="胜率" value={`${winRate.toFixed(0)}%`} sub="vs 上周期" />
          <Kpi label="ROI" value="—" sub="待后端 bet_outcomes 表" />
          <Kpi label="平均 Edge" value="—" sub="待后端聚合" />
        </div>

        <div className="filters" style={{ borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', marginBottom: 'var(--gap-grid)' }}>
          <div className="filter-grp">
            <span className="filter-lbl">策略</span>
            {[['all','全部'], ['drop','高跌幅'], ['value','高 Edge'], ['high','高可预测']].map(([k, l]) => (
              <button key={k} className={`chip${strategy === k ? ' active' : ''}`} onClick={() => setStrategy(k)}>{l}</button>
            ))}
          </div>
        </div>

        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          {isLoading && <div className="empty">加载中…</div>}
          {!isLoading && items.length === 0 && <div className="empty">无历史数据</div>}
          {items.length > 0 && (
            <table className="ht">
              <thead>
                <tr>
                  <th>日期</th>
                  <th>联赛</th>
                  <th>比赛</th>
                  <th style={{ textAlign: 'center' }}>比分</th>
                  <th style={{ textAlign: 'center' }}>跌幅</th>
                  <th style={{ textAlign: 'center' }}>预测度</th>
                  <th style={{ textAlign: 'center' }}>结果</th>
                </tr>
              </thead>
              <tbody>
                {items.map((h: any) => (
                  <tr key={h.id} onClick={() => nav(`/matches/${h.id}`)}>
                    <td className="num">{h.kickoff_utc?.slice(5, 10) ?? ''}</td>
                    <td>{h.competition_name}</td>
                    <td className="match">{h.home_team} vs {h.away_team}</td>
                    <td className="score" style={{ textAlign: 'center' }}>
                      {h.score_home ?? '-'}-{h.score_away ?? '-'}
                    </td>
                    <td className="num" style={{ textAlign: 'center', color: 'var(--acc)', fontWeight: 700 }}>
                      {h.drop_pct != null ? `${Math.round(h.drop_pct)}%` : '—'}
                    </td>
                    <td style={{ textAlign: 'center' }}><PredictabilityBadge level={h.predictability} /></td>
                    <td className={`r${h.result ?? ''}`} style={{ textAlign: 'center' }}>
                      {h.result === 'W' ? '✓ 赢' : h.result === 'L' ? '✗ 输' : h.result === 'D' ? '◯ 走' : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </>
  )
}

function Kpi({ label, value, sub }: { label: string; value: string | number; sub: string }) {
  return (
    <div className="kpi">
      <span className="kpi-lbl">{label}</span>
      <span className="kpi-val">{value}</span>
      <span className="kpi-delta">{sub}</span>
    </div>
  )
}

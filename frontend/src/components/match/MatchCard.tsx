import type { FixtureSummary } from '../../lib/api'
import { PredictabilityBadge } from '../shared/PredictabilityBadge'
import { FormStrip } from './FormStrip'
import { OddsPair } from './OddsPair'

type Props = { fixture: FixtureSummary; onClick?: () => void }

const fmtKO = (iso: string) => {
  const d = new Date(iso)
  return d.toLocaleString('zh-CN', { weekday: 'short', month: 'numeric', day: 'numeric',
                                       hour: '2-digit', minute: '2-digit' })
}

export function MatchCard({ fixture, onClick }: Props) {
  const ps = fixture.prediction_summary
  const ah = fixture.odds?.asian_handicap
  const ft = fixture.odds?.ft_result
  return (
    <div className="mc" role="button" tabIndex={0} onClick={onClick}
         onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onClick?.() }}>
      <div className="mc-head">
        <PredictabilityBadge level={fixture.predictability} />
        <span className="mc-teams">
          <strong>{fixture.home_team}</strong> vs <strong>{fixture.away_team}</strong>
        </span>
        {fixture.drop_flag && (
          <span className={`mc-drop ${fixture.drop_flag.drop_percentage >= 50 ? 'mc-drop-alert' : ''}`}>
            跌 {-Math.round(fixture.drop_flag.drop_percentage)}%
          </span>
        )}
      </div>
      <div className="mc-meta">
        {fixture.competition_name} · {fixture.competition_country ?? ''} · {fmtKO(fixture.kickoff_utc)}
      </div>

      <div className="mc-form">
        <span className="mc-form-label">FORM</span>
        <FormStrip form5={fixture.home_form?.form5 ?? ''} />
        <span className="mc-form-sep">·</span>
        <FormStrip form5={fixture.away_form?.form5 ?? ''} />
      </div>

      {ps && (
        <div className="mc-ai">
          <span className="mc-ai-label">AI</span>
          <span>主 {ps.home_win_pct.toFixed(1)}%</span>
          <span>平 {ps.draw_pct.toFixed(1)}%</span>
          <span>客 {ps.away_win_pct.toFixed(1)}%</span>
          <span className="mc-ai-extra">o2.5: {ps.o25_pct.toFixed(1)}%</span>
        </div>
      )}

      <div className="mc-odds">
        <OddsPair
          label="1x2"
          pinnacle={ft?.pinnacle ? { home: ft.pinnacle.home, draw: ft.pinnacle.draw ?? null, away: ft.pinnacle.away } : null}
          bet365={ft?.bet365 ? { home: ft.bet365.home, draw: ft.bet365.draw ?? null, away: ft.bet365.away } : null}
        />
        {ah ? (
          <OddsPair
            label={`AH ${ah.line > 0 ? '+' : ''}${ah.line}`}
            pinnacle={{ home: ah.pinnacle.home_odds, away: ah.pinnacle.away_odds }}
            bet365={ah.bet365 ? { home: ah.bet365.home_odds, away: ah.bet365.away_odds } : null}
            showDraw={false}
          />
        ) : (
          <div className="mc-no-ah">— 无亚盘 —</div>
        )}
      </div>
    </div>
  )
}

// Default export alias for backward-compat with Matches.tsx (default import)
export default MatchCard

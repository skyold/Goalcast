import type { FixtureSummary } from '../../lib/api'
import { fmtKickoff } from '../../lib/format'
import { PredictabilityBadge } from '../shared/PredictabilityBadge'
import { FormStrip } from './FormStrip'
import { TeamAbbr } from './TeamAbbr'
import { ProbBar } from './ProbBar'

interface Props {
  fixture: FixtureSummary
  homeTeamId?: number | null
  awayTeamId?: number | null
  onClick?: () => void
}

export function MatchCard({ fixture, homeTeamId, awayTeamId, onClick }: Props) {
  const ko = fmtKickoff(fixture.kickoff_utc)
  const ps = fixture.prediction_summary
  const ft = fixture.odds?.ft_result?.pinnacle ?? null
  const dropPct = fixture.drop_flag?.drop_percentage ?? null
  const hf = fixture.home_form
  const af = fixture.away_form

  return (
    <div
      className="mc"
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onClick?.() }}
    >
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
            <TeamAbbr name={fixture.home_team} teamId={homeTeamId} />
            <span className="mc-tname">{fixture.home_team}</span>
          </div>
          {hf && (
            <span className="mc-rank">
              进 {hf.gf} 失 {hf.ga} · {hf.won}胜{hf.drawn}平{hf.lost}负
            </span>
          )}
          <FormStrip form5={hf?.form5} />
        </div>

        <div className="mc-vs">
          <div className="mc-vs-time">{ko.time}</div>
          <div className="mc-vs-day">{ko.date}</div>
          <div className="mc-vs-vs">VS</div>
        </div>

        <div className="mc-team away">
          <div className="mc-namerow">
            <TeamAbbr name={fixture.away_team} teamId={awayTeamId} />
            <span className="mc-tname">{fixture.away_team}</span>
          </div>
          {af && (
            <span className="mc-rank">
              进 {af.gf} 失 {af.ga} · {af.won}胜{af.drawn}平{af.lost}负
            </span>
          )}
          <FormStrip form5={af?.form5} />
        </div>
      </div>

      {ps && <ProbBar h={ps.home_win_pct} d={ps.draw_pct} a={ps.away_win_pct} />}

      <div className="mc-ftr">
        <div className="odds-box">
          <div className={`ob${ps && ps.home_win_pct > 45 ? ' hot' : ''}`}>
            <div className="ol">主</div>
            <div className="ov">{ft?.home?.toFixed(2) ?? '—'}</div>
          </div>
          <div className="ob">
            <div className="ol">平</div>
            <div className="ov">{ft?.draw?.toFixed(2) ?? '—'}</div>
          </div>
          <div className={`ob${ps && ps.away_win_pct > 45 ? ' hot' : ''}`}>
            <div className="ol">客</div>
            <div className="ov">{ft?.away?.toFixed(2) ?? '—'}</div>
          </div>
        </div>
        {dropPct != null && (
          <>
            <div className="ftr-sep" />
            <div className={`drop-tag${dropPct >= 60 ? '' : ' warn'}`}>
              <span className="arr">▼</span>
              <span>{Math.round(dropPct)}%</span>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default MatchCard

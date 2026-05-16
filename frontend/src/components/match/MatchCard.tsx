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
  // Prefer API-provided zh names (seeded for top leagues); fall back to upstream English.
  const homeName = fixture.home_team_zh ?? fixture.home_team
  const awayName = fixture.away_team_zh ?? fixture.away_team
  const compName = fixture.competition_name_zh ?? fixture.competition_name
  const homeRank = fixture.home_rank ?? null
  const awayRank = fixture.away_rank ?? null

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
          <span>{compName}</span>
        </div>
        <div className="mc-time">
          <span className="day">{ko.day}</span>
          <span>{ko.time}</span>
        </div>
      </div>

      <div className="mc-body">
        <div className="mc-team home">
          <div className="mc-namerow">
            <TeamAbbr name={homeName} teamId={homeTeamId} />
            <span className="mc-tname">{homeName}</span>
          </div>
          {(hf || homeRank != null) && (
            <span className="mc-rank">
              {homeRank != null && <>排名 #{homeRank}{hf && ' · '}</>}
              {hf && <>进 {hf.gf} 失 {hf.ga}</>}
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
            <TeamAbbr name={awayName} teamId={awayTeamId} />
            <span className="mc-tname">{awayName}</span>
          </div>
          {(af || awayRank != null) && (
            <span className="mc-rank">
              {awayRank != null && <>排名 #{awayRank}{af && ' · '}</>}
              {af && <>进 {af.gf} 失 {af.ga}</>}
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

import type { FixtureSummary } from '../../lib/api'
import { fmtKickoff } from '../../lib/format'
import { PredictabilityBadge } from '../shared/PredictabilityBadge'
import { Tooltip } from '../shared/Tooltip'
import { gloss } from '../../lib/glossary'
import { useT, pickZh } from '../../lib/i18n'
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
  const t = useT()
  const ko = fmtKickoff(fixture.kickoff_utc)
  const ps = fixture.prediction_summary
  const ft = fixture.odds?.ft_result?.pinnacle ?? null
  const dropPct = fixture.drop_flag?.drop_percentage ?? null
  const hf = fixture.home_form
  const af = fixture.away_form
  // pickZh is locale-aware (returns zh under zh-locale, en under en-locale).
  // useT() above subscribes us to locale changes so this re-runs on switch.
  const homeName = pickZh(fixture.home_team_zh, fixture.home_team)
  const awayName = pickZh(fixture.away_team_zh, fixture.away_team)
  const compName = pickZh(fixture.competition_name_zh, fixture.competition_name)
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
              {homeRank != null && (
                <Tooltip content={gloss('mc.rank')}>
                  <span className="gc-seg" tabIndex={0}>{t('card.rank', { n: homeRank })}</span>
                </Tooltip>
              )}
              {homeRank != null && hf && ' · '}
              {hf && (
                <Tooltip content={gloss('mc.goals')}>
                  <span className="gc-seg" tabIndex={0}>{t('card.goals', { gf: hf.gf, ga: hf.ga })}</span>
                </Tooltip>
              )}
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
              {awayRank != null && (
                <Tooltip content={gloss('mc.rank')}>
                  <span className="gc-seg" tabIndex={0}>{t('card.rank', { n: awayRank })}</span>
                </Tooltip>
              )}
              {awayRank != null && af && ' · '}
              {af && (
                <Tooltip content={gloss('mc.goals')}>
                  <span className="gc-seg" tabIndex={0}>{t('card.goals', { gf: af.gf, ga: af.ga })}</span>
                </Tooltip>
              )}
            </span>
          )}
          <FormStrip form5={af?.form5} />
        </div>
      </div>

      {ps && <ProbBar h={ps.home_win_pct} d={ps.draw_pct} a={ps.away_win_pct} />}

      <div className="mc-ftr">
        <div className="odds-box">
          <Tooltip content={gloss('mc.odds.home')}>
            <div className={`ob${ps && ps.home_win_pct > 45 ? ' hot' : ''}`} tabIndex={0}>
              <div className="ol">{t('card.home')}</div>
              <div className="ov">{ft?.home?.toFixed(2) ?? '—'}</div>
            </div>
          </Tooltip>
          <Tooltip content={gloss('mc.odds.draw')}>
            <div className="ob" tabIndex={0}>
              <div className="ol">{t('card.draw')}</div>
              <div className="ov">{ft?.draw?.toFixed(2) ?? '—'}</div>
            </div>
          </Tooltip>
          <Tooltip content={gloss('mc.odds.away')}>
            <div className={`ob${ps && ps.away_win_pct > 45 ? ' hot' : ''}`} tabIndex={0}>
              <div className="ol">{t('card.away')}</div>
              <div className="ov">{ft?.away?.toFixed(2) ?? '—'}</div>
            </div>
          </Tooltip>
        </div>
        {dropPct != null && (
          <>
            <div className="ftr-sep" />
            <Tooltip content={gloss('mc.drop')}>
              <div className={`drop-tag${dropPct >= 60 ? '' : ' warn'}`} tabIndex={0}>
                <span className="arr">▼</span>
                <span>{Math.round(dropPct)}%</span>
              </div>
            </Tooltip>
          </>
        )}
      </div>
    </div>
  )
}

export default MatchCard

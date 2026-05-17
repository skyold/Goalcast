import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { fmtKickoff } from '../lib/format'
import { pickZh, useT, useLocale } from '../lib/i18n'
import MatchCard from '../components/match/MatchCard'
import { BigBar } from '../components/match/BigBar'
import { Spark } from '../components/shared/Spark'
import { InfoIcon } from '../components/shared/InfoIcon'
import type { GlossaryKey } from '../lib/glossary'

export default function Dashboard() {
  const nav = useNavigate()
  const t = useT()
  const locale = useLocale()

  // Three counts, all served by /fixtures with cheap filters.
  const { data: totalRes } = useQuery({
    queryKey: ['fix-count', 'total'],
    queryFn: () => api.fixtures({ limit: 1 }),
  })
  const { data: aiRes } = useQuery({
    queryKey: ['fix-count', 'ai'],
    queryFn: () => api.fixtures({ limit: 1, has_ai: true }),
  })
  const { data: predRes } = useQuery({
    queryKey: ['fix-count', 'pred'],
    queryFn: () => api.fixtures({ limit: 1, predictability: 'high,good,medium' }),
  })
  const { data: dropRes } = useQuery({
    queryKey: ['drop-top'],
    queryFn: () => api.droppingOdds({ min_drop: 50 }),
  })
  const { data: valueRes } = useQuery({
    queryKey: ['value-top'],
    queryFn: () => api.valueBets({ min_edge: 5 }),
  })
  const { data: upcomingRes } = useQuery({
    queryKey: ['fix-upcoming'],
    queryFn: () => api.fixtures({ limit: 4 }),
  })

  const total = totalRes?.total ?? 0
  const withAi = aiRes?.total ?? 0
  const pred = predRes?.total ?? 0
  const drops = dropRes?.items?.slice(0, 5) ?? []
  const values = valueRes?.items?.slice(0, 5) ?? []
  const upcoming = upcomingRes?.fixtures ?? []

  return (
    <>
      <div className="ph">
        <div>
          <div className="ph-title">{t('dash.title')}</div>
          <div className="ph-sub">{t('dash.subtitle_next_7')} · {new Date().toLocaleDateString(locale === 'en' ? 'en-US' : 'zh-CN', { month: 'long', day: 'numeric', weekday: 'long' })}</div>
        </div>
        <div className="ph-actions">
          <button className="btn">{t('common.export')}</button>
          <button className="btn btn-primary" onClick={() => api.triggerSync()}>{t('dash.btn_sync')}</button>
        </div>
      </div>

      <div className="page">
        <div className="kpi-grid">
          <Kpi label={t('dash.kpi.candidates')}      value={total}        delta={t('dash.kpi.delta_yesterday', { n: 3 })}                                       spark={[8, 10, 9, 11, 13, 12, 13]} color="var(--acc)"   infoKey="dash.candidates" />
          <Kpi label={t('dash.kpi.ai_modeled')}      value={withAi}       delta={t('dash.kpi.coverage_pct', { n: total ? Math.round(withAi/total*100) : 0 })}   spark={[6, 7, 8, 9, 10, 11, withAi]} color="var(--acc-3)" infoKey="dash.ai_modeled" />
          <Kpi label={t('dash.kpi.drop_high')}       value={drops.length} delta={t('dash.kpi.drop_alerts', { n: drops.length })}                                 spark={[2, 3, 4, 3, 5, 6, drops.length]} color="var(--acc-2)" infoKey="dash.drop_high" />
          <Kpi label={t('dash.kpi.predictability_ok')} value={pred}       delta={t('dash.kpi.coverage')}                                                         spark={[55, 58, 53, 60, 58, 61, pred]} color="var(--acc)"   infoKey="dash.predictability" />
        </div>

        <div className="dash-grid">
          <div className="dash-col">
            <div className="card">
              <div className="card-hdr">
                <div className="card-title">{t('dash.top_drops')} <InfoIcon k="dash.top_drops" /></div>
                <a className="card-sub" href="#" onClick={(e) => { e.preventDefault(); nav('/dropping') }}>{t('common.view_all')} →</a>
              </div>
              {drops.map((d, i) => {
                const ko = fmtKickoff(d.kickoff_utc)
                return (
                  <div key={i} className="alert-row" onClick={() => nav(`/matches/${d.fixture_id}`)}>
                    <div className="alert-pct">{Math.round(d.drop_pct ?? 0)}%</div>
                    <div className="alert-mid">
                      <div className="alert-match">{pickZh(d.home_team_zh, d.home_team)} vs {pickZh(d.away_team_zh, d.away_team)}</div>
                      <div className="alert-meta">{pickZh(d.competition_name_zh, d.competition_name)} · {ko.day} {ko.time} · {d.bookmaker}</div>
                    </div>
                  </div>
                )
              })}
              {drops.length === 0 && <div className="empty">{t('dash.empty.drops')}</div>}
            </div>

            <div className="card">
              <div className="card-hdr">
                <div className="card-title">{t('dash.upcoming')} <InfoIcon k="dash.upcoming" /></div>
                <a className="card-sub" href="#" onClick={(e) => { e.preventDefault(); nav('/matches') }}>{t('common.view_all')} →</a>
              </div>
              <div className="match-grid">
                {upcoming.map(f => (
                  <MatchCard key={f.id} fixture={f} onClick={() => nav(`/matches/${f.id}`)} />
                ))}
              </div>
            </div>
          </div>

          <div className="dash-col">
            <div className="card">
              <div className="card-hdr">
                <div className="card-title">{t('dash.value_bets')} <InfoIcon k="dash.value_bets" /></div>
                <a className="card-sub" href="#" onClick={(e) => { e.preventDefault(); nav('/value-bets') }}>{t('common.view_all')} →</a>
              </div>
              {values.map((v, i) => {
                const ko = fmtKickoff(v.kickoff_utc)
                return (
                  <div key={i} className="alert-row" onClick={() => nav(`/matches/${v.fixture_id}`)}>
                    <div className="alert-pct" style={{ color: 'var(--acc-2)' }}>+{v.edge_pct.toFixed(1)}%</div>
                    <div className="alert-mid">
                      <div className="alert-match">{pickZh(v.home_team_zh, v.home_team)} vs {pickZh(v.away_team_zh, v.away_team)}</div>
                      <div className="alert-meta">{pickZh(v.competition_name_zh, v.competition_name)} · {ko.day} {ko.time} · {v.selection} @ {v.odds.toFixed(2)}</div>
                    </div>
                  </div>
                )
              })}
              {values.length === 0 && <div className="empty">{t('dash.empty.values')}</div>}
            </div>

            <div className="card">
              <div className="card-hdr">
                <div className="card-title">{t('dash.health')} <InfoIcon k="dash.health" /></div>
                <span className="card-sub">{t('dash.health.sub')}</span>
              </div>
              {/* TODO: hook to a real /api/health endpoint when available */}
              <BigBar label={t('dash.health.odds')}           value={total ? Math.round((dropRes?.items?.length ?? 0) > 0 ? 90 : 60) : 0} kind="h" />
              <BigBar label={t('dash.health.model')}          value={total ? Math.round(withAi / total * 100) : 0}                       kind="a" />
              <BigBar label={t('dash.health.predictability')} value={total ? Math.round(pred / total * 100) : 0}                         kind="o" />
            </div>
          </div>
        </div>
      </div>
    </>
  )
}

function Kpi({ label, value, delta, spark, color, infoKey }: {
  label: string; value: number | string; delta: string; spark: number[]; color: string; infoKey?: GlossaryKey
}) {
  return (
    <div className="kpi">
      <span className="kpi-lbl">
        {label}
        {infoKey && <InfoIcon k={infoKey} />}
      </span>
      <span className="kpi-val">{value}</span>
      <span className="kpi-delta">{delta}</span>
      <Spark values={spark} color={color} />
    </div>
  )
}

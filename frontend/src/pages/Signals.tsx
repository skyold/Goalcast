// Unified Goalcast Signals view — single landing for all proprietary
// derivatives (mispricing / line move / sharp-square disagreement etc.).
//
// Tab "All" calls /signals/active (ranked across types). Other tabs filter
// to a specific signal_type. All views default to upcoming fixtures only;
// strength threshold tunable via chips.
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api, type SignalItem } from '../lib/api'
import { fmtKickoff } from '../lib/format'
import { pickZh, useT } from '../lib/i18n'

const TABS = [
  { key: 'all',             label: 'All' },
  { key: 'GS-Mispricing',   label: 'Mispricing' },
  { key: 'GS-LineMove',     label: 'LineMove' },
  { key: 'GS-SharpSquare',  label: 'SharpSquare' },
  { key: 'GS-KEN-HT-EV',       label: 'HT-EV' },
] as const

const STRENGTH_CHIPS = [0.3, 0.5, 0.7] as const

export default function Signals() {
  const t = useT()
  const [tab, setTab] = useState<typeof TABS[number]['key']>('all')
  const [minStrength, setMinStrength] = useState<number>(0.5)

  const { data, isLoading } = useQuery({
    queryKey: ['signals', tab, minStrength],
    queryFn: () =>
      tab === 'all'
        ? api.signals.active({ min_strength: minStrength, limit: 100 })
        : api.signals.byType(tab, { min_strength: minStrength, limit: 100 }),
    staleTime: 60_000,
  })
  const items = data?.items ?? []

  return (
    <>
      <div className="ph">
        <div>
          <div className="ph-title">{t('signals.title')}</div>
          <div className="ph-sub">{t('signals.subtitle')} · {items.length}</div>
        </div>
      </div>

      <div className="filters">
        <div className="filter-grp">
          <span className="filter-lbl">{t('signals.filter.type')}</span>
          {TABS.map(tb => (
            <button key={tb.key}
              className={`chip${tab === tb.key ? ' active' : ''}`}
              onClick={() => setTab(tb.key)}
            >{t(`signals.tab.${tb.key === 'all' ? 'all' : tb.key.replace('GS-', '').toLowerCase()}`)}</button>
          ))}
        </div>
        <div className="filter-grp">
          <span className="filter-lbl">{t('signals.filter.min_strength')}</span>
          {STRENGTH_CHIPS.map(v => (
            <button key={v}
              className={`chip${minStrength === v ? ' active' : ''}`}
              onClick={() => setMinStrength(v)}
            >≥ {(v * 100).toFixed(0)}%</button>
          ))}
        </div>
      </div>

      <div className="page">
        {isLoading && <div className="empty">{t('signals.loading')}</div>}
        {!isLoading && items.length === 0 && (
          <div className="empty">{t('signals.empty')}</div>
        )}
        {items.length > 0 && <SignalsTable items={items} t={t} />}
      </div>
    </>
  )
}

function SignalsTable({ items, t }: { items: SignalItem[]; t: (k: string, v?: any) => string }) {
  const nav = useNavigate()
  return (
    <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
      <table className="ht">
        <thead>
          <tr>
            <th>{t('signals.col.match')}</th>
            <th>{t('signals.col.signal')}</th>
            <th>{t('signals.col.detail')}</th>
            <th style={{ textAlign: 'right' }}>{t('signals.col.strength')}</th>
            <th>{t('signals.col.waypoint')}</th>
          </tr>
        </thead>
        <tbody>
          {items.map((s, i) => (
            <SignalRow
              key={`${s.signal_type}-${s.fixture_id}-${s.waypoint}-${i}`}
              s={s}
              t={t}
              onClick={() => nav(`/matches/${s.fixture_id}`)}
            />
          ))}
        </tbody>
      </table>
    </div>
  )
}

function SignalRow({ s, t, onClick }: { s: SignalItem; t: (k: string, v?: any) => string; onClick: () => void }) {
  const ko = s.kickoff_utc ? fmtKickoff(s.kickoff_utc) : { day: '', time: '' }
  const strength = s.strength ?? 0
  const barColor =
    strength >= 0.7 ? 'var(--acc)' :
    strength >= 0.5 ? 'var(--warn, #d97706)' :
                      'var(--text-mute)'
  return (
    <tr onClick={onClick} style={{ cursor: 'pointer' }}>
      <td className="match">
        <div>{pickZh(s.home_team_zh, s.home_team ?? '')} vs {pickZh(s.away_team_zh, s.away_team ?? '')}</div>
        <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-mute)' }}>
          {pickZh(s.competition_name_zh, s.competition_name ?? '') || `#${s.competition_id}`} · {ko.day} {ko.time}
        </div>
      </td>
      <td>
        <span style={{ fontWeight: 600 }}>{s.signal_type.replace('GS-', '')}</span>
        <span style={{ marginLeft: 6, fontSize: 'var(--fs-xs)', color: 'var(--text-mute)' }}>{s.signal_version ?? ''}</span>
        {s.scope === 'member' && (
          <span style={{ marginLeft: 6, padding: '0 6px', fontSize: 'var(--fs-xs)',
                          border: '1px solid var(--text-mute)', borderRadius: 999, color: 'var(--text-mute)' }}>
            {t('signals.scope.member')}
          </span>
        )}
      </td>
      <td><SignalDetail s={s} /></td>
      <td style={{ textAlign: 'right', minWidth: 130 }}>
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', alignItems: 'center' }}>
          <div style={{ width: 80, height: 6, background: 'var(--bg-mute)', borderRadius: 999, overflow: 'hidden' }}>
            <div style={{ width: `${(strength * 100).toFixed(0)}%`, height: '100%', background: barColor }} />
          </div>
          <span className="num" style={{ minWidth: 36 }}>{(strength * 100).toFixed(0)}%</span>
        </div>
      </td>
      <td>{s.waypoint}</td>
    </tr>
  )
}

function SignalDetail({ s }: { s: SignalItem }) {
  const t = useT()
  const v = s.value as Record<string, any>
  const sel = v.selection as string | undefined
  switch (s.signal_type) {
    case 'GS-Mispricing': {
      const delta = v.delta_pct as number | undefined
      const sign = delta == null ? '' : (delta > 0 ? '+' : '')
      const color = delta == null ? undefined : delta > 0 ? 'var(--acc)' : 'var(--neg)'
      return (
        <span>
          {sel} · <span style={{ color, fontWeight: 600 }}>{delta == null ? '—' : `${sign}${delta.toFixed(1)}%`}</span>
        </span>
      )
    }
    case 'GS-LineMove': {
      const mv = v.move_pct as number | undefined
      const sign = mv == null ? '' : (mv > 0 ? '+' : '')
      const color = mv == null ? undefined : mv < 0 ? 'var(--acc)' : 'var(--neg)'
      const open = v.open_odds as number | undefined
      const curr = v.current_odds as number | undefined
      return (
        <span>
          {sel} · {open?.toFixed(2)} → {curr?.toFixed(2)}{' '}
          <span style={{ color, fontWeight: 600 }}>{mv == null ? '' : `(${sign}${mv.toFixed(1)}%)`}</span>
        </span>
      )
    }
    case 'GS-SharpSquare': {
      const delta = v.delta_pct as number | undefined
      const sign = delta == null ? '' : (delta > 0 ? '+' : '')
      const pin = v.pinnacle_pct as number | undefined
      const b65 = v.bet365_pct  as number | undefined
      return (
        <span>
          {sel} · Pin {pin?.toFixed(1)}% vs 365 {b65?.toFixed(1)}% · {sign}{delta?.toFixed(1)}%
        </span>
      )
    }
    case 'GS-KEN-HT-EV': {
      const ahLabel = v.ah_label as string | undefined
      const hk5  = sel === 'home' ? v.hk_home_5  : v.hk_away_5
      const hk28 = sel === 'home' ? v.hk_home_28 : v.hk_away_28
      const ah = ahLabel ? t(`signals.ht_ev.ah.${ahLabel}`) : '—'
      return (
        <span>
          {sel} · {ah} · HK <span style={{ fontWeight: 600 }}>{hk5?.toFixed(2)}→{hk28?.toFixed(2)}</span>
        </span>
      )
    }
    default:
      return <span style={{ color: 'var(--text-mute)' }}>{JSON.stringify(v)}</span>
  }
}

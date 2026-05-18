// Compare mode — N signals laid out as rows of a single table for side-by-side
// evaluation of methodology + 7d activity. Phase 2 of the signal-catalog PRD.
//
// Columns: name+scope · description · strength formula · 7d triggered · 7d avg
//          strength · 7d max strength · failure modes count · methodology updated.
//
// Clicking a row sets the master-detail selection back to that signal_type
// (caller passes onSelect). Hit rate / House Book ROI columns wait for
// Phase 3 / Phase 4 — currently we have no FT-outcome attribution per signal.
import { type SignalCatalogItem } from '../../lib/api'
import { useT } from '../../lib/i18n'

export default function CompareTable({
  items, onSelect,
}: {
  items: SignalCatalogItem[]
  onSelect: (signal_type: string) => void
}) {
  const t = useT()
  return (
    <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
      <table className="ht" style={{ width: '100%' }}>
        <thead>
          <tr>
            <th>{t('signals.compare.col.signal')}</th>
            <th>{t('signals.compare.col.description')}</th>
            <th>{t('signals.compare.col.strength_formula')}</th>
            <th style={{ textAlign: 'right' }}>{t('signals.compare.col.triggered_7d')}</th>
            <th style={{ textAlign: 'right' }}>{t('signals.compare.col.avg_strength_7d')}</th>
            <th style={{ textAlign: 'right' }}>{t('signals.compare.col.max_strength_7d')}</th>
            <th style={{ textAlign: 'right' }}>{t('signals.compare.col.failure_count')}</th>
            <th>{t('signals.compare.col.updated')}</th>
          </tr>
        </thead>
        <tbody>
          {items.map(c => (
            <tr key={c.signal_type}
                onClick={() => onSelect(c.signal_type)}
                style={{ cursor: 'pointer' }}
            >
              <td>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
                  <span style={{ fontWeight: 600 }}>{c.signal_type.replace(/^GS-/, '')}</span>
                  <span style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-mute)' }}>{c.signal_version}</span>
                  {c.scope === 'member' && (
                    <span style={{
                      padding: '0 6px', fontSize: 'var(--fs-xs)',
                      border: '1px solid var(--text-mute)', borderRadius: 999, color: 'var(--text-mute)',
                    }}>{t('signals.scope.member')}</span>
                  )}
                </div>
              </td>
              <td style={{ fontSize: 13, color: 'var(--text-mute)' }}>{c.description}</td>
              <td>
                <code style={{
                  display: 'inline-block', padding: '2px 6px',
                  background: 'var(--bg-mute)', borderRadius: 4, fontSize: 12,
                }}>{c.strength_formula}</code>
              </td>
              <td className="num" style={{ textAlign: 'right' }}>
                {c.stats_7d ? c.stats_7d.triggered : '—'}
              </td>
              <td className="num" style={{ textAlign: 'right' }}>
                {c.stats_7d?.avg_strength != null
                  ? `${Math.round(c.stats_7d.avg_strength * 100)}%`
                  : '—'}
              </td>
              <td className="num" style={{ textAlign: 'right' }}>
                {c.stats_7d?.max_strength != null
                  ? `${Math.round(c.stats_7d.max_strength * 100)}%`
                  : '—'}
              </td>
              <td className="num" style={{ textAlign: 'right' }}>
                {c.failure_modes.length}
              </td>
              <td style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-mute)' }}>
                {c.methodology_updated_at ? c.methodology_updated_at.slice(0, 10) : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

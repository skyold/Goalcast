// Right pane of the /insights/signals master-detail layout. Shows the
// full methodology for one signal: ClassVar metadata (description / formula /
// output schema / failure modes) on top, then the markdown body below.
//
// Phase 1 of docs/PRD/signal-catalog-and-subscriptions.prd.md.
// Phase 3 adds the "Backtest" CTA in the header.
import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { type SignalCatalogItem } from '../../lib/api'
import { useT } from '../../lib/i18n'
import BacktestModal from './BacktestModal'

export default function MethodologyPanel({ item }: { item: SignalCatalogItem }) {
  const t = useT()
  const [backtestOpen, setBacktestOpen] = useState(false)
  // Strip GS- prefix for display, keeping any sub-namespace (e.g. KEN-).
  const shortName = item.signal_type.replace(/^GS-/, '')
  return (
    <div className="card" style={{ padding: 20 }}>
      <header style={{ display: 'flex', alignItems: 'baseline', gap: 12, marginBottom: 4 }}>
        <h2 style={{ margin: 0, fontSize: 22, fontWeight: 700 }}>{shortName}</h2>
        <span style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-mute)' }}>
          {item.signal_version}
        </span>
        {item.scope === 'member' && (
          <span style={{
            padding: '2px 8px', fontSize: 'var(--fs-xs)',
            border: '1px solid var(--text-mute)', borderRadius: 999, color: 'var(--text-mute)',
          }}>
            {t('signals.scope.member')}
          </span>
        )}
        <button
          className="chip active"
          onClick={() => setBacktestOpen(true)}
          style={{ marginLeft: 'auto' }}
        >
          {t('signals.backtest.open')}
        </button>
      </header>

      <p style={{ margin: '4px 0 16px', color: 'var(--text-mute)', fontSize: 14 }}>
        {item.description}
      </p>

      {/* Strength formula highlighted as a code block — the single most
          actionable piece of info for a comparing user. */}
      <section style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-mute)', marginBottom: 4 }}>
          {t('signals.method.strength_formula')}
        </div>
        <code style={{
          display: 'inline-block', padding: '4px 8px',
          background: 'var(--bg-mute)', borderRadius: 4, fontSize: 13,
        }}>{item.strength_formula}</code>
      </section>

      {/* Output schema — field name → semantics. Lays groundwork for users to
          understand the JSON they see in the fixture table on the same page. */}
      {Object.keys(item.output_schema).length > 0 && (
        <section style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-mute)', marginBottom: 4 }}>
            {t('signals.method.output_schema')}
          </div>
          <table className="ht" style={{ width: '100%', fontSize: 13 }}>
            <tbody>
              {Object.entries(item.output_schema).map(([field, doc]) => (
                <tr key={field}>
                  <td style={{ fontFamily: 'monospace', width: '30%', whiteSpace: 'nowrap' }}>{field}</td>
                  <td style={{ color: 'var(--text-mute)' }}>{doc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {/* Failure modes — when does this signal NOT fire / when to not trust. */}
      {item.failure_modes.length > 0 && (
        <section style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-mute)', marginBottom: 4 }}>
            {t('signals.method.failure_modes')}
          </div>
          <ul style={{ margin: 0, paddingLeft: 20, fontSize: 13 }}>
            {item.failure_modes.map((f, i) => <li key={i}>{f}</li>)}
          </ul>
        </section>
      )}

      {/* Long-form methodology body. The seed script writes a multi-section
          markdown with ## 计算原理 / ### 输入 / ### 公式 / ### 何时使用 /
          ### 何时不使用 — react-markdown renders headings + code + lists
          out of the box. */}
      <section className="methodology-md" style={{ fontSize: 14, lineHeight: 1.6 }}>
        {item.methodology_md ? (
          <ReactMarkdown>{item.methodology_md}</ReactMarkdown>
        ) : (
          <p style={{ color: 'var(--text-mute)', fontStyle: 'italic' }}>
            {t('signals.method.no_methodology')}
          </p>
        )}
      </section>

      {item.methodology_updated_at && (
        <footer style={{
          marginTop: 16, fontSize: 'var(--fs-xs)', color: 'var(--text-mute)',
          textAlign: 'right',
        }}>
          {t('signals.method.updated_at')}: {item.methodology_updated_at.slice(0, 10)}
        </footer>
      )}

      {backtestOpen && (
        <BacktestModal
          signal_type={item.signal_type}
          onClose={() => setBacktestOpen(false)}
        />
      )}
    </div>
  )
}

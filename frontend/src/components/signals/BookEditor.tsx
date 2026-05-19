// Book editor modal — Phase 4c of signal-catalog-and-subscriptions PRD.
//
// Two modes (controlled by `mode` prop):
//   - 'fork':   creating a Personal Book from a House Book template
//   - 'edit':   modifying an existing Personal Book
//
// Editable fields:
//   - name
//   - conditions.strength_min (slider, 0 → 1)
//   - starting_units (number input)
//   - match_scope (all / my_leagues)
//
// signal_type / signal_version are NOT editable here (server enforces). To
// switch signals → archive this book and create a new one.
//
// Conditions UI is intentionally minimalist in V1.5 (only strength_min). The
// raw conditions_json (filters[]) is preserved on PATCH if untouched —
// advanced editing belongs to a future JSON-editor surface.
import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import {
  api,
  type Book,
  type BookCreateBody,
  type BookUpdateBody,
} from '../../lib/api'
import { useT } from '../../lib/i18n'

type Mode =
  | { kind: 'fork'; from: Book }
  | { kind: 'edit'; book: Book }

export default function BookEditor({
  mode, onClose,
}: {
  mode: Mode
  onClose: () => void
}) {
  const t = useT()
  const qc = useQueryClient()

  const initial = mode.kind === 'fork' ? mode.from : mode.book
  const isFork = mode.kind === 'fork'

  const [name, setName] = useState(isFork ? '' : initial.name)
  const [strengthMin, setStrengthMin] = useState<number>(
    typeof initial.conditions?.strength_min === 'number'
      ? initial.conditions.strength_min : 0,
  )
  const [startingUnits, setStartingUnits] = useState<number>(initial.starting_units)
  const [matchScope, setMatchScope] = useState<'all' | 'my_leagues'>(
    isFork ? 'my_leagues' : initial.match_scope,
  )

  const mut = useMutation({
    mutationFn: () => {
      // Build updated conditions: preserve any non-strength_min keys (filters etc.)
      // and write the slider value back into strength_min.
      const conditions: Record<string, any> = { ...(initial.conditions || {}) }
      if (strengthMin > 0) {
        conditions.strength_min = strengthMin
      } else {
        delete conditions.strength_min
      }
      if (mode.kind === 'fork') {
        const body: BookCreateBody = {
          name: name.trim(),
          fork_from: mode.from.id,
          conditions,
          starting_units: startingUnits,
          match_scope: matchScope,
        }
        return api.paperTrading.createBook(body)
      }
      // edit mode — only send changed fields, but easier to send everything.
      const body: BookUpdateBody = {
        name: name.trim(),
        conditions,
        starting_units: startingUnits,
        match_scope: matchScope,
      }
      return api.paperTrading.updateBook(mode.book.id, body)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['paper.books'] })
      onClose()
    },
  })

  const isValid = name.trim().length > 0 && startingUnits > 0
  const errorMsg = mut.isError ? String((mut.error as Error)?.message ?? mut.error) : null

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.55)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100,
      }}
    >
      <div
        className="card"
        onClick={(e) => e.stopPropagation()}
        style={{
          width: 'min(520px, calc(100% - 32px))',
          maxHeight: 'calc(100% - 64px)',
          overflow: 'auto', padding: 20,
        }}
      >
        <header style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 16 }}>
          <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700 }}>
            {isFork ? t('book.editor.title.fork') : t('book.editor.title.edit')}
          </h3>
          <span style={{ color: 'var(--text-mute)', fontSize: 13 }}>
            {initial.signal_type.replace(/^GS-/, '')}
          </span>
          <button onClick={onClose} className="chip" style={{ marginLeft: 'auto' }}>×</button>
        </header>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <Field label={t('book.editor.field.name')}>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={80}
              placeholder={t('book.editor.field.name.placeholder')}
              style={{
                width: '100%', padding: '6px 10px', borderRadius: 4,
                border: '1px solid var(--border)', background: 'var(--bg)',
                color: 'var(--text)', fontSize: 14,
              }}
            />
          </Field>

          <Field label={`${t('book.editor.field.strength_min')}: ${strengthMin.toFixed(2)}`}>
            <input
              type="range"
              min={0} max={1} step={0.05}
              value={strengthMin}
              onChange={(e) => setStrengthMin(parseFloat(e.target.value))}
              style={{ width: '100%' }}
            />
          </Field>

          <Field label={t('book.editor.field.starting_units')}>
            <input
              type="number"
              value={startingUnits}
              onChange={(e) => setStartingUnits(parseFloat(e.target.value) || 0)}
              min={1} max={1_000_000} step={10}
              style={{
                width: 120, padding: '6px 10px', borderRadius: 4,
                border: '1px solid var(--border)', background: 'var(--bg)',
                color: 'var(--text)', fontSize: 14,
              }}
            />
          </Field>

          <Field label={t('book.editor.field.match_scope')}>
            <div style={{ display: 'flex', gap: 6 }}>
              <button
                type="button"
                className={`chip${matchScope === 'all' ? ' active' : ''}`}
                onClick={() => setMatchScope('all')}
              >{t('paper.books.match.all')}</button>
              <button
                type="button"
                className={`chip${matchScope === 'my_leagues' ? ' active' : ''}`}
                onClick={() => setMatchScope('my_leagues')}
              >{t('paper.books.match.my_leagues')}</button>
            </div>
          </Field>

          {errorMsg && (
            <div style={{ color: 'var(--neg)', fontSize: 13 }}>{errorMsg}</div>
          )}

          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <button className="chip" onClick={onClose}>
              {t('book.editor.cancel')}
            </button>
            <button
              className="chip active"
              disabled={!isValid || mut.isPending}
              onClick={() => mut.mutate()}
            >
              {mut.isPending
                ? t('book.editor.saving')
                : (isFork ? t('book.editor.create') : t('book.editor.save'))}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-mute)', marginBottom: 4 }}>
        {label}
      </div>
      {children}
    </div>
  )
}

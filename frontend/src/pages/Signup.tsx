import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../lib/auth'
import { useT } from '../lib/i18n'

type ErrState = { text: string; showLoginLink?: boolean }

// Parse `Error("HTTP <status>: <detail>")` thrown by api.ts into a user-facing
// message. Returns the i18n key plus optional CTA ("已注册 → 去登录").
function formatSignupError(e: unknown, t: (k: string, p?: Record<string, string | number>) => string): ErrState {
  if (!(e instanceof Error)) return { text: t('auth.err.network') }
  const m = e.message.match(/^HTTP (\d+): (.*)$/s)
  if (!m) return { text: t('auth.err.network') }
  const status = Number(m[1])
  const body = m[2]
  if (status === 409) return { text: t('auth.err.duplicate_email'), showLoginLink: true }
  if (status === 422) {
    // FastAPI returns `{"detail":[{loc,msg,type,...}]}`. Surface the first issue.
    try {
      const j = JSON.parse(body)
      const first = Array.isArray(j.detail) ? j.detail[0] : null
      if (first?.loc?.includes('password')) return { text: t('auth.err.weak_password') }
      if (first?.loc?.includes('email'))    return { text: t('auth.err.invalid_email') }
      if (first?.msg)                       return { text: t('auth.err.validation', { msg: first.msg }) }
    } catch { /* fall through */ }
    return { text: t('auth.err.validation_generic') }
  }
  // Server-side 5xx or unrecognized status: surface the raw detail so users see WHY.
  let detail = body
  try { const j = JSON.parse(body); if (typeof j.detail === 'string') detail = j.detail } catch { /* keep raw */ }
  return { text: t('auth.err.server', { code: status, detail: detail.slice(0, 200) }) }
}

export default function Signup() {
  const nav = useNavigate()
  const { signup } = useAuth()
  const t = useT()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState<ErrState | null>(null)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setErr(null)
    try {
      await signup.mutateAsync({ email, password })
      nav('/settings/leagues')
    } catch (e: unknown) {
      setErr(formatSignupError(e, t))
    }
  }

  return (
    <div className="auth-page">
      <form className="auth-card" onSubmit={submit}>
        <div className="auth-title">{t('auth.signup.title')}</div>
        <label className="auth-field">
          <span>{t('auth.email')}</span>
          <input type="email" required value={email} onChange={e => setEmail(e.target.value)} autoFocus />
        </label>
        <label className="auth-field">
          <span>{t('auth.password')}</span>
          <input type="password" required minLength={8} value={password} onChange={e => setPassword(e.target.value)} />
          <span className="auth-hint">{t('auth.password_hint')}</span>
        </label>
        {err && (
          <div className="auth-err">
            {err.text}
            {err.showLoginLink && <> <Link to="/login">{t('auth.err.go_login')}</Link></>}
          </div>
        )}
        <button className="btn btn-primary" type="submit" disabled={signup.isPending}>
          {signup.isPending ? t('auth.signup.submitting') : t('auth.signup')}
        </button>
        <div className="auth-foot">
          {t('auth.signup.have_account')}<Link to="/login">{t('auth.login')}</Link>
        </div>
      </form>
    </div>
  )
}

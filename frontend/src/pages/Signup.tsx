import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../lib/auth'
import { useT } from '../lib/i18n'

export default function Signup() {
  const nav = useNavigate()
  const { signup } = useAuth()
  const t = useT()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState<string | null>(null)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setErr(null)
    try {
      await signup.mutateAsync({ email, password })
      // First-time activation: route to my-leagues so the user picks prefs before
      // the dashboard / matches / mispricings pages have anything meaningful to show.
      nav('/settings/leagues')
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : ''
      if (msg.includes('409')) setErr(t('auth.err.duplicate_email'))
      else if (msg.includes('422')) setErr(t('auth.err.weak_password'))
      else setErr(t('auth.err.generic'))
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
        {err && <div className="auth-err">{err}</div>}
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

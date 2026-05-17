import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../lib/auth'
import { useT } from '../lib/i18n'

export default function Login() {
  const nav = useNavigate()
  const { login } = useAuth()
  const t = useT()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState<string | null>(null)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setErr(null)
    try {
      await login.mutateAsync({ email, password })
      nav('/')
    } catch {
      setErr(t('auth.err.bad_credentials'))
    }
  }

  return (
    <div className="auth-page">
      <form className="auth-card" onSubmit={submit}>
        <div className="auth-title">{t('auth.login.title')}</div>
        <label className="auth-field">
          <span>{t('auth.email')}</span>
          <input type="email" required value={email} onChange={e => setEmail(e.target.value)} autoFocus />
        </label>
        <label className="auth-field">
          <span>{t('auth.password')}</span>
          <input type="password" required minLength={8} value={password} onChange={e => setPassword(e.target.value)} />
        </label>
        {err && <div className="auth-err">{err}</div>}
        <button className="btn btn-primary" type="submit" disabled={login.isPending}>
          {login.isPending ? t('auth.login.submitting') : t('auth.login')}
        </button>
        <div className="auth-foot">
          {t('auth.login.no_account')}<Link to="/signup">{t('auth.signup')}</Link>
        </div>
      </form>
    </div>
  )
}

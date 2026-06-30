'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { createBrowserSupabaseClient } from '@/lib/browserSupabaseClient'

interface Props {
  initialEmail:      string | null
  initialRole:       string | null
  isDemo:            boolean
  browserConfigured: boolean
}

type FormState = 'idle' | 'loading' | 'error' | 'success'

export default function LoginForm({ initialEmail, initialRole, isDemo, browserConfigured }: Props) {
  const router = useRouter()
  const [email,     setEmail]     = useState('')
  const [password,  setPassword]  = useState('')
  const [state,     setState]     = useState<FormState>('idle')
  const [errorMsg,  setErrorMsg]  = useState<string | null>(null)

  const isLoggedIn = !!initialEmail && !isDemo

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault()
    if (!browserConfigured) return
    setState('loading')
    setErrorMsg(null)
    try {
      const client = createBrowserSupabaseClient()
      const { error } = await client.auth.signInWithPassword({ email, password })
      if (error) {
        setErrorMsg(error.message)
        setState('error')
        return
      }
      setState('success')
      router.refresh()
      router.push('/system/auth-session')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown error'
      setErrorMsg(msg)
      setState('error')
    }
  }

  async function handleLogout() {
    if (!browserConfigured) {
      router.push('/logout')
      return
    }
    setState('loading')
    try {
      const client = createBrowserSupabaseClient()
      await client.auth.signOut()
      router.refresh()
    } catch {
      // ignore sign-out errors
    } finally {
      setState('idle')
    }
  }

  // ── Already logged in ──────────────────────────────────────────────────────
  if (isLoggedIn) {
    return (
      <div>
        <div
          style={{
            padding:      '12px 16px',
            background:   '#d1fae5',
            borderRadius: 6,
            marginBottom: 20,
          }}
        >
          <div style={{ fontWeight: 600, color: '#065f46', marginBottom: 4 }}>
            Signed in
          </div>
          <div style={{ fontSize: 14, color: '#374151' }}>
            <strong>Email:</strong> {initialEmail}
          </div>
          {initialRole && (
            <div style={{ fontSize: 14, color: '#374151', marginTop: 2 }}>
              <strong>Role:</strong> {initialRole}
            </div>
          )}
        </div>
        <button
          onClick={handleLogout}
          disabled={state === 'loading'}
          style={buttonStyle('#ef4444')}
        >
          {state === 'loading' ? 'Signing out…' : 'Sign out'}
        </button>
      </div>
    )
  }

  // ── Demo fallback active ───────────────────────────────────────────────────
  if (isDemo && initialEmail) {
    return (
      <div>
        <div
          style={{
            padding:      '10px 14px',
            background:   '#dbeafe',
            borderRadius: 6,
            marginBottom: 20,
            fontSize: 13,
            color: '#1e40af',
          }}
        >
          Demo fallback active — no real session. Email: {initialEmail}
        </div>
        {browserConfigured && (
          <form onSubmit={handleLogin}>
            {_renderFields(email, setEmail, password, setPassword, state, errorMsg)}
          </form>
        )}
      </div>
    )
  }

  // ── Login form ─────────────────────────────────────────────────────────────
  return (
    <form onSubmit={handleLogin}>
      {_renderFields(email, setEmail, password, setPassword, state, errorMsg)}
    </form>
  )
}

function _renderFields(
  email:      string,
  setEmail:   (v: string) => void,
  password:   string,
  setPassword:(v: string) => void,
  state:      FormState,
  errorMsg:   string | null,
) {
  return (
    <>
      <div style={{ marginBottom: 16 }}>
        <label style={labelStyle}>Email</label>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          placeholder="admin@quantaaptus.local"
          style={inputStyle}
        />
      </div>
      <div style={{ marginBottom: 20 }}>
        <label style={labelStyle}>Password</label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          placeholder="••••••••"
          style={inputStyle}
        />
      </div>
      {errorMsg && (
        <div style={{ marginBottom: 14, padding: '8px 12px', background: '#fee2e2', borderRadius: 4, fontSize: 13, color: '#991b1b' }}>
          {errorMsg}
        </div>
      )}
      {state === 'success' && (
        <div style={{ marginBottom: 14, padding: '8px 12px', background: '#d1fae5', borderRadius: 4, fontSize: 13, color: '#065f46' }}>
          Signed in — redirecting…
        </div>
      )}
      <button
        type="submit"
        disabled={state === 'loading' || state === 'success'}
        style={buttonStyle('#3b82f6')}
      >
        {state === 'loading' ? 'Signing in…' : 'Sign in'}
      </button>
    </>
  )
}

const labelStyle: React.CSSProperties = {
  display:      'block',
  marginBottom: 6,
  fontSize:     14,
  fontWeight:   600,
  color:        '#374151',
}

const inputStyle: React.CSSProperties = {
  display:      'block',
  width:        '100%',
  padding:      '8px 10px',
  fontSize:     14,
  border:       '1px solid #d1d5db',
  borderRadius: 4,
  outline:      'none',
  boxSizing:    'border-box',
}

function buttonStyle(bg: string): React.CSSProperties {
  return {
    padding:      '9px 18px',
    background:   bg,
    color:        '#fff',
    border:       'none',
    borderRadius: 4,
    fontSize:     14,
    fontWeight:   600,
    cursor:       'pointer',
  }
}

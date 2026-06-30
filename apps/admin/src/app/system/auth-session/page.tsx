/**
 * /system/auth-session — Gate 61 auth session diagnostic.
 *
 * Server Component — shows current session state without exposing secrets.
 * Uses getServerAuthSession() and getCurrentProfile() from serverSupabaseAuth.
 */
import { getServerAuthSession, getCurrentProfile, getAuthMode } from '@/lib/serverSupabaseAuth'
import { isBrowserSupabaseConfigured } from '@/lib/browserSupabaseClient'
import { getContentSourceMode } from '@/lib/contentSource'

export const dynamic = 'force-dynamic'

function Badge({ label, ok }: { label: string; ok: boolean }) {
  return (
    <span
      style={{
        display:         'inline-block',
        padding:         '2px 8px',
        borderRadius:    4,
        fontSize:        12,
        fontWeight:      600,
        backgroundColor: ok ? '#d1fae5' : '#fee2e2',
        color:           ok ? '#065f46' : '#991b1b',
        marginLeft:      8,
      }}
    >
      {label}
    </span>
  )
}

function InfoBadge({ label }: { label: string }) {
  return (
    <span
      style={{
        display:         'inline-block',
        padding:         '2px 8px',
        borderRadius:    4,
        fontSize:        12,
        fontWeight:      600,
        backgroundColor: '#dbeafe',
        color:           '#1e40af',
        marginLeft:      8,
      }}
    >
      {label}
    </span>
  )
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <tr>
      <td style={{ padding: '5px 16px 5px 0', color: '#6b7280', whiteSpace: 'nowrap' }}>{label}</td>
      <td style={{ padding: '5px 0', fontFamily: 'monospace', fontSize: 13 }}>{value}</td>
    </tr>
  )
}

function Alert({ variant, children }: { variant: 'warn' | 'info' | 'success'; children: React.ReactNode }) {
  const c = {
    warn:    { bg: '#fef3c7', color: '#92400e' },
    info:    { bg: '#dbeafe', color: '#1e40af' },
    success: { bg: '#d1fae5', color: '#065f46' },
  }[variant]
  return (
    <div
      style={{
        marginTop:  10,
        padding:    '8px 12px',
        background: c.bg,
        borderRadius: 4,
        fontSize:   13,
        color:      c.color,
      }}
    >
      {children}
    </div>
  )
}

export default async function AuthSessionPage() {
  const contentMode      = getContentSourceMode()
  const authMode         = getAuthMode()
  const browserConfigured = isBrowserSupabaseConfigured()
  const demoFallback     = process.env.QA_AUTH_DEMO_FALLBACK === 'true'

  const session = await getServerAuthSession()
  const profile = session && !session.is_demo ? await getCurrentProfile() : null

  const isLoggedIn   = !!session && !session.is_demo
  const isDemoActive = !!session?.is_demo

  return (
    <main style={{ padding: '2rem', maxWidth: 680, fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>
        Auth Session Diagnostic
      </h1>
      <p style={{ color: '#6b7280', marginBottom: 28, fontSize: 14 }}>
        Gate 61 — shows current session state. No secrets displayed.
      </p>

      {/* Config */}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>Configuration</h2>
        <table style={{ borderCollapse: 'collapse' }}>
          <tbody>
            <Row
              label="QA_CONTENT_SOURCE"
              value={<code>{contentMode}</code>}
            />
            <Row
              label="Auth mode"
              value={
                <>
                  <code>{authMode}</code>
                  <InfoBadge label={authMode} />
                </>
              }
            />
            <Row
              label="NEXT_PUBLIC_SUPABASE_URL"
              value={<Badge label={browserConfigured ? 'Present' : 'Missing'} ok={browserConfigured} />}
            />
            <Row
              label="NEXT_PUBLIC_SUPABASE_ANON_KEY"
              value={<Badge label={browserConfigured ? 'Present' : 'Missing'} ok={browserConfigured} />}
            />
            <Row
              label="QA_AUTH_DEMO_FALLBACK"
              value={<Badge label={demoFallback ? 'true' : 'false'} ok={!demoFallback} />}
            />
          </tbody>
        </table>
      </section>

      {/* Session */}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>
          Current Session
          {isLoggedIn && <Badge label="Signed in" ok />}
          {isDemoActive && <InfoBadge label="demo fallback" />}
          {!session && <Badge label="No session" ok={false} />}
        </h2>
        <table style={{ borderCollapse: 'collapse' }}>
          <tbody>
            <Row
              label="status"
              value={
                isLoggedIn   ? <span style={{ color: '#065f46', fontWeight: 600 }}>authenticated</span>
                : isDemoActive ? <span style={{ color: '#1e40af' }}>demo fallback</span>
                : <span style={{ color: '#991b1b' }}>no session</span>
              }
            />
            <Row
              label="email"
              value={session?.email ?? <span style={{ color: '#9ca3af' }}>—</span>}
            />
            <Row
              label="is_demo"
              value={<code>{String(session?.is_demo ?? false)}</code>}
            />
          </tbody>
        </table>

        {isLoggedIn && (
          <Alert variant="success">
            Real Supabase Auth session active. Signed in as <strong>{session!.email}</strong>.
          </Alert>
        )}
        {isDemoActive && (
          <Alert variant="info">
            Demo fallback is active (QA_AUTH_DEMO_FALLBACK=true). No real session found.
            <a href="/login" style={{ marginLeft: 8, color: '#1e40af' }}>Sign in</a>
          </Alert>
        )}
        {!session && (
          <Alert variant="warn">
            No session and demo fallback is off. <a href="/login" style={{ color: '#92400e' }}>Sign in</a>
          </Alert>
        )}
      </section>

      {/* Profile */}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>
          Profile
          {profile && <Badge label={profile.role ?? 'unknown'} ok={!!profile.role} />}
        </h2>
        {profile && (
          <table style={{ borderCollapse: 'collapse' }}>
            <tbody>
              <Row label="id"           value={<code>{profile.id}</code>} />
              <Row label="display_name" value={profile.display_name ?? '—'} />
              <Row label="email"        value={profile.email ?? '—'} />
              <Row label="role"         value={<code>{profile.role ?? '—'}</code>} />
              <Row
                label="organization_id"
                value={profile.organization_id
                  ? <code>{profile.organization_id}</code>
                  : <span style={{ color: '#9ca3af' }}>null</span>}
              />
            </tbody>
          </table>
        )}
        {!profile && isDemoActive && (
          <Alert variant="info">
            Demo profile — real profile lookup skipped when demo fallback is active.
          </Alert>
        )}
        {!profile && !isDemoActive && (
          <Alert variant="warn">
            No profile found. Sign in first, or run <code>supabase/seed/seed_demo_auth_profiles.sql</code>.
          </Alert>
        )}
      </section>

      {/* Actions */}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>Actions</h2>
        <p style={{ fontSize: 13 }}>
          <a href="/login"  style={{ color: '#3b82f6', marginRight: 16 }}>Login page</a>
          <a href="/logout" style={{ color: '#3b82f6', marginRight: 16 }}>Sign out</a>
          <a href="/system/auth-roles" style={{ color: '#3b82f6' }}>Auth Roles</a>
        </p>
      </section>

      {/* Nav */}
      <p style={{ fontSize: 13, color: '#6b7280', marginTop: 12 }}>
        <a href="/system/student-results" style={{ color: '#3b82f6', marginRight: 16 }}>Student Results</a>
        <a href="/system/teacher-review"  style={{ color: '#3b82f6', marginRight: 16 }}>Teacher Review</a>
        <a href="/system/marking"         style={{ color: '#3b82f6', marginRight: 16 }}>Marking</a>
        <a href="/system/content-source"  style={{ color: '#3b82f6' }}>Content Source</a>
      </p>
    </main>
  )
}

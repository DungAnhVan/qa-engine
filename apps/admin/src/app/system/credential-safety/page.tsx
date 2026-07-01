import { requireAppRole } from '@/lib/roleAccess'
import { getContentSourceMode } from '@/lib/contentSource'

export const dynamic = 'force-dynamic'

function Badge({ label, ok, neutral }: { label: string; ok?: boolean; neutral?: boolean }) {
  const bg = neutral ? '#dbeafe' : ok ? '#d1fae5' : '#fee2e2'
  const fg = neutral ? '#1e40af' : ok ? '#065f46' : '#991b1b'
  return (
    <span
      style={{
        display:         'inline-block',
        padding:         '2px 8px',
        borderRadius:    4,
        fontSize:        12,
        fontWeight:      600,
        backgroundColor: bg,
        color:           fg,
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
      <td style={{ padding: '5px 16px 5px 0', color: '#6b7280', whiteSpace: 'nowrap', verticalAlign: 'top' }}>
        {label}
      </td>
      <td style={{ padding: '5px 0', fontFamily: 'monospace', fontSize: 13 }}>
        {value}
      </td>
    </tr>
  )
}

export default async function CredentialSafetyPage() {
  const { allowed, currentRole } = await requireAppRole(['admin'])
  if (!allowed) return (
    <main style={{ padding: '2rem', fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>Access denied</h1>
      <p style={{ color: '#6b7280', fontSize: 14, marginBottom: 12 }}>
        Required: admin. Your role: <code>{currentRole ?? 'none'}</code>
      </p>
      <a href="/login" style={{ color: '#3b82f6' }}>Sign in →</a>
    </main>
  )

  const contentSource   = getContentSourceMode()
  const demoFallback    = process.env.QA_AUTH_DEMO_FALLBACK
  const nodeEnv         = process.env.NODE_ENV ?? 'development'
  const isProduction    = nodeEnv === 'production'

  const demoFallbackOff   = demoFallback === 'false'
  const isLive            = contentSource === 'live_supabase'
  const internalTestingSafe = demoFallbackOff && isLive

  const DEMO_EMAILS = [
    'admin@quantaaptus.local',
    'teacher@quantaaptus.local',
    'student@quantaaptus.local',
    'parent@quantaaptus.local',
  ]

  return (
    <main style={{ padding: '2rem', maxWidth: 800, fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>
        Credential Safety
        <Badge
          label={internalTestingSafe ? 'INTERNAL TESTING OK' : 'ACTION REQUIRED'}
          ok={internalTestingSafe}
        />
      </h1>
      <p style={{ color: '#6b7280', marginBottom: 24, fontSize: 13 }}>
        Gate 69A — production credential hardening diagnostic. No secrets displayed.
      </p>

      {/* Warning banner */}
      <div
        style={{
          marginBottom: 24,
          padding:      '12px 16px',
          background:   '#fef3c7',
          borderRadius: 6,
          borderLeft:   '4px solid #f59e0b',
          fontSize:     13,
          color:        '#92400e',
        }}
      >
        <strong>Public launch is blocked.</strong> Demo accounts with known passwords may still exist.
        Complete the checklist in{' '}
        <code>deployment/PRODUCTION_CREDENTIAL_HARDENING_GATE69A.md</code> before allowing
        public traffic.
      </div>

      {/* Environment */}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8, color: '#374151', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Environment
        </h2>
        <table style={{ borderCollapse: 'collapse' }}>
          <tbody>
            <Row
              label="NODE_ENV"
              value={
                <>
                  <code>{nodeEnv}</code>
                  <Badge label={isProduction ? 'production' : 'development'} ok={isProduction} neutral={!isProduction} />
                </>
              }
            />
            <Row
              label="QA_CONTENT_SOURCE"
              value={
                <>
                  <code>{contentSource}</code>
                  <Badge label={isLive ? 'live_supabase' : contentSource} ok={isLive} />
                </>
              }
            />
            <Row
              label="QA_AUTH_DEMO_FALLBACK"
              value={
                <>
                  <code>{demoFallback ?? 'not_set'}</code>
                  <Badge
                    label={demoFallbackOff ? 'off (correct)' : demoFallback === 'true' ? 'on — RISK' : 'not set — WARN'}
                    ok={demoFallbackOff}
                  />
                </>
              }
            />
          </tbody>
        </table>
      </section>

      {/* Known demo accounts */}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8, color: '#374151', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Known Demo Accounts
        </h2>
        <p style={{ fontSize: 13, color: '#6b7280', marginBottom: 8 }}>
          These accounts may still exist in Supabase Auth with documented passwords.
          Run the credential safety check script to verify their current status.
        </p>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
              <th style={{ textAlign: 'left', padding: '5px 12px 5px 0', color: '#374151', fontWeight: 600 }}>Email</th>
              <th style={{ textAlign: 'left', padding: '5px 12px 5px 0', color: '#374151', fontWeight: 600 }}>Role</th>
              <th style={{ textAlign: 'left', padding: '5px 0', color: '#374151', fontWeight: 600 }}>Risk</th>
            </tr>
          </thead>
          <tbody>
            {[
              { email: DEMO_EMAILS[0], role: 'admin',   risk: 'HIGH — full admin access' },
              { email: DEMO_EMAILS[1], role: 'teacher', risk: 'MEDIUM' },
              { email: DEMO_EMAILS[2], role: 'student', risk: 'LOW' },
              { email: DEMO_EMAILS[3], role: 'parent',  risk: 'LOW' },
            ].map(({ email, role, risk }) => (
              <tr key={email} style={{ borderBottom: '1px solid #f3f4f6' }}>
                <td style={{ padding: '5px 12px 5px 0', fontFamily: 'monospace', fontSize: 12 }}>{email}</td>
                <td style={{ padding: '5px 12px 5px 0' }}><code>{role}</code></td>
                <td style={{ padding: '5px 0', fontSize: 12, color: risk.startsWith('HIGH') ? '#991b1b' : '#92400e' }}>
                  {risk}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {/* Launch readiness */}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8, color: '#374151', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Launch Readiness
        </h2>
        <table style={{ borderCollapse: 'collapse', fontSize: 13 }}>
          <tbody>
            <Row
              label="Safe for internal testing"
              value={<Badge label={internalTestingSafe ? 'YES' : 'NO'} ok={internalTestingSafe} />}
            />
            <Row
              label="Safe for public launch"
              value={
                <>
                  <Badge label="NO — credential hardening required" ok={false} />
                  <span style={{ marginLeft: 8, fontSize: 12, color: '#6b7280' }}>manual action required</span>
                </>
              }
            />
            <Row
              label="Real admin account"
              value={
                <>
                  <Badge label="UNVERIFIED" ok={false} />
                  <span style={{ marginLeft: 8, fontSize: 12, color: '#6b7280' }}>
                    run create_gate69a_real_admin_user_v1.py
                  </span>
                </>
              }
            />
            <Row
              label="Demo passwords rotated"
              value={
                <>
                  <Badge label="UNVERIFIED" ok={false} />
                  <span style={{ marginLeft: 8, fontSize: 12, color: '#6b7280' }}>
                    run check_gate69a_credential_safety_v1.py
                  </span>
                </>
              }
            />
          </tbody>
        </table>
      </section>

      {/* Required actions */}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8, color: '#374151', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Required Actions Before Public Launch
        </h2>
        <ol style={{ fontSize: 13, color: '#374151', paddingLeft: 20, lineHeight: 1.9 }}>
          <li>
            Create real admin account — run{' '}
            <code>tools/deploy/create_gate69a_real_admin_user_v1.py</code>
          </li>
          <li>Sign in with real admin and verify role on <a href="/system/auth-session" style={{ color: '#3b82f6' }}>auth-session</a> page</li>
          <li>
            Rotate or disable demo accounts — run{' '}
            <code>tools/deploy/disable_gate69a_demo_users_v1.py</code>
          </li>
          <li>
            Run credential safety check — run{' '}
            <code>tools/deploy/check_gate69a_credential_safety_v1.py</code>
          </li>
          <li>Confirm <code>QA_AUTH_DEMO_FALLBACK=false</code> in Vercel env vars (already done)</li>
          <li>Confirm <code>SUPABASE_SERVICE_ROLE_KEY</code> has no <code>NEXT_PUBLIC_</code> prefix</li>
        </ol>
        <p style={{ fontSize: 13, marginTop: 8 }}>
          Full guide: <code>deployment/PRODUCTION_CREDENTIAL_HARDENING_GATE69A.md</code>
        </p>
      </section>

      {/* Scripts */}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8, color: '#374151', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Check Scripts
        </h2>
        <pre
          style={{
            background:   '#f3f4f6',
            padding:      '12px 16px',
            borderRadius: 4,
            fontSize:     12,
            overflowX:    'auto',
            lineHeight:   1.7,
          }}
        >
          {[
            '# Dry-run: create real admin (no changes)',
            '.venv-ingest\\Scripts\\python.exe tools\\deploy\\create_gate69a_real_admin_user_v1.py \\',
            '    --email your@email.com --password-env QA_REAL_ADMIN_PASSWORD',
            '',
            '# Check credential safety',
            '.venv-ingest\\Scripts\\python.exe tools\\deploy\\check_gate69a_credential_safety_v1.py \\',
            '    https://admin.quantaaptus.com --real-admin-email your@email.com',
            '',
            '# Disable demo users (dry-run)',
            '.venv-ingest\\Scripts\\python.exe tools\\deploy\\disable_gate69a_demo_users_v1.py',
          ].join('\n')}
        </pre>
      </section>

      {/* Navigation */}
      <p style={{ fontSize: 13, color: '#6b7280', marginTop: 24 }}>
        <a href="/api/system/credential-safety" style={{ color: '#3b82f6', marginRight: 16 }}>Credential Safety API</a>
        <a href="/system/demo-safety"           style={{ color: '#3b82f6', marginRight: 16 }}>Demo Safety</a>
        <a href="/system/health"                style={{ color: '#3b82f6', marginRight: 16 }}>Health</a>
        <a href="/system/readiness"             style={{ color: '#3b82f6', marginRight: 16 }}>Readiness</a>
        <a href="/system/auth-session"          style={{ color: '#3b82f6' }}>Auth Session</a>
      </p>
    </main>
  )
}

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

export default async function DemoSafetyPage() {
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

  const contentSource  = getContentSourceMode()
  const demoFallback   = process.env.QA_AUTH_DEMO_FALLBACK
  const nodeEnv        = process.env.NODE_ENV ?? 'development'
  const isProduction   = nodeEnv === 'production'

  const demoFallbackOff  = demoFallback === 'false'
  const isLive           = contentSource === 'live_supabase'

  // Public launch is always unsafe while demo accounts exist.
  // Only manual verification by an admin can clear this status.
  const internalTestingSafe = demoFallbackOff && isLive

  const DEMO_EMAILS = [
    'admin@quantaaptus.local',
    'teacher@quantaaptus.local',
    'student@quantaaptus.local',
    'parent@quantaaptus.local',
  ]

  return (
    <main style={{ padding: '2rem', maxWidth: 760, fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>
        Demo Account Safety
        <Badge
          label={internalTestingSafe ? 'INTERNAL TESTING OK' : 'NEEDS ATTENTION'}
          ok={internalTestingSafe}
        />
      </h1>
      <p style={{ color: '#6b7280', marginBottom: 24, fontSize: 13 }}>
        Gate 66 — production demo safety diagnostic. No secrets displayed.
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
        <strong>Public launch is blocked.</strong> Demo accounts exist with known passwords
        (documented in Gate 61). Rotate or remove all <code>@quantaaptus.local</code> accounts
        before pointing a public domain to this deployment.
        See <code>deployment/PRODUCTION_DEMO_SAFETY_GATE66.md</code> for steps.
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

      {/* Demo accounts */}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8, color: '#374151', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Known Demo Accounts
        </h2>
        <p style={{ fontSize: 13, color: '#6b7280', marginBottom: 8 }}>
          These accounts may exist in the Supabase Auth database.
          Run the check script to verify their current status.
        </p>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
              <th style={{ textAlign: 'left', padding: '5px 12px 5px 0', color: '#374151', fontWeight: 600 }}>Email</th>
              <th style={{ textAlign: 'left', padding: '5px 0', color: '#374151', fontWeight: 600 }}>Role</th>
              <th style={{ textAlign: 'left', padding: '5px 0', color: '#374151', fontWeight: 600 }}>Status</th>
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
                  {risk} — password documented
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <p style={{ fontSize: 12, color: '#9ca3af', marginTop: 8 }}>
          Run <code>tools/deploy/check_gate66_demo_user_safety_v1.py</code> to verify
          which accounts still exist in Supabase.
        </p>
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
              value={
                <Badge
                  label={internalTestingSafe ? 'YES' : 'NO'}
                  ok={internalTestingSafe}
                />
              }
            />
            <Row
              label="Safe for public launch"
              value={
                <>
                  <Badge label="NO — passwords not rotated" ok={false} />
                  <span style={{ marginLeft: 8, fontSize: 12, color: '#6b7280' }}>
                    manual action required
                  </span>
                </>
              }
            />
            <Row
              label="Custom domain allowed"
              value={
                <>
                  <Badge label="BLOCKED" ok={false} />
                  <span style={{ marginLeft: 8, fontSize: 12, color: '#6b7280' }}>
                    complete Gate 66 checklist first
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
        <ol style={{ fontSize: 13, color: '#374151', paddingLeft: 20, lineHeight: 1.8 }}>
          <li>Rotate or delete all <code>@quantaaptus.local</code> passwords in Supabase Auth dashboard</li>
          <li>Create real admin account (<code>admin@quantaaptus.com</code>) and verify login</li>
          <li>Confirm <code>QA_AUTH_DEMO_FALLBACK=false</code> in Vercel env vars (already done)</li>
          <li>Confirm <code>SUPABASE_SERVICE_ROLE_KEY</code> is server-only in Vercel (no <code>NEXT_PUBLIC_</code> prefix)</li>
          <li>Confirm RLS is active on all Supabase tables (migration 000004)</li>
          <li>Test login with new admin credentials — old password must fail</li>
        </ol>
        <p style={{ fontSize: 13, marginTop: 8 }}>
          <a href="/system/demo-safety#" style={{ color: '#3b82f6' }}>
            Full guide: deployment/PRODUCTION_DEMO_SAFETY_GATE66.md
          </a>
        </p>
      </section>

      {/* Navigation */}
      <p style={{ fontSize: 13, color: '#6b7280', marginTop: 24 }}>
        <a href="/api/system/demo-safety" style={{ color: '#3b82f6', marginRight: 16 }}>Demo Safety API</a>
        <a href="/system/health"          style={{ color: '#3b82f6', marginRight: 16 }}>Health</a>
        <a href="/system/readiness"       style={{ color: '#3b82f6', marginRight: 16 }}>Readiness</a>
        <a href="/system/auth-session"    style={{ color: '#3b82f6', marginRight: 16 }}>Auth Session</a>
        <a href="/system/role-access"     style={{ color: '#3b82f6' }}>Role Access</a>
      </p>
    </main>
  )
}
